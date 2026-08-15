"""코어히트율 — 탄착군이 코어보다 크면 평타의 일부만 코어 보너스를 받는다.

숫자를 비율이 아니라 값으로 박는다. ATK 10000 x 발당 100%에 다른 major
modifier가 없으므로 한 발은 곧 10000 x (1 + p x 시전자의 코어 보너스)이고,
"1.44배"라고만 적으면 그 보너스가 움직여도 테스트가 계속 통과한다.
"""
import pytest

from app.raid_simulator import simulate_raid
from app.skill_rules._helpers import buff_rule

BASE_STATS = {s: {"atk": 10000, "def": 0, "max_hp": 0}
              for s in ("b1", "b2", "striker")}


def _deck(weapon):
    return [
        {"slug": "b1", "burst_tier": 1, "element": "Iron", "cooldown": 20.0},
        {"slug": "b2", "burst_tier": 2, "element": "Iron", "cooldown": 20.0},
        {"slug": "striker", "burst_tier": 3, "element": "Iron", "cooldown": 20.0,
         "weapon": weapon},
    ]


def _weapon(weapon, **overrides):
    return {"weapon": weapon, "damage_percent": 100.0, "max_ammo": 999,
            "reload_time": 0.0, "charge_time": 0.0, "charge_damage_percent": 100.0,
            **overrides}


def _log(weapon, *, core_diameter_px, striker_rules=(), two_pierce=False,
         weapon_mode_schedules=None, fight_duration=1.5, **weapon_overrides):
    return simulate_raid(
        _deck(weapon),
        {"b1": [], "b2": [], "striker": list(striker_rules)},
        burst_damage_percents={"striker": 100.0},
        base_stats=BASE_STATS,
        enemy_def=0,
        # The fight ends before any Full Burst window opens, so the core bonus is
        # the only major modifier in play.
        gauge_charge_time=30.0,
        fight_duration=fight_duration,
        base_crit_rate=0.0,
        weapon_stats={"striker": _weapon(weapon, **weapon_overrides)},
        core_hittable=True,
        core_diameter_px=core_diameter_px,
        pierce_hits_body_behind_core=two_pierce,
        weapon_mode_schedules=weapon_mode_schedules or {},
    )["damage_log"]


def _shots(log):
    return [e["damage"] for e in log if e["source"] == "normal_attack"]


def _first_shot(weapon, **kwargs):
    return _shots(_log(weapon, **kwargs))[0]


# SR and RL are charge weapons (attack_rate.CHARGE_WEAPONS), so firing them here
# would drag the charge model into a test about spread. Their 10px spread is
# already covered by test_accuracy.py, and MG stands in for "spread inside the
# core" among the sustained-fire weapons.
FIRING_WEAPONS = ("AR", "SG", "SMG", "MG")


def test_no_core_diameter_leaves_every_shot_on_the_core():
    # The opt-in contract: with no diameter the engine models its old ceiling.
    for weapon in FIRING_WEAPONS:
        assert _first_shot(weapon, core_diameter_px=None) == 20000.0


@pytest.mark.parametrize("weapon,expected", [
    ("AR", 10000.0 * (1 + (50 / 75) ** 2)),
    ("SMG", 10000.0 * (1 + (50 / 110) ** 2)),
    ("SG", 10000.0 * (1 + (50 / 250) ** 2)),
    # An MG converges to 10px, well inside a 50px core - but it OPENS a magazine
    # at 250px, so its first round is the widest shot any weapon here fires and
    # collects the same 4% a shotgun does.
    ("MG", 10000.0 * (1 + (50 / 250) ** 2)),
])
def test_each_weapon_collects_its_area_ratio(weapon, expected):
    assert _first_shot(weapon, core_diameter_px=50.0) == pytest.approx(expected)


def test_an_mg_magazine_tightens_onto_the_core_as_it_empties():
    """The measured convergence (250px -> 10px at 7px a round) spread across the
    rounds it actually takes: 29 rounds to reach a 50px core, and every round
    after that is a full core hit.

    The fight runs long enough for round 60 to land: a cold MG spends 2.28 sec
    on its warm-up ramp, so 1.5 sec does not even empty the converging stretch.
    """
    shots = _shots(_log("MG", core_diameter_px=50.0, fight_duration=4.0))
    assert shots[0] == pytest.approx(10000.0 * (1 + (50 / 250) ** 2))
    assert shots[10] == pytest.approx(10000.0 * (1 + (50 / 180) ** 2))
    assert shots[28] == pytest.approx(10000.0 * (1 + (50 / 54) ** 2))
    assert shots[29] == 20000.0
    assert shots[60] == 20000.0


