from app.effects import EffectRegistry
from app.skill_rules.anis_star import build_starfall_rules
from app.squad_engine import SquadContext, SquadMember, fire_trigger

# Real skill level 10 values pulled from api.dotgg.gg for anis-star's Starfall skill.
LEVEL_10_VALUES = {
    "description_value_01": "1",
    "description_value_02": "40.01",
    "description_value_03": "7.48",
    "description_value_04": "120.13",
    "description_value_05": "6",
}


def alone_context():
    return SquadContext(
        [
            SquadMember("anis-star", burst_tier=1, element="Electric"),
            SquadMember("crown", burst_tier=2, element="Iron"),
        ]
    )


def with_ally_context():
    return SquadContext(
        [
            SquadMember("anis-star", burst_tier=1, element="Electric"),
            SquadMember("other-burst1", burst_tier=1, element="Fire"),
        ]
    )


def test_gauge_fill_speed_applies_to_squad_at_battle_start():
    ctx = alone_context()
    registry = EffectRegistry()
    rules = {"anis-star": build_starfall_rules(LEVEL_10_VALUES)}

    fire_trigger("battle_start", rules, ctx, registry, time=0.0)

    crown = {"slug": "crown", "element": "Iron"}
    assert round(registry.total_for("burst_gauge_fill_speed_percent", crown, now=0.0), 4) == 0.06


def test_alone_branch_grants_my_own_star_atk_buff_and_sets_status():
    ctx = alone_context()
    registry = EffectRegistry()
    rules = {"anis-star": build_starfall_rules(LEVEL_10_VALUES)}

    fire_trigger("battle_start", rules, ctx, registry, time=0.0)

    anis = {"slug": "anis-star", "element": "Electric"}
    assert round(registry.total_for("atk_percent", anis, now=0.0), 4) == 0.4001
    assert ctx.has_status("anis-star", "My Own Star") is True
    assert ctx.has_status("anis-star", "Everyone's Star") is False


def test_alone_branch_emits_burst_cooldown_reduction_pulse():
    ctx = alone_context()
    registry = EffectRegistry()
    rules = {"anis-star": build_starfall_rules(LEVEL_10_VALUES)}

    fire_trigger("battle_start", rules, ctx, registry, time=0.0)

    pulses = registry.drain_pulses("burst_cooldown_reduction_sec")
    assert len(pulses) == 1
    assert pulses[0].value == 7.48
    assert pulses[0].scope == "squad"


def test_atk_buff_is_not_reapplied_on_repeated_full_burst_end_but_pulse_recurs():
    ctx = alone_context()
    registry = EffectRegistry()
    rules = {"anis-star": build_starfall_rules(LEVEL_10_VALUES)}

    fire_trigger("battle_start", rules, ctx, registry, time=0.0)
    fire_trigger("full_burst_end", rules, ctx, registry, time=15.0)
    fire_trigger("full_burst_end", rules, ctx, registry, time=30.0)

    anis = {"slug": "anis-star", "element": "Electric"}
    # still exactly one atk_percent worth of buff, not stacked 3x
    assert round(registry.total_for("atk_percent", anis, now=30.0), 4) == 0.4001

    # but the cooldown-reduction pulse fires every time (drain across all three firings)
    pulses = registry.drain_pulses("burst_cooldown_reduction_sec")
    assert len(pulses) == 3


def test_with_ally_branch_sets_everyones_star_and_clears_my_own_star():
    ctx = with_ally_context()
    registry = EffectRegistry()
    rules = {"anis-star": build_starfall_rules(LEVEL_10_VALUES)}

    fire_trigger("battle_start", rules, ctx, registry, time=0.0)

    assert ctx.has_status("anis-star", "Everyone's Star") is True
    assert ctx.has_status("anis-star", "My Own Star") is False

    anis = {"slug": "anis-star", "element": "Electric"}
    assert registry.total_for("atk_percent", anis, now=0.0) == 0.0
