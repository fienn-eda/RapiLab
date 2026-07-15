from app.effects import EffectRegistry
from app.skill_rules.velvet import (
    BULLETS_OF_LOVE_NUKE_SHOT_COUNT,
    build_bullets_of_love_per_shot_rules,
    build_velvet_rules,
)
from app.squad_engine import SquadContext, SquadMember, fire_trigger

# Real skill level 10 values from lootandwaifus.com (Velvet).
CASTER_ATK = 70000.0
PERFECT_EXECUTION = {
    "description_value_01": "7",      # deferred: weapon-transform damage %
    "description_value_02": "10",     # deferred: its duration
    "description_value_03": "34.52",  # self Attack Damage %
    "description_value_04": "10",     # duration
}
BULLETS_OF_LOVE = {
    "description_value_01": "300",    # ammo expend (non-constraint, not modeled)
    "description_value_02": "25.2",   # squad ATK % of caster's ATK
    "description_value_03": "3",      # its duration
    "description_value_04": "100.8",  # squad Charge Damage %
    "description_value_05": "3",      # its duration
    "description_value_06": "50",     # normal-attack threshold (deferred nuke bullet)
    "description_value_07": "300",    # ammo expend (not modeled)
    "description_value_08": "15.03",  # self Attack Damage %
    "description_value_09": "5",      # its duration
    "description_value_10": "400.92", # nuke % of final ATK
}


def make_context():
    return SquadContext([
        SquadMember("velvet", burst_tier=2, element="Wind"),
        SquadMember("ally", burst_tier=3, element="Fire"),
    ])


def build():
    return build_velvet_rules({"perfect_execution": PERFECT_EXECUTION})


VELVET = {"slug": "velvet", "element": "Wind"}
ALLY = {"slug": "ally", "element": "Fire"}


def test_burst_grants_self_attack_damage_only():
    ctx = make_context()
    registry = EffectRegistry()
    fire_trigger("own_burst_activate", {"velvet": build()}, ctx, registry, time=5.0)

    assert round(registry.total_for("attack_damage_up", VELVET, now=5.0), 4) == 0.3452
    assert registry.total_for("attack_damage_up", ALLY, now=5.0) == 0.0  # self-only
    assert registry.total_for("attack_damage_up", VELVET, now=15.1) == 0.0


def _bullets_of_love():
    return build_bullets_of_love_per_shot_rules({
        "bullets_of_love": BULLETS_OF_LOVE,
        "caster_atk": CASTER_ATK,
    })


def test_bullets_of_love_rules_are_full_burst_window_gated():
    rules = _bullets_of_love()
    assert len(rules) == 2
    (t1, m1, _), (t2, m2, _) = rules
    assert (t1, m1) == (1, "every_during_full_burst")  # every in-FB full charge
    assert (t2, m2) == (BULLETS_OF_LOVE_NUKE_SHOT_COUNT, "every_during_full_burst")


def test_bullets_of_love_full_charge_grants_squad_atk_and_charge_damage():
    _, _, rules = _bullets_of_love()[0]
    ctx = make_context()
    registry = EffectRegistry()
    for rule in rules:
        rule.action(ctx, "velvet", 5.0, registry)

    # squad flat ATK = 25.2% of caster's ATK, for 3 sec, on allies AND velvet
    assert round(registry.total_for("flat_atk", ALLY, now=5.0), 4) == round(0.252 * CASTER_ATK, 4)
    assert round(registry.total_for("flat_atk", VELVET, now=5.0), 4) == round(0.252 * CASTER_ATK, 4)
    assert round(registry.total_for("charge_damage_bonus", ALLY, now=5.0), 4) == 1.008
    assert registry.total_for("flat_atk", ALLY, now=8.1) == 0.0  # 3s duration

    # a later full charge inside the window refreshes, not stacks
    for rule in rules:
        rule.action(ctx, "velvet", 6.0, registry)
    assert round(registry.total_for("flat_atk", ALLY, now=6.0), 4) == round(0.252 * CASTER_ATK, 4)


def test_bullets_of_love_50_normal_bullet_nukes_and_self_buffs():
    _, _, rules = _bullets_of_love()[1]
    ctx = make_context()
    registry = EffectRegistry()
    for rule in rules:
        rule.action(ctx, "velvet", 5.0, registry)

    assert round(registry.total_for("attack_damage_up", VELVET, now=5.0), 4) == 0.1503
    assert registry.total_for("attack_damage_up", ALLY, now=5.0) == 0.0  # self-only
    pulses = registry.drain_pulses("instant_damage_percent")
    assert len(pulses) == 1
    assert pulses[0].value == 400.92
    assert pulses[0].full_burst_bonus_eligible is True  # "as additional damage"
