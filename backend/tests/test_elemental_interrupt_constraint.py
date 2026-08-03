"""속성저지 기믹: 파훼하려면 약점 속성 니케가 덱에 최소 1기 있어야 한다.

지금까지 덱 합법성 술어는 전부 유닛만 봤다(_no_character_clash 등). 이것은 보스에
의존하는 첫 제약이므로, 술어 자체와 그것이 탐색에 어떻게 들어가는지를 따로 고정한다.
"""
from dataclasses import dataclass

from app.deck_search import BossProfile, deck_breaks_gimmick, weakness_holders
from app.elements import weakness_of


@dataclass(frozen=True)
class Unit:
    """탐색이 유닛에게 묻는 것만 갖는 스텁. `base_stats`/`weapon_stats`는
    prune_candidate_pool의 `_prior`가 읽는 두 값이고(뒤의 Task들이 그 경로를 탄다),
    `backend/tests/test_deck_allocation.py`의 Unit이 같은 이유로 같은 모양이다."""
    slug: str
    burst_tier: int
    element: str
    base_stats: dict = None
    weapon_stats: dict = None

    def __post_init__(self):
        if self.base_stats is None:
            object.__setattr__(self, "base_stats", {"atk": 1000.0})
        if self.weapon_stats is None:
            object.__setattr__(self, "weapon_stats", {"damage_percent": 1.0})


def _deck(*elements):
    return [Unit(f"u{i}", 1 + i % 3, e) for i, e in enumerate(elements)]


def test_the_weakness_of_a_fire_boss_is_water():
    # elements.py: Water > Fire > Wind > Iron > Electric > Water
    assert weakness_of("Fire") == "Water"
    assert weakness_of("Water") == "Electric"


def test_every_element_has_exactly_one_weakness_and_it_round_trips():
    from app.elements import _STRONG_AGAINST

    for attacker, beaten in _STRONG_AGAINST.items():
        assert weakness_of(beaten) == attacker


def test_a_boss_with_no_gimmick_admits_any_deck():
    boss = BossProfile(element="Fire")
    assert deck_breaks_gimmick(_deck("Fire", "Fire", "Fire", "Fire", "Fire"), boss)


def test_an_element_less_boss_admits_any_deck_even_with_the_gimmick_on():
    # No element means no weakness, so demanding one would make every roster
    # infeasible rather than expressing a real requirement.
    boss = BossProfile(element=None, elemental_interrupt_required=True)
    assert deck_breaks_gimmick(_deck("Fire", "Fire", "Fire", "Fire", "Fire"), boss)


def test_the_gimmick_needs_one_unit_of_the_weakness_element():
    boss = BossProfile(element="Fire", elemental_interrupt_required=True)
    assert not deck_breaks_gimmick(_deck("Fire", "Wind", "Iron", "Electric", "Fire"), boss)
    assert deck_breaks_gimmick(_deck("Fire", "Wind", "Iron", "Electric", "Water"), boss)


def test_weakness_holders_counts_only_when_the_gimmick_is_on():
    units = _deck("Water", "Water", "Fire", "Fire", "Fire")
    assert weakness_holders(units, BossProfile(element="Fire")) == 0
    assert weakness_holders(
        units, BossProfile(element="Fire", elemental_interrupt_required=True)) == 2


def test_shape_combinations_drops_decks_that_cannot_break_the_gimmick():
    from app.deck_search import shape_combinations

    boss = BossProfile(element="Fire", elemental_interrupt_required=True)
    # Four tier-3 units (not three) so combinations(4, 3) has more than one
    # 3-of-4 pick - with exactly three, the only pick IS all three and always
    # includes the lone Water unit, leaving nothing for the filter to drop.
    roster = [Unit("b1", 1, "Fire"), Unit("b2", 2, "Fire"),
              Unit("c1", 3, "Fire"), Unit("c2", 3, "Fire"), Unit("c3", 3, "Water"),
              Unit("c4", 3, "Fire")]

    unfiltered = list(shape_combinations(roster))
    filtered = list(shape_combinations(roster, lambda d: deck_breaks_gimmick(d, boss)))

    assert unfiltered      # the roster does form (1,1,3) decks
    assert all(any(u.element == "Water" for u in deck) for deck in filtered)
    assert len(filtered) < len(unfiltered)


def test_shape_completions_drops_them_too():
    from app.deck_search import _shape_completions

    boss = BossProfile(element="Fire", elemental_interrupt_required=True)
    required = [Unit("b1", 1, "Fire")]
    candidates = [Unit("b2", 2, "Fire"), Unit("c1", 3, "Fire"),
                  Unit("c2", 3, "Fire"), Unit("c3", 3, "Water")]

    filtered = list(_shape_completions(required, candidates,
                                       lambda d: deck_breaks_gimmick(d, boss)))

    assert filtered
    assert all(any(u.element == "Water" for u in deck) for deck in filtered)


