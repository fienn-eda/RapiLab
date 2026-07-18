"""Real max-level figures from lootandwaifus for Red Hood (slug "red-hood"),
slots numbered left-to-right per skill (full transcription, no skips).
"""
import pytest

from app.effects import EffectRegistry
from app.skill_rules.red_hood import (
    TRANSFORM_SHOTS,
    build_red_hood_rules,
    build_red_wolf_scheduled_nukes,
)
from app.squad_engine import SquadContext, SquadMember, fire_trigger

GLARING_EYES = {
    "description_value_01": "3.81",   # Charge Speed per stack %
    "description_value_02": "10",     # stack cap
    "description_value_03": "5",      # stack lifetime sec (refreshed per shot - never lapses)
    "description_value_04": "100",    # conversion threshold (excess over 100%)
    "description_value_05": "240",    # conversion rate (% of excess -> Charge Damage)
}
WILD_TOOTH = {
    "description_value_01": "50.68",  # Beast Cage squad DEF % of caster DEF (skipped)
    "description_value_02": "10",     # its duration
    "description_value_03": "23.04",  # Last Howl self heal % (skipped)
    "description_value_04": "10",     # its duration
    "description_value_05": "71.42",  # Red Wolf cast: self ATK %
    "description_value_06": "10",     # its duration
}
RED_WOLF = {
    "description_value_01": "1",      # "Step 1" label
    "description_value_02": "77.55",  # Beast Cage squad ATK % of caster ATK (unreachable: B3-pinned)
    "description_value_03": "10",     # its duration
    "description_value_04": "40",     # Step 1 burst CD reduction (unreachable)
    "description_value_05": "2",      # "Step 2" label
    "description_value_06": "10",     # taunt duration (unreachable)
    "description_value_07": "74.88",  # incoming healing % (unreachable)
    "description_value_08": "10",     # its duration
    "description_value_09": "40",     # Step 2 burst CD reduction (unreachable)
    "description_value_10": "3",      # "Step 3" label
    "description_value_11": "51.46",  # transformed weapon damage % of final ATK
    "description_value_12": "250",    # transformed Full Charge Damage %
    "description_value_13": "10",     # transform duration sec
    "description_value_14": "100",    # Pierce range expansion % (deferred)
    "description_value_15": "10",     # its duration
    "description_value_16": "100.8",  # Charge Speed % during transform
    "description_value_17": "10",     # its duration
}
RED_HOOD_VALUES = {
    "glaring_eyes": GLARING_EYES,
    "wild_tooth": WILD_TOOTH,
    "red_wolf": RED_WOLF,
}
RED_HOOD = {"slug": "red-hood", "element": "Iron"}
ALLY = {"slug": "ally", "element": "Fire"}


def make_context():
    return SquadContext([
        SquadMember("red-hood", burst_tier=3, element="Iron"),
        SquadMember("ally", burst_tier=1, element="Fire"),
    ])


def test_glaring_eyes_steady_state_charge_speed_is_continuous_self():
    ctx = make_context()
    registry = EffectRegistry()
    rules = {"red-hood": build_red_hood_rules(RED_HOOD_VALUES)}

    fire_trigger("battle_start", rules, ctx, registry, time=0.0)

    # 10 stacks x 3.81% held permanently (SR cadence never lets the 5s
    # lifetime lapse - Raven counter precedent).
    assert round(registry.total_for("charge_speed_percent", RED_HOOD, now=100.0), 4) == 0.381
    assert registry.total_for("charge_speed_percent", ALLY, now=100.0) == 0.0


def test_wild_tooth_red_wolf_cast_grants_self_atk():
    ctx = make_context()
    registry = EffectRegistry()
    rules = {"red-hood": build_red_hood_rules(RED_HOOD_VALUES)}

    fire_trigger("own_burst_activate", rules, ctx, registry, time=50.0)

    assert round(registry.total_for("atk_percent", RED_HOOD, now=50.0), 4) == 0.7142
    assert registry.total_for("atk_percent", RED_HOOD, now=60.1) == 0.0
    assert registry.total_for("atk_percent", ALLY, now=50.0) == 0.0


def test_red_wolf_schedules_33_transform_shots_per_own_burst_window():
    specs = build_red_wolf_scheduled_nukes(RED_HOOD_VALUES)
    assert len(specs) == 1
    spec = specs[0]
    assert spec.get("damage_type", "attack") == "attack"
    assert not spec.get("full_burst_bonus_eligible", False)

    ctx = make_context()
    ctx.record_burst_time("red-hood", 50.0)
    times = spec["schedule"](ctx, 180.0)

    assert len(times) == TRANSFORM_SHOTS == 33
    # evenly spaced across the 10s transform window, first hit one interval in
    interval = 10.0 / 33
    assert times[0] == pytest.approx(50.0 + interval)
    assert times[-1] == pytest.approx(60.0)
    assert all(
        b - a == pytest.approx(interval) for a, b in zip(times, times[1:])
    )


def test_red_wolf_hits_past_fight_end_are_dropped():
    specs = build_red_wolf_scheduled_nukes(RED_HOOD_VALUES)
    ctx = make_context()
    ctx.record_burst_time("red-hood", 175.0)
    times = specs[0]["schedule"](ctx, 180.0)
    assert times
    assert max(times) < 180.0
    assert len(times) < 33


def test_red_wolf_per_hit_percent_nets_out_the_overlapping_normal_shots():
    spec = build_red_wolf_scheduled_nukes(RED_HOOD_VALUES)[0]

    # Gross transform shot: 51.46% x (250% full charge + 93.36%p converted
    # charge damage) - the conversion is (38.1 + 100.8 - 100) x 240%.
    gross = 51.46 * (2.50 + (0.381 + 1.008 - 1.0) * 2.40)
    # Static overlap subtraction: the engine's weapon pass keeps emitting her
    # normal SR shots inside the window (charge 1.0s / +38.1% charge speed,
    # 6-round magazine, 2.0s reload, 69.04% x 2.5 per shot).
    effective_charge = 1.0 / 1.381
    magazine_cycle = 6 * effective_charge + 2.0
    overlap_shots = 10.0 * 6 / magazine_cycle
    overlap_damage = overlap_shots * 69.04 * 2.5
    expected = (33 * gross - overlap_damage) / 33

    assert spec["percent"] == pytest.approx(expected)
    assert spec["percent"] == pytest.approx(127.2, abs=0.1)
