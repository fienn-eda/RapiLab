"""Assembles a user's submitted roster (UserNikkeState, from the web form)
into engine NikkeSpecs using LOCAL data files only - the glue between the API
and assemble_simulation_inputs / find_best_decks.

A unit that can't be loaded is EXCLUDED and reported, never an error (Fienn,
2026-07-16): not encoded; encoded but no SKILL_VALUE_MANIFESTS yet; missing a
data file (e.g. lootandwaifus-only units have no dotgg weapon stats until
collected). Character metadata prefers the lootandwaifus file (project source
priority) and falls back to the dotgg file; weapon stats come from dotgg only.
"""
from pathlib import Path

from app.models import UserNikkeState
from app.roster import NikkeSpec
from app.skill_rules.registry import ENCODED_SLUGS, get_skill_value_manifest
from app.skill_values import DATA_DIR, assemble_skill_values, load_character_data

_WEAPON_STAT_FIELDS = ("weapon", "maxAmmo", "damage", "reloadTime", "chargeTime", "chargeDamage")


def _percent(raw):
    return float(str(raw).rstrip("%"))


def _weapon_stats(dotgg_data):
    if any(field not in dotgg_data for field in _WEAPON_STAT_FIELDS):
        return None
    return {
        "weapon": dotgg_data["weapon"],
        "damage_percent": _percent(dotgg_data["damage"]),
        "max_ammo": int(dotgg_data["maxAmmo"]),
        "reload_time": float(dotgg_data["reloadTime"]),
        "charge_time": float(dotgg_data["chargeTime"]),
        "charge_damage_percent": _percent(dotgg_data["chargeDamage"]),
    }


def load_nikke_spec(state: UserNikkeState, data_dir: Path = DATA_DIR) -> NikkeSpec | None:
    slug = state.character_slug
    if slug not in ENCODED_SLUGS:
        return None
    manifest = get_skill_value_manifest(slug)
    if manifest is None:
        return None
    data_slug = manifest.get("data_slug", slug)
    # dotgg sometimes shortens a unit's slug (url "ada" for "ada-wong"); the
    # optional dotgg_slug manifest key bridges that for the weapon-stats lookup.
    try:
        dotgg = load_character_data("dotgg", manifest.get("dotgg_slug", data_slug), data_dir)
    except FileNotFoundError:
        return None
    weapon_stats = _weapon_stats(dotgg)
    if weapon_stats is None:
        return None
    try:
        meta = load_character_data("lootandwaifus", data_slug, data_dir)
    except FileNotFoundError:
        meta = dotgg
    try:
        skill_values = assemble_skill_values(
            slug, manifest, state.skill_levels.model_dump(), data_dir
        )
        burst_tier = int(meta["burst"])
        burst_cooldown = float(meta.get("cooldown") or meta["skills"][2]["cooldown"])
        element, weapon = meta["element"], meta["weapon"]
    except (KeyError, IndexError, TypeError, ValueError):
        return None
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
        cube=state.pve_cube.model_dump() if state.pve_cube else None,
    )


def load_roster(states: list[UserNikkeState], data_dir: Path = DATA_DIR):
    specs, excluded, seen = [], [], set()
    for state in states:
        spec = load_nikke_spec(state, data_dir)
        if spec is not None:
            specs.append(spec)
        elif state.character_slug not in seen:
            excluded.append(state.character_slug)
        seen.add(state.character_slug)
    return specs, excluded
