"""선언된 파츠 파괴 시각 - 불리언 플래그를 시각으로 정밀화하는 축.

`part_destructible`은 「이 보스에 파괴 가능한 파츠가 있는가」만 말하므로, 파괴에
반응하는 스킬은 floor(한 번도 안 깨진다)와 ceiling(전투 내내 깨져 있다) 두 갈래로만
근사됐다. `part_destruction_times`는 그 사이를 채운다: Fienn이 그 보스에서 실제로
파괴가 일어나는 시각을 관측해 적으면, 파괴에 걸린 버프가 그 시각마다 자기 지속시간
만큼만 산다.
"""
import pytest

from app.deck_search import BossProfile, evaluate_deck
from app.effects import EffectRegistry
from app.roster import NikkeSpec
from app.skill_rules.diesel_winter_sweets import build_diesel_intro_rules
from app.skill_rules.raven import build_raven_rules
from app.squad_engine import (
    SquadContext,
    SquadMember,
    boss_part_destructible,
    boss_part_destruction_untimed,
    fire_trigger,
)
from tests.test_ark_ranger_bracket import liter_spec
from tests.test_roster import anis_star_spec, crown_spec, takina_spec
from tests.test_skill_rules_diesel_winter_sweets import VALUES as DIESEL_VALUES
from tests.test_skill_rules_raven import RAVEN, VALUES as RAVEN_VALUES


def _ctx(part_destructible, times=()):
    return SquadContext(
        [SquadMember("raven", burst_tier=3, element="Iron")],
        part_destructible=part_destructible,
        part_destruction_times=times,
    )


def test_context_defaults_part_destruction_times_empty():
    assert SquadContext([SquadMember("x", 3, "Iron")]).part_destruction_times == ()


def test_declared_times_reach_the_context():
    assert _ctx(True, (1.0, 61.0, 126.0)).part_destruction_times == (1.0, 61.0, 126.0)


def test_untimed_condition_is_true_only_without_declared_times():
    # 시각이 선언되면 옛 ceiling 근사(전투 시작부터 영구)는 꺼져야 한다 - 그 자리를
    # 시각 기반 창이 대신 채우므로, 둘 다 켜지면 같은 버프가 두 번 걸린다.
    assert boss_part_destruction_untimed()(_ctx(True), "raven") is True
    assert boss_part_destruction_untimed()(_ctx(True, (1.0,)), "raven") is False
    assert boss_part_destruction_untimed()(_ctx(False), "raven") is False


def test_destructible_condition_stays_true_when_times_are_declared():
    # 시각 선언은 「파괴 가능하다」를 부정하지 않는다 - 아크레인저의 브래킷처럼
    # 불리언만 보는 기존 소비자는 그대로 동작해야 한다.
    assert boss_part_destructible()(_ctx(True, (1.0,)), "raven") is True


# --- 선언된 시각마다 열리는 창 -------------------------------------------

DIESEL = "diesel-winter-sweets-intro"
DIESEL_TARGET = {"slug": DIESEL, "element": "Fire", "burst_tier": 3, "weapon": "RL"}


def _fire(slug, element, rules, trigger, times, time):
    context = SquadContext(
        [SquadMember(slug, 3, element)],
        part_destructible=True,
        part_destruction_times=times,
    )
    registry = EffectRegistry()
    fire_trigger(trigger, {slug: rules}, context, registry, time)
    return registry


def test_raven_single_point_attack_lives_15s_from_the_declared_destruction():
    registry = _fire("raven", "Iron", build_raven_rules(RAVEN_VALUES),
                     "part_destroyed", (1.0, 61.0, 126.0), time=1.0)
    assert registry.total_for("sustained_damage_up", RAVEN, 1.0) == pytest.approx(0.4732)
    assert registry.total_for("sustained_damage_up", RAVEN, 15.9) == pytest.approx(0.4732)
    assert registry.total_for("sustained_damage_up", RAVEN, 16.1) == 0.0


def test_raven_ceiling_is_off_once_destruction_times_are_declared():
    # 시각이 있으면 battle_start의 영구 근사가 꺼져야 한다 - 안 꺼지면 창과 겹쳐
    # 같은 버프가 두 번 걸린다.
    registry = _fire("raven", "Iron", build_raven_rules(RAVEN_VALUES),
                     "battle_start", (1.0, 61.0, 126.0), time=0.0)
    assert registry.total_for("sustained_damage_up", RAVEN, 0.0) == 0.0


def test_diesel_part_destruction_buff_lives_15s_from_the_declared_destruction():
    registry = _fire(DIESEL, "Fire", build_diesel_intro_rules(DIESEL_VALUES),
                     "part_destroyed", (1.0, 61.0, 126.0), time=61.0)
    assert registry.total_for("sustained_damage_up", DIESEL_TARGET, 61.0) == pytest.approx(0.6804)
    assert registry.total_for("sustained_damage_up", DIESEL_TARGET, 75.9) == pytest.approx(0.6804)
    assert registry.total_for("sustained_damage_up", DIESEL_TARGET, 76.1) == 0.0


