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
    own_burst_status_active,
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


def test_top_atk_slugs_can_rank_within_a_member_subset():
    """"The 2 ally unit(s) with shotguns who have the highest final ATK" is a
    weapon filter AND a top-N, and neither helper alone expresses the pair.
    Filtering first keeps the ranking rule in one place - a unit module that
    re-derived final ATK to do this itself would drift from it silently."""
    ctx = SquadContext(
        [
            SquadMember("leona", burst_tier=2, element="Water", weapon="SG"),
            SquadMember("carry", burst_tier=3, element="Fire", weapon="AR"),
            SquadMember("dorothy", burst_tier=1, element="Wind", weapon="SG"),
            SquadMember("naga", burst_tier=2, element="Electric", weapon="SG"),
        ],
        base_atk={"leona": 50000, "carry": 99000, "dorothy": 80000, "naga": 70000},
    )
    registry = EffectRegistry()
    shotgun = lambda member: member.weapon == "SG"  # noqa: E731

    # The AR carry outranks every shotgun but must not be picked.
    assert ctx.top_atk_slugs(2, "leona", registry, 0.0) == ["carry", "dorothy"]
    assert ctx.top_atk_slugs(2, "leona", registry, 0.0, member_filter=shotgun) == [
        "dorothy", "naga"]
    assert ctx.top_atk_slugs(1, "leona", registry, 0.0, member_filter=shotgun) == ["dorothy"]


def test_top_atk_slugs_can_rank_the_caster_alongside_everyone_else():
    """"N ally unit(s) with the highest ATK" with NO "except caster" clause puts
    the caster in the pool from the start, if she meets the bullet's own
    conditions (Fienn, 2026-07-19 for Maxwell and 2026-08-08 as the general
    rule). The default stays exclusion, which is what Miranda's and Mana's text
    spells out."""
    ctx = SquadContext(
        [
            SquadMember("maxwell", burst_tier=3, element="Iron"),
            SquadMember("ally", burst_tier=1, element="Fire"),
            SquadMember("weak", burst_tier=2, element="Wind"),
        ],
        base_atk={"maxwell": 95000, "ally": 80000, "weak": 10000},
    )
    registry = EffectRegistry()
    # Excluded (the default): the caster's own 95k does not compete.
    assert ctx.top_atk_slugs(2, "maxwell", registry, 0.0) == ["ally", "weak"]
    # Included: she outranks both and takes a slot.
    assert ctx.top_atk_slugs(2, "maxwell", registry, 0.0, include_caster=True) == [
        "maxwell", "ally"]


def test_top_atk_slugs_include_caster_still_honours_the_member_filter():
    """"if she meets the conditions" is the whole clause - a caster outside the
    bullet's class is not in the pool even when the caster is includable."""
    ctx = SquadContext(
        [
            SquadMember("leona", burst_tier=2, element="Water", weapon="SG"),
            SquadMember("carry", burst_tier=3, element="Fire", weapon="AR"),
            SquadMember("dorothy", burst_tier=1, element="Wind", weapon="SG"),
        ],
        base_atk={"leona": 95000, "carry": 99000, "dorothy": 80000},
    )
    registry = EffectRegistry()
    shotgun = lambda member: member.weapon == "SG"  # noqa: E731
    # Leona is a shotgun and outranks Dorothy, so she takes the first slot.
    assert ctx.top_atk_slugs(2, "leona", registry, 0.0,
                             member_filter=shotgun, include_caster=True) == ["leona", "dorothy"]
    # An AR caster is outside the class - she cannot take a shotgun-only slot.
    assert ctx.top_atk_slugs(2, "carry", registry, 0.0,
                             member_filter=shotgun, include_caster=True) == ["leona", "dorothy"]


def test_top_atk_slugs_filter_still_lets_the_caster_fill_a_short_deck():
    """The caster fills remaining slots only when she matches the filter too -
    a non-shotgun caster must not be handed a shotgun-only buff."""
    ctx = SquadContext(
        [
            SquadMember("leona", burst_tier=2, element="Water", weapon="SG"),
            SquadMember("carry", burst_tier=3, element="Fire", weapon="AR"),
        ],
        base_atk={"leona": 50000, "carry": 99000},
    )
    registry = EffectRegistry()
    shotgun = lambda member: member.weapon == "SG"  # noqa: E731
    # Only one shotgun in the deck and it IS the caster, so she fills the slot.
    assert ctx.top_atk_slugs(2, "leona", registry, 0.0, member_filter=shotgun) == ["leona"]
    # A caster who does not match cannot fill it - the result stays empty.
    assert ctx.top_atk_slugs(2, "carry", registry, 0.0,
                             member_filter=lambda m: m.weapon == "RL") == []


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


def test_time_condition_defaults_to_always_true():
    fired = []
    rule = SkillRule(trigger="t", action=lambda c, s, time, r: fired.append(time))
    ctx = SquadContext([SquadMember("a", burst_tier=1, element="Fire")])
    fire_trigger("t", {"a": [rule]}, ctx, EffectRegistry(), time=3.0)
    assert fired == [3.0]


