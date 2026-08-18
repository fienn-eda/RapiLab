"""Which bullet spends a "for N round(s)" buff, and whether two of them stack.

Both rulings are Fienn's, in-game 2026-08-18:
1. The buff a bullet creates applies to the NEXT bullet. A bullet fired at the
   very instant of the grant has already left - it is neither covered by the
   buff nor the one that spends it.
2. Without a "stacks up to N time(s)" clause a round buff does not stack at all,
   so two live grants of the same bullet count once.
"""
import pytest

from app.effects import RoundGrant
from app.raid_simulator import (
    ROUND_GRANT_EPSILON,
    _capped_round_grant_segments,
    _round_grant_shot_window,
)
from app.skill_rules._helpers import round_buff_rule
from app.effects import EffectRegistry
from app.squad_engine import SquadContext, SquadMember

FIGHT = 100.0
EPS = ROUND_GRANT_EPSILON


def test_the_buff_ends_on_the_bullet_that_spends_it():
    # Granted at 1.5; the bullet at 2.0 spends it and is the last thing covered.
    # The idle stretch after that bullet is NOT - it used to run to 3.0.
    start, end = _round_grant_shot_window([1.0, 2.0, 3.0], 1.5, 1, [], FIGHT)
    assert (start, end) == (1.5, 2.0 + EPS)
    assert start <= 2.0 < end
    assert not start <= 2.5 < end


def test_a_bullet_fired_at_the_instant_of_the_grant_is_neither_covered_nor_spends_it():
    # The per-shot self-grant shape: the bullet at 1.0 triggered this grant, so
    # the buff belongs to the bullet at 2.0 and to nothing before it.
    start, end = _round_grant_shot_window([1.0, 2.0, 3.0], 1.0, 1, [], FIGHT,
                                          from_own_shot=True)
    assert (start, end) == (1.0 + EPS, 2.0 + EPS)
    assert not start <= 1.0 < end   # the bullet that granted it
    assert start <= 2.0 < end       # the next one


def test_consecutive_per_shot_self_grants_tile_without_overlapping():
    # Each bullet's grant covers exactly the following bullet, so a unit that
    # grants on every shot holds one at a time and never two.
    shots = [1.0, 2.0, 3.0, 4.0]
    windows = [_round_grant_shot_window(shots, t, 1, [], FIGHT, from_own_shot=True)
               for t in shots[:3]]
    for (start, end), covered in zip(windows, shots[1:]):
        assert sum(1 for t in shots if start <= t < end) == 1
        assert start <= covered < end
    assert windows[0][1] <= windows[1][0]   # no overlap


def test_the_gap_before_the_spending_bullet_still_belongs_to_the_buff():
    # Phantom's shape: her burst fires between two of her shots and must be
    # under the buff the previous shot granted.
    start, end = _round_grant_shot_window([2.0, 9.0], 2.0, 1, [], FIGHT,
                                          from_own_shot=True)
    assert (start, end) == (2.0 + EPS, 9.0 + EPS)
    assert start <= 5.0 < end


def test_a_grant_nobody_fires_after_lasts_to_fight_end():
    assert _round_grant_shot_window([1.0], 2.0, 1, [], FIGHT) == (2.0, FIGHT)


def test_an_unlimited_window_still_ends_it():
    assert _round_grant_shot_window([5.0], 2.5, 1, [(2.0, 12.0)], FIGHT) == (2.5, 12.0)


def _grant(value, granted_at, cap, group="g"):
    return RoundGrant("pierce_damage_up", value, "squad", "granter", 1, granted_at,
                      cap=cap, cap_group=group)


def test_a_bullet_with_no_stack_clause_counts_once_however_many_are_live():
    # Two grants of the same bullet overlapping on one recipient: without a
    # "stacks up to" clause the recipient holds one, not two.
    entries = [(0, _grant(0.25, 1.0, 1), 1.0, 6.0),
               (1, _grant(0.25, 2.0, 1), 2.0, 7.0)]
    assert _capped_round_grant_segments(entries, 1) == [(1.0, 7.0, 0.25)]


def test_round_buff_rule_defaults_to_not_stacking():
    # The default has to be no-stacking, because "stacks up to N" is the only
    # marker the skill text gives - a bullet without it does not stack.
    members = [SquadMember(slug="a", burst_tier=1, element="Iron")]
    context = SquadContext(members)
    registry = EffectRegistry()
    rule = round_buff_rule("battle_start", [("crit_rate", 0.5, "squad")])
    rule.action(context, "a", 0.0, registry)
    (grant,) = registry.round_grants()
    assert grant.cap == 1
    assert grant.cap_group is not None


def test_a_stack_clause_is_carried_through_as_the_cap():
    members = [SquadMember(slug="a", burst_tier=1, element="Iron")]
    context = SquadContext(members)
    registry = EffectRegistry()
    rule = round_buff_rule("battle_start", [("crit_rate", 0.5, "squad")], cap=3)
    rule.action(context, "a", 0.0, registry)
    (grant,) = registry.round_grants()
    assert grant.cap == 3


def test_two_different_rules_still_add_up():
    # The cap is per BULLET, not per stat: two skills granting the same stat are
    # two separate stacks and both pay.
    entries_a = [(0, _grant(0.25, 1.0, 1, "rule-a"), 1.0, 6.0)]
    entries_b = [(1, _grant(0.40, 1.0, 1, "rule-b"), 1.0, 6.0)]
    assert _capped_round_grant_segments(entries_a, 1) == [(1.0, 6.0, 0.25)]
    assert _capped_round_grant_segments(entries_b, 1) == [(1.0, 6.0, 0.40)]


def test_a_shot_that_only_MARKS_the_grant_is_covered_by_it():
    # Jill Valentine's Magnum Ammo: the reload created it and the magazine's
    # first bullet only says when. Without `from_own_shot` that bullet is one
    # of the nine, which is what "her next 9 rounds" means.
    start, end = _round_grant_shot_window([1.0, 2.0, 3.0, 4.0], 1.0, 2, [], FIGHT)
    assert (start, end) == (1.0, 2.0 + EPS)
    assert [t for t in [1.0, 2.0, 3.0, 4.0] if start <= t < end] == [1.0, 2.0]
