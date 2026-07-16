"""Ties burst_cycle + squad_engine + effects + damage_formula + attack_rate
into one timeline: schedules the burst rotation, fires skill triggers at the
right moments, and totals up both burst-skill damage instances and normal-
attack damage over the fight.

"Deals X% of final ATK as burst damage" (and normal attacks' own damage%)
are passed as calculate_damage's `attack_coefficient`, NOT folded into atk:
per nikke.gg's formula the coefficient multiplies the whole Base Damage
(after defense subtraction and flat-ATK additions), so pre-multiplying atk
would mis-scale defense and flat ATK. The raw summary ATK goes in as `atk`.

Normal-attack damage is computed as a separate pass after the burst-cycle
simulation finishes: burst_cycle's hooks already populate the EffectRegistry
with every buff across the whole fight (each Effect carries its own
applied_at/duration), so querying registry.total_for(stat, target, shot_time)
for a shot time anywhere in the fight is correct regardless of processing
order - no need to interleave shot generation with the burst-cycle hooks.

Core hit damage is a uniform +100% (200% total, i.e. exactly doubles a hit
with no other modifiers) across every weapon type, per Fienn's direct
in-game/ShiftyPad tooltip check - this corrects an earlier "1/1.5" figure
pulled from a summarized fetch of the nikke.gg formula page, which turned
out to be an unreliable paraphrase. `core_hittable` toggles it for the
whole simulation (some raid bosses have an exploitable core, some don't);
per-skill/per-shot core-hit eligibility isn't modeled, so this applies
uniformly to every damage instance for now.

reload_speed_percent and max_ammo_percent effects (from overload options or
skills) are read live from the registry at each magazine's start/reload
moment, so temporary buffs correctly speed up reloads or grow magazines
only while active - see attack_rate's docstring for exactly when each is
evaluated.

`boss_element` (optional) applies NIKKE's +10% elemental advantage to every
damage instance from an attacker whose element beats the boss's; None means
no element is considered (neutral for everyone).

Crit is modeled as expected value, not per-hit RNG: every hit's damage is
scaled by 1 + crit_rate*(0.5 + crit damage sources), where crit_rate is the
15% base plus any crit_rate buffs (capped at 100%). So crit rate AND crit
damage buffs both raise output, which is what most Burst-1 supporters exist
to do. base_crit_rate can be overridden (e.g. 0.0 in tests that want
deterministic non-crit numbers).

Known simplifications: a slug missing from `weapon_stats` contributes no
normal-attack damage (e.g. while that character's weapon data hasn't been
entered yet); pierce_damage_up is applied to every hit as a general damage-up
term (the formula's Damage Up bucket), not gated to actual pierce hits, since
per-hit pierce flags aren't modeled.

Some passives "Deal X% of final ATK as damage" on a trigger OTHER than the
caster's own burst (e.g. Brid: Silent Track's Ignition Sequence, which fires
on full_burst_enter regardless of who bursts) - this can't use
`burst_damage_percents`, which is tied to `own_burst_activate`. A skill rule
emits an `"instant_damage_percent"` Pulse instead (see
`_helpers.instant_nuke_pulse_rule`); `drain_instant_damage` drains it after
every trigger fire (battle_start, own_burst_activate, full_burst_enter,
full_burst_end) and computes the damage the same way as a burst nuke, using
the pulse's source_slug as caster. Logged with `source="instant_nuke"`.

Some skills react to a DIFFERENT unit's burst (e.g. Prika's Encore fires when
Mint's Sing Along takes effect - i.e. when Mint bursts). After a unit's burst
tier fires, `on_tier_fire` records the bursting slug on the context
(`last_burst_slug`) and fires an `ally_burst_activate` trigger across every
unit's rules, so a reacting rule can gate on `ally_bursted("mint")`. Fired after
the burster's own own_burst_activate, so the reacting rule sees the burst's own
effects already applied. These rules must be buff appliers (no instant nukes),
like periodic_rules.

Some skills fire repeatedly on their OWN fixed cooldown, entirely independent
of the burst cycle and every other trigger (e.g. Helm: Aquamarine's Aegis
Cannon Suppression Fire, a "Cooldown: 4s" active skill separate from her
Burst tab, that auto-fires throughout the whole fight). `periodic_nukes` is a
`{slug: {"cooldown": seconds, "percent": float}}` map; each entry ticks at
t=cooldown, 2*cooldown, ... up to fight_duration, computing damage the same
way as a burst nuke (using the tick time to read live buffs, so it correctly
reflects whatever's active at that instant). Logged with `source="periodic"`.
Computed as a pass after the burst-cycle simulation completes, same as the
normal-attack pass - order doesn't matter since it only reads the registry's
already-populated Effects at arbitrary times, like every other post-pass here.
"""
from app.attack_rate import CHARGE_WEAPONS, generate_shot_times, last_bullet_shot_times
from app.burst_cycle import simulate_burst_cycle
from app.damage_formula import calculate_damage
from app.effects import Effect, EffectRegistry, _matches_scope
from app.elements import element_multiplier
from app.squad_engine import SquadContext, SquadMember, fire_trigger

