"""A machine gun does not fire at its nominal rate from the first round.

Fienn's frame-by-frame reading (2026-08-07, Rosanna solo, no reload buffs, a
305-round magazine) is the anchor - `docs/measurements/mg-spinup.md` carries the
raw frame numbers. It settles three separate things at once, and the tests below
are one per thing so a future change says which one it broke.
"""
import pytest

from app.attack_rate import (MG_SPINUP, RATE_OF_FIRE_60FPS, ShotRecord,
                             generate_magazine_shot_times,
                             generate_segmented_shots,
                             magazine_first_bullet_times,
                             magazine_last_bullet_times, magazine_shot_offset,
                             reload_time_with_speed, spinup_for_weapon,
                             spinup_with_speed)

F = 1 / 60
MAGAZINE = 305
RELOAD_FILE = 1.67          # Rosanna's in-game tooltip, and her data file

# Raw frame numbers, as read.
FIRST_SHOT, SPINUP_DONE, EMPTY, RELOADED = 863, 1000, 1256, 1367
AMMO_AT_FIRST, AMMO_AT_SPINUP_DONE = 304, 256


def _one_magazine(**extra):
    return generate_magazine_shot_times(
        rate_of_fire=RATE_OF_FIRE_60FPS["MG"], max_ammo=MAGAZINE,
        reload_time=RELOAD_FILE, fight_duration=60.0, weapon="MG", **extra)


def _mg_base():
    return {"weapon": "MG", "damage_percent": 5.1, "max_ammo": MAGAZINE,
            "reload_time": RELOAD_FILE, "charge_time": 0.0,
            "charge_damage_percent": 100.0}


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


def test_the_ramp_is_a_curve_with_the_cost_at_the_front():
    """Three readings that carry ammo counts put three points on the ramp, and
    they are not a straight line: 56 of a cold magazine's 137 frames go to the
    first TWO rounds. `docs/measurements/mg-spinup.md`."""
    assert MG_SPINUP.elapsed(0) == pytest.approx(0.0)
    assert MG_SPINUP.elapsed(2) == pytest.approx(56 * F)
    assert MG_SPINUP.elapsed(24) == pytest.approx(111 * F)
    assert MG_SPINUP.elapsed(48) == pytest.approx(137 * F)
    assert MG_SPINUP.elapsed(60) == pytest.approx(137 * F)      # past the ramp
    # 41% of the ramp goes to the first 2 of its 48 rounds.
    assert MG_SPINUP.elapsed(2) / MG_SPINUP.seconds == pytest.approx(56 / 137)
    # Linear inside a segment: position 1 is half of the first one.
    assert MG_SPINUP.elapsed(1) == pytest.approx(28 * F)


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


def test_a_cold_magazine_follows_the_measured_curve():
    """The ramp's total is unchanged - what moves is where its rounds sit."""
    shots = _one_magazine()
    assert shots[2] == pytest.approx(56 * F)
    assert shots[24] == pytest.approx(111 * F)
    assert shots[MG_SPINUP.intervals] == pytest.approx(137 * F)
    assert shots[MAGAZINE - 1] == pytest.approx((EMPTY - FIRST_SHOT) * F)


def test_a_magazine_can_open_part_way_up_the_ramp():
    """The two short-reload readings, read straight off the curve: a magazine
    that keeps 24 of the 48 ramp rounds pays 26 frames, not the 68.5 a flat
    ramp would charge for those same 24 gaps."""
    interval = 1 / RATE_OF_FIRE_60FPS["MG"]
    assert magazine_shot_offset(24, interval, MG_SPINUP, 24) == pytest.approx(26 * F)
    assert magazine_shot_offset(46, interval, MG_SPINUP, 2) == pytest.approx(81 * F)
    # ramp_start defaults to a cold magazine
    assert magazine_shot_offset(48, interval, MG_SPINUP) == pytest.approx(137 * F)
    # past the ramp the nominal gap resumes
    assert magazine_shot_offset(25, interval, MG_SPINUP, 24) == pytest.approx(27 * F)
    # A point INSIDE a segment, where the curve and a flat ramp disagree. The
    # assertions above all land on the curve's own knots (2, 24, 48), where a
    # flat rate happens to give the same answer - so they alone do not hold the
    # shape down.
    assert magazine_shot_offset(10, interval, MG_SPINUP, 2) == pytest.approx(25 * F)


