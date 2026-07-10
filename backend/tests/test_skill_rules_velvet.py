from app.effects import EffectRegistry
from app.skill_rules.velvet import build_velvet_rules
from app.squad_engine import SquadContext, SquadMember, fire_trigger

# Real skill level 10 values from lootandwaifus.com (Velvet).
PERFECT_EXECUTION = {
    "description_value_01": "7",      # deferred: weapon-transform damage %
    "description_value_02": "10",     # deferred: its duration
    "description_value_03": "34.52",  # self Attack Damage %
    "description_value_04": "10",     # duration
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
