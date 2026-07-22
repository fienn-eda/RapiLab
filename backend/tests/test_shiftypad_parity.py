"""Parity harness: the ShiftyPad normalizer must reproduce dotgg's data.

For each fixture unit, run normalize_shiftypad on its committed raw bundle and
assert the fields that feed the engine match the committed dotgg file exactly.
This proves the parser without backfilling: the fixtures span all six weapon
types, so the structural cases (charge vs magazine, slot counts) are all
covered. Depends on data/dotgg/ being synced (python3 scripts/sync_worktree_data.py).
"""
import json
from pathlib import Path

import pytest

from app.shiftypad_normalize import normalize_shiftypad
from app.skill_values import _dotgg_path_for

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "shiftypad"
DATA_DIR = Path(__file__).resolve().parents[2] / "data"

# fixture slug -> the dotgg "url" that names its ground-truth file
PARITY_UNITS = {
    "anis-sparkling-summer": "anis-sparkling-summer",
    "rapi-red-hood": "rapi-red-hood",
    "anis-star": "anis-star",
    "miranda": "miranda",
    "d-killer-wife": "d-killer-wife",
    "julia": "julia",
}

WEAPON_FIELDS = ("weapon", "maxAmmo", "damage", "reloadTime", "chargeTime", "chargeDamage")


def _normalized(slug):
    bundle = json.loads((FIXTURES / f"{slug}.json").read_text(encoding="utf-8"))
    return normalize_shiftypad(bundle)


def _dotgg(url):
    return json.loads(_dotgg_path_for(url, DATA_DIR).read_text(encoding="utf-8"))


@pytest.mark.parametrize("slug,url", PARITY_UNITS.items())
def test_weapon_fields_match_dotgg(slug, url):
    got, truth = _normalized(slug), _dotgg(url)
    assert {f: got[f] for f in WEAPON_FIELDS} == {f: truth[f] for f in WEAPON_FIELDS}


@pytest.mark.parametrize("slug,url", PARITY_UNITS.items())
def test_meta_matches_dotgg(slug, url):
    got, truth = _normalized(slug), _dotgg(url)
    assert got["element"] == truth["element"]
    assert got["burst"] == truth["burst"]


@pytest.mark.parametrize("slug,url", PARITY_UNITS.items())
def test_skill_ladders_match_dotgg(slug, url):
    got, truth = _normalized(slug), _dotgg(url)
    for i in range(3):
        # dotgg keeps empty trailing slots (""); the normalizer emits exactly
        # the slots ShiftyPad carries, so compare only the slots dotgg fills.
        for lvl_got, lvl_truth in zip(got["skills"][i]["levels"], truth["skills"][i]["levels"]):
            filled = {k: v for k, v in lvl_truth.items() if v != ""}
            assert {k: lvl_got.get(k) for k in filled} == filled


@pytest.mark.parametrize("slug,url", PARITY_UNITS.items())
def test_burst_cooldown_matches_dotgg(slug, url):
    got, truth = _normalized(slug), _dotgg(url)
    assert got["skills"][2]["cooldown"] == float(truth["skills"][2]["cooldown"])
