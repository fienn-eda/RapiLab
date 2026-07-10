from app.effects import EffectRegistry
from app.skill_rules.rosanna_chic_ocean import build_rosanna_rules
from app.squad_engine import SquadContext, SquadMember, fire_trigger

# Real skill level 10 values from lootandwaifus.com (Rosanna: Chic Ocean).
FERITA = {
    "description_value_01": "24.26",  # Damage to Parts %
    "description_value_02": "15",     # duration
}
ONDA_GRANDE = {
    "description_value_01": "20.32",  # Sustained Damage % (squad)
    "description_value_02": "10",     # duration
    "description_value_03": "32.23",  # Damage Taken % (enemy)
    "description_value_04": "10",     # duration
}


def make_context():
    return SquadContext([
        SquadMember("rosanna-chic-ocean", burst_tier=2, element="Wind"),
        SquadMember("ally", burst_tier=3, element="Fire"),
    ])


def build():
    return build_rosanna_rules({"ferita": FERITA, "onda_grande": ONDA_GRANDE})


ROSANNA = {"slug": "rosanna-chic-ocean", "element": "Wind"}
ALLY = {"slug": "ally", "element": "Fire"}


def test_ferita_grants_squad_damage_to_parts_at_battle_start():
    ctx = make_context()
    registry = EffectRegistry()
    fire_trigger("battle_start", {"rosanna-chic-ocean": build()}, ctx, registry, time=0.0)

    assert round(registry.total_for("damage_to_parts_up", ALLY, now=0.0), 4) == 0.2426
    assert registry.total_for("damage_to_parts_up", ALLY, now=15.1) == 0.0


def test_burst_grants_squad_sustained_damage_and_enemy_damage_taken():
    ctx = make_context()
    registry = EffectRegistry()
    fire_trigger("own_burst_activate", {"rosanna-chic-ocean": build()}, ctx, registry, time=5.0)

    assert round(registry.total_for("sustained_damage_up", ALLY, now=5.0), 4) == 0.2032
    assert round(registry.total_for("damage_taken_up", ALLY, now=5.0), 4) == 0.3223
    assert registry.total_for("sustained_damage_up", ALLY, now=15.1) == 0.0
    assert registry.total_for("damage_taken_up", ALLY, now=15.1) == 0.0
