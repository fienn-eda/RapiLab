import pytest

from app.accuracy import (SPREAD_CONVERGENCE, WEAPON_SPREAD_DIAMETER,
                          ZERO_SPREAD_HIT_RATE, core_hit_rate, spread_diameter)


def test_base_diameters_are_the_values_in_the_game_data():
    # shot_detail.start_accuracy_circle_scale, uniform within each weapon class
    # across the 77 collected units. MG carries its converged `end` value.
    assert WEAPON_SPREAD_DIAMETER == {
        "AR": 75.0, "SG": 250.0, "SMG": 110.0, "MG": 10.0, "SR": 10.0, "RL": 10.0,
    }


def test_only_the_mg_converges_within_a_magazine():
    # start/end/accuracy_change_pershot across the collected raws: MG is the one
    # class whose start and end differ, and every other class carries a
    # per-shot change of 0.
    assert SPREAD_CONVERGENCE == {"MG": (250.0, 7.0)}


def test_the_mg_opens_a_magazine_wide_and_tightens_per_round():
    assert spread_diameter("MG", 0.0, magazine_index=0) == 250.0
    assert spread_diameter("MG", 0.0, magazine_index=1) == 243.0
    assert spread_diameter("MG", 0.0, magazine_index=20) == 110.0


def test_the_mg_floors_at_its_converged_diameter():
    # (250 - 10) / 7 = 34.3 rounds, and it never tightens past `end`.
    assert spread_diameter("MG", 0.0, magazine_index=34) == 12.0
    assert spread_diameter("MG", 0.0, magazine_index=35) == 10.0
    assert spread_diameter("MG", 0.0, magazine_index=9999) == 10.0


def test_a_non_converging_weapon_ignores_the_magazine_index():
    for weapon in ("AR", "SG", "SMG", "SR", "RL"):
        assert (spread_diameter(weapon, 0.0, magazine_index=0)
                == WEAPON_SPREAD_DIAMETER[weapon])


def test_no_magazine_index_keeps_the_converged_diameter():
    """The default is what every caller that does not track magazine position
    gets - a transform segment, and the frontend mirror - so wiring the
    convergence cannot silently widen a spread nobody asked about."""
    assert spread_diameter("MG", 0.0) == 10.0
    assert core_hit_rate("MG", 0.0, 48.89) == 1.0


def test_hit_rate_narrows_the_opening_spread_too():
    # The hit-rate factor multiplies whatever diameter the weapon draws at that
    # point in the magazine, not just the converged one. UNMEASURED: no reading
    # separates this from "hit rate only moves the converged end".
    assert spread_diameter("MG", 0.55, magazine_index=0) == pytest.approx(125.0)


def test_the_first_rounds_of_an_mg_magazine_miss_the_core():
    # The recorded Annihilio core is 48.89px, so an MG opens a magazine hitting
    # it 3.8% of the time and is inside it by round 29.
    assert core_hit_rate("MG", 0.0, 48.89, magazine_index=0) == pytest.approx(
        (48.89 / 250) ** 2)
    assert core_hit_rate("MG", 0.0, 48.89, magazine_index=28) == pytest.approx(
        (48.89 / 54) ** 2)
    assert core_hit_rate("MG", 0.0, 48.89, magazine_index=29) == 1.0


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
