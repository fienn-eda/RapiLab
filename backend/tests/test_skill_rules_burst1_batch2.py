"""Tests for the second batch of Burst-1 supporters: Rouge, Zwei, D: Killer
Wife. Values are the real max-level (dollskill for Zwei) figures from dotgg.
"""
from app.effects import EffectRegistry
from app.skill_rules.d_killer_wife import build_assault_formation_rules, build_d_killer_wife_rules
from app.skill_rules.rouge import build_rouge_rules
from app.skill_rules.zwei import build_zwei_rules
from app.squad_engine import SquadContext, SquadMember, fire_trigger

ALLY = {"slug": "ally", "element": "Fire"}


def deck_ctx(src_slug):
    return SquadContext([
        SquadMember(src_slug, burst_tier=1, element="Electric"),
        SquadMember("ally", burst_tier=3, element="Fire"),
    ])


def test_rouge_game_master_grants_caster_scaled_flat_atk_squadwide():
    values = {
        "game_master": {
            "description_value_01": "15.07", "description_value_02": "10", "description_value_03": "10.15",
            "description_value_04": "10", "description_value_05": "20.1", "description_value_06": "10",
            "description_value_07": "30.02", "description_value_08": "10",
        },
        "caster_atk": 300000,
    }
    reg = EffectRegistry()
    fire_trigger("own_burst_activate", {"rouge": build_rouge_rules(values)}, deck_ctx("rouge"), reg, 0.0)
    # 30.02% of Rouge's 300000 ATK = 90060 flat ATK to the squad
    assert round(reg.total_for("flat_atk", ALLY, 0.0), 2) == 90060.0
    assert reg.total_for("flat_atk", ALLY, 10.1) == 0.0


ZWEI = {
    "pierce_equation": {
        "description_value_01": "20.13", "description_value_02": "1", "description_value_03": "10.06",
        "description_value_04": "10", "description_value_05": "24.99", "description_value_06": "3", "description_value_07": "1",
    },
    "frame_analysis": {
        "description_value_01": "5", "description_value_02": "7.52", "description_value_03": "18.63",
        "description_value_04": "10", "description_value_05": "15", "description_value_06": "3", "description_value_07": "5",
    },
    "overcharge_formula": {
        "description_value_01": "50.69", "description_value_02": "1", "description_value_03": "25.03", "description_value_04": "10",
    },
}


def test_zwei_pierce_and_crit_rate_on_full_burst_and_burst():
    reg = EffectRegistry()
    rules = {"zwei": build_zwei_rules(ZWEI)}
    fire_trigger("full_burst_enter", rules, deck_ctx("zwei"), reg, 0.0)
    assert round(reg.total_for("pierce_damage_up", ALLY, 0.0), 4) == 0.1006
    assert round(reg.total_for("crit_rate", ALLY, 0.0), 4) == 0.1863
    fire_trigger("own_burst_activate", rules, deck_ctx("zwei"), reg, 0.0)
    # note: separate ctx above; re-fire on same reg to check burst pierce adds
    reg2 = EffectRegistry()
    fire_trigger("own_burst_activate", rules, deck_ctx("zwei"), reg2, 0.0)
    assert round(reg2.total_for("pierce_damage_up", ALLY, 0.0), 4) == 0.2503


DKW = {
    "calm_sniping": {"description_value_01": "3", "description_value_02": "13.55", "description_value_03": "10"},
    # Assault Formation (skills[1]), Lv.10, left-to-right: CDR count/sec (deferred),
    # then Attack Damage count/value/duration.
    "assault_formation": {
        "description_value_01": "8", "description_value_02": "7", "description_value_03": "5",
        "description_value_04": "5.06", "description_value_05": "10",
    },
}


def test_d_killer_wife_pierce_buff_on_full_burst():
    reg = EffectRegistry()
    fire_trigger("full_burst_enter", {"d-killer-wife": build_d_killer_wife_rules(DKW)}, deck_ctx("d-killer-wife"), reg, 0.0)
    assert round(reg.total_for("pierce_damage_up", ALLY, 0.0), 4) == 0.1355


def test_d_killer_wife_assault_formation_squad_attack_damage_every_5_full_charges():
    rules = build_assault_formation_rules(DKW["assault_formation"])
    assert len(rules) == 1
    threshold, mode, skill_rules = rules[0]
    assert (threshold, mode) == (5, "every")  # every 5 full charges

    reg = EffectRegistry()
    for rule in skill_rules:
        rule.action(deck_ctx("d-killer-wife"), "d-killer-wife", 8.0, reg)
    assert round(reg.total_for("attack_damage_up", ALLY, 8.0), 4) == 0.0506
    assert reg.total_for("attack_damage_up", ALLY, 18.1) == 0.0  # 10s duration
