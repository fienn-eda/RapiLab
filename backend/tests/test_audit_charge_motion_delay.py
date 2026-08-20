"""Tests for scripts/audit_charge_motion_delay.py and the tables it reads.

The audit's job is to keep asking about charge weapons nobody has timed, and its
failure mode is being ignored: a tool that is red every run stops being read. So
what needs proving is that the two kinds of untimed unit are told apart - the one
still waiting for a clock, and the ones whose stand-in was measured to be good
enough - and that separating them does not change any damage.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

import audit_charge_motion_delay as audit  # noqa: E402

from app.skill_rules.registry import (  # noqa: E402
    ASSUMED_CHARGE_MOTION_DELAY_SECONDS,
    INFERRED_NO_CHARGE_MOTION_DELAY,
    NO_CHARGE_MOTION_DELAY,
    STAND_IN_ACCEPTED_CHARGE_MOTION_DELAY,
    TIMED_CHARGE_MOTION_DELAY,
    _ASSUMED_CHARGE_MOTION_DELAY,
    get_charge_motion_delay,
    is_tap_fire_candidate,
)


def test_no_charge_weapon_is_waiting_for_a_timing():
    """Milk was the last one worth a clock and Fienn timed her, so this group is
    empty until a newly encoded charge weapon joins it."""
    assert _ASSUMED_CHARGE_MOTION_DELAY == frozenset()


def test_milk_is_timed_at_the_frame_her_reading_lands_on():
    """Her 9 delay readings average 21.889 frames, which rounds to the same 22
    the stand-in carries - so registering her moves no damage, and the point of
    the entry is that it is now a measurement rather than a guess."""
    assert TIMED_CHARGE_MOTION_DELAY["milk-blooming-bunny"] == 22 / 60


def test_ein_carries_her_auto_reading_and_not_her_manual_one():
    """아인은 자동으로 도는 좌석이라 표에 들어갈 값이 자동 판독이다.

    같은 계정에서 두 조작을 다 쟀고 **8.4프레임** 벌어졌다 - 자동 22.524f, 수동
    14.143f(docs/measurements/ein-tap-fire.md). 수동 쪽이 더 정밀해 보이지만 그것은
    **손으로 치는 좌석에만** 해당하고, 그런 좌석은 `TAP_FIRE_CANDIDATES`뿐이다.
    이 테스트는 누가 "더 잘 잰 값"이라며 수동 판독으로 갈아끼우면 깨진다.
    """
    assert TIMED_CHARGE_MOTION_DELAY["ein"] == 22 / 60
    assert not is_tap_fire_candidate("ein")


def test_the_two_stand_in_groups_are_disjoint():
    assert not (_ASSUMED_CHARGE_MOTION_DELAY & STAND_IN_ACCEPTED_CHARGE_MOTION_DELAY)


def test_accepting_the_stand_in_changes_no_damage():
    """The split is a change of QUESTION, not of model: both groups carry the
    same stand-in, so no unit's shot timeline moves."""
    for slug in STAND_IN_ACCEPTED_CHARGE_MOTION_DELAY | _ASSUMED_CHARGE_MOTION_DELAY:
        assert get_charge_motion_delay(slug) == ASSUMED_CHARGE_MOTION_DELAY_SECONDS


def test_a_timed_unit_is_never_carrying_a_stand_in():
    timed = set(TIMED_CHARGE_MOTION_DELAY)
    assert not (timed & STAND_IN_ACCEPTED_CHARGE_MOTION_DELAY)
    assert not (timed & _ASSUMED_CHARGE_MOTION_DELAY)


def test_status_for_separates_the_accepted_stand_in_from_the_open_question():
    assert audit.status_for("rouge") == "stand-in (accepted)"
    assert audit.status_for("milk-blooming-bunny") == "TIMED"
    assert audit.status_for("mint") == "TIMED"
    assert audit.status_for("liberalio") == "none (confirmed)"
    assert audit.status_for("cinderella") == "none (confirmed)"


def test_cinderella_no_longer_rests_on_an_inference():
    """Her zero came off the rate-of-fire table until Fienn timed 37 shots: the
    mean interval is 19.583 frames, which rules out a 22-frame pause at 15.5
    sigma and leaves the floor model standing."""
    assert "cinderella" in NO_CHARGE_MOTION_DELAY
    assert "cinderella" not in INFERRED_NO_CHARGE_MOTION_DELAY


def test_no_charge_weapon_is_left_unanswered():
    """Both open groups are empty, which is what makes the audit exit 0. A newly
    encoded charge weapon lands in `assumed` and turns it red again.

    Asserted on the tables rather than by walking every slug: the walk needs the
    gitignored weapon dumps to tell a charge weapon from the rest, so it would
    pass vacuously on a checkout that has none.
    """
    assert _ASSUMED_CHARGE_MOTION_DELAY == frozenset()
    assert INFERRED_NO_CHARGE_MOTION_DELAY == frozenset()


def test_an_accepted_stand_in_is_not_an_unanswered_question():
    """The exit code is the whole point: accepted rows must not keep it red, or
    the audit says 'ask Fienn' forever and nobody reads it again."""
    assert not audit.is_unanswered("stand-in (accepted)")
    assert audit.is_unanswered("assumed")
    assert audit.is_unanswered("UNVERIFIED")
    assert audit.is_unanswered("none (inferred)")
    assert not audit.is_unanswered("TIMED")
    assert not audit.is_unanswered("none (confirmed)")
