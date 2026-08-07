import pytest

from app.accuracy import (WEAPON_SPREAD_DIAMETER, ZERO_SPREAD_HIT_RATE,
                          core_hit_rate, spread_diameter)


def test_base_diameters_are_the_values_in_the_game_data():
    # shot_detail.start_accuracy_circle_scale, uniform within each weapon class
    # across the 77 collected units. MG carries its converged `end` value.
    assert WEAPON_SPREAD_DIAMETER == {
        "AR": 75.0, "SG": 250.0, "SMG": 110.0, "MG": 10.0, "SR": 10.0, "RL": 10.0,
    }


def test_hit_rate_narrows_the_spread_linearly():
    assert spread_diameter("SG", 0.0) == 250.0
    assert spread_diameter("SG", 0.55) == pytest.approx(125.0)
    assert spread_diameter("AR", 0.55) == pytest.approx(37.5)


def test_every_weapon_reaches_zero_spread_at_the_same_hit_rate():
    # The article's three per-weapon regressions all cross zero here, which is
    # what makes them one equation rather than three.
    for weapon in WEAPON_SPREAD_DIAMETER:
        assert spread_diameter(weapon, ZERO_SPREAD_HIT_RATE) == 0.0


def test_hit_rate_past_the_singularity_does_not_go_negative():
    # Dorothy: Serendipity stacks two buffs past 110%.
    assert spread_diameter("SG", 1.20) == 0.0


def test_negative_hit_rate_widens_the_spread():
    # Mast: Romantic Maid's Drunken stacks to -107.76%.
    assert spread_diameter("MG", -1.10) == pytest.approx(20.0)


def test_core_hit_rate_is_the_area_ratio():
    assert core_hit_rate("AR", 0.0, 50.0) == pytest.approx((50 / 75) ** 2)
    assert core_hit_rate("SMG", 0.0, 50.0) == pytest.approx((50 / 110) ** 2)
    assert core_hit_rate("SG", 0.0, 50.0) == pytest.approx((50 / 250) ** 2)


def test_a_spread_inside_the_core_always_hits_it():
    assert core_hit_rate("SR", 0.0, 50.0) == 1.0
    assert core_hit_rate("RL", 0.0, 50.0) == 1.0
    assert core_hit_rate("MG", 0.0, 50.0) == 1.0


def test_zero_spread_always_hits():
    assert core_hit_rate("SG", ZERO_SPREAD_HIT_RATE, 50.0) == 1.0


def test_an_unknown_weapon_raises():
    with pytest.raises(KeyError):
        spread_diameter("BOW", 0.0)
