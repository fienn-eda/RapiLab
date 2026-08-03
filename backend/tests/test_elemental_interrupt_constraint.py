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
