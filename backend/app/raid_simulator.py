"""Ties burst_cycle + squad_engine + effects + damage_formula into one
timeline: schedules the burst rotation, fires skill triggers at the right
moments, and totals up burst-skill damage instances.

"Deals X% of final ATK as burst damage" is modeled the way nikke.gg's Base
Damage formula treats an attack's own inherent multiplier: the X% scales
the caster's base ATK stat *before* additional %ATK buffs/flat bonuses are
layered on top, i.e. atk_for_hit = base_atk * (X / 100), then that value
feeds into calculate_damage's atk/atk_percent/flat_atk as usual.

Known simplification: burst damage is computed as non-critical with no
core-hit bonus (crit-rate-to-expected-damage and core-hit-eligibility per
skill aren't resolved yet). Normal-attack DPS between bursts isn't
accumulated at all - that needs the still-deferred attack-rate model. So
`total_damage` here is burst-skill damage only, a floor, not the full
picture.
"""
from app.burst_cycle import simulate_burst_cycle
from app.damage_formula import calculate_damage
from app.effects import EffectRegistry
from app.squad_engine import SquadContext, SquadMember, fire_trigger


def simulate_raid(
    deck,
    rules_by_slug,
    burst_damage_percents,
    base_stats,
    enemy_def,
    gauge_charge_time,
    fight_duration,
    mode="auto",
):
    context = SquadContext([SquadMember(m["slug"], m["burst_tier"], m["element"]) for m in deck])
    registry = EffectRegistry()
    damage_log = []
    member_by_slug = {m["slug"]: m for m in deck}

    def target_for(slug):
        return {"slug": slug, "element": member_by_slug[slug]["element"]}

    def on_battle_start(time):
        fire_trigger("battle_start", rules_by_slug, context, registry, time)

    def on_tier_fire(tier, slug, time):
        context.burst_used_this_cycle.add(slug)
        fire_trigger("own_burst_activate", {slug: rules_by_slug.get(slug, [])}, context, registry, time)

        percent = burst_damage_percents.get(slug)
        if not percent:
            return
        target = target_for(slug)
        damage = calculate_damage(
            atk=base_stats[slug]["atk"] * (percent / 100),
            enemy_def=enemy_def,
            atk_percent=registry.total_for("atk_percent", target, time),
            flat_atk=registry.total_for("flat_atk", target, time),
            other_elemental_bonus=registry.total_for("other_elemental_bonus", target, time),
            other_critical_damage_sources=registry.total_for("other_critical_damage_sources", target, time),
            charge_damage_bonus=registry.total_for("charge_damage_bonus", target, time),
            attack_damage_up=registry.total_for("attack_damage_up", target, time),
            damage_to_parts_up=registry.total_for("damage_to_parts_up", target, time),
        )
        damage_log.append({"slug": slug, "time": time, "damage": damage})

    def on_full_burst_enter(time):
        fire_trigger("full_burst_enter", rules_by_slug, context, registry, time)

    def on_full_burst_end(time):
        fire_trigger("full_burst_end", rules_by_slug, context, registry, time)
        context.burst_used_this_cycle.clear()
        pulses = registry.drain_pulses("burst_cooldown_reduction_sec")
        return sum(pulse.value for pulse in pulses)

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

    return {
        "total_damage": sum(entry["damage"] for entry in damage_log),
        "damage_log": damage_log,
        "events": events,
    }
