"""Assembles per-Nikke specs into the inputs simulate_raid expects.

A NikkeSpec bundles everything that varies per owned Nikke: fixed metadata
(from api.dotgg.gg), the user's investment (skill values, overload options,
cube), and weapon stats. assemble_simulation_inputs turns an ordered deck of
these into the (deck, rules_by_slug, burst_damage_percents, base_stats,
weapon_stats, periodic_nukes) that simulate_raid consumes - applying overload
and cube bonuses as permanent battle-start effects, which the earlier
hand-assembled demo omitted.

Deck ORDER is preserved end to end: burst_cycle picks the leftmost eligible
Nikke per tier, so the order of ordered_deck decides who nukes vs who is a
backup buffer among same-tier Nikkes.
"""
from dataclasses import dataclass, field

from app.cube_effects import cube_to_effects
from app.overload_effects import overload_options_to_effects
from app.skill_rules.registry import (
    build_nikke_rules,
    get_burst_damage_type,
    get_burst_hit_count,
    get_per_shot_rules,
    get_periodic_nuke,
    get_dynamic_hit_count_nukes,
    get_periodic_rules,
    get_resource_fill_triggered_buffs,
    get_resource_gated_buffs,
    get_resource_scaled_nukes,
    get_resource_specs,
    get_scheduled_nukes,
    get_weapon_mode_schedules,
)
from app.squad_engine import SkillRule


@dataclass
class NikkeSpec:
    slug: str
    burst_tier: int
    burst_cooldown: float
    element: str
    weapon: str
    base_stats: dict  # {"atk", "def", "max_hp"}
    skill_values: dict
    weapon_stats: dict
    overload_options: list = field(default_factory=list)
    cube: dict | None = None


def _battle_start_effects_rule(effects):
    def action(context, caster_slug, time, registry):
        for effect in effects:
            registry.add(effect, applied_at=time)

    return SkillRule(trigger="battle_start", action=action)


def _passive_effects(spec: NikkeSpec):
    effects = overload_options_to_effects(spec.overload_options, spec.slug)
    if spec.cube:
        effects += cube_to_effects(
            name=spec.cube["name"],
            source_slug=spec.slug,
            reload_speed_percent=spec.cube.get("reload_speed_percent"),
            superior_code_damage_percent=spec.cube.get("superior_code_damage_percent"),
        )
    return effects


def assemble_simulation_inputs(ordered_deck):
    deck = []
    rules_by_slug = {}
    burst_damage_percents = {}
    base_stats = {}
    weapon_stats = {}
    periodic_nukes = {}
    periodic_rules = {}
    per_shot_rules = {}
    resource_specs = {}
    burst_damage_types = {}
    burst_hit_counts = {}
    resource_scaled_nukes = {}
    resource_gated_buffs = {}
    dynamic_hit_count_nukes = {}
    resource_fill_triggered_buffs = {}
    scheduled_nukes = {}
    weapon_mode_schedules = {}

    for spec in ordered_deck:
        deck.append(
            {"slug": spec.slug, "burst_tier": spec.burst_tier, "element": spec.element,
             "cooldown": spec.burst_cooldown, "weapon": spec.weapon}
        )
        base_stats[spec.slug] = spec.base_stats
        weapon_stats[spec.slug] = spec.weapon_stats

        # inject caster base stats so skills that scale off them (e.g. Crown's
        # "X% of caster's ATK") resolve without the caller duplicating them
        skill_values = {
            **spec.skill_values,
            "caster_atk": spec.base_stats["atk"],
            "caster_def": spec.base_stats["def"],
            "caster_max_hp": spec.base_stats["max_hp"],
            "caster_weapon_stats": spec.weapon_stats,
        }
        rules, burst_percent = build_nikke_rules(spec.slug, skill_values)

        passive = _passive_effects(spec)
        if passive:
            rules = rules + [_battle_start_effects_rule(passive)]
        rules_by_slug[spec.slug] = rules

        if burst_percent is not None:
            burst_damage_percents[spec.slug] = burst_percent
            damage_type = get_burst_damage_type(spec.slug)
            if damage_type != "attack":
                burst_damage_types[spec.slug] = damage_type
            hit_count = get_burst_hit_count(spec.slug)
            if hit_count != 1:
                burst_hit_counts[spec.slug] = hit_count

        periodic_nuke = get_periodic_nuke(spec.slug, skill_values)
        if periodic_nuke is not None:
            periodic_nukes[spec.slug] = periodic_nuke

        periodic_rule = get_periodic_rules(spec.slug, skill_values)
        if periodic_rule:
            periodic_rules[spec.slug] = periodic_rule

        per_shot_rule = get_per_shot_rules(spec.slug, skill_values)
        if per_shot_rule:
            per_shot_rules[spec.slug] = per_shot_rule

        resource_spec = get_resource_specs(spec.slug, skill_values)
        if resource_spec:
            resource_specs[spec.slug] = resource_spec

        resource_scaled_nuke = get_resource_scaled_nukes(spec.slug, skill_values)
        if resource_scaled_nuke:
            resource_scaled_nukes[spec.slug] = resource_scaled_nuke

        resource_gated_buff = get_resource_gated_buffs(spec.slug, skill_values)
        if resource_gated_buff:
            resource_gated_buffs[spec.slug] = resource_gated_buff

        dynamic_hit_count_nuke = get_dynamic_hit_count_nukes(spec.slug, skill_values)
        if dynamic_hit_count_nuke:
            dynamic_hit_count_nukes[spec.slug] = dynamic_hit_count_nuke

        resource_fill_triggered_buff = get_resource_fill_triggered_buffs(spec.slug, skill_values)
        if resource_fill_triggered_buff:
            resource_fill_triggered_buffs[spec.slug] = resource_fill_triggered_buff

        scheduled_nuke = get_scheduled_nukes(spec.slug, skill_values)
        if scheduled_nuke:
            scheduled_nukes[spec.slug] = scheduled_nuke

        weapon_mode_schedule = get_weapon_mode_schedules(spec.slug, skill_values)
        if weapon_mode_schedule:
            weapon_mode_schedules[spec.slug] = weapon_mode_schedule

    return {
        "deck": deck,
        "rules_by_slug": rules_by_slug,
        "burst_damage_percents": burst_damage_percents,
        "base_stats": base_stats,
        "weapon_stats": weapon_stats,
        "periodic_nukes": periodic_nukes,
        "periodic_rules": periodic_rules,
        "per_shot_rules": per_shot_rules,
        "resource_specs": resource_specs,
        "burst_damage_types": burst_damage_types,
        "burst_hit_counts": burst_hit_counts,
        "resource_scaled_nukes": resource_scaled_nukes,
        "resource_gated_buffs": resource_gated_buffs,
        "dynamic_hit_count_nukes": dynamic_hit_count_nukes,
        "resource_fill_triggered_buffs": resource_fill_triggered_buffs,
        "scheduled_nukes": scheduled_nukes,
        "weapon_mode_schedules": weapon_mode_schedules,
    }
