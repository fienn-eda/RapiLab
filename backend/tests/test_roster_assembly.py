"""Parity: the API+calculator path must reproduce the collector's scraped roster."""
import json
from pathlib import Path
import pytest
from app.roster_assembly import assemble_roster, to_roster_json
from app.stat_assembly import load_stat_tables

ROOT = Path(__file__).resolve().parents[2]
ROSTER = ROOT / "tools" / "collect-blablalink" / "roster.json"
DETAILS = ROOT / "tools" / "collect-blablalink" / "details.json"
DIRECTORY = ROOT / "tools" / "collect-blablalink" / "nikke-directory.json"


@pytest.fixture(scope="module")
def tables():
    return load_stat_tables()


def test_assemble_roster_matches_the_collector_scrape(tables):
    if not (ROSTER.exists() and DETAILS.exists()):
        pytest.skip("local collector dumps not synced")
    directory = json.loads(DIRECTORY.read_text(encoding="utf-8"))
    raw = json.loads(DETAILS.read_text(encoding="utf-8"))
    scraped = {u["resource_id"]: u for u in json.loads(ROSTER.read_text(encoding="utf-8"))["units"]}

    out = {u["resource_id"]: u for u in assemble_roster(tables, directory, raw)}
    off = []
    for rid, want in scraped.items():
        got = out.get(rid)
        if got is None:
            off.append((want["name_en"], "missing from assembled"))
            continue
        # The model is documented accurate to <1.0 (stat_assembly.py's own fit
        # tolerance); rounding that float to an int can legitimately land ±1
        # from the scraped int without a mapping bug. A real join/field error
        # is off by thousands, so `> 1` still catches it.
        if abs(got["raid400"]["atk"] - want["raid400"]["atk"]) > 1:
            off.append((want["name_en"], "atk", got["raid400"]["atk"], want["raid400"]["atk"]))
        # Same rationale as atk above.
        if abs(got["raid400"]["hp"] - want["raid400"]["hp"]) > 1:
            off.append((want["name_en"], "hp", got["raid400"]["hp"], want["raid400"]["hp"]))
        gov = {o["name"]: round(o["value"], 2) for o in got.get("overload", [])}
        wov = {o["name"]: round(o["value"], 2) for o in (want.get("overload") or [])}
        if gov != wov:
            off.append((want["name_en"], "overload", gov, wov))
    assert off == [], off[:5]
