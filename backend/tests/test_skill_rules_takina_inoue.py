from app.effects import EffectRegistry
from app.skill_rules.takina_inoue import (
    BATTLEFIELD_CONTROL_COOLDOWN,
    SUPPRESSION_SHOT_COUNT,
    build_battlefield_control_rules,
    build_combat_support_rules,
    build_suppression_initiated_rules,
    build_suppression_initiated_weapon_mode_schedule,
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


def test_suppression_initiated_burst_debuffs_squad_for_the_window():
    ctx = make_context()
    reg = EffectRegistry()
    fire_trigger("own_burst_activate", {"takina-inoue": build_suppression_initiated_rules(SUPPRESSION_INITIATED)}, ctx, reg, time=5.0)

    # on-hit Damage Taken, approximated squad(enemy) for the burst window
    assert round(reg.total_for("damage_taken_up", ALLY, now=5.0), 4) == 0.0604
    assert reg.total_for("damage_taken_up", ALLY, now=15.1) == 0.0
    # the true-conversion is no longer a self effect - it rides on the transform
    # segment's shots (see the weapon-mode test below).
    assert reg.total_for("normal_attacks_deal_true", TAKINA, now=5.0) == 0.0


def test_suppression_initiated_transform_fires_25_true_damage_shots():
    schedule = build_suppression_initiated_weapon_mode_schedule(
        {"suppression_initiated": SUPPRESSION_INITIATED})
    ctx = make_context()
    ctx.burst_times["takina-inoue"] = [5.0, 50.0]

    segments = schedule(ctx, 180.0)
    assert [seg["start"] for seg in segments] == [5.0, 50.0]
    assert all(seg["until_shots"] == SUPPRESSION_SHOT_COUNT for seg in segments)

    profile = segments[0]["profile"]
    assert profile["damage_percent"] == 200.64
    assert profile["damage_type"] == "true"  # her True Damage buffs land on these
    assert profile["weapon"] == "SR"
    # 25 hits across the 10-sec window -> 2.5 shots/sec, an anchor taking no
    # cadence buffs.
    assert profile["rate_of_fire"] == 2.5
    assert "charge_time" not in profile
