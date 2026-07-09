from app.effects import Effect, EffectRegistry
from app.squad_engine import (
    SkillRule,
    SquadContext,
    SquadMember,
    deck_contains,
    fire_trigger,
    has_status,
    no_other_burst_tier_allies,
    not_condition,
    own_burst_fired_this_cycle,
)


def make_context(*members):
    return SquadContext(list(members))


def test_no_other_burst_tier_allies_true_when_alone_in_tier():
    ctx = make_context(
        SquadMember("anis-star", burst_tier=1, element="Electric"),
        SquadMember("crown", burst_tier=2, element="Iron"),
    )
    condition = no_other_burst_tier_allies(1)
    assert condition(ctx, "anis-star") is True


def test_no_other_burst_tier_allies_false_when_another_present():
    ctx = make_context(
        SquadMember("anis-star", burst_tier=1, element="Electric"),
        SquadMember("some-other-burst1", burst_tier=1, element="Fire"),
    )
    condition = no_other_burst_tier_allies(1)
    assert condition(ctx, "anis-star") is False


def test_status_flags_set_clear_and_query():
    ctx = make_context(SquadMember("anis-star", burst_tier=1, element="Electric"))
    assert ctx.has_status("anis-star", "My Own Star") is False

    ctx.set_status("anis-star", "My Own Star")
    assert ctx.has_status("anis-star", "My Own Star") is True

    ctx.clear_status("anis-star", "My Own Star")
    assert ctx.has_status("anis-star", "My Own Star") is False


def test_has_status_condition_and_not_condition():
    ctx = make_context(SquadMember("anis-star", burst_tier=1, element="Electric"))
    ctx.set_status("anis-star", "My Own Star")

    assert has_status("My Own Star")(ctx, "anis-star") is True
    assert not_condition(has_status("My Own Star"))(ctx, "anis-star") is False


def test_fire_trigger_runs_matching_rule_and_applies_effect():
    ctx = make_context(SquadMember("anis-star", burst_tier=1, element="Electric"))
    registry = EffectRegistry()

    def action(context, caster_slug, time, registry):
        registry.add(
            Effect(stat="atk_percent", value=0.4, scope="self", duration=None, source_slug=caster_slug),
            applied_at=time,
        )

    rules_by_slug = {"anis-star": [SkillRule(trigger="battle_start", action=action)]}
    fire_trigger("battle_start", rules_by_slug, ctx, registry, time=0.0)

    anis = {"slug": "anis-star", "element": "Electric"}
    assert registry.total_for("atk_percent", anis, now=0.0) == 0.4


def test_fire_trigger_skips_rule_when_condition_is_false():
    ctx = make_context(
        SquadMember("anis-star", burst_tier=1, element="Electric"),
        SquadMember("other-burst1", burst_tier=1, element="Fire"),
    )
    registry = EffectRegistry()
    applied = []

    def action(context, caster_slug, time, registry):
        applied.append(caster_slug)

    rules_by_slug = {
        "anis-star": [
            SkillRule(
                trigger="battle_start",
                condition=no_other_burst_tier_allies(1),
                action=action,
            )
        ]
    }
    fire_trigger("battle_start", rules_by_slug, ctx, registry, time=0.0)

    assert applied == []


def test_fire_trigger_only_matches_requested_trigger_type():
    ctx = make_context(SquadMember("anis-star", burst_tier=1, element="Electric"))
    registry = EffectRegistry()
    applied = []

    def action(context, caster_slug, time, registry):
        applied.append(caster_slug)

    rules_by_slug = {
        "anis-star": [SkillRule(trigger="full_burst_enter", action=action)]
    }
    fire_trigger("battle_start", rules_by_slug, ctx, registry, time=0.0)

    assert applied == []


def test_activation_count_tracks_firings_per_slug_and_trigger():
    ctx = make_context(SquadMember("anchor", burst_tier=2, element="Water"))
    registry = EffectRegistry()
    seen = []

    def record(context, caster_slug, time, registry):
        seen.append(context.activation_count(caster_slug, "full_burst_end"))

    rules = {"anchor": [SkillRule(trigger="full_burst_end", action=record)]}
    for t in (10.0, 25.0, 40.0):
        fire_trigger("full_burst_end", rules, ctx, registry, time=t)

    # each firing sees a 1-based count of how many times this trigger has fired
    # for this Nikke - i.e. the burst-cycle number for a per-cycle trigger.
    assert seen == [1, 2, 3]


def test_activation_count_zero_before_firing_and_separate_per_trigger():
    ctx = make_context(SquadMember("anchor", burst_tier=2, element="Water"))
    assert ctx.activation_count("anchor", "full_burst_end") == 0

    registry = EffectRegistry()
    rules = {"anchor": [SkillRule(trigger="full_burst_end", action=lambda c, s, t, r: None)]}
    fire_trigger("full_burst_end", rules, ctx, registry, time=1.0)

    assert ctx.activation_count("anchor", "full_burst_end") == 1
    assert ctx.activation_count("anchor", "own_burst_activate") == 0


def test_own_burst_fired_this_cycle_reads_burst_used_this_cycle():
    ctx = make_context(SquadMember("arcana", burst_tier=2, element="Electric"))
    condition = own_burst_fired_this_cycle()
    assert condition(ctx, "arcana") is False

    ctx.burst_used_this_cycle.add("arcana")
    assert condition(ctx, "arcana") is True


def test_deck_contains_checks_squad_membership():
    ctx = make_context(
        SquadMember("mast", burst_tier=2, element="Water"),
        SquadMember("anchor", burst_tier=2, element="Water"),
    )
    assert deck_contains("anchor")(ctx, "mast") is True
    assert deck_contains("liter")(ctx, "mast") is False


def test_branching_rules_pick_the_matching_branch_by_condition():
    # Models Anis: Star's Starfall: two mutually-exclusive branches keyed off
    # whether another Burst 1 ally is present.
    ctx_alone = make_context(SquadMember("anis-star", burst_tier=1, element="Electric"))
    ctx_with_ally = make_context(
        SquadMember("anis-star", burst_tier=1, element="Electric"),
        SquadMember("other-burst1", burst_tier=1, element="Fire"),
    )
    registry = EffectRegistry()
    fired_branches = []

    def alone_branch(context, caster_slug, time, registry):
        fired_branches.append("alone")

    def with_ally_branch(context, caster_slug, time, registry):
        fired_branches.append("with_ally")

    rules_by_slug = {
        "anis-star": [
            SkillRule(
                trigger="battle_start",
                condition=no_other_burst_tier_allies(1),
                action=alone_branch,
            ),
            SkillRule(
                trigger="battle_start",
                condition=not_condition(no_other_burst_tier_allies(1)),
                action=with_ally_branch,
            ),
        ]
    }

    fire_trigger("battle_start", rules_by_slug, ctx_alone, registry, time=0.0)
    fire_trigger("battle_start", rules_by_slug, ctx_with_ally, registry, time=0.0)

    assert fired_branches == ["alone", "with_ally"]
