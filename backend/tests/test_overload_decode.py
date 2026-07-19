import json
from pathlib import Path

import pytest

from app.overload_decode import assemble_overload, decode_option
from app.stat_assembly import load_stat_tables

ROSTER = Path(__file__).resolve().parents[2] / "tools" / "collect-blablalink" / "roster.json"
DETAILS = Path(__file__).resolve().parents[2] / "tools" / "collect-blablalink" / "details.json"
DIRECTORY = Path(__file__).resolve().parents[2] / "tools" / "collect-blablalink" / "nikke-directory.json"


@pytest.fixture(scope="module")
def tables():
    return load_stat_tables()


def test_assemble_overload_reproduces_every_scraped_unit(tables):
    """The decoded+valued overload must equal ShiftyPad's parsed lines for all 77."""
    if not (ROSTER.exists() and DETAILS.exists()):
        pytest.skip("local collector dumps not synced")
    directory = {e["name_code"]: e for e in json.loads(DIRECTORY.read_text(encoding="utf-8"))}
    by_rid = {e["resource_id"]: e for e in directory.values()}
    raw = json.loads(DETAILS.read_text(encoding="utf-8"))
    details = {d["name_code"]: d for d in raw["character_details"]}
    off = []
    checked = 0
    for u in json.loads(ROSTER.read_text(encoding="utf-8"))["units"]:
        scraped = u.get("overload") or []
        if not scraped:
            continue
        entry = by_rid.get(u["resource_id"])
        d = details.get(entry["name_code"]) if entry else None
        if not d:
            continue
        checked += 1
        got = {o["name"]: round(o["value"], 2) for o in assemble_overload(tables, d)}
        want = {o["name"]: round(o["value"], 2) for o in scraped}
        if got != want:
            off.append((u["name_en"], got, want))
    assert checked == 77
    assert off == [], off[:5]


def test_decode_option_splits_type_and_level():
    # 700 TT LL: measured on ShiftyPad gear (probe 2026-07-19).
    assert decode_option(7000811) == (8, 11)   # type 8, level 11
    assert decode_option(7001002) == (10, 2)   # type 10, level 2
    assert decode_option(7000905) == (9, 5)


def test_decode_option_empty_slot_is_none():
    assert decode_option(0) is None


def test_decode_option_rejects_a_non_overload_id():
    # Anything not 700-prefixed and 7 digits is not an overload option.
    assert decode_option(3111001) is None   # an equip tid
    assert decode_option(123) is None
