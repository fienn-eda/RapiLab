"""Tests for the first batch of Burst-1 supporters: Liter, Volume, Miranda.
Values are the real max-level (dollskill for Miranda) figures from dotgg.
"""
from app.effects import EffectRegistry
from app.skill_rules.liter import build_liter_rules
from app.skill_rules.miranda import build_miranda_rules
from app.skill_rules.volume import build_volume_rules
from app.squad_engine import SquadContext, SquadMember, fire_trigger

ALLY = {"slug": "ally", "element": "Fire"}


def deck_ctx(src_slug):
    return SquadContext([
        SquadMember(src_slug, burst_tier=1, element="Iron"),
        SquadMember("ally", burst_tier=3, element="Fire"),
    ])


LITER = {
    "liter_boost": {
        "description_value_01": "2.34", "description_value_02": "2.7", "description_value_03": "3.17",
        "description_value_04": "45.17", "description_value_05": "5", "description_value_06": "12.46",
        "description_value_07": "5", "description_value_08": "14.42", "description_value_09": "5",
    },
    "double_boost": {"description_value_01": "66", "description_value_02": "5"},
}


def test_liter_full_burst_cdr_and_burst_squad_buffs():
    ctx = deck_ctx("liter")
    reg = EffectRegistry()
    rules = {"liter": build_liter_rules(LITER)}

    fire_trigger("full_burst_enter", rules, ctx, reg, time=2.0)
    assert reg.drain_pulses("burst_cooldown_reduction_sec")[0].value == 3.17

    fire_trigger("own_burst_activate", rules, ctx, reg, time=2.0)
    assert round(reg.total_for("atk_percent", ALLY, 2.0), 4) == round(0.1442 + 0.66, 4)
    assert round(reg.total_for("max_ammo_percent", ALLY, 2.0), 4) == 0.4517
    assert round(reg.total_for("other_critical_damage_sources", ALLY, 2.0), 4) == 0.1246


VOLUME = {
    "drop_the_beat": {
        "description_value_01": "2.34", "description_value_02": "2.7", "description_value_03": "3.17",
        "description_value_04": "10.77", "description_value_05": "5", "description_value_06": "12.46",
        "description_value_07": "5", "description_value_08": "14.42", "description_value_09": "5",
    },
    "turn_up": {"description_value_01": "31.9", "description_value_02": "5"},
}


def test_volume_stacks_three_crit_damage_tiers_and_grants_crit_rate():
    ctx = deck_ctx("volume")
    reg = EffectRegistry()
    rules = {"volume": build_volume_rules(VOLUME)}

    fire_trigger("full_burst_enter", rules, ctx, reg, time=0.0)
    assert reg.drain_pulses("burst_cooldown_reduction_sec")[0].value == 3.17

    fire_trigger("own_burst_activate", rules, ctx, reg, time=0.0)
    # crit damage tiers 10.77 + 12.46 + 14.42 = 37.65% stacked
    assert round(reg.total_for("other_critical_damage_sources", ALLY, 0.0), 4) == 0.3765
    assert round(reg.total_for("crit_rate", ALLY, 0.0), 4) == 0.319


MIRANDA = {
    "wake_up": {
        "description_value_01": "32.99", "description_value_02": "10", "description_value_03": "30.1",
        "description_value_04": "10", "description_value_05": "23.7", "description_value_06": "10",
        "description_value_07": "1", "description_value_08": "85.42", "description_value_09": "1",
    },
    "powering_up": {
        "description_value_01": "2", "description_value_02": "40.4", "description_value_03": "10",
        "description_value_04": "56.23", "description_value_05": "10",
    },
}


def test_miranda_full_burst_squad_crit_damage_and_self_buffs():
    ctx = deck_ctx("miranda")
    reg = EffectRegistry()
    rules = {"miranda": build_miranda_rules(MIRANDA)}

    fire_trigger("full_burst_enter", rules, ctx, reg, time=0.0)
    assert round(reg.total_for("other_critical_damage_sources", ALLY, 0.0), 4) == 0.3299  # squad
    miranda = {"slug": "miranda", "element": "Iron"}
    assert round(reg.total_for("crit_rate", miranda, 0.0), 4) == 0.301  # self
    assert reg.total_for("crit_rate", ALLY, 0.0) == 0.0  # not squad
    assert round(reg.total_for("attack_damage_up", miranda, 0.0), 4) == 0.237  # self


def test_miranda_burst_applies_atk_and_crit_damage_squadwide_approx():
    ctx = deck_ctx("miranda")
    reg = EffectRegistry()
    rules = {"miranda": build_miranda_rules(MIRANDA)}

    fire_trigger("own_burst_activate", rules, ctx, reg, time=0.0)
    assert round(reg.total_for("atk_percent", ALLY, 0.0), 4) == 0.404
    assert round(reg.total_for("other_critical_damage_sources", ALLY, 0.0), 4) == 0.5623
