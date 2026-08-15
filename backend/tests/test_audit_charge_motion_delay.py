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
    STAND_IN_ACCEPTED_CHARGE_MOTION_DELAY,
    TIMED_CHARGE_MOTION_DELAY,
    _ASSUMED_CHARGE_MOTION_DELAY,
    get_charge_motion_delay,
)


def test_only_milk_is_still_waiting_for_a_timing():
    """Every other untimed charge weapon was measured to barely depend on the
    value (scripts/measure_charge_delay_sensitivity.py), so she is the only one
    left worth a clock."""
    assert _ASSUMED_CHARGE_MOTION_DELAY == frozenset({"milk-blooming-bunny"})


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
    assert audit.status_for("milk-blooming-bunny") == "assumed"
    assert audit.status_for("mint") == "TIMED"
    assert audit.status_for("liberalio") == "none (confirmed)"
    assert audit.status_for("cinderella") == "none (inferred)"


def test_an_accepted_stand_in_is_not_an_unanswered_question():
    """The exit code is the whole point: accepted rows must not keep it red, or
    the audit says 'ask Fienn' forever and nobody reads it again."""
    assert not audit.is_unanswered("stand-in (accepted)")
    assert audit.is_unanswered("assumed")
    assert audit.is_unanswered("UNVERIFIED")
    assert audit.is_unanswered("none (inferred)")
    assert not audit.is_unanswered("TIMED")
    assert not audit.is_unanswered("none (confirmed)")
