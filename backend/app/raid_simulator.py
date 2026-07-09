"""Ties burst_cycle + squad_engine + effects + damage_formula + attack_rate
into one timeline: schedules the burst rotation, fires skill triggers at the
right moments, and totals up both burst-skill damage instances and normal-
attack damage over the fight.

"Deals X% of final ATK as burst damage" (and normal attacks' own damage%)
are modeled the way nikke.gg's Base Damage formula treats an attack's own
inherent multiplier: the X% scales the caster's base ATK stat *before*
additional %ATK buffs/flat bonuses are layered on top, i.e.
atk_for_hit = base_atk * (X / 100), then that value feeds into
calculate_damage's atk/atk_percent/flat_atk as usual.

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

Known simplifications: all damage is computed as non-critical (crit-rate-
to-expected-damage isn't resolved yet); a slug missing from `weapon_stats`
contributes no normal-attack damage (e.g. while that character's weapon
data hasn't been entered yet); reload_speed_percent/max_ammo_percent
effects don't change the normal-attack shot schedule (see attack_rate's
docstring).
"""
from app.attack_rate import CHARGE_WEAPONS, generate_shot_times
from app.burst_cycle import simulate_burst_cycle
from app.damage_formula import calculate_damage
from app.effects import EffectRegistry
from app.squad_engine import SquadContext, SquadMember, fire_trigger

CORE_HIT_BONUS = 1.0


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
):
    weapon_stats = weapon_stats or {}
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
            core_hit_bonus=CORE_HIT_BONUS if core_hittable else 0.0,
            charge_damage_bonus=registry.total_for("charge_damage_bonus", target, time),
            attack_damage_up=registry.total_for("attack_damage_up", target, time),
            damage_to_parts_up=registry.total_for("damage_to_parts_up", target, time),
        )
        damage_log.append({"slug": slug, "time": time, "damage": damage, "source": "burst"})

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

    for slug, weapon in weapon_stats.items():
        target = target_for(slug)
        is_charge_weapon = weapon["weapon"] in CHARGE_WEAPONS
        shot_times = generate_shot_times(
            weapon["weapon"],
            weapon["max_ammo"],
            weapon["reload_time"],
            weapon["charge_time"],
            fight_duration,
        )
        for shot_time in shot_times:
            charge_damage_bonus = registry.total_for("charge_damage_bonus", target, shot_time)
            if is_charge_weapon:
                charge_damage_bonus += weapon["charge_damage_percent"] / 100 - 1
            damage = calculate_damage(
                atk=base_stats[slug]["atk"] * (weapon["damage_percent"] / 100),
                enemy_def=enemy_def,
                atk_percent=registry.total_for("atk_percent", target, shot_time),
                flat_atk=registry.total_for("flat_atk", target, shot_time),
                other_elemental_bonus=registry.total_for("other_elemental_bonus", target, shot_time),
                other_critical_damage_sources=registry.total_for(
                    "other_critical_damage_sources", target, shot_time
                ),
                core_hit_bonus=CORE_HIT_BONUS if core_hittable else 0.0,
                charge_damage_bonus=charge_damage_bonus,
                attack_damage_up=registry.total_for("attack_damage_up", target, shot_time),
                damage_to_parts_up=registry.total_for("damage_to_parts_up", target, shot_time),
            )
            damage_log.append({"slug": slug, "time": shot_time, "damage": damage, "source": "normal_attack"})

    return {
        "total_damage": sum(entry["damage"] for entry in damage_log),
        "damage_log": damage_log,
        "events": events,
    }
