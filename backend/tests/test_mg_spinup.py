"""A machine gun does not fire at its nominal rate from the first round.

Fienn's frame-by-frame reading (2026-08-07, Rosanna solo, no reload buffs, a
305-round magazine) is the anchor - `docs/measurements/mg-spinup.md` carries the
raw frame numbers. It settles three separate things at once, and the tests below
are one per thing so a future change says which one it broke.
"""
import pytest

from app.attack_rate import (MG_SPINUP, RATE_OF_FIRE_60FPS, ShotRecord,
                             generate_magazine_shot_times,
                             generate_segmented_shots, reload_time_with_speed,
                             spinup_for_weapon)

F = 1 / 60
MAGAZINE = 305
RELOAD_FILE = 1.67          # Rosanna's in-game tooltip, and her data file

# Raw frame numbers, as read.
FIRST_SHOT, SPINUP_DONE, EMPTY, RELOADED = 863, 1000, 1256, 1367
AMMO_AT_FIRST, AMMO_AT_SPINUP_DONE = 304, 256


def _one_magazine():
    return generate_magazine_shot_times(
        rate_of_fire=RATE_OF_FIRE_60FPS["MG"], max_ammo=MAGAZINE,
        reload_time=RELOAD_FILE, fight_duration=60.0, weapon="MG")


def test_top_rate_is_exactly_one_round_per_frame():
    """256 rounds in 256 frames, once the spin-up is over - so the engine's
    nominal 60/sec was right all along, as a MAXIMUM."""
    rounds = AMMO_AT_SPINUP_DONE
    frames = EMPTY - SPINUP_DONE
    assert rounds == frames
    assert RATE_OF_FIRE_60FPS["MG"] == pytest.approx(rounds / (frames * F))


def test_the_spin_up_costs_a_fixed_time_at_the_head_of_each_magazine():
    """48 intervals took 137 frames where full speed would take 48."""
    assert MG_SPINUP.intervals == AMMO_AT_FIRST - AMMO_AT_SPINUP_DONE == 48
    assert MG_SPINUP.seconds == pytest.approx((SPINUP_DONE - FIRST_SHOT) * F)
    cost = MG_SPINUP.seconds - MG_SPINUP.intervals * F
    assert cost == pytest.approx(89 * F)      # 1.4833 sec a magazine
    assert spinup_for_weapon("MG") is MG_SPINUP
    for weapon in ("AR", "SMG", "SG"):
        assert spinup_for_weapon(weapon) is None


def test_a_magazine_reproduces_the_measured_frame_numbers():
    shots = _one_magazine()
    # Shot 1 opens the magazine; shot 49 is where the ramp ends; shot 305 empties it.
    assert shots[0] == pytest.approx(0.0)
    assert shots[48] == pytest.approx((SPINUP_DONE - FIRST_SHOT) * F)
    assert shots[MAGAZINE - 1] == pytest.approx((EMPTY - FIRST_SHOT) * F)
    # ...and the reload after it, which is the affine model's third confirmation
    # on a third unit: 111 frames measured, 109.1 predicted.
    assert reload_time_with_speed(RELOAD_FILE, 0.0) == pytest.approx((RELOADED - EMPTY) * F, abs=2 * F)
    # The engine's own convention is that the last round occupies its interval
    # too, so the next magazine opens one gap plus a reload after the last shot.
    # Against the measurement that is 110.1 frames where 111 were read - inside
    # the same one-frame reading precision as everything else here.
    assert shots[MAGAZINE] == pytest.approx(
        shots[MAGAZINE - 1] + F + reload_time_with_speed(RELOAD_FILE, 0.0))
    assert (shots[MAGAZINE] - shots[MAGAZINE - 1]) == pytest.approx(
        (RELOADED - EMPTY) * F, abs=2 * F)


def test_a_magazine_takes_longer_than_the_nominal_rate_says():
    """The headline number: 393 frames where the engine used to say 304."""
    shots = _one_magazine()
    span = shots[MAGAZINE - 1] - shots[0]
    assert span == pytest.approx((EMPTY - FIRST_SHOT) * F)
    assert span / ((MAGAZINE - 1) * F) == pytest.approx(393 / 304, rel=1e-6)


def test_the_production_shot_pass_spins_up_too():
    """`generate_segmented_shots` is what every unit's weapon pass runs through,
    and it must not diverge from the generator above."""
    base = {"weapon": "MG", "damage_percent": 5.1, "max_ammo": MAGAZINE,
            "reload_time": RELOAD_FILE, "charge_time": 0.0,
            "charge_damage_percent": 100.0}
    records = generate_segmented_shots(base, [], fight_duration=60.0)
    assert all(isinstance(r, ShotRecord) for r in records)
    times = [r.time for r in records]
    assert times[:MAGAZINE + 1] == pytest.approx(_one_magazine()[:MAGAZINE + 1])


def test_a_charge_weapon_is_untouched():
    """Spin-up is an MG mechanic; nothing else may move."""
    base = {"weapon": "SR", "damage_percent": 10.0, "max_ammo": 6,
            "reload_time": 2.0, "charge_time": 1.0, "charge_damage_percent": 250.0}
    times = [r.time for r in generate_segmented_shots(base, [], fight_duration=20.0)]
    assert times[:6] == pytest.approx([1.0, 2.0, 3.0, 4.0, 5.0, 6.0])
