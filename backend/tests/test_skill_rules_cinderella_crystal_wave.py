"""Cinderella: Crystal Wave, two static mode slugs ("cinderella-crystal-wave-mg"
and "-snipe"). Real max-level (base-skill) figures from lootandwaifus, slots
numbered left-to-right per skill - every number in the raw text tokenizes,
including the "Additional Effect 1/2/3" labels (see skill_values.py's plain
left-to-right convention; verified against test_skill_value_assembly.py, no
drop_tokens needed).
"""
import pytest

from app.effects import EffectRegistry
from app.skill_rules.cinderella_crystal_wave import (
    SKILL_VALUE_MANIFESTS,
    build_beauty_full_gauge_fills,
    build_crystal_wave_mg_rules,
    build_crystal_wave_snipe_rules,
    build_snipe_weapon_profile,
    crystal_wave_burst_percent,
    crystal_wave_periodic_nuke,
)
from app.skill_rules.registry import MODE_VARIANTS
from app.squad_engine import SquadContext, SquadMember, fire_trigger

CRYSTAL_WAVE_VALUES = {
    "beauty_full": {
        "description_value_01": "1", "description_value_02": "62.13",
        "description_value_03": "250", "description_value_04": "15",
        "description_value_05": "1", "description_value_06": "2",
        "description_value_07": "40", "description_value_08": "3",
        "description_value_09": "1", "description_value_10": "24",
        "description_value_11": "3", "description_value_12": "6",
        "description_value_13": "5", "description_value_14": "900",
        "description_value_15": "200", "description_value_16": "12",
    },
    "mode_swap": {
        "description_value_01": "70.34", "description_value_02": "29",
        "description_value_03": "26.21", "description_value_04": "26",
        "description_value_05": "1", "description_value_06": "1189.66",
        "description_value_07": "1", "description_value_08": "833.79",
    },
    "glass_slippers": {
        "description_value_01": "92", "description_value_02": "10",
        "description_value_03": "65", "description_value_04": "10",
        "description_value_05": "6000",
    },
}


def make_context(core_hittable=False):
    return SquadContext(
        [
            SquadMember("cinderella-crystal-wave-mg", burst_tier=3, element="Iron"),
            SquadMember("ally", burst_tier=1, element="Water"),
        ],
        core_hittable=core_hittable,
    )


class _FakeRegistry:
    """Minimal registry stand-in exposing a bare `.added` list - none of the
    existing test files' FakeRegistry helpers expose one, and buff_rule's
    action only ever calls `registry.add`."""

    def __init__(self):
        self.added = []

    def add(self, effect, applied_at):
        self.added.append((effect.stat, effect.value, effect.scope, effect.duration))


def _applied_buffs(rule):
    reg = _FakeRegistry()
    rule.action(make_context(), "cinderella-crystal-wave-mg", 0.0, reg)
    return reg.added


def test_shared_kit_battle_start_and_burst_buffs():
    rules = build_crystal_wave_mg_rules(CRYSTAL_WAVE_VALUES)
    starts = [r for r in rules if r.trigger == "battle_start"]
    bursts = [r for r in rules if r.trigger == "own_burst_activate"]
    assert ("attack_damage_up", 0.24, "self", None) in _applied_buffs(starts[0])
    assert ("atk_percent", 0.29, "self", None) in _applied_buffs(starts[0])
    assert ("other_core_damage_sources", 0.26, "self", None) in _applied_buffs(starts[1])
    assert ("attack_damage_up", 0.92, "self", 10.0) in _applied_buffs(bursts[0])
    assert ("atk_percent", 0.65, "self", 10.0) in _applied_buffs(bursts[0])


def test_snipe_shared_kit_battle_start_and_burst_buffs():
    # Snipe shares the same _shared_rules battle_start/own_burst_activate
    # buffs as MG - only the mode-specific battle_start bullet and FB nuke differ.
    rules = build_crystal_wave_snipe_rules(CRYSTAL_WAVE_VALUES)
    starts = [r for r in rules if r.trigger == "battle_start"]
    bursts = [r for r in rules if r.trigger == "own_burst_activate"]
    assert ("attack_damage_up", 0.24, "self", None) in _applied_buffs(starts[0])
    assert ("atk_percent", 0.29, "self", None) in _applied_buffs(starts[0])
    assert ("damage_to_parts_up", 0.2621, "self", None) in _applied_buffs(starts[1])
    assert ("attack_damage_up", 0.92, "self", 10.0) in _applied_buffs(bursts[0])
    assert ("atk_percent", 0.65, "self", 10.0) in _applied_buffs(bursts[0])


