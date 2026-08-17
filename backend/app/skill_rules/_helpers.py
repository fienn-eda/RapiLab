"""Small builders shared by the many Burst-1 support skill encodings.

Most supporters just grant a bundle of timed buffs on a trigger, or emit a
burst-cooldown-reduction pulse. These two helpers cover that so each Nikke
module only has to declare its stats/values, not re-implement the action.
"""
from itertools import count

from app.burst_cycle import FULL_BURST_DURATION
from app.effects import Effect, Pulse, ResourceBuff, RoundGrant
from app.squad_engine import SkillRule

# Distinct cap-group ids for capped round_buff_rules (see round_buff_rule).
_round_cap_group_ids = count()
_refresh_group_ids = count()


def full_burst_window_length(context, time):
    """지금 열린 창이 남긴 시간. 컨텍스트가 창을 모르면(버스트 사이클 없는 테스트)
    엔진 기본값으로 떨어진다. "continuously"라고 적힌 풀 버스트 버프(도로시의
    Radiant Wings)가 쓴다 - 창 길이가 사이클마다 달라지므로 고정 상수로는 못
    재현한다."""
    end = context.current_full_burst_end
    return FULL_BURST_DURATION if end is None else max(0.0, end - time)


def _rule(trigger, action, condition, time_condition=None):
    """Build a SkillRule, attaching `condition`/`time_condition` only when given
    (None keeps SkillRule's own always-true defaults) - so a gated bullet (e.g. a
    boss-element-conditional debuff, or one gated on a status that may have
    lapsed) reuses the same builder as an ungated one."""
    rule = SkillRule(trigger=trigger, action=action)
    if condition is not None:
        rule.condition = condition
    if time_condition is not None:
        rule.time_condition = time_condition
    return rule


def buff_rule(trigger, buffs, condition=None, time_condition=None):
    """buffs: list of (stat, value, scope, duration). duration None = permanent.
    `condition`: optional SkillRule condition (e.g. boss_is_element("Wind")) for a
    bullet that only applies in some sims.
    `time_condition`: optional gate that needs the trigger's own TIME - for a
    bullet gated on a status whose window runs on a clock the deck does not set
    (Emma: Tactical Upgrade's Enhanced Environment Setup, live 10 sec out of
    every 30 from battle start)."""

    def action(context, caster_slug, time, registry):
        for stat, value, scope, duration in buffs:
            registry.add(Effect(stat, value, scope, duration, caster_slug), applied_at=time)

    return _rule(trigger, action, condition, time_condition)


def seated_scope(context, caster_slug, registry, time):
    """The scope of a bullet that reaches the caster's SEAT - herself plus the 2
    allies beside her.

    Two wordings land here. The direct one names the sides ("Affects self and 2
    allies on both sides", Rouge's Sword Coin). The indirect one names a STATE
    that a sibling bullet granted to "self and both adjacent allies" ("Affects
    all allies in the Peace of Mind state", Flora's Favorite Item) - the state's
    holders are that same three, so the scope is the same.

    Who the 2 are is `SquadContext.neighbor_slugs`: the seating if one was
    supplied, otherwise its policy. The caster leads the list because every one
    of these wordings includes her."""
    return "slugs:" + ",".join(
        [caster_slug] + context.neighbor_slugs(caster_slug, registry, time))


def seated_buff_rule(trigger, buffs, condition=None):
    """Like buff_rule, but scoped to the caster's seat (see seated_scope).
    buffs: list of (stat, value, duration) - no scope, since the seat IS the
    scope and it is only known when the rule fires."""

    def action(context, caster_slug, time, registry):
        scope = seated_scope(context, caster_slug, registry, time)
        for stat, value, duration in buffs:
            registry.add(Effect(stat, value, scope, duration, caster_slug), applied_at=time)

    return _rule(trigger, action, condition)


