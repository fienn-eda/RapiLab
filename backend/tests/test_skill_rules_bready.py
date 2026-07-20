"""Real max-level figures from lootandwaifus for Bready (slugs
"bready-lingering" / "bready-recommended"), slots numbered left-to-right per
skill.
"""
import pytest

from app.effects import EffectRegistry
from app.skill_rules.bready import (
    build_aftertaste_scheduled_nukes,
    build_bready_lingering_rules,
    build_bready_recommended_rules,
    build_lingering_per_shot_rules,
    build_recommended_per_shot_rules,
)
from app.squad_engine import SquadContext, SquadMember, fire_trigger

LONELY_GOURMET = {
    "description_value_01": "70.01",  # Full Burst self ATK %
    "description_value_02": "10",     # its duration sec
    "description_value_03": "20",     # Lingering Taste Charge Speed penalty %
    "description_value_04": "50",     # its duration sec
    "description_value_05": "20",     # Recommended Taste Charge Speed penalty %
    "description_value_06": "50",     # its duration sec
}
FAVORITE_CANDY = {
    "description_value_01": "3",       # Full Charges needed (Lingering)
    "description_value_02": "10.2",    # Damage Taken %
    "description_value_03": "5",       # its duration sec
    "description_value_04": "150.04",  # Aftertaste sustained damage %
    "description_value_05": "1",       # its tick interval sec
    "description_value_06": "5",       # its duration sec
    "description_value_07": "60.01",   # Recommended self Attack Damage %
    "description_value_08": "5",       # its duration sec
    "description_value_09": "265.07",  # Recommended distributed damage %
}
NEW_FLAVOR = {
    "description_value_01": "60.19",  # burst self Attack Damage %
    "description_value_02": "10",     # its duration sec
    "description_value_03": "349.8",  # Aftertaste Effect %  (Lingering)
    "description_value_04": "10",     # its duration sec
    "description_value_05": "70.09",  # burst self ATK %     (Recommended)
    "description_value_06": "10",     # its duration sec
}
BREADY_VALUES = {
    "lonely_gourmet": LONELY_GOURMET,
    "favorite_candy": FAVORITE_CANDY,
    "new_flavor": NEW_FLAVOR,
}
LINGERING = {"slug": "bready-lingering", "element": "Water"}
ALLY = {"slug": "ally", "element": "Iron"}


def make_context(slug="bready-lingering", shot_times=()):
    context = SquadContext(
        [SquadMember(slug, burst_tier=3, element="Water"),
         SquadMember("ally", burst_tier=1, element="Iron")],
        base_atk={slug: 60000.0, "ally": 0.0},
    )
    if shot_times:
        context.shot_times[slug] = list(shot_times)
    return context


def test_both_modes_share_the_full_burst_atk_buff_and_charge_speed_penalty():
    for build in (build_bready_lingering_rules, build_bready_recommended_rules):
        context = make_context()
        registry = EffectRegistry()
        rules = {"bready-lingering": build(BREADY_VALUES)}

        fire_trigger("battle_start", rules, context, registry, 0.0)
        fire_trigger("full_burst_enter", rules, context, registry, 5.0)

        assert registry.total_for("atk_percent", LINGERING, 10.0) == pytest.approx(0.7001)
        # Charge Speed is a real DPS stat now, and the Taste state slows her.
        assert registry.total_for("charge_speed_percent", LINGERING, 10.0) == -0.20


def test_lingering_burst_amplifies_aftertaste_via_self_sustained_damage():
    context = make_context()
    registry = EffectRegistry()
    rules = {"bready-lingering": build_bready_lingering_rules(BREADY_VALUES)}

    fire_trigger("own_burst_activate", rules, context, registry, 10.0)

    assert registry.total_for("attack_damage_up", LINGERING, 15.0) == 0.6019
    assert registry.total_for("sustained_damage_up", LINGERING, 15.0) == 3.498
    assert registry.total_for("sustained_damage_up", LINGERING, 20.1) == 0.0
    assert registry.total_for("sustained_damage_up", ALLY, 15.0) == 0.0  # self-scoped


def test_recommended_burst_gives_raw_atk_instead_of_the_aftertaste_amplifier():
    context = make_context()
    registry = EffectRegistry()
    rules = {"bready-lingering": build_bready_recommended_rules(BREADY_VALUES)}

    fire_trigger("own_burst_activate", rules, context, registry, 10.0)

    assert registry.total_for("attack_damage_up", LINGERING, 15.0) == 0.6019
    assert registry.total_for("atk_percent", LINGERING, 15.0) == pytest.approx(0.7009)
    assert registry.total_for("sustained_damage_up", LINGERING, 15.0) == 0.0


def test_lingering_marks_the_target_every_third_full_charge():
    shot_count, mode, rules = build_lingering_per_shot_rules(BREADY_VALUES)[0]
    assert (shot_count, mode) == (3, "every")
    context = make_context()
    registry = EffectRegistry()

    fire_trigger("per_shot", {"bready-lingering": rules}, context, registry, 4.0)

    assert registry.total_for("damage_taken_up", LINGERING, 8.9) == 0.102
    assert registry.total_for("damage_taken_up", LINGERING, 9.1) == 0.0


def test_recommended_fires_a_distributed_hit_on_every_full_charge():
    shot_count, mode, rules = build_recommended_per_shot_rules(BREADY_VALUES)[0]
    assert (shot_count, mode) == (1, "every")  # SR: every shot is a Full Charge
    context = make_context()
    registry = EffectRegistry()

    fire_trigger("per_shot", {"bready-lingering": rules}, context, registry, 4.0)

    assert registry.total_for("attack_damage_up", LINGERING, 8.9) == 0.6001
    pulses = registry.drain_pulses("instant_damage_percent")
    assert [(p.value, p.damage_type) for p in pulses] == [(265.07, "distributed")]


def test_aftertaste_ticks_every_second_and_a_replant_refreshes_rather_than_stacks():
    spec = build_aftertaste_scheduled_nukes(BREADY_VALUES)[0]
    assert spec["percent"] == 150.04
    assert spec["damage_type"] == "sustained"
    # Shots every 2s: every 3rd (t=6, 12) plants a 5s window. The windows
    # [6,11) and [12,17) do not overlap, so each ticks its own five times.
    context = make_context(shot_times=[2.0, 4.0, 6.0, 8.0, 10.0, 12.0])

    ticks = list(spec["schedule"](context, 30.0))

    assert ticks == [7.0, 8.0, 9.0, 10.0, 11.0, 13.0, 14.0, 15.0, 16.0, 17.0]


def test_aftertaste_overlapping_replants_do_not_double_tick():
    spec = build_aftertaste_scheduled_nukes(BREADY_VALUES)[0]
    # Plants at t=3 and t=6 - the second lands while the first is still
    # running, so the window extends to 11 instead of running two copies.
    context = make_context(shot_times=[1.0, 2.0, 3.0, 4.0, 5.0, 6.0])

    ticks = list(spec["schedule"](context, 30.0))

    assert ticks == [4.0, 5.0, 6.0, 7.0, 8.0, 9.0, 10.0, 11.0]