def test_the_mg_spread_reopens_with_the_next_magazine():
    """It is a MAGAZINE convergence, so a reload hands the next magazine the
    same wide opening - the same shape as the warm-up ramp, and the reason the
    round index rides on the shot record rather than counting shots fired."""
    shots = _shots(_log("MG", core_diameter_px=50.0, max_ammo=5, reload_time=0.1))
    wide = pytest.approx(10000.0 * (1 + (50 / 250) ** 2))
    assert shots[0] == wide
    assert shots[5] == wide, "round 0 of the second magazine is wide again"
    assert shots[4] == pytest.approx(10000.0 * (1 + (50 / 222) ** 2))


def test_a_charge_weapon_is_unmoved_by_the_magazine_index():
    # SR/RL carry start == end in the data, so tracking their magazine position
    # must not change a number. Guards the general form against an MG-shaped
    # special case leaking onto every weapon.
    shots = _shots(_log("SR", core_diameter_px=50.0, fight_duration=4.0))
    assert shots and all(s == 20000.0 for s in shots)


def test_a_hit_rate_buff_narrows_the_spread_and_raises_the_damage():
    # Without this wiring hit_rate registers and nothing happens - which is
    # exactly what fifteen slugs had been recording as a deferral.
    bare = _first_shot("SG", core_diameter_px=50.0)
    # 55% halves an SG's 250px spread to 125px, so p goes 0.04 -> 0.16.
    buffed = _first_shot(
        "SG", core_diameter_px=50.0,
        striker_rules=[buff_rule("battle_start", [("hit_rate", 0.55, "self", None)])],
    )
    assert bare == pytest.approx(10400.0)
    assert buffed == pytest.approx(11600.0)


def test_hit_rate_past_the_singularity_reaches_every_core():
    # Dorothy: Serendipity stacks two buffs past 110%, where the spread is a
    # point and even a shotgun cannot miss.
    assert _first_shot(
        "SG", core_diameter_px=50.0,
        striker_rules=[buff_rule("battle_start", [("hit_rate", 1.20, "self", None)])],
    ) == 20000.0


def test_a_negative_hit_rate_widens_the_spread():
    # Mast: Romantic Maid's Drunken. An AR at -55% spreads to 112.5px.
    assert _first_shot(
        "AR", core_diameter_px=50.0,
        striker_rules=[buff_rule("battle_start", [("hit_rate", -0.55, "self", None)])],
    ) == pytest.approx(10000.0 * (1 + (50 / 112.5) ** 2))


def test_core_strike_ignores_the_spread():
    """Skill damage whose own text says it strikes the core is not a question
    of aim - only the `is_normal_attack` gate decides, not the weapon's own
    spread. `weapon_stats` gives the striker an SG so that spread is actually
    in play: without the gate this would fall to 10400.0 (SG at 50px core =
    4% of the bonus), the same number `test_each_weapon_collects_its_area_ratio`
    pins for a bare SG normal attack."""
    result = simulate_raid(
        _deck("SG"),
        {s: [] for s in ("b1", "b2", "striker")},
        burst_damage_percents={"striker": 100.0},
        base_stats=BASE_STATS,
        enemy_def=0,
        gauge_charge_time=2.0,
        fight_duration=30.0,
        base_crit_rate=0.0,
        weapon_stats={"striker": _weapon("SG")},
        core_hittable=True,
        core_diameter_px=50.0,
        burst_damage_types={"striker": "core_strike"},
    )
    burst = next(e["damage"] for e in result["damage_log"] if e["source"] == "burst")
    # An SG's own normal attacks would only collect 4% of the bonus here.
    assert burst == 20000.0


def test_a_scheduled_summon_hit_also_ignores_the_spread():
    # Anis: Star's Shooting Stars ticks record as source="scheduled" with
    # core_eligible_override=True - the summon aims and fires on its own, so
    # like core_strike its damage skips the spread math the same way, through
    # the same is_normal_attack gate. Without the gate this would fall to
    # 10400.0, same as the bare-SG case above.
    result = simulate_raid(
        _deck("SG"),
        {s: [] for s in ("b1", "b2", "striker")},
        burst_damage_percents={"striker": 100.0},
        base_stats=BASE_STATS,
        enemy_def=0,
        gauge_charge_time=30.0,
        fight_duration=1.5,
        base_crit_rate=0.0,
        weapon_stats={"striker": _weapon("SG")},
        core_hittable=True,
        core_diameter_px=50.0,
        scheduled_nukes={"striker": [{
            "schedule": lambda context, fight_duration: [0.5],
            "percent": 100.0,
            "core_eligible": True,
        }]},
    )
    tick = next(e["damage"] for e in result["damage_log"] if e["source"] == "scheduled")
    assert tick == 20000.0


