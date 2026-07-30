"""`scheduled_nukes` schedules that derive from the owner's OWN shot timeline.

Ein's feathers only needed her burst times, but damage hung off a unit's firing
(Raven's Shock Wave: a 5s sustained DoT per Full Charge) needs the shot times
the engine already generates. They ride on the context, so the schedule callable
keeps its (context, fight_duration) signature.
"""

import pytest
from app.raid_simulator import simulate_raid

WEAPON = {"weapon": "RL", "damage_percent": 61.3, "max_ammo": 6,
          "reload_time": 2.0, "charge_time": 1.0, "charge_damage_percent": 250.0}


def _deck():
    return [
        {"slug": "b1", "burst_tier": 1, "element": "Fire", "cooldown": 15.0},
        {"slug": "b2", "burst_tier": 2, "element": "Fire", "cooldown": 15.0},
        {"slug": "b3", "burst_tier": 3, "element": "Fire", "cooldown": 15.0},
    ]


def _run(scheduled_nukes=None, weapon_stats=None, fight_duration=20.0):
    deck = _deck()
    return simulate_raid(
        deck=deck,
        rules_by_slug={m["slug"]: [] for m in deck},
        burst_damage_percents={},
        base_stats={m["slug"]: {"atk": 10000} for m in deck},
        enemy_def=0,
        gauge_charge_time=5.0,
        fight_duration=fight_duration,
        base_crit_rate=0.0,
        weapon_stats=weapon_stats or {},
        scheduled_nukes=scheduled_nukes,
    )


def test_schedule_sees_the_owners_shot_times():
    seen = {}

    def schedule(context, fight_duration):
        seen["times"] = list(context.shot_times.get("b3", []))
        return []

    _run({"b3": [{"schedule": schedule, "percent": 100.0}]}, weapon_stats={"b3": WEAPON})
    # RL: 1s charge per shot, 6-round magazine, 2s file reload (2.148 with the
    # fixed segment), so the seventh shot lands at 6 + 2.148 + 1.
    assert seen["times"][:7] == pytest.approx(
        [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 9.148])


def test_shot_times_are_empty_for_a_unit_without_weapon_stats():
    seen = {}

    def schedule(context, fight_duration):
        seen["times"] = list(context.shot_times.get("b3", []))
        return []

    _run({"b3": [{"schedule": schedule, "percent": 100.0}]}, weapon_stats={})
    assert seen["times"] == []


def test_a_per_shot_dot_can_be_built_from_the_shot_times():
    """Raven's shape: every Full Charge starts a 5-tick, 1s-interval DoT."""
    def schedule(context, fight_duration):
        ticks = []
        for shot in context.shot_times.get("b3", []):
            ticks.extend(shot + n for n in range(1, 6))
        return ticks

    result = _run(
        {"b3": [{"schedule": schedule, "percent": 50.0, "damage_type": "sustained"}]},
        weapon_stats={"b3": WEAPON},
    )
    ticks = sorted(e["time"] for e in result["damage_log"] if e["source"] == "scheduled")
    # Every shot contributes five ticks, minus any pushed past the fight's end.
    # They deliberately OVERLAP - concurrent ticks at one instant are what
    # "stacks up to 10 times" means.
    shots = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0,
             9.148, 10.148, 11.148, 12.148, 13.148, 14.148,
             17.296, 18.296, 19.296]
    expected = [s + n for s in shots for n in range(1, 6) if s + n < 20.0]
    assert ticks == pytest.approx(sorted(expected))
    # t=6 sits under five live DoTs at once (from the shots at t=1..5).
    assert ticks.count(6.0) == 5