def refreshing_buff_rule(trigger, buffs, condition=None, refresh_group=None):
    """Like buff_rule, but each buff REFRESHES instead of stacking (see
    EffectRegistry.add_refreshing) - for a per-shot buff re-applied every shot,
    which the game refreshes rather than stacks. `condition`: optional SkillRule
    condition, as in buff_rule.

    Each rule instance gets its own refresh group, so re-applications of THIS
    bullet collapse into one another while the same unit's other buffs on the
    same stat are left alone. Without that, Liberalio's permanent Raging
    Current (+231% self Attack Damage) was truncated to nothing by her own
    on-core buff (+20.83%, same stat and scope) on her very first shot.

    Pass an explicit `refresh_group` for ONE status granted by SEVERAL triggers -
    Eunhwa: Tactical Upgrade's Camouflage arms both on her burst and on every
    Full Charge inside Full Burst, and the two windows overlap. Sharing a group
    is what makes them one status rather than two that sum."""
    group = refresh_group or f"refresh_{next(_refresh_group_ids)}"

    def action(context, caster_slug, time, registry):
        for stat, value, scope, duration in buffs:
            registry.add_refreshing(
                Effect(stat, value, scope, duration, caster_slug, refresh_group=group),
                applied_at=time,
            )

    return _rule(trigger, action, condition)


def cdr_pulse_rule(trigger, seconds, scope="squad"):
    def action(context, caster_slug, time, registry):
        registry.add_pulse(Pulse("burst_cooldown_reduction_sec", seconds, scope, caster_slug))

    return SkillRule(trigger=trigger, action=action)


def instant_nuke_pulse_rule(
    trigger, percent, condition=None, damage_type="attack"
):
    """"Deals X% of final ATK as damage" tied to a trigger OTHER than the
    caster's own burst (e.g. Brid: Silent Track's Ignition Sequence, on
    full_burst_enter). raid_simulator.drain_instant_damage computes it using
    the caster's own ATK and live buffs, exactly like a burst nuke.

    There is NO Full Burst eligibility parameter, deliberately. A pulse emitted
    here is recorded at the time its trigger fires, and the engine gives it the
    bonus if and only if that time falls inside a Full Burst window. Passing an
    opt-in used to be required, keyed on whether the skill said "as ADDITIONAL
    damage"; that rule was deleted on 2026-07-28 (Fienn) once its origin was
    clear - a Burst 3's instant "as damage" bullets resolve AT the cast, one
    beat before the window opens, so the phrase only ever CORRELATED with the
    timing and was never the cause. See `_damage_instance` in raid_simulator.

    `condition`: optional SkillRule condition (e.g. boss_is_element("Wind")) for a
    bullet that only applies in some sims.

    `damage_type`: the nuke's damage typing when its text names one (e.g.
    "as Distributed Damage" -> "distributed"), so the type-gated Damage-Up
    buckets apply to it. Default "attack"."""

    def action(context, caster_slug, time, registry):
        registry.add_pulse(
            Pulse(
                "instant_damage_percent", percent, "self", caster_slug,
                damage_type,
            )
        )

    return _rule(trigger, action, condition)


def _resolve_scope(scope_spec, context, caster_slug, registry, time, grant_stats=None):
    """A buff's scope can be a static string ("squad", "self", "element:X") or a
    dynamic ("top_atk", n) that resolves - at application time - to the n allies
    with the highest final ATK, encoded as a "slugs:a,b" scope.

    `grant_stats` is what stat this grant hands out, recorded on the target log
    (SquadContext.target_grants) for WHICHEVER caller's `("top_atk", n)` scope
    this resolves - not only Miranda's. A static scope has no ranking to
    record, so it's ignored there."""
    if isinstance(scope_spec, tuple) and scope_spec[0] == "top_atk":
        slugs = context.top_atk_slugs(scope_spec[1], caster_slug, registry, time,
                                      grant_stats=grant_stats)
        return "slugs:" + ",".join(slugs)
    return scope_spec


