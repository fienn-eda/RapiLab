from app.effects import EffectRegistry
from app.skill_rules.marciana_marine_study import (
    HIGH_RISK_NUKE_SHOT_COUNT,
    WHISTLE_CAP,
    build_marciana_per_shot_rules,
    build_marciana_rules,
)
from app.squad_engine import SquadContext, SquadMember, fire_trigger

# Real skill level 10 values from lootandwaifus.com (Marciana: Marine Study).
# Slots numbered left-to-right by scaling-value appearance in the skill text.
EMERGENCY_WHISTLE = {
    "description_value_01": "3789.25",  # Flagged Target Designation additional-damage nuke %
    "description_value_02": "10.56",    # Flagged Target ATK % (deferred - ambiguous scope)
    "description_value_03": "152.68",   # High-Risk 20-normal additional-damage nuke %
}
PENGUIN_EMERGENCY_DISPATCH = {
    "description_value_01": "32.73",  # Whistle ATK % per stack (up to 5)
    "description_value_02": "20.41",  # Elemental Advantage Attack Damage % (continuous)
}
PENGUIN_SPIRAL = {
    "description_value_01": "30.97",  # self Elemental Advantage Attack Damage % (10s)
    "description_value_02": "27.45",  # self Attack Damage % (10s)
    "description_value_03": "10.56",  # High-Risk Target DEF down %
}

SKILL_VALUES = {
    "emergency_whistle": EMERGENCY_WHISTLE,
    "penguin_emergency_dispatch": PENGUIN_EMERGENCY_DISPATCH,
    "penguin_spiral": PENGUIN_SPIRAL,
}

SELF = {"slug": "marciana-marine-study", "element": "Iron"}
SQUAD_ALLY = {"slug": "ally", "element": "Fire"}


def make_context(boss_element=None):
    return SquadContext([
        SquadMember("marciana-marine-study", burst_tier=3, element="Iron"),
        SquadMember("ally", burst_tier=1, element="Fire"),
    ], boss_element=boss_element)


def build():
    return build_marciana_rules(SKILL_VALUES)


def test_whistle_steady_state_grants_self_atk_from_battle_start():
    # Whistle: ATK +32.73% per stack, capped at 5 stacks (163.65%), always at cap
    # under the raptures=1 assumption - modeled as a permanent self buff.
    ctx = make_context()
    registry = EffectRegistry()
    fire_trigger("battle_start", {"marciana-marine-study": build()}, ctx, registry, time=0.0)
    assert round(registry.total_for("atk_percent", SELF, now=90.0), 4) == round(0.3273 * WHISTLE_CAP, 4)


def test_elemental_advantage_goes_in_element_bonus_group_only_against_electric_boss():
    # "Elemental Advantage Attack Damage +20.41% continuously" is Element Bonus
    # Damage (only counts with elemental advantage, Iron > Electric), so it lands
    # in other_elemental_bonus - NOT attack_damage_up - gated on an Electric boss.
    electric = make_context(boss_element="Electric")
    registry = EffectRegistry()
    fire_trigger("battle_start", {"marciana-marine-study": build()}, electric, registry, time=0.0)
    assert round(registry.total_for("other_elemental_bonus", SELF, now=90.0), 4) == 0.2041
    assert registry.total_for("attack_damage_up", SELF, now=90.0) == 0.0

    non_electric = make_context(boss_element="Fire")
    registry2 = EffectRegistry()
    fire_trigger("battle_start", {"marciana-marine-study": build()}, non_electric, registry2, time=0.0)
    assert registry2.total_for("other_elemental_bonus", SELF, now=90.0) == 0.0


