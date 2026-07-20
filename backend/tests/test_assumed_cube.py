import logging

import pytest

from app.cube_effects import (
    ASSUMED_CUBE_LEVEL,
    assumed_cube_effects,
    cube_skill_percents,
)
from app.stat_assembly import load_stat_tables


@pytest.fixture(scope="module")
def tables():
    return load_stat_tables()


def test_assumed_level_matches_the_in_game_tooltip(tables):
    # Resilience Cube (렐릭 베어 큐브) Lv.15, confirmed against the in-game
    # tooltip by Fienn on 2026-07-20.
    assert cube_skill_percents(tables, ASSUMED_CUBE_LEVEL) == {
        "reload_speed_percent": 29.69,
        "other_elemental_bonus": 19.09,
    }


def test_a_mid_level_cube_reads_lower_rungs_of_each_ladder(tables):
    # At cube level 5 the slots sit at skill level 2 and 1 respectively.
    assert cube_skill_percents(tables, 5) == {
        "reload_speed_percent": 22.27,
        "other_elemental_bonus": 8.48,
    }


def test_a_slot_that_has_not_unlocked_yet_is_omitted(tables):
    # level2 is still 0 at cube level 4, so only the reload slot contributes.
    assert set(cube_skill_percents(tables, 4)) == {"reload_speed_percent"}


def test_an_unmapped_cube_skill_is_skipped_with_a_warning(tables, caplog):
    doctored = dict(tables)
    cube = dict(tables["resilience_cube"])
    groups = [dict(g) if g else g for g in cube["harmonycube_skill_group"]]
    groups[1]["name_localkey"] = "미지의 HC"
    cube["harmonycube_skill_group"] = groups
    doctored["resilience_cube"] = cube

    with caplog.at_level(logging.WARNING, logger="app.cube_effects"):
        percents = cube_skill_percents(doctored, ASSUMED_CUBE_LEVEL)

    assert set(percents) == {"reload_speed_percent"}
    assert "미지의 HC" in caplog.text


def test_assumed_cube_effects_are_permanent_self_buffs():
    effects = assumed_cube_effects("anis-star")
    by_stat = {e.stat: e for e in effects}
    assert round(by_stat["reload_speed_percent"].value, 4) == 0.2969
    assert round(by_stat["other_elemental_bonus"].value, 4) == 0.1909
    for effect in effects:
        assert effect.scope == "self"
        assert effect.duration is None
        assert effect.source_slug == "anis-star"