def test_a_pruned_pool_is_topped_back_up_with_the_weakness_element():
    """prune_candidate_pool ranks by marginal contribution and knows nothing
    about the gimmick, so its cut can hold no weakness unit at all - and then the
    constrained search has nothing to return. Widen the pool rather than fall
    back to an exhaustive walk over the full roster (millions of orderings)."""
    from app.deck_search import _ensure_weakness_in_pool

    boss = BossProfile(element="Fire", elemental_interrupt_required=True)
    cut = [Unit("b1", 1, "Fire"), Unit("b2", 2, "Fire"), Unit("c1", 3, "Fire")]
    roster = cut + [Unit("w1", 1, "Water"), Unit("w3", 3, "Water")]

    topped = _ensure_weakness_in_pool(cut, roster, boss)

    assert any(u.element == "Water" for u in topped)
    # Unit is frozen but holds dict fields (base_stats/weapon_stats), so it is
    # unhashable - set() would raise TypeError. Containment only needs __eq__.
    assert all(u in topped for u in cut)


def test_a_pool_that_already_holds_the_weakness_is_left_alone():
    from app.deck_search import _ensure_weakness_in_pool

    boss = BossProfile(element="Fire", elemental_interrupt_required=True)
    cut = [Unit("b1", 1, "Water"), Unit("b2", 2, "Fire")]

    assert _ensure_weakness_in_pool(cut, cut, boss) is cut


# 작열 보스의 약점. 이 파일 전체가 이 한 쌍으로 말한다.
WEAKNESS = "Water"
GIMMICK_BOSS = BossProfile(element="Fire", elemental_interrupt_required=True)


def _roster(n_weakness):
    """10 units - two decks' worth - of which the first `n_weakness` are the
    weakness element and the rest are the boss's own.

    Tiers 3/2/5 (B1/B2/B3) put every ordering under SEARCH_SIM_BUDGET (720 of
    1200), so the search enumerates rather than pruning: this file is about the
    constraint, not about the cut. The weakness units land at tier 1 first, so
    n=2 gives two B1s that CAN sit in different decks - which is what makes the
    budget cap in Task 10 a real test rather than a tautology.
    """
    tiers = [1, 1, 1, 2, 2, 3, 3, 3, 3, 3]
    return [Unit(f"u{i}", t, WEAKNESS if i < n_weakness else "Fire")
            for i, t in enumerate(tiers)]


def test_a_single_deck_search_returns_a_deck_that_breaks_the_gimmick(monkeypatch):
    """종단 확인 - 술어가 아니라 search_best_decks의 반환값을 본다."""
    from app.deck_search import search_best_decks
    from tests.test_deck_allocation import patch_scorer

    roster = _roster(2)
    by_slug = {u.slug: u for u in roster}
    # 약점 유닛이 없는 덱을 더 높게 친다 - 제약이 없으면 그쪽이 뽑힌다.
    patch_scorer(monkeypatch,
                 lambda slugs: 10.0 if any(by_slug[s].element == WEAKNESS for s in slugs)
                 else 100.0)

    result = search_best_decks(roster, GIMMICK_BOSS, top_n=1)

    assert any(by_slug[s].element == WEAKNESS for s in result[0]["deck"])


def test_a_roster_with_no_weakness_unit_still_gets_a_recommendation(monkeypatch):
    # 제약을 못 지키는 로스터에 대해 추천을 거부하지 않는다 - UI가 경고를 단다.
    from app.deck_search import search_best_decks
    from tests.test_deck_allocation import patch_scorer

    patch_scorer(monkeypatch, lambda slugs: 1.0)

    assert search_best_decks(_roster(0), GIMMICK_BOSS, top_n=1)


def test_best_completions_deck_filter_none_means_unconstrained_not_derived(monkeypatch):
    """None must mean "search with no filter at all" and not silently fall
    back to the boss-derived gimmick filter - Task 10's unconstrained
    fallback for an undraftable completion depends on the two being
    different. `required` fills tier 2 and all of tier 3, leaving only one
    tier-1 seat; the sole tier-1 candidate shares the boss's own element, so
    the only completion this draft can ever form fails the gimmick outright -
    the constrained call must refuse it and the unconstrained one must not."""
    from app.deck_search import best_completions, deck_breaks_gimmick
    from tests.test_deck_allocation import patch_scorer

    required = [Unit("r2", 2, "Fire"), Unit("r3a", 3, "Fire"),
                Unit("r3b", 3, "Fire"), Unit("r3c", 3, "Fire")]
    candidates = [Unit("f1", 1, "Fire"), Unit("w3", 3, "Water")]
    by_slug = {u.slug: u for u in required + candidates}
    patch_scorer(monkeypatch, lambda slugs: 1.0)

    constrained = best_completions(required, candidates, GIMMICK_BOSS, top_n=1)
    assert constrained == []

    unconstrained = best_completions(required, candidates, GIMMICK_BOSS, top_n=1,
                                     deck_filter=None)
    assert unconstrained
    deck = [by_slug[s] for s in unconstrained[0]["deck"]]
    assert not deck_breaks_gimmick(deck, GIMMICK_BOSS)