def test_a_false_time_condition_blocks_the_action():
    fired = []
    rule = SkillRule(
        trigger="t", action=lambda c, s, time, r: fired.append(time),
        time_condition=lambda c, s, time: time < 5.0,
    )
    ctx = SquadContext([SquadMember("a", burst_tier=1, element="Fire")])
    fire_trigger("t", {"a": [rule]}, ctx, EffectRegistry(), time=3.0)
    fire_trigger("t", {"a": [rule]}, ctx, EffectRegistry(), time=7.0)
    assert fired == [3.0]


def test_own_burst_status_active_is_true_only_while_the_status_runs():
    check = own_burst_status_active(10.0)
    ctx = SquadContext([SquadMember("a", burst_tier=2, element="Electric")])

    # 한 번도 버스트하지 않았으면 상태가 없다.
    assert check(ctx, "a", 5.0) is False

    ctx.record_burst_time("a", 2.5)
    assert check(ctx, "a", 12.4) is True     # 만료 직전
    assert check(ctx, "a", 12.5) is False    # 정확히 만료
    assert check(ctx, "a", 12.6) is False    # 만료 후


def test_own_burst_status_active_measures_from_the_latest_burst():
    # 「가장 최근」은 `burst_times`가 버스트 사이클 워크와 함께 자라는 동안의 뜻이다.
    # 그 워크 밖에서 이 술어를 걸면 목록이 비어 있거나(사이클 이전) 전투 마지막
    # 버스트로 끝나 있어(사이클 이후) 답이 틀린다 - 술어 독스트링의 제약.
    check = own_burst_status_active(10.0)
    ctx = SquadContext([SquadMember("a", burst_tier=2, element="Electric")])
    ctx.record_burst_time("a", 2.5)
    ctx.record_burst_time("a", 42.5)
    assert check(ctx, "a", 50.0) is True


def test_full_burst_extension_stage_reads_the_window_a_time_falls_in():
    """소다의 per-shot 넉이 자기 샷의 사이클 확장 단계를 묻는 자리. 단계는
    창마다 다르고(칩이 줄면 내려간다), 창 밖은 0이다."""
    context = SquadContext([SquadMember("soda", burst_tier=3, element="Iron")])
    assert context.full_burst_extension_stage(5.0, "soda") == 0   # 아직 아무것도 안 실림

    context.full_burst_extension_stages = [(2.0, 17.0, {"soda": 2}), (25.0, 37.0, {"soda": 1})]
    assert context.full_burst_extension_stage(2.0, "soda") == 2     # 창 시작 포함
    assert context.full_burst_extension_stage(16.9, "soda") == 2
    assert context.full_burst_extension_stage(17.0, "soda") == 0    # 창 끝 배제
    assert context.full_burst_extension_stage(20.0, "soda") == 0    # 창 사이
    assert context.full_burst_extension_stage(30.0, "soda") == 1
    assert context.full_burst_extension_stage(100.0, "soda") == 0   # 마지막 창 뒤
    assert context.full_burst_extension_stage(5.0, "someone-else") == 0  # 다른 유닛


def test_top_atk_slugs_records_the_grant_when_asked():
    log = []
    ctx = SquadContext(
        [
            SquadMember("miranda", burst_tier=1, element="Fire"),
            SquadMember("scarlet", burst_tier=3, element="Fire"),
            SquadMember("blast", burst_tier=1, element="Wind"),
        ],
        base_atk={"miranda": 50000, "scarlet": 70000, "blast": 60000},
        target_grants=log,
    )
    registry = EffectRegistry()
    ctx.top_atk_slugs(1, "miranda", registry, time=2.5, grant_stats=("crit_rate",))
    assert log == [{"caster": "miranda", "time": 2.5,
                    "stats": ["crit_rate"], "targets": ["scarlet"]}]


def test_top_atk_slugs_records_nothing_without_grant_stats():
    # grant_stats 없이 top_atk_slugs를 직접 부르면 기록에 안 남는다 - 무슨 불릿인지
    # 말하지 않은 호출을 무슨 불릿인지 아는 척 적을 수 없다. 소다가 이렇게 직접
    # 부른다; 맥스웰·레오나·나가는 공유 헬퍼 highest_atk_buff_rule을 거치며 그
    # 헬퍼가 grant_stats를 대신 넘기므로 기록되고, 마나는 top-N 랭킹을 안 쓴다.
    log = []
    ctx = SquadContext(
        [SquadMember("a", burst_tier=1, element="Fire"),
         SquadMember("b", burst_tier=3, element="Fire")],
        base_atk={"a": 1, "b": 2},
        target_grants=log,
    )
    ctx.top_atk_slugs(1, "a", EffectRegistry(), time=0.0)
    assert log == []


def test_top_atk_slugs_records_nothing_without_a_log():
    # 기본 컨텍스트는 로그가 없다 - grant_stats를 넘겨도 조용하다.
    ctx = SquadContext(
        [SquadMember("a", burst_tier=1, element="Fire"),
         SquadMember("b", burst_tier=3, element="Fire")],
        base_atk={"a": 1, "b": 2},
    )
    assert ctx.target_grants is None
    assert ctx.top_atk_slugs(1, "a", EffectRegistry(), 0.0, grant_stats=("atk_percent",)) == ["b"]
