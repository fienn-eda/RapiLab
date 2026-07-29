"""FB 창 안의 샷 타임라인 (docs/superpowers/specs/2026-07-29-charge-window-calculator-design.md)."""
from dataclasses import replace

import pytest

from app.charge_window import (WindowInputs, aggregate_charge_speed,
                               aggregation_rules_disagree, charge_speed_steps,
                               outcome, reload_intervenes, shot_interval,
                               shot_times, thresholds)

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
    buffed = replace(SCARLET, charge_time_reduction_sec=LIBERALIO_CUT)
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
    small = replace(SCARLET, max_ammo=5)
    assert reload_intervenes(small) is True
    assert reload_intervenes(SCARLET) is False


def test_the_reload_gap_is_the_cube_buffed_one():
    # 5 rounds at 0.73 sec empty the magazine at 3.65 sec; the sixth shot comes
    # one buffed reload plus one charge later. reload_time_with_speed is the
    # engine's, so this test pins that the calculator does not restate it.
    from app.attack_rate import reload_time_with_speed

    small = replace(SCARLET, max_ammo=5)
    times = shot_times(small, start_charged=False)
    gap = times[5] - times[4]
    expected = reload_time_with_speed(2.0, 0.2969) + shot_interval(small)
    assert gap == pytest.approx(expected)


def test_charge_speed_steps_are_one_frame_apart():
    # Scarlet charges in 0.30 sec = 18 frames, so a frame costs 1/18 = 5.56%.
    steps = charge_speed_steps(0.30)
    assert steps[0] == pytest.approx(0.0)
    assert steps[1] == pytest.approx(1 / 18)
    assert steps[2] == pytest.approx(2 / 18)
    assert len(steps) == 19  # 0 frames through 18 (a charge of zero)


def test_a_step_below_the_next_frame_changes_nothing():
    # 2.86% and 5.0% both floor to zero frames of an 18-frame charge.
    quiet = replace(SCARLET, charge_speed_percent=0.05)
    assert shot_interval(quiet) == pytest.approx(shot_interval(SCARLET))


def test_aggregate_sums_the_lines_and_returns_a_ratio():
    assert aggregate_charge_speed([2.86], 0.30) == pytest.approx(0.0286)
    assert aggregate_charge_speed([4.33, 4.33], 0.30) == pytest.approx(0.0866)
    assert aggregate_charge_speed([], 0.30) == pytest.approx(0.0)


def test_the_two_aggregation_rules_are_compared_exactly():
    # Scarlet's 0.30 sec charge is 18 frames. One line of 5.51%: the engine's
    # raw sum buys floor(18 * 0.0551) = 0 frames, the community's rounding to 6%
    # buys 1. They disagree.
    assert aggregation_rules_disagree([5.51], 0.30) is True
    # Two lines of 4.33%: equal values sum to 8.66% before rounding, so 9% buys
    # floor(18 * 0.09) = 1 frame and the raw 8.66% buys 1 too. They agree.
    assert aggregation_rules_disagree([4.33, 4.33], 0.30) is False
    # Nothing rolled is nothing to disagree about.
    assert aggregation_rules_disagree([], 0.30) is False


def test_a_liberalio_sized_charge_is_judged_on_its_own_frame_grid():
    # Liberalio charges in 1.5 sec = 90 frames, so a frame is 1.11% and most
    # totals leave the two rules agreeing - the answer depends on the charge
    # time, not on a fixed band around the total.
    assert aggregation_rules_disagree([2.6], 1.5) is False
    assert aggregation_rules_disagree([4.33], 1.5) is False
    # 1.2% buys one frame raw; rounding it down to 1% buys none.
    assert aggregation_rules_disagree([1.2], 1.5) is True
    # Two 4.33% lines sum to 8.66% = 7 frames raw, but group and round to 9% = 8.
    assert aggregation_rules_disagree([4.33, 4.33], 1.5) is True


def test_outcome_splits_the_window_between_two_shot_counts():
    # At 0.53 sec a 10-second window holds 18.87 intervals, so the phase decides
    # between 19 and 18, and 19 comes up 87% of the time.
    buffed = replace(SCARLET, charge_time_reduction_sec=LIBERALIO_CUT)
    got = outcome(buffed)
    assert got.high_shots == 19
    assert got.low_shots == 18
    assert got.high_probability == pytest.approx(0.868, abs=0.005)
    assert got.low_probability == pytest.approx(1 - got.high_probability)


def test_a_reload_inside_the_window_still_splits_the_two_counts():
    # 6 rounds at 0.73 sec empty at 4.38 sec; after the buffed reload the 12th
    # shot lands at 9.572, only 0.428 sec of slack before the window closes. The
    # evenly-spaced fraction would read 10/0.73 - 11 = 2.7 and pin to a false
    # 100%; the timeline says 59%.
    small = replace(SCARLET, max_ammo=6)
    assert reload_intervenes(small) is True
    got = outcome(small)
    assert (got.high_shots, got.low_shots) == (12, 11)
    times = shot_times(small, start_charged=True)
    expected = (small.window_seconds - times[-1]) / shot_interval(small)
    assert got.high_probability == pytest.approx(expected)
    assert got.high_probability == pytest.approx(0.586, abs=0.005)
    assert got.low_probability == pytest.approx(1 - got.high_probability)


def test_thresholds_only_list_charge_speeds_that_change_the_interval():
    buffed = replace(SCARLET, charge_time_reduction_sec=LIBERALIO_CUT)
    got = thresholds(buffed)
    assert [round(t.charge_speed_percent * 100, 2) for t in got][:5] == [
        0.0, 5.56, 11.11, 16.67, 22.22]
    intervals = [t.interval for t in got]
    assert intervals == sorted(intervals, reverse=True), "each step must be faster"


def test_thresholds_carry_the_shot_counts_fienn_asked_about():
    buffed = replace(SCARLET, charge_time_reduction_sec=LIBERALIO_CUT)
    by_percent = {round(t.charge_speed_percent * 100, 2): t.outcome for t in thresholds(buffed)}
    assert by_percent[0.0].high_shots == 19
    assert by_percent[5.56].high_shots == 20
    assert by_percent[11.11].high_shots == 21
    assert by_percent[22.22].high_shots == 22


def test_a_small_magazine_caps_the_shots_no_matter_the_charge_speed():
    """Charge speed is wasted money once the magazine, not the cadence, is the
    binding constraint - the reload eats whatever the faster charge bought."""
    small = replace(SCARLET, max_ammo=6,
                                charge_time_reduction_sec=LIBERALIO_CUT)
    counts = {t.outcome.high_shots for t in thresholds(small)}
    roomy = replace(SCARLET, max_ammo=22,
                                charge_time_reduction_sec=LIBERALIO_CUT)
    assert max(counts) < max(t.outcome.high_shots for t in thresholds(roomy))
