"""Searches a roster for the highest-damage single deck.

Feasibility + exhaustive-over-a-pruned-space hybrid (per the plan): a deck is
5 Nikkes with at least one of each burst tier (1/2/3), else it can never
reach Full Burst. Within a feasible combination, only the relative order of
same-tier Nikkes affects the result - burst_cycle fires the leftmost eligible
per tier, so intra-tier order decides who nukes vs who is a backup buffer.
Cross-tier order never matters (tiers always fire 1->2->3), so decks are
emitted in canonical tier order.

feasible_orderings is pure combinatorics on burst_tier (no simulation), so it
works on any object exposing `.burst_tier`. Scoring goes through the roster
assembly layer + simulate_raid.

Known simplification (from the plan): flexible-burst units (Anis: Star's
re-entry, Rapi: Red Hood's Combat Assist standing in for Burst 1) are placed
by their nominal burst_tier for feasibility; their branch effects are still
simulated correctly, but the scheduler slots them nominally.
"""
from dataclasses import dataclass
from itertools import combinations, permutations

from app.raid_simulator import simulate_raid
from app.roster import assemble_simulation_inputs
from app.skill_rules.registry import MODE_VARIANTS

# variant slug -> its base, for the seat-exclusion check below.
_VARIANT_GROUP = {variant: base
                  for base, variants in MODE_VARIANTS.items() for variant in variants}


def _no_variant_clash(units):
    seen = set()
    for unit in units:
        base = _VARIANT_GROUP.get(unit.slug)
        if base is not None:
            if base in seen:
                return False
            seen.add(base)
    return True


@dataclass
class BossProfile:
    element: str | None = None
    core_hittable: bool = False
    enemy_def: float = 0.0
    fight_duration: float = 180.0
    gauge_charge_time: float = 2.0
    mode: str = "manual"
    part_destructible: bool = False


# Real decks come in exactly these B1/B2/B3 shapes (Fienn, 2026-07-17);
# "at least one of each tier" also admits shapes that never occur in play.
ALLOWED_SHAPES = ((1, 1, 3), (1, 2, 2), (2, 1, 2))


def shape_combinations(roster):
    """Canonical tier-ordered 5-unit combinations, restricted to the shapes
    real play uses. Pure combinatorics on `.burst_tier` (like
    feasible_orderings); intra-tier order is the input order."""
    by_tier = {1: [], 2: [], 3: []}
    for unit in roster:
        if unit.burst_tier in by_tier:
            by_tier[unit.burst_tier].append(unit)
    for n1, n2, n3 in ALLOWED_SHAPES:
        for c1 in combinations(by_tier[1], n1):
            for c2 in combinations(by_tier[2], n2):
                for c3 in combinations(by_tier[3], n3):
                    deck = list(c1) + list(c2) + list(c3)
                    if _no_variant_clash(deck):
                        yield deck


def feasible_orderings(roster):
    for combo in combinations(roster, 5):
        by_tier = {1: [], 2: [], 3: []}
        infeasible = False
        for unit in combo:
            if unit.burst_tier not in by_tier:
                infeasible = True
                break
            by_tier[unit.burst_tier].append(unit)
        if infeasible or not all(by_tier[t] for t in (1, 2, 3)) or not _no_variant_clash(combo):
            continue
        for order1 in permutations(by_tier[1]):
            for order2 in permutations(by_tier[2]):
                for order3 in permutations(by_tier[3]):
                    yield list(order1) + list(order2) + list(order3)


def evaluate_deck(ordered_deck, boss: BossProfile):
    inputs = assemble_simulation_inputs(ordered_deck)
    return simulate_raid(
        **inputs,
        enemy_def=boss.enemy_def,
        gauge_charge_time=boss.gauge_charge_time,
        fight_duration=boss.fight_duration,
        mode=boss.mode,
        core_hittable=boss.core_hittable,
        boss_element=boss.element,
        part_destructible=boss.part_destructible,
    )


