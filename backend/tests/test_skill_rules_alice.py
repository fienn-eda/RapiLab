"""Alice - a Burst-3 SR Attacker whose burst deals no damage and whose whole
output is normal attacks. Her cadence lives in `registry.MANUAL_TAP_FIRE_INTERVAL`
and `tests/test_manual_tap_fire.py`; this module covers her three skills.
"""
import pytest

from app.effects import EffectRegistry
from app.skill_rules.alice import (build_alice_rules,
                                   energizing_carrot_charge_cut_seconds)
from app.squad_engine import SquadContext, SquadMember, fire_trigger

ENERGIZING_CARROT = {
    "description_value_01": "2", "description_value_02": "11.67",
    "description_value_03": "10", "description_value_04": "7",
    "description_value_05": "10",
}
HEALTHY_CARROT = {
    "description_value_01": "80", "description_value_02": "80",
    "description_value_03": "8.12",
}
WONDERLAND = {
    "description_value_01": "80.15", "description_value_02": "10",
    "description_value_03": "55.12", "description_value_04": "10",
}
# 그녀 자신의 차지 1.5초가 Energizing Carrot의 기준이다 (data/shiftypad/alice.json)
ALICE_WEAPON = {"charge_time": 1.5}
ALICE_VALUES = {
    "energizing_carrot": ENERGIZING_CARROT,
    "healthy_carrot": HEALTHY_CARROT,
    "wonderland": WONDERLAND,
    "caster_weapon_stats": ALICE_WEAPON,
}

ALICE = {"slug": "alice", "element": "Fire"}
ALLY_HIGH = {"slug": "ally-high", "element": "Water"}
ALLY_LOW = {"slug": "ally-low", "element": "Wind"}


def make_context(base_atk):
    return SquadContext(
        [
            SquadMember("alice", burst_tier=3, element="Fire", weapon="SR"),
            SquadMember("ally-high", burst_tier=1, element="Water", weapon="AR"),
            SquadMember("ally-low", burst_tier=2, element="Wind", weapon="AR"),
        ],
        base_atk=base_atk,
    )


def _fire(trigger, base_atk=None, time=0.0):
    base_atk = base_atk or {"alice": 10000.0, "ally-high": 20000.0, "ally-low": 100.0}
    registry = EffectRegistry()
    fire_trigger(trigger, {"alice": build_alice_rules(ALICE_VALUES)},
                 make_context(base_atk), registry, time)
    return registry


def test_alice_has_one_rule_per_skill():
    rules = build_alice_rules(ALICE_VALUES)
    assert [r.trigger for r in rules] == [
        "full_burst_enter", "battle_start", "own_burst_activate"]


def test_energizing_carrot_charge_cut_is_seconds_off_the_casters_own_charge():
    """"X% of the skill user's Charge Speed" is a percentage of HER charge time,
    handed over as absolute seconds - Liberalio's Calm Depths mechanism. Encoding
    it as a percent would hand a 1.0-sec-charge recipient a different cut than
    the game gives.
    """
    assert energizing_carrot_charge_cut_seconds(
        ENERGIZING_CARROT, ALICE_WEAPON) == pytest.approx(0.17505)
    # 기준은 받는 쪽이 아니라 시전자다: 무기가 바뀌면 초가 따라 움직인다.
    assert energizing_carrot_charge_cut_seconds(
        ENERGIZING_CARROT, {"charge_time": 1.0}) == pytest.approx(0.1167)


def test_energizing_carrot_buffs_the_top_two_including_alice_herself():
    """원문에 "(except caster)" 절이 없으므로 그녀도 자기 두 자리를 두고 경쟁한다."""
    registry = _fire("full_burst_enter", {"alice": 10000.0, "ally-high": 20000.0,
                                          "ally-low": 100.0})
    assert registry.total_for("charge_time_reduction_sec", ALICE, now=0.0) == pytest.approx(0.17505)
    assert registry.total_for("charge_time_reduction_sec", ALLY_HIGH, now=0.0) == pytest.approx(0.17505)
    assert registry.total_for("charge_time_reduction_sec", ALLY_LOW, now=0.0) == 0.0
    assert registry.total_for("charge_damage_bonus", ALICE, now=0.0) == pytest.approx(0.07)
    assert registry.total_for("charge_damage_bonus", ALLY_HIGH, now=0.0) == pytest.approx(0.07)
    assert registry.total_for("charge_damage_bonus", ALLY_LOW, now=0.0) == 0.0


def test_energizing_carrot_drops_alice_when_two_allies_outrank_her():
    registry = _fire("full_burst_enter", {"alice": 100.0, "ally-high": 20000.0,
                                          "ally-low": 10000.0})
    assert registry.total_for("charge_time_reduction_sec", ALICE, now=0.0) == 0.0
    assert registry.total_for("charge_time_reduction_sec", ALLY_LOW, now=0.0) == pytest.approx(0.17505)


def test_energizing_carrot_lasts_ten_seconds():
    registry = _fire("full_burst_enter")
    assert registry.total_for("charge_damage_bonus", ALICE, now=9.9) == pytest.approx(0.07)
    assert registry.total_for("charge_damage_bonus", ALICE, now=10.1) == 0.0


def test_healthy_carrot_grants_pierce_permanently_to_herself():
    """HP 80% 이상 분기다. 시뮬은 아군을 다치게 하지 않으므로 조건이 상시 참이고,
    창이 끊길 자리가 없어 전투 시작부터 영구로 준다.
    """
    registry = _fire("battle_start")
    assert registry.total_for("has_pierce", ALICE, now=0.0) == 1.0
    assert registry.total_for("has_pierce", ALICE, now=179.0) == 1.0
    assert registry.total_for("has_pierce", ALLY_HIGH, now=0.0) == 0.0


def test_wonderland_gives_her_charge_speed_and_atk_for_ten_seconds():
    registry = _fire("own_burst_activate")
    assert registry.total_for("charge_speed_percent", ALICE, now=0.0) == pytest.approx(0.8015)
    assert registry.total_for("atk_percent", ALICE, now=0.0) == pytest.approx(0.5512)
    assert registry.total_for("charge_speed_percent", ALLY_HIGH, now=0.0) == 0.0
    assert registry.total_for("atk_percent", ALLY_HIGH, now=0.0) == 0.0
    assert registry.total_for("charge_speed_percent", ALICE, now=10.1) == 0.0
    assert registry.total_for("atk_percent", ALICE, now=10.1) == 0.0