def test_periodic_900_every_5s():
    assert crystal_wave_periodic_nuke(CRYSTAL_WAVE_VALUES) == {"cooldown": 5.0, "percent": 900.0}


def test_burst_nuke_is_6000():
    assert crystal_wave_burst_percent(CRYSTAL_WAVE_VALUES) == 6000.0


def test_beauty_full_fills_the_gauge_every_200_ally_rounds():
    """Beauty-Full: 아군 누적 소모탄 200발마다 게이지 12%(lv10, 양 모드 공유)."""
    fills = build_beauty_full_gauge_fills(CRYSTAL_WAVE_VALUES)
    assert fills == [{"every_ally_rounds": 200.0, "fraction": pytest.approx(0.12)}]


def test_snipe_profile_is_static_sr_charge_weapon():
    # burst_energy_pershot/pellets_per_shot must survive the swap - they
    # describe the MG she never stops holding, not the SR profile below.
    collected = {"burst_energy_pershot": 500.0, "pellets_per_shot": 1}
    assert build_snipe_weapon_profile(CRYSTAL_WAVE_VALUES, collected) == {
        "weapon": "SR", "damage_percent": 62.13, "max_ammo": 15,
        "reload_time": 2.5,  # Step 1 answer: no reload value in the skill
        # text - MG base reload, Fienn's ruling 2026-07-19.
        "charge_time": 1.0, "charge_damage_percent": 250.0,
        "burst_energy_pershot": 500.0, "pellets_per_shot": 1,
    }


def test_mg_fb_nuke_gated_on_own_burst_and_core():
    rules = build_crystal_wave_mg_rules(CRYSTAL_WAVE_VALUES)
    slug = "cinderella-crystal-wave-mg"

    def fires(core_hittable, burst_fired):
        ctx = make_context(core_hittable=core_hittable)
        if burst_fired:
            ctx.burst_used_this_cycle.add(slug)
        reg = EffectRegistry()
        fire_trigger("full_burst_enter", {slug: rules}, ctx, reg, time=5.0)
        return reg.drain_pulses("instant_damage_percent")

    both = fires(core_hittable=True, burst_fired=True)
    assert len(both) == 1 and both[0].value == 833.79

    assert fires(core_hittable=True, burst_fired=False) == []
    assert fires(core_hittable=False, burst_fired=True) == []
    assert fires(core_hittable=False, burst_fired=False) == []


def test_snipe_fb_nuke_gated_on_own_burst_only():
    rules = build_crystal_wave_snipe_rules(CRYSTAL_WAVE_VALUES)
    slug = "cinderella-crystal-wave-snipe"

    def fires(core_hittable, burst_fired):
        ctx = make_context(core_hittable=core_hittable)
        if burst_fired:
            ctx.burst_used_this_cycle.add(slug)
        reg = EffectRegistry()
        fire_trigger("full_burst_enter", {slug: rules}, ctx, reg, time=5.0)
        return reg.drain_pulses("instant_damage_percent")

    # Fires even with no exploitable core - only own_burst_fired_this_cycle gates it.
    no_core = fires(core_hittable=False, burst_fired=True)
    assert len(no_core) == 1 and no_core[0].value == 1189.66

    with_core = fires(core_hittable=True, burst_fired=True)
    assert len(with_core) == 1 and with_core[0].value == 1189.66

    assert fires(core_hittable=False, burst_fired=False) == []
    assert fires(core_hittable=True, burst_fired=False) == []


def test_manifests_registered_for_both_slugs():
    for slug in ("cinderella-crystal-wave-mg", "cinderella-crystal-wave-snipe"):
        manifest = SKILL_VALUE_MANIFESTS[slug]
        assert manifest["data_slug"] == "cinderella-crystal-wave"
        assert manifest["dotgg_slug"] == "cinderella-crystal-wave"


def test_mode_variants_registers_both_slugs_under_the_base():
    assert MODE_VARIANTS["cinderella-crystal-wave"] == (
        "cinderella-crystal-wave-mg", "cinderella-crystal-wave-snipe",
    )


# Module-level fixture aliases so the assembly verification harness
# (test_skill_value_assembly.py) can resolve each sub-skill fixture by name.
BEAUTY_FULL = CRYSTAL_WAVE_VALUES["beauty_full"]
MODE_SWAP = CRYSTAL_WAVE_VALUES["mode_swap"]
GLASS_SLIPPERS = CRYSTAL_WAVE_VALUES["glass_slippers"]
