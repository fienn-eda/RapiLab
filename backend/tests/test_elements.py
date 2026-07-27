import sys
from pathlib import Path

import pytest

from app.elements import ELEMENT_ADVANTAGE_BONUS, element_multiplier

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))


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


def test_record_boss_is_the_iron_annihilio_the_record_describes():
    """The calibration harness's boss must stay the boss Fienn actually fought.

    The record says "애니힐리오: 철갑=Wind 약점" (docs/decisions.md) - Annihilio is
    IRON code and Wind attackers counter it. `element` names the boss's OWN
    code, and reading that field as "the code that counters it" is the mistake
    that made this constant "Water" until 2026-07-27: that spelling made the
    boss ELECTRIC-weak, inflating Cinderella (Electric) to 1.88x of her
    recorded damage and deflating Volume (Wind) to 0.78x of hers. Every
    calibration ratio measured through the harness rides on this one field, and
    nothing else pinned it.
    """
    from raid_record import RECORD_BOSS

    assert RECORD_BOSS["element"] == "Iron"
    assert element_multiplier("Wind", RECORD_BOSS["element"]) == 1.1
    assert element_multiplier("Electric", RECORD_BOSS["element"]) == 1.0


def test_the_harness_reads_the_record_rather_than_its_own_copy():
    """One boss definition, not two that can drift apart.

    `measure_deck_breakdown` used to declare its own RECORD_BOSS; a second copy
    is how a constant gets corrected in one place and left wrong in the other.
    """
    import measure_deck_breakdown
    import raid_record

    assert measure_deck_breakdown.RECORD_BOSS is raid_record.RECORD_BOSS


def test_every_recorded_deck_is_a_five_unit_deck_with_positive_damage():
    """Guards the record fixture itself against a typo'd edit.

    The record is ground truth for every calibration claim this project makes,
    and it is hand-transcribed from a damage log, so it gets the same shape
    check any other input would.
    """
    from raid_record import RECORD_DECKS, deck_total

    assert len(RECORD_DECKS) == 5
    for name, deck in RECORD_DECKS.items():
        assert len(deck) == 5, f"{name} has {len(deck)} units"
        assert all(damage > 0 for damage in deck.values()), name
        assert deck_total(name) == sum(deck.values())
    seated = [slug for deck in RECORD_DECKS.values() for slug in deck]
    assert len(seated) == len(set(seated)), "a unit is seated in two decks"
