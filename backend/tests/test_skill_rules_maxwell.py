"""Real max-level figures from lootandwaifus for Maxwell (slug "maxwell"),
slots numbered left-to-right per skill (full transcription, no skips -
"2 allies" in Straight Shot's text counts as its own leading token).
"""
from types import SimpleNamespace

from app.effects import EffectRegistry
from app.skill_rules.maxwell import (
    build_maxwell_rules,
    build_pierce_shot_weapon_mode_schedule,
)
from app.squad_engine import SquadContext, SquadMember, fire_trigger

STRAIGHT_SHOT = {
    "description_value_01": "2",     # allies affected (incl. caster - Fienn 2026-07-19)
    "description_value_02": "4.48",  # Charge Speed %
    "description_value_03": "10",    # its duration sec
    "description_value_04": "43.1",  # ATK %
    "description_value_05": "10",    # its duration sec
}
PIERCE_SHOT = {
    "description_value_01": "2",       # charge time sec
    "description_value_02": "813.42",  # shot damage %
    "description_value_03": "300",     # full charge damage %
    "description_value_04": "1",       # magazine size round(s)
}
MAXWELL_VALUES = {
    "straight_shot": STRAIGHT_SHOT,
    "pierce_shot": PIERCE_SHOT,
}
MAXWELL = {"slug": "maxwell", "element": "Iron"}
ALLY_HIGH = {"slug": "ally-high", "element": "Fire"}
ALLY_LOW = {"slug": "ally-low", "element": "Wind"}


def make_context(base_atk):
    return SquadContext(
        [
            SquadMember("maxwell", burst_tier=3, element="Iron"),
            SquadMember("ally-high", burst_tier=1, element="Fire"),
            SquadMember("ally-low", burst_tier=2, element="Wind"),
        ],
        base_atk=base_atk,
    )


def test_straight_shot_rule_is_single_full_burst_enter_rule():
    rules = build_maxwell_rules(MAXWELL_VALUES)
    assert len(rules) == 1
    assert rules[0].trigger == "full_burst_enter"


def test_straight_shot_buffs_maxwell_when_she_ranks_top_2_including_herself():
    # maxwell (10000) ranks 2nd, ally-high (20000) 1st, ally-low (100) 3rd -
    # maxwell must be INCLUDED in the top-2 scope, unlike the shared
    # top_atk_slugs helper which would exclude the caster entirely.
    ctx = make_context({"maxwell": 10000.0, "ally-high": 20000.0, "ally-low": 100.0})
    registry = EffectRegistry()
    rules = {"maxwell": build_maxwell_rules(MAXWELL_VALUES)}

    fire_trigger("full_burst_enter", rules, ctx, registry, time=5.0)

    assert round(registry.total_for("atk_percent", MAXWELL, now=5.0), 4) == 0.431
    assert round(registry.total_for("charge_speed_percent", MAXWELL, now=5.0), 4) == 0.0448
    assert round(registry.total_for("atk_percent", ALLY_HIGH, now=5.0), 4) == 0.431
    # ally-low is 3rd - excluded from the top 2
    assert registry.total_for("atk_percent", ALLY_LOW, now=5.0) == 0.0
    # 10s duration
    assert registry.total_for("atk_percent", MAXWELL, now=15.1) == 0.0


def test_straight_shot_excludes_maxwell_when_two_allies_outrank_her():
    ctx = make_context({"maxwell": 100.0, "ally-high": 20000.0, "ally-low": 10000.0})
    registry = EffectRegistry()
    rules = {"maxwell": build_maxwell_rules(MAXWELL_VALUES)}

    fire_trigger("full_burst_enter", rules, ctx, registry, time=5.0)

    assert registry.total_for("atk_percent", MAXWELL, now=5.0) == 0.0
    assert round(registry.total_for("atk_percent", ALLY_HIGH, now=5.0), 4) == 0.431
    assert round(registry.total_for("atk_percent", ALLY_LOW, now=5.0), 4) == 0.431


def test_burst_transform_is_single_2s_charged_cannon_shot():
    schedule = build_pierce_shot_weapon_mode_schedule(MAXWELL_VALUES)
    context = SimpleNamespace(burst_times={"maxwell": [20.0]})
    segments = schedule(context, 180.0)
    assert segments == [{
        "start": 20.0,
        "until_shots": 1,
        "profile": {
            "weapon": "SR",
            "damage_percent": 813.42,
            "charge_damage_percent": 300.0,
            "charge_time": 2.0,
        },
    }]


def test_burst_transform_schedule_has_one_segment_per_own_burst():
    schedule = build_pierce_shot_weapon_mode_schedule(MAXWELL_VALUES)
    context = SimpleNamespace(burst_times={"maxwell": [20.0, 60.0, 100.0]})
    segments = schedule(context, 180.0)
    assert [seg["start"] for seg in segments] == [20.0, 60.0, 100.0]
    assert all(seg["until_shots"] == 1 for seg in segments)
