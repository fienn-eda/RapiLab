"""Tests for scripts/check_new_nikkes.py (pure comparison logic and
orchestration with a fake notifier - the headless dump is exercised only by
real runs)."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

import check_new_nikkes as chk


def _entry(rid, name, rare="SSR"):
    return {"resource_id": rid, "name_code": 3000 + rid, "name_en": name,
            "original_rare": rare, "class": "Attacker", "corporation": "ELYSION"}


def test_new_entries_finds_ids_absent_from_the_committed_snapshot():
    committed = [_entry(10, "Alpha")]
    fresh = [_entry(10, "Alpha"), _entry(20, "Bravo")]
    assert [e["name_en"] for e in chk.new_entries(committed, fresh)] == ["Bravo"]


def test_new_entries_is_empty_when_nothing_was_added():
    committed = [_entry(10, "Alpha"), _entry(20, "Bravo")]
    assert chk.new_entries(committed, list(committed)) == []


def test_new_entries_ignores_a_rename_of_an_existing_resource_id():
    # A renamed unit is not a release; only unseen resource_ids are.
    committed = [_entry(10, "Alpha")]
    fresh = [_entry(10, "Alpha Renamed")]
    assert chk.new_entries(committed, fresh) == []


def test_new_entries_ignores_entries_removed_from_the_directory():
    committed = [_entry(10, "Alpha"), _entry(20, "Bravo")]
    fresh = [_entry(10, "Alpha")]
    assert chk.new_entries(committed, fresh) == []


def test_new_ssr_filters_out_non_ssr_releases():
    entries = [_entry(20, "Bravo"), _entry(21, "Charlie", rare="SR")]
    assert [e["name_en"] for e in chk.new_ssr(entries)] == ["Bravo"]


def test_toast_body_lists_every_name_up_to_three():
    entries = [_entry(20, "Bravo"), _entry(21, "Charlie"), _entry(22, "Delta")]
    assert chk.toast_body(entries) == "Bravo, Charlie, Delta"


def test_toast_body_truncates_past_three_names():
    entries = [_entry(20 + i, n) for i, n in
               enumerate(["Bravo", "Charlie", "Delta", "Echo", "Foxtrot"])]
    assert chk.toast_body(entries) == "Bravo, Charlie, Delta 외 2명"


def test_run_offline_returns_zero_and_stays_silent_when_nothing_is_new(tmp_path):
    fresh = tmp_path / "fresh.json"
    fresh.write_text(json.dumps(chk.load_committed()), encoding="utf-8")
    sent = []
    assert chk.run(str(fresh), dry_run=False, notify=lambda t, b: sent.append((t, b))) == 0
    assert sent == []


def test_run_offline_returns_one_and_notifies_when_a_new_ssr_appears(tmp_path):
    committed = chk.load_committed()
    fresh = tmp_path / "fresh.json"
    fresh.write_text(json.dumps(committed + [_entry(999999, "Zulu")]), encoding="utf-8")
    sent = []
    assert chk.run(str(fresh), dry_run=False, notify=lambda t, b: sent.append((t, b))) == 1
    assert len(sent) == 1 and "Zulu" in sent[0][1]


def test_run_stays_silent_for_a_new_non_ssr(tmp_path):
    committed = chk.load_committed()
    fresh = tmp_path / "fresh.json"
    fresh.write_text(json.dumps(committed + [_entry(999999, "Zulu", rare="SR")]),
                     encoding="utf-8")
    sent = []
    assert chk.run(str(fresh), dry_run=False, notify=lambda t, b: sent.append((t, b))) == 0
    assert sent == []


def test_dry_run_does_not_notify_but_still_reports_the_finding(tmp_path):
    committed = chk.load_committed()
    fresh = tmp_path / "fresh.json"
    fresh.write_text(json.dumps(committed + [_entry(999999, "Zulu")]), encoding="utf-8")
    sent = []
    assert chk.run(str(fresh), dry_run=True, notify=lambda t, b: sent.append((t, b))) == 1
    assert sent == []
