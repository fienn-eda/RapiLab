"""Tests for scripts/audit_charge_speed_rolls.py.

What needs proving is that the script's verdict - "this unit's frame count is
undecided until someone knows the rolls" - is right, because that verdict is
what sends Fienn to re-sync a roster. The cases pinned here are the ones a hand
calculation gets wrong: totals that several line multisets reach and every one
of them agrees on, a total where they do not, and the grouping rule's own
counter-intuitive direction (two equal rolls can buy LESS than the same two
rolls counted apart).

The script calls the engine's aggregation rather than restating it, so these
tests also fail if that rule moves - which is the point. Its predecessor kept a
private copy and went stale silently.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

import audit_charge_speed_rolls as audit


def _cents(*percents):
    return [round(percent * 100) for percent in percents]


def test_a_single_492_line_buys_a_frame_the_raw_sum_would_not():
    """The measurement that settled the rule (Prika, 6.22 sigma). 4.92% of 60
    frames is 2.952 raw; rounding the roll to a whole 5% buys 3. One decomposition,
    so the reading needed no assumption about which lines were equipped."""
    assert audit.frames_bought(1.0, _cents(4.92)) == 3
    assert len(audit.decompositions(492)) == 1


def test_grouping_equal_rolls_can_cost_a_whole_percent():
    """Two 4.63 rolls group to 9.26 and round DOWN to 9%, where rounding each on
    its own would give 5 + 5 = 10%. Grouping is not a bonus - it is the rule, and
    here it takes a point away."""
    assert audit.frames_bought(1.0, _cents(4.63, 4.63)) == 5      # 9% of 60
    apart = audit.frames_bought(1.0, _cents(4.63)) * 2            # 5% twice
    assert apart == 6


def test_the_community_example_separates_rolls_from_their_total():
    """4.63 / 4.63 / 4.33 grants 9 + 4 = 13%, while the 13.59% total a roster
    displays rounds to 14%. On a 1-sec charge that is 7 frames against 8 - the
    exact gap a rolls-free roster cannot close."""
    rolls = _cents(4.63, 4.63, 4.33)
    assert audit.frames_bought(1.0, rolls) == 7
    assert audit.frames_bought(1.0, [sum(rolls)]) == 8


def test_a_total_every_decomposition_agrees_on_needs_no_rolls():
    """9.84 is 4.92 twice, and four other multisets besides - but all five buy 6
    frames, and so does the total read as one roll. Re-syncing would tell nobody
    anything about this unit."""
    fallback, outcomes, combos = audit.roll_outcomes(1.0, 984)
    assert len(combos) == 5
    assert [4.92, 4.92] in [[value / 100 for value in combo] for combo in combos]
    assert outcomes == {6}
    assert fallback == 6


def test_a_total_its_decompositions_disagree_on_is_flagged():
    """Neon: Vision Eye's 9.47% is the live case: twelve multisets reach it and
    they do not land on the same frame, so the total alone cannot say whether she
    buys 5 frames or 6."""
    fallback, outcomes, combos = audit.roll_outcomes(1.0, 947)
    assert len(combos) == 12
    assert outcomes == {5, 6}
    assert fallback == 5


def test_a_short_charge_swallows_a_difference_a_long_one_shows():
    """Charge time decides whether any of this is visible. The same 4.92% that
    buys a frame of a 60-frame charge buys none of Scarlet's 18."""
    assert audit.frames_bought(0.30, _cents(4.92)) == 0
    assert audit.frames_bought(0.30, [492]) == 0


def test_a_total_no_canonical_lines_can_reach_has_no_decomposition():
    """Guards the search rather than the arithmetic: a mistyped or stale total
    should come back empty instead of silently matching something close."""
    assert audit.decompositions(100) == []
    assert audit.decompositions(197) == []
    assert audit.decompositions(198) == [(198,)]


def test_every_canonical_line_value_is_reachable_on_its_own():
    for cents in audit.LINE_CENTS:
        assert (cents,) in audit.decompositions(cents)
