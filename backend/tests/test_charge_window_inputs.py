"""The two skill-text values the calculator needs, shared with the rule builders.

These live in the unit modules rather than in the calculator so there is exactly
one place each value is read. A copy in the calculator would drift silently the
day a skill level or a weapon stat changes.
"""
from app.skill_rules.liberalio import calm_depths_charge_cut_seconds
from app.skill_rules.scarlet_black_shadow import full_burst_max_ammo_percent


def test_asura_max_ammo_is_read_as_a_ratio():
    values = {"fleetly_fading_asura": {"description_value_01": "60",
                                       "description_value_02": "10",
                                       "description_value_03": "100"}}
    assert full_burst_max_ammo_percent(values) == 0.60


def test_calm_depths_cut_is_the_percent_times_the_casters_own_charge():
    # "Charge Speed +12.74% of the skill user's" on a 1.5 sec Sniper Rifle is
    # 0.1911 sec for the recipient - an absolute figure that does NOT scale with
    # whoever receives it.
    values = {"calm_depths": {"description_value_07": "12.74",
                              "description_value_08": "10"}}
    assert calm_depths_charge_cut_seconds(values, {"charge_time": 1.5}) == 0.1274 * 1.5


def test_the_rule_hands_out_exactly_what_the_shared_function_returns():
    """Pin that the builder did not keep its own copy of the arithmetic. Fires
    the real rule through a real registry - the same way
    test_skill_rules_burst3_eb1 exercises Calm Depths - and compares the effect
    it granted against the shared function's answer."""
    from app.effects import EffectRegistry
    from app.skill_rules.liberalio import build_calm_depths_charge_rules
    from app.squad_engine import SquadContext, SquadMember, fire_trigger

    values = {"calm_depths": {"description_value_07": "12.74",
                              "description_value_08": "10"}}
    weapon = {"charge_time": 1.5}
    rules = {"liberalio": build_calm_depths_charge_rules(values, weapon)}
    ctx = SquadContext(
        [
            SquadMember("liberalio", burst_tier=3, element="Wind"),
            SquadMember("scarlet-black-shadow", burst_tier=3, element="Wind"),
        ],
        base_atk={"liberalio": 400_000, "scarlet-black-shadow": 300_000},
    )
    registry = EffectRegistry()
    fire_trigger("full_burst_enter", rules, ctx, registry, time=5.0)

    granted = registry.total_for(
        "charge_time_reduction_sec",
        {"slug": "scarlet-black-shadow", "element": "Wind"}, now=5.0)
    assert granted == calm_depths_charge_cut_seconds(values, weapon)
