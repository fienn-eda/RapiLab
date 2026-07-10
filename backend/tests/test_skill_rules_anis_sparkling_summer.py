from app.effects import EffectRegistry
from app.skill_rules.anis_sparkling_summer import build_anis_sparkling_summer_rules
from app.squad_engine import SquadContext, SquadMember, fire_trigger

# Real skill level 10 values from lootandwaifus.com (Anis: Sparkling Summer).
CASTER_ATK = 80000.0

SPARKLING_BOOST = {
    "description_value_01": "55.31",  # ATK % of caster's ATK (Electric allies)
    "description_value_02": "10",     # its duration
    "description_value_03": "49.28",  # Reload Speed %
    "description_value_04": "10",     # its duration
}
SPARKLING_WAVE = {
    "description_value_01": "73.92",  # Max Ammunition Capacity % (self)
    "description_value_02": "10",     # its duration
    "description_value_03": "27.72",  # Reload Speed % (self)
    "description_value_04": "10",     # its duration
}


def make_context():
    return SquadContext([
        SquadMember("anis-sparkling-summer", burst_tier=3, element="Electric"),
        SquadMember("electric-ally", burst_tier=1, element="Electric"),
        SquadMember("fire-ally", burst_tier=2, element="Fire"),
    ])


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

    assert round(registry.total_for("max_ammo_percent", ANIS, now=5.0), 4) == 0.7392
    assert round(registry.total_for("reload_speed_percent", ANIS, now=5.0), 4) == 0.2772
    # self-scoped: allies don't share it
    assert registry.total_for("max_ammo_percent", ELECTRIC_ALLY, now=5.0) == 0.0
