"""Small builders shared by the many Burst-1 support skill encodings.

Most supporters just grant a bundle of timed buffs on a trigger, or emit a
burst-cooldown-reduction pulse. These two helpers cover that so each Nikke
module only has to declare its stats/values, not re-implement the action.
"""
from app.effects import Effect, Pulse, ResourceBuff, RoundGrant
from app.squad_engine import SkillRule


def _rule(trigger, action, condition):
    """Build a SkillRule, attaching `condition` only when given (None keeps
    SkillRule's own default of always-true) - so a gated bullet (e.g. a
    boss-element-conditional debuff) reuses the same builder as an ungated one."""
    rule = SkillRule(trigger=trigger, action=action)
    if condition is not None:
        rule.condition = condition
    return rule


def buff_rule(trigger, buffs, condition=None):
    """buffs: list of (stat, value, scope, duration). duration None = permanent.
    `condition`: optional SkillRule condition (e.g. boss_is_element("Wind")) for a
    bullet that only applies in some sims."""

    def action(context, caster_slug, time, registry):
        for stat, value, scope, duration in buffs:
            registry.add(Effect(stat, value, scope, duration, caster_slug), applied_at=time)

    return _rule(trigger, action, condition)


def refreshing_buff_rule(trigger, buffs, condition=None):
    """Like buff_rule, but each buff REFRESHES instead of stacking (see
    EffectRegistry.add_refreshing) - for a per-shot buff re-applied every shot,
    which the game refreshes rather than stacks. `condition`: optional SkillRule
    condition, as in buff_rule."""

    def action(context, caster_slug, time, registry):
        for stat, value, scope, duration in buffs:
            registry.add_refreshing(Effect(stat, value, scope, duration, caster_slug), applied_at=time)

    return _rule(trigger, action, condition)


def cdr_pulse_rule(trigger, seconds, scope="squad"):
    def action(context, caster_slug, time, registry):
        registry.add_pulse(Pulse("burst_cooldown_reduction_sec", seconds, scope, caster_slug))

    return SkillRule(trigger=trigger, action=action)


def instant_nuke_pulse_rule(
    trigger, percent, full_burst_bonus_eligible=False, condition=None, damage_type="attack"
):
    """"Deals X% of final ATK as damage" tied to a trigger OTHER than the
    caster's own burst (e.g. Brid: Silent Track's Ignition Sequence, on
    full_burst_enter). raid_simulator.drain_instant_damage computes it using
    the caster's own ATK and live buffs, exactly like a burst nuke.

    `full_burst_bonus_eligible`: pass True only when the skill's own damage
    text says "as additional damage" (Fienn, 2026-07-12) - e.g. Asuka's Skill 1
    per-shot nuke. raid_simulator still checks the shot's actual time against
    the Full Burst window; this only opts the instance IN to that check.

    `condition`: optional SkillRule condition (e.g. boss_is_element("Electric"))
    for an additional-damage bullet that only fires against a matching enemy.

    `damage_type`: the nuke's damage typing when its text names one (e.g.
    "as Distributed Damage" -> "distributed"), so the type-gated Damage-Up
    buckets apply to it. Default "attack"."""

    def action(context, caster_slug, time, registry):
        registry.add_pulse(
            Pulse(
                "instant_damage_percent", percent, "self", caster_slug,
                full_burst_bonus_eligible, damage_type,
            )
        )

    return _rule(trigger, action, condition)


def _resolve_scope(scope_spec, context, caster_slug, registry, time):
    """A buff's scope can be a static string ("squad", "self", "element:X") or a
    dynamic ("top_atk", n) that resolves - at application time - to the n allies
    with the highest final ATK, encoded as a "slugs:a,b" scope."""
    if isinstance(scope_spec, tuple) and scope_spec[0] == "top_atk":
        slugs = context.top_atk_slugs(scope_spec[1], caster_slug, registry, time)
        return "slugs:" + ",".join(slugs)
    return scope_spec


def highest_atk_buff_rule(trigger, n, buffs):
    """Timed buffs on the `n` allies with the highest final ATK at trigger time
    (except the caster) - e.g. Miranda's Powering Up. buffs: (stat, value,
    duration). The target set is ranked live, so a buff applied earlier in the
    same cycle is reflected (see SquadContext.top_atk_slugs)."""

    def action(context, caster_slug, time, registry):
        scope = "slugs:" + ",".join(context.top_atk_slugs(n, caster_slug, registry, time))
        for stat, value, duration in buffs:
            registry.add(Effect(stat, value, scope, duration, caster_slug), applied_at=time)

    return SkillRule(trigger=trigger, action=action)


