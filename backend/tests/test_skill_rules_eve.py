"""EVE's rules, against her real max-level skill values.

Slot numbering follows the assembly harness (`extract_lootandwaifus_slots`)
with the manifest's `drop_tokens` applied - Counter Chain's three "Mk2" tokens
are dropped, which is what makes slots 04/05 the two "scaled by 100%" clauses
rather than the literal 2s in the skill names.
"""
import pytest

from app.effects import EffectRegistry
from app.skill_rules.eve import (
    COUNTER_CHAIN_HIT_COUNT,
    build_eve_rules,
    build_unstable_energy_per_shot_rules,
    counter_chain_burst_percent,
)
from app.squad_engine import SquadContext, SquadMember, fire_trigger

# "Critical Rate 60%", "44 critical hits", "240% of final ATK", "3 time(s)",
# "Damage Taken 10%", "for 10 sec"
IMPACT_EXOSPINE = {
    "description_value_01": "60",
    "description_value_02": "44",
    "description_value_03": "240",
    "description_value_04": "3",
    "description_value_05": "10",
    "description_value_06": "10",
}
# "ATK 50% of the skill user's ATK", "Max Ammunition Capacity 25%",
# "10 normal attack(s)", "Reloads 3 round(s)"
EAGLE_EYE_EXOSPINE = {
    "description_value_01": "50",
    "description_value_02": "25",
    "description_value_03": "10",
    "description_value_04": "3",
}
# After drop_tokens [2, 4, 6]: "457.14%", "6 time(s)", "Duration: 10 sec",
# Unstable Energy "scaled by 100%", Eagle Eye "scaled by 100%"
COUNTER_CHAIN = {
    "description_value_01": "457.14",
    "description_value_02": "6",
    "description_value_03": "10",
    "description_value_04": "100",
    "description_value_05": "100",
}

CASTER_ATK = 400000.0

VALUES = {
    "impact_exospine": IMPACT_EXOSPINE,
    "eagle_eye_exospine": EAGLE_EYE_EXOSPINE,
    "counter_chain": COUNTER_CHAIN,
    "caster_atk": CASTER_ATK,
}

SLUG = "eve"


def _context(boss_element=None, burst_times=None):
    context = SquadContext(
        [SquadMember(SLUG, 3, "Iron", "AR")], boss_element=boss_element
    )
    context.burst_times = {SLUG: burst_times or []}
    return context


def _fire(rules, trigger, time=0.0, boss_element=None, burst_times=None):
    registry = EffectRegistry()
    context = _context(boss_element, burst_times)
    fire_trigger(trigger, {SLUG: rules}, context, registry, time)
    return registry


def test_battle_start_grants_the_two_permanent_exospine_buffs():
    registry = _fire(build_eve_rules(VALUES), "battle_start")

    assert registry.total_for("crit_rate", {"slug": SLUG}, 0.0) == pytest.approx(0.60)
    assert registry.total_for("max_ammo_percent", {"slug": SLUG}, 0.0) == pytest.approx(0.25)
    # Eagle Eye: flat ATK = 50% of her own ATK
    assert registry.total_for("flat_atk", {"slug": SLUG}, 0.0) == pytest.approx(200000.0)


def test_battle_start_buffs_are_permanent():
    registry = _fire(build_eve_rules(VALUES), "battle_start")

    assert registry.total_for("crit_rate", {"slug": SLUG}, 170.0) == pytest.approx(0.60)


def test_mk2_raises_eagle_eyes_atk_multiplier_to_100_percent_for_10_sec():
    rules = build_eve_rules(VALUES)
    registry = _fire(rules, "battle_start")
    fire_trigger("own_burst_activate", {SLUG: rules}, _context(), registry, 20.0)

    # 50% permanent + 50% Mk2 = 100% of her own ATK while the window is open
    assert registry.total_for("flat_atk", {"slug": SLUG}, 25.0) == pytest.approx(400000.0)
    # ...and back to the permanent half once it expires
    assert registry.total_for("flat_atk", {"slug": SLUG}, 30.5) == pytest.approx(200000.0)


def test_unstable_energy_rides_the_expected_crit_counter():
    (threshold, mode, rules), = build_unstable_energy_per_shot_rules(VALUES)

    assert mode == "every_n_critical_hits"
    assert threshold == pytest.approx(44.0)
    assert len(rules) == 1


def test_unstable_energy_emits_three_separate_hits():
    (_threshold, _mode, rules), = build_unstable_energy_per_shot_rules(VALUES)
    registry = _fire(rules, "per_shot", time=30.0)

    pulses = registry.drain_pulses("instant_damage_percent")
    assert [p.value for p in pulses] == [pytest.approx(240.0)] * 3
    # "as damage", not "as additional damage"
    assert not any(p.full_burst_bonus_eligible for p in pulses)


def test_unstable_energy_doubles_inside_the_mk2_window():
    (_threshold, _mode, rules), = build_unstable_energy_per_shot_rules(VALUES)
    registry = _fire(rules, "per_shot", time=22.0, burst_times=[20.0])

    pulses = registry.drain_pulses("instant_damage_percent")
    assert [p.value for p in pulses] == [pytest.approx(480.0)] * 3


def test_unstable_energy_is_back_to_base_after_the_mk2_window():
    (_threshold, _mode, rules), = build_unstable_energy_per_shot_rules(VALUES)
    registry = _fire(rules, "per_shot", time=30.5, burst_times=[20.0])

    pulses = registry.drain_pulses("instant_damage_percent")
    assert [p.value for p in pulses] == [pytest.approx(240.0)] * 3


def test_electric_rider_applies_only_against_an_electric_boss():
    (_threshold, _mode, rules), = build_unstable_energy_per_shot_rules(VALUES)

    electric = _fire(rules, "per_shot", time=30.0, boss_element="Electric")
    assert electric.total_for("damage_taken_up", {"slug": SLUG}, 35.0) == pytest.approx(0.10)

    iron = _fire(rules, "per_shot", time=30.0, boss_element="Iron")
    assert iron.total_for("damage_taken_up", {"slug": SLUG}, 35.0) == pytest.approx(0.0)


def test_electric_rider_expires_after_ten_seconds():
    (_threshold, _mode, rules), = build_unstable_energy_per_shot_rules(VALUES)
    registry = _fire(rules, "per_shot", time=30.0, boss_element="Electric")

    assert registry.total_for("damage_taken_up", {"slug": SLUG}, 40.5) == pytest.approx(0.0)


def test_counter_chain_burst_is_six_sequential_hits():
    assert counter_chain_burst_percent(VALUES) == pytest.approx(457.14)
    assert COUNTER_CHAIN_HIT_COUNT == 6