def highest_atk_buff_rule(trigger, n, buffs, refreshing=False, member_filter=None,
                          include_caster=False):
    """Timed buffs on the `n` allies with the highest final ATK at trigger time
    (except the caster) - e.g. Miranda's Powering Up. buffs: (stat, value,
    duration). The target set is ranked live, so a buff applied earlier in the
    same cycle is reflected (see SquadContext.top_atk_slugs).

    This is a SHARED helper - it also backs Maxwell's Straight Shot, Leona's
    pellet bullet and Naga's Support of Friendship. Every call passes its own
    buffs' stat names as `grant_stats`, so whichever caster invokes it gets
    logged the same way when a log is attached; a consumer reads
    SquadContext.target_grants and filters by caster to pick out the one
    bullet it cares about.

    `refreshing`: for a bullet re-applied faster than it expires - a per-shot
    top-N grant whose duration outlives its own trigger interval (Naga's
    Support of Friendship, 5 sec on every 5th shot, which her shotgun fires
    every 3.3-5.0 sec). Without it the overlaps SUM, multiplying the buff by
    however many windows are live. Each rule instance gets its own refresh
    group, as in refreshing_buff_rule, so it never truncates a different
    bullet that happens to grant the same stat.

    `member_filter(member) -> bool`: narrow the candidates before ranking, for a
    bullet that is a class AND a top-N at once ("the 2 ally unit(s) with
    shotguns who have the highest final ATK", Leona). Passed to top_atk_slugs;
    a deck with no matching member grants nothing.

    `include_caster`: whether the caster competes for the slots. Read it off the
    bullet - an "except caster" clause means False (the default, Miranda/Mana/
    Soda), its absence means True (Maxwell/Leona/Naga). See top_atk_slugs."""
    group = f"refresh_{next(_refresh_group_ids)}" if refreshing else None

    def action(context, caster_slug, time, registry):
        targets = context.top_atk_slugs(n, caster_slug, registry, time,
                                        member_filter=member_filter,
                                        include_caster=include_caster,
                                        grant_stats=tuple(stat for stat, _, _ in buffs))
        if not targets:
            return
        scope = "slugs:" + ",".join(targets)
        for stat, value, duration in buffs:
            effect = Effect(stat, value, scope, duration, caster_slug, refresh_group=group)
            if refreshing:
                registry.add_refreshing(effect, applied_at=time)
            else:
                registry.add(effect, applied_at=time)

    return SkillRule(trigger=trigger, action=action)


def member_subset_buff_rule(trigger, member_filter, buffs, condition=None,
                            refreshing=False, time_condition=None):
    """Timed buffs on the squad members selected by `member_filter` at trigger
    time - the narrow subsets Effect.scope can't express ("all Wind Code allies
    with assault rifles", "all Burst 3 allies who previously used their Burst
    Skill"). Resolved live to a "slugs:" scope like highest_atk_buff_rule, so
    dynamic state (burst_used_this_cycle) is read at the trigger's own moment.
    member_filter(member, context) -> bool; the caster is included when it
    matches. buffs: (stat, value, duration)."""
    group = f"refresh_{next(_refresh_group_ids)}"

    def action(context, caster_slug, time, registry):
        slugs = [m.slug for m in context.members if member_filter(m, context)]
        if not slugs:
            return
        scope = "slugs:" + ",".join(slugs)
        for stat, value, duration in buffs:
            effect = Effect(stat, value, scope, duration, caster_slug,
                            refresh_group=group if refreshing else None)
            if refreshing:
                registry.add_refreshing(effect, applied_at=time)
            else:
                registry.add(effect, applied_at=time)

    return _rule(trigger, action, condition, time_condition)


