"""A skill that "expends N rounds from the ammo pouch" fires one real bullet;
the N is ammo ACCOUNTING that feeds consumption-counting synergies (Fienn,
2026-07-19) - Little Mermaid's Bubble Barrage being the one the engine models.
These pin that simulate_raid books each shot at its unit's accounting rate,
and that the rate follows the Full Burst window (Velvet spends 300 rounds per
shot inside it, 100 outside).
"""
from app.raid_simulator import simulate_raid

WEAPON = {"weapon": "AR", "damage_percent": 10.0, "max_ammo": 1000,
          "reload_time": 0.1, "charge_time": 0.0, "charge_damage_percent": 0.0}
DECK = [
    {"slug": "counter", "burst_tier": 1, "element": "Iron", "cooldown": 20.0},
    {"slug": "pouch", "burst_tier": 2, "element": "Iron", "cooldown": 20.0},
    {"slug": "b3", "burst_tier": 3, "element": "Iron", "cooldown": 20.0},
]
BASE_STATS = {s["slug"]: {"atk": 10000, "def": 0, "max_hp": 0} for s in DECK}


def _rounds_booked(ammo_rounds_per_shot):
    """Total rounds the squad ammo counter sees, read back through a schedule
    that fires one hit per 1000 rounds - the same channel Bubble Barrage uses."""
    seen = {}

    def schedule(context, fight_duration):
        seen["rounds"] = sum(
            sum(context.shot_ammo_rounds.get(slug, [1.0] * len(times)))
            for slug, times in context.shot_times.items()
        )
        seen["shots"] = sum(len(times) for times in context.shot_times.values())
        return []

    simulate_raid(
        DECK,
        {s["slug"]: [] for s in DECK},
        burst_damage_percents={},
        base_stats=BASE_STATS,
        enemy_def=0,
        gauge_charge_time=2.0,
        fight_duration=40.0,
        weapon_stats={"pouch": WEAPON},
        scheduled_nukes={"counter": [{"schedule": schedule, "percent": 100.0}]},
        ammo_rounds_per_shot=ammo_rounds_per_shot,
    )
    return seen


def test_a_plain_magazine_books_one_round_per_shot():
    seen = _rounds_booked(None)
    assert seen["shots"] > 0
    assert seen["rounds"] == seen["shots"]


def test_a_pouch_shot_books_its_accounting_rate_not_one():
    seen = _rounds_booked({"pouch": (50.0, 50.0)})
    assert seen["rounds"] == seen["shots"] * 50.0


def test_the_accounting_rate_follows_the_full_burst_window():
    # 300 inside Full Burst, 100 outside (Velvet's two pouch skills). The fight
    # has both kinds of shot, so the booked total must land strictly between
    # the two uniform rates - proving the window, not just the number, is read.
    seen = _rounds_booked({"pouch": (300.0, 100.0)})
    assert seen["shots"] * 100.0 < seen["rounds"] < seen["shots"] * 300.0
