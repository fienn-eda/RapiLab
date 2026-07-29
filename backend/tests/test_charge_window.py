"""FB 창 안의 샷 타임라인 (docs/superpowers/specs/2026-07-29-charge-window-calculator-design.md)."""
import pytest

from app.charge_window import WindowInputs, reload_intervenes, shot_interval, shot_times

# Scarlet: Black Shadow as Fienn actually measured her (2026-07-29): a 0.30 sec
# charge, a 0.43 sec motion delay, and a 2.86% charge-speed overload too small
# to buy a frame of an 18-frame charge. Magazine is large enough that no reload
# lands inside the window, so these cases isolate the cadence.
SCARLET = WindowInputs(
    charge_time=0.30,
    motion_delay=0.43,
    max_ammo=22,
    reload_time=2.0,
    charge_speed_percent=0.0286,
    charge_time_reduction_sec=0.0,
    reload_speed_percent=0.2969,
)
LIBERALIO_CUT = 0.1274 * 1.5  # 0.1911 sec, her caster-based grant


def test_interval_reproduces_the_solo_measurement():
    # 14 shots 0.72998 sec apart. A third of a frame is the tolerance.
    assert shot_interval(SCARLET) == pytest.approx(0.72998, abs=1 / 180)


def test_interval_reproduces_the_liberalio_measurement():
    # Two runs, 0.52923 and 0.52709 sec. Carrying the unfloored 0.1089 charge
    # would give 0.5389 and fail both.
    buffed = dataclasses_replace(SCARLET, charge_time_reduction_sec=LIBERALIO_CUT)
    for measured in (0.52923, 0.52709):
        assert shot_interval(buffed) == pytest.approx(measured, abs=1 / 180)


def test_start_charged_lands_a_shot_at_zero():
    times = shot_times(SCARLET, start_charged=True)
    assert times[0] == pytest.approx(0.0)


def test_starting_empty_delays_the_first_shot_by_one_interval():
    times = shot_times(SCARLET, start_charged=False)
    assert times[0] == pytest.approx(shot_interval(SCARLET))


def test_every_shot_lands_strictly_inside_the_window():
    for start_charged in (True, False):
        times = shot_times(SCARLET, start_charged=start_charged)
        assert times, "the window must fit at least one shot"
        assert max(times) < SCARLET.window_seconds


def test_starting_charged_is_worth_exactly_one_shot_when_no_reload_lands():
    charged = len(shot_times(SCARLET, start_charged=True))
    empty = len(shot_times(SCARLET, start_charged=False))
    assert charged - empty == 1


def test_a_small_magazine_forces_a_reload_inside_the_window():
    small = dataclasses_replace(SCARLET, max_ammo=5)
    assert reload_intervenes(small) is True
    assert reload_intervenes(SCARLET) is False


def test_the_reload_gap_is_the_cube_buffed_one():
    # 5 rounds at 0.73 sec empty the magazine at 3.65 sec; the sixth shot comes
    # one buffed reload plus one charge later. reload_time_with_speed is the
    # engine's, so this test pins that the calculator does not restate it.
    from app.attack_rate import reload_time_with_speed

    small = dataclasses_replace(SCARLET, max_ammo=5)
    times = shot_times(small, start_charged=False)
    gap = times[5] - times[4]
    expected = reload_time_with_speed(2.0, 0.2969) + shot_interval(small)
    assert gap == pytest.approx(expected)


def dataclasses_replace(inputs, **changes):
    import dataclasses

    return dataclasses.replace(inputs, **changes)
