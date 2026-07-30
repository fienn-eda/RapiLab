import logging

import pytest

from app.attack_rate import AmmoRefund
from app.cube_effects import (
    ASSUMED_CUBE_LEVEL,
    assumed_cube_effects,
    cube_ammo_refund,
    cube_refund_for,
    cube_skill_percents,
    load_cube,
)


@pytest.fixture(scope="module")
def resilience():
    return load_cube("resilience")


@pytest.fixture(scope="module")
def tactical_bear():
    return load_cube("tactical_bear")


def test_assumed_level_matches_the_in_game_tooltip(resilience):
    # Resilience Cube (렐릭 베어 큐브) Lv.15, confirmed against the in-game
    # tooltip by Fienn on 2026-07-20.
    assert cube_skill_percents(resilience, ASSUMED_CUBE_LEVEL) == {
        "reload_speed_percent": 29.69,
        "other_elemental_bonus": 19.09,
    }


def test_a_mid_level_cube_reads_lower_rungs_of_each_ladder(resilience):
    # At cube level 5 the slots sit at skill level 2 and 1 respectively.
    assert cube_skill_percents(resilience, 5) == {
        "reload_speed_percent": 22.27,
        "other_elemental_bonus": 8.48,
    }


def test_a_slot_that_has_not_unlocked_yet_is_omitted(resilience):
    # level2 is still 0 at cube level 4, so only the reload slot contributes.
    assert set(cube_skill_percents(resilience, 4)) == {"reload_speed_percent"}


def test_an_unmapped_cube_skill_is_skipped_with_a_warning(resilience, caplog):
    cube = dict(resilience)
    groups = [dict(g) if g else g for g in cube["harmonycube_skill_group"]]
    groups[1]["name_localkey"] = "미지의 HC"
    cube["harmonycube_skill_group"] = groups

    with caplog.at_level(logging.WARNING, logger="app.cube_effects"):
        percents = cube_skill_percents(cube, ASSUMED_CUBE_LEVEL)

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


def test_the_two_cubes_differ_only_in_their_first_slot(tactical_bear, resilience):
    # Both give superior code damage 19.09% at Lv.15, and their flat stats are
    # identical - the Tactical Bear spends slot 1 on ammo instead of reload.
    assert cube_skill_percents(tactical_bear, ASSUMED_CUBE_LEVEL) == {
        "other_elemental_bonus": 19.09,
    }
    assert resilience["atk"] == tactical_bear["atk"]
    assert resilience["hp"] == tactical_bear["hp"]


def test_the_tactical_bear_refunds_three_rounds_every_ten_shots(tactical_bear):
    assert cube_ammo_refund(tactical_bear, ASSUMED_CUBE_LEVEL) == AmmoRefund(10, 3)


def test_the_resilience_cube_refunds_nothing(resilience):
    assert cube_ammo_refund(resilience, ASSUMED_CUBE_LEVEL) is None


def test_a_refund_slot_that_has_not_unlocked_yet_gives_nothing(tactical_bear):
    # The Tactical Bear's ammo slot sits at skill level 1 from cube level 1, so
    # there is no locked rung to read - level 1 is the lowest rung, 1 round.
    assert cube_ammo_refund(tactical_bear, 1) == AmmoRefund(10, 1)


def test_the_refund_lookup_is_keyed_by_cube_name():
    assert cube_refund_for("tactical_bear") == AmmoRefund(10, 3)
    assert cube_refund_for("resilience") is None


def test_an_unknown_cube_name_is_rejected():
    with pytest.raises(KeyError, match="unknown harmony cube"):
        load_cube("gravedigger")


def test_a_tactical_bear_wearer_gets_no_reload_speed():
    stats = {e.stat for e in assumed_cube_effects("scarlet-black-shadow",
                                                  "tactical_bear")}
    assert stats == {"other_elemental_bonus"}
