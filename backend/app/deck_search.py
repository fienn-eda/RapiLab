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
re-entry) are placed by their nominal burst_tier for feasibility; their
branch effects are still simulated correctly, but the scheduler slots them
nominally.
"""
from collections import Counter, defaultdict
from dataclasses import dataclass
from itertools import combinations, permutations

from app.raid_simulator import simulate_raid
from app.roster import assemble_simulation_inputs
from app.skill_rules.registry import character_map

# candidate slug -> the owned character it is a build of, for the seat-exclusion
# check below. An absent slug is its own character.
_CHARACTER_OF = character_map()


def character_of(slug):
    """The single OWNED CHARACTER a candidate slug stands for - a mode variant
    and a Favorite Item build alike map to the character they are a build of,
    and every other slug is its own character.

    Anything that must not spend one owned character twice keys on this rather
    than on the slug: a deck's seats (`_no_character_clash` below) and, because
    the player fields all of a raid's decks at once, the whole allocation
    (deck_allocation's peel, bench and hill-climb).
    """
    return _CHARACTER_OF.get(slug, slug)


def _no_character_clash(units):
    seen = set()
    for unit in units:
        character = _CHARACTER_OF.get(unit.slug)
        if character is not None:
            if character in seen:
                return False
            seen.add(character)
    return True


# Variants whose kit only holds when they are the deck's ONLY Burst-1 unit
# (Rapi: Red Hood's Combat Assist cancels itself next to a real B1 - seating
# her as one of two B1s would simulate a formation the game never produces).
SOLE_TIER1_SLUGS = {"rapi-red-hood-b1"}


def _tier1_seating_valid(units):
    tier1 = [u for u in units if u.burst_tier == 1]
    if len(tier1) <= 1:
        return True
    return not any(u.slug in SOLE_TIER1_SLUGS for u in tier1)


# Units the player runs as non-bursting buffers ("totems"): their burst is a
# DPS loss (Modernia's Destroy Mode) or buff-only with no nuke (Velvet), so they
# should yield the burst to a same-tier ally and provide only their passive /
# Skill 1-2 value. Encoded as a SEAT rule: they must sit LAST in their tier, so
# burst_cycle (which fires the leftmost eligible member) hands the burst to a
# tier-mate, and they only fall back to bursting if every tier-mate is on
# cooldown.
#
# The deck SHAPE is deliberately NOT hard-restricted (Fienn, 2026-07-22). The
# shape that actually lets them never burst needs enough same-tier allies to
# cover a burst EVERY Full-Burst cycle - one ally cannot, given the ~40s Burst
# cooldown (the same reason ALLOWED_SHAPES requires two Burst-3s), so Modernia
# wants three Burst-3s = (1,1,3) and Velvet two Burst-2s = (1,2,2). Those shapes
# simply score highest for these units, so the search picks them on its own; a
# hard shape lock would instead make a roster that cannot form the shape
# infeasible (no recommendation at all), which is the worse failure.
_BUFFER_SEAT_SLUGS = {"modernia", "velvet"}


def _buffer_seat_valid(ordered_units):
    """A buffer unit (see _BUFFER_SEAT_SLUGS) must sit LAST in its tier - no
    same-tier ally after it - so a tier-mate is the leftmost-eligible burster."""
    for i, unit in enumerate(ordered_units):
        if unit.slug in _BUFFER_SEAT_SLUGS and any(
                u.burst_tier == unit.burst_tier for u in ordered_units[i + 1:]):
            return False
    return True


@dataclass
class BossProfile:
    element: str | None = None
    core_hittable: bool = False
    enemy_def: float = 0.0
    fight_duration: float = 180.0
    # Deliberately LOW, so it rarely binds (Fienn): the real burst gauge fills
    # from damage dealt, so it is a property of the DECK, not the boss, and in
    # most compositions - anything carrying a 7.48-sec CDR unit like Anis: Star,
    # Moran or Rapi: Red Hood B1 - it fills faster than cooldowns clear and is
    # not the bottleneck at all. A single constant can only be wrong per deck,
    # so it is set where it invents the fewest constraints.
    # Known error: in the deck-4 composition, whose Volume supplies up to 8.21
    # sec of CDR a cycle, the gauge DOES bind and Fienn's range run measures it
    # at 2.65 sec (14 Full Bursts, the 14th at 2:57) - the engine's 14th lands
    # at 169 sec instead of 177. See docs/roadmap.md for the open item.
    gauge_charge_time: float = 2.0
    mode: str = "manual"
    part_destructible: bool = False
    # How far away this boss is fought, which decides WHICH weapons are inside
    # their effective range and collect +0.30 in the major bucket on their
    # normal attacks (measured on Ade: Agent Bunny, engine-gaps item 16).
    # `raid_simulator.EFFECTIVE_RANGE_BANDS` holds the weapon lists: "near"
    # pays SG/SMG, "mid" pays AR/MG, "far" pays SR, and a Rocket Launcher is
    # paid by none of them.
    #
    # It sits on the BOSS because the distance is not the player's to pick -
    # Nikke positions are fixed and the encounter sets the range (Fienn,
    # 2026-07-31). That makes it unlike the core-hit assumption, which is aim
    # and therefore a ceiling the engine may take for granted.
    #
    # None means the band has not been read for this encounter and pays nobody,
    # which is what every caller computed before the term was wired at all.
    effective_range_band: str | None = None
    # This boss keeps its core as a separate object from its body, so a Pierce
    # holder's shot passes through the core and hits the body behind it - one
    # normal attack, two instances. Depends on `core_hittable`: there is nothing
    # to pierce through without a hittable core, and raid_simulator reads the two
    # together rather than trusting the caller not to send the contradiction.
    pierce_hits_body_behind_core: bool = False


# Real decks come in exactly these B1/B2/B3 shapes (Fienn, 2026-07-17);
# "at least one of each tier" also admits shapes that never occur in play.
ALLOWED_SHAPES = ((1, 1, 3), (1, 2, 2), (2, 1, 2))

# How many orderings either search will simulate before it cuts the pool
# instead. Shared by search_best_decks (a free deck) and best_completions (a
# drafted one) - the same simulator at the same ~100 ms answers both, so the
# point where enumeration stops being affordable is the same too. Exported so
# callers can ask the question the search will ask.
SEARCH_SIM_BUDGET = 1200


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
                    if _no_character_clash(deck) and _tier1_seating_valid(deck):
                        yield deck


def _shape_completions(required, candidates):
    """Yield 5-unit decks (canonical tier order) that contain every unit in
    `required`, filling the rest from `candidates`, for every ALLOWED_SHAPES
    compatible with required's per-tier counts. Pure combinatorics on burst_tier."""
    req_counts = Counter(u.burst_tier for u in required)
    if any(t not in (1, 2, 3) for t in req_counts):
        return
    cand_by_tier = {1: [], 2: [], 3: []}
    for u in candidates:
        if u.burst_tier in cand_by_tier:
            cand_by_tier[u.burst_tier].append(u)
    for n1, n2, n3 in ALLOWED_SHAPES:
        need = {1: n1 - req_counts.get(1, 0),
                2: n2 - req_counts.get(2, 0),
                3: n3 - req_counts.get(3, 0)}
        if any(v < 0 for v in need.values()):
            continue  # required already exceeds this shape's tier slot
        for f1 in combinations(cand_by_tier[1], need[1]):
            for f2 in combinations(cand_by_tier[2], need[2]):
                for f3 in combinations(cand_by_tier[3], need[3]):
                    deck = list(required) + list(f1) + list(f2) + list(f3)
                    # canonical tier order for _no_character_clash / seating checks
                    deck.sort(key=lambda u: u.burst_tier)
                    if _no_character_clash(deck) and _tier1_seating_valid(deck):
                        yield deck


def best_completions(required, candidates, boss: BossProfile, top_n=1, pool=None,
                     sim_budget=SEARCH_SIM_BUDGET, cascade=None):
    """Best `top_n` 5-unit decks that contain every unit in `required`, over
    every ALLOWED_SHAPES-compatible completion drawn from `candidates`.
    Returns [] when required's tier counts fit no shape or no valid
    completion exists.

    Budget-aware for the same reason search_best_decks is, and more urgently:
    the fewer seats a draft fills, the MORE completions there are. One drafted
    seat on a 77-unit roster leaves 1.8M orderings - hours of simulation for a
    single deck, on the path a player reaches by dropping one chip - while a
    complete 5-seat draft leaves 4.

    Over the budget the search is cut, `cascade` first (duck-typed, see
    app.cascade.Cascade) and prune_candidate_pool's picks if it declines - the
    same two-step search_best_decks takes. Which one runs matters here more
    than it does for a free deck: the fewer seats a draft fills, the more of
    the answer comes out of the cut pool, so on a one-seat draft prune's
    marginal-contribution cut alone measured 14.6% below the ranked shortlist.
    """
    orderings = _bounded_orderings(_shape_completions(required, candidates), sim_budget)
    if orderings is None:
        combos = (cascade.shortlist_completions(required, candidates, boss, pool)
                  if cascade is not None else None)
        if combos is None:
            cut = prune_candidate_pool(candidates, boss, pool)
            combos = _shape_completions(required, cut)
        orderings = _all_intra_tier_orderings(combos)
        if not orderings:
            # The cut pool cannot complete this draft even though the full one
            # can (every candidate left at some tier is a sibling build
            # of a drafted unit, say). Reporting the draft infeasible would be
            # wrong, so pay the exhaustive search rather than refuse a deck the
            # player can actually field.
            orderings = _all_intra_tier_orderings(_shape_completions(required, candidates))
    if not orderings:
        return []
    totals = _score_batch(orderings, boss, pool)
    ranked = sorted(zip(totals, orderings), key=lambda pair: pair[0], reverse=True)
    return [_summarize(ordered, evaluate_deck(ordered, boss)) for _, ordered in ranked[:top_n]]


def feasible_orderings(roster):
    for combo in combinations(roster, 5):
        by_tier = {1: [], 2: [], 3: []}
        infeasible = False
        for unit in combo:
            if unit.burst_tier not in by_tier:
                infeasible = True
                break
            by_tier[unit.burst_tier].append(unit)
        if (infeasible or not all(by_tier[t] for t in (1, 2, 3))
                or not _no_character_clash(combo) or not _tier1_seating_valid(combo)):
            continue
        for order1 in permutations(by_tier[1]):
            for order2 in permutations(by_tier[2]):
                for order3 in permutations(by_tier[3]):
                    ordered = list(order1) + list(order2) + list(order3)
                    if _buffer_seat_valid(ordered):
                        yield ordered


def evaluate_deck(ordered_deck, boss: BossProfile, max_bursts=None):
    """`max_bursts` ({slug: N}) caps how many times a seat spends its burst, for
    scoring a run the player actually played rather than one the scheduler would
    choose: 0 is a totem seated for its passives alone, 1 an opening burst then
    held. It is a decision made in the run, not a unit property, so it never
    comes from the registry - only a caller with a real record supplies it."""
    inputs = assemble_simulation_inputs(ordered_deck)
    if max_bursts:
        for member in inputs["deck"]:
            if member["slug"] in max_bursts:
                member["max_bursts"] = max_bursts[member["slug"]]
    return simulate_raid(
        **inputs,
        enemy_def=boss.enemy_def,
        gauge_charge_time=boss.gauge_charge_time,
        fight_duration=boss.fight_duration,
        mode=boss.mode,
        core_hittable=boss.core_hittable,
        boss_element=boss.element,
        part_destructible=boss.part_destructible,
        effective_range_band=boss.effective_range_band,
        pierce_hits_body_behind_core=boss.pierce_hits_body_behind_core,
    )


def _score_batch(decks, boss, pool):
    """Total damage for each deck. `pool` (a SimPool, duck-typed - this module
    must not import sim_pool, which imports evaluate_deck from here) fans the
    batch out to worker processes; None runs inline."""
    if pool is None:
        return [evaluate_deck(deck, boss)["total_damage"] for deck in decks]
    return pool.score_many(decks)


def _summarize(ordered_deck, result):
    # The simulator logs eight damage sources; a player thinks in three. Burst
    # skills and normal attacks keep their own line, and everything else - the
    # DoTs, the per-shot riders, the self-cooldowned procs - is "skill damage".
    # The three must add up to the total: a breakdown that leaves most of a
    # deck's damage unnamed reads as a broken number, not an incomplete one.
    by_source = defaultdict(float)
    for e in result["damage_log"]:
        by_source[e["source"]] += e["damage"]
    burst = by_source.pop("burst", 0.0)
    normal = by_source.pop("normal_attack", 0.0)
    return {
        "deck": [spec.slug for spec in ordered_deck],
        "total_damage": result["total_damage"],
        "burst_damage": burst,
        "normal_attack_damage": normal,
        "skill_damage": sum(by_source.values()),
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
                ordered = list(o1) + list(o2) + list(o3)
                if _buffer_seat_valid(ordered):
                    yield ordered


def deck_is_valid(units):
    """Whether these exact 5 units can ever be fielded as a legal deck.

    `shape_combinations`/`_shape_completions` never need this: they only ever
    GENERATE decks by construction, so every deck they produce already passes
    every rule below. A caller HANDED a fixed 5-unit deck instead of building
    one has to ask the same question explicitly, or it will call a deck legal
    that the search would never have produced - the two paths would then
    disagree about what is playable."""
    if len(units) != 5:
        return False
    tier_counts = Counter(u.burst_tier for u in units)
    shape = tuple(tier_counts.get(t, 0) for t in (1, 2, 3))
    return (shape in ALLOWED_SHAPES
            and _no_character_clash(units)
            and _tier1_seating_valid(units)
            and next(_intra_tier_orderings(units), None) is not None)


# Curated two-unit sets that only work together (Fienn, 2026-07-17): candidate
# cuts must measure them as a pair and never separate them. Keyed by slug, so a
# member that ever gains a Favorite Item encoding needs its `-signature` build
# added here too - the pair is matched literally, and a set that silently stops
# matching is the failure mode that killed the weapon-theme anchor this replaced
# the last of (see docs/decisions.md, 2026-08-02).
SYNERGY_SETS = (frozenset({"mint", "prika"}),
                frozenset({"mast-romantic-maid", "anchor-innocent-maid"}))

# Per-tier pool caps sized so shape_combinations stays a few hundred combos
# (~103 ms/sim budget); synergy/theme guards may exceed them slightly.
PRUNED_TIER_CAPS = {1: 2, 2: 3, 3: 6}


def _prior(unit):
    # Round-0 prior (no sims): investment-adjusted ATK x weapon hit percent.
    # Only seeds the reference decks - the swap-in measurement corrects it.
    return unit.base_stats["atk"] * unit.weapon_stats["damage_percent"]


def _reference_deck(by_tier, b1):
    # _character_safe_top only guards against two B3 picks clashing with EACH
    # OTHER - it doesn't know `b1` occupies a slot too, so a B1 whose
    # sibling build lives at tier 3 (VARIANT_BURST_TIERS, e.g. Rapi:
    # Red Hood's Combat Assist stand-in vs. her Burst-3 self) needs that
    # sibling filtered out of the B3 pool up front, or it could rank into the
    # B3 picks and seat both builds in the same reference deck - the exact
    # clash _no_character_clash forbids for real candidate decks.
    b1_character = _CHARACTER_OF.get(b1.slug, b1.slug)
    b3_pool = [u for u in by_tier[3] if _CHARACTER_OF.get(u.slug, u.slug) != b1_character]
    if len(b3_pool) < 3:
        # No legal way to fill all 3 B3 slots without b1's own sibling (e.g.
        # exactly 3 total B3 units and one of them IS the sibling) - a
        # degenerate roster, so accept the clash rather than short the
        # reference deck below 5 units (breaking _TIER_SLOT's fixed slot-4
        # assumption downstream).
        b3_pool = by_tier[3]
    b3_picks = _character_safe_top(b3_pool, 3)
    if len(b3_picks) < 3:
        # _character_safe_top's SAME-TIER dedup (two builds of one character both
        # surviving the cross-tier filter above, e.g. Cinderella: Crystal
        # Wave's MG/Snipe modes) can independently short the picks below 3
        # even though b3_pool itself has 3+ units - top back up from
        # b3_pool, accepting the clash, for the same reason the fallback
        # above does: never short the reference deck below 5 units.
        picked = {u.slug for u in b3_picks}
        for unit in b3_pool:
            if unit.slug not in picked:
                b3_picks.append(unit)
                picked.add(unit.slug)
                if len(b3_picks) == 3:
                    break
    reference = [b1, by_tier[2][0], *b3_picks]
    if len(reference) != 5 or [u.burst_tier for u in reference] != [1, 2, 3, 3, 3]:
        # Loud failure, not a silent short reference: every caller downstream
        # (_TIER_SLOT, _swap_slot, prune_candidate_pool's baseline) assumes
        # this exact 5-unit [1,2,3,3,3] shape.
        raise AssertionError(
            "_reference_deck postcondition violated: expected 5 units in "
            f"tier layout [1, 2, 3, 3, 3], got "
            f"{[u.burst_tier for u in reference]} ({len(reference)} units)"
        )
    return reference


def _character_safe_top(units, n):
    """First `n` from a prior-ranked list, skipping any unit whose character is
    already taken - _reference_deck's B3 picks otherwise slice the top 3
    blindly, which could seat two builds of one character (e.g. both
    Cinderella: Crystal Wave modes) in one "deck," the exact clash
    _no_character_clash forbids for real candidate decks."""
    chosen, characters_seen = [], set()
    for unit in units:
        character = _CHARACTER_OF.get(unit.slug, unit.slug)
        if character in characters_seen:
            continue
        characters_seen.add(character)
        chosen.append(unit)
        if len(chosen) == n:
            break
    return chosen


_TIER_SLOT = {1: 0, 2: 1, 3: 4}


def _swap_slot(reference, unit):
    """Index in `reference` that swapping `unit` in should overwrite, or None if
    no single-slot swap can seat `unit` without also seating a sibling build.

    Normally the unit's tier default (B3 replaces the reference's weakest B3,
    the last one). But if a sibling build of `unit` already sits in a different
    reference slot (e.g. the reference's first, non-last B3
    slot), swap over the sibling instead of the tier default - otherwise the
    default slot leaves the sibling seated too, measuring a deck with both
    builds present at once, the exact clash _no_character_clash forbids for
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
    instead would leave that sibling seated too, still a clash between two
    builds of one character. Neither is safe, so the swap is refused."""
    character = _CHARACTER_OF.get(unit.slug)
    if character is not None:
        same_tier_slot, cross_tier_sibling = None, False
        for i, seated in enumerate(reference):
            if _CHARACTER_OF.get(seated.slug) == character:
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
    """When `unit`'s sibling build sits in `reference` at a
    DIFFERENT burst tier than `unit`'s own (VARIANT_BURST_TIERS), _swap_slot
    refuses the swap - see its docstring for why neither available slot is
    safe. Refusing isn't the end of the story: `unit` can still get a real
    marginal score by measuring it against a second, equally legal reference
    where the sibling is swapped out for the best other unit of the
    sibling's own tier, with `unit` then seated at its own tier-default slot
    in THAT deck. The result keeps the (1,2,3x3) shape; the alternative is
    also picked to keep `alt_reference` itself clash-free (never seated
    elsewhere in `reference`, never a sibling build of `unit`, and never
    a sibling build of any OTHER unit still seated in `reference` - the
    alternative's own sibling build could otherwise already occupy
    an unrelated slot).

    Returns `(alt_reference, deck)`. The caller must diff `deck` against a
    freshly-evaluated baseline of `alt_reference`, NOT the original
    `reference`'s baseline - that baseline still has the sibling seated, so
    it isn't a fair basis for a deck that swapped the sibling out too.

    Returns None if the sibling's tier has no LEGAL alternative at all
    (either it's the only unit `by_tier[sibling.burst_tier]` has, or every
    other candidate there would clash with something else still seated in
    `reference`) - every legal reference must then seat the sibling, so
    `unit` genuinely cannot be measured against this reference family.
    Callers must not treat that None as a real 0.0 score; see
    prune_candidate_pool and _measure_against."""
    character = _CHARACTER_OF.get(unit.slug)
    if character is None:
        return None
    sibling, sibling_slot = None, None
    for i, seated in enumerate(reference):
        if _CHARACTER_OF.get(seated.slug) == character and seated.burst_tier != unit.burst_tier:
            sibling, sibling_slot = seated, i
            break
    if sibling is None:
        return None
    seated_slugs = {u.slug for u in reference}
    alt_reference = None
    for candidate in by_tier[sibling.burst_tier]:
        if candidate.slug in seated_slugs or _CHARACTER_OF.get(candidate.slug, candidate.slug) == character:
            continue
        trial = list(reference)
        trial[sibling_slot] = candidate
        # _no_character_clash catches a candidate whose own sibling build
        # already sits elsewhere in `reference` under an unrelated character -
        # the same clash rule real candidate decks are held to, reused here
        # instead of duplicating it.
        if _no_character_clash(trial):
            alt_reference = trial
            break
    if alt_reference is None:
        return None
    deck = list(alt_reference)
    deck[_TIER_SLOT[unit.burst_tier]] = unit
    return alt_reference, deck


def _measure_against(reference, unit, boss, baseline, by_tier):
    # Swap the candidate into its tier slot and score the marginal change
    # over the reference's baseline. A unit already in the reference leaves
    # the deck unchanged, so its marginal contribution is 0.0 with no
    # re-simulation. A unit with no safe single-slot swap (_swap_slot
    # returns None for a cross-tier sibling build) is measured
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


def _shell_damage(shell_b1, two_b2s, shell_b3, boss):
    """The (1,2,2) shell's damage with `two_b2s` in its Burst-2 seats, best of
    both seatings - burst_cycle fires the LEFTMOST eligible same-tier unit, and
    order-dependent synergies exist (Prika must burst before Mint for her Encore
    to ever fire). Both the pair and the baseline it is measured against go
    through this, so neither is judged in a seating the other was spared.

    The shell shape assumes a two-Burst-2 pair; a future cross-tier SYNERGY_SETS
    entry would need a different one.
    """
    return max(evaluate_deck([shell_b1, *ordering, *shell_b3], boss)["total_damage"]
               for ordering in (list(two_b2s), list(two_b2s)[::-1]))


def prune_candidate_pool(roster, boss: BossProfile, pool=None):
    """Cut the roster to a pool the budget can enumerate. Scores are marginal
    contributions in reference-deck context (two passes: prior-seeded B1, then
    best-measured B1 - CDR holders change cycle count, Fienn rule 2/3), with
    synergy sets measured as pairs rather than trusting the mis-contextual cut.
    A candidate
    whose sibling build holds a cross-tier reference slot still gets
    a genuine simulated score, against an alternate reference with that
    sibling swapped out (_cross_tier_reference) - it is never scored an
    unmeasured 0.0 purely because the primary reference couldn't seat it.
    That score is a real simulation, not a fabricated one, but it is measured
    against a DIFFERENT reference deck than its same-pass peers - the deltas
    still all feed the same PRUNED_TIER_CAPS sort below, so a cross-tier
    candidate's ranking isn't produced under identical conditions to a
    same-slot swap-in's. On degenerate rosters with fewer than 3 distinct
    distinct characters at tier 3, the reference deck itself may seat two
    builds of one character."""
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
            # no safe single-slot swap exists (cross-tier sibling build
            # elsewhere in the reference, _swap_slot) - measure
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

    # Synergy sets: both members share what the pair is worth OVER the two
    # Burst 2s the shell would otherwise hold. It must be that delta and not the
    # shell's total, because every other entry in `scores` is a marginal
    # contribution: a total is a different quantity an order of magnitude
    # larger, so a pair carrying one wins `max()` on scale alone and holds the
    # tier cap whatever the pair is actually worth. The delta is measured in a
    # (1,2,2) shell while the rest of `scores` is measured against the
    # (1,2,3,3,3) reference deck, which makes the two the same KIND of number
    # without being strictly comparable - the same caveat _cross_tier_reference
    # carries for its own alternate baseline.
    shell_b1, shell_b3 = by_tier[1][0], by_tier[3][:2]
    slugs = {u.slug: u for u in roster}
    for pair in SYNERGY_SETS:
        if pair <= slugs.keys():
            members = [slugs[s] for s in sorted(pair)]
            # The two best Burst 2s the pair displaces. Fewer than two means the
            # tier is too small to build the comparison - and too small for the
            # cap to cut much either - so the pair keeps its individual scores
            # rather than being credited against a baseline that doesn't exist.
            others = [u for u in by_tier[2] if u.slug not in pair][:2]
            if len(others) < 2:
                continue
            pair_score = (_shell_damage(shell_b1, members, shell_b3, boss)
                          - _shell_damage(shell_b1, others, shell_b3, boss))
            for member in members:
                scores[member.slug] = max(scores[member.slug], pair_score)

    pool = []
    for tier, cap in PRUNED_TIER_CAPS.items():
        ranked = sorted(by_tier[tier], key=lambda u: scores[u.slug], reverse=True)
        if tier == 1:
            # A SOLE_TIER1_SLUGS member can't co-seat with any other B1
            # (_tier1_seating_valid). If she fills one of only `cap` tier-1
            # slots, the pool's only tier-1 pair is illegal and
            # shape_combinations can never produce a (2,1,2) deck - widen
            # the cap by one per such slug so a real B1 pair also survives
            # the cut alongside her. This single pass assumes at most one such
            # slug reaches the ranking; a second member would require fixpoint
            # widening to avoid reintroducing the degenerate case.
            cap += sum(1 for u in ranked[:cap] if u.slug in SOLE_TIER1_SLUGS)
        pool.extend(ranked[:cap])

    pool_slugs = {u.slug for u in pool}
    for pair in SYNERGY_SETS:  # companion pull-in
        if pair & pool_slugs and pair <= slugs.keys():
            pool.extend(slugs[s] for s in pair if s not in pool_slugs)
            pool_slugs |= pair
    return pool


def _reference_b1_variants(by_tier, boss):
    # Pass 1: prior-seeded B1. Pass 2: the B1 whose swap-in measured best
    # (usually the CDR holder - shorter cycles change everyone's value).
    # _measure_against may score a cross-tier sibling-build candidate against
    # an alternate reference's baseline instead of this one's (see its
    # docstring) - the delta is still a legitimate marginal contribution
    # either way, so max() over the deltas is a fair comparison even though
    # the baselines themselves can differ.
    first = by_tier[1][0]
    yield first
    reference = _reference_deck(by_tier, first)
    baseline = evaluate_deck(reference, boss)["total_damage"]
    best_b1 = max(by_tier[1],
                  key=lambda u: _measure_against(reference, u, boss, baseline, by_tier))
    if best_b1.slug != first.slug:
        yield best_b1


def _all_intra_tier_orderings(combos):
    return [ordered for combo in combos for ordered in _intra_tier_orderings(combo)]


def _bounded_orderings(combos, sim_budget):
    """Every intra-tier ordering of `combos`, or None once they exceed the budget.

    Only the ANSWER to "does this fit the budget" is needed when it doesn't, so
    the walk stops at the first ordering past it. Enumerating the full space to
    then discard it costs real time on a large roster - a 78-unit roster has
    millions of orderings, and the parent-side generation showed up as ~23% of a
    profiled allocation.
    """
    out = []
    for combo in combos:
        for ordered in _intra_tier_orderings(combo):
            out.append(ordered)
            if len(out) > sim_budget:
                return None
    return out


def _orderings_within_budget(roster, sim_budget):
    """_bounded_orderings over every deck `roster` can form (no draft to honor)."""
    return _bounded_orderings(shape_combinations(roster), sim_budget)


def completions_fit_budget(required, candidates, sim_budget=SEARCH_SIM_BUDGET):
    """Whether best_completions can enumerate this draft's completions outright.

    Exported so a caller can decide UP FRONT whether to pay for something only
    the over-budget path needs (allocate_decks fits a surrogate). Asking is
    nearly free: the walk stops at the first ordering past the budget.
    """
    return _bounded_orderings(_shape_completions(required, candidates),
                              sim_budget) is not None


def search_best_decks(roster, boss: BossProfile, top_n=5,
                      sim_budget=SEARCH_SIM_BUDGET, pool=None, cascade=None):
    """Budget-aware replacement for exhaustive find_best_decks: every shape
    combination is scored in EVERY intra-tier order, and when that would blow
    the budget the roster is first cut to a candidate pool
    (prune_candidate_pool). `pool` (a SimPool or None) fans the map-shaped
    batches out to worker processes.

    Intra-tier order is not a tie-break between equivalent decks - it decides
    which member of a tier never bursts at all, because burst_cycle picks the
    first ready member of each tier (see `simulate_burst_cycle`). That is a
    real strategy, not an artifact: a (1,1,3) commonly runs its rightmost
    Burst 3 as a buffer/normal-attack unit that never bursts, Prika must
    burst before Mint for her Encore to hand Mint the slot, and Velvet and
    Helm: Aquamarine are usually played without bursting at all (Fienn,
    2026-07-19). Ranking combinations on ONE arbitrary order therefore
    mis-scores them outright - measured at up to 78% low on real data, with
    the true best (1,1,3) ranking #21 - so orderings are scored in full
    rather than refined for a top-K shortlist.

    `cascade` (duck-typed, see app.cascade.Cascade) is consulted when the
    budget is blown: its shortlist replaces the exhaustive scoring of the
    pruned pool. It may decline by returning None, in which case the pruned
    exhaustive path runs unchanged. This module never imports the cascade -
    surrogate.py already imports this one.
    """
    candidates = list(roster)
    orderings = _orderings_within_budget(candidates, sim_budget)
    if orderings is None:
        combos = cascade.shortlist(roster, boss, pool) if cascade is not None else None
        if combos is None:
            combos = shape_combinations(prune_candidate_pool(roster, boss, pool))
        orderings = _all_intra_tier_orderings(combos)
    # Ranked on slim scores first; only the returned top_n get a second sim to
    # attach the full "result" (evaluate_deck is pure, so the floats are
    # identical to scoring the full summaries directly).
    totals = _score_batch(orderings, boss, pool)
    ranked = sorted(zip(totals, orderings), key=lambda pair: pair[0], reverse=True)
    return [_summarize(ordered, evaluate_deck(ordered, boss)) for _, ordered in ranked[:top_n]]
