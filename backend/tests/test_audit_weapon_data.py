"""Tests for scripts/audit_weapon_data.py (pure comparison + the AllStep tolerance).

The audit's whole value is that "everything matches" is trustworthy, so what
needs proving is the opposite: that a wrong local value is actually reported.
A comparison that silently skips a field would report a clean roster forever.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

import audit_weapon_data as audit


def _live(**overrides):
    live = {
        "weapon": "SMG",
        "maxAmmo": 120,
        "damage": "8.73%",
        "reloadTime": 1.5,
        "chargeTime": 0.0,
        "chargeDamage": "100%",
        "element": "Iron",
        "burst": "1",
    }
    live.update(overrides)
    return live


def test_percent_formatting_is_not_a_mismatch():
    # dotgg writes "8.73%", a stub may write 8.73 - same number, same weapon
    local = {**_live(), "damage": 8.73, "chargeDamage": "100.0%"}
    assert audit.compare(local, _live(), audit.WEAPON_FIELDS) == {}


def test_wrong_value_is_reported_per_field():
    local = {**_live(), "maxAmmo": 119, "reloadTime": 9.9}
    diffs = audit.compare(local, _live(), audit.WEAPON_FIELDS)
    assert diffs == {"maxAmmo": (119, 120), "reloadTime": (9.9, 1.5)}


def test_missing_local_field_is_reported_not_skipped():
    local = {k: v for k, v in _live().items() if k != "chargeDamage"}
    diffs = audit.compare(local, _live(), audit.WEAPON_FIELDS)
    assert diffs == {"chargeDamage": ("<missing>", "100%")}


def test_field_absent_from_live_is_skipped():
    # a weapon-only hand stub carries no element/burst; that is not a mismatch
    live = {k: v for k, v in _live().items() if k not in ("element", "burst")}
    assert audit.compare({"weapon": "SMG"}, live, audit.META_FIELDS) == {}


FIXTURES = Path(__file__).resolve().parent / "fixtures" / "shiftypad"


def test_allstep_unit_still_yields_weapon_fields(tmp_path):
    """Red Hood's live burst is "AllStep", which normalize_shiftypad cannot map to
    a tier (it raises). The weapon fields are unaffected, so the audit must keep
    the unit and flag the burst rather than crash or drop it.

    Built by patching a committed fixture, so the test does not depend on
    gitignored collected data."""
    bundle = json.loads((FIXTURES / "rapi-red-hood.json").read_text(encoding="utf-8"))
    bundle["directory"]["use_burst_skill"] = "AllStep"
    (tmp_path / "16.json").write_text(json.dumps(bundle), encoding="utf-8")

    live = audit.load_live(tmp_path)[16]
    assert live["_burst_unmapped"] == "AllStep"
    assert live["weapon"] and live["maxAmmo"]


def test_step_unit_is_not_flagged(tmp_path):
    bundle = json.loads((FIXTURES / "rapi-red-hood.json").read_text(encoding="utf-8"))
    (tmp_path / "16.json").write_text(json.dumps(bundle), encoding="utf-8")

    live = audit.load_live(tmp_path)[16]
    assert live["_burst_unmapped"] is None
    assert live["burst"] == "3"
