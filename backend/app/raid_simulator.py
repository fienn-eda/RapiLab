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
A spec may opt in with `"full_burst_bonus_eligible": True` - the repeating-
tick-DoT rule (Fienn, 2026-07-16): each tick computes at its own time, so
ticks landing inside a Full Burst window get the bonus. Absent/False keeps
the pre-existing no-bonus behavior, so units encoded before this field are
unchanged until deliberately flagged.
A spec may also carry `"during_full_burst": True` (ticks only inside each
Full Burst window, anchored to the window's start - gap #6), `"hit_count": N`
(each tick records N separate hits, same rationale as burst_hit_counts), and
`"own_burst_interval": (interval, duration)` (a window whose start falls
inside [own burst, +duration) ticks at `interval` instead of `cooldown`).
Defaults keep every existing spec identical.
Computed as a pass after the burst-cycle simulation completes, same as the
normal-attack pass - order doesn't matter since it only reads the registry's
already-populated Effects at arbitrary times, like every other post-pass here.

Both `periodic_nukes` values and `resource_scaled_nukes` specs may carry an
optional `"requires_part_destructible": True | False` to fire only on one
side of a boss-profile flag (e.g. Ark Ranger Black's floor DoT vs. ceiling
DoT modeling the same battery-transformation state two different ways);
absent field = always fires, matching every existing spec's behavior.
"""
from app.attack_rate import generate_segmented_shots
from app.burst_cycle import simulate_burst_cycle
from app.damage_formula import calculate_damage
from app.effects import Effect, EffectRegistry, _matches_scope
from app.elements import element_multiplier
from app.squad_engine import SquadContext, SquadMember, fire_trigger

# How far past a window's end an "after this window ends" event is placed, so
# it orders after anything landing on the boundary instant itself.
AFTER_WINDOW_EPSILON = 1e-3

CORE_HIT_BONUS = 1.0
BASE_CRIT_RATE = 0.15

# A `burst_anchored_buffs` duration meaning "hold until this unit's next own
# burst" (a state a burst enters and only the next burst clears), as opposed to
# a fixed number of seconds.
UNTIL_NEXT_OWN_BURST = "until_next_own_burst"


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
    if kind == "per_shot_every_outside_full_burst":
        n = fill[1]
        # Closed on the right: a shot landing exactly at a Full Burst window's
        # end still belongs to the burst moment, not "outside" it. Left open
        # (< end) would make outside-FB firing depend on which side of the
        # float boundary a coincident shot rounds to (e.g. a transform tick
        # nominally at burst+duration == FB end).
        out_of_window = [
            t for t in shot_times if not any(start <= t <= end for start, end in full_burst_windows)
        ]
        return [t for i, t in enumerate(out_of_window) if (i + 1) % n == 0]
    if kind == "on_last_bullet":
        return sorted(last_bullet_times)
    if kind == "at_battle_start":
        return [0.0]
    if kind == "on_full_burst_end_after_own_burst":
        # Mihara's Restraint Chains: re-banked when Full Burst ends "if this
        # unit has just used her Burst Skill", and spent whole just AFTER that
        # ("풀 버스트 타임 종료 후"). The later Burst-Stage-3 discharge trigger
        # then always finds an empty bank, so this is the only recurring
        # discharge in a raid. The nudge past the window's end is what the
        # skill text says AND what makes the discharge survive a resource
        # reset landing on that same instant (Bonding Pain cancelling the
        # stacks it just detonated) - resource_count discards fills recorded
        # at or before its baseline reset.
        times = []
        for burst_time in own_burst_times:
            end = next((e for s, e in full_burst_windows if s <= burst_time <= e), None)
            if end is not None and end + AFTER_WINDOW_EPSILON not in times:
                times.append(end + AFTER_WINDOW_EPSILON)
        return sorted(times)
    raise ValueError(f"unknown resource fill kind: {kind}")


def _fill_sources(fill):
    """A resource's `fill` is either ONE fill spec (granting 1 stack a time,
    the shape every pre-existing consumer uses) or a list of (fill spec,
    amount) pairs for a resource fed by several sources at different rates -
    e.g. Mihara's Ensnaring Chains, +10 per chain discharge and +1 per 40
    normal attacks during Full Burst."""
    if isinstance(fill, list):
        return fill
    return [(fill, 1)]


def _sequence_fire_rules(spec, stage_rules, shot_times, own_burst_times):
    """gap #10 (Scarlet's Fleetly Fading Breakthrough): one running shot
    counter walks a staged requirement table - stage k fires its rules once
    the count reaches spec["requirements"][k], and after the last stage the
    count resets and the cycle restarts. Inside the owner's own-burst window
    (spec["own_burst_window"] = (duration, alt_requirements), e.g. Scarlet's
    burst "Changes Full Charge attack count required for Skill 1 to 1/2/3 for
    10 sec") the requirement table is swapped in place; the running count and
    stage CARRY OVER across the boundary (Fienn 2026-07-18) - a stage fires
    once count >= the ACTIVE requirement for it, so progress made under one
    table is never lost under the other. At most one stage fires per shot
    ("Only one effect is triggered at a time"). Returns {shot_time: rules}."""
    base_reqs = spec["requirements"]
    override = spec.get("own_burst_window")
    windows = ()
    override_reqs = base_reqs
    if override:
        duration, override_reqs = override
        windows = [(bt, bt + duration) for bt in own_burst_times]
    fires = {}
    count, stage = 0, 0
    for t in shot_times:
        count += 1
        reqs = override_reqs if any(start <= t < end for start, end in windows) else base_reqs
        if count >= reqs[stage]:
            fires[t] = stage_rules[stage]
            stage += 1
            if stage == len(base_reqs):
                count, stage = 0, 0
    return fires


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
    "projectile_attachment": ["projectile_attachment_damage_up"],
}

# Every registry stat phase-2 damage computation can read (_damage_instance,
# _normal_attack_percent). All are constant within one state epoch, so the
# whole bundle is resolved once per (target, epoch, registry version) - see
# _stat_bundle in simulate_raid. normal_attack_type reads its single stat
# directly - it runs in phase 1 where per-shot mutations churn the version,
# so bundle misses there cost more than they save.
_BUNDLE_STATS = (
    "enemy_def_percent", "atk_percent", "flat_atk", "other_elemental_bonus",
    "other_critical_damage_sources", "crit_rate", "other_core_damage_sources",
    "charge_damage_bonus", "attack_damage_up", "damage_to_parts_up",
    "pierce_damage_up", "damage_taken_up",
    "sustained_damage_up", "distributed_damage_up", "true_damage_up",
    "projectile_explosion_damage_up", "projectile_attachment_damage_up",
    "normal_attack_damage_multiplier",
)


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
    part_destructible=False,
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
    resource_fill_triggered_buffs=None,
    scheduled_nukes=None,
    weapon_mode_schedules=None,
    burst_anchored_buffs=None,
):
    weapon_stats = weapon_stats or {}
    weapon_mode_schedules = weapon_mode_schedules or {}
    periodic_nukes = periodic_nukes or {}
    burst_damage_types = burst_damage_types or {}
    periodic_rules = periodic_rules or {}
    per_shot_rules = per_shot_rules or {}
    resource_specs = resource_specs or {}
    burst_hit_counts = burst_hit_counts or {}
    resource_scaled_nukes = resource_scaled_nukes or {}
    resource_gated_buffs = resource_gated_buffs or {}
    dynamic_hit_count_nukes = dynamic_hit_count_nukes or {}
    resource_fill_triggered_buffs = resource_fill_triggered_buffs or {}
    scheduled_nukes = scheduled_nukes or {}
    context = SquadContext(
        [SquadMember(m["slug"], m["burst_tier"], m["element"], m.get("weapon")) for m in deck],
        base_atk={m["slug"]: base_stats[m["slug"]]["atk"] for m in deck},
        boss_element=boss_element,
        part_destructible=part_destructible,
        core_hittable=core_hittable,
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

    stat_bundles = {}

    def _stat_bundle(slug, time):
        # All _BUNDLE_STATS are constant within one state epoch, so resolve
        # them once per (target, epoch); the version key drops stale bundles
        # whenever the registry mutates, which keeps replay-late effects
        # behaving exactly as per-stat queries did.
        # Phase-2 only: do NOT call this from phase 1 - per-shot mutations
        # churn the version there, so every call misses, rebuilds the whole
        # bundle, and grows the memo (see the _BUNDLE_STATS note).
        target = target_for(slug)
        key = (slug, registry.state_epoch(target, time), registry.version)
        bundle = stat_bundles.get(key)
        if bundle is None:
            bundle = {stat: registry.total_for(stat, target, time) for stat in _BUNDLE_STATS}
            stat_bundles[key] = bundle
        return bundle

    def element_bonus_for(slug):
        if boss_element is None:
            return 1.0
        return element_multiplier(member_by_slug[slug]["element"], boss_element)

    def _damage_instance(
        slug, percent, time, damage_type="attack", extra_charge_bonus=0.0, extra_flat_atk=0.0,
        full_burst_bonus_eligible=False,
    ):
        bundle = _stat_bundle(slug, time)
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
            enemy_def_percent=bundle["enemy_def_percent"],
            atk_percent=bundle["atk_percent"],
            flat_atk=bundle["flat_atk"] + extra_flat_atk,
            other_elemental_bonus=bundle["other_elemental_bonus"],
            other_critical_damage_sources=bundle["other_critical_damage_sources"],
            crit_rate=min(1.0, base_crit_rate + bundle["crit_rate"]),
            core_hit_bonus=CORE_HIT_BONUS if core_hittable else 0.0,
            other_core_damage_sources=(
                bundle["other_core_damage_sources"] if core_hittable else 0.0
            ),
            full_burst_bonus=1.0 if in_full_burst else 0.0,
            element_multiplier=element_bonus_for(slug),
            charge_damage_bonus=bundle["charge_damage_bonus"] + extra_charge_bonus,
            attack_damage_up=bundle["attack_damage_up"],
            damage_to_parts_up=bundle["damage_to_parts_up"],
            pierce_damage_up=bundle["pierce_damage_up"],
            damage_taken_up=bundle["damage_taken_up"],
        )
        # Type-specific Damage-Up buckets apply only to instances of that type.
        for bucket in _TYPE_BUCKETS[damage_type]:
            terms[bucket] = bundle[bucket]
        return calculate_damage(**terms)

    def normal_attack_type(slug, weapon_type, time):
        # A skill can convert a unit's normal attacks to a damage type for a
        # window (e.g. Takina Inoue's burst: "normal attacks deal true damage").
        if registry.total_for("normal_attacks_deal_true", target_for(slug), time) > 0:
            return "true"
        # Otherwise a rocket launcher's normal attacks are projectile explosions.
        if weapon_type == "RL":
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
                damage_type=pulse.damage_type,
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
            # An Ark Ranger Black-style spec may be bracketed to only one side
            # of the boss's part_destructible flag (e.g. a burst-anchored
            # floor DoT vs. a whole-fight ceiling DoT modeling the same
            # transformation state differently); absent field = always fires.
            required = spec.get("requires_part_destructible")
            if required is not None and required != context.part_destructible:
                continue
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
    context.full_burst_windows = full_burst_windows

    # A buff a unit's own burst grants at an OFFSET from the burst, whose
    # duration may run "until that unit's NEXT own burst" rather than a fixed
    # number of seconds - Milk: Blooming Bunny's Embarrassment state, entered a
    # few seconds after her Overconfident immunity lapses and cleared only by
    # her next burst (Fienn, 2026-07-20).
    #
    # Resolved here rather than from an `own_burst_activate` rule because "until
    # the next own burst" is unknowable while the burst-cycle walk is still
    # running - the walk has not scheduled that burst yet. By this point
    # `context.burst_times` is complete. Placed BEFORE the shot loop so a buff
    # landed here is visible both to shot generation (max ammo / reload / cadence
    # callables) and to phase 2's damage bundles, unlike the resource-driven buff
    # passes further down which run after the timeline is already fixed.
    for slug, specs in (burst_anchored_buffs or {}).items():
        own_bursts = context.burst_times.get(slug, [])
        for spec in specs:
            offset = spec.get("offset", 0.0)
            for index, burst_time in enumerate(own_bursts):
                start = burst_time + offset
                if start >= fight_duration:
                    continue
                duration = spec["duration"]
                if duration == UNTIL_NEXT_OWN_BURST:
                    # The fight ending counts as the state's end, so the last
                    # window is trimmed rather than running past the sim.
                    next_burst = (
                        own_bursts[index + 1] if index + 1 < len(own_bursts) else fight_duration
                    )
                    duration = next_burst - start
                    if duration <= 0:
                        continue
                registry.add(
                    Effect(spec["stat"], spec["value"], spec["scope"], duration, slug),
                    applied_at=start,
                )

    shot_times_by_slug = {}
    last_bullet_times_by_slug = {}
    for slug, weapon in weapon_stats.items():
        target = target_for(slug)
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
        schedule_fn = weapon_mode_schedules.get(slug)
        segments = schedule_fn(context, fight_duration) if schedule_fn is not None else []
        shot_records = generate_segmented_shots(
            weapon, segments, fight_duration,
            max_ammo_percent_at=max_ammo_percent_at,
            reload_speed_percent_at=reload_speed_percent_at,
            attack_speed_percent_at=attack_speed_percent_at,
            charge_speed_percent_at=charge_speed_percent_at,
        )
        shot_times = [r.time for r in shot_records]
        last_bullets = {r.time for r in shot_records if r.is_last_bullet}
        first_bullets = {r.time for r in shot_records if r.is_first_bullet}
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
        # instant_damage_percent pulse recorded as a per-shot nuke.
        # "every_n_critical_hits" counts EXPECTED crits rather than shots (EVE's
        # Unstable Energy) - see its branch below. Rules must
        # be stateless and must not change shot generation (reload/ammo), which
        # is already fixed for this unit here.
        unit_per_shot = per_shot_rules.get(slug, [])
        last_bullet_times_by_slug[slug] = last_bullets
        # The window-gated modes fire on the same in-window shot times a
        # matching resource fill would pick, so reuse `_resource_fill_times`'
        # window filter. "every_during_full_burst" carries N in `threshold`;
        # "every_during_own_status_window" carries (N, window_duration).
        own_burst_times = context.burst_times.get(slug, [])
        window_fire_times = {}
        # every_during_segment/every_outside_segment are keyed on record
        # IDENTITY (shot_index), not shot_time: a magazine-type base weapon
        # (AR/MG/SMG/SG) resumes with a fresh magazine at the exact instant
        # an until_shots segment's last shot lands (attack_rate's documented
        # resume semantic), so the segment's last ShotRecord (in_segment=
        # True) and the resumed magazine's first ShotRecord (in_segment=
        # False) can share an identical `time`. Matching by time value would
        # make both records satisfy both modes at that instant, breaking the
        # in_segment flag's whole purpose - a structural guarantee that one
        # shot can never fire both (Task 8 fix).
        window_fire_indices = {}
        sequence_fires = {}
        for idx, (threshold, mode, _rules) in enumerate(unit_per_shot):
            if mode == "every_during_full_burst":
                window_fire_times[idx] = set(_resource_fill_times(
                    ("per_shot_every_during_full_burst", threshold), shot_times,
                    core_hittable, fight_duration, full_burst_windows,
                ))
            elif mode == "every_outside_full_burst":
                window_fire_times[idx] = set(_resource_fill_times(
                    ("per_shot_every_outside_full_burst", threshold), shot_times,
                    core_hittable, fight_duration, full_burst_windows,
                ))
            elif mode == "every_during_own_status_window":
                n, window_duration = threshold
                window_fire_times[idx] = set(_resource_fill_times(
                    ("per_shot_every_during_own_status_window", n, window_duration), shot_times,
                    core_hittable, fight_duration, full_burst_windows, own_burst_times,
                ))
            elif mode == "every_during_segment":
                seg_indices = [i for i, r in enumerate(shot_records) if r.in_segment]
                window_fire_indices[idx] = {
                    i for pos, i in enumerate(seg_indices) if (pos + 1) % threshold == 0}
            elif mode == "every_outside_segment":
                base_indices = [i for i, r in enumerate(shot_records) if not r.in_segment]
                window_fire_indices[idx] = {
                    i for pos, i in enumerate(base_indices) if (pos + 1) % threshold == 0}
            elif mode == "every_n_critical_hits":
                # This engine never rolls crit per hit - every hit's damage is
                # scaled by the expected crit factor - so there is no "was this
                # shot a crit" event to count. An "after N critical hits"
                # trigger is therefore counted in EXPECTED crits: each shot
                # contributes the unit's live crit rate at that instant, and the
                # rule fires each time the running total crosses N, carrying the
                # remainder forward. Reading the rate PER SHOT rather than once
                # at build time is the whole point - it is what lets deck crit
                # buffs move the trigger's cadence (Fienn, 2026-07-20: an
                # expected-value conversion is only acceptable if the deck's
                # crit buffs count). Caveat: shot loops run per unit, so a crit
                # buff applied by a LATER-processed ally's own per-shot rules is
                # not visible here; burst / full-burst-triggered crit buffs are,
                # since those rules run before any shot loop.
                crit_fires = set()
                expected_crits = 0.0
                for i, crit_rec in enumerate(shot_records):
                    expected_crits += min(
                        1.0, base_crit_rate + registry.total_for("crit_rate", target, crit_rec.time)
                    )
                    # Tolerance, not cosmetics: summing a rate like 0.3 ten
                    # times lands on 2.9999999999999996, which would silently
                    # push a proc a whole shot later than exact arithmetic puts
                    # it (same class of rounding trap as burst_cycle's
                    # last + cooldown comparison).
                    if expected_crits + 1e-9 >= threshold:
                        crit_fires.add(i)
                        expected_crits -= threshold
                window_fire_indices[idx] = crit_fires
            elif mode == "sequence":
                # threshold carries the requirement spec; the rules slot holds
                # one rule list PER STAGE (see _sequence_fire_rules).
                sequence_fires[idx] = _sequence_fire_rules(
                    threshold, _rules, shot_times, own_burst_times
                )
        for shot_index, rec in enumerate(shot_records):
            shot_time = rec.time
            count = shot_index + 1
            for idx, (threshold, mode, rules) in enumerate(unit_per_shot):
                if mode == "sequence":
                    rules = sequence_fires[idx].get(shot_time, ())
                    fires = bool(rules)
                else:
                    fires = (
                        (mode == "after" and count == threshold)
                        or (mode == "every" and count % threshold == 0)
                        or (mode == "last_bullet" and shot_time in last_bullets)
                        or (mode == "first_bullet" and shot_time in first_bullets)
                        or (idx in window_fire_times and shot_time in window_fire_times[idx])
                        or (idx in window_fire_indices and shot_index in window_fire_indices[idx])
                    )
                if fires:
                    for rule in rules:
                        if rule.condition(context, slug):
                            rule.action(context, slug, shot_time, registry)
                    for pulse in registry.drain_pulses("instant_damage_percent"):
                        record(
                            pulse.source_slug, pulse.value, shot_time, "per_shot_nuke",
                            damage_type=pulse.damage_type,
                            full_burst_bonus_eligible=pulse.full_burst_bonus_eligible,
                        )
            damage_type = rec.damage_type or normal_attack_type(slug, rec.weapon, shot_time)
            record(slug, rec.damage_percent, shot_time, "normal_attack",
                   damage_type=damage_type, extra_charge_bonus=rec.extra_charge_bonus)
        shot_times_by_slug[slug] = shot_times

    # "For N round(s)" (bullet-count) buffs expire when the affected ally
    # fires N normal attacks, not after a fixed time. Turn each grant that
    # targets a unit into a concrete Effect whose window covers exactly its
    # next N shots after the grant (from the first covered shot up to the next
    # uncovered shot / fight end), so phase 2 applies the buff to precisely
    # those shots and nothing after. A squad grant is consumed independently
    # by each ally's own shots (one Effect per unit). Runs as a SECOND pass
    # after ALL units' shot loops (gap #9 refactor), so grants recorded by
    # per-shot rules - of this unit or a later-processed one - convert too;
    # burst-cycle-trigger grants (Zwei, Miranda) exist before any shot loop,
    # so their covering shots are unchanged by the move.
    for slug, shot_times in shot_times_by_slug.items():
        target = target_for(slug)
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
            # A resource may be fed by several sources at different rates, each
            # granting its own amount (see _fill_sources).
            fill_times = []
            for source, amount in _fill_sources(spec.fill):
                source_times = _resource_fill_times(
                    source, shot_times, core_hittable, fight_duration, full_burst_windows,
                    context.burst_times.get(slug, []), last_bullet_times_by_slug.get(slug, set()),
                )
                for ft in source_times:
                    context.fill_resource(slug, spec.name, amount, ft)
                fill_times.extend(source_times)

            # Resets (a resource SET to a new value rather than incremented,
            # e.g. Soda's Golden Chip consumed down to 17 on her own burst) are
            # collected from every reset spec and replayed in time order, so
            # each reset's pre-value correctly reflects fills AND any earlier
            # reset already applied. Each spec carries either a fixed `value`
            # or a `value_fn(pre_value)` for a consumption that reads the count
            # it is spending - e.g. Elegg's ghosts, spending 9 at the 13 cap
            # and 6 below it but never dropping under 1.
            reset_events = []
            for reset_spec in spec.resets:
                if reset_spec["trigger"] == "battle_start":
                    reset_events.append((0.0, reset_spec))
                elif reset_spec["trigger"] == "own_burst":
                    reset_events.extend((rt, reset_spec) for rt in context.burst_times.get(slug, []))
                elif reset_spec["trigger"] == "own_burst_delayed":
                    # Resets `reset_spec["delay"]` seconds AFTER each own-burst
                    # fire, not at the burst itself - e.g. Asuka's Anti A.T.
                    # Field, cleared when Annihilation State ends (9s later),
                    # not when the burst that started it fires.
                    delay = reset_spec["delay"]
                    reset_events.extend(
                        (rt + delay, reset_spec) for rt in context.burst_times.get(slug, [])
                    )
                else:
                    raise ValueError(f"unknown resource reset trigger: {reset_spec['trigger']}")
            reset_events.sort(key=lambda e: e[0])
            for reset_time, reset_spec in reset_events:
                pre_value = context.resource_count(slug, spec.name, reset_time, spec.cap)
                value_fn = reset_spec.get("value_fn")
                post_value = value_fn(pre_value) if value_fn else reset_spec["value"]
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

    # A buff triggered by a resource's FILL events, landing on OTHER squad
    # members (gap #8 - e.g. Maiden's Blessings Upon You: "when MP is
    # replenished, affects all Electric Code allies except for self").
    # resource_gated_buffs (below) reads a count at the owner's burst; this
    # reacts to each fill itself. Refreshing: consecutive fills within the
    # duration refresh rather than stack (one source, NIKKE convention). Runs
    # after the resource_specs loop, so every fill is recorded by now; the
    # buffs are phase-2-visible like every other post-pass Effect.
    for slug, specs in resource_fill_triggered_buffs.items():
        for spec in specs:
            if spec.get("condition") is not None and not spec["condition"](context, slug):
                continue
            targets = [m.slug for m in context.members if spec["member_filter"](m, slug)]
            if not targets:
                continue
            scope = "slugs:" + ",".join(targets)
            for fill_time, _amount in context.resource_fills.get((slug, spec["resource"]), []):
                for stat, value, duration in spec["buffs"]:
                    registry.add_refreshing(
                        Effect(stat, value, scope, duration, slug), applied_at=fill_time
                    )

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
                # `hit_count_fn` (optional): the count picks the hit count
                # instead of being it - e.g. Elegg's 13 Ghosts, 13 sequential
                # hits at the 13-ghost cap and 6 hits below it.
                hit_count_fn = spec.get("hit_count_fn")
                if hit_count_fn:
                    hit_count = hit_count_fn(hit_count)
                for _ in range(int(hit_count)):
                    record(
                        slug, spec["base_percent"], fire_time, "dynamic_hit_count_nuke",
                        damage_type=spec.get("damage_type", "attack"), extra_flat_atk=extra_flat_atk,
                        full_burst_bonus_eligible=spec.get("full_burst_bonus_eligible", False),
                    )

    for slug, spec in periodic_nukes.items():
        required = spec.get("requires_part_destructible")
        if required is not None and required != context.part_destructible:
            continue
        cooldown = spec["cooldown"]
        percent = spec["percent"]
        damage_type = spec.get("damage_type", "attack")
        hit_count = spec.get("hit_count", 1)
        eligible = spec.get("full_burst_bonus_eligible", False)

        def _tick(tick_time, slug=slug, percent=percent, damage_type=damage_type,
                  hit_count=hit_count, eligible=eligible):
            for _ in range(hit_count):
                record(slug, percent, tick_time, "periodic", damage_type=damage_type,
                       full_burst_bonus_eligible=eligible)

        if spec.get("during_full_burst"):
            # Ticks only inside Full Burst windows, anchored to each window's
            # start (gap #6 - e.g. Ada Wong's Flash Grenade "every 2 sec during
            # Full Burst", Little Mermaid's Bubble Wave "every 1 sec only
            # during Full Burst"). own_burst_interval=(interval, duration):
            # a window starting inside [own burst, +duration) ticks at the
            # enhanced interval instead (Ada's post-burst "activation time
            # condition v 1 sec for 10 sec", Fienn 2026-07-16); her burst and
            # the FB start share ~the same instant, hence the <= comparison.
            own_interval = spec.get("own_burst_interval")
            own_bursts = context.burst_times.get(slug, [])
            for start, end in full_burst_windows:
                interval = cooldown
                if own_interval is not None and any(
                    bt <= start < bt + own_interval[1] for bt in own_bursts
                ):
                    interval = own_interval[0]
                tick = start + interval
                while tick < end:
                    _tick(tick)
                    tick += interval
        else:
            tick = cooldown
            while tick < fight_duration:
                _tick(tick)
                tick += cooldown

    # Damage on a cadence the unit computes for itself. `periodic_nukes` covers
    # a fixed interval; a summoned entity whose attack rate depends on how many
    # of it are alive (Ein's Near Feathers) has a varying one. The schedule is
    # still deterministic - it falls out of the owner's burst times, which are
    # settled by now - so the unit module builds the time list and the engine
    # only emits it, keeping summon-lifetime bookkeeping out of the simulator.
    context.shot_times = shot_times_by_slug
    for slug, specs in scheduled_nukes.items():
        for spec in specs:
            damage_type = spec.get("damage_type", "attack")
            eligible = spec.get("full_burst_bonus_eligible", False)
            # Optional `resource_gate` (same 4-tuple shape resource_scaled_nukes
            # uses): each tick's percent is scaled by a named resource's count
            # AT THAT TICK'S OWN TIME, resolved in phase 2. Lets a whole-fight
            # scheduled DoT scale off a stack counter - e.g. Mihara's Ensnaring
            # Chains, ticking every second at 25.08% PER stack.
            resource_gate = spec.get("resource_gate")
            for hit_time in spec["schedule"](context, fight_duration):
                if hit_time >= fight_duration:
                    continue
                record(slug, spec["percent"], hit_time, "scheduled",
                       damage_type=damage_type, resource_gate=resource_gate,
                       full_burst_bonus_eligible=eligible)

    def _normal_attack_percent(ev):
        # Normal Attack Damage Multiplier is a Final ATK modifier on the
        # user's NORMAL ATTACKS only (damage-formula reference) - it scales
        # the shot's own coefficient, not any Damage-Up bucket, and touches
        # no other damage source.
        multiplier = 1 + _stat_bundle(ev["slug"], ev["time"])["normal_attack_damage_multiplier"]
        return _resolve_percent(ev) * multiplier

    # Phase 2: now that every buff/debuff is in the registry, compute each
    # recorded damage event against the final registry (each read at its own
    # time is replay-safe).
    damage_log = [
        {
            "slug": ev["slug"],
            "time": ev["time"],
            "damage": _damage_instance(
                ev["slug"],
                _normal_attack_percent(ev) if ev["source"] == "normal_attack" else _resolve_percent(ev),
                ev["time"],
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