def round_buff_rule(trigger, buffs, shots=1, cap=None):
    """"For N round(s)" buffs, whose duration is measured in the affected ally's
    NEXT `shots` normal attacks (bullets), not seconds - e.g. Zwei's Pierce
    Equation, Miranda's Wake Up crit rate. Records a RoundGrant per buff; the shot
    loop turns each into a timed Effect covering exactly those shots. buffs:
    (stat, value, scope_spec) where scope_spec is "squad"/"self"/"element:X" or a
    dynamic ("top_atk", n) resolved to the top-ATK allies at grant time.
    `cap` is the skill's "stacks up to N time(s)" limit, if it has one: no
    recipient holds more than `cap` concurrent grants from THIS rule (see
    effects.RoundGrant). Rules built without it are uncapped as before."""

    # One cap group per rule instance, so a caster's other round-grant rules -
    # including ones granting the same stat - never share this rule's cap.
    cap_group = f"round_grant_cap_{next(_round_cap_group_ids)}" if cap is not None else None

    def action(context, caster_slug, time, registry):
        for stat, value, scope_spec in buffs:
            scope = _resolve_scope(scope_spec, context, caster_slug, registry, time,
                                   grant_stats=(stat,))
            registry.add_round_grant(
                RoundGrant(stat, value, scope, caster_slug, shots, time, cap, cap_group)
            )

    return SkillRule(trigger=trigger, action=action)


def linear_resource_buff(stat, per_stack, scope):
    """A resource-derived buff whose value grows linearly with the stack count:
    `per_stack` per stack (e.g. Guillotine's EXP: ATK +1.81% per stack; Modernia's
    Crit Damage +14.25% per stack). Build a ResourceSpec around one or more of
    these (see effects.ResourceSpec).

    How long the stack lives is the RESOURCE's property, set on the
    `ResourceSpec` - the game gives the stack one clock and every reader of the
    count shares it. The skill text picks between three:
    - `lifetime=None` = permanent accumulation ("stacks up to N ...
      continuously"), and also the exact model for a timed stack whose fills
      always arrive inside its duration (Leona's Roar, Centi's Field Discussion).
    - `lifetime=D, lifetime_refreshes=True` = "stacks up to N and lasts for D
      sec": one clock the whole stack shares, restarted by every fill. The usual
      reading of that clause.
    - `lifetime=D` alone = each stack on its own clock. The rarer case - justify
      it where it is used.
    """
    return ResourceBuff(stat=stat, scope=scope, value_fn=lambda count: per_stack * count)


