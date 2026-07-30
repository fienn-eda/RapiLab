"""Tests for scripts/find_charge_rule_discriminators.py.

What needs proving is that the script does not send Fienn to record the wrong
unit. It reports "these two rules disagree on her by N frames", and a reading
taken on a unit where they actually agree costs a filming session and settles
nothing. So the cases pinned here are the ones a hand calculation gets wrong:
where the engine and the community rule land on the SAME frame despite the
percentages differing, and where a two-line total has more than one way to have
been rolled.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

import find_charge_rule_discriminators as finder


def _cents(*percents):
    return [round(percent * 100) for percent in percents]


def test_a_single_492_line_is_the_decisive_case_on_a_one_second_charge():
    """The experiment the docs point at. 4.92% of 60 frames is 2.952, which the
    engine floors to 2; rounding the line to a whole 5% buys 3. One frame, and
    4.92 has exactly one decomposition so the reading needs no assumption about
    which lines are equipped."""
    frames, cents = 60, _cents(4.92)
    assert finder.engine_frames(frames, sum(cents)) == 2
    assert finder.whole_percent_frames(frames, cents) == 3
    assert len(finder.decompositions(sum(cents))) == 1


def test_two_equal_433_lines_do_not_separate_the_engine_from_the_community_rule():
    """The case that reads as decisive and is not: grouping 4.33 twice rounds
    8.66 up to 9%, which buys 5 frames of 60 - and the engine's raw 8.66% floors
    to 5 as well. Only the ungrouped variant (two 4% lines, 8%) lands elsewhere,
    and no community source claims that one, so this reading cannot settle
    whether grouping happens."""
    frames, cents = 60, _cents(4.33, 4.33)
    assert finder.engine_frames(frames, sum(cents)) == 5
    assert finder.whole_percent_frames(frames, cents) == 5
    ungrouped = int(frames * sum(round(line / 100) for line in cents) / 100)
    assert ungrouped == 4


def test_scarlet_frame_count_hides_the_disagreement_a_one_second_charge_shows():
    """Charge time decides whether a rule difference is visible at all. The same
    4.92% that splits a 60-frame charge buys 0 frames of Scarlet's 18 either
    way, which is why the decisive unit had to be found rather than assumed."""
    cents = _cents(4.92)
    assert finder.engine_frames(18, sum(cents)) == 0
    assert finder.whole_percent_frames(18, cents) == 0


def test_a_percentage_difference_still_has_to_survive_the_frame_grid():
    """Crossing a rounding boundary is necessary but not sufficient. 4.33 twice
    groups to 9% against an ungrouped 8%, and 60 frames keep that apart (5 vs 4).
    2.57 twice groups to 5% against an ungrouped 6% - a bigger percentage gap -
    and the grid swallows it, because 3.0 and 3.6 both floor to 3. A candidate
    has to be checked against the frame count, not against the percentages."""
    grouped_433 = finder.whole_percent_frames(60, _cents(4.33, 4.33))
    ungrouped_433 = int(60 * sum(round(line / 100) for line in _cents(4.33, 4.33)) / 100)
    assert (grouped_433, ungrouped_433) == (5, 4)

    grouped_257 = finder.whole_percent_frames(60, _cents(2.57, 2.57))
    ungrouped_257 = int(60 * sum(round(line / 100) for line in _cents(2.57, 2.57)) / 100)
    assert (grouped_257, ungrouped_257) == (3, 3)


def test_decomposition_enumerates_every_way_a_total_could_have_rolled():
    """The roster stores an aggregate, so a total that several line combinations
    reach cannot pin the composition. 9.84 is 4.92 twice, and also four other
    multisets - the script only calls a unit decisive when they all agree."""
    found = finder.decompositions(984)
    assert [4.92, 4.92] in [[value / 100 for value in combo] for combo in found]
    assert len(found) == 5
    frames = 60
    assert {finder.whole_percent_frames(frames, combo) for combo in found} == {6}
    assert finder.engine_frames(frames, 984) == 5


def test_a_total_no_canonical_lines_can_reach_has_no_decomposition():
    """Guards the search rather than the arithmetic: a mistyped or stale total
    should come back empty instead of silently matching something close."""
    assert finder.decompositions(100) == []
    assert finder.decompositions(197) == []
    assert finder.decompositions(198) == [(198,)]


def test_every_canonical_line_value_is_reachable_on_its_own():
    for cents in finder.LINE_CENTS:
        assert (cents,) in finder.decompositions(cents)
