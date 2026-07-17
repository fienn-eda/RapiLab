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
                    yield list(c1) + list(c2) + list(c3)


def feasible_orderings(roster):
    for combo in combinations(roster, 5):
        by_tier = {1: [], 2: [], 3: []}
        infeasible = False
        for unit in combo:
            if unit.burst_tier not in by_tier:
                infeasible = True
                break
            by_tier[unit.burst_tier].append(unit)
        if infeasible or not all(by_tier[t] for t in (1, 2, 3)):
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
    return [b1, by_tier[2][0], *by_tier[3][:3]]


def _measure_against(reference, unit, boss):
    # Swap the candidate into its tier slot (B3 replaces the reference's
    # weakest B3, the last one) and score the whole deck.
    slot = {1: 0, 2: 1, 3: 4}[unit.burst_tier]
    deck = list(reference)
    if unit.slug in {u.slug for u in deck}:
        deck_score = evaluate_deck(deck, boss)["total_damage"]
        return deck_score
    deck[slot] = unit
    return evaluate_deck(deck, boss)["total_damage"]


def prune_candidate_pool(roster, boss: BossProfile):
    """Cut the roster to a pool the budget can enumerate. Scores are marginal
    contributions in reference-deck context (two passes: prior-seeded B1, then
    best-measured B1 - CDR holders change cycle count, Fienn rule 2/3), with
    synergy sets measured as pairs and weapon-themed units pulled in around
    their anchor rather than trusting the mis-contextual cut."""
    by_tier = {t: sorted((u for u in roster if u.burst_tier == t),
                         key=_prior, reverse=True) for t in (1, 2, 3)}
    if not (by_tier[1] and by_tier[2] and len(by_tier[3]) >= 3):
        return list(roster)  # too small to cut; search handles infeasibility

    scores = {}
    for reference_b1 in _reference_b1_variants(by_tier, boss):
        reference = _reference_deck(by_tier, reference_b1)
        for unit in roster:
            score = _measure_against(reference, unit, boss)
            scores[unit.slug] = max(scores.get(unit.slug, 0.0), score)

    # Synergy sets: measured as a pair in a (1,2,2) shell; both members share it.
    shell_b1, shell_b3 = by_tier[1][0], by_tier[3][:2]
    slugs = {u.slug: u for u in roster}
    for pair in SYNERGY_SETS:
        if pair <= slugs.keys():
            members = [slugs[s] for s in sorted(pair)]
            deck = [shell_b1, *members, *shell_b3]
            pair_score = evaluate_deck(deck, boss)["total_damage"]
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
    first = by_tier[1][0]
    yield first
    reference = _reference_deck(by_tier, first)
    best_b1 = max(by_tier[1],
                  key=lambda u: _measure_against(reference, u, boss))
    if best_b1.slug != first.slug:
        yield best_b1


def search_best_decks(roster, boss: BossProfile, top_n=5, sim_budget=1200, permutation_top_k=40):
    """Budget-aware replacement for exhaustive find_best_decks: canonical
    tier-order scores rank the shape combinations (intra-tier order only
    decides nuker-vs-backup roles), and only the top K get their permutations
    evaluated. When canonical enumeration alone would blow the budget, the
    roster is first cut to a candidate pool (prune_candidate_pool)."""
    pool = list(roster)
    combos = list(shape_combinations(pool))
    if len(combos) > sim_budget:
        pool = prune_candidate_pool(roster, boss)
        combos = list(shape_combinations(pool))
    canonical = sorted(
        ((evaluate_deck(combo, boss)["total_damage"], i) for i, combo in enumerate(combos)),
        reverse=True,
    )
    refined = []
    for _, i in canonical[:permutation_top_k]:
        for ordered in _intra_tier_orderings(combos[i]):
            refined.append(_summarize(ordered, evaluate_deck(ordered, boss)))
    refined.sort(key=lambda entry: entry["total_damage"], reverse=True)
    return refined[:top_n]
