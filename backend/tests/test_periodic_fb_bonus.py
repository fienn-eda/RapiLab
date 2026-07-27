"""A periodic_nukes tick collects the Full Burst bonus exactly when its OWN
tick time falls inside a Full Burst window - no opt-in, no skill-text test.

This file used to assert the opposite shape: that a spec had to declare
`full_burst_bonus_eligible: True` to get the bonus at all. That flag carried a
rule keyed on the phrase "as additional damage", deleted 2026-07-28 once Fienn
pinned down why it ever seemed to hold - a Burst 3's instant "as damage"
bullets resolve AT the cast, one beat before the window opens, so the phrase
only ever correlated with the timing. Cast time and Full Burst entry are
separate instants in this engine, so the time is the whole rule.
"""
from app.raid_simulator import simulate_raid

RULES_BY_SLUG = {"buffer": [], "midtier": [], "attacker": []}
SPEC = {"cooldown": 1.0, "percent": 100.0, "damage_type": "sustained"}


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


def run():
    return simulate_raid(
        make_deck(),
        RULES_BY_SLUG,
        burst_damage_percents={},
        base_stats=make_base_stats(),
        enemy_def=0,
        gauge_charge_time=5.0,
        fight_duration=20.0,
        mode="auto",
        base_crit_rate=0.0,
        periodic_nukes={"attacker": SPEC},
    )


def windows(result):
    return list(zip((e["time"] for e in result["events"] if e["type"] == "full_burst_start"),
                    (e["time"] for e in result["events"] if e["type"] == "full_burst_end")))


def in_window(event, wins):
    return any(start <= event["time"] < end for start, end in wins)


def test_a_tick_inside_the_window_is_worth_exactly_the_bonus_more_than_one_outside():
    # Same spec, same fight, and no buffs at all - the only thing separating
    # these two ticks is which side of the window boundary they land on, so
    # their ratio IS the bonus: the major-modifier bucket is a bare 1 outside
    # and 1 + 0.5 inside.
    result = run()
    wins = windows(result)
    ticks = [e for e in result["damage_log"] if e["source"] == "periodic"]
    inside = next(e for e in ticks if in_window(e, wins))
    outside = next(e for e in ticks if not in_window(e, wins))
    assert round(inside["damage"] / outside["damage"], 6) == 1.5


def test_every_tick_is_judged_on_its_own_time():
    # Not a per-run switch. One run's periodic log holds exactly two damage
    # values, and each tick sits on the side its own time puts it - which is
    # what "decided by when the damage is computed" has to mean.
    result = run()
    wins = windows(result)
    ticks = [e for e in result["damage_log"] if e["source"] == "periodic"]
    values = {round(e["damage"], 6) for e in ticks}
    assert len(values) == 2
    bonused = max(values)
    for e in ticks:
        assert (round(e["damage"], 6) == bonused) is in_window(e, wins)
