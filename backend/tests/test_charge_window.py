"""FB 창 안의 샷 타임라인 (docs/superpowers/specs/2026-07-29-charge-window-calculator-design.md)."""
from dataclasses import replace

import pytest

from app.attack_rate import AmmoRefund
from app.charge_window import (WindowInputs, aggregate_charge_speed,
                               charge_speed_steps, outcome, reload_intervenes,
                               shot_interval, shot_times,
                               shots_without_magazine_limit, thresholds)

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
    # Main account, four Full Burst windows: 0.73371 sec apart. The bound is
    # loose because the 0.43 motion delay it rests on is itself only known to
    # the nearest 0.01 sec - see the grant test below for the tight anchor.
    assert shot_interval(SCARLET) == pytest.approx(0.73371, abs=0.35 / 60)


def test_interval_reproduces_the_liberalio_measurement():
    # Main account, two accompanied windows: 0.54352 sec apart.
    buffed = replace(SCARLET, charge_time_reduction_sec=LIBERALIO_CUT)
    assert shot_interval(buffed) == pytest.approx(0.54352, abs=0.35 / 60)


def test_liberalio_grant_matches_the_delay_free_measurement():
    """The one comparison that assumes nothing about the motion delay: solo
    minus accompanied, within one account, cancels it. Main account reads
    0.19019 sec (2026-07-30). Snapping the surviving charge to the frame grid
    would make it 0.20000 and miss by 0.59 frames."""
    buffed = replace(SCARLET, charge_time_reduction_sec=LIBERALIO_CUT)
    assert shot_interval(SCARLET) - shot_interval(buffed) == pytest.approx(
        0.19019, abs=0.1 / 60)


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


def test_aggregate_rounds_each_group_of_equal_rolls_to_a_whole_percent():
    """Prika settled this: a roll grants its rounded percent, not its exact one
    (docs/measurements/prika-charge.md). The aggregation is the calculator's
    single seam onto that rule."""
    assert aggregate_charge_speed([2.86]) == pytest.approx(0.03)
    assert aggregate_charge_speed([4.92]) == pytest.approx(0.05)
    assert aggregate_charge_speed([]) == pytest.approx(0.0)


def test_equal_rolls_sum_before_they_round_and_can_cost_a_point():
    """Grouping is not a rounding detail - it changes the answer, and not always
    in the player's favour. 4.63 rounds up alone but 9.26 rounds down together,
    so two of them grant 9 where rounding each would have granted 10."""
    assert aggregate_charge_speed([4.63, 4.63]) == pytest.approx(0.09)
    assert aggregate_charge_speed([4.63]) == pytest.approx(0.05)
    # The community post's worked example: 4.63 twice and 4.33 once is 9 + 4.
    assert aggregate_charge_speed([4.63, 4.63, 4.33]) == pytest.approx(0.13)
    # Unequal rolls do NOT share a group, so each rounds on its own.
    assert aggregate_charge_speed([4.63, 4.33]) == pytest.approx(0.09)


def test_the_rolls_are_needed_because_their_total_is_not_enough():
    """The reason `lines` is threaded all the way from the sync rather than a
    total being rounded on arrival: 2.28 + 4.92 and 2.57 + 4.63 both display
    7.20%, and they grant 7 and 8. A roster that only kept the total cannot tell
    which of those the player is holding."""
    assert sum([2.28, 4.92]) == pytest.approx(sum([2.57, 4.63]))
    assert aggregate_charge_speed([2.28, 4.92]) == pytest.approx(0.07)
    assert aggregate_charge_speed([2.57, 4.63]) == pytest.approx(0.08)


def test_outcome_splits_the_window_between_two_shot_counts():
    # At 0.5389 sec a 10-second window holds 18.56 intervals, so the phase
    # decides between 19 and 18, and 19 comes up 56% of the time.
    buffed = replace(SCARLET, charge_time_reduction_sec=LIBERALIO_CUT)
    got = outcome(buffed)
    assert got.high_shots == 19
    assert got.low_shots == 18
    assert got.high_probability == pytest.approx(0.556, abs=0.005)
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
    assert got.high_probability == pytest.approx(0.570, abs=0.005)
    assert got.low_probability == pytest.approx(1 - got.high_probability)