CORE_HIT_BONUS = 1.0
BASE_CRIT_RATE = 0.15


def _resource_fill_times(
    fill, shot_times, core_hittable, fight_duration, full_burst_windows=(), own_burst_times=(),
    last_bullet_times=(),
):
    """The times a resource gains a stack, from its fill spec and the owner's
    shot timeline. ("per_shot_every", N) fires at the owner's Nth, 2Nth, ... shot
    (count = index+1, matching per_shot_rules' "every N").
    ("per_shot_every_core", core_n, noncore_n) picks core_n on a core-hittable
    boss and noncore_n otherwise - for a skill whose fill rate differs between
    hitting the core and not (e.g. Guillotine's EXP). ("periodic", interval)
    fires at t=interval, 2*interval, ... up to fight_duration, independent of
    the owner's shots (e.g. Cinderella's Beautiful, which ticks on a fixed timer
    while her decoy is up from battle start). ("per_shot_every_during_full_burst",
    N) is like "per_shot_every" but counts only shots whose time falls within a
    Full Burst window (e.g. Soda's Golden Chip, "every 3 normal attacks during
    Full Burst") - shots outside any window are dropped before the "every Nth"
    count, not just skipped in place. ("per_shot_every_during_own_status_window",
    N, window_duration) is the same idea but the window is anchored to the
    OWNER'S OWN burst-fire times instead of the global Full Burst window (e.g.
    Asuka's Anti A.T. Field, "every 10 shots while in Annihilation State" - a
    9s window that starts at HER burst, not the squad's Full Burst window).
    ("on_last_bullet",) fires whenever the owner's OWN shot empties its
    magazine (e.g. Julia's Crescendo, "when the last bullet hits the target"
    - see `attack_rate.last_bullet_shot_times`), not on any fixed shot count
    or window."""
    kind = fill[0]
    if kind == "per_shot_every":
        n = fill[1]
        return [t for i, t in enumerate(shot_times) if (i + 1) % n == 0]
    if kind == "per_shot_every_core":
        n = fill[1] if core_hittable else fill[2]
        return [t for i, t in enumerate(shot_times) if (i + 1) % n == 0]
    if kind == "periodic":
        interval = fill[1]
        ticks = []
        tick = interval
        while tick <= fight_duration:
            ticks.append(tick)
            tick += interval
        return ticks
    if kind == "per_shot_every_during_full_burst":
        n = fill[1]
        in_window = [t for t in shot_times if any(start <= t < end for start, end in full_burst_windows)]
        return [t for i, t in enumerate(in_window) if (i + 1) % n == 0]
    if kind == "per_shot_every_during_own_status_window":
        n, window_duration = fill[1], fill[2]
        windows = [(bt, bt + window_duration) for bt in own_burst_times]
        in_window = [t for t in shot_times if any(start <= t < end for start, end in windows)]
        return [t for i, t in enumerate(in_window) if (i + 1) % n == 0]
    if kind == "on_last_bullet":
        return sorted(last_bullet_times)
    raise ValueError(f"unknown resource fill kind: {kind}")


def _resolve_squad_burst_cycle_resource(spec, slug, events, context):
    """Fills/resets a resource driven by GLOBAL burst-cycle events (not the
    owner's own shots), where the fill is CONDITIONAL on the resource's own
    running value - e.g. Maiden's MP: "+1 if MP==0" whenever ANY squad
    tier-1 fires, "+1 if MP>=1" on entering Full Burst. This can't be a flat
    deterministic schedule (see `_resource_fill_times`) because whether a
    fill applies depends on state that changes as events are processed, so
    it's walked as a genuine sequential replay instead.

    fill = ("squad_burst_cycle_conditional", rules), rules a list of
    (event_matcher, condition_fn, delta): event_matcher(event) -> bool tests
    one of simulate_burst_cycle's own events (e.g. {"type": "burst", "tier":
    1, ...} or {"type": "full_burst_start", ...}); condition_fn(count) -> bool
    gates the fill on the CURRENT running value.

    Only `spec.resets` with trigger "own_burst" is supported (checked inline
    against each event's own slug, at the exact point it occurs in `events` -
    not merged in afterward) - "battle_start" is applied once before the
    walk begins. This preserves exact same-instant ordering from `events`
    (e.g. the owner's own burst always precedes full_burst_start, per the
    strict burst1->burst2->burst3->full-burst rule), which a resource whose
    fill depends on that exact ordering needs. `spec.buffs` isn't supported
    for this fill kind (no current consumer needs a continuous buff off a
    squad-burst-cycle-driven resource)."""
    rules = spec.fill[1]
    running = 0.0
    for reset_spec in spec.resets:
        if reset_spec["trigger"] == "battle_start":
            context.reset_resource(slug, spec.name, 0.0, running, reset_spec["value"])
            running = min(spec.cap, reset_spec["value"])
    own_burst_reset_value = next(
        (r["value"] for r in spec.resets if r["trigger"] == "own_burst"), None
    )
    for event in events:
        for matcher, condition, delta in rules:
            if matcher(event) and condition(running):
                running = min(spec.cap, running + delta)
                context.fill_resource(slug, spec.name, delta, event["time"])
        if own_burst_reset_value is not None and event.get("type") == "burst" and event.get("slug") == slug:
            pre_value = running
            running = own_burst_reset_value
            context.reset_resource(slug, spec.name, event["time"], pre_value, running)


