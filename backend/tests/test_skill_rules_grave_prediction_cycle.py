"""Grave's Prediction cycle: unlimited ammo, then the ammo dump, then a reload
that runs twice because Reload Ratio halves each load.

The in-game tooltip ("[방열 제거 조건]") gives Heat Emission TWO removal
conditions - a reload that reaches max ammo, or her burst - and the first fires
far earlier. So the squad buff hanging off Heat Emission lives for the double
reload, not until her next burst.
"""
import pytest

from app.attack_rate import rate_of_fire_for_weapon, reload_time_with_speed
from app.effects import EffectRegistry
from app.skill_rules.grave import (
    PREDICTION_DURATION,
    build_grave_rules,
    build_grave_weapon_mode_schedule,
    heat_emission_seconds,
    unlimited_ammo_percent,
)
from app.squad_engine import SquadContext, SquadMember, fire_trigger

SLUG = "grave"

# Read from assemble_skill_values at skill level 10.
HEAT_EMISSION = {
    "description_value_01": "100",
    "description_value_02": "50",
    "description_value_03": "2",
    "description_value_04": "38.96",
    "description_value_05": "48.4",
}
PLOT_SPOILER = {
    "description_value_01": "1",
    "description_value_02": "52.8",
    "description_value_03": "48.2",
    "description_value_04": "39.98",
    "description_value_05": "3",
    "description_value_06": "85.19",
}
# reload_time is 2.0, not her file's 1.0: CLIP_RELOAD_SPLITS["grave"] = 2 (her
# AR loads 60 rounds in halves) is already multiplied in by user_roster before
# a builder ever sees the dict. That is her WEAPON's standing behaviour; the
# skill's Reload Ratio is a separate, Heat-Emission-only halving on top.
VALUES = {
    "heat_emission": HEAT_EMISSION,
    "plot_spoiler": PLOT_SPOILER,
    "caster_weapon_stats": {"weapon": "AR", "reload_time": 2.0, "max_ammo": 60},
}


class _Context:
    def __init__(self, burst_times):
        self.burst_times = {SLUG: burst_times}


def test_heat_emission_lives_for_a_doubled_reload_not_until_her_next_burst():
    # THE point of the tooltip: condition 1 (a reload reaching max ammo) fires
    # long before condition 2 (her next burst, 40 sec away). Reload Ratio down
    # 50% halves what each load puts back, so it takes TWICE HER NORMAL reload
    # to reach max - and her normal one already includes the clip split.
    normal = reload_time_with_speed(2.0, 0.0)
    assert heat_emission_seconds(VALUES) == pytest.approx(2 * normal)
    assert heat_emission_seconds(VALUES) < PREDICTION_DURATION


def test_the_squad_pierce_buff_expires_with_heat_emission():
    registry = EffectRegistry()
    context = SquadContext([SquadMember(SLUG, 2, "Fire", "AR")])
    rules = {SLUG: build_grave_rules(VALUES)}

    fire_trigger("own_burst_activate", rules, context, registry, 0.0)
    # own_burst_fired_this_cycle() reads burst_used_this_cycle, which only
    # raid_simulator populates outside a test - set it the way the existing
    # Grave tests do (test_skill_rules_grave.py).
    context.burst_used_this_cycle.add(SLUG)
    fire_trigger("full_burst_end", rules, context, registry, PREDICTION_DURATION)

    target = {"slug": SLUG, "element": "Fire"}
    live = PREDICTION_DURATION + heat_emission_seconds(VALUES)
    assert registry.total_for("pierce_damage_up", target, live - 0.01) > 0.0
    assert registry.total_for("pierce_damage_up", target, live + 0.01) == pytest.approx(0.0)


def test_unlimited_ammo_covers_the_prediction_window_with_headroom():
    # 10 sec at an AR's 12/s is 120 rounds; the grant must cover that even
    # under heavy attack-speed buffs.
    percent = unlimited_ammo_percent(VALUES)
    rounds = 60 * (1 + percent)
    assert rounds >= PREDICTION_DURATION * rate_of_fire_for_weapon("AR") * 4


def test_the_forced_reload_segment_is_twice_a_normal_reload():
    schedule = build_grave_weapon_mode_schedule(VALUES)

    (segment,) = schedule(_Context([0.0]), 180.0)

    assert segment["start"] == pytest.approx(PREDICTION_DURATION)
    assert segment["end"] - segment["start"] == pytest.approx(2 * reload_time_with_speed(2.0, 0.0))
    assert 1.0 / segment["profile"]["rate_of_fire"] > segment["end"] - segment["start"]
    assert segment["profile"]["damage_percent"] == 0.0
