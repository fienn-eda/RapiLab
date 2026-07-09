from app.effects import EffectRegistry
from app.skill_rules.crown import build_last_kingdom_rules, build_one_for_all_rules
from app.squad_engine import SquadContext, SquadMember, fire_trigger

# Real skill level 10 values from api.dotgg.gg for crown's skills[0] "One for All"
# and skills[2] "Last Kingdom".
ONE_FOR_ALL_VALUES = {
    "description_value_01": "64.51",
    "description_value_02": "15",
    "description_value_03": "44.35",
    "description_value_04": "15",
    "description_value_05": "37.44",
    "description_value_06": "15",
    "description_value_07": "44.35",
    "description_value_08": "15",
}

LAST_KINGDOM_VALUES = {
    "description_value_01": "36.24",
    "description_value_02": "15",
    "description_value_03": "10.45",
    "description_value_04": "15",
}


def make_context():
    return SquadContext(
        [
            SquadMember("crown", burst_tier=2, element="Iron"),
            SquadMember("b3-a", burst_tier=3, element="Fire"),
            SquadMember("b3-b", burst_tier=3, element="Water"),
        ]
    )


def test_one_for_all_grants_flat_atk_and_reload_to_members_who_already_burst():
    ctx = make_context()
    ctx.burst_used_this_cycle = {"crown", "b3-a"}
    registry = EffectRegistry()
    rules = {"crown": build_one_for_all_rules(ONE_FOR_ALL_VALUES, caster_atk=10000, caster_def=2000)}

    fire_trigger("full_burst_enter", rules, ctx, registry, time=5.0)

    crown_target = {"slug": "crown", "element": "Iron"}
    b3a_target = {"slug": "b3-a", "element": "Fire"}
    assert registry.total_for("flat_atk", crown_target, now=5.0) == 6451.0
    assert round(registry.total_for("reload_speed_percent", crown_target, now=5.0), 4) == 0.4435


def test_one_for_all_grants_flat_def_and_reload_to_members_who_have_not_burst_yet():
    ctx = make_context()
    ctx.burst_used_this_cycle = {"crown", "b3-a"}
    registry = EffectRegistry()
    rules = {"crown": build_one_for_all_rules(ONE_FOR_ALL_VALUES, caster_atk=10000, caster_def=2000)}

    fire_trigger("full_burst_enter", rules, ctx, registry, time=5.0)

    b3b_target = {"slug": "b3-b", "element": "Water"}
    assert registry.total_for("flat_def", b3b_target, now=5.0) == 748.8
    assert round(registry.total_for("reload_speed_percent", b3b_target, now=5.0), 4) == 0.4435
    # b3-b hasn't burst, so it should NOT get the flat_atk bonus
    assert registry.total_for("flat_atk", b3b_target, now=5.0) == 0.0


def test_one_for_all_buffs_expire_after_their_duration():
    ctx = make_context()
    ctx.burst_used_this_cycle = {"crown"}
    registry = EffectRegistry()
    rules = {"crown": build_one_for_all_rules(ONE_FOR_ALL_VALUES, caster_atk=10000, caster_def=2000)}

    fire_trigger("full_burst_enter", rules, ctx, registry, time=5.0)

    crown_target = {"slug": "crown", "element": "Iron"}
    assert registry.total_for("flat_atk", crown_target, now=19.9) == 6451.0
    assert registry.total_for("flat_atk", crown_target, now=20.1) == 0.0


def test_last_kingdom_applies_squad_wide_attack_damage_up_on_own_burst():
    ctx = make_context()
    registry = EffectRegistry()
    rules = {"crown": build_last_kingdom_rules(LAST_KINGDOM_VALUES, caster_max_hp=50000)}

    fire_trigger("own_burst_activate", rules, ctx, registry, time=5.0)

    ally = {"slug": "b3-a", "element": "Fire"}
    assert round(registry.total_for("attack_damage_up", ally, now=5.0), 4) == 0.3624
    assert round(registry.total_for("shield_amount", ally, now=5.0), 2) == 5225.0
