"""Assembles a user's submitted roster (UserNikkeState, from the web form)
into engine NikkeSpecs using LOCAL data files only - the glue between the API
and assemble_simulation_inputs / find_best_decks.

A unit that can't be loaded is EXCLUDED and reported, never an error (Fienn,
2026-07-16): not encoded; encoded but no SKILL_VALUE_MANIFESTS yet; missing a
data file (e.g. lootandwaifus-only units have no dotgg weapon stats until
collected). Character metadata prefers the lootandwaifus file (project source
priority) and falls back to the dotgg file; weapon stats come from the
manifest's `weapon_source`, defaulting to its `source` - dotgg for dotgg- and
lootandwaifus-source units, or the unit's normalized data/shiftypad/<slug>.json
when the source (or the override) is shiftypad.
"""
from pathlib import Path

from app.collectible_effects import collectible_modifiers
from app.models import UserNikkeState
from app.roster import NikkeSpec
from app.skill_rules.registry import (
    ENCODED_SLUGS,
    MODE_VARIANTS,
    VARIANT_BURST_TIERS,
    get_skill_value_manifest,
    get_weapon_profile_override,
)
from app.skill_values import (DATA_DIR, assemble_skill_values,
                              load_character_data, load_weapon_data)

_WEAPON_STAT_FIELDS = ("weapon", "maxAmmo", "damage", "reloadTime", "chargeTime", "chargeDamage")


def _percent(raw):
    return float(str(raw).rstrip("%"))


def _weapon_stats(weapon_data):
    if any(field not in weapon_data for field in _WEAPON_STAT_FIELDS):
        return None
    return {
        "weapon": weapon_data["weapon"],
        "damage_percent": _percent(weapon_data["damage"]),
        "max_ammo": int(weapon_data["maxAmmo"]),
        "reload_time": float(weapon_data["reloadTime"]),
        "charge_time": float(weapon_data["chargeTime"]),
        "charge_damage_percent": _percent(weapon_data["chargeDamage"]),
    }


def load_nikke_spec(
    state: UserNikkeState, data_dir: Path = DATA_DIR, slug_override: str | None = None
) -> NikkeSpec | None:
    slug = slug_override or state.character_slug
    if slug not in ENCODED_SLUGS:
        return None
    manifest = get_skill_value_manifest(slug)
    if manifest is None:
        return None
    data_slug = manifest.get("data_slug", slug)
    # Which file the weapon stats come from is load_weapon_data's call, shared
    # with supported_units so a unit can never be loadable to one and invisible
    # to the other (see its docstring for what that cost once).
    try:
        weapon_data = load_weapon_data(manifest, slug, data_dir)
    except FileNotFoundError:
        return None
    weapon_stats = _weapon_stats(weapon_data)
    if weapon_stats is None:
        return None
    try:
        meta = load_character_data("lootandwaifus", data_slug, data_dir)
    except FileNotFoundError:
        meta = weapon_data
    try:
        skill_values = assemble_skill_values(
            slug, manifest, state.skill_levels.model_dump(), data_dir
        )
        override = get_weapon_profile_override(slug, skill_values, weapon_stats)
        if override is not None:
            weapon_stats = override
        variant_tier = VARIANT_BURST_TIERS.get(slug)
        burst_tier = variant_tier if variant_tier is not None else int(meta["burst"])
        burst_cooldown = float(meta.get("cooldown") or meta["skills"][2]["cooldown"])
        element, weapon = meta["element"], meta["weapon"]
    except (KeyError, IndexError, TypeError, ValueError):
        return None
    # A collectible's 배율 scales the WEAPON's own base stat, so it lands here
    # rather than in the buff registry - and after any mode override, so a unit
    # whose weapon profile swaps mid-kit still carries it.
    weapon_multipliers, _ = collectible_modifiers(
        state.collectible_tid, state.collectible_level, slug)
    if weapon_multipliers:
        weapon_stats = dict(weapon_stats)
        for stat, factor in weapon_multipliers.items():
            weapon_stats[stat] = weapon_stats[stat] * factor
    return NikkeSpec(
        slug=slug,
        burst_tier=burst_tier,
        burst_cooldown=burst_cooldown,
        element=element,
        weapon=weapon,
        base_stats={"atk": state.atk, "def": state.def_, "max_hp": state.hp},
        skill_values=skill_values,
        # OverloadOption models pass through as-is: roster._passive_effects hands
        # them to overload_options_to_effects, which reads .name/.value attributes.
        overload_options=list(state.overload_options),
        weapon_stats=weapon_stats,
        collectible_tid=state.collectible_tid,
        collectible_level=state.collectible_level,
    )


def load_roster(states: list[UserNikkeState], data_dir: Path = DATA_DIR):
    specs, excluded, seen = [], [], set()
    for state in states:
        slugs = MODE_VARIANTS.get(state.character_slug) or (state.character_slug,)
        loaded = [s for s in (load_nikke_spec(state, data_dir, slug_override=slug)
                              for slug in slugs) if s is not None]
        specs.extend(loaded)
        if not loaded and state.character_slug not in seen:
            excluded.append(state.character_slug)
        seen.add(state.character_slug)
    return specs, excluded
