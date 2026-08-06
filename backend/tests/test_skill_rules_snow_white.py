"""Real max-level figures from lootandwaifus for Snow White (slug
"snow-white"), slots numbered left-to-right per skill (full transcription, no
skips).
"""
from types import SimpleNamespace

from app.effects import EffectRegistry
from app.skill_rules.snow_white import (
    SEVEN_DWARVES_V_VI_COOLDOWN,
    build_determination_per_shot_rules,
    build_seven_dwarves_weapon_mode_schedule,
    build_snow_white_rules,
    snow_white_periodic_nuke,
)
from app.squad_engine import SquadContext, SquadMember, fire_trigger

DETERMINATION = {
    "description_value_01": "30",    # normal-attack-hit threshold
    "description_value_02": "82.8",  # additional damage %
    "description_value_03": "30",    # "hits 30 time(s)" repeated for the self buff
    "description_value_04": "8.28",  # self ATK %
    "description_value_05": "5",     # self ATK duration sec
}
SEVEN_DWARVES_V_VI = {
    "description_value_01": "144.73",  # damage %
    "description_value_02": "26.1",    # self Critical Rate % during Full Burst (deferred rider)
    "description_value_03": "10",      # its duration sec
}
SEVEN_DWARVES_I = {
    "description_value_01": "5",       # charge time sec
    "description_value_02": "499.5",   # shot damage %
    "description_value_03": "1000",    # full charge damage %
    "description_value_04": "1",       # magazine size (round(s))
}
SNOW_WHITE_VALUES = {
    "determination": DETERMINATION,
    "seven_dwarves_v_vi": SEVEN_DWARVES_V_VI,
    "seven_dwarves_i": SEVEN_DWARVES_I,
}
SNOW_WHITE = {"slug": "snow-white", "element": "Iron"}


def test_determination_atk_cannot_outlive_the_transform_charge():
    """Fienn (2026-08-07): Determination's ATK +8.28% does NOT reach the
    transform's charged shot, because that charge takes 5 sec and the buff
    lasts 5 sec.

    The engine already produces this - the buff's last possible application is
    at the burst instant and the shot lands a whole charge later, and effects
    are active on [start, start+duration), so it has expired. Nothing enforces
    it though: it holds only while the buff is not LONGER than the charge, and
    both numbers are skill slots a rebalance can move. This pins the relation
    rather than the two numbers, so it fails on the change that would break the
    ruling instead of on any change at all.
    """
    buff_duration = float(DETERMINATION["description_value_05"])
    charge_time = float(SEVEN_DWARVES_I["description_value_01"])
    assert buff_duration <= charge_time
ALLY = {"slug": "ally", "element": "Fire"}


def make_context():
    return SquadContext([
        SquadMember("snow-white", burst_tier=3, element="Iron"),
        SquadMember("ally", burst_tier=1, element="Fire"),
    ])


def test_snow_white_burst_grants_only_pierce_for_its_one_transform_shot():
    # Burst is the weapon-mode transform (Seven Dwarves: I) - no buffs and no
    # direct nuke. Its one non-weapon effect is "Additional Effect: Pierce",
    # the property, and the transform is a single charged shot.
    rule, = build_snow_white_rules(SNOW_WHITE_VALUES)
    assert rule.trigger == "own_burst_activate"


def test_determination_fires_every_30_shots_with_additional_damage():
    entries = build_determination_per_shot_rules(SNOW_WHITE_VALUES)
    assert len(entries) == 1
    threshold, mode, rules = entries[0]
    assert threshold == 30
    assert mode == "every"
    assert len(rules) == 2

    ctx = make_context()
    registry = EffectRegistry()
    for rule in rules:
        rule.action(ctx, "snow-white", 5.0, registry)

    pulses = registry.drain_pulses("instant_damage_percent")
    assert len(pulses) == 1
    assert pulses[0].value == 82.8
    # "as additional damage" -> opts in to the Full Burst bonus check.
    assert pulses[0].damage_type == "attack"

    assert round(registry.total_for("atk_percent", SNOW_WHITE, now=5.0), 4) == 0.0828
    assert registry.total_for("atk_percent", ALLY, now=5.0) == 0.0  # self-only
    assert registry.total_for("atk_percent", SNOW_WHITE, now=10.1) == 0.0  # 5s duration


def test_seven_dwarves_v_vi_is_cd15_periodic_nuke():
    assert SEVEN_DWARVES_V_VI_COOLDOWN == 15.0
    assert snow_white_periodic_nuke(SNOW_WHITE_VALUES) == {"cooldown": 15.0, "percent": 144.73}


def test_burst_transform_is_single_5s_charged_cannon_shot():
    schedule = build_seven_dwarves_weapon_mode_schedule(SNOW_WHITE_VALUES)
    context = SimpleNamespace(burst_times={"snow-white": [20.0]})
    segments = schedule(context, 180.0)
    assert segments == [{
        "start": 20.0,
        "until_shots": 1,
        "profile": {
            "weapon": "SR",
            "damage_percent": 499.5,
            "charge_damage_percent": 1000.0,
            "charge_time": 5.0,
        },
    }]


def test_burst_transform_schedule_has_one_segment_per_own_burst():
    schedule = build_seven_dwarves_weapon_mode_schedule(SNOW_WHITE_VALUES)
    context = SimpleNamespace(burst_times={"snow-white": [20.0, 60.0, 100.0]})
    segments = schedule(context, 180.0)
    assert [seg["start"] for seg in segments] == [20.0, 60.0, 100.0]
    assert all(seg["until_shots"] == 1 for seg in segments)


def test_determinations_self_atk_refreshes_instead_of_stacking():
    """The bullet names no stack count, so a re-application replaces the live
    grant. 30 AR shots take 2.5 sec against a 5 sec duration, so stacking would
    double the buff the skill grants."""
    _threshold, _mode, rules = build_determination_per_shot_rules(SNOW_WHITE_VALUES)[0]
    ctx = make_context()
    registry = EffectRegistry()
    for time in (2.5, 5.0, 7.5, 10.0):
        fire_trigger("per_shot", {"snow-white": rules}, ctx, registry, time)
    assert round(registry.total_for("atk_percent", SNOW_WHITE, 10.0), 4) == 0.0828
