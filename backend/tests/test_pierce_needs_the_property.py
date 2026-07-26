"""Pierce Damage Up only credits a unit that actually HAS Pierce - the
skill-text marker is [관통 특화] / "Gain Pierce" (Fienn, 2026-07-26). The
property is its own registry stat, `has_pierce`, so a unit that gains it for a
window is credited for exactly that window.

These pin the gate itself. Per-unit grants are pinned in each unit's own test.
"""
from app.raid_simulator import simulate_raid
from app.skill_rules._helpers import buff_rule

DECK = [
    {"slug": "b1", "burst_tier": 1, "element": "Iron", "cooldown": 20.0},
    {"slug": "b2", "burst_tier": 2, "element": "Iron", "cooldown": 20.0},
    {"slug": "striker", "burst_tier": 3, "element": "Iron", "cooldown": 20.0},
]
BASE_STATS = {s["slug"]: {"atk": 10000, "def": 0, "max_hp": 0} for s in DECK}


def _burst_damage(striker_rules):
    result = simulate_raid(
        DECK,
        {"b1": [buff_rule("battle_start", [("pierce_damage_up", 0.5, "squad", None)])],
         "b2": [], "striker": striker_rules},
        burst_damage_percents={"striker": 100.0},
        base_stats=BASE_STATS,
        enemy_def=0,
        gauge_charge_time=2.0,
        fight_duration=30.0,
        base_crit_rate=0.0,
    )
    return next(e["damage"] for e in result["damage_log"] if e["source"] == "burst")


def test_a_squad_pierce_buff_does_nothing_for_an_ally_without_pierce():
    assert _burst_damage([]) == 10000.0


def test_the_same_buff_counts_in_full_for_an_ally_that_gains_pierce():
    holder = [buff_rule("battle_start", [("has_pierce", 1.0, "self", None)])]
    assert _burst_damage(holder) == 15000.0


def test_pierce_is_credited_only_while_the_property_is_actually_held():
    # The striker bursts at t=2 (gauge 2.0); a 1-second Pierce window opened at
    # battle start has lapsed by then, so the buff finds no property to credit.
    lapsed = [buff_rule("battle_start", [("has_pierce", 1.0, "self", 1.0)])]
    assert _burst_damage(lapsed) == 10000.0
