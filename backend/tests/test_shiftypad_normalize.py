"""Tests for backend/app/shiftypad_normalize.py against committed fixtures."""
import json
from pathlib import Path

from app.shiftypad_normalize import clip_reload_splits, normalize_shiftypad

FIXTURES = Path(__file__).resolve().parent / "fixtures" / "shiftypad"


def _bundle(slug):
    return json.loads((FIXTURES / f"{slug}.json").read_text(encoding="utf-8"))


def test_weapon_fields_use_dotgg_fixed_point():
    out = normalize_shiftypad(_bundle("rapi-red-hood"))
    assert out["weapon"] == "MG"
    assert out["maxAmmo"] == 300
    assert out["damage"] == "5.57%"
    assert out["reloadTime"] == 2.5
    assert out["chargeTime"] == 0
    assert out["chargeDamage"] == "100%"


def test_meta_from_directory():
    out = normalize_shiftypad(_bundle("rapi-red-hood"))
    assert out["element"] == "Fire"
    assert out["burst"] == "3"


def test_burst_cooldown_is_centiseconds_over_100():
    out = normalize_shiftypad(_bundle("rapi-red-hood"))
    assert out["skills"][2]["cooldown"] == 40


def test_skill_ladder_is_transposed_to_dotgg_shape():
    out = normalize_shiftypad(_bundle("rapi-red-hood"))
    level1 = out["skills"][0]["levels"][0]
    assert level1["description_value_01"] == "1"
    assert level1["description_value_02"] == "5.34"
    assert level1["description_value_03"] == "59.4"
    # every skill carries all 10 levels
    assert all(len(s["levels"]) == 10 for s in out["skills"])


def test_charge_weapon_full_charge_damage():
    out = normalize_shiftypad(_bundle("anis-star"))  # RL
    assert out["weapon"] == "RL"
    assert out["chargeTime"] == 1
    assert out["chargeDamage"] == "250%"


def test_electronic_element_maps_to_electric():
    # ShiftyPad's directory reports the electric-code element as "Electronic";
    # dotgg and the engine's elements.py both call it "Electric" -- an
    # unmapped name breaks element-advantage lookups for these units.
    out = normalize_shiftypad(_bundle("anis-star"))
    assert out["element"] == "Electric"
    dotgg = json.loads((Path(__file__).resolve().parent.parent.parent / "data" / "dotgg" / "char_anis-star.json").read_text(encoding="utf-8"))
    assert out["element"] == dotgg["element"]


def test_burst_is_a_dotgg_style_string():
    out = normalize_shiftypad(_bundle("rapi-red-hood"))
    assert out["burst"] == "3"
    assert isinstance(out["burst"], str)


def test_empty_slots_produce_dotgg_matching_level_dict():
    # rapi-red-hood's skill1 has 11 description_value slots but only 8 carry
    # real data; slots 9-11 come back from ShiftyPad as bare `{}` (no
    # "description_value" key). The normalizer must fill "" for those rather
    # than raising or dropping the slot, matching dotgg's own convention.
    out = normalize_shiftypad(_bundle("rapi-red-hood"))
    level1 = out["skills"][0]["levels"][0]
    assert level1["description_value_09"] == ""
    assert level1["description_value_10"] == ""
    assert level1["description_value_11"] == ""

    dotgg = json.loads(
        (Path(__file__).resolve().parent.parent.parent / "data" / "dotgg" / "char_rapi-red-hood.json").read_text(
            encoding="utf-8"
        )
    )
    assert level1 == dotgg["skills"][0]["levels"][0]


def _shot(max_ammo, reload_bullet):
    return {"max_ammo": max_ammo, "reload_bullet": reload_bullet}


def test_whole_magazine_reload_is_one_split():
    assert clip_reload_splits(_shot(300, 10000)) == 1


def test_centi_loads_a_six_round_magazine_two_at_a_time():
    # 6 x 33% = 2 rounds a load, so three loads - Fienn watched exactly this
    # (2026-07-30) and the data agrees, which is what pins the field's meaning.
    assert clip_reload_splits(_shot(6, 3300)) == 3


def test_a_nine_round_shotgun_also_takes_three_loads():
    assert clip_reload_splits(_shot(9, 3300)) == 3


def test_grave_reloads_her_sixty_rounds_in_halves():
    assert clip_reload_splits(_shot(60, 5000)) == 2


def test_split_count_survives_a_max_ammo_buff():
    # The field is a FRACTION of the magazine, so a bigger magazine gets a
    # bigger clip and the number of loads does not move. Overload's Max
    # Ammunition therefore cannot change this constant.
    assert clip_reload_splits(_shot(8, 3300)) == 3
    assert clip_reload_splits(_shot(12, 3300)) == 3
