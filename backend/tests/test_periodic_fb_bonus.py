"""periodic_nukes ticks landing inside a Full Burst window get the Full Burst
bonus when the spec opts in with `full_burst_bonus_eligible: True` (the
repeating-tick-DoT rule, Fienn 2026-07-16 — each tick computes at its own time
with live state, so ticks inside the window are eligible like any other
repeating DoT). Absent field keeps the old behavior (no bonus), so existing
periodic units are unchanged until each is deliberately flagged.
"""
from app.raid_simulator import simulate_raid

RULES_BY_SLUG = {"buffer": [], "midtier": [], "attacker": []}


def make_deck():
    return [
        {"slug": "buffer", "burst_tier": 1, "element": "Iron", "cooldown": 20.0},
        {"slug": "midtier", "burst_tier": 2, "element": "Iron", "cooldown": 20.0},
        {"slug": "attacker", "burst_tier": 3, "element": "Iron", "cooldown": 40.0},
    ]


def make_base_stats():
    return {
        "buffer": {"atk": 0, "def": 0, "max_hp": 0},
        "midtier": {"atk": 0, "def": 0, "max_hp": 0},
        "attacker": {"atk": 100000.0, "def": 5000.0, "max_hp": 500000.0},
    }


def _total(periodic_spec):
    result = simulate_raid(
        make_deck(),
        RULES_BY_SLUG,
        burst_damage_percents={},
        base_stats=make_base_stats(),
        enemy_def=0,
        gauge_charge_time=5.0,
        fight_duration=20.0,
        mode="auto",
        base_crit_rate=0.0,
        periodic_nukes={"attacker": periodic_spec},
    )
    return result["total_damage"]


BASE = {"cooldown": 1.0, "percent": 100.0, "damage_type": "sustained"}


def test_eligible_periodic_ticks_get_full_burst_bonus():
    # Identical spec, only the opt-in flag differs. With a 1s tick over a 20s
    # fight and a Full Burst window opening after the ~5s gauge charge, several
    # ticks land inside the window - the eligible run must total strictly more.
    eligible = _total(dict(BASE, full_burst_bonus_eligible=True))
    ineligible = _total(BASE)
    assert ineligible > 0
    assert eligible > ineligible


def test_absent_flag_keeps_old_behavior():
    # A spec that never mentions the field totals exactly what an explicit
    # False does - existing periodic units (encoded before the field existed)
    # are untouched.
    assert _total(BASE) == _total(dict(BASE, full_burst_bonus_eligible=False))
