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

from app.elements import weakness_of
from app.raid_simulator import simulate_raid
from app.roster import assemble_simulation_inputs
from app.skill_rules.registry import (SEATED_BUFF_SLUGS, TASTE_INDUCER_SLUGS,
                                      character_map, deck_grants_ally_round_buffs,
                                      get_burst_delay, get_hold_fire_release_shots,
                                      has_burst_delay, is_tap_fire_candidate)

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


def _taste_induced_valid(units):
    """Whether every state-gated variant here has a deck-mate that induces its
    state (registry's TASTE_INDUCER_SLUGS).

    Bready's two builds are the only ones: she enters a Taste by RECEIVING a
    buff of the matching damage kind, and almost her whole kit is gated on being
    in one. Seating her beside no such buffer scores a unit the game does not
    produce - so this refuses the deck rather than letting the search bank
    damage she cannot deal. She has no Taste-less build to fall back to, and
    measurement says she should not: stripped of the gated bullets she loses to
    27 of the 32 Burst-3s her bench offered (Fienn's deck 5, 2026-08-04)."""
    slugs = {u.slug for u in units}
    return all(slugs & inducers
               for variant, inducers in TASTE_INDUCER_SLUGS.items()
               if variant in slugs)


def _skips_opening_cycle(unit):
    if not has_burst_delay(unit.slug):
        return False
    delay = get_burst_delay(unit.slug, unit.skill_values) or {}
    return delay.get("skip_cycles", 0) > 0


def _seat_order_is_playable(ordered_units):
    """Whether this seat order produces, on its own, the schedule its units'
    burst delays imply.

    The scheduler fires the leftmost READY member of a tier and the game does
    the same - but a `skip_cycles` delay makes a unit unready for the opening
    cycles, and a SEAT cannot say that. So an ordering that puts such a unit
    first in her tier scores exactly what the playable one scores while
    contradicting itself on screen: fielded as shown, the game bursts her in
    cycle 1 and she never reaches the state the delay exists to model (Diesel:
    Winter Sweets' Highlight, Fienn 2026-08-04). Behind a tier-mate, the game's
    own rule produces the held schedule with nothing asked of the player."""
    for tier in (1, 2, 3):
        members = [u for u in ordered_units if u.burst_tier == tier]
        if len(members) > 1 and _skips_opening_cycle(members[0]):
            return False
    return True


def tap_fire_slugs(ordered_deck):
    """이 덱에서 톡톡이로 계산된 좌석 - `registry.TAP_FIRE_CANDIDATES` 멤버 전원.

    후보라는 것 자체가 「이 유닛은 손으로 톡톡 눌러 쏜다」는 뜻이다. 자기 차속이 차지를
    0으로 미는 구간에서도 손은 똑같이 톡톡이이고, 다만 그때는 눌러도 풀차지라 배율을
    하나도 안 버린다 - `partial_charge_slugs`가 그 구분을 답한다."""
    return [spec.slug for spec in ordered_deck if is_tap_fire_candidate(spec.slug)]