def leveled_resource_buff(stat, per_level, level_fn, scope):
    """A resource-derived buff scaled by a LEVEL derived from the stack count,
    not the raw count - e.g. Guillotine's Hero Level (= EXP // 10, capped),
    granting per-level buffs. `level_fn` maps the (capped) count to the level;
    the buff value is `per_level * level`, so it steps only when the level rises."""
    return ResourceBuff(
        stat=stat, scope=scope, value_fn=lambda count: per_level * level_fn(count)
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

    Each TIER refreshes only against itself: the tiers are cumulative, so two of
    them granting the same stat must add rather than replace one another.
    """
    tier_groups = [f"refresh_{next(_refresh_group_ids)}" for _ in tiers]

    def action(context, caster_slug, time, registry):
        n = context.activation_count(caster_slug, trigger)
        for unlock_at, buffs in enumerate(tiers, start=1):
            if n >= unlock_at:
                for stat, value, scope, duration in buffs:
                    effect = Effect(stat, value, scope, duration, caster_slug,
                                    refresh_group=tier_groups[unlock_at - 1] if refreshing else None)
                    if refreshing:
                        registry.add_refreshing(effect, applied_at=time)
                    else:
                        registry.add(effect, applied_at=time)

    return SkillRule(trigger=trigger, action=action)


def escalating_cdr_rule(trigger, tier_seconds):
    """The cooldown-reduction half of an escalating bullet.

    `escalating_buff_rule` covers the registry-effect case; a burst-cooldown
    reduction is a Pulse instead, so it needs its own accumulator. On the Nth
    activation every tier unlocked so far fires and they ADD - 2.34, then 5.04,
    then 8.21 sec (Fienn, 2026-07-27). The range measurement could only prove
    the tiers escalate, since cumulative and superseding agree on activation 1;
    Fienn settled which.
    """

    def action(context, caster_slug, time, registry):
        n = context.activation_count(caster_slug, trigger)
        seconds = sum(
            value for unlock_at, value in enumerate(tier_seconds, start=1) if n >= unlock_at
        )
        if seconds:
            registry.add_pulse(Pulse("burst_cooldown_reduction_sec", seconds, "squad", caster_slug))

    return SkillRule(trigger=trigger, action=action)


# Nikkes whose own skills restore a unit's HP. Derived from the collected skill
# text - `provider_scan.heal_provider_slugs()` re-derives it and
# tests/test_provider_lists_match_data.py fails when this drifts, so a newly
# encoded healer cannot go missing here the way six of them did.
# Cover-HP restores are excluded: the cover's health is not a unit receiving
# recovery. Used only by Crown, whose Royal Attire arms on ANY ally's healing -
# the engine has no heal event, so deck presence is what can be asked.
HEAL_PROVIDER_SLUGS = frozenset({
    "ada-wong",
    "anchor-innocent-maid",
    "anis-star",
    "asuka-shikinami-langley-wille",
    "blanc",
    "centi",
    "centi-signature",
    "crown",
    "delta-ninja-thief",
    "emma-tactical-upgrade",
    "flora",
    "flora-signature",
    "grave",
    "guillotine-winter-slayer",
    "helm",
    "helm-signature",
    "mana",
    "mint",
    "moran",
    "moran-signature",
    "naga",
    "nayuta",
    "prika",
    "red-hood",
    "soline-frost-ticket",
    "yukiko-amagi",
})

# Nikkes whose own skills place a shield that reaches the WHOLE squad. Same
# shape and same reason as the heal list: Flora's Favorite Item Iris bullet arms
# on "a shield is placed in front of this unit" and the engine has no shield
# event, so deck presence is what can be asked.
SHIELD_PROVIDER_SLUGS = frozenset({
    "blanc",
    "centi",
    "centi-signature",
    "crown",
    "flora",
    "flora-signature",
})

# The Absolute squad, ELYSION's own - the audience of "Affects all allies from
# the same squad", which Eunhwa: Tactical Upgrade's AS Formation and Emma:
# Tactical Upgrade's LT Formation both use. A NIKKE's squad is her in-fiction
# unit (`detail.squad` in the ShiftyPad bundle), not her deck, and the engine's
# scopes cannot express it - but the membership is short and settled: Emma,
# Eunhwa and Vesti, base and Tactical Upgrade each, six units, of which these
# two are the only ones encoded (read off the 43 ELYSION SSR bundles,
# 2026-08-08). So the bullet resolves EXACTLY via member_subset_buff_rule
# rather than being approximated onto `squad`.
#
# Add the other four here as they are encoded; a squad-mate missing from this
# set silently loses a buff the game gives her.
ABSOLUTE_SQUAD_SLUGS = frozenset({
    "emma-tactical-upgrade",
    "eunhwa-tactical-upgrade",
})


# The Persona state, the audience of "all standard Burst 3 allies (except the
# skill user) in the Persona state" - Queen (Makoto Nijima)'s Baton Pass and
# Yukiko Amagi's Follow Up. Each collab unit puts HERSELF in it with her own
# Skill 1 at battle start ("Persona - Johanna", "Persona - Konohana Sakuya"),
# and nothing else grants it, so the state is exactly "is a Persona unit". Like
# ABSOLUTE_SQUAD_SLUGS it is a membership the engine's scopes cannot express but
# that member_subset_buff_rule can resolve exactly, so neither bullet is
# approximated onto `squad`.
#
# Aigis is the collab's third unit and is deliberately absent: she is SR, so she
# is neither a raid deck candidate nor encoded. Add her here if that changes.
PERSONA_STATE_SLUGS = frozenset({
    "queen-makoto-nijima",
    "yukiko-amagi",
})

# Units who can be in "Annihilation State", the same shape of membership as
# PERSONA_STATE_SLUGS - a named status the engine's scopes cannot express, read
# by an ALLY's bullet rather than by its own holder. Rei Ayanami (Tentative
# Name)'s Annihilation Support buffs "all allies in Annihilation State status",
# and Asuka: WILLE is the only unit who has it.
#
# It differs from the Persona state in one way that matters: Persona is
# self-applied at battle start and never removed, so membership alone answers
# it, while Annihilation State is opened by the holder's OWN burst and runs 9
# sec. So a consumer must ALSO check `context.burst_used_this_cycle` - being
# the right unit is necessary, not sufficient.
ANNIHILATION_STATE_SLUGS = frozenset({
    "asuka-shikinami-langley-wille",
})


def persona_state_allies(context, caster_slug, tier):
    """"all standard Burst <tier> allies (except the skill user) in the Persona
    state" - the audience Queen (Makoto Nijima)'s Baton Pass and Yukiko Amagi's
    Follow Up share, resolved live against the deck. Empty when the caster is
    the deck's only Persona unit, which is what the game does: neither bullet
    has anyone to land on."""
    return [
        m.slug for m in context.members
        if m.burst_tier == tier
        and m.slug in PERSONA_STATE_SLUGS
        and m.slug != caster_slug
    ]


# Shields that exist but reach only part of the squad, so deck presence alone
# does NOT establish that the consumer received one. Rei: Ayanami's shield is
# "Affects all Fire Code allies" and Flora - the only consumer - is Electric.
# Kept as its own set rather than dropped, so the data cross-check stays total.
ELEMENT_GATED_SHIELD_SLUGS = frozenset({
    "rei-ayanami",
})

# Shields whose every bullet reads "Affects self" - the narrowest partial scope
# of all, and the one that reaches no consumer at all. Delta: Ninja Thief's
# Ninjutsu Camouflage shields only herself, so it can never be the shield a
# consumer asks about ("when a shield is placed in front of THIS unit"). Same
# reason ELEMENT_GATED_SHIELD_SLUGS is separate: the data cross-check has to
# account for every shield the scan finds, and silence would read as "she
# places none".
SELF_ONLY_SHIELD_SLUGS = frozenset({
    "delta-ninja-thief",
})

# Nikkes whose skills raise an ALLY's Sustained / Distributed damage. Third and
# fourth of the same shape as the two lists above, and re-derived from skill
# text by `provider_scan` under the same cross-check - a newly encoded buffer
# that never reaches these sets would silently keep Bready out of a deck she
# belongs in.
#
# Bready's consumer is not a bullet but a STATE: Lingering Taste is entered by
# "gaining a buff that increases sustained damage" and Recommended Taste by one
# that increases distributed damage. Self-scoped buffs are excluded on purpose -
# she has to RECEIVE one - which is why Diesel, Mana, Raven and the rest of the
# units whose text says "Sustained Damage ▲ ... Affects self" are absent.
SQUAD_SUSTAINED_DAMAGE_BUFF_SLUGS = frozenset({
    "rosanna-chic-ocean",
})

SQUAD_DISTRIBUTED_DAMAGE_BUFF_SLUGS = frozenset({
    "anchor-innocent-maid",
    "delta-ninja-thief",
    "mast-romantic-maid",
})

# Sustained-damage buffs that reach only part of the squad, so deck presence
# alone does not establish that a given ally received one - the same distinction
# ELEMENT_GATED_SHIELD_SLUGS draws. Ark: Ranger Black's Tremble! is "Affects all
# Wind Code allies with assault rifles", and Bready - the only consumer - is a
# Water SR. Kept as its own set rather than dropped, so the data cross-check
# stays total.
SUBSET_SUSTAINED_DAMAGE_BUFF_SLUGS = frozenset({
    "ark-ranger-black",
})


def silent_reload_segments(slug, reload_seconds, weapon, *, offset=0.0):
    """Windows that fire nothing, one per own-burst - the engine's way to spend
    a reload that a skill forced.

    A segment boundary discards the magazine and resumes with a fresh one, so a
    window this long IS "Removes N% of ammo" + "Forced Reload". `rate_of_fire`
    (not `charge_time`) because an explicit-rate profile takes no cadence buffs
    by contract, so no ally's Charge Speed can shrink the window into leaking a
    shot; `damage_percent` 0.0 makes a boundary shot harmless regardless.
    """
    def schedule(context, fight_duration):
        segments = []
        for burst_time in context.burst_times.get(slug, []):
            start = burst_time + offset
            if start >= fight_duration:
                continue
            segments.append({
                "start": start,
                "end": min(start + reload_seconds, fight_duration),
                "profile": {
                    "weapon": weapon,
                    "damage_percent": 0.0,
                    "rate_of_fire": 1.0 / (reload_seconds * 2),
                },
            })
        return segments

    return schedule


def max_hp_scaled_atk_rule(
    trigger, percent, scope, duration, base_max_hp, condition=None, refreshing=False,
    refresh_group=None,
):
    """"ATK 캐스터 Max HP의 X%"를 캐스터의 LIVE Max HP로 환산해 flat_atk를 건다.

    라이브 = 캐릭터정보 Max HP(`base_max_hp`) + 발동 시점에 활성인 `flat_max_hp`
    버프 총합. 정적 `caster_max_hp`만 쓰던 기존 인코딩은 아군/자기 Max HP 버프를
    통째로 무시했다 (Rouge의 Game Master가 유일한 부여자였고 소비자가 없어
    죽은 스탯이었다).

    의미론은 스냅샷이다 - 값은 이 룰이 발동하는 순간 고정된다. 발동 이후 도착한
    Max HP 버프는 이미 걸린 flat_atk를 소급해 키우지 않으므로, 전투 중 Max HP가
    계속 자라는 유닛은 Max HP가 바뀌는 시점마다 이 룰을 다시 발동시켜야 한다
    (Laplace의 Over Energy 단계). 딜 계산 핫패스(_stat_bundle / total_for의
    세그먼트 테이블)를 건드리지 않으려는 의도적 트레이드오프다 - 환산은
    트리거당 한 번만 일어난다.

    `percent`는 소수 비율(4.05% -> 0.0405)."""

    def action(context, caster_slug, time, registry):
        by_slug = {m.slug: m for m in context.members}
        target = {"slug": caster_slug, "element": by_slug[caster_slug].element}
        live_max_hp = context.live_max_hp(base_max_hp, target, time, registry)
        effect = Effect("flat_atk", live_max_hp * percent, scope, duration, caster_slug, refresh_group)
        if refreshing:
            registry.add_refreshing(effect, applied_at=time)
        else:
            registry.add(effect, applied_at=time)

    return _rule(trigger, action, condition)


def expected_shots_per_proc(chance_percent):
    """"There is an X% chance of activating when attacking" -> how many shots
    one activation costs on average.

    This engine is deterministic: it never rolls, and the damage path already
    resolves every other probability by its expected value (each hit is scaled
    by `crit_rate`, each shot by `core_hit_rate`, and `every_n_critical_hits`
    accumulates the live crit rate rather than counting real crits). Fienn's
    ruling, 2026-08-17: a chance-to-activate trigger is resolved the same way -
    a p% chance per shot becomes one proc every 100/p shots.

    What this does NOT unblock: a chance sitting on a trigger the engine has no
    timeline for. Sugar's Black Typhoon is "a 20% chance of activating when
    COVER IS ATTACKED", and the engine models no incoming attacks, so there is
    no event stream to thin - it stays deferred at p=1.0 as much as at p=0.2.

    Rounded to a whole shot, because the counters that consume it
    (`AmmoRefund.every_shots`, per-shot rule thresholds) index shots.
    """
    if not 0 < chance_percent <= 100:
        raise ValueError(
            f"chance must be a percentage in (0, 100], got {chance_percent!r} - "
            f"a 0% chance never procs and has no expected interval")
    return max(1, round(100 / chance_percent))