def test_burst_grants_self_attack_damage_and_electric_gated_elem_advantage():
    electric = make_context(boss_element="Electric")
    registry = EffectRegistry()
    fire_trigger("own_burst_activate", {"marciana-marine-study": build()}, electric, registry, time=5.0)
    # Unconditional Attack Damage 27.45% (Damage-Up group); Elemental Advantage
    # 30.97% goes in the Element Bonus group, gated on Electric.
    assert round(registry.total_for("attack_damage_up", SELF, now=5.0), 4) == 0.2745
    assert round(registry.total_for("other_elemental_bonus", SELF, now=5.0), 4) == 0.3097
    assert registry.total_for("attack_damage_up", SELF, now=15.1) == 0.0
    assert registry.total_for("other_elemental_bonus", SELF, now=15.1) == 0.0

    non_electric = make_context(boss_element="Fire")
    registry2 = EffectRegistry()
    fire_trigger("own_burst_activate", {"marciana-marine-study": build()}, non_electric, registry2, time=5.0)
    # Only the unconditional Attack Damage against a non-Electric boss.
    assert round(registry2.total_for("attack_damage_up", SELF, now=5.0), 4) == 0.2745
    assert registry2.total_for("other_elemental_bonus", SELF, now=5.0) == 0.0


def test_high_risk_def_debuff_only_against_electric_boss():
    electric = make_context(boss_element="Electric")
    registry = EffectRegistry()
    fire_trigger("own_burst_activate", {"marciana-marine-study": build()}, electric, registry, time=5.0)
    # DEF -10.56% on the boss (squad-scope enemy debuff) for 20 sec.
    assert round(registry.total_for("enemy_def_percent", SQUAD_ALLY, now=5.0), 4) == -0.1056
    assert registry.total_for("enemy_def_percent", SQUAD_ALLY, now=25.1) == 0.0

    non_electric = make_context(boss_element="Wind")
    registry2 = EffectRegistry()
    fire_trigger("own_burst_activate", {"marciana-marine-study": build()}, non_electric, registry2, time=5.0)
    assert registry2.total_for("enemy_def_percent", SQUAD_ALLY, now=5.0) == 0.0


def test_flagged_target_nuke_fires_on_full_burst_after_own_burst():
    ctx = make_context()
    registry = EffectRegistry()
    rules = {"marciana-marine-study": build()}

    # Without her own burst this cycle, the nuke does not fire.
    fire_trigger("full_burst_enter", rules, ctx, registry, time=5.0)
    assert registry.drain_pulses("instant_damage_percent") == []

    # After her own burst fired this cycle, the 3789.25% additional-damage nuke
    # fires and is Full Burst Bonus eligible ("as additional damage").
    ctx.burst_used_this_cycle.add("marciana-marine-study")
    fire_trigger("full_burst_enter", rules, ctx, registry, time=5.0)
    pulses = registry.drain_pulses("instant_damage_percent")
    assert len(pulses) == 1
    assert pulses[0].value == 3789.25
    assert pulses[0].full_burst_bonus_eligible is True


def test_high_risk_20_normal_nuke_fires_every_20_normals_gated_on_electric():
    rules = build_marciana_per_shot_rules(SKILL_VALUES)
    assert len(rules) == 1
    threshold, mode, skill_rules = rules[0]
    assert threshold == HIGH_RISK_NUKE_SHOT_COUNT
    assert mode == "every"

    electric = make_context(boss_element="Electric")
    registry = EffectRegistry()
    for rule in skill_rules:
        if rule.condition(electric, "marciana-marine-study"):
            rule.action(electric, "marciana-marine-study", 8.0, registry)
    pulses = registry.drain_pulses("instant_damage_percent")
    assert len(pulses) == 1
    assert pulses[0].value == 152.68
    assert pulses[0].full_burst_bonus_eligible is True

    non_electric = make_context(boss_element="Water")
    registry2 = EffectRegistry()
    for rule in skill_rules:
        if rule.condition(non_electric, "marciana-marine-study"):
            rule.action(non_electric, "marciana-marine-study", 8.0, registry2)
    assert registry2.drain_pulses("instant_damage_percent") == []