def hold_burst_slugs(ordered_deck):
    """Seats the PLAYER has to hold back by hand for this order to be the one
    that was scored - empty for the vast majority.

    `best_ordering_summary` prefers a playable order whenever the scores tie, so
    this only fills when the leading order genuinely scored higher with the
    skipper in front. Then the seat alone no longer produces her held schedule
    and nothing else between here and the screen knows it: the deck is right,
    but fielding it as drawn hands her the state she was scored as NOT having."""
    return [members[0].slug
            for tier in (1, 2, 3)
            for members in [[u for u in ordered_deck if u.burst_tier == tier]]
            if len(members) > 1 and _skips_opening_cycle(members[0])]


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
    # 게이지 채움 시간의 **시드** - 고정점이 아직 그 사이클의 값을 못 낸 동안
    # 사이클이 못 내려가는 하한이다: 풀 버스트(10초) + 이 값 + 티어 갭.
    #
    # Measured (Fienn, 2026-08-05): a deck carrying a 7.48-sec CDR unit, driven
    # as fast as the gauge can be controlled, opens its 15th Full Burst at
    # t~179. While the gauge binds, cycle spacing is independent of cooldown
    # reduction, so that single instant fixes the value:
    #     15th start = (g + 0.2) + 14 * (10.2 + g) = 143.0 + 15g = 179 -> g = 2.4
    # test_default_gauge_reproduces_the_measured_fifteenth_full_burst holds that
    # arithmetic, so changing this number fails there before anything else.
    #
    # The gauge binds MORE as a deck's cooldown reduction grows, not less -
    # cooldowns clear sooner and the gauge is all that is left. So the decks this
    # value decides are exactly the CDR-heavy ones: scoring one deck either side
    # of it moves a CDR-heavy composition 16.3% and a composition without CDR
    # 0.4%, which is also why a too-low value quietly promotes CDR-stacked decks
    # in the search.
    #
    # 이제 이 값은 **첫 패스의 시드**다. 게이지는 덱이 넣은 타격 수로 차므로
    # 사이클마다 다른 덱의 양이고, `simulate_raid`가 고정점까지 반복하며
    # `burst_gauge.fill_times`가 계산한 사이클별 값으로 이것을 대체한다. 표에
    # 없는 사이클(개전 -> 첫 버스트)만 이 값이 그대로 답한다.
    gauge_charge_time: float = 2.4
    mode: str = "manual"
    part_destructible: bool = False
    # 이 인카운터에서 파츠가 실제로 깨지는 시각들(초). 공지에는 없고 그 보스를
    # 관측해서 나오는 값이라 `core_diameter_px`와 같은 계열이다 - 비어 있으면
    # (기본값) 파괴에 반응하는 스킬은 `part_destructible` 불리언만 보던 근사
    # 그대로 돈다. 전투 길이를 넘는 시각은 그 전투에서 일어나지 않는다.
    part_destruction_times: tuple[float, ...] = ()
    # 잡몹이 주기적으로 생성되는 보스. 이 사실 하나가 홀드 파이어 택틱을 통째로
    # 지운다 - 나오는 잡몹을 치워야 하므로 자기 풀 버스트 동안 평타를 멈출 수
    # 없다(Fienn, 2026-08-20, 솔로 40시즌 「사치스러운 거미」). 그래서
    # `evaluate_deck_hold_fire_options`가 후보를 아예 안 낸다: 시뮬을 돌려 봐야
    # 플레이어가 못 두는 수다.
    #
    # 딜 계산 자체에는 안 들어간다 - 잡몹이 얼마나 딜을 가져가는지, 치우는 데
    # 몇 발이 드는지는 모델하지 않는다. 이 플래그가 답하는 것은 「그 택틱을 둘 수
    # 있는가」 하나뿐이다.
    spawns_adds: bool = False
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
    # 코어의 지름(px). None이면 이 인카운터는 코어히트율을 모델링하지 않고
    # 적격 평타가 전부 코어에 든다고 본다 - 엔진이 오래 모델해 온 상한이다.
    # 값을 주면 무기 탄착군과의 면적비가 그 비율을 정한다(app/accuracy.py).
    # `core_hittable`이 거짓이면 무시된다: 코어가 없으면 크기를 물을 수 없다.
    core_diameter_px: float | None = None
    # The boss gates a gimmick on an elemental interrupt: breaking it needs at
    # least one Nikke holding elemental advantage, so a deck without one cannot
    # clear the phase however much damage it does. Unlike every other deck
    # legality rule in this module, this one depends on the BOSS - see
    # deck_breaks_gimmick.
    elemental_interrupt_required: bool = False


def weakness_holders(units, boss: BossProfile):
    """How many of `units` hold elemental advantage over this boss - 0 whenever
    the gimmick is off or the boss has no element, so callers need no second
    guard before budgeting them across decks."""
    if not boss.elemental_interrupt_required or boss.element is None:
        return 0
    weakness = weakness_of(boss.element)
    return sum(1 for u in units if u.element == weakness)


def deck_breaks_gimmick(units, boss: BossProfile):
    """Whether these units can break the boss's elemental-interrupt gimmick.

    Vacuously true when the boss has no gimmick, and ALSO when it has no element:
    an element-less boss has no weakness, so no deck could ever satisfy the
    requirement and enforcing it would make every roster infeasible rather than
    expressing anything real.
    """
    if not boss.elemental_interrupt_required or boss.element is None:
        return True
    weakness = weakness_of(boss.element)
    return any(u.element == weakness for u in units)