def test_thresholds_only_list_charge_speeds_that_change_the_interval():
    buffed = replace(SCARLET, charge_time_reduction_sec=LIBERALIO_CUT)
    got = thresholds(buffed)
    assert [round(t.charge_speed_percent * 100, 2) for t in got][:5] == [
        0.0, 5.56, 11.11, 16.67, 22.22]
    intervals = [t.interval for t in got]
    assert intervals == sorted(intervals, reverse=True), "each step must be faster"


def test_the_ladder_stops_at_a_total_the_player_cannot_reach():
    """Steps above what overload can actually grant are money that does not
    exist. Scarlet's grid moves every 5.56%, so a 24% ceiling makes 22.22% the
    last row anyone can buy - 27.78% is off the table, not merely expensive."""
    buffed = replace(SCARLET, charge_time_reduction_sec=LIBERALIO_CUT)
    rows = thresholds(buffed, ceiling=0.24)
    assert [round(row.charge_speed_percent * 100, 2) for row in rows] == [
        0.0, 5.56, 11.11, 16.67, 22.22]


def test_without_a_ceiling_the_ladder_runs_until_the_charge_is_gone():
    """No ceiling is the pure frame-grid question, and it ends where the charge
    does: at 38.89% Liberalio's cut already covers what is left of the 0.30 sec,
    so every faster step reads the same 0.43 motion delay and dedupes away."""
    buffed = replace(SCARLET, charge_time_reduction_sec=LIBERALIO_CUT)
    rows = thresholds(buffed)
    assert round(rows[-1].charge_speed_percent * 100, 2) == 38.89
    assert rows[-1].interval == pytest.approx(SCARLET.motion_delay)


def test_thresholds_carry_the_shot_counts_fienn_asked_about():
    """The question this calculator was built for: what charge-speed total buys
    19, 20, 21 shots. Each row's HIGH count is the one a favourable Full Burst
    entry reaches; the row's probability says how often."""
    buffed = replace(SCARLET, charge_time_reduction_sec=LIBERALIO_CUT)
    by_percent = {round(t.charge_speed_percent * 100, 2): t.outcome for t in thresholds(buffed)}
    assert by_percent[0.0].high_shots == 19
    assert by_percent[5.56].high_shots == 20
    assert by_percent[16.67].high_shots == 21
    assert by_percent[27.78].high_shots == 22
    # 11.11% buys a frame but not a shot - it only makes 20 likelier.
    assert by_percent[11.11].high_shots == 20
    assert by_percent[11.11].high_probability > by_percent[5.56].high_probability


def test_a_small_magazine_caps_the_shots_no_matter_the_charge_speed():
    """Charge speed is wasted money once the magazine, not the cadence, is the
    binding constraint - the reload eats whatever the faster charge bought."""
    small = replace(SCARLET, max_ammo=6,
                                charge_time_reduction_sec=LIBERALIO_CUT)
    counts = {t.outcome.high_shots for t in thresholds(small)}
    roomy = replace(SCARLET, max_ammo=22,
                                charge_time_reduction_sec=LIBERALIO_CUT)
    assert max(counts) < max(t.outcome.high_shots for t in thresholds(roomy))


def test_the_shots_a_magazine_costs_are_countable():
    """What the ladder cannot say on its own: whether a row is flat because of
    the cadence or because of the magazine. Fienn's synced Scarlet holds 18
    rounds and reads 18 shots at every step through 22.22%, while the cadence
    alone would have landed 19."""
    capped = replace(SCARLET, max_ammo=18, charge_time_reduction_sec=LIBERALIO_CUT)
    assert outcome(capped).high_shots == 18
    assert shots_without_magazine_limit(capped) == 19


def test_a_magazine_that_never_empties_costs_nothing():
    roomy = replace(SCARLET, charge_time_reduction_sec=LIBERALIO_CUT)
    assert reload_intervenes(roomy) is False
    assert shots_without_magazine_limit(roomy) == outcome(roomy).high_shots


def test_the_bear_refund_pushes_the_reload_past_the_window():
    """A Tactical Bear turns Scarlet's 18 rounds into 24 fired before the
    magazine empties, and the window closes long before that. It is the whole
    difference between the 18 shots the Resilience assumption reads and the even
    19 Fienn measures."""
    capped = replace(SCARLET, max_ammo=18, charge_time_reduction_sec=LIBERALIO_CUT)
    bear = replace(capped, ammo_refund=AmmoRefund(10, 3), reload_speed_percent=0.0)
    assert reload_intervenes(capped) is True
    assert outcome(capped).high_shots == 18
    assert reload_intervenes(bear) is False
    assert outcome(bear).high_shots == 19
