"""Tests for scripts/check_skill_value_drift.py (pure comparison logic and
orchestration with fakes - the curl path is exercised only by real runs)."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

import check_skill_value_drift as drift


def _level(**slots):
    """dotgg level dict helper: _level(description_value_01="10", ...)"""
    return dict(slots)


def test_dotgg_level_values_skips_empty_and_zero_filler():
    level = _level(description_value_01="60", description_value_02="10",
                   description_value_03="0", description_value_04="")
    assert drift.dotgg_level_values(level) == ["60", "10"]


def test_level_missing_all_present_is_empty():
    level = _level(description_value_01="40", description_value_02="10")
    text = "Max Ammunition Capacity 40% for 10 sec."
    assert drift.level_missing(level, text) == []


def test_level_missing_reports_drifted_value():
    level = _level(description_value_01="250.47")
    text = "Deals 283.03% of final ATK as damage."
    assert drift.level_missing(level, text) == ["250.47"]


def test_level_missing_is_multiset():
    # two identical dotgg values need two tokens in the text
    level = _level(description_value_01="10", description_value_02="10")
    assert drift.level_missing(level, "lasts 10 sec") == ["10"]
    assert drift.level_missing(level, "10 sec, again 10 sec") == []


def test_level_missing_matches_numerically():
    # "500" matches the "500.00" token (float compare), extra tokens are fine
    level = _level(description_value_01="500")
    text = "Deals 500.00% of ATK as damage 3 times."
    assert drift.level_missing(level, text) == []


def _unit_data(values, array="skills", levels=10):
    """Build matching dotgg/lw structures: one skill whose every level
    carries the given slot values (dotgg) / a text containing them (lw)."""
    dotgg_levels = [{f"description_value_{i+1:02d}": v
                     for i, v in enumerate(values)} for _ in range(levels)]
    lw_levels = ["Effect " + " and ".join(f"{v}%" for v in values)
                 for _ in range(levels)]
    return ({array: [{"levels": dotgg_levels}]},
            {array: [{"levels": lw_levels}]})


def test_compare_unit_ok():
    dotgg_data, lw_data = _unit_data(["37.28", "5"])
    found, warnings = drift.compare_unit(dotgg_data, lw_data,
                                         {"s1": ("skills", 0)})
    assert found == {}
    assert warnings == []


def test_compare_unit_reports_drift_with_level_numbers():
    dotgg_data, lw_data = _unit_data(["37.28"])
    dotgg_data["skills"][0]["levels"][9]["description_value_01"] = "99.99"
    found, warnings = drift.compare_unit(dotgg_data, lw_data,
                                         {"s1": ("skills", 0)})
    assert found == {"s1": [(10, ["99.99"])]}
    assert warnings == []


def test_compare_unit_warns_on_missing_array():
    dotgg_data, _ = _unit_data(["10"], array="dollskills")
    found, warnings = drift.compare_unit(dotgg_data, {"skills": []},
                                         {"sig": ("dollskills", 0)})
    assert found == {}
    assert len(warnings) == 1 and "dollskills[0]" in warnings[0]


def test_compare_unit_warns_on_level_count_mismatch():
    dotgg_data, lw_data = _unit_data(["10"])
    lw_data["skills"][0]["levels"] = lw_data["skills"][0]["levels"][:7]
    found, warnings = drift.compare_unit(dotgg_data, lw_data,
                                         {"s1": ("skills", 0)})
    assert found == {}
    assert len(warnings) == 1 and "level count mismatch" in warnings[0]