def test_a_magazine_takes_longer_than_the_nominal_rate_says():
    """The headline number: 393 frames where the engine used to say 304."""
    shots = _one_magazine()
    span = shots[MAGAZINE - 1] - shots[0]
    assert span == pytest.approx((EMPTY - FIRST_SHOT) * F)
    assert span / ((MAGAZINE - 1) * F) == pytest.approx(393 / 304, rel=1e-6)


def test_the_production_shot_pass_spins_up_too():
    """`generate_segmented_shots` is what every unit's weapon pass runs through,
    and it must not diverge from the generator above."""
    records = generate_segmented_shots(_mg_base(), [], fight_duration=60.0)
    assert all(isinstance(r, ShotRecord) for r in records)
    times = [r.time for r in records]
    assert times[:MAGAZINE + 1] == pytest.approx(_one_magazine()[:MAGAZINE + 1])


def test_a_charge_weapon_is_untouched():
    """Spin-up is an MG mechanic; nothing else may move."""
    base = {"weapon": "SR", "damage_percent": 10.0, "max_ammo": 6,
            "reload_time": 2.0, "charge_time": 1.0, "charge_damage_percent": 250.0}
    times = [r.time for r in generate_segmented_shots(base, [], fight_duration=20.0)]
    assert times[:6] == pytest.approx([1.0, 2.0, 3.0, 4.0, 5.0, 6.0])


# --- "MG heating up speed", the buff that moves the ramp ---

def test_zero_heating_speed_is_the_identity():
    assert spinup_with_speed(MG_SPINUP, 0.0, RATE_OF_FIRE_60FPS["MG"]) is MG_SPINUP


def test_a_weapon_without_a_warm_up_stays_without_one():
    assert spinup_with_speed(None, 1.0, RATE_OF_FIRE_60FPS["AR"]) is None


def test_heating_speed_down_100_percent_doubles_the_ramp():
    # Fienn (2026-08-14): a speed arrow reads as a multiplier on the DURATION,
    # the same shape as Ada's charge speed down 300% meaning charge time x4.
    scaled = spinup_with_speed(MG_SPINUP, -1.0, RATE_OF_FIRE_60FPS["MG"])
    assert scaled.seconds == pytest.approx(MG_SPINUP.seconds * 2)
    assert scaled.intervals == MG_SPINUP.intervals


def test_heating_speed_up_100_percent_halves_the_ramp():
    scaled = spinup_with_speed(MG_SPINUP, 1.0, RATE_OF_FIRE_60FPS["MG"])
    assert scaled.seconds == pytest.approx(MG_SPINUP.seconds / 2)
    assert scaled.intervals == MG_SPINUP.intervals


def test_the_ramp_can_never_beat_the_nominal_rate():
    """A warm-up is a slow start, not an accelerator. 137/60 sec over 48 gaps
    only reaches the nominal 48/60 at +185.4%, so clamp above that."""
    reached_at = MG_SPINUP.seconds / (MG_SPINUP.intervals / RATE_OF_FIRE_60FPS["MG"]) - 1
    assert reached_at == pytest.approx(1.854166, abs=1e-6)
    scaled = spinup_with_speed(MG_SPINUP, 5.0, RATE_OF_FIRE_60FPS["MG"])
    assert scaled.seconds == pytest.approx(
        MG_SPINUP.intervals / RATE_OF_FIRE_60FPS["MG"])
    assert scaled.intervals == MG_SPINUP.intervals


def test_an_unbuffed_unit_is_bit_identical_to_the_default():
    """The property the whole extension rests on: a unit with no heating buff
    fires at exactly the instants it always did, down to the float."""
    assert _one_magazine(heating_speed_percent_at=lambda _t: 0.0) == _one_magazine()
    plain = generate_segmented_shots(_mg_base(), [], fight_duration=60.0)
    explicit_zero = generate_segmented_shots(
        _mg_base(), [], fight_duration=60.0,
        heating_speed_percent_at=lambda _t: 0.0)
    assert [r.time for r in explicit_zero] == [r.time for r in plain]