def _score_batch(decks, boss, pool):
    """Total damage for each deck. `pool` (a SimPool, duck-typed - this module
    must not import sim_pool, which imports evaluate_deck from here) fans the
    batch out to worker processes; None runs inline."""
    if pool is None:
        return [evaluate_deck(deck, boss)["total_damage"] for deck in decks]
    return pool.score_many(decks)


def _summarize(ordered_deck, result):
    burst = sum(e["damage"] for e in result["damage_log"] if e["source"] == "burst")
    normal = sum(e["damage"] for e in result["damage_log"] if e["source"] == "normal_attack")
    return {
        "deck": [spec.slug for spec in ordered_deck],
        "total_damage": result["total_damage"],
        "burst_damage": burst,
        "normal_attack_damage": normal,
        "result": result,
    }


def find_best_decks(roster, boss: BossProfile, top_n=5):
    scored = [
        _summarize(ordered, evaluate_deck(ordered, boss))
        for ordered in feasible_orderings(roster)
    ]
    scored.sort(key=lambda entry: entry["total_damage"], reverse=True)
    return scored[:top_n]


def _intra_tier_orderings(combo):
    by_tier = {1: [], 2: [], 3: []}
    for unit in combo:
        by_tier[unit.burst_tier].append(unit)
    for o1 in permutations(by_tier[1]):
        for o2 in permutations(by_tier[2]):
            for o3 in permutations(by_tier[3]):
                yield list(o1) + list(o2) + list(o3)


# Curated two-unit sets that only work together (Fienn, 2026-07-17): candidate
# cuts must measure them as a pair and never separate them.
SYNERGY_SETS = (frozenset({"mint", "prika"}),
                frozenset({"mast-romantic-maid", "anchor-innocent-maid"}))

# A weapon-scoped buffer anchors a themed sub-pool: its weapon's B3 attackers
# are only meaningful with it in the deck (Fienn: "SG B3s need Tove"), so they
# join the pool whenever the anchor is rostered, bypassing the mis-contextual
# marginal cut.
WEAPON_SYNERGY_ANCHORS = {"tove": "SG"}

# Per-tier pool caps sized so shape_combinations stays a few hundred combos
# (~103 ms/sim budget); synergy/theme guards may exceed them slightly.
PRUNED_TIER_CAPS = {1: 2, 2: 3, 3: 6}


def _prior(unit):
    # Round-0 prior (no sims): investment-adjusted ATK x weapon hit percent.
    # Only seeds the reference decks - the swap-in measurement corrects it.
    return unit.base_stats["atk"] * unit.weapon_stats["damage_percent"]


def _reference_deck(by_tier, b1):
    return [b1, by_tier[2][0], *_variant_safe_top(by_tier[3], 3)]


def _variant_safe_top(units, n):
    """First `n` from a prior-ranked list, skipping any unit whose
    MODE_VARIANTS base is already taken - _reference_deck's B3 picks otherwise
    slice the top 3 blindly, which could seat two variants of the same base
    (e.g. both Cinderella: Crystal Wave modes) in one "deck," the exact clash
    _no_variant_clash forbids for real candidate decks (deck_search.py:32)."""
    chosen, bases_seen = [], set()
    for unit in units:
        base = _VARIANT_GROUP.get(unit.slug, unit.slug)
        if base in bases_seen:
            continue
        bases_seen.add(base)
        chosen.append(unit)
        if len(chosen) == n:
            break
    return chosen


_TIER_SLOT = {1: 0, 2: 1, 3: 4}


