from app.skill_rules.registry import get_skill_value_manifest
from app.skill_values import assemble_skill_values, dotgg_slots, extract_lootandwaifus_slots

# Real Lv10 text shape from data/lootandwaifus (Ark Ranger Black, Tremble!).
TREMBLE_TEXT = (
    "■ Activates when Transformation takes effect and when the enemy appears "
    "while Transformation is in effect. Affects all enemies.\n"
    "Ark Black Collider: Deals 45.87% of final ATK as sustained damage every 1 sec "
    "until Transformation is canceled.\n"
    "■ Activates when entering Full Burst. Affects all Wind Code allies with assault rifles.\n"
    "Sustained Damage ▲ 77.5% for 10 sec."
)


def test_extracts_numeric_tokens_left_to_right():
    assert extract_lootandwaifus_slots(TREMBLE_TEXT) == {
        "description_value_01": "45.87",
        "description_value_02": "1",
        "description_value_03": "77.5",
        "description_value_04": "10",
    }


def test_drop_tokens_renumbers_remaining_slots():
    # Dropping token #1 ("1" from "every 1 sec") shifts later tokens up.
    assert extract_lootandwaifus_slots(TREMBLE_TEXT, drop_tokens=[1]) == {
        "description_value_01": "45.87",
        "description_value_02": "77.5",
        "description_value_03": "10",
    }


def test_dotgg_slots_pass_through_and_drop_empties():
    level = {"description_value_01": "1254", "description_value_02": "72.18", "description_value_03": ""}
    assert dotgg_slots(level) == {"description_value_01": "1254", "description_value_02": "72.18"}


def test_registry_exposes_pilot_manifests():
    manifest = get_skill_value_manifest("drake")
    assert manifest["source"] == "dotgg"
    assert manifest["keys"]["drake_special"] == ("skills", 2)
    assert get_skill_value_manifest("not-a-slug") is None


def test_assemble_drake_max_level_from_real_data_file():
    manifest = get_skill_value_manifest("drake")
    values = assemble_skill_values(
        "drake", manifest, {"skill1": 10, "skill2": 10, "burst": 10}
    )
    # Ground truth: DRAKE_SPECIAL fixture in test_skill_rules_drake.py.
    assert float(values["drake_special"]["description_value_01"]) == 1254.0


def test_assemble_respects_user_skill_level():
    manifest = get_skill_value_manifest("drake")
    lv10 = assemble_skill_values("drake", manifest, {"skill1": 10, "skill2": 10, "burst": 10})
    lv1 = assemble_skill_values("drake", manifest, {"skill1": 10, "skill2": 10, "burst": 1})
    assert float(lv1["drake_special"]["description_value_01"]) < float(
        lv10["drake_special"]["description_value_01"]
    )
