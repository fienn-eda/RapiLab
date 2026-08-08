"""A boss whose core is a separate object from its body: a Pierce holder's shot
passes through the core and lands on the body behind it, so one normal attack
produces TWO damage instances.

The body hit is the same instance minus the core bonus (Fienn, 2026-08-03), so
with no other major modifiers the pair reads (1 + 1.0) + 1 = 3.0 against the core
hit's 2.0. The numbers below are pinned rather than expressed as "1.5x": that
ratio is only true at this unit's core bonus of 1.0 (`core_damage.py`), and a
test that hides the constant would keep passing if the constant moved.

A unit without Pierce can still hit the core, but nothing is behind it for her.
"""
from app.raid_simulator import simulate_raid
from app.skill_rules._helpers import buff_rule, instant_nuke_pulse_rule

DECK = [
    {"slug": "b1", "burst_tier": 1, "element": "Iron", "cooldown": 20.0},
    {"slug": "b2", "burst_tier": 2, "element": "Iron", "cooldown": 20.0},
    {"slug": "striker", "burst_tier": 3, "element": "Iron", "cooldown": 20.0, "weapon": "AR"},
]
BASE_STATS = {s["slug"]: {"atk": 10000, "def": 0, "max_hp": 0} for s in DECK}
# 100% of ATK per shot with no reload, so one normal attack's damage IS the bucket.
WEAPON = {"weapon": "AR", "damage_percent": 100.0, "max_ammo": 999,
          "reload_time": 0.0, "charge_time": 0.0, "charge_damage_percent": 100.0}

HOLDS_PIERCE = [buff_rule("battle_start", [("has_pierce", 1.0, "self", None)])]


def _log(striker_rules, *, core_hittable=True, two_pierce=True, per_shot_rules=None):
    return simulate_raid(
        DECK,
        {"b1": [], "b2": [], "striker": striker_rules},
        burst_damage_percents={"striker": 100.0},
        base_stats=BASE_STATS,
        enemy_def=0,
        # The fight ends before any Full Burst window opens, so the core bonus is
        # the only major modifier in play.
        gauge_charge_time=30.0,
        fight_duration=1.5,
        base_crit_rate=0.0,
        weapon_stats={"striker": WEAPON},
        core_hittable=core_hittable,
        pierce_hits_body_behind_core=two_pierce,
        per_shot_rules=per_shot_rules,
    )["damage_log"]


def _shots(log):
    return [e["damage"] for e in log if e["source"] == "normal_attack"]


def test_a_pierce_holders_shot_lands_on_the_core_and_the_body():
    log = _log(HOLDS_PIERCE)
    off = _log(HOLDS_PIERCE, two_pierce=False)

    assert len(_shots(log)) == 2 * len(_shots(off))
    # core 10000 x (1 + 1.0), body 10000 x 1
    assert _shots(log)[:2] == [20000.0, 10000.0]
    assert sum(_shots(log)) == 1.5 * sum(_shots(off))


def test_a_unit_without_pierce_is_untouched():
    assert _shots(_log([])) == _shots(_log([], two_pierce=False))


def test_a_pierce_holders_skill_damage_still_lands_once():
    # Pierce is a property of NORMAL ATTACKS. A per-shot nuke fired by the same
    # unit at the same instant has nothing behind the core to hit.
    nuke = {"striker": [(1, "every", [instant_nuke_pulse_rule("per_shot", 100.0)])]}
    log = _log(HOLDS_PIERCE, per_shot_rules=nuke)
    off = _log(HOLDS_PIERCE, two_pierce=False, per_shot_rules=nuke)

    pulses = [e["damage"] for e in log if e["source"] == "per_shot_nuke"]
    assert pulses == [e["damage"] for e in off if e["source"] == "per_shot_nuke"]


def test_the_flag_does_nothing_when_the_core_cannot_be_hit():
    # There is no 2-pierce without a core to pierce, so the flag has to be inert
    # rather than silently doubling body damage.
    assert _shots(_log(HOLDS_PIERCE, core_hittable=False)) == _shots(
        _log(HOLDS_PIERCE, core_hittable=False, two_pierce=False))


def test_only_the_shots_inside_the_pierce_window_land_twice():
    # Pierce for 0.5 sec: the early shots pass through, the later ones still hit
    # the core but have nothing behind it to reach.
    lapsed = [buff_rule("battle_start", [("has_pierce", 1.0, "self", 0.5)])]
    shots = _shots(_log(lapsed))

    assert shots[:2] == [20000.0, 10000.0]   # first shot: core, then body
    assert shots[-1] == 20000.0              # window lapsed: core only
    assert len(shots) > len(_shots(_log(lapsed, two_pierce=False)))


def test_a_weapon_transform_shot_lands_twice_too():
    """A transform segment fires through the SAME shot loop and is recorded as
    "normal_attack", so it needs no special casing - this pins that it really is
    so (design C.5). It matters because the units that hold Pierce and the units
    that transform are largely the same list: Maxwell and Snow White gain Pierce
    for exactly the one charged shot their transform is, and Red Hood holds it
    continuously, so on this boss her transform shots AND her base-weapon shots
    both land twice.
    """
    def schedule(context, fight_duration):
        # charge_time=0.0 is falsy, so _segment_shot_records treats this as a
        # rate_of_fire profile (like the sustained/distributed transform tests
        # in test_raid_simulator.py) rather than a charge weapon - it needs
        # rate_of_fire to fire at all.
        return [{"start": 0.0, "end": 1.5,
                 "profile": {"weapon": "SR", "damage_percent": 500.0,
                             "charge_time": 0.0, "charge_damage_percent": 100.0,
                             "rate_of_fire": 2.0}}]

    def run(two_pierce):
        return simulate_raid(
            DECK,
            {"b1": [], "b2": [], "striker": HOLDS_PIERCE},
            burst_damage_percents={"striker": 100.0},
            base_stats=BASE_STATS, enemy_def=0, gauge_charge_time=30.0,
            fight_duration=1.5, base_crit_rate=0.0,
            weapon_stats={"striker": WEAPON},
            weapon_mode_schedules={"striker": schedule},
            core_hittable=True,
            pierce_hits_body_behind_core=two_pierce,
        )["damage_log"]

    on, off = _shots(run(True)), _shots(run(False))

    assert off, "fixture broken: the transform window produced no normal attacks"
    assert len(on) == 2 * len(off)
    assert sum(on) == 1.5 * sum(off)
    # the transform's own shot: core 10000 x 5.0 x (1 + 1.0), body without the bonus
    assert 100000.0 in on and 50000.0 in on
