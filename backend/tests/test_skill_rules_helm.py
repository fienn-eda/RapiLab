from app.effects import EffectRegistry
from app.skill_rules.helm import build_fire_away_rules, build_frontline_command_rules
from app.squad_engine import SquadContext, SquadMember, fire_trigger

# Real skill level 10 values from api.dotgg.gg for helm's skills[0] "Frontline
# Command" and skills[1] "Fire Away".
FRONTLINE_COMMAND_VALUES = {
    "description_value_01": "14.64",
    "description_value_02": "5",
}

FIRE_AWAY_VALUES = {
    "description_value_01": "3.08",
    "description_value_02": "11.85",
    "description_value_03": "10",
}


def make_context():
    return SquadContext(
        [
            SquadMember("helm", burst_tier=3, element="Water"),
            SquadMember("ally", burst_tier=1, element="Iron"),
        ]
    )


def test_frontline_command_grants_squad_crit_rate_on_last_bullet_hit():
    ctx = make_context()
    registry = EffectRegistry()
    rules = {"helm": build_frontline_command_rules(FRONTLINE_COMMAND_VALUES)}

    fire_trigger("on_last_bullet_hit", rules, ctx, registry, time=3.0)

    ally = {"slug": "ally", "element": "Iron"}
    assert round(registry.total_for("crit_rate", ally, now=3.0), 4) == 0.1464
    assert registry.total_for("crit_rate", ally, now=8.1) == 0.0


def test_fire_away_grants_permanent_squad_damage_to_parts():
    ctx = make_context()
    registry = EffectRegistry()
    rules = {"helm": build_fire_away_rules(FIRE_AWAY_VALUES)}

    fire_trigger("battle_start", rules, ctx, registry, time=0.0)

    ally = {"slug": "ally", "element": "Iron"}
    assert round(registry.total_for("damage_to_parts_up", ally, now=99999), 4) == 0.0308


def test_fire_away_grants_squad_attack_damage_up_on_full_burst_enter():
    ctx = make_context()
    registry = EffectRegistry()
    rules = {"helm": build_fire_away_rules(FIRE_AWAY_VALUES)}

    fire_trigger("full_burst_enter", rules, ctx, registry, time=5.0)

    ally = {"slug": "ally", "element": "Iron"}
    assert round(registry.total_for("attack_damage_up", ally, now=5.0), 4) == 0.1185
    assert registry.total_for("attack_damage_up", ally, now=15.1) == 0.0