def test_a_debuffed_magazine_takes_longer_to_empty():
    slowed = _one_magazine(heating_speed_percent_at=lambda _t: -1.0)
    assert slowed[MG_SPINUP.intervals] == pytest.approx(MG_SPINUP.seconds * 2)
    assert len(slowed) < len(_one_magazine())


def test_the_markers_follow_a_heated_magazine():
    """The first/last-bullet generators walk their own magazines, so a ramp
    they do not see would fire those triggers at instants no shot occupies."""
    heated = dict(heating_speed_percent_at=lambda _t: -1.0)
    shots = set(_one_magazine(**heated))
    firsts = magazine_first_bullet_times(
        rate_of_fire=RATE_OF_FIRE_60FPS["MG"], max_ammo=MAGAZINE,
        reload_time=RELOAD_FILE, fight_duration=60.0, weapon="MG", **heated)
    lasts = magazine_last_bullet_times(
        rate_of_fire=RATE_OF_FIRE_60FPS["MG"], max_ammo=MAGAZINE,
        reload_time=RELOAD_FILE, fight_duration=60.0, weapon="MG", **heated)
    assert firsts <= shots and lasts <= shots
    ordered = sorted(shots)
    assert ordered[0] in firsts
    assert ordered[MAGAZINE - 1] in lasts


def test_the_ramp_is_sampled_at_the_magazine_that_opens_under_it():
    """Same granularity as `shot_interval` and `capacity`, which this samples
    beside: a buff that lapses mid-magazine holds until the next one opens."""
    shots = _one_magazine(
        heating_speed_percent_at=lambda t: -1.0 if t < 5.0 else 0.0)
    assert shots[MG_SPINUP.intervals] == pytest.approx(MG_SPINUP.seconds * 2)
    second_magazine = shots[MAGAZINE]
    assert second_magazine > 5.0
    assert (shots[MAGAZINE + MG_SPINUP.intervals] - second_magazine
            == pytest.approx(MG_SPINUP.seconds))


def test_the_production_shot_pass_takes_the_heating_debuff():
    """`generate_segmented_shots` is the path every unit's weapon pass runs
    through, so the buff has to reach `_base_shot_records` as well."""
    slowed = generate_segmented_shots(
        _mg_base(), [], fight_duration=60.0,
        heating_speed_percent_at=lambda _t: -1.0)
    assert slowed[MG_SPINUP.intervals].time == pytest.approx(MG_SPINUP.seconds * 2)
    assert [r.time for r in slowed] == pytest.approx(
        _one_magazine(heating_speed_percent_at=lambda _t: -1.0))


def test_the_clamp_floor_ignores_attack_speed():
    """`spinup_with_speed`'s clamp keeps the ramp no tighter than the weapon's
    OWN nominal gap (`intervals / rate_of_fire`) - every call site threads in
    the weapon's nominal rate for that, not a rate an Attack Speed buff has
    already inflated (which would pull the floor tighter and let the ramp
    beat the un-buffed weapon's own cadence). Attack Speed +100% doubles the
    post-ramp cadence; a heating buff far past the +185.4% clamp point pins
    the ramp itself to the untouched 1/60 sec nominal gap regardless."""
    slowed = generate_segmented_shots(
        _mg_base(), [], fight_duration=60.0,
        attack_speed_percent_at=lambda _t: 1.0,
        heating_speed_percent_at=lambda _t: 10.0)
    ramp_total = slowed[MG_SPINUP.intervals].time - slowed[0].time
    assert ramp_total == pytest.approx(MG_SPINUP.intervals / RATE_OF_FIRE_60FPS["MG"])
    post_ramp_gap = (slowed[MG_SPINUP.intervals + 1].time
                      - slowed[MG_SPINUP.intervals].time)
    assert post_ramp_gap == pytest.approx(1 / (2 * RATE_OF_FIRE_60FPS["MG"]))


def test_a_weapon_class_with_no_warm_up_ignores_the_buff():
    """`heating` is an MG word; an AR has no ramp for it to scale."""
    ar = dict(rate_of_fire=RATE_OF_FIRE_60FPS["AR"], max_ammo=60,
              reload_time=1.0, fight_duration=60.0, weapon="AR")
    assert (generate_magazine_shot_times(**ar, heating_speed_percent_at=lambda _t: -1.0)
            == generate_magazine_shot_times(**ar))
