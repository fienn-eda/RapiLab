from app.effects import EffectRegistry
from app.skill_rules.privaty import build_ex_magazine_rules
from app.squad_engine import SquadContext, SquadMember, fire_trigger

# Real skill level 10 values from api.dotgg.gg for privaty's skills[0]
# "EX Magazine".
EX_MAGAZINE_VALUES = {
    "description_value_01": "23.61",
    "description_value_02": "10",
    "description_value_03": "51.16",
    "description_value_04": "10",
    "description_value_05": "50.66",
    "description_value_06": "10",
}


def make_context():
    return SquadContext(
        [
            SquadMember("privaty", burst_tier=3, element="Water"),
            SquadMember("ally", burst_tier=1, element="Iron"),
        ]
    )


def test_ex_magazine_grants_squad_atk_and_reload_speed_on_full_burst_enter():
    ctx = make_context()
    registry = EffectRegistry()
    rules = {"privaty": build_ex_magazine_rules(EX_MAGAZINE_VALUES)}

    fire_trigger("full_burst_enter", rules, ctx, registry, time=5.0)

    ally = {"slug": "ally", "element": "Iron"}
    assert round(registry.total_for("atk_percent", ally, now=5.0), 4) == 0.2361
    assert round(registry.total_for("reload_speed_percent", ally, now=5.0), 4) == 0.5116
    assert registry.total_for("atk_percent", ally, now=15.1) == 0.0


def test_ex_magazine_reduces_max_ammo_capacity():
    ctx = make_context()
    registry = EffectRegistry()
    rules = {"privaty": build_ex_magazine_rules(EX_MAGAZINE_VALUES)}

    fire_trigger("full_burst_enter", rules, ctx, registry, time=5.0)

    ally = {"slug": "ally", "element": "Iron"}
    # value is a reduction, stored as a negative percent so consumers can just sum it
    assert round(registry.total_for("max_ammo_percent", ally, now=5.0), 4) == -0.5066