def _transform(**profile_extras):
    profile = {"weapon": "SR", "damage_percent": 100.0, "charge_time": 0.0,
               "charge_damage_percent": 100.0, "rate_of_fire": 2.0}
    profile.update(profile_extras)
    return {"striker": lambda context, fight_duration: [
        {"start": 0.0, "end": 1.5, "profile": profile}
    ]}


def test_a_transform_segment_keeps_the_base_weapon_spread_by_default():
    """A segment's `"weapon"` string is a hand-written label, not a measured
    aiming circle, so it does NOT get to pick a spread on its own - the unit's
    real weapon does. Here an SG that transforms into an "SR" profile still
    collects the SG's 4%."""
    shots = _shots(_log("SG", core_diameter_px=50.0,
                        weapon_mode_schedules=_transform()))
    assert shots and all(s == pytest.approx(10400.0) for s in shots)


def test_a_segment_may_declare_that_it_always_strikes_the_core():
    """Nayuta's Memory Incineration: the transform turns her SMG into a charged
    shot that lands on the core every time (Fienn, in play). That is a measured
    property of the segment, so it is declared on the profile rather than
    inferred from its weapon label - segments without the declaration keep the
    base weapon's spread (the test above)."""
    shots = _shots(_log("SG", core_diameter_px=50.0,
                        weapon_mode_schedules=_transform(always_core_hit=True)))
    assert shots and all(s == 20000.0 for s in shots)


def test_a_segment_may_declare_its_own_measured_aiming_circle():
    """Moran's spear mode: not core-locked, but its circle was MEASURED, so the
    segment declares a diameter instead of `always_core_hit`. It is the same
    kind of statement - a measured property of the transform that its `weapon`
    label could never carry - and it replaces the base weapon's diameter for
    exactly that segment's shots. Here an SG (250) declaring 100 collects
    (50/100)^2 = 25% instead of its own 4%."""
    shots = _shots(_log("SG", core_diameter_px=50.0,
                        weapon_mode_schedules=_transform(spread_diameter=100.0)))
    assert shots and all(s == pytest.approx(12500.0) for s in shots)


def test_a_declared_spread_covers_the_segment_and_nothing_else():
    schedules = {"striker": lambda context, fight_duration: [
        {"start": 0.0, "end": 1.0,
         "profile": {"weapon": "SR", "damage_percent": 100.0, "charge_time": 0.0,
                     "charge_damage_percent": 100.0, "rate_of_fire": 4.0,
                     "spread_diameter": 100.0}}
    ]}
    shots = _shots(_log("SG", core_diameter_px=50.0, weapon_mode_schedules=schedules))
    assert pytest.approx(12500.0) in shots, "the segment's own shots use the declaration"
    assert pytest.approx(10400.0) in shots, "shots after the window use the SG's 250"


def test_an_always_core_segment_still_reads_the_hit_rate_for_base_shots():
    """The declaration covers the segment's own shots and nothing else: with the
    window ending at 1.0 sec, the shots after it are back on the SG's spread."""
    schedules = {"striker": lambda context, fight_duration: [
        {"start": 0.0, "end": 1.0,
         "profile": {"weapon": "SR", "damage_percent": 100.0, "charge_time": 0.0,
                     "charge_damage_percent": 100.0, "rate_of_fire": 4.0,
                     "always_core_hit": True}}
    ]}
    shots = _shots(_log("SG", core_diameter_px=50.0, weapon_mode_schedules=schedules))
    assert 20000.0 in shots, "the segment's own shot should ignore the spread"
    assert pytest.approx(10400.0) in shots, "shots after the window should not"


def test_the_pierce_body_instance_is_weighted_by_the_core_hit_rate():
    # A round that missed the core has no core to pass through, so there is
    # nothing behind it to hit: the body instance exists only for the share
    # that hit.
    holds_pierce = [buff_rule("battle_start", [("has_pierce", 1.0, "self", None)])]
    shots = _shots(_log("AR", core_diameter_px=50.0,
                        striker_rules=holds_pierce, two_pierce=True))
    p = (50 / 75) ** 2
    assert shots[:2] == [pytest.approx(10000.0 * (1 + p)),
                         pytest.approx(10000.0 * p)]


def test_pierce_is_unchanged_when_no_diameter_is_given():
    holds_pierce = [buff_rule("battle_start", [("has_pierce", 1.0, "self", None)])]
    shots = _shots(_log("AR", core_diameter_px=None,
                        striker_rules=holds_pierce, two_pierce=True))
    assert shots[:2] == [20000.0, 10000.0]
