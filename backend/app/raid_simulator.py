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
"""
from app.attack_rate import CHARGE_WEAPONS, generate_shot_times
from app.burst_cycle import simulate_burst_cycle
from app.damage_formula import calculate_damage
from app.effects import EffectRegistry
from app.elements import element_multiplier
from app.squad_engine import SquadContext, SquadMember, fire_trigger

CORE_HIT_BONUS = 1.0
BASE_CRIT_RATE = 0.15


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
):
    weapon_stats = weapon_stats or {}
    context = SquadContext([SquadMember(m["slug"], m["burst_tier"], m["element"]) for m in deck])
    registry = EffectRegistry()
    damage_log = []
    member_by_slug = {m["slug"]: m for m in deck}

    def target_for(slug):
        return {"slug": slug, "element": member_by_slug[slug]["element"]}

    def crit_rate_for(target, time):
        return min(1.0, base_crit_rate + registry.total_for("crit_rate", target, time))

    def element_bonus_for(slug):
        if boss_element is None:
            return 1.0
        return element_multiplier(member_by_slug[slug]["element"], boss_element)

    def _damage_from_percent(slug, percent, time):
        target = target_for(slug)
        return calculate_damage(
            atk=base_stats[slug]["atk"],
            attack_coefficient=percent / 100,
            enemy_def=enemy_def,
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
            charge_damage_bonus=registry.total_for("charge_damage_bonus", target, time),
            attack_damage_up=registry.total_for("attack_damage_up", target, time),
            damage_to_parts_up=registry.total_for("damage_to_parts_up", target, time),
            pierce_damage_up=registry.total_for("pierce_damage_up", target, time),
            damage_taken_up=registry.total_for("damage_taken_up", target, time),
        )

    def drain_instant_damage(time):
        # A passive that deals damage on a trigger OTHER than the caster's own
        # burst (e.g. Brid: Silent Track's Ignition Sequence, on full_burst_enter)
        # can't use burst_damage_percents (tied to own_burst_activate). It emits
        # an "instant_damage_percent" pulse instead; drained here after every
        # trigger fire, computed exactly like a burst nuke using the caster's
        # own ATK and live buffs.
        for pulse in registry.drain_pulses("instant_damage_percent"):
            slug = pulse.source_slug
            damage = _damage_from_percent(slug, pulse.value, time)
            damage_log.append({"slug": slug, "time": time, "damage": damage, "source": "instant_nuke"})

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
        damage = _damage_from_percent(slug, percent, time)
        damage_log.append({"slug": slug, "time": time, "damage": damage, "source": "burst"})

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
        for shot_time in shot_times:
            charge_damage_bonus = registry.total_for("charge_damage_bonus", target, shot_time)
            if is_charge_weapon:
                charge_damage_bonus += weapon["charge_damage_percent"] / 100 - 1
            damage = calculate_damage(
                atk=base_stats[slug]["atk"],
                attack_coefficient=weapon["damage_percent"] / 100,
                enemy_def=enemy_def,
                atk_percent=registry.total_for("atk_percent", target, shot_time),
                flat_atk=registry.total_for("flat_atk", target, shot_time),
                other_elemental_bonus=registry.total_for("other_elemental_bonus", target, shot_time),
                other_critical_damage_sources=registry.total_for(
                    "other_critical_damage_sources", target, shot_time
                ),
                crit_rate=crit_rate_for(target, shot_time),
                core_hit_bonus=CORE_HIT_BONUS if core_hittable else 0.0,
                other_core_damage_sources=(
                    registry.total_for("other_core_damage_sources", target, shot_time)
                    if core_hittable
                    else 0.0
                ),
                element_multiplier=element_bonus_for(slug),
                charge_damage_bonus=charge_damage_bonus,
                attack_damage_up=registry.total_for("attack_damage_up", target, shot_time),
                damage_to_parts_up=registry.total_for("damage_to_parts_up", target, shot_time),
                pierce_damage_up=registry.total_for("pierce_damage_up", target, shot_time),
                damage_taken_up=registry.total_for("damage_taken_up", target, shot_time),
            )
            damage_log.append({"slug": slug, "time": shot_time, "damage": damage, "source": "normal_attack"})

    return {
        "total_damage": sum(entry["damage"] for entry in damage_log),
        "damage_log": damage_log,
        "events": events,
    }