def _satisfied(alloc, roster):
    by_slug = {u.slug: u for u in roster}
    return sum(1 for d in alloc["decks"]
               if any(by_slug[s].element == WEAKNESS for s in d["deck"]))


def _stacking_scorer(monkeypatch):
    """Reward putting BOTH weakness units in one deck.

    Without the peel's per-deck cap the greedy peel takes that bait and deck 2
    gets nothing - which is exactly the starvation the cap exists to prevent. A
    scorer that is indifferent would make these tests pass for the wrong reason.
    """
    from tests.test_deck_allocation import patch_scorer
    patch_scorer(monkeypatch, lambda slugs: 100.0 if {"u0", "u1"} <= slugs else 10.0)


def test_the_peel_spreads_the_weakness_units_across_the_decks(monkeypatch):
    """설계 B.2. 약점유닛 2기 / 2덱이면 2덱 다 만족한다 - 점수가 몰아넣기를 부추겨도."""
    from app.deck_allocation import allocate_decks

    _stacking_scorer(monkeypatch)
    roster = _roster(2)
    alloc = allocate_decks(roster, GIMMICK_BOSS, num_decks=2, time_budget_sec=0.0)

    assert len(alloc["decks"]) == 2
    assert _satisfied(alloc, roster) == 2


def test_a_thin_roster_satisfies_as_many_decks_as_it_can_and_no_fewer(monkeypatch):
    """약점유닛 1기 / 2덱이면 정확히 1덱. 0덱(제약을 놓침)도 2덱(없는 유닛)도 아니다."""
    from app.deck_allocation import allocate_decks
    from tests.test_deck_allocation import patch_scorer

    patch_scorer(monkeypatch, lambda slugs: 1.0)
    roster = _roster(1)
    alloc = allocate_decks(roster, GIMMICK_BOSS, num_decks=2, time_budget_sec=0.0)

    assert _satisfied(alloc, roster) == 1


def test_a_roster_with_no_weakness_unit_still_allocates(monkeypatch):
    from app.deck_allocation import allocate_decks
    from tests.test_deck_allocation import patch_scorer

    patch_scorer(monkeypatch, lambda slugs: 1.0)
    roster = _roster(0)
    alloc = allocate_decks(roster, GIMMICK_BOSS, num_decks=2, time_budget_sec=0.0)

    assert len(alloc["decks"]) == 2
    assert _satisfied(alloc, roster) == 0


def test_the_climb_will_not_stack_the_weakness_units_back_together(monkeypatch):
    """가드의 첫 번째 갈래. 몰아넣기가 100 + 10 = 110점이고 흩뿌리기는 10 + 10 = 20점
    이므로, 가드가 없으면 힐클라임이 peel의 배분을 즉시 되돌린다."""
    from app.deck_allocation import allocate_decks

    _stacking_scorer(monkeypatch)
    roster = _roster(2)
    alloc = allocate_decks(roster, GIMMICK_BOSS, num_decks=2, time_budget_sec=30.0)

    assert _satisfied(alloc, roster) == 2


def test_the_swap_floor_never_exceeds_what_we_already_hold():
    """가드의 두 번째 갈래. K에 못 미치는 상태에서는 하한도 K가 아니라 현재값이다 -
    K를 그대로 쓰면 모든 스왑이 거부되어 클라임이 통째로 죽는다."""
    from app.deck_allocation import _gimmick_floor, _satisfied_count

    decks = [[Unit("a", 1, WEAKNESS)], [Unit("b", 1, "Fire")]]

    assert _satisfied_count(decks, GIMMICK_BOSS) == 1
    assert _gimmick_floor(decks, GIMMICK_BOSS, 2) == 1   # K=2지만 지금은 1
    assert _gimmick_floor(decks, GIMMICK_BOSS, 1) == 1
    assert _satisfied_count(decks, BossProfile(element="Fire")) == 0   # 기믹 없음


def test_an_allocation_without_the_gimmick_is_byte_for_byte_the_old_one(monkeypatch):
    """제약이 꺼져 있으면 _gimmick_budget이 None, gimmick_target이 0이라 peel도
    클라임도 이전 코드와 같은 경로를 탄다. 배분 결과가 달라지면 회귀다."""
    from app.deck_allocation import allocate_decks

    _stacking_scorer(monkeypatch)
    roster = _roster(2)

    off = allocate_decks(roster, BossProfile(element="Fire"), num_decks=2,
                         time_budget_sec=30.0)

    # 기믹이 없으면 점수를 그대로 따라가 두 약점유닛이 한 덱에 몰린다.
    assert _satisfied(off, roster) == 1
    assert sum(d["total_damage"] for d in off["decks"]) == 110.0
