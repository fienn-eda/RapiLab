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


def test_load_live_keys_by_resource_id(tmp_path):
    """The audit joins a slug to live data through the raw file's name, so a
    mis-keyed bundle would compare a unit against someone else's weapon."""
    bundle = json.loads((FIXTURES / "rapi-red-hood.json").read_text(encoding="utf-8"))
    (tmp_path / "16.json").write_text(json.dumps(bundle), encoding="utf-8")

    live = audit.load_live(tmp_path)
    assert set(live) == {16}
    assert live[16]["weapon"] and live[16]["burst"] == "3"


def test_an_unregistered_clip_weapon_is_a_mismatch():
    # The failure this guards: a newly onboarded clip Nikke nobody added to
    # CLIP_RELOAD_SPLITS reads as 11% faster than she fires, and nothing else
    # in the pipeline would say so.
    assert audit.reload_splits_diff("liter", {"max_ammo": 6, "reload_bullet": 3300}) == (1, 3)


def test_a_registered_clip_weapon_agrees():
    assert audit.reload_splits_diff("centi", {"max_ammo": 6, "reload_bullet": 3300}) is None


def test_an_ordinary_weapon_agrees():
    assert audit.reload_splits_diff("liter", {"max_ammo": 120, "reload_bullet": 10000}) is None


def test_a_stale_table_entry_is_a_mismatch():
    # The mirror case: a balance patch that makes Centi load her whole magazine
    # at once leaves the table one reload too slow.
    assert audit.reload_splits_diff("centi", {"max_ammo": 6, "reload_bullet": 10000}) == (3, 1)
