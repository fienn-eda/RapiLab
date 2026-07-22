"""Tests for backend/app/shiftypad_normalize.py against committed fixtures."""
import json
from pathlib import Path

from app.shiftypad_normalize import normalize_shiftypad

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
    assert out["burst"] == 3


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
