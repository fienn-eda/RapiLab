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
    """Regression test on the value: fires the real rule through a real
    registry - the same way test_skill_rules_burst3_eb1 exercises Calm Depths
    - and compares the effect it granted against the shared function's
    answer. This does not by itself prove the builder calls the shared
    function rather than recomputing the same number - see the patch-based
    test below for that."""
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


def test_the_rule_reads_the_cut_through_the_shared_function():
    """The single source is the deliverable, so the builder must CALL the
    shared function rather than recompute the same number: patching it moves
    the rule."""
    from unittest.mock import patch

    from app.effects import EffectRegistry
    from app.skill_rules import liberalio
    from app.squad_engine import SquadContext, SquadMember, fire_trigger

    values = {"calm_depths": {"description_value_07": "12.74",
                              "description_value_08": "10"}}
    weapon = {"charge_time": 1.5}
    with patch.object(liberalio, "calm_depths_charge_cut_seconds", return_value=0.5):
        rules = {"liberalio": liberalio.build_calm_depths_charge_rules(values, weapon)}
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
    assert granted == 0.5


import pytest

from app.charge_window_inputs import (CALCULATOR_SLUGS, LIBERALIO_SLUG, Overrides,
                                      build_inputs)
from app.models import OverloadOption, SkillLevels, UserNikkeState

MAXED = SkillLevels(skill1=10, skill2=10, burst=10)


def a_state(slug, overloads=()):
    return UserNikkeState(
        character_slug=slug, level=200, hp=1_000_000, atk=100_000, def_=10_000,
        skill_levels=MAXED,
        overload_options=[OverloadOption(name=n, value=v) for n, v in overloads],
    )


def test_the_three_units_the_calculator_covers():
    assert CALCULATOR_SLUGS == ("scarlet-black-shadow", "liberalio", "neon-vision-eye")
    assert LIBERALIO_SLUG == "liberalio"


def test_scarlet_carries_her_measured_charge_and_delay():
    got = build_inputs(a_state("scarlet-black-shadow"), with_liberalio=False,
                       overrides=Overrides(None, None, None))
    assert got.charge_time == pytest.approx(0.30)
    assert got.motion_delay == pytest.approx(0.43)


def test_asuras_magazine_grant_is_folded_into_max_ammo():
    # Base 9 rounds, Asura +60%, no overload: round(9 * 1.60) = 14.
    got = build_inputs(a_state("scarlet-black-shadow"), with_liberalio=False,
                       overrides=Overrides(None, None, None))
    assert got.max_ammo == 14


def test_an_overload_max_ammo_line_stacks_on_top_of_asura():
    # round(9 * (1 + 0.6 + 0.8537)) = 22.
    state = a_state("scarlet-black-shadow", [("최대 장탄 수 증가", 85.37)])
    got = build_inputs(state, with_liberalio=False, overrides=Overrides(None, None, None))
    assert got.max_ammo == 22


def test_the_charge_speed_overload_line_reaches_the_inputs():
    state = a_state("scarlet-black-shadow", [("차지 속도 증가", 2.86)])
    got = build_inputs(state, with_liberalio=False, overrides=Overrides(None, None, None))
    assert got.charge_speed_percent == pytest.approx(0.0286)


def test_the_roster_path_aggregates_through_the_shared_function():
    """The single aggregation rule is the deliverable, so the roster path must
    CALL `aggregate_charge_speed` rather than sum the options itself: patching
    it moves the roster's answer too, not only a typed override's."""
    from unittest.mock import patch

    from app import charge_window_inputs

    state = a_state("scarlet-black-shadow", [("차지 속도 증가", 2.86)])
    with patch.object(charge_window_inputs, "aggregate_charge_speed",
                      return_value=0.5) as aggregate:
        got = build_inputs(state, with_liberalio=False,
                           overrides=Overrides(None, None, None))
    assert got.charge_speed_percent == 0.5
    assert aggregate.call_args.args[0] == [2.86]


def test_the_assumed_cube_supplies_reload_speed():
    got = build_inputs(a_state("scarlet-black-shadow"), with_liberalio=False,
                       overrides=Overrides(None, None, None))
    assert got.reload_speed_percent == pytest.approx(0.2969, abs=1e-4)


def test_liberalio_hands_over_her_absolute_seconds():
    got = build_inputs(a_state("scarlet-black-shadow"), with_liberalio=True,
                       overrides=Overrides(None, None, None),
                       liberalio_state=a_state(LIBERALIO_SLUG))
    assert got.charge_time_reduction_sec == pytest.approx(0.1274 * 1.5, abs=1e-4)


def test_without_the_companion_there_is_no_cut():
    got = build_inputs(a_state("scarlet-black-shadow"), with_liberalio=False,
                       overrides=Overrides(None, None, None))
    assert got.charge_time_reduction_sec == 0.0


def test_an_absent_liberalio_grants_nothing_rather_than_borrowing_the_subject():
    # Her grant is built from her own skill levels and collectible. With no
    # Liberalio in the roster there is nothing to build it from, and reading the
    # subject's investment instead would answer a question nobody asked.
    got = build_inputs(a_state("scarlet-black-shadow"), with_liberalio=True,
                       overrides=Overrides(None, None, None), liberalio_state=None)
    assert got.charge_time_reduction_sec == 0.0


def test_liberalio_refuses_the_cut_even_when_asked():
    # Strange Currents makes her immune to external charge-speed effects, so the
    # companion toggle cannot apply to her own row.
    got = build_inputs(a_state(LIBERALIO_SLUG), with_liberalio=True,
                       overrides=Overrides(None, None, None),
                       liberalio_state=a_state(LIBERALIO_SLUG))
    assert got.charge_time_reduction_sec == 0.0


def test_overrides_replace_the_roster_values():
    state = a_state("scarlet-black-shadow", [("차지 속도 증가", 2.86)])
    got = build_inputs(state, with_liberalio=False,
                       overrides=Overrides(charge_speed_lines=[6.09, 6.09],
                                           max_ammo_percent=0.8537,
                                           reload_speed_percent=0.0))
    assert got.charge_speed_percent == pytest.approx(0.1218)
    assert got.max_ammo == 22
    assert got.reload_speed_percent == 0.0


def test_an_unknown_slug_is_refused():
    with pytest.raises(ValueError, match="charge-window calculator"):
        build_inputs(a_state("liter"), with_liberalio=False,
                     overrides=Overrides(None, None, None))
