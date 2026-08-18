"""Holding fire through your own Full Burst, so an ally's "for N round(s)" buff
survives it.

A round buff is spent BY a bullet. Not firing keeps it, so every skill hit in
the window lands under it - Mihara's chain DoT, Ein's Near Feathers. Real
in-game tactic (Fienn, 2026-08-18).

It is a PLAY DECISION, never a unit property: with no round buff to preserve,
holding fire only removes shots. That is why nothing switches it on by itself
and why the deck gate exists.
"""
import pytest

from app.deck_search import (BossProfile, deck_is_valid, evaluate_deck,
                             evaluate_deck_hold_fire_options, feasible_orderings)
from app.models import UserNikkeState
from app.roster import assemble_simulation_inputs
from app.skill_rules._helpers import (HOLD_FIRE_RELEASE_MARGIN, hold_fire_segments,
                                      round_buff_rule)
from app.skill_rules.registry import (deck_grants_ally_round_buffs,
                                      get_hold_fire_release_shots)
from app.user_roster import load_roster

BOSS = BossProfile(element="Iron", fight_duration=180.0)
RL = {"weapon": "RL", "damage_percent": 100.0, "charge_damage_percent": 250.0}
MIHARA = "mihara-bonding-chain"
WITH_GRANTER = ["miranda-signature", "liter", "crown", MIHARA, "helm-signature"]
WITHOUT_GRANTER = ["liter", "volume", "crown", MIHARA, "helm-signature"]


class _Context:
    def __init__(self, bursts, windows):
        self.burst_times = {"unit": bursts}
        self.full_burst_windows = windows


def test_holding_throughout_fires_nothing_in_the_window():
    schedule = hold_fire_segments(RL, "unit", release_shots=0)
    (segment,) = schedule(_Context([2.5], [(2.6, 12.6)]), 180.0)
    assert (segment["start"], segment["end"]) == (2.6, 12.6)
    assert segment["profile"]["damage_percent"] == 0.0
    # One interval is twice the window, so the first shot would land past its end.
    assert 1.0 / segment["profile"]["rate_of_fire"] > segment["end"] - segment["start"]
    assert "until_shots" not in segment


def test_the_released_shot_lands_just_INSIDE_full_burst():
    # The window is half-open, so a shot exactly on the bell is outside it and
    # loses the Full Burst bonus the tactic exists to collect.
    schedule = hold_fire_segments(RL, "unit", release_shots=1)
    (segment,) = schedule(_Context([2.5], [(2.6, 12.6)]), 180.0)
    assert segment["until_shots"] == 1
    shot = segment["start"] + 1.0 / segment["profile"]["rate_of_fire"]
    assert shot == pytest.approx(12.6 - HOLD_FIRE_RELEASE_MARGIN)
    assert 2.6 <= shot < 12.6
    assert segment["profile"]["damage_percent"] == RL["damage_percent"]
    assert segment["profile"]["charge_damage_percent"] == RL["charge_damage_percent"]


def test_only_full_bursts_the_unit_opened_herself_are_held():
    # Two windows, one burst: the ally-opened window is not hers to hold.
    schedule = hold_fire_segments(RL, "unit", release_shots=0)
    segments = schedule(_Context([20.0], [(2.6, 12.6), (20.1, 30.1)]), 180.0)
    assert [s["start"] for s in segments] == [20.1]


def test_the_window_is_the_real_one_so_an_extension_counts():
    schedule = hold_fire_segments(RL, "unit", release_shots=0)
    (segment,) = schedule(_Context([2.5], [(2.6, 17.6)]), 180.0)   # +5 sec extension
    assert segment["end"] == 17.6


def test_the_table_says_who_plays_it_and_who_releases():
    assert get_hold_fire_release_shots(MIHARA) == 0
    assert get_hold_fire_release_shots("ein") == 1
    # Ada Wong plays it in game, but her Special Modification's charge slowdown
    # is not on the engine's timeline, so her released shot would be wrong in
    # both its timing and its Charge Damage - see the table's own comment.
    assert get_hold_fire_release_shots("ada-wong") is None
    assert get_hold_fire_release_shots("snow-white") is None


def test_the_gate_reads_the_rules_not_a_list_of_granter_slugs():
    ally = round_buff_rule("full_burst_enter", [("crit_rate", 0.5, ("top_atk", 1))])
    mine = round_buff_rule("per_shot", [("crit_rate", 0.5, "self")])
    assert deck_grants_ally_round_buffs({"a": [ally]})
    assert not deck_grants_ally_round_buffs({"a": [mine]})
    assert not deck_grants_ally_round_buffs({"a": []})


def _nikke(slug, carry):
    return UserNikkeState.model_validate({
        "character_slug": slug, "level": 200, "core_level": 0, "hp": 1_000_000.0,
        "atk": 95_000.0 if slug == carry else 55_000.0, "def_": 3_000.0,
        "skill_levels": {"skill1": 10, "skill2": 10, "burst": 10}})


def _ordering(deck, carry):
    specs, excluded = load_roster([_nikke(s, carry) for s in deck])
    assert not excluded, excluded
    return next(o for o in feasible_orderings(specs)
                if {u.slug for u in o} == set(deck) and deck_is_valid(o))


def test_a_deck_with_nobody_to_preserve_a_buff_for_is_never_offered_the_hold():
    assert evaluate_deck_hold_fire_options(
        _ordering(WITHOUT_GRANTER, MIHARA)) == [frozenset()]


def test_a_deck_with_a_granter_and_a_holder_is_offered_both():
    options = evaluate_deck_hold_fire_options(_ordering(WITH_GRANTER, MIHARA))
    assert options == [frozenset(), frozenset({MIHARA})]


def test_a_deck_with_a_granter_but_no_holder_is_not_offered_the_hold():
    deck = ["miranda-signature", "liter", "crown", "snow-white", "helm-signature"]
    assert evaluate_deck_hold_fire_options(_ordering(deck, "snow-white")) == [frozenset()]


def test_holding_pays_when_there_is_a_buff_to_preserve_and_costs_when_there_is_not():
    ordering = _ordering(WITH_GRANTER, MIHARA)
    plain = evaluate_deck(ordering, BOSS)
    held = evaluate_deck(ordering, BOSS, hold_fire={MIHARA})
    assert held["total_damage"] > plain["total_damage"]

    bare = _ordering(WITHOUT_GRANTER, MIHARA)
    assert (evaluate_deck(bare, BOSS, hold_fire={MIHARA})["total_damage"]
            < evaluate_deck(bare, BOSS)["total_damage"])


def test_holding_a_unit_that_also_transforms_her_weapon_is_refused_not_guessed():
    deck = ["miranda-signature", "liter", "crown", "snow-white", "helm-signature"]
    with pytest.raises(ValueError, match="weapon-mode schedule"):
        assemble_simulation_inputs(_ordering(deck, "snow-white"),
                                   hold_fire={"snow-white"})
