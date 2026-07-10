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
from app.skill_rules.registry import build_nikke_rules, get_burst_damage_type, get_periodic_nuke
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
    burst_damage_types = {}

    for spec in ordered_deck:
        deck.append(
            {"slug": spec.slug, "burst_tier": spec.burst_tier, "element": spec.element,
             "cooldown": spec.burst_cooldown}
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

        periodic_nuke = get_periodic_nuke(spec.slug, skill_values)
        if periodic_nuke is not None:
            periodic_nukes[spec.slug] = periodic_nuke

    return {
        "deck": deck,
        "rules_by_slug": rules_by_slug,
        "burst_damage_percents": burst_damage_percents,
        "base_stats": base_stats,
        "weapon_stats": weapon_stats,
        "periodic_nukes": periodic_nukes,
        "burst_damage_types": burst_damage_types,
    }