def _swap_slot(reference, unit):
    """Index in `reference` that swapping `unit` in should overwrite, or
    None if no single-slot swap can seat `unit` without also seating a
    MODE_VARIANTS sibling of it.

    Normally the unit's tier default (B3 replaces the reference's weakest
    B3, the last one). But if a MODE_VARIANTS sibling of `unit` already sits
    in a different reference slot (e.g. the reference's first, non-last B3
    slot), swap over the sibling instead of the tier default - otherwise the
    default slot leaves the sibling seated too, measuring a deck with both
    variants present at once, the exact clash _no_variant_clash forbids for
    real candidate decks. Swapping over the sibling (rather than skipping the
    unit) still gives it a real marginal score: how it performs standing in
    for its own sibling.

    That sibling swap-over is only safe within `unit`'s own tier family,
    though: VARIANT_BURST_TIERS lets one base's two variants span different
    burst tiers (e.g. Rapi: Red Hood's B1 stand-in vs. its B3 self), and
    every reference slot's occupant's burst_tier already IS that slot's tier
    family (_reference_deck's fixed slot-0-tier1/slot-1-tier2/slots-2-4-tier3
    layout) - comparing burst_tier directly, instead of a second slot->tier
    table, can't drift out of sync with that layout. Swapping over a
    cross-tier sibling would misplace the unit's own tier (e.g. a B3 unit
    evicting the reference's only B1); falling back to the tier default
    instead would leave that sibling seated too, still a two-variant clash.
    Neither is safe, so the swap is refused."""
    base = _VARIANT_GROUP.get(unit.slug)
    if base is not None:
        same_tier_slot, cross_tier_sibling = None, False
        for i, seated in enumerate(reference):
            if _VARIANT_GROUP.get(seated.slug) == base:
                if seated.burst_tier == unit.burst_tier:
                    same_tier_slot = i
                    break
                cross_tier_sibling = True
        if same_tier_slot is not None:
            return same_tier_slot
        if cross_tier_sibling:
            return None
    return _TIER_SLOT[unit.burst_tier]


def _cross_tier_reference(reference, unit, by_tier):
    """When `unit`'s MODE_VARIANTS sibling sits in `reference` at a
    DIFFERENT burst tier than `unit`'s own (VARIANT_BURST_TIERS), _swap_slot
    refuses the swap - see its docstring for why neither available slot is
    safe. Refusing isn't the end of the story: `unit` can still get a real
    marginal score by measuring it against a second, equally legal reference
    where the sibling is swapped out for the best other unit of the
    sibling's own tier, with `unit` then seated at its own tier-default slot
    in THAT deck. The result keeps the (1,2,3x3) shape and stays clash-free
    (the alternative is never seated elsewhere in `reference` and is never a
    same-base variant of `unit`).

    Returns `(alt_reference, deck)`. The caller must diff `deck` against a
    freshly-evaluated baseline of `alt_reference`, NOT the original
    `reference`'s baseline - that baseline still has the sibling seated, so
    it isn't a fair basis for a deck that swapped the sibling out too.

    Returns None if the sibling's tier has no alternative at all (it's the
    only unit `by_tier[sibling.burst_tier]` has) - every legal reference
    must then seat the sibling, so `unit` genuinely cannot be measured
    against this reference family. Callers must not treat that None as a
    real 0.0 score; see prune_candidate_pool and _measure_against."""
    base = _VARIANT_GROUP.get(unit.slug)
    if base is None:
        return None
    sibling, sibling_slot = None, None
    for i, seated in enumerate(reference):
        if _VARIANT_GROUP.get(seated.slug) == base and seated.burst_tier != unit.burst_tier:
            sibling, sibling_slot = seated, i
            break
    if sibling is None:
        return None
    seated_slugs = {u.slug for u in reference}
    alternative = next(
        (u for u in by_tier[sibling.burst_tier]
         if u.slug not in seated_slugs and _VARIANT_GROUP.get(u.slug, u.slug) != base),
        None,
    )
    if alternative is None:
        return None
    alt_reference = list(reference)
    alt_reference[sibling_slot] = alternative
    deck = list(alt_reference)
    deck[_TIER_SLOT[unit.burst_tier]] = unit
    return alt_reference, deck


