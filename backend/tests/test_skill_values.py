from app.skill_values import dotgg_slots, extract_lootandwaifus_slots

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