def test_diesel_ceiling_is_off_once_destruction_times_are_declared():
    registry = _fire(DIESEL, "Fire", build_diesel_intro_rules(DIESEL_VALUES),
                     "battle_start", (1.0, 61.0, 126.0), time=0.0)
    assert registry.total_for("sustained_damage_up", DIESEL_TARGET, 0.0) == 0.0


def _fire_all(slug, element, rules, trigger, times):
    """같은 레지스트리에 여러 시각으로 트리거를 쏜다 - 창이 겹칠 때를 보려면
    호출마다 레지스트리를 새로 만들면 안 된다."""
    context = SquadContext(
        [SquadMember(slug, 3, element)],
        part_destructible=True,
        part_destruction_times=times,
    )
    registry = EffectRegistry()
    for time in times:
        fire_trigger(trigger, {slug: rules}, context, registry, time)
    return registry


def test_raven_overlapping_destructions_refresh_rather_than_stack():
    # 스킬 원문에 「Stacks up to N」이 없다. 그러면 중첩이 아니라 갱신이다 -
    # 15초 안에 파츠가 두 번 깨지면 버프가 두 배가 되는 게 아니라 창이 늘어난다.
    registry = _fire_all("raven", "Iron", build_raven_rules(RAVEN_VALUES),
                         "part_destroyed", (1.0, 5.0))

    assert registry.total_for("sustained_damage_up", RAVEN, 6.0) == pytest.approx(0.4732)
    # 두 번째 파괴가 창을 5+15=20까지 민다.
    assert registry.total_for("sustained_damage_up", RAVEN, 19.9) == pytest.approx(0.4732)
    assert registry.total_for("sustained_damage_up", RAVEN, 20.1) == 0.0


def test_diesel_overlapping_destructions_refresh_rather_than_stack():
    registry = _fire_all(DIESEL, "Fire", build_diesel_intro_rules(DIESEL_VALUES),
                         "part_destroyed", (1.0, 5.0))

    assert registry.total_for("sustained_damage_up", DIESEL_TARGET, 6.0) \
        == pytest.approx(0.6804)
    assert registry.total_for("sustained_damage_up", DIESEL_TARGET, 20.1) == 0.0


# --- 시뮬레이터가 그 시각에 실제로 트리거를 쏘는가 ------------------------

def raven_spec():
    return NikkeSpec(
        slug="raven",
        burst_tier=3,
        burst_cooldown=40.0,  # data/lootandwaifus/char_raven.json
        element="Iron",
        weapon="RL",
        base_stats={"atk": 400000, "def": 55000, "max_hp": 9700000},
        # caster_atk는 roster가 base_stats에서 넣어 준다 - 여기 적으면 두 출처가 된다.
        skill_values={k: v for k, v in RAVEN_VALUES.items() if k != "caster_atk"},
        weapon_stats={
            "weapon": "RL", "damage_percent": 100.0, "max_ammo": 6,
            "reload_time": 2.0, "charge_time": 1.0, "charge_damage_percent": 250.0,
        },
    )


def _raven_deck_damage(part_destructible, times=()):
    boss = BossProfile(
        fight_duration=180.0,
        part_destructible=part_destructible,
        part_destruction_times=times,
    )
    deck = [liter_spec(), anis_star_spec(), crown_spec(), takina_spec(), raven_spec()]
    return evaluate_deck(deck, boss)["total_damage"]


def test_declared_times_open_more_windows_than_the_untimed_approximation():
    """시각을 모르는 근사는 전투 시작의 창 하나뿐이다. 시각 셋을 선언하면 창이
    셋이 되므로 딜이 올라가야 한다 - 시뮬레이터가 그 시각마다 트리거를 쏘아야만
    올라간다."""
    no_parts = _raven_deck_damage(False)
    untimed = _raven_deck_damage(True)
    timed = _raven_deck_damage(True, (1.0, 61.0, 126.0))

    assert no_parts < untimed < timed


def test_times_do_nothing_on_a_boss_with_no_destructible_parts():
    # 파괴 가능한 파츠가 없다고 말해 놓고 파괴 시각을 적은 상태는 모순이고,
    # 불리언이 이긴다 - 그게 「이 보스에 깨지는 파츠가 있는가」를 말하는 필드다.
    # 안 그러면 floor로 재려는 사람이 아크레인저만 floor고 레이븐·디젤은 창을
    # 받는 반쪽 인카운터를 얻는다.
    floor = _raven_deck_damage(False)

    assert _raven_deck_damage(False, (1.0, 61.0, 126.0)) == floor


def test_times_past_the_fights_end_do_not_land():
    # 인카운터가 선언한 시각은 전투 길이보다 길 수 있다(같은 보스, 짧은 전투).
    # 안 일어난 파괴가 버프를 주면 안 된다.
    short = _raven_deck_damage(True, (1.0, 500.0))
    only_first = _raven_deck_damage(True, (1.0,))

    assert short == only_first
