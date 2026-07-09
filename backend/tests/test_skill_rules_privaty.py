from app.effects import EffectRegistry
from app.skill_rules.privaty import (
    ak_missile_burst_percent,
    build_ak_missile_rules,
    build_ex_magazine_rules,
)
from app.squad_engine import SquadContext, SquadMember, fire_trigger

# Privaty has her signature weapon ("dollskills") completed, so these are the
# dollskills level-10 values, not the base skills - Fienn confirmed the
# cherished-weapon version applies. It adds a 4th effect to EX Magazine
# (Attack Damage up) that the base skill doesn't have at all, and roughly
# triples AK Missile's burst damage percent (457.87% base -> 1407.64%).
EX_MAGAZINE_VALUES = {
    "description_value_01": "23.61",
    "description_value_02": "10",
    "description_value_03": "51.16",
    "description_value_04": "10",
    "description_value_05": "50.66",
    "description_value_06": "10",
    "description_value_07": "20.16",
    "description_value_08": "10",
}

AK_MISSILE_VALUES = {
    "description_value_01": "1407.64",
    "description_value_02": "3",
    "description_value_03": "5.02",
    "description_value_04": "10",
    "description_value_05": "130",
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


def test_ex_magazine_grants_squad_attack_damage_up():
    ctx = make_context()
    registry = EffectRegistry()
    rules = {"privaty": build_ex_magazine_rules(EX_MAGAZINE_VALUES)}

    fire_trigger("full_burst_enter", rules, ctx, registry, time=5.0)

    ally = {"slug": "ally", "element": "Iron"}
    assert round(registry.total_for("attack_damage_up", ally, now=5.0), 4) == 0.2016
    assert registry.total_for("attack_damage_up", ally, now=15.1) == 0.0


def test_ak_missile_grants_self_elemental_bonus_on_own_burst():
    ctx = make_context()
    registry = EffectRegistry()
    rules = {"privaty": build_ak_missile_rules(AK_MISSILE_VALUES)}

    fire_trigger("own_burst_activate", rules, ctx, registry, time=5.0)

    privaty = {"slug": "privaty", "element": "Water"}
    assert round(registry.total_for("other_elemental_bonus", privaty, now=5.0), 4) == 1.30
    assert registry.total_for("other_elemental_bonus", privaty, now=15.1) == 0.0

    ally = {"slug": "ally", "element": "Iron"}
    assert registry.total_for("other_elemental_bonus", ally, now=5.0) == 0.0


def test_ak_missile_burst_percent_reads_the_damage_slot():
    assert ak_missile_burst_percent(AK_MISSILE_VALUES) == 1407.64
