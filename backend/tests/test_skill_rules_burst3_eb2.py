"""Burst-3 attacker batch eb2: Ludmilla: Winter Owner, Chisato Nishikigi, Jill
Valentine. Real max-level (base-skill) figures from lootandwaifus, slots numbered
left-to-right per skill.
"""
from app.effects import EffectRegistry
from app.skill_rules.chisato_nishikigi import build_chisato_per_shot_rules, build_chisato_rules
from app.skill_rules.jill_valentine import build_jill_rules
from app.skill_rules.ludmilla_winter_owner import (
    build_ludmilla_per_shot_rules,
    build_ludmilla_rules,
)
from app.squad_engine import SquadContext, SquadMember, fire_trigger

ALLY = {"slug": "ally", "element": "Iron"}


def deck_ctx(src_slug, element):
    return SquadContext([
        SquadMember(src_slug, burst_tier=3, element=element),
        SquadMember("ally", burst_tier=1, element="Iron"),
    ])


# --- Ludmilla: Winter Owner (MG/Water) ---
LUDMILLA = {
    "queens_gaze": {
        "description_value_01": "60", "description_value_02": "12.56", "description_value_03": "3",
        "description_value_04": "158.43", "description_value_05": "60", "description_value_06": "20",
    },
    "snowstorm": {
        "description_value_01": "60", "description_value_02": "109.64",
        "description_value_03": "14.6", "description_value_04": "10",
    },
    "guiding_lantern": {
        "description_value_01": "62.54", "description_value_02": "10",
        "description_value_03": "67.2", "description_value_04": "20",
    },
}
LUD = {"slug": "ludmilla", "element": "Water"}


def test_ludmilla_full_burst_crit_and_burst_atk_reload():
    reg = EffectRegistry()
    rules = {"ludmilla": build_ludmilla_rules(LUDMILLA)}
    ctx = deck_ctx("ludmilla", "Water")
    fire_trigger("full_burst_enter", rules, ctx, reg, 0.0)
    assert round(reg.total_for("crit_rate", LUD, 0.0), 4) == 0.146
    fire_trigger("own_burst_activate", rules, ctx, reg, 0.0)
    assert round(reg.total_for("atk_percent", LUD, 0.0), 4) == 0.6254
    assert round(reg.total_for("reload_speed_percent", LUD, 0.0), 4) == 0.672
    assert reg.total_for("reload_speed_percent", LUD, 21.0) == 0.0  # 20s expired


def test_ludmilla_per_shot_every_60_normal_debuff_and_nuke():
    ps = build_ludmilla_per_shot_rules(LUDMILLA)
    assert len(ps) == 1  # Snowstorm core-60 nuke deferred (see module docstring)
    threshold, mode, rules = ps[0]
    assert (threshold, mode) == (60, "every")
    reg = EffectRegistry()
    ctx = deck_ctx("ludmilla", "Water")
    for rule in rules:
        rule.action(ctx, "ludmilla", 5.0, reg)
    assert round(reg.total_for("damage_taken_up", ALLY, 5.0), 4) == 0.1256  # squad debuff
    assert reg.total_for("damage_taken_up", ALLY, 8.1) == 0.0  # 3s expired
    assert [round(p.value, 2) for p in reg.drain_pulses("instant_damage_percent")] == [158.43]


# --- Chisato Nishikigi (SMG/Iron) ---
CHISATO = {
    "extrasensory": {"description_value_06": "53.69", "description_value_08": "48.62"},
    "ap_rounds": {"description_value_01": "10", "description_value_02": "48", "description_value_03": "472.18"},
    "emergency_charge": {"description_value_01": "100", "description_value_02": "73.16", "description_value_03": "10"},
}
CHI = {"slug": "chisato-nishikigi", "element": "Iron"}


def test_chisato_extrasensory_steady_state_self_buffs():
    reg = EffectRegistry()
    rules = {"chisato-nishikigi": build_chisato_rules(CHISATO)}
    ctx = deck_ctx("chisato-nishikigi", "Iron")
    fire_trigger("battle_start", rules, ctx, reg, 0.0)
    assert round(reg.total_for("atk_percent", CHI, 100.0), 4) == 0.5369       # permanent
    assert round(reg.total_for("true_damage_up", CHI, 100.0), 4) == 0.4862    # permanent
    assert reg.total_for("atk_percent", ALLY, 100.0) == 0.0                   # self-only


def test_chisato_burst_atk_and_true_conversion():
    reg = EffectRegistry()
    rules = {"chisato-nishikigi": build_chisato_rules(CHISATO)}
    ctx = deck_ctx("chisato-nishikigi", "Iron")
    fire_trigger("own_burst_activate", rules, ctx, reg, 0.0)
    assert round(reg.total_for("atk_percent", CHI, 0.0), 4) == 0.7316
    assert reg.total_for("normal_attacks_deal_true", CHI, 0.0) == 1.0
    assert reg.total_for("normal_attacks_deal_true", CHI, 10.1) == 0.0  # 10s window


def test_chisato_per_shot_true_nuke_every_48():
    ps = build_chisato_per_shot_rules(CHISATO)
    assert len(ps) == 1
    threshold, mode, rules = ps[0]
    assert (threshold, mode) == (48, "every")
    reg = EffectRegistry()
    ctx = deck_ctx("chisato-nishikigi", "Iron")
    for rule in rules:
        rule.action(ctx, "chisato-nishikigi", 5.0, reg)
    assert [round(p.value, 2) for p in reg.drain_pulses("instant_damage_percent")] == [472.18]


# --- Jill Valentine (AR/Electric) ---
JILL = {
    "magnum_ammo": {"description_value_01": "30", "description_value_02": "9", "description_value_03": "34.99", "description_value_04": "10"},
    "acid_ammo": {"description_value_01": "192", "description_value_02": "1", "description_value_03": "30", "description_value_04": "40.03", "description_value_05": "10"},
    "supercop": {
        "description_value_01": "99.96", "description_value_02": "10", "description_value_03": "100",
        "description_value_04": "80.78", "description_value_05": "10", "description_value_06": "75",
        "description_value_07": "10", "description_value_08": "10",
    },
}
JIL = {"slug": "jill-valentine", "element": "Electric"}


def test_jill_full_burst_self_atk():
    reg = EffectRegistry()
    rules = {"jill-valentine": build_jill_rules(JILL)}
    ctx = deck_ctx("jill-valentine", "Electric")
    fire_trigger("full_burst_enter", rules, ctx, reg, 0.0)
    assert round(reg.total_for("atk_percent", JIL, 0.0), 4) == 0.4003


def test_jill_burst_true_damage_attack_damage_reload_and_conversion():
    reg = EffectRegistry()
    rules = {"jill-valentine": build_jill_rules(JILL)}
    ctx = deck_ctx("jill-valentine", "Electric")
    fire_trigger("own_burst_activate", rules, ctx, reg, 0.0)
    assert round(reg.total_for("true_damage_up", JIL, 0.0), 4) == 0.3499
    assert round(reg.total_for("attack_damage_up", JIL, 0.0), 4) == 0.75
    assert round(reg.total_for("reload_speed_percent", JIL, 0.0), 4) == 0.9996
    assert reg.total_for("normal_attacks_deal_true", JIL, 0.0) == 1.0
    assert reg.total_for("normal_attacks_deal_true", JIL, 10.1) == 0.0
