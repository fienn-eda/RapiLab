import json
import logging
from pathlib import Path

import pytest

from app.overload_decode import (assemble_overload, charge_speed_percent_from_lines,
                                 decode_option, overload_value)
from app.stat_assembly import load_stat_tables

ROSTER = Path(__file__).resolve().parents[2] / "tools" / "collect-blablalink" / "roster.json"
DETAILS = Path(__file__).resolve().parents[2] / "tools" / "collect-blablalink" / "details.json"
DIRECTORY = Path(__file__).resolve().parents[2] / "tools" / "collect-blablalink" / "nikke-directory.json"


@pytest.fixture(scope="module")
def tables():
    return load_stat_tables()


def test_assemble_overload_reproduces_every_scraped_unit(tables):
    """The decoded+valued overload must equal ShiftyPad's parsed lines.

    Two independent reads of the same gear: `--details` gives option ids (effect
    type + level, no values), the scrape gives summed percentages (values, no
    levels). Agreement means the id decode AND the value table are both right.

    The coverage assertion is derived from the roster rather than pinned to a
    count, because the count is how many units happen to wear overload today -
    it grew from 77 to 78 between two syncs. What must hold is that no unit with
    a scraped overload was skipped for want of a details entry.
    """
    if not (ROSTER.exists() and DETAILS.exists()):
        pytest.skip("local collector dumps not synced")
    directory = {e["name_code"]: e for e in json.loads(DIRECTORY.read_text(encoding="utf-8"))}
    by_rid = {e["resource_id"]: e for e in directory.values()}
    raw = json.loads(DETAILS.read_text(encoding="utf-8"))
    details = {d["name_code"]: d for d in raw["character_details"]}
    units = json.loads(ROSTER.read_text(encoding="utf-8"))["units"]
    off = []
    checked = 0
    for u in units:
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
    wearing_overload = sum(1 for u in units if u.get("overload"))
    assert checked == wearing_overload
    # A roster that scraped no overload at all would make the comparison vacuous,
    # and that is exactly what a page rewording produced once (RECIPE §f).
    assert checked > 0
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


def test_every_observed_level_returns_the_table_value_verbatim(tables):
    """Filling the gaps must not perturb a single level the roster actually measured."""
    for etype, levels in tables["overload"]["values"].items():
        for level, value in levels.items():
            assert overload_value(tables, int(etype), int(level)) == pytest.approx(value, abs=0.005)


def test_an_unobserved_level_lands_on_the_types_linear_curve(tables):
    """Each type is an arithmetic progression in level, so a gap is determined, not guessed.

    Types 8 and 9 share an identical curve on every level both were measured at,
    and only 8 was rolled at 15 - so 9's unobserved 15 predicting 8's measured
    14.63 is an independent check that the fill is right rather than merely smooth.
    """
    assert overload_value(tables, 9, 15) == pytest.approx(14.63, abs=0.01)
    # Below the observed floor (type 12 was never rolled at 1) and inside a gap.
    assert overload_value(tables, 12, 1) == pytest.approx(6.64, abs=0.01)
    assert overload_value(tables, 7, 12) == pytest.approx(73.04, abs=0.01)


def test_a_level_outside_the_roll_range_is_rejected(tables):
    """1..15 is the whole roll range; anything else means the id decode is wrong."""
    for bad in (0, 16):
        with pytest.raises(KeyError):
            overload_value(tables, 8, bad)


def _detail_with(option_id: int) -> dict:
    return {"head_equip_option1_id": option_id}


def test_an_unknown_effect_type_is_skipped_with_a_warning(tables, caplog):
    """A type this roster never rolled must not crash another user's sync.

    Type 4 is absent from both the value and the name table. The unit still
    assembles; the option is dropped and reported so the tables can be filled in.
    """
    with caplog.at_level(logging.WARNING):
        lines = assemble_overload(tables, _detail_with(7000405))
    assert lines == []
    assert "4" in caplog.text and "5" in caplog.text


def test_a_known_type_at_an_unobserved_level_is_kept(tables):
    """The fill means an unmeasured roll is valued, not dropped."""
    lines = assemble_overload(tables, _detail_with(7000915))
    assert lines == [{
        "name": "차지 대미지 증가",
        "value": pytest.approx(14.63, abs=0.01),
        "lines": [{"slot": "head", "value": pytest.approx(14.63, abs=0.01)}],
    }]


def test_the_rolls_behind_a_total_survive_as_lines(tables):
    """A total cannot be decomposed back into the rolls that made it, and charge
    speed rounds per roll - so the rolls have to be carried, tagged with the slot
    a future per-piece view would label them by.

    The rolls here are the community post's own worked example: charge speed at
    level 10 twice and level 9 once, which it reports as 9 + 4 = 13%."""
    detail = {"head_equip_option1_id": 7001010,   # charge speed lv10 = 4.63
              "arm_equip_option1_id": 7001010,    # the same roll on another piece
              "torso_equip_option1_id": 7001009}  # lv9 = 4.33
    [row] = assemble_overload(tables, detail)
    assert [line["slot"] for line in row["lines"]] == ["head", "torso", "arm"]
    assert row["value"] == pytest.approx(13.59, abs=0.01)
    # Two of the three rolls are equal - exactly what a total cannot recover.
    values = [line["value"] for line in row["lines"]]
    assert values[0] == values[2] and values[0] != values[1]
    assert charge_speed_percent_from_lines(values) == 13
