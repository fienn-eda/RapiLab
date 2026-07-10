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
from app.attack_rate import CHARGE_WEAPONS, generate_shot_times
from app.burst_cycle import simulate_burst_cycle
from app.damage_formula import calculate_damage
from app.effects import EffectRegistry
from app.elements import element_multiplier
from app.squad_engine import SquadContext, SquadMember, fire_trigger

CORE_HIT_BONUS = 1.0
BASE_CRIT_RATE = 0.15

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
):
    weapon_stats = weapon_stats or {}
    periodic_nukes = periodic_nukes or {}
    burst_damage_types = burst_damage_types or {}
    periodic_rules = periodic_rules or {}
    per_shot_rules = per_shot_rules or {}
    context = SquadContext([SquadMember(m["slug"], m["burst_tier"], m["element"]) for m in deck])
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

    def _damage_instance(slug, percent, time, damage_type="attack", extra_charge_bonus=0.0):
        target = target_for(slug)
        # True Damage ignores enemy DEF (nikke.gg glossary).
        instance_enemy_def = 0 if damage_type == "true" else enemy_def
        terms = dict(
            atk=base_stats[slug]["atk"],
            attack_coefficient=percent / 100,
            enemy_def=instance_enemy_def,
            atk_percent=registry.total_for("atk_percent", target, time),
            flat_atk=registry.total_for("flat_atk", target, time),
            other_elemental_bonus=registry.total_for("other_elemental_bonus", target, time),
            other_critical_damage_sources=registry.total_for("other_critical_damage_sources", target, time),
            crit_rate=crit_rate_for(target, time),
            core_hit_bonus=CORE_HIT_BONUS if core_hittable else 0.0,
            other_core_damage_sources=(
                registry.total_for("other_core_damage_sources", target, time) if core_hittable else 0.0
            ),
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

    def record(slug, percent, time, source, damage_type="attack", extra_charge_bonus=0.0):
        damage_events.append({
            "slug": slug, "percent": percent, "time": time, "source": source,
            "damage_type": damage_type, "extra_charge_bonus": extra_charge_bonus,
        })

    def drain_instant_damage(time):
        # A passive that deals damage on a trigger OTHER than the caster's own
        # burst (e.g. Brid: Silent Track's Ignition Sequence, on full_burst_enter)
        # can't use burst_damage_percents (tied to own_burst_activate). It emits
        # an "instant_damage_percent" pulse instead; drained here after every
        # trigger fire, recorded as a nuke computed later like a burst nuke.
        for pulse in registry.drain_pulses("instant_damage_percent"):
            record(pulse.source_slug, pulse.value, time, "instant_nuke")

    def on_battle_start(time):
        fire_trigger("battle_start", rules_by_slug, context, registry, time)
        drain_instant_damage(0.0)

    def on_tier_fire(tier, slug, time):
        context.burst_used_this_cycle.add(slug)
        fire_trigger("own_burst_activate", {slug: rules_by_slug.get(slug, [])}, context, registry, time)
        drain_instant_damage(time)

        percent = burst_damage_percents.get(slug)
        if not percent:
            return
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

    for slug, weapon in weapon_stats.items():
        target = target_for(slug)
        is_charge_weapon = weapon["weapon"] in CHARGE_WEAPONS
        shot_times = generate_shot_times(
            weapon["weapon"],
            weapon["max_ammo"],
            weapon["reload_time"],
            weapon["charge_time"],
            fight_duration,
            max_ammo_percent_at=lambda t, target=target: registry.total_for("max_ammo_percent", target, t),
            reload_speed_percent_at=lambda t, target=target: registry.total_for(
                "reload_speed_percent", target, t
            ),
        )
        extra_charge_bonus = weapon["charge_damage_percent"] / 100 - 1 if is_charge_weapon else 0.0
        # Per-shot triggers count this unit's shots and fire at a threshold
        # ("after N": once at the Nth shot; "every N": at every Nth). Their
        # rules apply buffs to the registry (seen by phase 2 at each shot's
        # time) or emit an instant_damage_percent pulse recorded as a per-shot
        # nuke. Rules must be stateless and must not change shot generation
        # (reload/ammo), which is already fixed for this unit here.
        unit_per_shot = per_shot_rules.get(slug, [])
        for shot_index, shot_time in enumerate(shot_times):
            count = shot_index + 1
            for threshold, mode, rules in unit_per_shot:
                if (mode == "after" and count == threshold) or (mode == "every" and count % threshold == 0):
                    for rule in rules:
                        if rule.condition(context, slug):
                            rule.action(context, slug, shot_time, registry)
                    for pulse in registry.drain_pulses("instant_damage_percent"):
                        record(pulse.source_slug, pulse.value, shot_time, "per_shot_nuke")
            damage_type = normal_attack_type(slug, weapon, target, shot_time)
            record(slug, weapon["damage_percent"], shot_time, "normal_attack",
                   damage_type=damage_type, extra_charge_bonus=extra_charge_bonus)

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
                ev["slug"], ev["percent"], ev["time"],
                damage_type=ev["damage_type"], extra_charge_bonus=ev["extra_charge_bonus"],
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
