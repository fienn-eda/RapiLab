"""Raven - Burst-3 Iron RL. Shock Wave lays a stacking 5s sustained DoT on every
Full Charge, driven off her own shot times; Single Point Attack is bracketed on
the boss's part_destructible flag rather than dropped."""
import pytest

from app.effects import EffectRegistry
from app.skill_rules.raven import (
    build_raven_rules,
    build_raven_scheduled_nukes,
    tempest_burst_percent,
)
from app.squad_engine import SquadContext, SquadMember, fire_trigger

SHOCK_WAVE = {
    "description_value_01": "68.46",  # sustained damage % per tick
    "description_value_02": "1",      # every 1 sec
    "description_value_03": "10",     # stacks up to 10
    "description_value_04": "5",      # lasts 5 sec
    "description_value_05": "47.52",  # FB self ATK, % of the user's ATK
    "description_value_06": "10",     # duration
}
BLUE_BLADE = {
    "description_value_01": "21.12",  # Vital Attack: Damage to Parts (deferred)
    "description_value_02": "5",
    "description_value_03": "21.12",  # Vital Attack on Full Burst (deferred)
    "description_value_04": "5",
    "description_value_05": "47.32",  # Single Point Attack: Sustained Damage %
    "description_value_06": "15",     # duration
}
TEMPEST = {
    "description_value_01": "492.3",  # burst nuke %
    "description_value_02": "89.44",  # A.N. Mode: self Sustained Damage %
    "description_value_03": "10",     # duration
}

CASTER_ATK = 60000.0
RAVEN = {"slug": "raven", "element": "Iron"}
VALUES = {
    "shock_wave": SHOCK_WAVE,
    "blue_blade": BLUE_BLADE,
    "tempest": TEMPEST,
    "caster_atk": CASTER_ATK,
}


class _Context:
    def __init__(self, shot_times=()):
        self.shot_times = {"raven": list(shot_times)}
        self.burst_times = {}


def test_burst_percent():
    assert tempest_burst_percent(VALUES) == pytest.approx(492.3)


def test_shock_wave_lays_five_ticks_per_full_charge():
    spec = build_raven_scheduled_nukes(VALUES)[0]
    assert spec["percent"] == pytest.approx(68.46)
    assert spec["damage_type"] == "sustained"
    ticks = spec["schedule"](_Context([1.0, 2.0]), 180.0)
    assert ticks == [2.0, 3.0, 4.0, 5.0, 6.0, 3.0, 4.0, 5.0, 6.0, 7.0]


def test_shock_wave_instances_overlap_rather_than_refresh():
    """Her RL fires every ~1s and each DoT lasts 5s, so several are always live -
    that stacking IS her damage, so the ticks must not collapse."""
    spec = build_raven_scheduled_nukes(VALUES)[0]
    ticks = spec["schedule"](_Context([1.0, 2.0, 3.0, 4.0, 5.0]), 180.0)
    assert ticks.count(6.0) == 5      # all five shots have a live tick at t=6


def test_shock_wave_is_silent_without_shot_times():
    spec = build_raven_scheduled_nukes(VALUES)[0]
    assert spec["schedule"](_Context([]), 180.0) == []


def _fire(trigger, part_destructible=False, time=0.0):
    ctx = SquadContext(
        [SquadMember("raven", burst_tier=3, element="Iron")],
        part_destructible=part_destructible,
    )
    registry = EffectRegistry()
    fire_trigger(trigger, {"raven": build_raven_rules(VALUES)}, ctx, registry, time=time)
    return registry


def test_full_burst_atk_is_scaled_off_the_casters_own_atk():
    registry = _fire("full_burst_enter")
    # 47.52% OF THE USER'S ATK: 0.4752 x 60000 = 28512 flat ATK, not a percent buff.
    assert registry.total_for("flat_atk", RAVEN, now=0.0) == pytest.approx(28512.0)
    assert registry.total_for("atk_percent", RAVEN, now=0.0) == 0.0
    assert registry.total_for("flat_atk", RAVEN, now=11.0) == 0.0   # 10s duration


def test_an_mode_grants_sustained_damage_on_her_burst():
    registry = _fire("own_burst_activate")
    assert registry.total_for("sustained_damage_up", RAVEN, now=0.0) == pytest.approx(0.8944)
    assert registry.total_for("sustained_damage_up", RAVEN, now=11.0) == 0.0


def test_single_point_attack_only_lands_on_the_ceiling_branch():
    """Bracketed like Ark Ranger Black: with no destructible parts it can never
    fire, with them it is treated as up from the start."""
    floor = _fire("battle_start", part_destructible=False)
    assert floor.total_for("sustained_damage_up", RAVEN, now=0.0) == 0.0

    ceiling = _fire("battle_start", part_destructible=True)
    assert ceiling.total_for("sustained_damage_up", RAVEN, now=0.0) == pytest.approx(0.4732)
