from app.effects import Effect, EffectRegistry
from app.squad_engine import (
    SkillRule,
    SquadContext,
    SquadMember,
    all_conditions,
    ally_bursted,
    boss_is_element,
    burst_stage_entered,
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


def test_burst_stage_entered_keys_off_the_burster_tier_not_its_slug():
    # "Activates when entering Burst Stage 2" is about the STAGE, not about the
    # caster bursting: Flora's Favorite Item bullet must fire even in the cycle
    # where a different Burst-2 ally takes the tier-2 slot.
    ctx = make_context(
        SquadMember("flora-signature", burst_tier=2, element="Electric"),
        SquadMember("other-b2", burst_tier=2, element="Water"),
        SquadMember("some-b3", burst_tier=3, element="Fire"),
    )
    assert burst_stage_entered(2)(ctx, "flora-signature") is False  # nobody bursted yet
    ctx.last_burst_slug = "flora-signature"
    assert burst_stage_entered(2)(ctx, "flora-signature") is True  # she took the slot
    ctx.last_burst_slug = "other-b2"
    assert burst_stage_entered(2)(ctx, "flora-signature") is True  # stage 2 entered anyway
    ctx.last_burst_slug = "some-b3"
    assert burst_stage_entered(2)(ctx, "flora-signature") is False
    # An unknown slug must not raise - it simply isn't a stage-2 entry.
    ctx.last_burst_slug = "not-in-deck"
    assert burst_stage_entered(2)(ctx, "flora-signature") is False


def test_boss_is_element_reads_context_boss_element():
    # A boss-element-conditional debuff (e.g. Brid's Wind-Code Damage Taken)
    # gates on the boss's element, which only raid_simulator knows - it's threaded
    # onto SquadContext so a SkillRule condition can read it.
    ctx = make_context(SquadMember("brid-silent-track", burst_tier=2, element="Fire"))
    assert ctx.boss_element is None  # default when unset
    assert boss_is_element("Wind")(ctx, "brid-silent-track") is False

    ctx.boss_element = "Wind"
    assert boss_is_element("Wind")(ctx, "brid-silent-track") is True
    assert boss_is_element("Electric")(ctx, "brid-silent-track") is False


def test_squad_context_stores_boss_element():
    ctx = SquadContext(
        [SquadMember("helm-aquamarine", burst_tier=2, element="Iron")],
        boss_element="Electric",
    )
    assert ctx.boss_element == "Electric"


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


def test_resource_count_accumulates_all_fills_up_to_time_when_permanent():
    # A permanent (lifetime=None) resource: count at `time` is the sum of every
    # fill AT OR BEFORE that time (Guillotine's EXP, which accumulates
    # continuously). Fills recorded out of order still sum correctly by time.
    ctx = make_context(SquadMember("guillotine-winter-slayer", burst_tier=3, element="Water"))
    ctx.fill_resource("guillotine-winter-slayer", "exp", 1, time=3.0)
    ctx.fill_resource("guillotine-winter-slayer", "exp", 1, time=1.0)
    ctx.fill_resource("guillotine-winter-slayer", "exp", 1, time=2.0)
    count = lambda t: ctx.resource_count("guillotine-winter-slayer", "exp", t, cap=100)
    assert count(0.5) == 0
    assert count(1.0) == 1  # fill at exactly t counts
    assert count(2.5) == 2
    assert count(10.0) == 3


def test_resource_count_clamps_to_cap():
    ctx = make_context(SquadMember("soda-twinkling-bunny", burst_tier=3, element="Iron"))
    ctx.fill_resource("soda-twinkling-bunny", "chip", 50, time=0.0)
    ctx.fill_resource("soda-twinkling-bunny", "chip", 50, time=1.0)
    # 100 raw, but capped at 50.
    assert ctx.resource_count("soda-twinkling-bunny", "chip", 2.0, cap=50) == 50


def test_resource_count_windowed_for_timed_stacks():
    # A timed resource (lifetime seconds): a fill at tf is active for
    # [tf, tf+lifetime); at query time t only fills in (t-lifetime, t] count
    # (Modernia's stacks last 10 sec). Cap still applies to the window.
    ctx = make_context(SquadMember("modernia", burst_tier=3, element="Fire"))
    for tf in (0.0, 4.0, 8.0):
        ctx.fill_resource("modernia", "evolution", 1, time=tf)
    count = lambda t: ctx.resource_count("modernia", "evolution", t, cap=5, lifetime=10.0)
    assert count(0.0) == 1  # only the t=0 fill
    assert count(8.0) == 3  # all three within the last 10s
    assert count(10.5) == 2  # t=0 fill expired (0 <= 10.5-10=0.5 is false), t=4,8 remain
    assert count(18.5) == 0  # all expired


def test_resource_count_zero_for_unfilled_resource():
    ctx = make_context(SquadMember("modernia", burst_tier=3, element="Fire"))
    assert ctx.resource_count("modernia", "evolution", 5.0, cap=5) == 0


def test_resource_count_uses_latest_reset_as_baseline():
    # A reset (e.g. Soda's Golden Chip resetting to 17 on her own burst) sets a
    # new baseline - fills BEFORE the reset no longer count; fills after it add
    # on top of the reset's post-value.
    ctx = make_context(SquadMember("soda-twinkling-bunny", burst_tier=3, element="Iron"))
    ctx.fill_resource("soda-twinkling-bunny", "chip", 1, time=1.0)
    ctx.fill_resource("soda-twinkling-bunny", "chip", 1, time=2.0)
    ctx.reset_resource("soda-twinkling-bunny", "chip", time=3.0, pre_value=50, post_value=17)
    ctx.fill_resource("soda-twinkling-bunny", "chip", 1, time=4.0)
    count = lambda t: ctx.resource_count("soda-twinkling-bunny", "chip", t, cap=50)
    assert count(2.5) == 2       # before the reset: just the two early fills
    assert count(3.0) == 17      # at the reset: the post-value applies
    assert count(4.0) == 18      # a fill after the reset adds on top of it
    assert count(2.9999) == 2    # confirms the reset boundary, not a fluke


def test_resource_count_before_reset_reads_the_pre_value_at_that_exact_time():
    ctx = make_context(SquadMember("soda-twinkling-bunny", burst_tier=3, element="Iron"))
    ctx.reset_resource("soda-twinkling-bunny", "chip", time=3.0, pre_value=32, post_value=17)
    assert ctx.resource_count_before_reset("soda-twinkling-bunny", "chip", 3.0) == 32
    assert ctx.resource_count_before_reset("soda-twinkling-bunny", "chip", 3.1) is None
    assert ctx.resource_count_before_reset("soda-twinkling-bunny", "other-resource", 3.0) is None


def test_resource_count_handles_multiple_resets_in_sequence():
    ctx = make_context(SquadMember("soda-twinkling-bunny", burst_tier=3, element="Iron"))
    ctx.reset_resource("soda-twinkling-bunny", "chip", time=0.0, pre_value=0, post_value=50)
    ctx.fill_resource("soda-twinkling-bunny", "chip", 1, time=5.0)
    ctx.reset_resource("soda-twinkling-bunny", "chip", time=10.0, pre_value=51, post_value=17)
    count = lambda t: ctx.resource_count("soda-twinkling-bunny", "chip", t, cap=50)
    assert count(0.0) == 50
    assert count(5.0) == 50  # +1 clamped at cap 50
    assert count(10.0) == 17
    assert count(10.1) == 17


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


def test_boss_core_hittable_condition_reads_context_flag():
    from app.squad_engine import SquadContext, SquadMember, boss_core_hittable
    cond = boss_core_hittable()
    members = [SquadMember("a", 3, "Iron")]
    assert cond(SquadContext(members, core_hittable=True), "a") is True
    assert cond(SquadContext(members), "a") is False
