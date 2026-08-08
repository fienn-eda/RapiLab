"""힐/쉴드 제공자 상수가 스킬 데이터와 어긋나면 실패한다.

두 상수는 "덱에 이런 유닛이 있나"만 묻는 근사의 재료다(엔진에 힐·쉴드 이벤트가
없다). 손으로 유지되던 힐 목록은 실제로 **여섯 슬러그만큼 낡은 채 굳어 있었고**
(플로라 두 빌드 포함 — 스쿼드에서 가장 순수한 힐러 옆에서 크라운의 천장 분기가
한 번도 안 켜졌다), 목록이 낡아도 테스트는 전부 green이었다. 그래서 이 대조가
있다: 새 유닛을 인코딩하거나 데이터를 다시 받으면 여기서 걸린다.
"""
import pytest

from app.skill_rules._helpers import (
    ELEMENT_GATED_SHIELD_SLUGS,
    HEAL_PROVIDER_SLUGS,
    SELF_ONLY_SHIELD_SLUGS,
    SHIELD_PROVIDER_SLUGS,
    SQUAD_DISTRIBUTED_DAMAGE_BUFF_SLUGS,
    SQUAD_SUSTAINED_DAMAGE_BUFF_SLUGS,
    SUBSET_SUSTAINED_DAMAGE_BUFF_SLUGS,
)
from app.skill_rules.provider_scan import (
    distributed_damage_buff_slugs,
    heal_provider_slugs,
    shield_provider_slugs,
    sustained_damage_buff_slugs,
    unreadable_slugs,
)


@pytest.fixture(scope="module")
def unreadable():
    return unreadable_slugs()


def test_heal_provider_constant_matches_the_skill_data(unreadable):
    derived = heal_provider_slugs()
    assert derived - unreadable == HEAL_PROVIDER_SLUGS - unreadable


def test_shield_provider_constant_matches_the_skill_data(unreadable):
    # 상수는 소비자에게 실제로 닿는 것만 담고, 닿는 범위가 좁은 쉴드는 사유와
    # 함께 따로 뺀다(속성 게이트 / 자기 전용) - 셋을 합치면 데이터가 말하는
    # 전량이어야 한다.
    derived = shield_provider_slugs()
    committed = SHIELD_PROVIDER_SLUGS | ELEMENT_GATED_SHIELD_SLUGS | SELF_ONLY_SHIELD_SLUGS
    assert derived - unreadable == committed - unreadable


def test_element_gated_shields_are_not_also_counted_as_reaching_everyone():
    assert not (SHIELD_PROVIDER_SLUGS & ELEMENT_GATED_SHIELD_SLUGS)


def test_self_only_shields_are_not_also_counted_as_reaching_everyone():
    """자기에게만 거는 쉴드가 전체 도달 목록에 섞이면, 소비자가 「내 앞에 쉴드가
    놓였나」에 거짓으로 예라고 답하게 된다."""
    assert not (SELF_ONLY_SHIELD_SLUGS & (SHIELD_PROVIDER_SLUGS | ELEMENT_GATED_SHIELD_SLUGS))


def test_sustained_damage_buff_constant_matches_the_skill_data(unreadable):
    """같은 대조를 지속딜 버퍼에도 건다. 이쪽은 소비자가 불릿이 아니라 **상태**다 —
    브래디는 지속딜 버프를 받아야 Lingering Taste에 들어가고, 그 상태가 없으면
    Favorite Candy 두 불릿과 New Flavor의 3분의 2가 전부 안 켜진다. 목록이 낡으면
    새 지속딜 버퍼 옆에서도 그녀가 계속 불법으로 판정된다."""
    derived = sustained_damage_buff_slugs()
    committed = SQUAD_SUSTAINED_DAMAGE_BUFF_SLUGS | SUBSET_SUSTAINED_DAMAGE_BUFF_SLUGS
    assert derived - unreadable == committed - unreadable


def test_distributed_damage_buff_constant_matches_the_skill_data(unreadable):
    derived = distributed_damage_buff_slugs()
    assert derived - unreadable == SQUAD_DISTRIBUTED_DAMAGE_BUFF_SLUGS - unreadable


def test_subset_sustained_buffs_are_not_also_counted_as_reaching_everyone():
    assert not (SQUAD_SUSTAINED_DAMAGE_BUFF_SLUGS & SUBSET_SUSTAINED_DAMAGE_BUFF_SLUGS)
