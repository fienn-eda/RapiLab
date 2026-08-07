"""코어히트율 — 탄착군이 코어보다 크면 평타의 일부만 코어 보너스를 받는다.

숫자를 비율이 아니라 값으로 박는다. ATK 10000 x 발당 100%에 다른 major
modifier가 없으므로 한 발은 곧 10000 x (1 + p x CORE_HIT_BONUS)이고,
"1.44배"라고만 적으면 CORE_HIT_BONUS가 움직여도 테스트가 계속 통과한다.
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


def _weapon(weapon):
    return {"weapon": weapon, "damage_percent": 100.0, "max_ammo": 999,
            "reload_time": 0.0, "charge_time": 0.0, "charge_damage_percent": 100.0}


def _log(weapon, *, core_diameter_px, striker_rules=(), two_pierce=False):
    return simulate_raid(
        _deck(weapon),
        {"b1": [], "b2": [], "striker": list(striker_rules)},
        burst_damage_percents={"striker": 100.0},
        base_stats=BASE_STATS,
        enemy_def=0,
        # The fight ends before any Full Burst window opens, so the core bonus is
        # the only major modifier in play.
        gauge_charge_time=30.0,
        fight_duration=1.5,
        base_crit_rate=0.0,
        weapon_stats={"striker": _weapon(weapon)},
        core_hittable=True,
        core_diameter_px=core_diameter_px,
        pierce_hits_body_behind_core=two_pierce,
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
    # An MG's spread converges to 10px, already inside a 50px core.
    ("MG", 20000.0),
])
def test_each_weapon_collects_its_area_ratio(weapon, expected):
    assert _first_shot(weapon, core_diameter_px=50.0) == pytest.approx(expected)


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
    """Skill damage whose own text says it strikes the core is not a question of
    aim. The same `is_normal_attack` gate also covers a summon that aims and
    shoots on its own (Anis: Star's Shooting Stars, `core_eligible_override`)."""
    result = simulate_raid(
        _deck("SG"),
        {s: [] for s in ("b1", "b2", "striker")},
        burst_damage_percents={"striker": 100.0},
        base_stats=BASE_STATS,
        enemy_def=0,
        gauge_charge_time=2.0,
        fight_duration=30.0,
        base_crit_rate=0.0,
        core_hittable=True,
        core_diameter_px=50.0,
        burst_damage_types={"striker": "core_strike"},
    )
    burst = next(e["damage"] for e in result["damage_log"] if e["source"] == "burst")
    # An SG's own normal attacks would only collect 4% of the bonus here.
    assert burst == 20000.0


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
