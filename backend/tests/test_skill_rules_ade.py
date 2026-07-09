from app.effects import EffectRegistry
from app.skill_rules.ade_agent_bunny import build_ade_rules
from app.squad_engine import SquadContext, SquadMember, fire_trigger

# Real skill level 10 values from api.dotgg.gg.
AGENTS_GAZE = {
    "description_value_01": "15.2",   # squad ATK % of caster's ATK
    "description_value_02": "5",
    "description_value_03": "4.44",   # Spy Lens range (not modeled)
    "description_value_04": "10",
    "description_value_05": "5",
}
AGENTS_MOVEMENT = {
    "description_value_01": "18.36",  # squad Pierce Damage %
    "description_value_02": "5",
    "description_value_03": "16",     # self ATK % (Spy Lens fully stacked)
}
CUTTING_EDGE_EQUIPMENT = {
    "description_value_01": "55.56",  # self Minimum Effective Range (not modeled)
    "description_value_02": "10",
    "description_value_03": "55.04",  # squad Attack Damage %
    "description_value_04": "10",
    "description_value_05": "10.13",  # squad Pierce Damage %
    "description_value_06": "10",
}


def make_context():
    return SquadContext([
        SquadMember("ade-agent-bunny", burst_tier=2, element="Iron"),
        SquadMember("dealer", burst_tier=3, element="Fire"),
    ])


def build(caster_atk=10000):
    return build_ade_rules({
        "agents_gaze": AGENTS_GAZE,
        "agents_movement": AGENTS_MOVEMENT,
        "cutting_edge_equipment": CUTTING_EDGE_EQUIPMENT,
        "caster_atk": caster_atk,
    })


DEALER = {"slug": "dealer", "element": "Fire"}
ADE = {"slug": "ade-agent-bunny", "element": "Iron"}


def test_battle_start_grants_always_on_squad_atk_and_pierce():
    ctx = make_context()
    registry = EffectRegistry()
    fire_trigger("battle_start", {"ade-agent-bunny": build()}, ctx, registry, time=0.0)

    # squad ATK = 15.2% of caster ATK 10000 = 1520; squad pierce = 18.36%.
    assert registry.total_for("flat_atk", DEALER, now=0.0) == 1520.0
    assert round(registry.total_for("pierce_damage_up", DEALER, now=0.0), 4) == 0.1836
    # permanent (steady-state approximation) - still active late in the fight.
    assert registry.total_for("flat_atk", DEALER, now=175.0) == 1520.0


def test_self_atk_buff_is_self_scoped():
    ctx = make_context()
    registry = EffectRegistry()
    fire_trigger("battle_start", {"ade-agent-bunny": build()}, ctx, registry, time=0.0)

    # self ATK (Spy Lens fully stacked) applies to Ade only, not the squad.
    assert registry.total_for("atk_percent", ADE, now=0.0) == 0.16
    assert registry.total_for("atk_percent", DEALER, now=0.0) == 0.0


def test_burst_grants_squad_attack_damage_and_pierce():
    ctx = make_context()
    registry = EffectRegistry()
    fire_trigger("own_burst_activate", {"ade-agent-bunny": build()}, ctx, registry, time=5.0)

    assert round(registry.total_for("attack_damage_up", DEALER, now=5.0), 4) == 0.5504
    assert round(registry.total_for("pierce_damage_up", DEALER, now=5.0), 4) == 0.1013
    # 10s duration
    assert registry.total_for("attack_damage_up", DEALER, now=15.1) == 0.0
