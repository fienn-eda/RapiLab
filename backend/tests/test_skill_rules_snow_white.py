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
ALLY = {"slug": "ally", "element": "Fire"}


def make_context():
    return SquadContext([
        SquadMember("snow-white", burst_tier=3, element="Iron"),
        SquadMember("ally", burst_tier=1, element="Fire"),
    ])


def test_snow_white_rules_are_empty_burst_is_weapon_transform_only():
    # Burst is entirely the weapon-mode transform (Seven Dwarves: I) - no
    # buffs, no direct nuke.
    assert build_snow_white_rules(SNOW_WHITE_VALUES) == []


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
    assert pulses[0].full_burst_bonus_eligible is True
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
