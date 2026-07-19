"""Real max-level figures from lootandwaifus for Diesel: Winter Sweets (slugs
"diesel-winter-sweets-intro" / "diesel-winter-sweets-highlight"), slots
numbered left-to-right per skill.
"""
import pytest

from app.effects import EffectRegistry
from app.skill_rules.diesel_winter_sweets import (
    BURST_DELAY,
    build_diesel_highlight_rules,
    build_diesel_intro_rules,
    build_diesel_burst_dot,
    build_diesel_full_burst_dot,
    build_diesel_resource_specs,
)
from app.squad_engine import SquadContext, SquadMember, fire_trigger

MIC_TEST = {
    "description_value_01": "20.28",   # Intro Critical Damage %
    "description_value_02": "20.28",   # Highlight Critical Damage %
    "description_value_03": "60.19",   # Intro Sustained Damage %
    "description_value_04": "10",      # its duration sec
    "description_value_05": "235.03",  # Highlight Sustained Damage %
    "description_value_06": "10",      # its duration sec
}
SING_NOW = {
    "description_value_01": "3",       # Mute stack cap (not modeled)
    "description_value_02": "68.04",   # part-destruction Sustained Damage %
    "description_value_03": "15",      # its duration sec
    "description_value_04": "318.14",  # Full Charge Sustained Damage %
    "description_value_05": "3",       # its duration sec
    "description_value_06": "2",       # its stack cap
    "description_value_07": "63.33",   # Full Burst DoT % of final ATK
    "description_value_08": "1",       # its tick interval sec
    "description_value_09": "9",       # its duration sec
}
LA_LA_LA = {
    "description_value_01": "25.09",   # burst Damage Taken %
    "description_value_02": "10",      # its duration sec
    "description_value_03": "18.43",   # all-enemy DoT % of final ATK
    "description_value_04": "1",       # its tick interval sec
    "description_value_05": "9",       # its duration sec
    "description_value_06": "181.2",   # stage-target DoT % of final ATK
    "description_value_07": "1",       # its tick interval sec
    "description_value_08": "9",       # its duration sec
    "description_value_09": "100",     # Noise Pollution Hit Rate % (deferred)
    "description_value_10": "1",       # its duration sec
    "description_value_11": "1",       # Mute stacks consumed (not modeled)
}

VALUES = {"mic_test": MIC_TEST, "sing_now": SING_NOW, "la_la_la": LA_LA_LA}

DIESEL_INTRO = "diesel-winter-sweets-intro"
DIESEL_HIGHLIGHT = "diesel-winter-sweets-highlight"


def _context(slug, part_destructible=False):
    return SquadContext(
        [SquadMember(slug, 3, "Fire", "RL")], part_destructible=part_destructible
    )


def _target(slug):
    return {"slug": slug, "element": "Fire", "burst_tier": 3, "weapon": "RL"}


def _apply(rules, slug, trigger, time=0.0, part_destructible=False):
    registry = EffectRegistry()
    context = _context(slug, part_destructible)
    fire_trigger(trigger, {slug: rules}, context, registry, time)
    return registry


# --- Locked Intro / Highlight state ------------------------------------


def test_intro_locks_the_weaker_sustained_buff_on_every_full_burst():
    registry = _apply(build_diesel_intro_rules(VALUES), DIESEL_INTRO, "full_burst_enter", 5.0)
    assert registry.total_for("sustained_damage_up", _target(DIESEL_INTRO), 6.0) == 0.6019


def test_highlight_locks_the_stronger_sustained_buff_on_every_full_burst():
    registry = _apply(
        build_diesel_highlight_rules(VALUES), DIESEL_HIGHLIGHT, "full_burst_enter", 5.0
    )
    assert registry.total_for("sustained_damage_up", _target(DIESEL_HIGHLIGHT), 6.0) == 2.3503


def test_the_sustained_buff_expires_after_ten_seconds():
    registry = _apply(
        build_diesel_highlight_rules(VALUES), DIESEL_HIGHLIGHT, "full_burst_enter", 5.0
    )
    assert registry.total_for("sustained_damage_up", _target(DIESEL_HIGHLIGHT), 15.1) == 0.0


