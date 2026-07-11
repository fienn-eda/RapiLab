from app.effects import Effect, EffectRegistry
from app.squad_engine import (
    SkillRule,
    SquadContext,
    SquadMember,
    all_conditions,
    ally_bursted,
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


def test_record_burst_time_accumulates_per_slug():
    ctx = make_context(
        SquadMember("mint", burst_tier=2, element="Iron"),
        SquadMember("prika", burst_tier=2, element="Water"),
    )
    assert ctx.burst_times["mint"] == []
    ctx.record_burst_time("mint", 5.0)
    ctx.record_burst_time("mint", 25.0)
    ctx.record_burst_time("prika", 5.0)
    assert ctx.burst_times["mint"] == [5.0, 25.0]
    assert ctx.burst_times["prika"] == [5.0]


def test_set_status_keeps_earliest_time_and_status_since_reads_it():
    ctx = make_context(SquadMember("mint", burst_tier=2, element="Iron"))
    assert ctx.status_since("mint", "singing") is None
    ctx.set_status("mint", "singing", 25.0)
    ctx.set_status("mint", "singing", 40.0)  # re-applied later; earliest wins
    assert ctx.has_status("mint", "singing") is True
    assert ctx.status_since("mint", "singing") == 25.0
    # default time (callers that don't care about timing) records 0.0
    ctx.set_status("mint", "dancing")
    assert ctx.status_since("mint", "dancing") == 0.0


def test_ally_bursted_reads_last_burst_slug():
    # An ally_burst_activate rule reacts to a SPECIFIC other unit bursting (e.g.
    # Prika's Encore keys off Mint). last_burst_slug is set by raid_simulator
    # before the trigger fires.
    ctx = make_context(
        SquadMember("mint", burst_tier=2, element="Iron"),
        SquadMember("prika", burst_tier=2, element="Water"),
    )
    assert ally_bursted("mint")(ctx, "prika") is False  # nobody bursted yet
    ctx.last_burst_slug = "mint"
    assert ally_bursted("mint")(ctx, "prika") is True
    ctx.last_burst_slug = "prika"
    assert ally_bursted("mint")(ctx, "prika") is False


def test_all_conditions_requires_every_condition():
    ctx = make_context(SquadMember("prika", burst_tier=2, element="Water"))
    ctx.set_status("prika", "performance")
    ctx.last_burst_slug = "mint"
    cond = all_conditions(ally_bursted("mint"), has_status("performance"))
    assert cond(ctx, "prika") is True
    ctx.clear_status("prika", "performance")
    assert cond(ctx, "prika") is False


def test_deck_contains_checks_squad_membership():
    ctx = make_context(
        SquadMember("mast", burst_tier=2, element="Water"),
        SquadMember("anchor", burst_tier=2, element="Water"),
    )
    assert deck_contains("anchor")(ctx, "mast") is True
    assert deck_contains("liter")(ctx, "mast") is False


def test_top_atk_slugs_ranks_allies_by_base_atk_excluding_caster():
    ctx = SquadContext(
        [
            SquadMember("miranda", burst_tier=1, element="Fire"),
            SquadMember("scarlet", burst_tier=3, element="Fire"),
            SquadMember("blast", burst_tier=1, element="Wind"),
            SquadMember("liter", burst_tier=1, element="Iron"),
        ],
        base_atk={"miranda": 90000, "scarlet": 80000, "blast": 70000, "liter": 60000},
    )
    registry = EffectRegistry()
    # caster (miranda) is excluded even though she has the highest base ATK.
    assert ctx.top_atk_slugs(2, "miranda", registry, time=0.0) == ["scarlet", "blast"]
    assert ctx.top_atk_slugs(1, "miranda", registry, time=0.0) == ["scarlet"]


def test_top_atk_slugs_uses_live_final_atk_including_buffs():
    ctx = SquadContext(
        [
            SquadMember("miranda", burst_tier=1, element="Fire"),
            SquadMember("scarlet", burst_tier=3, element="Fire"),
            SquadMember("blast", burst_tier=1, element="Wind"),
        ],
        base_atk={"miranda": 50000, "scarlet": 70000, "blast": 72000},
    )
    registry = EffectRegistry()
    # base ranking would be blast (72k) > scarlet (70k); a big atk_percent on
    # scarlet flips it - final ATK is evaluated live at `time`.
    registry.add(Effect("atk_percent", 0.5, "slugs:scarlet", None, "buffer"), applied_at=0.0)
    assert ctx.top_atk_slugs(1, "miranda", registry, time=1.0) == ["scarlet"]  # 70k*1.5=105k
    # flat_atk also counts
    registry2 = EffectRegistry()
    registry2.add(Effect("flat_atk", 10000, "slugs:blast", None, "buffer"), applied_at=0.0)
    assert ctx.top_atk_slugs(1, "miranda", registry2, time=1.0) == ["blast"]  # 72k+10k=82k > 70k


def test_top_atk_slugs_includes_caster_when_not_enough_allies():
    # "including the caster if there are not enough allies": a 2-member deck asked
    # for top-2 non-caster allies has only 1, so the caster fills the second slot.
    ctx = SquadContext(
        [
            SquadMember("miranda", burst_tier=1, element="Fire"),
            SquadMember("scarlet", burst_tier=3, element="Fire"),
        ],
        base_atk={"miranda": 90000, "scarlet": 80000},
    )
    registry = EffectRegistry()
    result = ctx.top_atk_slugs(2, "miranda", registry, time=0.0)
    assert sorted(result) == ["miranda", "scarlet"]


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
