"""Rosanna's Favorite Item build - adds a permanent elemental buff, a shot-counted
Frenzy source her base build can never reach, and a Water-Code damage-taken debuff."""
from app.effects import EffectRegistry
from app.skill_rules.rosanna_signature import (
    build_rosanna_signature_per_shot_rules,
    build_rosanna_signature_rules,
    vendetta_signature_burst_percent,
)
from app.squad_engine import SquadContext, SquadMember, fire_trigger

# lootandwaifus dollskills, level 10, every number in the text numbered left-to-right.
ON_THE_LAM = {
    "description_value_01": "120", "description_value_02": "10",
    "description_value_03": "19.34", "description_value_04": "3",
    "description_value_05": "10", "description_value_06": "2",
    "description_value_07": "5", "description_value_08": "20",
}
CAPO_DEI_CAPI = {
    "description_value_01": "5", "description_value_02": "22.61",
    "description_value_03": "10", "description_value_04": "30",
    "description_value_05": "36.54", "description_value_06": "1",
    "description_value_07": "400", "description_value_08": "500",
    "description_value_09": "22.61", "description_value_10": "10",
    "description_value_11": "30",
}
VENDETTA = {
    "description_value_01": "2", "description_value_02": "1310.4",
    "description_value_03": "561.6", "description_value_04": "29",
    "description_value_05": "30",
}
ROSANNA_SIG = {"on_the_lam": ON_THE_LAM, "capo_dei_capi": CAPO_DEI_CAPI, "vendetta": VENDETTA}

SELF = {"slug": "rosanna-signature", "element": "Electric"}
ALLY = {"slug": "ally", "element": "Fire"}


def _ctx(boss_element=None):
    return SquadContext([
        SquadMember("rosanna-signature", burst_tier=1, element="Electric", weapon="MG"),
        SquadMember("ally", burst_tier=3, element="Fire", weapon="AR"),
    ], boss_element=boss_element)


def _fire(trigger, boss_element=None, time=0.0):
    reg = EffectRegistry()
    fire_trigger(trigger, {"rosanna-signature": build_rosanna_signature_rules(ROSANNA_SIG)},
                 _ctx(boss_element), reg, time)
    return reg


def test_burst_percent_matches_the_base_build():
    assert vendetta_signature_burst_percent(ROSANNA_SIG) == 1310.4 + 561.6


def test_stage_target_elemental_buff_is_permanent_and_self_only():
    # "when the stage target appears" - a raid always has an enemy, so it is on
    # from t=0 (the documented always-on-in-raid convention).
    reg = _fire("battle_start")
    assert round(reg.total_for("other_elemental_bonus", SELF, 0.0), 4) == 0.20
    assert round(reg.total_for("other_elemental_bonus", SELF, 179.0), 4) == 0.20
    assert reg.total_for("other_elemental_bonus", ALLY, 0.0) == 0.0


def test_water_code_damage_taken_debuff_is_squad_scoped_and_gated():
    reg = _fire("own_burst_activate", boss_element="Water", time=20.0)
    assert round(reg.total_for("damage_taken_up", SELF, 20.0), 4) == 0.29
    assert round(reg.total_for("damage_taken_up", ALLY, 20.0), 4) == 0.29  # all attackers share it
    assert reg.total_for("damage_taken_up", SELF, 50.1) == 0.0  # 30s
    assert _fire("own_burst_activate", boss_element="Fire", time=20.0).total_for(
        "damage_taken_up", SELF, 20.0) == 0.0


def test_two_shot_counters_crit_at_120_and_frenzy_at_500():
    rules = build_rosanna_signature_per_shot_rules(ROSANNA_SIG)
    assert sorted(every for every, _mode, _rules in rules) == [120, 500]
    assert {mode for _every, mode, _rules in rules} == {"every"}

    by_count = {every: shot_rules for every, _mode, shot_rules in rules}
    reg = EffectRegistry()
    ctx = _ctx()
    fire_trigger("per_shot", {"rosanna-signature": by_count[120]}, ctx, reg, 5.0)
    assert round(reg.total_for("crit_rate", SELF, 5.0), 4) == 0.1934

    reg = EffectRegistry()
    fire_trigger("per_shot", {"rosanna-signature": by_count[500]}, ctx, reg, 11.0)
    assert round(reg.total_for("atk_percent", SELF, 11.0), 4) == 0.2261
    assert reg.total_for("atk_percent", ALLY, 11.0) == 0.0
    assert reg.total_for("atk_percent", SELF, 41.1) == 0.0  # 30s


def test_frenzy_stacks_when_the_counter_completes_again_inside_its_duration():
    # 500 MG shots take ~11.1s of wall clock against a 30s buff, so a few
    # instances overlap - the engine produces the real count rather than the
    # skill text's unreachable 10-stack cap.
    rules = build_rosanna_signature_per_shot_rules(ROSANNA_SIG)
    frenzy = next(shot_rules for every, _m, shot_rules in rules if every == 500)
    reg = EffectRegistry()
    ctx = _ctx()
    for t in (11.1, 22.2, 33.3):
        fire_trigger("per_shot", {"rosanna-signature": frenzy}, ctx, reg, t)
    assert round(reg.total_for("atk_percent", SELF, 33.3), 4) == round(0.2261 * 3, 4)


def test_the_crit_buff_refreshes_while_frenzy_keeps_stacking():
    """Only Frenzy's text names a stack count ("Stacks up to 10 times"); the
    crit bullet does not, so it refreshes. 120 MG shots take 2.0 sec against a
    3 sec duration, and the two bullets must not collapse into each other."""
    by_count = {every: shot_rules for every, _mode, shot_rules in
                build_rosanna_signature_per_shot_rules(ROSANNA_SIG)}
    reg = EffectRegistry()
    ctx = _ctx()
    for time in (2.0, 4.0, 6.0, 8.0):
        fire_trigger("per_shot", {"rosanna-signature": by_count[120]}, ctx, reg, time)
    assert round(reg.total_for("crit_rate", SELF, 8.0), 4) == 0.1934

    fire_trigger("per_shot", {"rosanna-signature": by_count[500]}, ctx, reg, 11.1)
    fire_trigger("per_shot", {"rosanna-signature": by_count[120]}, ctx, reg, 12.0)
    assert round(reg.total_for("atk_percent", SELF, 12.0), 4) == 0.2261
    assert round(reg.total_for("crit_rate", SELF, 12.0), 4) == 0.1934
