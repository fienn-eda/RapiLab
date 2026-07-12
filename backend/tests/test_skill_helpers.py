from app.effects import EffectRegistry
from app.skill_rules._helpers import (
    buff_rule,
    cdr_pulse_rule,
    escalating_buff_rule,
    highest_atk_buff_rule,
    instant_nuke_pulse_rule,
    leveled_resource_buff,
    linear_resource_buff,
    round_buff_rule,
)
from app.squad_engine import SquadContext, SquadMember, fire_trigger


def ctx():
    return SquadContext([
        SquadMember("src", burst_tier=1, element="Iron"),
        SquadMember("ally", burst_tier=3, element="Fire"),
    ])


def ranked_ctx():
    return SquadContext(
        [
            SquadMember("miranda", burst_tier=1, element="Fire"),
            SquadMember("scarlet", burst_tier=3, element="Fire"),
            SquadMember("blast", burst_tier=1, element="Wind"),
        ],
        base_atk={"miranda": 50000, "scarlet": 80000, "blast": 70000},
    )


def test_buff_rule_adds_all_listed_effects_scoped_and_timed():
    rule = buff_rule("full_burst_enter", [
        ("atk_percent", 0.66, "squad", 5.0),
        ("crit_rate", 0.30, "self", 5.0),
    ])
    registry = EffectRegistry()
    fire_trigger("full_burst_enter", {"src": [rule]}, ctx(), registry, time=2.0)

    ally = {"slug": "ally", "element": "Fire"}
    src = {"slug": "src", "element": "Iron"}
    assert registry.total_for("atk_percent", ally, now=2.0) == 0.66  # squad
    assert registry.total_for("crit_rate", ally, now=2.0) == 0.0     # self-only
    assert registry.total_for("crit_rate", src, now=2.0) == 0.30
    assert registry.total_for("atk_percent", ally, now=7.1) == 0.0   # expired


def test_escalating_buff_rule_applies_tiers_cumulatively_by_activation():
    # "Once/Twice/Three times, previous effects trigger repeatedly": each tier
    # unlocks on its activation and is re-applied every activation after. Tier 1
    # here is empty (e.g. a non-DPS hit-rate step).
    rule = escalating_buff_rule("full_burst_end", [
        [],
        [("flat_atk", 100.0, "squad", 10.0)],
        [("reload_speed_percent", 0.4, "squad", 15.0)],
    ])
    registry = EffectRegistry()
    context = ctx()
    ally = {"slug": "ally", "element": "Fire"}

    fire_trigger("full_burst_end", {"src": [rule]}, context, registry, time=10.0)
    assert registry.total_for("flat_atk", ally, now=10.0) == 0.0  # cycle 1: nothing

    fire_trigger("full_burst_end", {"src": [rule]}, context, registry, time=30.0)
    assert registry.total_for("flat_atk", ally, now=30.0) == 100.0  # cycle 2 unlock
    assert registry.total_for("reload_speed_percent", ally, now=30.0) == 0.0

    fire_trigger("full_burst_end", {"src": [rule]}, context, registry, time=50.0)
    # cycle 3: reload unlocks; flat_atk re-applied fresh (its cycle-2 window expired)
    assert registry.total_for("flat_atk", ally, now=50.0) == 100.0
    assert registry.total_for("reload_speed_percent", ally, now=50.0) == 0.4


def test_escalating_buff_rule_refreshing_does_not_stack_overlapping_reapplications():
    # With refreshing=True, a tier re-applied while its prior window is still active
    # collapses to one value (not the sum) - for a duration longer than the
    # re-trigger interval, e.g. Isabel's 45s Marked Target vs her 40s burst cd.
    rule = escalating_buff_rule("own_burst_activate", [
        [("crit_rate", 0.0626, "self", 45.0)],
    ], refreshing=True)
    registry = EffectRegistry()
    context = ctx()
    src = {"slug": "src", "element": "Iron"}
    fire_trigger("own_burst_activate", {"src": [rule]}, context, registry, time=0.0)
    fire_trigger("own_burst_activate", {"src": [rule]}, context, registry, time=40.0)
    # both 45s windows overlap at t=40; refresh -> single value, not 0.1252
    assert round(registry.total_for("crit_rate", src, now=40.0), 4) == 0.0626


