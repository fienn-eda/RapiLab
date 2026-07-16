from app.effects import EffectRegistry
from app.skill_rules.rapi_red_hood import (
    build_battlefield_assessment_rules,
    power_of_inheritance_stage3_burst_percent,
)
from app.squad_engine import SquadContext, SquadMember, fire_trigger

# Real skill level 10 values from api.dotgg.gg for rapi-red-hood's skills[0]
# "Battlefield Assessment".
VALUES = {
    "description_value_01": "1",
    "description_value_02": "7.48",
    "description_value_03": "95.04",
    "description_value_04": "10",
    "description_value_05": "48",
    "description_value_06": "10",
    "description_value_07": "8.02",
    "description_value_08": "10",
}


def context_with_burst1_ally():
    return SquadContext(
        [
            SquadMember("rapi-red-hood", burst_tier=3, element="Fire"),
            SquadMember("anis-star", burst_tier=1, element="Electric"),
        ]
    )


def context_without_burst1_ally():
    return SquadContext(
        [
            SquadMember("rapi-red-hood", burst_tier=3, element="Fire"),
            SquadMember("someone-else", burst_tier=2, element="Iron"),
        ]
    )


def test_cancels_combat_assist_when_a_burst1_ally_is_present():
    ctx = context_with_burst1_ally()
    registry = EffectRegistry()
    rules = {"rapi-red-hood": build_battlefield_assessment_rules(VALUES)}

    fire_trigger("battle_start", rules, ctx, registry, time=0.0)

    assert ctx.has_status("rapi-red-hood", "Combat Assist") is False


def test_enters_combat_assist_when_no_burst1_ally_present():
    ctx = context_without_burst1_ally()
    registry = EffectRegistry()
    rules = {"rapi-red-hood": build_battlefield_assessment_rules(VALUES)}

    fire_trigger("battle_start", rules, ctx, registry, time=0.0)

    assert ctx.has_status("rapi-red-hood", "Combat Assist") is True


def test_self_buff_branch_fires_on_full_burst_enter_when_not_in_combat_assist():
    ctx = context_with_burst1_ally()
    registry = EffectRegistry()
    rules = {"rapi-red-hood": build_battlefield_assessment_rules(VALUES)}

    fire_trigger("battle_start", rules, ctx, registry, time=0.0)
    fire_trigger("full_burst_enter", rules, ctx, registry, time=5.0)

    rapi = {"slug": "rapi-red-hood", "element": "Fire"}
    assert round(registry.total_for("atk_percent", rapi, now=5.0), 4) == 0.9504
    assert round(registry.total_for("damage_to_parts_up", rapi, now=5.0), 4) == 0.48
    # this branch should NOT emit a squad-wide burst cooldown reduction
    assert registry.drain_pulses("burst_cooldown_reduction_sec") == []


def test_combat_assist_branch_fires_on_full_burst_enter_when_no_burst1_ally():
    ctx = context_without_burst1_ally()
    registry = EffectRegistry()
    rules = {"rapi-red-hood": build_battlefield_assessment_rules(VALUES)}

    fire_trigger("battle_start", rules, ctx, registry, time=0.0)
    fire_trigger("full_burst_enter", rules, ctx, registry, time=5.0)

    ally = {"slug": "someone-else", "element": "Iron"}
    assert round(registry.total_for("attack_damage_up", ally, now=5.0), 4) == 0.0802
    pulses = registry.drain_pulses("burst_cooldown_reduction_sec")
    assert len(pulses) == 1
    assert pulses[0].value == 7.48

    # and the self-buff branch should NOT have fired
    rapi = {"slug": "rapi-red-hood", "element": "Fire"}
    assert registry.total_for("atk_percent", rapi, now=5.0) == 0.0


# rapi-red-hood has no signature weapon (no dollskills entry), so this is the
# base skill's level-10 value for the Stage 3 nuke. Module-level so the assembly
# verification harness (test_skill_value_assembly.py) can resolve it by name.
POWER_OF_INHERITANCE = {"description_value_05": "2808"}


def test_power_of_inheritance_stage3_burst_percent_reads_the_damage_slot():
    assert power_of_inheritance_stage3_burst_percent(POWER_OF_INHERITANCE) == 2808.0
