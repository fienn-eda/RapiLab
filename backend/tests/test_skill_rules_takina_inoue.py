from app.effects import EffectRegistry
from app.skill_rules.takina_inoue import (
    BATTLEFIELD_CONTROL_COOLDOWN,
    build_battlefield_control_rules,
    build_combat_support_rules,
    build_suppression_initiated_rules,
)
from app.squad_engine import SquadContext, SquadMember, fire_trigger

# Real skill level 10 values from lootandwaifus.com (Takina Inoue).
COMBAT_SUPPORT = {
    "description_value_01": "80.04",  # self ATK %
    "description_value_02": "5",      # duration
    "description_value_03": "35.05",  # self True Damage %
    "description_value_04": "15",     # duration
}
BATTLEFIELD_CONTROL = {
    "description_value_01": "10.09",   # enemy Damage Taken %
    "description_value_02": "5",       # duration
    "description_value_03": "140.49",  # ally True Damage %
    "description_value_04": "10",      # duration
}
SUPPRESSION_INITIATED = {
    "description_value_01": "200.64",  # weapon-transform damage % (deferred)
    "description_value_02": "10",      # transform / true-conversion window
    "description_value_03": "6.04",    # on-hit Damage Taken %
    "description_value_04": "5",       # its per-hit duration (approximated to window)
}


def make_context():
    return SquadContext([
        SquadMember("takina-inoue", burst_tier=2, element="Iron"),
        SquadMember("ally", burst_tier=3, element="Fire"),
    ])


TAKINA = {"slug": "takina-inoue", "element": "Iron"}
ALLY = {"slug": "ally", "element": "Fire"}


def test_battlefield_control_cooldown_is_15s():
    assert BATTLEFIELD_CONTROL_COOLDOWN == 15.0


def test_combat_support_self_atk_on_battle_start_and_full_burst_end():
    ctx = make_context()
    rules = {"takina-inoue": build_combat_support_rules(COMBAT_SUPPORT)}

    reg = EffectRegistry()
    fire_trigger("battle_start", rules, ctx, reg, time=0.0)
    assert round(reg.total_for("atk_percent", TAKINA, now=0.0), 4) == 0.8004
    assert reg.total_for("atk_percent", ALLY, now=0.0) == 0.0  # self only
    assert reg.total_for("atk_percent", TAKINA, now=5.1) == 0.0

    reg2 = EffectRegistry()
    fire_trigger("full_burst_end", rules, ctx, reg2, time=20.0)
    assert round(reg2.total_for("atk_percent", TAKINA, now=20.0), 4) == 0.8004


def test_combat_support_self_true_damage_on_full_burst_enter():
    ctx = make_context()
    reg = EffectRegistry()
    fire_trigger("full_burst_enter", {"takina-inoue": build_combat_support_rules(COMBAT_SUPPORT)}, ctx, reg, time=10.0)
    assert round(reg.total_for("true_damage_up", TAKINA, now=10.0), 4) == 0.3505
    assert reg.total_for("true_damage_up", ALLY, now=10.0) == 0.0  # self only
    assert reg.total_for("true_damage_up", TAKINA, now=25.1) == 0.0


def test_battlefield_control_squad_debuff_and_true_damage():
    ctx = make_context()
    reg = EffectRegistry()
    for rule in build_battlefield_control_rules(BATTLEFIELD_CONTROL):
        rule.action(ctx, "takina-inoue", 15.0, reg)
    assert round(reg.total_for("damage_taken_up", ALLY, now=15.0), 4) == 0.1009
    assert round(reg.total_for("true_damage_up", ALLY, now=15.0), 4) == 1.4049
    assert reg.total_for("damage_taken_up", ALLY, now=20.1) == 0.0  # 5s window
    assert round(reg.total_for("true_damage_up", ALLY, now=24.9), 4) == 1.4049  # 10s window
    assert reg.total_for("true_damage_up", ALLY, now=25.1) == 0.0


def test_battlefield_control_rules_are_labeled_periodic():
    assert all(r.trigger == "periodic" for r in build_battlefield_control_rules(BATTLEFIELD_CONTROL))


def test_suppression_initiated_burst_converts_normals_to_true_and_debuffs():
    ctx = make_context()
    reg = EffectRegistry()
    fire_trigger("own_burst_activate", {"takina-inoue": build_suppression_initiated_rules(SUPPRESSION_INITIATED)}, ctx, reg, time=5.0)

    # normal attacks deal true damage (self, 10s)
    assert reg.total_for("normal_attacks_deal_true", TAKINA, now=5.0) == 1.0
    assert reg.total_for("normal_attacks_deal_true", ALLY, now=5.0) == 0.0
    assert reg.total_for("normal_attacks_deal_true", TAKINA, now=15.1) == 0.0
    # on-hit Damage Taken, approximated squad(enemy) for the burst window
    assert round(reg.total_for("damage_taken_up", ALLY, now=5.0), 4) == 0.0604
