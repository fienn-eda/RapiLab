from app.effects import EffectRegistry
from app.skill_rules.prika import build_prika_rules
from app.squad_engine import SquadContext, SquadMember, fire_trigger

# Real skill level 10 values from lootandwaifus.com (Prika is not on dotgg).
GET_READY_FOR_AN_AMAZING_SHOW = {
    "description_value_01": "3.04",   # self HP recovery %/sec (not modeled)
    "description_value_02": "25",     # duration
    "description_value_03": "25",     # squad Charge Damage %
    "description_value_04": "25",     # duration
}


def make_context():
    return SquadContext([
        SquadMember("prika", burst_tier=2, element="Water"),
        SquadMember("ally", burst_tier=3, element="Fire"),
    ])


def build():
    return build_prika_rules({"get_ready_for_an_amazing_show": GET_READY_FOR_AN_AMAZING_SHOW})


ALLY = {"slug": "ally", "element": "Fire"}


def test_burst_grants_squad_charge_damage():
    ctx = make_context()
    registry = EffectRegistry()
    fire_trigger("own_burst_activate", {"prika": build()}, ctx, registry, time=5.0)

    assert round(registry.total_for("charge_damage_bonus", ALLY, now=5.0), 4) == 0.25
    assert registry.total_for("charge_damage_bonus", ALLY, now=29.9) == 0.25
    assert registry.total_for("charge_damage_bonus", ALLY, now=30.1) == 0.0
