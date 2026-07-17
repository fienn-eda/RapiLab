"""Raven - Burst-3 Iron RL. Shock Wave lays a stacking 5s sustained DoT on every
Full Charge, driven off her own shot times; Single Point Attack is bracketed on
the boss's part_destructible flag rather than dropped."""
import pytest

from app.effects import EffectRegistry
from app.skill_rules.raven import (
    _stack_counts,
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


def test_each_full_charge_adds_one_stack():
    # Fienn 2026-07-17: 1st Full Charge -> 1 stack, 2nd -> 2, ... 10th -> 10.
    assert _stack_counts([1.0, 2.0, 3.0]) == [1, 2, 3]


def test_stacks_stop_at_the_cap():
    shots = [float(n) for n in range(1, 15)]
    assert _stack_counts(shots)[-4:] == [10, 10, 10, 10]


def test_a_full_charge_inside_the_window_refreshes_the_whole_counter():
    """"Lasts for 5 sec" is the counter's life, refreshed by each Full Charge -
    not a per-stack expiry (Fienn 2026-07-17). Firing at 4s intervals keeps
    stacking even though every stack is older than 5s."""
    assert _stack_counts([0.0, 4.0, 8.0, 12.0]) == [1, 2, 3, 4]


def test_the_counter_resets_after_a_gap_longer_than_the_window():
    assert _stack_counts([0.0, 1.0, 2.0, 20.0, 21.0]) == [1, 2, 3, 1, 2]


def test_shock_wave_ticks_once_per_second_per_live_stack():
    spec = build_raven_scheduled_nukes(VALUES)[0]
    assert spec["percent"] == pytest.approx(68.46)
    assert spec["damage_type"] == "sustained"
    # Shots at t=1,2,3 -> counter alive from t=1, ticking every 1s; each tick
    # lands one 68.46% hit PER live stack, so the tick time repeats.
    ticks = spec["schedule"](_Context([1.0, 2.0, 3.0]), 9.0)
    assert ticks.count(2.0) == 2   # two stacks at t=2
    assert ticks.count(3.0) == 3   # three at t=3
    assert ticks.count(4.0) == 3   # no more shots, but the counter holds
    assert ticks.count(8.0) == 3   # alive until 3.0 + 5s
    assert ticks.count(9.0) == 0   # expired, and past fight_duration anyway


def test_shock_wave_is_silent_without_shot_times():
    spec = build_raven_scheduled_nukes(VALUES)[0]
    assert spec["schedule"](_Context([]), 180.0) == []


def test_her_real_cadence_never_lets_the_counter_expire():
    """Her RL takes 1s per Full Charge and its longest gap is the 3s reload -
    inside the 5s window, so she reaches 10 stacks and holds them all fight.
    This is why the cap matters and a steady-state guess would not."""
    shots = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 9.0, 10.0, 11.0, 12.0, 13.0, 14.0, 17.0]
    counts = _stack_counts(shots)
    assert counts == [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 10, 10, 10]
    assert 1 not in counts[1:]     # never resets


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
