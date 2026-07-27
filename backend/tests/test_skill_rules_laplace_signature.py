"""Laplace's signature-weapon (dollskills) build, slug "laplace-signature" - a
separate roster entry from base Laplace (slug "laplace"), per Fienn's decision
to model base/signature as distinct slugs (2026-07-12). Real max-level
dollskill figures from lootandwaifus, slots numbered left-to-right per skill.
"""
from types import SimpleNamespace

import pytest

from app.effects import EffectRegistry
from app.skill_rules.laplace_signature import (
    BUSTER_SHOTS,
    build_buster_scheduled_nukes,
    build_buster_weapon_mode_schedule,
    build_hero_bomber_signature_per_shot_rules,
    build_laplace_signature_rules,
    laplace_buster_signature_burst_percent,
)
from app.squad_engine import SquadContext, SquadMember

# Real skill level 10 values from lootandwaifus.com (dollskills / signature build).
HERO_VISION = {
    "description_value_01": "3.57",  # Explosion Radius % (deferred, inert stat)
    "description_value_02": "5",     # stacks up to (deferred, Pattern B counter)
    "description_value_03": "15",    # lasts sec (deferred)
}
HERO_BOMBER = {
    "description_value_01": "132.45",  # Full-Charge additional damage %
    "description_value_02": "14.78",   # deferred: parts-hit additional damage %
}
LAPLACE_BUSTER = {
    "description_value_01": "1455.72",  # First Damage % of final ATK (burst nuke)
    "description_value_02": "22.2",     # Normal Damage % per transform tick
    "description_value_03": "10",       # transform duration sec
    "description_value_04": "11.9",     # per-tick true-damage rider %
}
LAPLACE_SIGNATURE_VALUES = {
    "hero_vision": HERO_VISION,
    "hero_bomber": HERO_BOMBER,
    "laplace_buster": LAPLACE_BUSTER,
}


def make_context():
    return SquadContext([SquadMember("laplace-signature", burst_tier=3, element="Iron")])


def test_buster_shots_is_93():
    assert BUSTER_SHOTS == 93


def test_burst_percent_is_first_damage():
    assert laplace_buster_signature_burst_percent(LAPLACE_SIGNATURE_VALUES) == 1455.72


def test_build_laplace_signature_rules_grants_only_the_transforms_pierce():
    # No ally buffs - all DPS lives in the burst nuke, the weapon-mode segment,
    # and the scheduled-nuke rider. The one self effect is Laplace Buster's
    # "Additional Effect 1: Gains Pierce", for the transform's own duration.
    rule, = build_laplace_signature_rules(LAPLACE_SIGNATURE_VALUES)
    assert rule.trigger == "own_burst_activate"


def test_hero_bomber_fires_every_full_charge_outside_full_burst():
    rules = build_hero_bomber_signature_per_shot_rules(LAPLACE_SIGNATURE_VALUES)
    assert len(rules) == 1
    threshold, mode, subrules = rules[0]
    assert (threshold, mode) == (1, "every_outside_full_burst")

    registry = EffectRegistry()
    subrules[0].action(make_context(), "laplace-signature", 5.0, registry)
    pulses = registry.drain_pulses("instant_damage_percent")
    assert len(pulses) == 1
    assert pulses[0].value == 132.45


def test_buster_weapon_mode_schedule_shape():
    schedule = build_buster_weapon_mode_schedule(LAPLACE_SIGNATURE_VALUES)
    context = SimpleNamespace(burst_times={"laplace-signature": [20.0]})
    segments = schedule(context, 180.0)
    assert segments == [{
        "start": 20.0,
        "until_shots": 93,
        "profile": {
            "weapon": "RL",
            "damage_percent": 22.2,
            "rate_of_fire": pytest.approx(9.3),
            "damage_type": "true",
        },
    }]


def test_buster_weapon_mode_schedule_one_segment_per_own_burst():
    schedule = build_buster_weapon_mode_schedule(LAPLACE_SIGNATURE_VALUES)
    context = SimpleNamespace(burst_times={"laplace-signature": [20.0, 60.0, 100.0]})
    segments = schedule(context, 180.0)
    assert [seg["start"] for seg in segments] == [20.0, 60.0, 100.0]
    assert all(seg["until_shots"] == 93 for seg in segments)


def test_buster_scheduled_nukes_spec_shape():
    spec = build_buster_scheduled_nukes(LAPLACE_SIGNATURE_VALUES)[0]
    assert spec["percent"] == pytest.approx(11.9)
    assert spec["damage_type"] == "true"


def test_buster_scheduled_nukes_produce_93_ticks_per_window():
    # interval = duration / BUSTER_SHOTS = 10 / 93; the same cadence the
    # weapon-mode segment's ticks land on, so the rider never drifts.
    spec = build_buster_scheduled_nukes(LAPLACE_SIGNATURE_VALUES)[0]
    context = SimpleNamespace(burst_times={"laplace-signature": [20.0]})
    times = spec["schedule"](context, 180.0)
    assert len(times) == 93
    assert times[0] == pytest.approx(20.0 + 10.0 / 93)
    assert times[-1] == pytest.approx(30.0)  # 20 + 93 * (10/93)


def test_buster_scheduled_nukes_drop_ticks_past_fight_duration():
    spec = build_buster_scheduled_nukes(LAPLACE_SIGNATURE_VALUES)[0]
    context = SimpleNamespace(burst_times={"laplace-signature": [20.0]})
    times = spec["schedule"](context, 25.0)
    assert all(t < 25.0 for t in times)
    assert len(times) == 46  # k=1..46: 20 + k*10/93 < 25


def test_buster_scheduled_nukes_one_window_per_own_burst():
    spec = build_buster_scheduled_nukes(LAPLACE_SIGNATURE_VALUES)[0]
    context = SimpleNamespace(burst_times={"laplace-signature": [20.0, 60.0]})
    times = spec["schedule"](context, 180.0)
    assert len(times) == 186  # 93 per window, two windows


# HERO_VISION, HERO_BOMBER, LAPLACE_BUSTER above double as the module-level
# fixtures the assembly verification harness (test_skill_value_assembly.py)
# resolves by key.upper() - no separate aliases needed.