def member_subset_buff_rule(trigger, member_filter, buffs, condition=None, refreshing=False):
    """Timed buffs on the squad members selected by `member_filter` at trigger
    time - the narrow subsets Effect.scope can't express ("all Wind Code allies
    with assault rifles", "all Burst 3 allies who previously used their Burst
    Skill"). Resolved live to a "slugs:" scope like highest_atk_buff_rule, so
    dynamic state (burst_used_this_cycle) is read at the trigger's own moment.
    member_filter(member, context) -> bool; the caster is included when it
    matches. buffs: (stat, value, duration)."""

    def action(context, caster_slug, time, registry):
        slugs = [m.slug for m in context.members if member_filter(m, context)]
        if not slugs:
            return
        scope = "slugs:" + ",".join(slugs)
        for stat, value, duration in buffs:
            effect = Effect(stat, value, scope, duration, caster_slug)
            if refreshing:
                registry.add_refreshing(effect, applied_at=time)
            else:
                registry.add(effect, applied_at=time)

    return _rule(trigger, action, condition)


def round_buff_rule(trigger, buffs, shots=1):
    """"For N round(s)" buffs, whose duration is measured in the affected ally's
    NEXT `shots` normal attacks (bullets), not seconds - e.g. Zwei's Pierce
    Equation, Miranda's Wake Up crit rate. Records a RoundGrant per buff; the shot
    loop turns each into a timed Effect covering exactly those shots. buffs:
    (stat, value, scope_spec) where scope_spec is "squad"/"self"/"element:X" or a
    dynamic ("top_atk", n) resolved to the top-ATK allies at grant time."""

    def action(context, caster_slug, time, registry):
        for stat, value, scope_spec in buffs:
            scope = _resolve_scope(scope_spec, context, caster_slug, registry, time)
            registry.add_round_grant(RoundGrant(stat, value, scope, caster_slug, shots, time))

    return SkillRule(trigger=trigger, action=action)


def linear_resource_buff(stat, per_stack, scope, lifetime=None):
    """A resource-derived buff whose value grows linearly with the stack count:
    `per_stack` per stack (e.g. Guillotine's EXP: ATK +1.81% per stack; Modernia's
    Crit Damage +14.25% per stack). lifetime None = permanent accumulation; a
    number = each stack expires that many seconds after its fill. Build a
    ResourceSpec around one or more of these (see effects.ResourceSpec)."""
    return ResourceBuff(stat=stat, scope=scope, value_fn=lambda count: per_stack * count, lifetime=lifetime)


def leveled_resource_buff(stat, per_level, level_fn, scope, lifetime=None):
    """A resource-derived buff scaled by a LEVEL derived from the stack count,
    not the raw count - e.g. Guillotine's Hero Level (= EXP // 10, capped),
    granting per-level buffs. `level_fn` maps the (capped) count to the level;
    the buff value is `per_level * level`, so it steps only when the level rises."""
    return ResourceBuff(
        stat=stat, scope=scope, value_fn=lambda count: per_level * level_fn(count), lifetime=lifetime
    )


def escalating_buff_rule(trigger, tiers, refreshing=False):
    """Cumulative "Once/Twice/Three times, previous effects trigger repeatedly".

    tiers[k] is the list of (stat, value, scope, duration) UNLOCKED at the
    (k+1)-th activation; use an empty list for a tier with no DPS-relevant
    effect (e.g. a Hit Rate step). On the Nth activation every unlocked tier
    (1..N) is re-applied. Relies on SquadContext.activation_count, so it must be
    fired via fire_trigger.

    `refreshing`: when a tier's duration is LONGER than the re-trigger interval
    (so re-applications overlap - e.g. Isabel's 45s Marked Target vs 40s burst
    cd), pass True to use `add_refreshing`, collapsing the overlap to one value
    instead of summing it. Default False keeps the plain-add behaviour for tiers
    whose windows never overlap.
    """

    def action(context, caster_slug, time, registry):
        n = context.activation_count(caster_slug, trigger)
        for unlock_at, buffs in enumerate(tiers, start=1):
            if n >= unlock_at:
                for stat, value, scope, duration in buffs:
                    effect = Effect(stat, value, scope, duration, caster_slug)
                    if refreshing:
                        registry.add_refreshing(effect, applied_at=time)
                    else:
                        registry.add(effect, applied_at=time)

    return SkillRule(trigger=trigger, action=action)