def _measure_against(reference, unit, boss, baseline, by_tier):
    # Swap the candidate into its tier slot and score the marginal change
    # over the reference's baseline. A unit already in the reference leaves
    # the deck unchanged, so its marginal contribution is 0.0 with no
    # re-simulation. A unit with no safe single-slot swap (_swap_slot
    # returns None for a cross-tier MODE_VARIANTS sibling) is measured
    # against an alternate reference instead (_cross_tier_reference) rather
    # than being scored an unmeasured 0.0; only when that alternate doesn't
    # exist either (no other unit at the sibling's tier) does it fall
    # through to an honest, documented 0.0.
    if unit.slug in {u.slug for u in reference}:
        return 0.0
    slot = _swap_slot(reference, unit)
    if slot is not None:
        deck = list(reference)
        deck[slot] = unit
        return evaluate_deck(deck, boss)["total_damage"] - baseline
    cross = _cross_tier_reference(reference, unit, by_tier)
    if cross is None:
        return 0.0
    alt_reference, deck = cross
    alt_baseline = evaluate_deck(alt_reference, boss)["total_damage"]
    return evaluate_deck(deck, boss)["total_damage"] - alt_baseline


def prune_candidate_pool(roster, boss: BossProfile, pool=None):
    """Cut the roster to a pool the budget can enumerate. Scores are marginal
    contributions in reference-deck context (two passes: prior-seeded B1, then
    best-measured B1 - CDR holders change cycle count, Fienn rule 2/3), with
    synergy sets measured as pairs and weapon-themed units pulled in around
    their anchor rather than trusting the mis-contextual cut. A candidate
    whose MODE_VARIANTS sibling holds a cross-tier reference slot still gets
    a genuine simulated score, against an alternate reference with that
    sibling swapped out (_cross_tier_reference) - it is never scored an
    unmeasured 0.0 purely because the primary reference couldn't seat it."""
    by_tier = {t: sorted((u for u in roster if u.burst_tier == t),
                         key=_prior, reverse=True) for t in (1, 2, 3)}
    if not (by_tier[1] and by_tier[2] and len(by_tier[3]) >= 3):
        return list(roster)  # too small to cut; search handles infeasibility

    scores = {}
    for reference_b1 in _reference_b1_variants(by_tier, boss):
        reference = _reference_deck(by_tier, reference_b1)
        baseline = evaluate_deck(reference, boss)["total_damage"]
        reference_slugs = {u.slug for u in reference}
        candidates, swapped, baselines = [], [], []
        for unit in roster:
            if unit.slug in reference_slugs:
                # a unit already in the reference leaves the deck unchanged,
                # so its marginal contribution is 0.0 with no re-simulation
                scores[unit.slug] = max(scores.get(unit.slug, 0.0), 0.0)
                continue
            slot = _swap_slot(reference, unit)
            if slot is not None:
                deck = list(reference)
                deck[slot] = unit
                candidates.append(unit)
                swapped.append(deck)
                baselines.append(baseline)
                continue
            # no safe single-slot swap exists (cross-tier MODE_VARIANTS
            # sibling elsewhere in the reference, _swap_slot) - measure
            # against an alternate reference instead of starving the
            # candidate at an unmeasured 0.0 (_cross_tier_reference).
            cross = _cross_tier_reference(reference, unit, by_tier)
            if cross is None:
                # the sibling's tier has no alternative at all - no legal
                # reference can seat this candidate, so 0.0 is honest here,
                # not a measurement artifact. Still needs a scores entry so
                # the tier-cap sort below never KeyErrors on it.
                scores.setdefault(unit.slug, 0.0)
                continue
            alt_reference, deck = cross
            candidates.append(unit)
            swapped.append(deck)
            baselines.append(evaluate_deck(alt_reference, boss)["total_damage"])
        for unit, total, base in zip(candidates, _score_batch(swapped, boss, pool), baselines):
            scores[unit.slug] = max(scores.get(unit.slug, 0.0), total - base)

    # Synergy sets: measured as a pair in a (1,2,2) shell; both members share it.
    shell_b1, shell_b3 = by_tier[1][0], by_tier[3][:2]
    slugs = {u.slug: u for u in roster}
    for pair in SYNERGY_SETS:
        if pair <= slugs.keys():
            members = [slugs[s] for s in sorted(pair)]
            # burst_cycle fires the LEFTMOST eligible same-tier unit, and
            # order-dependent synergies exist (Prika must burst before Mint
            # for Encore to ever fire) - measure both orders, keep the max.
            # Shells assume a two-B2 pair; a future cross-tier set would need
            # a different shell shape.
            pair_score = max(
                evaluate_deck([shell_b1, *ordering, *shell_b3], boss)["total_damage"]
                for ordering in (members, members[::-1])
            )
            for member in members:
                scores[member.slug] = max(scores[member.slug], pair_score)

    pool = []
    for tier, cap in PRUNED_TIER_CAPS.items():
        ranked = sorted(by_tier[tier], key=lambda u: scores[u.slug], reverse=True)
        pool.extend(ranked[:cap])

    pool_slugs = {u.slug for u in pool}
    for pair in SYNERGY_SETS:  # companion pull-in
        if pair & pool_slugs and pair <= slugs.keys():
            pool.extend(slugs[s] for s in pair if s not in pool_slugs)
            pool_slugs |= pair
    for anchor, weapon in WEAPON_SYNERGY_ANCHORS.items():  # themed pull-in
        if anchor in slugs:
            themed = [u for u in roster
                      if u.slug == anchor
                      or (u.burst_tier == 3 and getattr(u, "weapon", None) == weapon)]
            pool.extend(u for u in themed if u.slug not in pool_slugs)
            pool_slugs |= {u.slug for u in themed}
    return pool


