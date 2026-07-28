"""Seats whose burst the player never spends, end to end through evaluate_deck.

A raid record can seat a Nikke purely for her passive kit ("totem") or burst her
once and then hold her for the rest of the fight. That is a decision made in the
run, not a property of the unit, so it never comes from the registry - it is
handed to `evaluate_deck` as `max_bursts` and lands on the deck member the
scheduler reads (see burst_cycle's `max_bursts`).
"""
from app.deck_search import BossProfile, evaluate_deck
from tests.test_roster import minimal_feasible_deck

BOSS = BossProfile(enemy_def=31_784, fight_duration=180.0, core_hittable=True)


def _sources(result, slug):
    return {event["source"] for event in result["damage_log"] if event["slug"] == slug}


def test_a_totem_seat_contributes_no_burst_damage():
    deck = minimal_feasible_deck()

    played = evaluate_deck(deck, BOSS)
    totem = evaluate_deck(deck, BOSS, max_bursts={"helm": 0})

    assert "burst" in _sources(played, "helm")
    assert "burst" not in _sources(totem, "helm")


def test_holding_a_seats_burst_costs_the_deck_its_full_bursts():
    # Helm is the only Burst 3 here, so holding her burst means the deck never
    # reaches Full Burst at all - every unit loses the window's bonus, not just
    # the held one.
    deck = minimal_feasible_deck()

    played = evaluate_deck(deck, BOSS)
    totem = evaluate_deck(deck, BOSS, max_bursts={"helm": 0})

    assert totem["total_damage"] < played["total_damage"]


def test_omitting_the_override_leaves_the_result_byte_identical():
    deck = minimal_feasible_deck()

    assert (evaluate_deck(deck, BOSS)["total_damage"]
            == evaluate_deck(deck, BOSS, max_bursts=None)["total_damage"])