def test_crit_damage_starts_at_the_first_full_burst_and_is_permanent():
    rules = build_diesel_intro_rules(VALUES)
    registry = EffectRegistry()
    context = _context(DIESEL_INTRO)
    fire_trigger("full_burst_enter", {DIESEL_INTRO: rules}, context, registry, 5.0)

    assert registry.total_for("other_critical_damage_sources", _target(DIESEL_INTRO), 4.9) == 0.0
    assert registry.total_for("other_critical_damage_sources", _target(DIESEL_INTRO), 179.0) == 0.2028


def test_crit_damage_does_not_restack_on_later_full_bursts():
    # The state is entered once and "cannot be removed" - re-entering Full
    # Burst must not add a second copy.
    rules = build_diesel_intro_rules(VALUES)
    registry = EffectRegistry()
    context = _context(DIESEL_INTRO)
    for time in (5.0, 25.0, 45.0):
        fire_trigger("full_burst_enter", {DIESEL_INTRO: rules}, context, registry, time)

    assert registry.total_for("other_critical_damage_sources", _target(DIESEL_INTRO), 50.0) == 0.2028


def test_only_highlight_carries_the_skip_a_cycle_burst_delay():
    assert BURST_DELAY == {DIESEL_HIGHLIGHT: {"skip_cycles": 1}}


# --- Part-destruction bracket ------------------------------------------


def test_part_destruction_sustained_buff_applies_only_on_a_destructible_boss():
    rules = build_diesel_intro_rules(VALUES)
    ceiling = _apply(rules, DIESEL_INTRO, "battle_start", 0.0, part_destructible=True)
    floor = _apply(rules, DIESEL_INTRO, "battle_start", 0.0, part_destructible=False)

    assert ceiling.total_for("sustained_damage_up", _target(DIESEL_INTRO), 100.0) == pytest.approx(0.6804)
    assert floor.total_for("sustained_damage_up", _target(DIESEL_INTRO), 100.0) == 0.0


# --- Full Charge stacks -------------------------------------------------


def test_full_charge_stacks_cap_at_two_and_expire_after_three_seconds():
    specs = build_diesel_resource_specs(VALUES)
    assert len(specs) == 1
    spec = specs[0]
    assert spec.fill == ("per_shot_every", 1)
    assert spec.cap == 2

    buff = spec.buffs[0]
    assert buff.stat == "sustained_damage_up"
    assert buff.scope == "self"
    assert buff.lifetime == 3.0
    assert buff.value_fn(1) == 3.1814
    assert buff.value_fn(2) == 6.3628


# --- Damage-over-time nukes ---------------------------------------------


def test_full_burst_dot_ticks_once_per_second_for_nine_seconds():
    spec = build_diesel_full_burst_dot(VALUES)[0]
    assert spec["percent"] == 63.33
    assert spec["damage_type"] == "sustained"

    context = SquadContext([SquadMember(DIESEL_HIGHLIGHT, 3, "Fire", "RL")])
    context.full_burst_windows = [(5.0, 15.0), (30.0, 40.0)]
    times = spec["schedule"](context, 180.0)

    assert times[:9] == [5.0, 6.0, 7.0, 8.0, 9.0, 10.0, 11.0, 12.0, 13.0]
    assert len(times) == 18


def test_burst_dot_sums_the_all_enemy_and_stage_target_ticks():
    # A raid is a single boss, so it is always the stage target and takes both.
    spec = build_diesel_burst_dot(VALUES)[0]
    assert spec["base_percent"] == 199.63
    assert spec["tick_count"] == 9
    assert spec["tick_interval"] == 1.0
    assert spec["damage_type"] == "sustained"


def test_burst_puts_damage_taken_up_on_the_boss_for_ten_seconds():
    registry = _apply(
        build_diesel_highlight_rules(VALUES), DIESEL_HIGHLIGHT, "own_burst_activate", 20.0
    )
    assert registry.total_for("damage_taken_up", _target(DIESEL_HIGHLIGHT), 25.0) == 0.2509
    assert registry.total_for("damage_taken_up", _target(DIESEL_HIGHLIGHT), 30.1) == 0.0


def test_both_modes_share_every_non_state_effect():
    intro = build_diesel_intro_rules(VALUES)
    highlight = build_diesel_highlight_rules(VALUES)
    assert len(intro) == len(highlight)
    assert build_diesel_burst_dot(VALUES) == build_diesel_burst_dot(VALUES)
