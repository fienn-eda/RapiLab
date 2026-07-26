"""A burst nuke worded "as additional damage" takes the Full Burst bonus.

Fienn's 2026-07-12 rule was stated about burst skills, but the opt-in it
produced (`full_burst_bonus_eligible`) only ever reached per-shot, periodic and
resource-scaled nukes - the plain `burst_damage_percents` path never passed it,
so no burst nuke could take the bonus. Measured on Fienn's recorded deck 1 that
cost Liberalio 42.5% of her burst damage.

Only a Burst-3's nuke can benefit: Burst 1 and 2 fire BEFORE full_burst_start,
so the window test excludes them on timing alone (Fienn, 2026-07-26). That
holds in MANUAL mode, which is what BossProfile defaults to and what every raid
runs - `burst_cycle` staggers the three casts 0.1s apart there. In auto mode
the gap is 0.0 and all three coincide with the window start, so a flagged
Burst 1 would collect the bonus; no Burst-1 slug is flagged today, and these
tests use manual mode because that is the mode the ruling describes.
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
        "buffer": {"atk": 100000.0, "def": 5000.0, "max_hp": 500000.0},
        "midtier": {"atk": 100000.0, "def": 5000.0, "max_hp": 500000.0},
        "attacker": {"atk": 100000.0, "def": 5000.0, "max_hp": 500000.0},
    }


def _burst_damage(slug, eligible_slugs):
    result = simulate_raid(
        make_deck(),
        RULES_BY_SLUG,
        burst_damage_percents={slug: 900.0},
        base_stats=make_base_stats(),
        enemy_def=0,
        gauge_charge_time=5.0,
        fight_duration=40.0,
        mode="manual",
        base_crit_rate=0.0,
        burst_full_burst_bonus_eligible=eligible_slugs,
    )
    return sum(e["damage"] for e in result["damage_log"] if e["source"] == "burst")


def test_an_eligible_burst_3_nuke_takes_the_full_burst_bonus():
    # Same nuke, same timing; only the opt-in differs. The Burst 3 fires at the
    # instant Full Burst opens, which the window test counts as inside.
    eligible = _burst_damage("attacker", {"attacker"})
    ineligible = _burst_damage("attacker", set())
    assert ineligible > 0
    assert eligible > ineligible


def test_an_unflagged_burst_nuke_is_unchanged():
    # Every unit encoded before this wiring existed must total exactly what it
    # totalled before - the flag is opt-in, not a default.
    assert _burst_damage("attacker", set()) == _burst_damage("attacker", None)


def test_a_burst_1_nuke_gains_nothing_because_it_fires_before_the_window():
    # Burst 1 casts ahead of full_burst_start, so even flagged it is outside
    # every window and the bonus cannot apply.
    assert _burst_damage("buffer", {"buffer"}) == _burst_damage("buffer", set())
