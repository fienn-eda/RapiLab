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


def test_compare_unit_ignores_unreferenced_leftover_slot():
    # Reproduces brid-silent-track "Full Throttle": description interpolates
    # only _01 and _02; the leftover _04 duplicates the duration value and
    # must not be compared.
    dotgg_data = {"skills": [{
        "description": "ATK {description_value_01}% of caster's ATK for "
                        "{description_value_02} sec.",
        "levels": [_level(description_value_01="66.52",
                          description_value_02="10",
                          description_value_03="0",
                          description_value_04="10")],
    }]}
    lw_data = {"skills": [{
        "levels": ["ATK 66.52% of caster's ATK for 10 sec."]}]}
    found, warnings = drift.compare_unit(dotgg_data, lw_data,
                                         {"s1": ("skills", 0)})
    assert found == {}
    assert warnings == []


def test_compare_unit_still_drifts_on_referenced_slot_change():
    dotgg_data = {"skills": [{
        "description": "ATK {description_value_01}% of caster's ATK for "
                        "{description_value_02} sec.",
        "levels": [_level(description_value_01="66.52",
                          description_value_02="10",
                          description_value_03="0",
                          description_value_04="10")],
    }]}
    lw_data = {"skills": [{
        "levels": ["ATK 99.99% of caster's ATK for 10 sec."]}]}
    found, warnings = drift.compare_unit(dotgg_data, lw_data,
                                         {"s1": ("skills", 0)})
    assert found == {"s1": [(1, ["66.52"])]}
    assert warnings == []


def test_compare_unit_fallback_without_description_counts_all_slots():
    # No "description" key: current all-non-filler behavior is preserved, so
    # the same leftover-duplicate level as above still drifts.
    dotgg_data = {"skills": [{
        "levels": [_level(description_value_01="66.52",
                          description_value_02="10",
                          description_value_03="0",
                          description_value_04="10")],
    }]}
    lw_data = {"skills": [{
        "levels": ["ATK 66.52% of caster's ATK for 10 sec."]}]}
    found, warnings = drift.compare_unit(dotgg_data, lw_data,
                                         {"s1": ("skills", 0)})
    assert found == {"s1": [(1, ["10"])]}
    assert warnings == []


def _lw_page(name="Testy", values=("10.5", "20", "30")):
    """Minimal HTML that parse_html reads warning-free: h1, character-info
    alts, 3 skill titles, 10 level paragraphs each."""
    info = ('<div id="character-info"><img alt="Fire"><img alt="AR">'
            '<img alt="Attacker"><img alt="Burst 3"></div>')
    blocks = []
    for i, v in enumerate(values):
        levels = "".join(
            f'<p class="level-description" data-level="{n}">'
            f"ATK up {v}% for 5 sec.</p>" for n in range(10))
        blocks.append(f'<div class="skill-title-section"><h3>Skill {i}'
                      f"</h3></div>{levels}")
    return f"<h1>{name}</h1>{info}<div id=\"skills\">{''.join(blocks)}</div>"


def test_refresh_lw_writes_html_and_json(tmp_path):
    warnings = drift.refresh_lw(["testy"], tmp_path,
                                lambda slug: _lw_page(name="Testy"))
    assert warnings == []
    assert (tmp_path / "char_testy.html").exists()
    data = json.loads((tmp_path / "char_testy.json").read_text(encoding="utf-8"))
    assert data["name"] == "Testy" and data["source"] == "lootandwaifus"
    assert len(data["skills"][0]["levels"]) == 10


def test_refresh_lw_fetch_failure_is_warning_not_crash(tmp_path):
    def boom(slug):
        raise RuntimeError("curl failed")
    warnings = drift.refresh_lw(["testy"], tmp_path, boom)
    assert len(warnings) == 1 and "testy" in warnings[0]
    assert not (tmp_path / "char_testy.json").exists()


def _data_root(tmp_path, dotgg_values, lw_values):
    """data root with dotgg/char_x.json (url-field indexed) and
    lootandwaifus/char_x.json for slug "x"."""
    (tmp_path / "dotgg").mkdir(parents=True, exist_ok=True)
    (tmp_path / "lootandwaifus").mkdir(parents=True, exist_ok=True)
    dotgg_data, _ = _unit_data(dotgg_values)
    dotgg_data["url"] = "x"
    _, lw_data = _unit_data(lw_values)
    (tmp_path / "dotgg" / "char_x.json").write_text(
        json.dumps(dotgg_data), encoding="utf-8")
    (tmp_path / "lootandwaifus" / "char_x.json").write_text(
        json.dumps(lw_data), encoding="utf-8")
    return tmp_path


MANIFEST = {"x": {"source": "dotgg", "keys": {"s1": ("skills", 0)}}}


def test_run_check_ok_and_drift(tmp_path):
    root = _data_root(tmp_path, ["37.28"], ["37.28"])
    results, refresh_warnings = drift.run_check(
        MANIFEST, root / "lootandwaifus", root)
    assert refresh_warnings == []
    assert results["x"]["status"] == "OK"

    drifted = _data_root(tmp_path / "b", ["37.28"], ["99.99"])
    results, _ = drift.run_check(MANIFEST, drifted / "lootandwaifus", drifted)
    assert results["x"]["status"] == "DRIFT"
    assert results["x"]["drift"]["s1"][0][1] == ["37.28"]


def test_run_check_missing_lw_json_is_warn(tmp_path):
    root = _data_root(tmp_path, ["1"], ["1"])
    (root / "lootandwaifus" / "char_x.json").unlink()
    results, _ = drift.run_check(MANIFEST, root / "lootandwaifus", root)
    assert results["x"]["status"] == "WARN"
    assert "char_x.json" in results["x"]["warnings"][0]


def test_run_check_refreshes_before_comparing(tmp_path):
    root = _data_root(tmp_path, ["10.5"], ["99.99"])  # stale lw says 99.99
    results, refresh_warnings = drift.run_check(
        MANIFEST, root / "lootandwaifus", root,
        fetch_html=lambda slug: _lw_page(values=("10.5", "2", "3")))
    assert refresh_warnings == []
    assert results["x"]["status"] == "OK"  # fresh fetch wins over stale file