# Each damage instance has a damage_type. The type-specific Damage-Up buckets
# below are read from the registry ONLY for instances of that type, so a buff
# like "Sustained Damage +X%" only boosts sustained-typed damage (not every
# hit). The always-on buckets (attack_damage_up, pierce/parts/damage_taken) are
# applied to every instance regardless of type - see _damage_instance. "attack"
# is the default type and adds no type-specific bucket, so untyped instances
# are computed exactly as before.
_TYPE_BUCKETS = {
    "attack": [],
    "sustained": ["sustained_damage_up"],
    "distributed": ["distributed_damage_up"],
    "true": ["true_damage_up"],
    "projectile_explosion": ["projectile_explosion_damage_up"],
}


def simulate_raid(
    deck,
    rules_by_slug,
    burst_damage_percents,
    base_stats,
    enemy_def,
    gauge_charge_time,
    fight_duration,
    mode="auto",
    core_hittable=False,
    weapon_stats=None,
    boss_element=None,
    base_crit_rate=BASE_CRIT_RATE,
    periodic_nukes=None,
    burst_damage_types=None,
    periodic_rules=None,
    per_shot_rules=None,
    resource_specs=None,
    burst_hit_counts=None,
    resource_scaled_nukes=None,
    resource_gated_buffs=None,
    dynamic_hit_count_nukes=None,
):
    weapon_stats = weapon_stats or {}
    periodic_nukes = periodic_nukes or {}
    burst_damage_types = burst_damage_types or {}
    periodic_rules = periodic_rules or {}
    per_shot_rules = per_shot_rules or {}
    resource_specs = resource_specs or {}
    burst_hit_counts = burst_hit_counts or {}
    resource_scaled_nukes = resource_scaled_nukes or {}
    resource_gated_buffs = resource_gated_buffs or {}
    dynamic_hit_count_nukes = dynamic_hit_count_nukes or {}
    context = SquadContext(
        [SquadMember(m["slug"], m["burst_tier"], m["element"]) for m in deck],
        base_atk={m["slug"]: base_stats[m["slug"]]["atk"] for m in deck},
        boss_element=boss_element,
    )
    registry = EffectRegistry()
    # Damage is RECORDED as events during phase 1 (buffs are applied but no
    # damage is computed yet), then computed in a single phase-2 pass once EVERY
    # buff/debuff is in the registry - so e.g. a per-shot squad debuff applied
    # mid-fight correctly raises a burst nuke that fired earlier. Effects are
    # replay-safe (added with applied_at >= their time; truncate_open_ended
    # mutates in place), so deferring computation never changes an existing
    # value - only lets late buffs reach instances they should have.
    damage_events = []
    member_by_slug = {m["slug"]: m for m in deck}

    def target_for(slug):
        return {"slug": slug, "element": member_by_slug[slug]["element"]}

    def crit_rate_for(target, time):
        return min(1.0, base_crit_rate + registry.total_for("crit_rate", target, time))

    def element_bonus_for(slug):
        if boss_element is None:
            return 1.0
        return element_multiplier(member_by_slug[slug]["element"], boss_element)

    def _damage_instance(
        slug, percent, time, damage_type="attack", extra_charge_bonus=0.0, extra_flat_atk=0.0,
        full_burst_bonus_eligible=False,
    ):
        target = target_for(slug)
        # True Damage ignores enemy DEF (nikke.gg glossary).
        instance_enemy_def = 0 if damage_type == "true" else enemy_def
        # Full Burst Bonus only applies to damage a unit's skill text describes
        # as "additional damage" (Fienn, 2026-07-12) - i.e. damage actually
        # computed later than cast time, which can land inside a Full Burst
        # window. `full_burst_bonus_eligible` is an explicit per-instance opt-in
        # (set by the caller from that skill-text signal); ordinary cast-time
        # damage never sets it, so this stays inert for every other unit.
        in_full_burst = full_burst_bonus_eligible and any(
            start <= time < end for start, end in full_burst_windows
        )
        terms = dict(
            atk=base_stats[slug]["atk"],
            attack_coefficient=percent / 100,
            enemy_def=instance_enemy_def,
            atk_percent=registry.total_for("atk_percent", target, time),
            flat_atk=registry.total_for("flat_atk", target, time) + extra_flat_atk,
            other_elemental_bonus=registry.total_for("other_elemental_bonus", target, time),
            other_critical_damage_sources=registry.total_for("other_critical_damage_sources", target, time),
            crit_rate=crit_rate_for(target, time),
            core_hit_bonus=CORE_HIT_BONUS if core_hittable else 0.0,
            other_core_damage_sources=(
                registry.total_for("other_core_damage_sources", target, time) if core_hittable else 0.0
            ),
            full_burst_bonus=1.0 if in_full_burst else 0.0,
            element_multiplier=element_bonus_for(slug),
            charge_damage_bonus=registry.total_for("charge_damage_bonus", target, time) + extra_charge_bonus,
            attack_damage_up=registry.total_for("attack_damage_up", target, time),
            damage_to_parts_up=registry.total_for("damage_to_parts_up", target, time),
            pierce_damage_up=registry.total_for("pierce_damage_up", target, time),
            damage_taken_up=registry.total_for("damage_taken_up", target, time),
        )
        # Type-specific Damage-Up buckets apply only to instances of that type.
        for bucket in _TYPE_BUCKETS[damage_type]:
            terms[bucket] = registry.total_for(bucket, target, time)
        return calculate_damage(**terms)

    def normal_attack_type(slug, weapon, target, time):
        # A skill can convert a unit's normal attacks to a damage type for a
        # window (e.g. Takina Inoue's burst: "normal attacks deal true damage").
        if registry.total_for("normal_attacks_deal_true", target, time) > 0:
            return "true"
        # Otherwise a rocket launcher's normal attacks are projectile explosions.
        if weapon["weapon"] == "RL":
            return "projectile_explosion"
        return "attack"

    def record(
        slug, percent, time, source, damage_type="attack",
        extra_charge_bonus=0.0, resource_gate=None, extra_flat_atk=0.0,
        full_burst_bonus_eligible=False,
    ):
        damage_events.append({
            "slug": slug, "percent": percent, "time": time, "source": source,
            "damage_type": damage_type, "extra_charge_bonus": extra_charge_bonus,
            "resource_gate": resource_gate, "extra_flat_atk": extra_flat_atk,
            "full_burst_bonus_eligible": full_burst_bonus_eligible,
        })

    def _resolve_percent(ev):
        # A resource-scaled/gated nuke's recorded percent is a BASE value; its
        # real magnitude depends on the resource's count at the event's OWN
        # time, which isn't known until the resolution pass runs (after the
        # burst cycle that records this event) - so it's resolved here, in
        # phase 2, exactly like a deferred buff (see module docstring).
        if ev["resource_gate"] is None:
            return ev["percent"]
        name, cap, lifetime, scale_fn = ev["resource_gate"]
        count = context.resource_count(ev["slug"], name, ev["time"], cap, lifetime)
        return ev["percent"] * scale_fn(count)

    def drain_instant_damage(time):
        # A passive that deals damage on a trigger OTHER than the caster's own
        # burst (e.g. Brid: Silent Track's Ignition Sequence, on full_burst_enter)
        # can't use burst_damage_percents (tied to own_burst_activate). It emits
        # an "instant_damage_percent" pulse instead; drained here after every
        # trigger fire, recorded as a nuke computed later like a burst nuke.
        for pulse in registry.drain_pulses("instant_damage_percent"):
            record(
                pulse.source_slug, pulse.value, time, "instant_nuke",
                full_burst_bonus_eligible=pulse.full_burst_bonus_eligible,
            )

    def on_battle_start(time):
        fire_trigger("battle_start", rules_by_slug, context, registry, time)
        drain_instant_damage(0.0)

    def on_tier_fire(tier, slug, time):
        context.burst_used_this_cycle.add(slug)
        context.last_burst_slug = slug
        context.record_burst_time(slug, time)
        fire_trigger("own_burst_activate", {slug: rules_by_slug.get(slug, [])}, context, registry, time)
        drain_instant_damage(time)
        # Let other units react to THIS unit's burst (e.g. Prika's Encore firing
        # on Mint's Sing Along). Fired across every unit's rules AFTER the
        # burster's own own_burst_activate, so a reacting rule sees the burst's
        # own effects already applied. ally_burst_activate rules must be buff
        # appliers (no instant nukes), like periodic_rules.
        fire_trigger("ally_burst_activate", rules_by_slug, context, registry, time)

        # A burst-fired nuke whose magnitude depends on a named resource's
        # count - a single gated/scaled additional hit (tick_count=1), or a
        # repeating tick (e.g. a Hero-Level-scaled DoT) where each tick reads
        # the count at ITS OWN time, not frozen at burst-fire time. Independent
        # of the plain burst_damage_percents nuke below (a unit can have
        # either, both, or neither).
        for spec in resource_scaled_nukes.get(slug, []):
            # "resource" is optional: a plain repeating DoT with no resource
            # scaling (e.g. Mana's Fatal Error!) reuses this same tick_count/
            # tick_interval loop, just with no resource_gate to resolve later.
            resource_gate = (
                (spec["resource"], spec["cap"], spec.get("lifetime"), spec["scale_fn"])
                if spec.get("resource") is not None else None
            )
            for i in range(spec["tick_count"]):
                tick_time = time + i * spec["tick_interval"]
                record(
                    slug, spec["base_percent"], tick_time, "resource_scaled_nuke",
                    damage_type=spec.get("damage_type", "attack"),
                    resource_gate=resource_gate,
                    full_burst_bonus_eligible=spec.get("full_burst_bonus_eligible", False),
                )

        percent = burst_damage_percents.get(slug)
        if not percent:
            return
        # A burst that "attacks sequentially N times" deals N SEPARATE hits, not
        # one hit at N*percent - defense is a flat per-hit subtraction (see
        # damage_formula), so splitting into hits changes the total whenever
        # enemy_def > 0. All N hits land at the same instant.
        for _ in range(burst_hit_counts.get(slug, 1)):
            record(slug, percent, time, "burst", damage_type=burst_damage_types.get(slug, "attack"))

    def on_full_burst_enter(time):
        fire_trigger("full_burst_enter", rules_by_slug, context, registry, time)
        drain_instant_damage(time)

    def cdr_targets(pulse):
        if pulse.scope == "self":
            return [pulse.source_slug]
        if pulse.scope == "squad":
            return [m["slug"] for m in deck]
        if pulse.scope.startswith("element:"):
            element = pulse.scope.split(":", 1)[1]
            return [m["slug"] for m in deck if m["element"] == element]
        raise ValueError(f"unknown pulse scope: {pulse.scope}")

    def on_full_burst_end(time):
        fire_trigger("full_burst_end", rules_by_slug, context, registry, time)
        drain_instant_damage(time)
        context.burst_used_this_cycle.clear()
        reductions = {}
        for pulse in registry.drain_pulses("burst_cooldown_reduction_sec"):
            for slug in cdr_targets(pulse):
                reductions[slug] = reductions.get(slug, 0.0) + pulse.value
        return reductions

    # A Skill 1/2 with its own cooldown first fires at t=cooldown and repeats
    # (a universal battle-system rule, not at battle start). These rules apply
    # buffs/debuffs, which are INPUTS to damage - so unlike periodic_nukes (a
    # post-pass), they must populate the registry BEFORE the burst cycle
    # computes any nuke that should reflect them. Effects are replay-safe, so
    # pre-adding them at t=cooldown, 2*cooldown, ... is correct for every later
    # read. Fired against the initial context (no burst-cycle state yet), so
    # periodic rules must be stateless buff appliers.
    for slug, groups in periodic_rules.items():
        for cooldown, rules in groups:
            tick = cooldown
            while tick < fight_duration:
                for rule in rules:
                    if rule.condition(context, slug):
                        rule.action(context, slug, tick, registry)
                tick += cooldown

    events = simulate_burst_cycle(
        deck,
        gauge_charge_time,
        fight_duration,
        mode,
        on_battle_start=on_battle_start,
        on_tier_fire=on_tier_fire,
        on_full_burst_enter=on_full_burst_enter,
        on_full_burst_end=on_full_burst_end,
    )

    # Full Burst windows [start, end) from the burst-cycle's own event log, so
    # a resource fill gated to "during Full Burst" (e.g. Soda's Golden Chip)
    # can filter shots against them without re-deriving burst timing itself.
    full_burst_windows = list(zip(
        (e["time"] for e in events if e["type"] == "full_burst_start"),
        (e["time"] for e in events if e["type"] == "full_burst_end"),
    ))

    shot_times_by_slug = {}
    last_bullet_times_by_slug = {}
    for slug, weapon in weapon_stats.items():
        target = target_for(slug)
        is_charge_weapon = weapon["weapon"] in CHARGE_WEAPONS
        max_ammo_percent_at = lambda t, target=target: registry.total_for("max_ammo_percent", target, t)
        reload_speed_percent_at = lambda t, target=target: registry.total_for(
            "reload_speed_percent", target, t
        )
        attack_speed_percent_at = lambda t, target=target: registry.total_for(
            "attack_speed_percent", target, t
        )
        charge_speed_percent_at = lambda t, target=target: registry.total_for(
            "charge_speed_percent", target, t
        )
        shot_times = generate_shot_times(
            weapon["weapon"],
            weapon["max_ammo"],
            weapon["reload_time"],
            weapon["charge_time"],
            fight_duration,
            max_ammo_percent_at=max_ammo_percent_at,
            reload_speed_percent_at=reload_speed_percent_at,
            attack_speed_percent_at=attack_speed_percent_at,
            charge_speed_percent_at=charge_speed_percent_at,
        )
        extra_charge_bonus = weapon["charge_damage_percent"] / 100 - 1 if is_charge_weapon else 0.0
        # "For N round(s)" (bullet-count) buffs expire when the affected ally
        # fires N normal attacks, not after a fixed time. Now that this unit's shot
        # timeline is known, turn each grant that targets it into a concrete Effect
        # whose window covers exactly its next N shots after the grant (from the
        # first covered shot up to the next uncovered shot / fight end), so phase 2
        # applies the buff to precisely those shots and nothing after. A squad grant
        # is consumed independently by each ally's own shots (one Effect per unit).
        for grant in registry.round_grants():
            if grant.scope == "self":
                covers_unit = grant.source_slug == slug
            else:
                covers_unit = _matches_scope(grant.scope, target)
            if not covers_unit:
                continue
            covered = [t for t in shot_times if t >= grant.granted_at][: grant.shots]
            if not covered:
                continue
            after_covered = [t for t in shot_times if t > covered[-1]]
            window_end = after_covered[0] if after_covered else fight_duration
            registry.add(
                Effect(grant.stat, grant.value, f"slugs:{slug}", window_end - covered[0], grant.source_slug),
                applied_at=covered[0],
            )
        # Per-shot triggers count this unit's shots and fire at a threshold
        # ("after N": once at the Nth shot; "every N": at every Nth) or on
        # the shot that empties its magazine ("last_bullet", threshold
        # unused - gap #1's residual variant, e.g. Julia's Crescendo). The
        # window-gated modes ("every_during_full_burst" / "every_during_own_
        # status_window") count only shots inside a window before the "every
        # Nth" step, exactly like the same-named resource fills (gap #7 - a
        # buff/nuke fired directly on the in-window count, e.g. Soda's Lucky
        # Golden Chip, Asuka's Anti A.T. Field nuke). Their rules apply buffs
        # to the registry (seen by phase 2 at each shot's time) or emit an
        # instant_damage_percent pulse recorded as a per-shot nuke. Rules must
        # be stateless and must not change shot generation (reload/ammo), which
        # is already fixed for this unit here.
        unit_per_shot = per_shot_rules.get(slug, [])
        # Also needed by an "on_last_bullet" resource fill (below, resolved in
        # a later pass) - computed once here and cached so both consumers
        # share identical magazine boundaries.
        needs_last_bullets = any(mode == "last_bullet" for _, mode, _ in unit_per_shot) or any(
            spec.fill[0] == "on_last_bullet" for spec in resource_specs.get(slug, [])
        )
        last_bullets = (
            last_bullet_shot_times(
                weapon["weapon"], weapon["max_ammo"], weapon["reload_time"], weapon["charge_time"],
                fight_duration, max_ammo_percent_at, reload_speed_percent_at,
                attack_speed_percent_at, charge_speed_percent_at,
            )
            if needs_last_bullets else set()
        )
        last_bullet_times_by_slug[slug] = last_bullets
        # The window-gated modes fire on the same in-window shot times a
        # matching resource fill would pick, so reuse `_resource_fill_times`'
        # window filter. "every_during_full_burst" carries N in `threshold`;
        # "every_during_own_status_window" carries (N, window_duration).
        own_burst_times = context.burst_times.get(slug, [])
        window_fire_times = {}
        for idx, (threshold, mode, _rules) in enumerate(unit_per_shot):
            if mode == "every_during_full_burst":
                window_fire_times[idx] = set(_resource_fill_times(
                    ("per_shot_every_during_full_burst", threshold), shot_times,
                    core_hittable, fight_duration, full_burst_windows,
                ))
            elif mode == "every_during_own_status_window":
                n, window_duration = threshold
                window_fire_times[idx] = set(_resource_fill_times(
                    ("per_shot_every_during_own_status_window", n, window_duration), shot_times,
                    core_hittable, fight_duration, full_burst_windows, own_burst_times,
                ))
        for shot_index, shot_time in enumerate(shot_times):
            count = shot_index + 1
            for idx, (threshold, mode, rules) in enumerate(unit_per_shot):
                fires = (
                    (mode == "after" and count == threshold)
                    or (mode == "every" and count % threshold == 0)
                    or (mode == "last_bullet" and shot_time in last_bullets)
                    or (idx in window_fire_times and shot_time in window_fire_times[idx])
                )
                if fires:
                    for rule in rules:
                        if rule.condition(context, slug):
                            rule.action(context, slug, shot_time, registry)
                    for pulse in registry.drain_pulses("instant_damage_percent"):
                        record(
                            pulse.source_slug, pulse.value, shot_time, "per_shot_nuke",
                            full_burst_bonus_eligible=pulse.full_burst_bonus_eligible,
                        )
            damage_type = normal_attack_type(slug, weapon, target, shot_time)
            record(slug, weapon["damage_percent"], shot_time, "normal_attack",
                   damage_type=damage_type, extra_charge_bonus=extra_charge_bonus)
        shot_times_by_slug[slug] = shot_times

    # Resolve quantity-based resources (battery / ammo pouch / N-stack counter).
    # Each spec's fill schedule is deterministic (here: +amount every Nth of the
    # owner's shots), so its count is a function of time (context.resource_count).
    # Each derived buff is emitted as a STEP FUNCTION over the fill/expiry events:
    # at each event we add a delta Effect (duration=None) carrying the change in
    # value, so total_for's running sum equals value_fn(count) at every time -
    # permanent stacks ramp up (all-positive deltas that plateau at the cap) and
    # timed stacks also come back down (negative deltas as they expire). Runs
    # after the shot loop so every fill is known; before phase 2, so
    # record-then-compute lets these buffs reach damage recorded earlier.
    for slug, specs in resource_specs.items():
        shot_times = shot_times_by_slug.get(slug, [])
        for spec in specs:
            if spec.fill[0] == "squad_burst_cycle_conditional":
                _resolve_squad_burst_cycle_resource(spec, slug, events, context)
                continue
            fill_times = _resource_fill_times(
                spec.fill, shot_times, core_hittable, fight_duration, full_burst_windows,
                context.burst_times.get(slug, []), last_bullet_times_by_slug.get(slug, set()),
            )
            # Every per-shot fill grants exactly one stack. (A fill source that
            # grants more than one at a time - e.g. a battle-start +N - would
            # carry its own amount; none exists yet.)
            for ft in fill_times:
                context.fill_resource(slug, spec.name, 1, ft)

            # Resets (a resource SET to a fixed value rather than incremented,
            # e.g. Soda's Golden Chip consumed down to 17 on her own burst) are
            # collected from every reset spec and replayed in time order, so
            # each reset's pre-value correctly reflects fills AND any earlier
            # reset already applied.
            reset_events = []
            for reset_spec in spec.resets:
                if reset_spec["trigger"] == "battle_start":
                    reset_events.append((0.0, reset_spec["value"]))
                elif reset_spec["trigger"] == "own_burst":
                    reset_events.extend((rt, reset_spec["value"]) for rt in context.burst_times.get(slug, []))
                elif reset_spec["trigger"] == "own_burst_delayed":
                    # Resets `reset_spec["delay"]` seconds AFTER each own-burst
                    # fire, not at the burst itself - e.g. Asuka's Anti A.T.
                    # Field, cleared when Annihilation State ends (9s later),
                    # not when the burst that started it fires.
                    delay = reset_spec["delay"]
                    reset_events.extend(
                        (rt + delay, reset_spec["value"]) for rt in context.burst_times.get(slug, [])
                    )
                else:
                    raise ValueError(f"unknown resource reset trigger: {reset_spec['trigger']}")
            reset_events.sort(key=lambda e: e[0])
            for reset_time, post_value in reset_events:
                pre_value = context.resource_count(slug, spec.name, reset_time, spec.cap)
                context.reset_resource(slug, spec.name, reset_time, pre_value, post_value)
            reset_times = [rt for rt, _ in reset_events]

            for buff in spec.buffs:
                # NOT `events` - that name holds simulate_burst_cycle's own
                # event log (read by _resolve_squad_burst_cycle_resource for
                # OTHER slugs' resources processed later in this same loop);
                # shadowing it here corrupted that log for any
                # squad_burst_cycle_conditional resource resolved afterward
                # in the same simulate_raid call (only surfaced once a deck
                # combined a buffed resource with one, e.g. Asuka + Maiden
                # sharing Burst 3 - see test_interaction_asuka_maiden_shared_burst_tier.py).
                buff_step_times = set(fill_times) | set(reset_times)
                if buff.lifetime is not None:
                    buff_step_times |= {
                        ft + buff.lifetime for ft in fill_times if ft + buff.lifetime < fight_duration
                    }
                prev_value = 0.0
                for event_time in sorted(buff_step_times):
                    count = context.resource_count(slug, spec.name, event_time, spec.cap, buff.lifetime)
                    value = buff.value_fn(count)
                    if value != prev_value:
                        registry.add(
                            Effect(buff.stat, value - prev_value, buff.scope, None, slug),
                            applied_at=event_time,
                        )
                        prev_value = value

    # A burst-fired buff gated on (or scaled by) a named resource's count AT
    # THE BURST'S OWN TIME - e.g. Soda's ATK+65.25%/15s if she had >=30 Golden
    # Chip stacks right before her burst consumed it down to 17. Processed
    # here (not at on_tier_fire, where the burst is actually recorded)
    # because the resource's fills/resets from the loop above aren't known
    # until now - same ordering reason as resource_scaled_nukes' deferred
    # percent, but a buff has no "phase 2" to defer to, so it's resolved here
    # instead, using context.burst_times (already recorded during the burst
    # cycle) for each of the owner's own burst-fire times.
    for slug, specs in resource_gated_buffs.items():
        for spec in specs:
            for burst_time in context.burst_times.get(slug, []):
                if spec.get("use_pre_reset"):
                    count = context.resource_count_before_reset(slug, spec["resource"], burst_time)
                    if count is None:
                        continue
                else:
                    count = context.resource_count(
                        slug, spec["resource"], burst_time, spec["cap"], spec.get("lifetime")
                    )
                if spec["gate_fn"](count):
                    registry.add(
                        Effect(spec["stat"], spec["value"], spec["scope"], spec["duration"], slug),
                        applied_at=burst_time,
                    )

    # A burst-fired nuke whose HIT COUNT (not just its percent) is itself a
    # resource's value at burst time - e.g. Maiden's Diamond Dust, "attacks
    # repeatedly based on current MP". Reads the PRE-reset count (the resource
    # is drained by this same burst) at each of the owner's own burst times,
    # recording that many identical damage events. `extra_flat_atk_percent_of_
    # max_hp` (optional) adds a percentage of the owner's Max HP directly into
    # THIS nuke's own flat_atk term (e.g. "1372.8% of the sum of 10% Max HP and
    # ATK") without leaking into any other damage instance from the same slug.
    for slug, specs in dynamic_hit_count_nukes.items():
        for spec in specs:
            extra_flat_atk = spec.get("extra_flat_atk_percent_of_max_hp", 0.0) * base_stats[slug]["max_hp"]
            # `fire_delay` (optional): the nuke fires this many seconds AFTER
            # the burst, not at burst time itself - e.g. Asuka's Annihilation,
            # which lands when Annihilation State ends (9s later). The hit
            # count is read (and the resource reset, if any) at that same
            # delayed instant, matching `own_burst_delayed` above.
            delay = spec.get("fire_delay", 0.0)
            for burst_time in context.burst_times.get(slug, []):
                fire_time = burst_time + delay
                hit_count = context.resource_count_before_reset(slug, spec["resource"], fire_time)
                if hit_count is None:
                    continue
                for _ in range(int(hit_count)):
                    record(
                        slug, spec["base_percent"], fire_time, "dynamic_hit_count_nuke",
                        damage_type=spec.get("damage_type", "attack"), extra_flat_atk=extra_flat_atk,
                        full_burst_bonus_eligible=spec.get("full_burst_bonus_eligible", False),
                    )

    for slug, spec in periodic_nukes.items():
        cooldown = spec["cooldown"]
        percent = spec["percent"]
        damage_type = spec.get("damage_type", "attack")
        tick = cooldown
        while tick < fight_duration:
            record(slug, percent, tick, "periodic", damage_type=damage_type)
            tick += cooldown

    # Phase 2: now that every buff/debuff is in the registry, compute each
    # recorded damage event against the final registry (each read at its own
    # time is replay-safe).
    damage_log = [
        {
            "slug": ev["slug"],
            "time": ev["time"],
            "damage": _damage_instance(
                ev["slug"], _resolve_percent(ev), ev["time"],
                damage_type=ev["damage_type"], extra_charge_bonus=ev["extra_charge_bonus"],
                extra_flat_atk=ev["extra_flat_atk"],
                full_burst_bonus_eligible=ev["full_burst_bonus_eligible"],
            ),
            "source": ev["source"],
            "damage_type": ev["damage_type"],
        }
        for ev in damage_events
    ]

    return {
        "total_damage": sum(entry["damage"] for entry in damage_log),
        "damage_log": damage_log,
        "events": events,
    }
