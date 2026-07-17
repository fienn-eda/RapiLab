"""Sakura: Bloom in Summer - Burst-3 Wind AR. Bloom force-fires Full Glory at
battle start, so Sakura Petals' DoT runs on a schedule fixed before the fight
(t=0, 30, 60, ...) rather than the usual first-fire-at-cooldown."""
import pytest

from app.skill_rules.sakura_bloom_in_summer import (
    FULL_GLORY_COOLDOWN,
    _full_glory_times,
    build_sakura_bloom_in_summer_rules,
    build_sakura_periodic_rules,
    build_sakura_resource_scaled_nukes,
    build_sakura_scheduled_nukes,
    ephemeral_spender_burst_hit_count,
    ephemeral_spender_burst_percent,
)

BLOOM = {
    "description_value_01": "5.1",    # part-destroy Sustained Damage % (deferred)
    "description_value_02": "30",     # duration
    "description_value_03": "10.02",  # Dancing Flower Duration + (deferred)
    "description_value_04": "10.02",  # Sakura Petals Duration + (deferred)
}
FULL_GLORY = {
    "description_value_01": "15.64",  # Dancing Flower: self Attack Damage %
    "description_value_02": "15",     # duration
    "description_value_03": "256",    # Sakura Petals sustained damage %
    "description_value_04": "1",      # every 1 sec
    "description_value_05": "15",     # for 15 sec
}
EPHEMERAL_SPENDER = {
    "description_value_01": "457.14",  # burst nuke %
    "description_value_02": "10",      # attacks sequentially 10 times
    "description_value_03": "35.16",   # DoT % per stack
    "description_value_04": "1",       # every 1 sec
    "description_value_05": "10",      # stacks up to 10
    "description_value_06": "10",      # lasts 10 sec
}

VALUES = {
    "bloom": BLOOM,
    "full_glory": FULL_GLORY,
    "ephemeral_spender": EPHEMERAL_SPENDER,
}


class _Context:
    burst_times = {}
    shot_times = {}


def test_full_glory_starts_at_battle_start_not_at_its_cooldown():
    # Bloom's "Forcefully uses Skill 2" is why t=0 is in here at all.
    assert _full_glory_times(180.0) == [0.0, 30.0, 60.0, 90.0, 120.0, 150.0]


def test_dancing_flower_is_granted_at_battle_start_and_every_cooldown():
    battle = build_sakura_bloom_in_summer_rules(VALUES)
    assert len(battle) == 1
    assert battle[0].trigger == "battle_start"

    periodic = build_sakura_periodic_rules(VALUES)
    assert len(periodic) == 1
    cooldown, rules = periodic[0]
    assert cooldown == FULL_GLORY_COOLDOWN
    assert rules[0].trigger == "periodic"


def test_sakura_petals_ticks_fifteen_times_per_full_glory():
    spec = build_sakura_scheduled_nukes(VALUES)[0]
    assert spec["percent"] == pytest.approx(256.0)
    assert spec["damage_type"] == "sustained"
    ticks = spec["schedule"](_Context(), 180.0)
    # 6 casts x 15 ticks, the first at t=1 (one interval after the t=0 cast).
    assert len(ticks) == 6 * 15
    assert ticks[:3] == [1.0, 2.0, 3.0]
    assert ticks[14] == 15.0          # last tick of the first cast
    assert ticks[15] == 31.0          # first tick of the second cast


def test_sakura_petals_does_not_read_the_context():
    # The schedule is fixed by Full Glory's cooldown alone, so an empty context
    # is enough - unlike Ein's feathers, nothing here depends on the deck.
    spec = build_sakura_scheduled_nukes(VALUES)[0]
    ticks = spec["schedule"](_Context(), 40.0)
    # Casts at t=0 and t=30 only; trimming ticks past the fight's end is the
    # engine's job (see test_scheduled_nukes), not the schedule's.
    assert ticks == [float(n) for n in range(1, 16)] + [30.0 + n for n in range(1, 16)]


def test_burst_is_ten_separate_hits():
    assert ephemeral_spender_burst_percent(VALUES) == pytest.approx(457.14)
    assert ephemeral_spender_burst_hit_count(VALUES) == 10


def test_burst_dot_runs_at_all_ten_stacks_at_once():
    """The burst's 10 sequential hits each lay a stack (Fienn 2026-07-17), so the
    DoT ticks at 10x the per-stack percent rather than ramping up."""
    spec = build_sakura_resource_scaled_nukes(VALUES)[0]
    assert spec["base_percent"] == pytest.approx(351.6)   # 35.16 x 10 stacks
    assert spec["tick_count"] == 10
    assert spec["tick_interval"] == pytest.approx(1.0)
    assert spec["damage_type"] == "sustained"
    assert "resource" not in spec      # the stack count never varies
