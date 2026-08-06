from app.effects import EffectRegistry
from app.skill_rules.anis_sparkling_summer import (
    build_anis_sparkling_summer_rules,
    build_sparkling_missile_per_shot_rules,
)
from app.squad_engine import SquadContext, SquadMember, fire_trigger

# Real skill level 10 values from lootandwaifus.com (Anis: Sparkling Summer).
CASTER_ATK = 80000.0

SPARKLING_BOOST = {
    "description_value_01": "55.31",  # ATK % of caster's ATK (Electric allies)
    "description_value_02": "10",     # its duration
    "description_value_03": "49.28",  # Reload Speed %
    "description_value_04": "10",     # its duration
}
SPARKLING_MISSILE = {
    "description_value_01": "382.42",  # last-bullet nuke % of final ATK
    "description_value_02": "6.91",    # self Damage to Interruption Parts %
    "description_value_03": "10",      # its duration
}
SPARKLING_WAVE = {
    "description_value_01": "73.92",  # Max Ammunition Capacity % (self)
    "description_value_02": "10",     # its duration
    "description_value_03": "27.72",  # Reload Speed % (self)
    "description_value_04": "10",     # its duration
    "description_value_05": "42.24",  # Elemental Advantage Attack Damage % (self)
    "description_value_06": "10",     # its duration
}


def make_context(boss_element=None):
    return SquadContext([
        SquadMember("anis-sparkling-summer", burst_tier=3, element="Electric"),
        SquadMember("electric-ally", burst_tier=1, element="Electric"),
        SquadMember("fire-ally", burst_tier=2, element="Fire"),
    ], boss_element=boss_element)


def build():
    return build_anis_sparkling_summer_rules({
        "sparkling_boost": SPARKLING_BOOST,
        "sparkling_wave": SPARKLING_WAVE,
        "caster_atk": CASTER_ATK,
    })


ANIS = {"slug": "anis-sparkling-summer", "element": "Electric"}
ELECTRIC_ALLY = {"slug": "electric-ally", "element": "Electric"}
FIRE_ALLY = {"slug": "fire-ally", "element": "Fire"}


def test_sparkling_boost_buffs_electric_allies_on_full_burst():
    ctx = make_context()
    registry = EffectRegistry()
    fire_trigger("full_burst_enter", {"anis-sparkling-summer": build()}, ctx, registry, time=5.0)

    assert registry.total_for("flat_atk", ELECTRIC_ALLY, now=5.0) == CASTER_ATK * 0.5531
    assert round(registry.total_for("reload_speed_percent", ELECTRIC_ALLY, now=5.0), 4) == 0.4928
    # Anis is Electric herself, so element:Electric includes her.
    assert registry.total_for("flat_atk", ANIS, now=5.0) == CASTER_ATK * 0.5531


def test_sparkling_boost_skips_non_electric_allies():
    ctx = make_context()
    registry = EffectRegistry()
    fire_trigger("full_burst_enter", {"anis-sparkling-summer": build()}, ctx, registry, time=5.0)

    assert registry.total_for("flat_atk", FIRE_ALLY, now=5.0) == 0.0
    assert registry.total_for("reload_speed_percent", FIRE_ALLY, now=5.0) == 0.0


def test_sparkling_boost_expires_after_10s():
    ctx = make_context()
    registry = EffectRegistry()
    fire_trigger("full_burst_enter", {"anis-sparkling-summer": build()}, ctx, registry, time=5.0)

    assert registry.total_for("flat_atk", ELECTRIC_ALLY, now=15.1) == 0.0


def test_burst_grants_self_ammo_and_reload():
    ctx = make_context()
    registry = EffectRegistry()
    fire_trigger("own_burst_activate", {"anis-sparkling-summer": build()}, ctx, registry, time=5.0)

    # "Max Ammunition Capacity ▼ 73.92%" - her burst SHRINKS her magazine, which
    # is the point: a 5-round shotgun drops to 1 round, so every shot is a last
    # bullet and Sparkling Missile's 382.42% nuke fires on each of them.
    assert round(registry.total_for("max_ammo_percent", ANIS, now=5.0), 4) == -0.7392
    assert round(registry.total_for("reload_speed_percent", ANIS, now=5.0), 4) == 0.2772
    # self-scoped: allies don't share it
    assert registry.total_for("max_ammo_percent", ELECTRIC_ALLY, now=5.0) == 0.0


def test_burst_grants_water_gated_elemental_advantage():
    # Anis is Electric, so her Elemental Advantage Attack Damage only counts
    # against a Water boss (Electric > Water). It lands in the Element Bonus
    # group (other_elemental_bonus), self-scoped, for 10 sec.
    water = make_context(boss_element="Water")
    registry = EffectRegistry()
    fire_trigger("own_burst_activate", {"anis-sparkling-summer": build()}, water, registry, time=5.0)

    assert round(registry.total_for("other_elemental_bonus", ANIS, now=5.0), 4) == 0.4224
    assert registry.total_for("other_elemental_bonus", ANIS, now=15.1) == 0.0  # expires after 10s
    # self-scoped: allies don't share it
    assert registry.total_for("other_elemental_bonus", ELECTRIC_ALLY, now=5.0) == 0.0

    # No elemental advantage against a non-Water boss.
    non_water = make_context(boss_element="Fire")
    registry2 = EffectRegistry()
    fire_trigger("own_burst_activate", {"anis-sparkling-summer": build()}, non_water, registry2, time=5.0)
    assert registry2.total_for("other_elemental_bonus", ANIS, now=5.0) == 0.0


def test_sparkling_missile_last_bullet_nuke_and_self_parts_buff():
    rules = build_sparkling_missile_per_shot_rules(SPARKLING_MISSILE)
    assert len(rules) == 1
    threshold, mode, skill_rules = rules[0]
    assert (threshold, mode) == (None, "last_bullet")

    ctx = make_context()
    registry = EffectRegistry()
    for rule in skill_rules:
        rule.action(ctx, "anis-sparkling-summer", 3.0, registry)

    pulses = registry.drain_pulses("instant_damage_percent")
    assert len(pulses) == 1
    assert pulses[0].value == 382.42
    assert pulses[0].source_slug == "anis-sparkling-summer"

    # self-scoped Damage to Interruption Parts +6.91% for 10 sec
    assert round(registry.total_for("damage_to_interruption_parts_up", ANIS, now=3.0), 4) == 0.0691
    assert registry.total_for("damage_to_interruption_parts_up", ELECTRIC_ALLY, now=3.0) == 0.0
    assert registry.total_for("damage_to_interruption_parts_up", ANIS, now=13.1) == 0.0


def test_sparkling_missile_parts_buff_refreshes_not_stacks():
    rules = build_sparkling_missile_per_shot_rules(SPARKLING_MISSILE)
    _, _, skill_rules = rules[0]
    ctx = make_context()
    registry = EffectRegistry()
    # Two last-bullets within the 10s window must refresh, not stack.
    for rule in skill_rules:
        rule.action(ctx, "anis-sparkling-summer", 3.0, registry)
    for rule in skill_rules:
        rule.action(ctx, "anis-sparkling-summer", 8.0, registry)
    registry.drain_pulses("instant_damage_percent")
    assert round(registry.total_for("damage_to_interruption_parts_up", ANIS, now=8.0), 4) == 0.0691
