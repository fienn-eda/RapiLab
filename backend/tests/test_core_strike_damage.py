""""Core strike damage" (코어 명중 대미지) is skill damage that still collects
the core bonus. Its in-game tooltip: it strikes the target's BODY rather than a
real core part, but is displayed as core damage and "the core bonus multiplier
and core-damage up/down effects apply" (Fienn, 2026-07-26). That makes it the
one exception to "Core Damage is normal-attack-only", so these pin the
exception itself rather than any one unit's numbers.
"""
from app.raid_simulator import core_eligible, simulate_raid

DECK = [
    {"slug": "b1", "burst_tier": 1, "element": "Iron", "cooldown": 20.0},
    {"slug": "b2", "burst_tier": 2, "element": "Iron", "cooldown": 20.0},
    {"slug": "striker", "burst_tier": 3, "element": "Iron", "cooldown": 20.0},
]
BASE_STATS = {s["slug"]: {"atk": 10000, "def": 0, "max_hp": 0} for s in DECK}


def _burst_damage(damage_type, core_hittable):
    result = simulate_raid(
        DECK,
        {s["slug"]: [] for s in DECK},
        burst_damage_percents={"striker": 100.0},
        base_stats=BASE_STATS,
        enemy_def=0,
        gauge_charge_time=2.0,
        fight_duration=30.0,
        base_crit_rate=0.0,
        core_hittable=core_hittable,
        burst_damage_types={"striker": damage_type} if damage_type != "attack" else {},
    )
    return next(e["damage"] for e in result["damage_log"] if e["source"] == "burst")


def test_ordinary_skill_damage_never_collects_the_core_bonus():
    assert not core_eligible("burst", "attack")
    assert not core_eligible("instant_nuke", "attack")
    assert _burst_damage("attack", core_hittable=True) == 10000.0


def test_core_strike_collects_the_core_bonus_despite_being_skill_damage():
    assert core_eligible("burst", "core_strike")
    assert core_eligible("instant_nuke", "core_strike")
    assert core_eligible("scheduled", "core_strike")
    # CORE_HIT_BONUS is 1.0, so the core bonus doubles an otherwise bare hit.
    assert _burst_damage("core_strike", core_hittable=True) == 20000.0


def test_core_strike_still_needs_the_boss_to_have_an_exploitable_core():
    # The skill text scopes it to "enemies with activated cores", and the sim
    # gates every core correction on core_hittable - the exception is about
    # WHICH damage collects the bonus, not about conjuring a core.
    assert _burst_damage("core_strike", core_hittable=False) == 10000.0


def test_sustained_and_distributed_stay_off_the_core_even_as_normal_attacks():
    assert not core_eligible("normal_attack", "sustained")
    assert not core_eligible("normal_attack", "distributed")
