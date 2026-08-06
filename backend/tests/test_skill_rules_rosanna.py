"""Rosanna (base build) - a Burst-1 Electric MG Attacker whose burst is the payload."""
from app.effects import EffectRegistry
from app.skill_rules.rosanna import (
    build_rosanna_base_per_shot_rules,
    build_rosanna_base_rules,
    vendetta_burst_percent,
)
from app.squad_engine import SquadContext, SquadMember, fire_trigger

# ShiftyPad native slots (data/shiftypad/rosanna.json, level 10).
ON_THE_LAM = {
    "description_value_01": "120", "description_value_02": "10",
    "description_value_03": "19.34", "description_value_04": "3",
    "description_value_05": "10", "description_value_06": "2",
    "description_value_07": "5", "description_value_08": "1",
}
CAPO_DEI_CAPI = {
    "description_value_01": "5", "description_value_02": "22.61",
    "description_value_03": "10", "description_value_04": "30",
    "description_value_05": "36.54",
}
VENDETTA = {
    "description_value_01": "2", "description_value_02": "1310.4",
    "description_value_03": "561.6",
}
ROSANNA = {"on_the_lam": ON_THE_LAM, "capo_dei_capi": CAPO_DEI_CAPI, "vendetta": VENDETTA}

SELF = {"slug": "rosanna", "element": "Electric"}
ALLY = {"slug": "ally", "element": "Fire"}


def test_burst_percent_folds_in_the_concealment_rider():
    # Concealment is re-granted every 120 shots (2.0s of MG fire, ~2.7s wall
    # clock with reloads) against a 10s duration, so it is permanently up -
    # Fienn ruled the rider always active (2026-07-24).
    assert vendetta_burst_percent(ROSANNA) == 1310.4 + 561.6


def test_on_the_lam_grants_self_crit_rate_every_120_shots():
    rules = build_rosanna_base_per_shot_rules(ROSANNA)
    assert len(rules) == 1
    every, mode, shot_rules = rules[0]
    assert (every, mode) == (120, "every")

    reg = EffectRegistry()
    ctx = SquadContext([
        SquadMember("rosanna", burst_tier=1, element="Electric", weapon="MG"),
        SquadMember("ally", burst_tier=3, element="Fire", weapon="AR"),
    ])
    fire_trigger("per_shot", {"rosanna": shot_rules}, ctx, reg, 5.0)
    assert round(reg.total_for("crit_rate", SELF, 5.0), 4) == 0.1934
    assert reg.total_for("crit_rate", ALLY, 5.0) == 0.0
    assert reg.total_for("crit_rate", SELF, 8.1) == 0.0  # 3s duration


def test_the_crit_buff_refreshes_instead_of_stacking():
    """The bullet names no stack count, so a re-application replaces the live
    grant. 120 MG shots take 2.0 sec against a 3 sec duration, so stacking
    would leave her permanently at double the crit rate the skill grants."""
    _every, _mode, shot_rules = build_rosanna_base_per_shot_rules(ROSANNA)[0]
    reg = EffectRegistry()
    ctx = SquadContext([SquadMember("rosanna", burst_tier=1, element="Electric", weapon="MG")])
    for time in (2.0, 4.0, 6.0, 8.0):
        fire_trigger("per_shot", {"rosanna": shot_rules}, ctx, reg, time)
    assert round(reg.total_for("crit_rate", SELF, 8.0), 4) == 0.1934


def test_frenzy_and_the_buff_strip_are_not_emitted():
    """Frenzy keys off "a Nikke is incapacitated" (the sim never downs an ally)
    and the enemy buff-strip has no engine concept."""
    reg = EffectRegistry()
    ctx = SquadContext([SquadMember("rosanna", burst_tier=1, element="Electric", weapon="MG")])
    rules = {"rosanna": build_rosanna_base_rules(ROSANNA)}
    for trigger in ("battle_start", "own_burst_activate", "full_burst_enter"):
        fire_trigger(trigger, rules, ctx, reg, 0.0)
    assert reg.total_for("atk_percent", SELF, 0.0) == 0.0
    assert reg.total_for("flat_atk", SELF, 0.0) == 0.0
