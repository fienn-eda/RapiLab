"""The Effective Range bonus: +0.30 in the major bucket, and who collects it.

Measured on Ade: Agent Bunny in a one-unit range (ATK 305,667, full-charge core
hit): outside range 1,309,593 -> inside 1,506,032 = exactly 1.150000, which on
a core hit's major of 2.0 is +0.30 (Fienn, 2026-07-27). `test_damage_formula`
pins that arithmetic; these pin the SCOPE and the switch.

Two things decide whether an instance collects it. The encounter decides the
distance - `BossProfile.effective_range_band`, unread (None) by default,
because Nikke positions are fixed and the player does not choose the range
(Fienn, 2026-07-31) - and that band decides WHICH weapons are in range: "near"
pays SG/SMG, "mid" pays AR/MG, "far" pays SR. The engine decides the scope,
which is Core Damage's scope, plus one weapon that no band ever pays: a Rocket
Launcher collects it at no distance at all.
"""
import pytest

from app.raid_simulator import simulate_raid

DECK = [
    {"slug": "b1", "burst_tier": 1, "element": "Iron", "cooldown": 20.0},
    {"slug": "b2", "burst_tier": 2, "element": "Iron", "cooldown": 20.0},
    {"slug": "attacker", "burst_tier": 3, "element": "Iron", "cooldown": 40.0},
]
BASE_STATS = {s["slug"]: {"atk": 10000, "def": 0, "max_hp": 0} for s in DECK}

# The bonus is a flag times 0.3, exactly like the Full Burst bonus is a flag
# times 0.5 - so on a bare hit (no crit, no core, outside any window) the major
# bucket goes 1.0 -> 1.3.
RANGE_MULTIPLIER = 1.3


def _weapon(kind="AR", **over):
    # A launcher fires on a charge, so it needs a charge time to fire at all -
    # a 0.0 there produces no shots and would make the RL case vacuously pass.
    charging = kind in ("RL", "SR")
    w = {"weapon": kind, "damage_percent": 10.0, "max_ammo": 100,
         "reload_time": 1.0, "charge_time": 0.2 if charging else 0.0,
         "charge_damage_percent": 100.0 if charging else 0.0}
    w.update(over)
    return w


def _fight(band, weapon="AR", **over):
    """One fight, short by default so no Full Burst opens - a window would add
    its own +0.5 to the same bucket and stop the ratio from being the range
    term alone."""
    kwargs = dict(
        rules_by_slug={s["slug"]: [] for s in DECK},
        burst_damage_percents={},
        base_stats=BASE_STATS,
        enemy_def=0,
        gauge_charge_time=5.0,
        fight_duration=1.0,
        base_crit_rate=0.0,
        core_hittable=False,
        weapon_stats={"attacker": _weapon(weapon)},
        effective_range_band=band,
    )
    kwargs.update(over)
    return simulate_raid(DECK, **kwargs)


def _damage_from(result, source):
    return sum(e["damage"] for e in result["damage_log"] if e["source"] == source)


def test_no_full_burst_opens_in_the_short_fixture():
    # The main comparison rests on it.
    assert not [e for e in _fight(None)["events"] if e["type"] == "full_burst_start"]


def test_off_by_default_leaves_normal_attacks_exactly_as_they_were():
    default = simulate_raid(
        DECK,
        rules_by_slug={s["slug"]: [] for s in DECK},
        burst_damage_percents={},
        base_stats=BASE_STATS,
        enemy_def=0,
        gauge_charge_time=5.0,
        fight_duration=1.0,
        base_crit_rate=0.0,
        weapon_stats={"attacker": _weapon()},
    )
    assert _damage_from(default, "normal_attack") == _damage_from(
        _fight(None), "normal_attack")


def test_in_range_adds_030_to_a_normal_attack():
    outside = _damage_from(_fight(None), "normal_attack")
    inside = _damage_from(_fight("mid"), "normal_attack")
    assert outside > 0
    assert inside == pytest.approx(outside * RANGE_MULTIPLIER)


def test_a_rocket_launcher_collects_it_at_no_distance():
    # Anis: Star's range footage reads her non-crit normal attack's major
    # bucket as exactly 1.000000 outside Full Burst - no range term - which is
    # what makes an RL the measuring stick for the rest of the bucket.
    outside = _damage_from(_fight(None, weapon="RL"), "normal_attack")
    inside = _damage_from(_fight("mid", weapon="RL"), "normal_attack")
    assert outside > 0
    assert inside == outside


def test_a_sniper_rifle_does_collect_it_so_the_carve_out_is_the_weapon():
    # Ade: Agent Bunny, the unit the +0.30 was measured on, is an SR - and she
    # charges her shots just like a launcher does. So the RL exception is about
    # the weapon, not about charging.
    outside = _damage_from(_fight(None, weapon="SR"), "normal_attack")
    inside = _damage_from(_fight("far", weapon="SR"), "normal_attack")
    assert outside > 0
    assert inside == pytest.approx(outside * RANGE_MULTIPLIER)


def test_a_band_pays_only_the_weapons_that_belong_to_it():
    # The recorded raid is the case this exists for: Annihilio is mid range, so
    # its AR and MG collect the bonus while the same AR at any other distance
    # does not. Without this the band would be a boolean wearing three names.
    bare = _damage_from(_fight(None), "normal_attack")
    assert _damage_from(_fight("mid"), "normal_attack") == pytest.approx(
        bare * RANGE_MULTIPLIER)
    assert _damage_from(_fight("near"), "normal_attack") == bare
    assert _damage_from(_fight("far"), "normal_attack") == bare


def test_an_unrecognised_band_raises_instead_of_paying_nobody():
    # Paying nobody is what None means, so a typo that silently did the same
    # would be indistinguishable from "not read yet" in every output.
    with pytest.raises(ValueError, match="unknown effective range band"):
        _fight("medium")


def test_skill_damage_never_collects_it():
    # Same scope as Core Damage: burst nukes, per-shot riders and DoTs are out.
    # Long enough for the burst to fire; both runs share whatever windows open,
    # so the burst source is comparable between them.
    runs = [_fight(flag, fight_duration=30.0, burst_damage_percents={"attacker": 100.0})
            for flag in (None, "mid")]
    burst = [_damage_from(r, "burst") for r in runs]
    assert burst[0] > 0
    assert burst[1] == burst[0]
    # ...while the normal attacks in those same runs DID move, so the fixture
    # is not simply failing to turn the flag on.
    assert (_damage_from(runs[1], "normal_attack")
            > _damage_from(runs[0], "normal_attack"))
