"""Tests for scripts/roster_fixture.py - the bridge every measurement crosses.

The scripts read an exported drafts file, so anything this module drops is
invisible everywhere downstream while still looking like a clean run. Charge
speed is the sharp case: it rounds per gear roll, so a dropped `lines` leaves
the calibration estimating from totals no matter how recently the roster was
synced, and the re-sync that was supposed to fix it changes nothing.
"""
import argparse
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

import roster_fixture  # noqa: E402


def _draft(**over):
    draft = {
        "character_slug": "prika", "level": "200",
        "hp": "1000000", "atk": "100000", "def_": "10000",
        "skill_levels": {"skill1": "10", "skill2": "10", "burst": "10"},
        "overload_options": [],
    }
    return draft | over


def _write(tmp_path, drafts):
    path = tmp_path / "roster-drafts.json"
    path.write_text(json.dumps(drafts), encoding="utf-8")
    return path


def test_the_per_gear_rolls_reach_the_measurement_scripts(tmp_path):
    path = _write(tmp_path, [_draft(overload_options=[{
        "name": "차지 속도 증가", "value": "7.2",
        "lines": [{"slot": "head", "value": 2.57}, {"slot": "arm", "value": 4.63}],
    }])])
    [state] = roster_fixture.real_roster(path)
    [option] = state.overload_options
    assert [line.slot for line in option.lines] == ["head", "arm"]
    assert [line.value for line in option.lines] == [2.57, 4.63]


def test_a_roster_exported_before_rolls_existed_still_loads(tmp_path):
    """The drafts file is a personal export, so an old one has to keep working -
    it simply measures as the estimate it always was."""
    path = _write(tmp_path, [_draft(overload_options=[
        {"name": "차지 속도 증가", "value": "7.2"}])])
    [state] = roster_fixture.real_roster(path)
    assert state.overload_options[0].lines is None


def test_an_empty_lines_list_is_not_mistaken_for_known_rolls(tmp_path):
    """`[]` means the exporter had nothing to say, not "this unit rolled zero
    lines totalling 7.2" - keeping it would make the total unreachable."""
    path = _write(tmp_path, [_draft(overload_options=[
        {"name": "차지 속도 증가", "value": "7.2", "lines": []}])])
    [state] = roster_fixture.real_roster(path)
    assert state.overload_options[0].lines is None


def test_a_missing_roster_is_none_rather_than_a_crash(tmp_path):
    assert roster_fixture.real_roster(tmp_path / "absent.json") is None


def test_the_roster_flag_defaults_to_the_blessed_export():
    """One flag definition shared by five scripts, so the default cannot drift
    between them - and naming another account's export is a path away."""
    parser = argparse.ArgumentParser()
    roster_fixture.add_roster_argument(parser)
    assert parser.parse_args([]).roster == roster_fixture.REAL_ROSTER_JSON
    assert parser.parse_args(["--roster", "alt.json"]).roster == Path("alt.json")


@pytest.mark.parametrize("script", [
    "measure_record_calibration", "measure_deck_breakdown", "measure_thin_draft",
    "audit_swap_ordering", "measure_swap_phase",
])
def test_every_roster_reading_script_accepts_the_flag(script, capsys):
    """A script that reads the synced roster but cannot be pointed at another
    account's export silently measures the wrong one - comparing two accounts is
    the reason the flag exists (Scarlet's unresolved 9.5-sigma gap)."""
    module = __import__(script)
    with pytest.raises(SystemExit):
        sys.argv = [script, "--help"]
        module.main()
    assert "--roster" in capsys.readouterr().out