# Sentinel default for the `deck_filter` parameter on search_best_decks and
# best_completions, distinct from None. A caller passing None wants exactly
# that - no filter at all, the deliberate unconstrained fallback a drafted
# completion needs when no constrained completion exists - so None cannot
# also mean "derive one from the boss" or that caller has no way to ask for
# an unfiltered search.
_DERIVE_FILTER = object()


def _gimmick_filter(boss: BossProfile):
    """The boss's gimmick as a deck predicate, or None when there is none to
    apply. None (rather than a predicate that always returns True) is what lets
    every generator below skip the call entirely on the common path."""
    if not boss.elemental_interrupt_required or boss.element is None:
        return None
    return lambda units: deck_breaks_gimmick(units, boss)


def _ensure_weakness_in_pool(cut, roster, boss: BossProfile):
    """Guarantee the cut pool can still form a deck that breaks the gimmick.

    prune_candidate_pool ranks by marginal contribution and knows nothing about
    the boss, so its cut can hold no unit of the weakness element - and then the
    constrained search has nothing at all to return. Top the pool back up with
    the best weakness unit at each tier instead. This is the same move
    _reference_deck makes when its picks come up short: widen the pool rather
    than return nothing, and never fall back to an exhaustive walk over the full
    roster (millions of orderings on a real one).
    """
    if not boss.elemental_interrupt_required or boss.element is None:
        return cut
    weakness = weakness_of(boss.element)
    if any(u.element == weakness for u in cut):
        return cut
    in_cut = {u.slug for u in cut}
    added = []
    for tier in (1, 2, 3):
        pick = max((u for u in roster
                    if u.burst_tier == tier and u.element == weakness
                    and u.slug not in in_cut),
                   key=_prior, default=None)
        if pick is not None:
            added.append(pick)
    return list(cut) + added


# Real decks come in exactly these B1/B2/B3 shapes (Fienn, 2026-07-17);
# "at least one of each tier" also admits shapes that never occur in play.
ALLOWED_SHAPES = ((1, 1, 3), (1, 2, 2), (2, 1, 2))

# How many orderings either search will simulate before it cuts the pool
# instead. Shared by search_best_decks (a free deck) and best_completions (a
# drafted one) - the same simulator at the same ~100 ms answers both, so the
# point where enumeration stops being affordable is the same too. Exported so
# callers can ask the question the search will ask.
SEARCH_SIM_BUDGET = 1200


def shape_combinations(roster, deck_filter=None):
    """Canonical tier-ordered 5-unit combinations, restricted to the shapes
    real play uses. Pure combinatorics on `.burst_tier` (like
    feasible_orderings); intra-tier order is the input order.

    `deck_filter` is an optional extra legality predicate on the finished deck.
    It exists for a rule this module had none of until now: one that depends on
    the BOSS rather than only on the units (deck_breaks_gimmick). Filtering here
    rather than after the search is deliberate - a search that converges on decks
    the rule forbids and is corrected afterwards loses an unpredictable amount.
    """
    by_tier = {1: [], 2: [], 3: []}
    for unit in roster:
        if unit.burst_tier in by_tier:
            by_tier[unit.burst_tier].append(unit)
    for n1, n2, n3 in ALLOWED_SHAPES:
        for c1 in combinations(by_tier[1], n1):
            for c2 in combinations(by_tier[2], n2):
                for c3 in combinations(by_tier[3], n3):
                    deck = list(c1) + list(c2) + list(c3)
                    if (_no_character_clash(deck) and _tier1_seating_valid(deck)
                            and _taste_induced_valid(deck)
                            and (deck_filter is None or deck_filter(deck))):
                        yield deck


