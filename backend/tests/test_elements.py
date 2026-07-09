import pytest

from app.elements import ELEMENT_ADVANTAGE_BONUS, element_multiplier


def test_advantageous_matchups_return_the_bonus_multiplier():
    # Verified cycle (nikke.gg/code, Fandom wiki): Water > Fire > Wind > Iron
    # > Electric > Water. Attacker with advantage deals +10%.
    assert element_multiplier("Water", "Fire") == 1.1
    assert element_multiplier("Fire", "Wind") == 1.1
    assert element_multiplier("Wind", "Iron") == 1.1
    assert element_multiplier("Iron", "Electric") == 1.1
    assert element_multiplier("Electric", "Water") == 1.1


def test_disadvantageous_matchups_return_neutral():
    # the reverse of each advantageous pairing is NOT advantaged
    assert element_multiplier("Fire", "Water") == 1.0
    assert element_multiplier("Wind", "Fire") == 1.0
    assert element_multiplier("Iron", "Wind") == 1.0
    assert element_multiplier("Electric", "Iron") == 1.0
    assert element_multiplier("Water", "Electric") == 1.0


def test_same_element_is_neutral():
    for element in ("Fire", "Water", "Wind", "Iron", "Electric"):
        assert element_multiplier(element, element) == 1.0


def test_non_adjacent_matchups_are_neutral():
    # Fire is only advantaged against Wind; against Iron/Electric it's neutral.
    assert element_multiplier("Fire", "Iron") == 1.0
    assert element_multiplier("Fire", "Electric") == 1.0


def test_bonus_constant_is_ten_percent():
    assert ELEMENT_ADVANTAGE_BONUS == 0.1


def test_unknown_element_raises():
    with pytest.raises(KeyError):
        element_multiplier("Plasma", "Fire")
