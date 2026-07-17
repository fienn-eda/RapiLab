"""`scheduled_nukes`: damage fired at an arbitrary, unit-computed schedule.

`periodic_nukes` covers a FIXED interval. Summoned-entity units need a schedule
whose cadence CHANGES over the fight - Ein's Near Feathers attack faster the
more of them are alive, and how many are alive depends on her burst times and
per-feather lifetimes. The times are still fully deterministic, so the unit
module precomputes them from the context and the engine just emits them.
"""
from app.raid_simulator import simulate_raid


def _deck():
    return [
        {"slug": "b1", "burst_tier": 1, "element": "Fire", "cooldown": 15.0},
        {"slug": "b2", "burst_tier": 2, "element": "Fire", "cooldown": 15.0},
        {"slug": "b3", "burst_tier": 3, "element": "Fire", "cooldown": 15.0},
    ]


def _run(scheduled_nukes=None, enemy_def=0, fight_duration=30.0):
    deck = _deck()
    return simulate_raid(
        deck=deck,
        rules_by_slug={m["slug"]: [] for m in deck},
        burst_damage_percents={},
        base_stats={m["slug"]: {"atk": 10000} for m in deck},
        enemy_def=enemy_def,
        gauge_charge_time=5.0,
        fight_duration=fight_duration,
        base_crit_rate=0.0,
        scheduled_nukes=scheduled_nukes,
    )


def _scheduled(result):
    return [e for e in result["damage_log"] if e["source"] == "scheduled"]


def test_emits_one_hit_at_each_scheduled_time():
    result = _run({"b3": [{"schedule": lambda ctx, dur: [1.0, 2.5, 7.25], "percent": 100.0}]})
    assert [e["time"] for e in _scheduled(result)] == [1.0, 2.5, 7.25]


def test_schedule_receives_context_burst_times_and_fight_duration():
    seen = {}

    def schedule(context, fight_duration):
        seen["bursts"] = list(context.burst_times.get("b3", []))
        seen["duration"] = fight_duration
        return [t + 0.5 for t in seen["bursts"]]

    result = _run({"b3": [{"schedule": schedule, "percent": 100.0}]})
    assert seen["duration"] == 30.0
    assert seen["bursts"], "schedule must see the owner's burst times"
    assert [e["time"] for e in _scheduled(result)] == [t + 0.5 for t in seen["bursts"]]


def test_times_at_or_past_fight_duration_are_dropped():
    result = _run(
        {"b3": [{"schedule": lambda ctx, dur: [5.0, 29.99, 30.0, 45.0], "percent": 100.0}]},
        fight_duration=30.0,
    )
    assert [e["time"] for e in _scheduled(result)] == [5.0, 29.99]


def test_true_damage_type_ignores_enemy_def():
    plain = _run(
        {"b3": [{"schedule": lambda ctx, dur: [5.0], "percent": 100.0}]},
        enemy_def=4000,
    )
    true = _run(
        {"b3": [{"schedule": lambda ctx, dur: [5.0], "percent": 100.0, "damage_type": "true"}]},
        enemy_def=4000,
    )
    assert _scheduled(true)[0]["damage"] > _scheduled(plain)[0]["damage"]


def test_absent_param_emits_nothing():
    assert _scheduled(_run()) == []