def test_instant_nuke_pulse_rule_emits_a_drainable_instant_damage_pulse():
    rule = instant_nuke_pulse_rule("full_burst_enter", 636.0)
    registry = EffectRegistry()
    fire_trigger("full_burst_enter", {"src": [rule]}, ctx(), registry, time=5.0)

    pulses = registry.drain_pulses("instant_damage_percent")
    assert len(pulses) == 1
    assert pulses[0].value == 636.0
    assert pulses[0].scope == "self"
    assert pulses[0].source_slug == "src"


def test_highest_atk_buff_rule_scopes_timed_buffs_to_top_n_allies():
    # Miranda's Powering Up: ATK/Crit Damage on the top-2 highest-final-ATK allies
    # (except caster). Applied to exactly scarlet + blast, not miranda herself.
    rule = highest_atk_buff_rule("own_burst_activate", 2, [
        ("atk_percent", 0.404, 10.0),
        ("other_critical_damage_sources", 0.5623, 10.0),
    ])
    registry = EffectRegistry()
    fire_trigger("own_burst_activate", {"miranda": [rule]}, ranked_ctx(), registry, time=2.0)

    scarlet = {"slug": "scarlet", "element": "Fire"}
    blast = {"slug": "blast", "element": "Wind"}
    miranda = {"slug": "miranda", "element": "Fire"}
    assert registry.total_for("atk_percent", scarlet, now=2.0) == 0.404
    assert registry.total_for("atk_percent", blast, now=2.0) == 0.404
    assert registry.total_for("atk_percent", miranda, now=2.0) == 0.0   # caster excluded
    assert registry.total_for("other_critical_damage_sources", scarlet, now=2.0) == 0.5623
    assert registry.total_for("atk_percent", scarlet, now=12.1) == 0.0  # 10s expired


def test_round_buff_rule_records_a_squad_scoped_round_grant():
    rule = round_buff_rule("full_burst_enter", [("pierce_damage_up", 0.2013, "squad")], shots=1)
    registry = EffectRegistry()
    fire_trigger("full_burst_enter", {"zwei": [rule]}, ctx(), registry, time=12.0)

    grants = registry.round_grants()
    assert len(grants) == 1
    g = grants[0]
    assert (g.stat, g.value, g.scope, g.source_slug, g.shots, g.granted_at) == (
        "pierce_damage_up", 0.2013, "squad", "zwei", 1, 12.0,
    )


def test_round_buff_rule_resolves_top_atk_scope_to_slugs():
    # Miranda's Wake Up: Crit Rate on the top-1 highest-final-ATK ally, for 1 round.
    rule = round_buff_rule("full_burst_enter", [("crit_rate", 0.8542, ("top_atk", 1))], shots=1)
    registry = EffectRegistry()
    fire_trigger("full_burst_enter", {"miranda": [rule]}, ranked_ctx(), registry, time=12.0)

    grants = registry.round_grants()
    assert len(grants) == 1
    assert grants[0].scope == "slugs:scarlet"  # highest-final-ATK ally
    assert grants[0].stat == "crit_rate"
    assert grants[0].value == 0.8542


def test_cdr_pulse_rule_emits_a_drainable_pulse():
    rule = cdr_pulse_rule("full_burst_enter", 3.17)
    registry = EffectRegistry()
    fire_trigger("full_burst_enter", {"src": [rule]}, ctx(), registry, time=0.0)

    pulses = registry.drain_pulses("burst_cooldown_reduction_sec")
    assert len(pulses) == 1
    assert pulses[0].value == 3.17
    assert pulses[0].scope == "squad"


def test_linear_resource_buff_scales_value_by_stack_count():
    buff = linear_resource_buff("atk_percent", per_stack=0.0181, scope="self", lifetime=10.0)
    assert buff.stat == "atk_percent"
    assert buff.scope == "self"
    assert buff.lifetime == 10.0
    assert buff.value_fn(0) == 0.0
    assert round(buff.value_fn(3), 4) == round(0.0181 * 3, 4)


def test_leveled_resource_buff_scales_value_by_derived_level():
    # level = count // 10 (Guillotine's Hero Level rises every 10 EXP); value is
    # per_level * level, so it steps only when the level increments.
    buff = leveled_resource_buff(
        "attack_damage_up", per_level=0.0116, level_fn=lambda c: c // 10, scope="element:Water"
    )
    assert buff.scope == "element:Water"
    assert buff.lifetime is None
    assert buff.value_fn(9) == 0.0        # level 0
    assert round(buff.value_fn(25), 4) == round(0.0116 * 2, 4)  # level 2
