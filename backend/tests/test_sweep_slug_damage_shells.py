"""scripts/sweep_slug_damage.py의 셸이 **제품이 실제로 만들 수 있는 덱**인지.

이 스윕은 엔진 변경을 슬러그별로 A/B하는 도구다. 그 숫자가 의미를 가지려면 잰
덱이 추천기가 내놓을 수 있는 덱이어야 하는데, 티어 3 셸은 두 달 동안
`(2,2,1)` — `ALLOWED_SHAPES`에 없는 모양 — 이었다. 대부분의 유닛에게는 티가 안
났고, **티어메이트가 반드시 필요한 한 유닛에서만** 드러났다: 디젤: 윈터
스위츠(Highlight)는 첫 사이클을 거르는 킷이라 대신 쏠 Burst 3이 없으면 풀
버스트가 한 번도 안 열려, 평타만으로 163M(정상 ~774M)을 조용히 보고했다.

셸은 손으로 유지되는 표이므로 여기서 대조한다.
"""
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

import sweep_slug_damage as sweep  # noqa: E402

from app.deck_search import deck_is_valid  # noqa: E402
from app.user_roster import load_roster  # noqa: E402


def _deck(slugs):
    specs, excluded = load_roster([sweep._nikke(s) for s in slugs])
    assert not excluded, f"셸 유닛을 로스터가 못 만든다: {excluded}"
    return specs


@pytest.mark.parametrize("tier", [1, 2, 3])
def test_each_shell_plus_a_unit_of_its_tier_is_a_deck_the_search_would_build(tier):
    """셸 + 그 티어 유닛 하나 = `deck_is_valid`를 통과하는 5인 덱."""
    probe = {1: "liter", 2: "crown", 3: "jill-valentine"}[tier]
    shell = sweep._shell_for(probe, tier)
    assert shell is not None and len(shell) == 4
    assert deck_is_valid(_deck(shell + [probe]))


def test_the_tier_three_shell_seats_a_burst_three():
    """모든 `ALLOWED_SHAPES`가 Burst 3을 둘 이상 요구하므로, 티어 3 셸에 Burst
    3이 없으면 그 셸은 존재할 수 없는 덱이다 - 셸 규칙(「재는 티어를 넣지
    마라」)이 티어 3에서만 성립하지 않는 이유다."""
    shell = sweep.SHELLS[3]
    tiers = [spec.burst_tier for spec in _deck(shell)]
    assert tiers.count(3) == 1, f"티어 3 셸의 Burst 3 수가 1이 아니다: {shell}"


def test_a_stand_in_is_declared_for_every_partner_that_needs_one():
    """짝 자신을 잴 때는 대역이 있어야 한다 - 없으면 그 행이 캐릭터 충돌로
    조용히 「덱 없음」이 된다."""
    for character in [sweep.TIER3_PARTNER, *sweep.TIER3_PARTNER_OVERRIDES.values()]:
        assert sweep.TIER3_PARTNER_OVERRIDES.get(character, sweep.TIER3_PARTNER) != character


def test_no_two_slugs_are_measured_on_the_same_five_units():
    """두 행이 같은 덱이면 영원히 같이 움직여서, 어느 유닛이 변했는지 못 가린다.
    셸들이 티어를 넘나들며 같은 몇 유닛을 재사용하므로 실수로 만들기 쉽다 -
    티어 3 셸에 Burst 1을 넣자 그 Burst 1의 티어 1 덱이 그대로 복원됐다."""
    clashes = sweep.check_shells_are_distinct()
    assert clashes == [], clashes
