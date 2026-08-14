"""Jill Valentine's Supercop empties her magazine and forces a reload.

The window's length is derived from her own weapon's reload time through the
skill's own "reload speed is fixed at" value, the same way Milk's is - not a
transcribed constant.
"""
import pytest

from app.attack_rate import reload_time_with_speed
from app.skill_rules.jill_valentine import build_jill_weapon_mode_schedule

SLUG = "jill-valentine"

# Read from assemble_skill_values at skill level 10: _01 is the fixed reload
# speed (99.96%), _03 is the ammo removed (100%).
SUPERCOP = {
    "description_value_01": "99.96",
    "description_value_02": "10",
    "description_value_03": "100",
    "description_value_04": "80.78",
    "description_value_05": "10",
    "description_value_06": "75",
    "description_value_07": "10",
    "description_value_08": "10",
}
# Her real weapon as a builder receives it (no clip split applies to her).
VALUES = {
    "supercop": SUPERCOP,
    "caster_weapon_stats": {"weapon": "AR", "reload_time": 1.0, "max_ammo": 9},
}


class _Context:
    def __init__(self, burst_times):
        self.burst_times = {SLUG: burst_times}


def test_segment_starts_at_her_burst_and_lasts_the_fixed_reload():
    schedule = build_jill_weapon_mode_schedule(VALUES)

    (segment,) = schedule(_Context([20.0]), 180.0)

    assert segment["start"] == pytest.approx(20.0)
    assert segment["end"] == pytest.approx(20.0 + reload_time_with_speed(1.0, 0.9996))


def test_no_shot_fits_in_the_window_and_it_would_be_harmless_if_one_did():
    schedule = build_jill_weapon_mode_schedule(VALUES)

    (segment,) = schedule(_Context([20.0]), 180.0)

    window = segment["end"] - segment["start"]
    assert 1.0 / segment["profile"]["rate_of_fire"] > window
    assert segment["profile"]["damage_percent"] == 0.0
    assert segment["profile"]["weapon"] == "AR"


def test_segment_is_clipped_by_the_fight_end():
    schedule = build_jill_weapon_mode_schedule(VALUES)

    segments = schedule(_Context([179.9]), 180.0)

    assert segments[-1]["end"] == pytest.approx(180.0)


def test_no_segment_for_a_burst_at_or_past_the_bell():
    schedule = build_jill_weapon_mode_schedule(VALUES)

    assert schedule(_Context([180.0]), 180.0) == []
