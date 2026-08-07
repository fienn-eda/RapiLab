"""Phantom (base build) - Distributed Damage attacker whose Thief's Dagger chain
is structurally unreachable without her Favorite Item."""
from app.effects import EffectRegistry
from app.skill_rules.phantom import (
    build_phantom_per_shot_rules,
    build_phantom_rules,
    secret_trick_burst_percent,
)
from app.squad_engine import SquadContext, SquadMember, fire_trigger

# ShiftyPad native slots (data/shiftypad/phantom.json, level 10).
CALLING_CARD = {
    "description_value_01": "32.19", "description_value_02": "5",
    "description_value_03": "25.75", "description_value_04": "3",
    "description_value_05": "5", "description_value_06": "75.17",
    "description_value_07": "1",
}
THIEFS_VISION = {
    "description_value_01": "12.86", "description_value_02": "3",
    "description_value_03": "10", "description_value_04": "85.12",
    "description_value_05": "5", "description_value_06": "31.92",
    "description_value_07": "10", "description_value_08": "84.33",
}
SECRET_TRICK = {"description_value_01": "1457.28"}
PHANTOM = {
    "calling_card": CALLING_CARD,
    "thiefs_vision": THIEFS_VISION,
    "secret_trick": SECRET_TRICK,
}

SELF = {"slug": "phantom", "element": "Water"}
ALLY = {"slug": "ally", "element": "Fire"}


def _ctx():
    return SquadContext([
        SquadMember("phantom", burst_tier=3, element="Water", weapon="AR"),
        SquadMember("ally", burst_tier=1, element="Fire", weapon="MG"),
    ])


def test_burst_percent_is_the_distributed_nuke():
    assert secret_trick_burst_percent(PHANTOM) == 1457.28


def test_calling_card_is_a_permanent_squad_wide_enemy_def_debuff():
    reg = EffectRegistry()
    fire_trigger("battle_start", {"phantom": build_phantom_rules(PHANTOM)}, _ctx(), reg, 0.0)
    # negative enemy_def_percent = the enemy's DEF is reduced; squad scope because
    # the debuff sits on the enemy and every attacker benefits.
    assert round(reg.total_for("enemy_def_percent", SELF, 0.0), 4) == -0.3219
    assert round(reg.total_for("enemy_def_percent", ALLY, 179.0), 4) == -0.3219


def test_two_shot_counters_attack_damage_every_shot_and_the_10_shot_pair():
    rules = build_phantom_per_shot_rules(PHANTOM)
    assert sorted(every for every, _mode, _rules in rules) == [1, 10]
    by_count = {every: shot_rules for every, _mode, shot_rules in rules}

    reg = EffectRegistry()
    ctx = _ctx()
    fire_trigger("per_shot", {"phantom": by_count[1]}, ctx, reg, 3.0)
    # "for 1 round(s)" is a bullet-count grant, not a timed effect - the shot loop
    # turns it into an Effect covering exactly the next shot.
    grants = reg.round_grants()
    assert len(grants) == 1
    assert (grants[0].stat, grants[0].scope, grants[0].shots) == ("attack_damage_up", "self", 1)
    assert round(grants[0].value, 4) == 0.7517
    assert reg.total_for("attack_damage_up", SELF, 3.0) == 0.0  # not a timed effect

    reg = EffectRegistry()
    fire_trigger("per_shot", {"phantom": by_count[10]}, ctx, reg, 3.0)
    assert round(reg.total_for("atk_percent", SELF, 3.0), 4) == 0.8512
    assert round(reg.total_for("distributed_damage_up", SELF, 3.0), 4) == 0.3192
    assert reg.total_for("atk_percent", SELF, 8.1) == 0.0  # 5s
    assert round(reg.total_for("distributed_damage_up", SELF, 12.9), 4) == 0.3192  # 10s
    assert reg.total_for("distributed_damage_up", SELF, 13.1) == 0.0


def test_the_10_shot_pair_refreshes_instead_of_stacking():
    """The bullet carries no "Stacks up to N times" clause, so a re-application
    replaces the live grant. At 12 AR shots/sec the counter fires every 0.83 sec,
    far inside both durations, so stacking would multiply it six- to twelvefold."""
    by_count = {every: shot_rules for every, _mode, shot_rules in
                build_phantom_per_shot_rules(PHANTOM)}
    reg = EffectRegistry()
    ctx = _ctx()
    for shot in range(10, 121, 10):
        fire_trigger("per_shot", {"phantom": by_count[10]}, ctx, reg, shot / 12.0)
    assert round(reg.total_for("atk_percent", SELF, 10.0), 4) == 0.8512
    assert round(reg.total_for("distributed_damage_up", SELF, 10.0), 4) == 0.3192


def test_dagger_gated_bullets_are_absent():
    """The dagger can never reach max stacks in this build (Fienn, 2026-07-24),
    so neither Thief's Vision's 84.33% nor its stacking Distributed Damage may
    appear."""
    reg = EffectRegistry()
    ctx = _ctx()
    rules = {"phantom": build_phantom_rules(PHANTOM)}
    for trigger in ("battle_start", "own_burst_activate", "full_burst_enter"):
        fire_trigger(trigger, rules, ctx, reg, 0.0)
    assert reg.total_for("distributed_damage_up", SELF, 0.0) == 0.0


def test_the_daggers_one_held_stack_is_a_permanent_self_hit_rate():
    """One stack, not the text's three: the same deadlock that pins the dagger
    is what fixes the value, and the stack is re-earned within a tenth of a
    second of lapsing, so it is up for the whole fight. Self-scoped."""
    reg = EffectRegistry()
    ctx = _ctx()
    fire_trigger("battle_start", {"phantom": build_phantom_rules(PHANTOM)}, ctx, reg, 0.0)
    assert round(reg.total_for("hit_rate", SELF, 0.0), 4) == 0.2575
    assert round(reg.total_for("hit_rate", SELF, 175.0), 4) == 0.2575  # permanent
    assert reg.total_for("hit_rate", ALLY, 0.0) == 0.0