def _shape_completions(required, candidates, deck_filter=None):
    """Yield 5-unit decks (canonical tier order) that contain every unit in
    `required`, filling the rest from `candidates`, for every ALLOWED_SHAPES
    compatible with required's per-tier counts. Pure combinatorics on burst_tier.

    `deck_filter` is the same optional boss-dependent legality predicate
    shape_combinations takes - see its docstring for why filtering happens here.
    """
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
                    if (_no_character_clash(deck) and _tier1_seating_valid(deck)
                            and _taste_induced_valid(deck)
                            and (deck_filter is None or deck_filter(deck))):
                        yield deck


def best_completions(required, candidates, boss: BossProfile, top_n=1, pool=None,
                     sim_budget=SEARCH_SIM_BUDGET, cascade=None, deck_filter=_DERIVE_FILTER):
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

    `deck_filter` left at its default derives the boss's gimmick filter (or
    None, if the boss has none). Pass None explicitly to search with NO
    filter at all - the two are not the same thing: a caller with no legal
    constrained completion needs to ask for an actually unconstrained one.
    """
    if deck_filter is _DERIVE_FILTER:
        deck_filter = _gimmick_filter(boss)
    orderings = _bounded_orderings(_shape_completions(required, candidates, deck_filter),
                                   sim_budget)
    if orderings is None:
        combos = (cascade.shortlist_completions(required, candidates, boss, pool)
                  if cascade is not None else None)
        if combos is not None and deck_filter is not None:
            combos = [c for c in combos if deck_filter(c)] or None
        if combos is None:
            cut = prune_candidate_pool(candidates, boss, pool)
            combos = _shape_completions(required,
                                        _ensure_weakness_in_pool(cut, candidates, boss),
                                        deck_filter)
        orderings = _all_intra_tier_orderings(combos)
        if not orderings:
            # The cut pool cannot complete this draft even though the full one
            # can (every candidate left at some tier is a sibling build
            # of a drafted unit, say). Reporting the draft infeasible would be
            # wrong, so pay the exhaustive search rather than refuse a deck the
            # player can actually field.
            orderings = _all_intra_tier_orderings(
                _shape_completions(required, candidates, deck_filter))
    if not orderings:
        return []
    totals = _score_batch(orderings, boss, pool)
    ranked = sorted(zip(totals, orderings), key=lambda pair: pair[0], reverse=True)
    return _report(ranked, boss, top_n)


def feasible_orderings(roster, deck_filter=None):
    for combo in combinations(roster, 5):
        by_tier = {1: [], 2: [], 3: []}
        infeasible = False
        for unit in combo:
            if unit.burst_tier not in by_tier:
                infeasible = True
                break
            by_tier[unit.burst_tier].append(unit)
        if (infeasible or not all(by_tier[t] for t in (1, 2, 3))
                or not _no_character_clash(combo) or not _tier1_seating_valid(combo)
                or not _taste_induced_valid(combo)
                or (deck_filter is not None and not deck_filter(combo))):
            continue
        for order1 in permutations(by_tier[1]):
            for order2 in permutations(by_tier[2]):
                for order3 in permutations(by_tier[3]):
                    ordered = list(order1) + list(order2) + list(order3)
                    if _buffer_seat_valid(ordered):
                        yield ordered


def evaluate_deck(ordered_deck, boss: BossProfile, max_bursts=None,
                  collect_target_grants=False, adjacency=None, hold_fire=()):
    """`max_bursts` ({slug: N}) caps how many times a seat spends its burst, for
    scoring a run the player actually played rather than one the scheduler would
    choose: 0 is a totem seated for its passives alone, 1 an opening burst then
    held. It is a decision made in the run, not a unit property, so it never
    comes from the registry - only a caller with a real record supplies it.

    `collect_target_grants`는 top-N 대상형 버프가 누구에게 갔는지를 결과에
    싣는다 - 미란다 계산기(app/miranda_targets.py)가 읽는 기록이고, 기본 off라
    탐색 경로는 오늘 그대로다.

    `adjacency` ({slug: [양 옆 아군 둘]})는 "자신과 양 옆 아군 2명" 불릿이 누구에게
    가는지를 못박는다. 안 주면 `SquadContext.neighbor_slugs`의 정책(최고 ATK 둘)이
    답하므로 탐색 경로의 비용은 오늘 그대로고, 최적 좌석이 필요한 쪽은
    `evaluate_deck_best_seating`을 부른다.

    `hold_fire` (슬러그 집합)는 그 유닛이 **자기 버스트로 연 풀 버스트 동안 평타를
    의도적으로 안 쐈다**는 것이다 - 탄으로 소모되는 「N발 유지」 버프를 창 내내
    살려 스킬딜을 전부 그 아래에 놓는 실전 택틱이다(Fienn, 2026-08-18).
    `max_bursts`와 같은 범주다: **런에서 내린 결정이지 유닛 속성이 아니므로**
    레지스트리에서 오지 않는다. 라운드 버프를 남에게 주는 유닛이 덱에 없으면
    홀드는 순손해라(미하라 −31.66%·아인 −27.39% 실측) 부를 이유도 없다 -
    `evaluate_deck_hold_fire_options`가 그 게이트를 답한다."""
    inputs = assemble_simulation_inputs(ordered_deck, hold_fire=hold_fire)
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
        part_destruction_times=boss.part_destruction_times,
        effective_range_band=boss.effective_range_band,
        pierce_hits_body_behind_core=boss.pierce_hits_body_behind_core,
        core_diameter_px=boss.core_diameter_px,
        collect_target_grants=collect_target_grants,
        adjacency=adjacency,
    )


def evaluate_deck_hold_fire_options(ordered_deck, boss):
    """The `hold_fire` sets worth SCORING for this deck, cheapest first.

    Always includes the empty set (nobody holds - today's answer). The
    alternatives only appear when the ENCOUNTER allows the tactic at all AND
    the deck actually holds a unit it is played on AND somebody in it hands out
    a "for N round(s)" buff: holding fire removes shots and adds nothing on its
    own, so with no such buff to preserve the alternative is a guaranteed loss
    and is not worth a simulation.

    The encounter gate is `BossProfile.spawns_adds`: against a boss that keeps
    producing adds the player cannot stop firing, so the tactic is not on the
    board however good the deck's buffs are. `boss` is required rather than
    optional for the reason `effective_range_band` was silently dropped by
    three endpoints - an input a caller can forget is an input that eventually
    goes missing.

    Subsets rather than one all-on set, because holding is not jointly good: in
    a deck with three Burst 3s, Ada holding while Ein also holds cost the deck
    3 percentage points against Ein holding alone, since she barely bursts and
    threw her normal attacks away for a window she rarely opened."""
    if boss.spawns_adds:
        return [frozenset()]
    slugs = [unit.slug for unit in ordered_deck]
    holders = [slug for slug in slugs if get_hold_fire_release_shots(slug) is not None]
    if not holders:
        return [frozenset()]
    inputs = assemble_simulation_inputs(ordered_deck)
    if not deck_grants_ally_round_buffs(inputs["rules_by_slug"]):
        return [frozenset()]
    return [frozenset(subset)
            for size in range(len(holders) + 1)
            for subset in combinations(holders, size)]


def seat_arrangements(ordered_deck):
    """Every adjacency map this deck's five seats can produce, deduplicated.

    Enumerating SEATS rather than neighbor pairs is what keeps the answer
    honest once a deck can hold two seated-buff units: a line of five seats
    constrains them jointly, so picking each one's best pair independently
    would score a formation the game cannot make. Two units are already
    possible (Rouge is Burst 1, Flora's Favorite Item Burst 2), so this is not
    a hypothetical.

    A unit's allowed seats come from SEATED_BUFF_SLUGS - Rouge's bullet needs
    the back row, Flora's does not. Arrangements collapse to the adjacency they
    induce, since the seats of everyone else are invisible to the simulation:
    that is what turns 5! = 120 orders into 6 distinct maps for a Rouge deck,
    10 for a Flora one (her end seats leave her a single neighbor) and 18 for a
    deck holding both. Empty when the deck holds no such unit.
    """
    slugs = [unit.slug for unit in ordered_deck]
    if not any(slug in SEATED_BUFF_SLUGS for slug in slugs):
        return []
    distinct = {}
    for arrangement in permutations(slugs):
        seats = {slug: seat for seat, slug in enumerate(arrangement)}
        if any(seats[slug] not in SEATED_BUFF_SLUGS[slug]
               for slug in slugs if slug in SEATED_BUFF_SLUGS):
            continue
        adjacency = {
            slug: [arrangement[j] for j in (seat - 1, seat + 1)
                   if 0 <= j < len(arrangement)]
            for seat, slug in enumerate(arrangement) if slug in SEATED_BUFF_SLUGS
        }
        key = tuple(sorted((slug, tuple(sorted(mates)))
                           for slug, mates in adjacency.items()))
        distinct.setdefault(key, adjacency)
    return list(distinct.values())


def evaluate_deck_best_seating(ordered_deck, boss: BossProfile, **kwargs):
    """`evaluate_deck`, but the seat arrangement is CHOSEN rather than assumed:
    the deck is scored under every arrangement its seated-buff units could take
    and the best one wins, reported as `result["seating"]`.

    Exhaustive over `seat_arrangements`, so it is the true maximum rather than a
    sample - and every candidate is a formation the player can actually field,
    which is what makes the reported number reproducible.

    It costs one simulation per arrangement: 6 for a Rouge deck, 10 for a Flora
    one, 18 for a deck holding both. Measured at a 180-sec fight against a plain
    evaluation of the same deck, that is +0.50 sec, +1.64 sec and +2.51 sec per
    reported deck - so a top-5 of decks that all hold both would add ~12 sec.
    This is why it is the REPORT path and not the search path: a request scores
    ~1200 decks (SEARCH_SIM_BUDGET) and cannot pay that per deck.
    Ranking therefore uses SquadContext.neighbor_slugs's policy and only the
    handful of decks actually shown to the player are re-scored here. A deck
    with no seated-buff unit costs exactly one simulation, as before, and
    carries no `seating` key - there is nothing for the player to arrange.

    The HOLD-FIRE tactic is chosen here for the same reason and on the same
    terms (`evaluate_deck_hold_fire_options`): whether to stop firing through a
    unit own Full Burst is a play decision, worth several percent when an ally
    round buff is there to preserve and a straight loss when it is not, and the
    gate means a deck that cannot use it still costs exactly one simulation.
    The winner is reported as `result["hold_fire"]`, absent when nobody holds.
    """
    arrangements = seat_arrangements(ordered_deck)
    holds = evaluate_deck_hold_fire_options(ordered_deck, boss)
    if not arrangements and holds == [frozenset()]:
        return evaluate_deck(ordered_deck, boss, **kwargs)
    best, best_arrangement, best_hold = None, None, frozenset()
    for adjacency in arrangements or [None]:
        for hold in holds:
            # Not passed when nobody holds, so a deck that cannot use the tactic
            # calls `evaluate_deck` with exactly the arguments it always did.
            held = {"hold_fire": hold} if hold else {}
            result = evaluate_deck(ordered_deck, boss, adjacency=adjacency,
                                   **held, **kwargs)
            if best is None or result["total_damage"] > best["total_damage"]:
                best, best_arrangement, best_hold = result, adjacency, hold
    if arrangements:
        best["seating"] = best_arrangement
    if best_hold:
        best["hold_fire"] = sorted(best_hold)
    return best


def _report(ranked, boss, top_n):
    """The leading `top_n` of a ranking, as summaries scored under each deck's
    BEST seating - and re-sorted on that score.

    The two numbers are not the same measurement. Ranking used
    SquadContext.neighbor_slugs's cheap policy; the report measures all six
    seatings and keeps the best. A deck whose arrangement gains more than its
    neighbor's therefore overtakes it right here, and publishing the ranking
    order would hand the caller a list that is not in descending order of the
    totals printed beside it (measured: a 7-unit roster where Rouge is the only
    Burst 1 puts the 4th deck above the 3rd). Sorting is stable, so decks that
    come out equal keep the ranking's order.
    """
    summaries = [_summarize(ordered, evaluate_deck_best_seating(ordered, boss))
                 for _, ordered in ranked[:top_n]]
    summaries.sort(key=lambda entry: entry["total_damage"], reverse=True)
    return summaries


def never_full_bursts(result):
    """이 배치가 풀 버스트를 한 번도 못 여는가 - `evaluate_deck`의 결과에 대고
    묻는다.

    「덱이 성립하지 않는다」는 뜻이 아니라 「이 배치로는 창이 안 열린다」는
    뜻이고, 총딜은 평타만으로 여전히 나온다. 그래서 그 숫자를 그냥 출력하면
    다른 배치와 비교 가능한 값처럼 보인다 - 실제로는 아니다.

    측정 스크립트가 각자 `events`를 뒤지는 대신 여기 물어보는 이유: 규칙을
    자체 구현한 스크립트는 에러 없이 틀린 숫자를 낸다(이 저장소에서 이미 두 번
    났다). 오늘 이 답이 참인 유일한 경우는 티어의 유일한 멤버가 `skip_cycles`
    지연이나 `max_bursts` 소진으로 영구히 못 쏘는 배치다 - 디젤: 윈터
    스위츠(Highlight)를 유일한 Burst 3으로 앉히면 그렇게 된다(그 조합은
    `ALLOWED_SHAPES`가 B3를 항상 둘 이상 요구하므로 추천 경로로는 안 나온다)."""
    return any(e["type"] == "full_burst_missed" for e in result["events"])


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
        "hold_burst_slugs": hold_burst_slugs(ordered_deck),
        "tap_fire_slugs": tap_fire_slugs(ordered_deck),
        # 그중 **배율을 실제로 버린** 좌석 - 차지가 살아 있는 구간에서도 톡톡이가 이겨서
        # 무차지 샷을 쏜 경우다. 유닛의 속성이 아니라 **이 덱에서의 결과**이고(재장전이
        # 부호를 정한다) 덱 목록만으로는 재현할 수 없어, hold_burst_slugs·seating과 같은
        # 계약으로 실려 온다. 비어 있으면 그 유닛은 차지가 0인 구간에서만 톡톡이다.
        "partial_charge_slugs": result.get("tap_fire_used", []),
        "partial_charge_full_rounds": result.get("tap_fire_full_rounds", {}),
        # Which allies this deck's seated-buff unit was scored beside, when it
        # holds one - the arrangement the player has to field for the number
        # above to be the one they get. Empty for every other deck. Same
        # contract as hold_burst_slugs: the deck alone does not carry it.
        "seating": result.get("seating", {}),
        # 쿨은 돌았는데 게이지가 안 차서 버스트를 못 쓴 사이클 수(**버충 밀림**).
        # 게이지가 덱 속성이 된 이상 이 수가 곧 「이 편성이 실전에서 밀리는가」다.
        # 분모는 이 전투가 완주한 사이클 전부이고, 분자는 그중 첫 사이클을 뺀
        # 나머지에서만 나온다 - 첫 사이클엔 돌고 있던 쿨다운이 없어 밀릴 것이
        # 없다(`raid_simulator`의 계수 참조).
        # 개수와 시간을 둘 다 싣는다 - 개수만으로는 4.3초 밀린 덱과 11.6초 밀린
        # 덱이 똑같이 「11/14」로 읽힌다.
        "gauge_bound_cycles": result.get("gauge_bound_cycles", 0),
        "gauge_delay_seconds": result.get("gauge_delay_seconds", 0.0),
        "total_cycles": sum(1 for e in result.get("events", ())
                            if e["type"] == "full_burst_end"),
        "result": result,
    }


def find_best_decks(roster, boss: BossProfile, top_n=5):
    """Not a production path (search_best_decks is), but the two must not
    disagree about what is playable - so it gets the same unfiltered retry
    search_best_decks does: a roster with no weakness-element unit at all
    cannot break the gimmick in any deck, and refusing a recommendation
    outright is worse than the best deck that clears everything but the phase
    gate."""
    deck_filter = _gimmick_filter(boss)
    scored = [
        _summarize(ordered, evaluate_deck_best_seating(ordered, boss))
        for ordered in feasible_orderings(roster, deck_filter)
    ]
    if not scored and deck_filter is not None:
        scored = [
            _summarize(ordered, evaluate_deck_best_seating(ordered, boss))
            for ordered in feasible_orderings(roster, None)
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
            and _taste_induced_valid(units)
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


def _orderings_within_budget(roster, sim_budget, deck_filter=None):
    """_bounded_orderings over every deck `roster` can form (no draft to honor)."""
    return _bounded_orderings(shape_combinations(roster, deck_filter), sim_budget)


def completions_fit_budget(required, candidates, sim_budget=SEARCH_SIM_BUDGET, deck_filter=None):
    """Whether best_completions can enumerate this draft's completions outright.

    Exported so a caller can decide UP FRONT whether to pay for something only
    the over-budget path needs (allocate_decks fits a surrogate). Asking is
    nearly free: the walk stops at the first ordering past the budget.
    """
    return _bounded_orderings(_shape_completions(required, candidates, deck_filter),
                              sim_budget) is not None


def search_best_decks(roster, boss: BossProfile, top_n=5,
                      sim_budget=SEARCH_SIM_BUDGET, pool=None, cascade=None,
                      deck_filter=_DERIVE_FILTER):
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

    A roster that holds no weakness-element unit at all cannot break the
    gimmick in ANY deck, so a `deck_filter` derived from it rejects the whole
    space and `_resolve_orderings` legitimately comes back empty. Refusing a
    recommendation outright is worse than the best deck that clears
    everything but the phase gate, so that case is retried unfiltered - the
    caller surfaces the shortfall itself (weakness_holders) rather than the
    search returning nothing. "Unfiltered" only drops the `deck_filter`
    predicate, though: `_ensure_weakness_in_pool` (in `_resolve_orderings`'s
    pruned-cut path) is gated on `boss.elemental_interrupt_required` alone, so
    a gimmick-on boss still gets this retry's pruned pool topped up with up to
    3 weakness units (one per tier) even here. Harmless - it only ever widens
    the pool a filterless search draws from - but this retry's pool is not
    quite the same size a gimmick-less boss's search would see.

    `deck_filter` left at its default derives the boss's gimmick filter (or
    None, if the boss has none). Pass None explicitly to search with NO
    filter at all - the two are not the same thing.
    """
    candidates = list(roster)
    if deck_filter is _DERIVE_FILTER:
        deck_filter = _gimmick_filter(boss)
        if deck_filter is not None and not deck_breaks_gimmick(roster, boss):
            # No unit anywhere in the roster holds the weakness element, so no
            # deck drawn from it can ever hold one either - walking the full
            # shape space just to discover that is a multi-second stall on a
            # real roster (measured ~9s on 78 units). Drop the filter up
            # front rather than pay for the doomed walk and its retry below.
            deck_filter = None
    orderings = _resolve_orderings(candidates, boss, sim_budget, pool, cascade, deck_filter)
    if not orderings and deck_filter is not None:
        orderings = _resolve_orderings(candidates, boss, sim_budget, pool, cascade, None)
    # Ranked on slim scores first; only the returned top_n get a second sim to
    # attach the full "result" (evaluate_deck is pure, so the floats are
    # identical to scoring the full summaries directly).
    totals = _score_batch(orderings, boss, pool)
    ranked = sorted(zip(totals, orderings), key=lambda pair: pair[0], reverse=True)
    return _report(ranked, boss, top_n)


def _resolve_orderings(roster, boss, sim_budget, pool, cascade, deck_filter):
    """search_best_decks's budget-then-cascade-then-cut ladder for one
    deck_filter value: try the full space first, and only pay for cascade's
    shortlist or prune_candidate_pool's cut once the full space blows the
    budget. A named function lets search_best_decks run the same ladder under
    two different filter values without keeping two copies in sync."""
    orderings = _orderings_within_budget(roster, sim_budget, deck_filter)
    if orderings is None:
        combos = cascade.shortlist(roster, boss, pool) if cascade is not None else None
        if combos is not None and deck_filter is not None:
            # The cascade ranks by predicted damage and knows nothing about the
            # gimmick, so its shortlist can be entirely decks the filter rejects.
            # Falling through to the pruned path is the same two-step this
            # function already takes when the cascade declines outright.
            combos = [c for c in combos if deck_filter(c)] or None
        if combos is None:
            cut = prune_candidate_pool(roster, boss, pool)
            combos = shape_combinations(_ensure_weakness_in_pool(cut, roster, boss),
                                        deck_filter)
        orderings = _all_intra_tier_orderings(combos)
    return orderings
