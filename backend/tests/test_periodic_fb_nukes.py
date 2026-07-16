"""periodic_nukes `during_full_burst` window + `hit_count` + `own_burst_interval`
(gap #6): a periodic skill that ticks only inside Full Burst windows, anchored
to each window's start (e.g. Ada Wong's Flash Grenade, Little Mermaid's Bubble
Wave), optionally with multiple hits per tick and an enhanced interval for FB
windows opened by the owner's own burst."""
from app.raid_simulator import simulate_raid


def _deck(extra=()):
    deck = [
        {"slug": "b1", "burst_tier": 1, "element": "Fire", "cooldown": 15.0},
        {"slug": "b2", "burst_tier": 2, "element": "Fire", "cooldown": 15.0},
        {"slug": "b3", "burst_tier": 3, "element": "Fire", "cooldown": 15.0},
    ]
    return deck + list(extra)


def _run(periodic_nukes, deck=None):
    deck = deck or _deck()
    return simulate_raid(
        deck=deck,
        rules_by_slug={m["slug"]: [] for m in deck},
        burst_damage_percents={},
        base_stats={m["slug"]: {"atk": 10000} for m in deck},
        enemy_def=0,
        gauge_charge_time=5.0,
        fight_duration=30.0,
        base_crit_rate=0.0,
        periodic_nukes=periodic_nukes,
    )


def _fb_windows(result):
    events = result["events"]
    return list(zip(
        (e["time"] for e in events if e["type"] == "full_burst_start"),
        (e["time"] for e in events if e["type"] == "full_burst_end"),
    ))


def _periodic_times(result):
    return [e["time"] for e in result["damage_log"] if e["source"] == "periodic"]


def test_during_full_burst_ticks_only_inside_windows():
    result = _run({"b3": {"cooldown": 2.0, "percent": 100.0, "during_full_burst": True}})
    windows = _fb_windows(result)
    assert len(windows) >= 2
    times = _periodic_times(result)
    assert times
    for t in times:
        assert any(start < t < end for start, end in windows)
    # 10s window, 2s cd -> 4 ticks per window at start+2,+4,+6,+8
    for start, end in windows:
        in_window = sorted(t for t in times if start <= t < end)
        assert in_window == [start + 2.0, start + 4.0, start + 6.0, start + 8.0]


def test_hit_count_records_n_hits_per_tick():
    result = _run({"b3": {"cooldown": 2.0, "percent": 100.0, "during_full_burst": True,
                          "hit_count": 4}})
    times = _periodic_times(result)
    windows = _fb_windows(result)
    start, end = windows[0]
    first_tick = start + 2.0
    assert times.count(first_tick) == 4


def test_own_burst_interval_enhances_windows_opened_by_own_burst():
    # b3 opens every FB window with her own burst -> 1s ticks (9 per window).
    spec = {"cooldown": 2.0, "percent": 100.0, "during_full_burst": True,
            "own_burst_interval": (1.0, 10.0)}
    result = _run({"b3": dict(spec)})
    windows = _fb_windows(result)
    start, end = windows[0]
    in_window = sorted(t for t in _periodic_times(result) if start <= t < end)
    assert in_window == [start + i for i in range(1, 10)]

    # The same spec on a unit who never bursts keeps the base 2s interval.
    deck = _deck(extra=[{"slug": "idle-b1", "burst_tier": 1, "element": "Fire", "cooldown": 15.0}])
    result2 = _run({"idle-b1": dict(spec)}, deck=deck)
    windows2 = _fb_windows(result2)
    start2, _ = windows2[0]
    in_window2 = sorted(t for t in _periodic_times(result2) if start2 <= t < start2 + 10.0)
    assert in_window2 == [start2 + 2.0, start2 + 4.0, start2 + 6.0, start2 + 8.0]


def test_default_periodic_nukes_unchanged():
    # No during_full_burst flag: whole-fight ticks at t=cd, 2cd, ... as before.
    result = _run({"b3": {"cooldown": 4.0, "percent": 100.0}})
    assert _periodic_times(result) == [4.0 * i for i in range(1, 8)]  # 4..28