def _reference_b1_variants(by_tier, boss):
    # Pass 1: prior-seeded B1. Pass 2: the B1 whose swap-in measured best
    # (usually the CDR holder - shorter cycles change everyone's value).
    # Both candidates are scored against the same reference's baseline, so
    # the max is a fair comparison (it wouldn't be if baselines differed).
    first = by_tier[1][0]
    yield first
    reference = _reference_deck(by_tier, first)
    baseline = evaluate_deck(reference, boss)["total_damage"]
    best_b1 = max(by_tier[1],
                  key=lambda u: _measure_against(reference, u, boss, baseline, by_tier))
    if best_b1.slug != first.slug:
        yield best_b1


def search_best_decks(roster, boss: BossProfile, top_n=5, sim_budget=1200, permutation_top_k=40,
                      pool=None):
    """Budget-aware replacement for exhaustive find_best_decks: canonical
    tier-order scores rank the shape combinations (intra-tier order only
    decides nuker-vs-backup roles), and only the top K get their permutations
    evaluated. When canonical enumeration alone would blow the budget, the
    roster is first cut to a candidate pool (prune_candidate_pool). `pool` (a
    SimPool or None) fans the map-shaped batches out to worker processes."""
    candidates = list(roster)
    combos = list(shape_combinations(candidates))
    if len(combos) > sim_budget:
        candidates = prune_candidate_pool(roster, boss, pool)
        combos = list(shape_combinations(candidates))
    canonical = sorted(
        ((total, i) for i, total in enumerate(_score_batch(combos, boss, pool))),
        reverse=True,
    )
    # Permutations are ranked on slim scores first; only the returned top_n get
    # a second sim to attach the full "result" (evaluate_deck is pure, so the
    # floats are identical to scoring the full summaries directly).
    orderings = [ordered
                 for _, i in canonical[:permutation_top_k]
                 for ordered in _intra_tier_orderings(combos[i])]
    totals = _score_batch(orderings, boss, pool)
    ranked = sorted(zip(totals, orderings), key=lambda pair: pair[0], reverse=True)
    return [_summarize(ordered, evaluate_deck(ordered, boss)) for _, ordered in ranked[:top_n]]
