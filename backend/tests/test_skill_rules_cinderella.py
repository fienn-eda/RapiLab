"""Cinderella (slug "cinderella"), Burst-3 Rocket Launcher attacker. Real
max-level (base-skill) figures from lootandwaifus, slots numbered left-to-right
per skill (fixed reference numbers like "Burst Stage 3" are not data slots).
"""
import pytest

from app.effects import EffectRegistry, ResourceSpec
from app.raid_simulator import simulate_raid
from app.skill_rules.cinderella import (
    GLASS_SLIPPERS_HIT_COUNT,
    build_beautiful_max_hp_rules,
    build_beautiful_resources,
    build_flawless_glass_charge_speed_rules,
    build_flawless_glass_per_shot_rules,
    build_flawless_glass_rules,
    flawless_glass_charge_speed,
    build_glass_slippers_resource_scaled_nuke,
    glass_slippers_burst_percent,
)
from app.squad_engine import SquadContext, SquadMember, fire_trigger

CINDERELLA = {
    "flawless_glass": {
        "description_value_01": "2.71", "description_value_02": "10",
        "description_value_03": "100", "description_value_04": "136.6",
    },
    "dirt_resistant_mirror": {
        "description_value_01": "96", "description_value_02": "96",
        "description_value_03": "3", "description_value_04": "1.6", "description_value_05": "12",
    },
    "glass_slippers": {
        "description_value_01": "1365.92", "description_value_02": "10", "description_value_03": "28.9",
    },
}
CASTER_MAX_HP = 50000

CINDY = {"slug": "cinderella", "element": "Fire"}


def make_context():
    return SquadContext([
        SquadMember("cinderella", burst_tier=3, element="Fire"),
        SquadMember("ally", burst_tier=1, element="Iron"),
    ])


def test_glass_slippers_hit_count_is_ten():
    assert GLASS_SLIPPERS_HIT_COUNT == 10


def test_glass_slippers_burst_percent_is_per_hit_base():
    assert glass_slippers_burst_percent(CINDERELLA) == 1365.92


def test_flawless_glass_self_atk_from_max_hp_on_own_burst():
    ctx = make_context()
    reg = EffectRegistry()
    for rule in build_flawless_glass_rules(CINDERELLA, CASTER_MAX_HP):
        rule.action(ctx, "cinderella", 10.0, reg)
    # 2.71% of 50000 = 1355, as flat_atk for 10s.
    assert round(reg.total_for("flat_atk", CINDY, now=10.0), 4) == 1355.0
    assert reg.total_for("flat_atk", CINDY, now=20.1) == 0.0


def _fire_flawless_glass(burster, time=10.0):
    """Fire her Flawless Glass rules for the cycle `burster` took Stage 3 in."""
    ctx = SquadContext([
        SquadMember("cinderella", burst_tier=3, element="Fire"),
        SquadMember("other-b3", burst_tier=3, element="Water"),
        SquadMember("ally", burst_tier=1, element="Iron"),
    ])
    ctx.last_burst_slug = burster
    reg = EffectRegistry()
    fire_trigger("ally_burst_activate",
                 {"cinderella": build_flawless_glass_rules(CINDERELLA, CASTER_MAX_HP)},
                 ctx, reg, time)
    return reg


def test_flawless_glass_fires_in_a_cycle_another_burst_three_took():
    # "Activates when entering Burst Stage 3" is about the STAGE, not the
    # caster - she still gets it in the cycles an allied Burst 3 bursts.
    assert round(_fire_flawless_glass("other-b3").total_for("flat_atk", CINDY, 10.0), 4) == 1355.0


def test_flawless_glass_still_fires_in_her_own_burst_cycles():
    assert round(_fire_flawless_glass("cinderella").total_for("flat_atk", CINDY, 10.0), 4) == 1355.0


def test_flawless_glass_does_not_fire_on_a_lower_stage():
    assert _fire_flawless_glass("ally").total_for("flat_atk", CINDY, 10.0) == 0.0


def test_flawless_glass_per_shot_nuke_fires_every_shot():
    ps = build_flawless_glass_per_shot_rules(CINDERELLA)
    assert len(ps) == 1
    threshold, mode, rules = ps[0]
    assert (threshold, mode) == (1, "every")
    reg = EffectRegistry()
    rules[0].action(make_context(), "cinderella", 0.0, reg)
    pulses = reg.drain_pulses("instant_damage_percent")
    assert len(pulses) == 1 and pulses[0].value == 136.6


def test_flawless_glass_per_shot_nuke_takes_the_full_burst_bonus():
    # Its own text says "as additional damage", and a shot has a known time, so
    # the instance opts in and the simulator checks it against the FB window.
    _, _, rules = build_flawless_glass_per_shot_rules(CINDERELLA)[0]
    reg = EffectRegistry()
    rules[0].action(make_context(), "cinderella", 0.0, reg)


def test_beautiful_resource_ticks_every_3_sec_capped_at_12():
    specs = build_beautiful_resources(CINDERELLA)
    assert len(specs) == 1
    spec = specs[0]
    assert isinstance(spec, ResourceSpec)
    assert spec.name == "beautiful"
    assert spec.fill == ("periodic", 3.0)
    assert spec.cap == 12
    # The resource carries the COUNT only. Its Max HP per stack rides a
    # battle-start rule instead (see below): resource buffs resolve after the
    # shot loop, too late for Flawless Glass's live Max HP read.
    assert spec.buffs == []


def test_beautiful_max_hp_ramps_one_stack_every_three_seconds_to_twelve():
    rules = build_beautiful_max_hp_rules(CINDERELLA, CASTER_MAX_HP)
    reg = EffectRegistry()
    for rule in rules:
        rule.action(make_context(), "cinderella", 0.0, reg)
    per_stack = CASTER_MAX_HP * 0.016  # 1.6% of final Max HP per stack
    assert reg.total_for("flat_max_hp", CINDY, now=0.0) == 0.0  # first tick is at t=3
    assert round(reg.total_for("flat_max_hp", CINDY, now=10.0), 4) == round(3 * per_stack, 4)
    assert round(reg.total_for("flat_max_hp", CINDY, now=36.0), 4) == round(12 * per_stack, 4)
    # Capped at 12 and continuous - it never grows past the cap, never expires.
    assert round(reg.total_for("flat_max_hp", CINDY, now=179.0), 4) == round(12 * per_stack, 4)


def test_beautiful_max_hp_feeds_flawless_glass_own_atk():
    # The two bullets are wired together: her ATK buff reads LIVE Max HP, so a
    # burst after the ramp is worth 12 stacks more ATK than one at t=0.
    reg = EffectRegistry()
    for rule in build_beautiful_max_hp_rules(CINDERELLA, CASTER_MAX_HP):
        rule.action(make_context(), "cinderella", 0.0, reg)
    ctx = make_context()
    ctx.last_burst_slug = "cinderella"
    for rule in build_flawless_glass_rules(CINDERELLA, CASTER_MAX_HP):
        rule.action(ctx, "cinderella", 40.0, reg)
    live_max_hp = CASTER_MAX_HP * (1 + 12 * 0.016)
    assert round(reg.total_for("flat_atk", CINDY, now=40.0), 4) == round(live_max_hp * 0.0271, 4)


def test_glass_slippers_additional_hit_mirrors_beautiful_stack_count():
    specs = build_glass_slippers_resource_scaled_nuke(CINDERELLA)
    assert len(specs) == 1
    spec = specs[0]
    assert spec["resource"] == "beautiful"
    assert spec["cap"] == 12
    assert spec["base_percent"] == 28.9
    assert spec["scale_fn"](7) == 7  # mirrors the count directly
    assert (spec["tick_count"], spec["tick_interval"]) == (1, 0.0)


def test_cinderella_end_to_end_burst_hits_and_mirrored_additional_hit():
    # Full chain through simulate_raid: Beautiful ticks every 3s from battle
    # start, Glass Slippers fires 10 separate 1365.92% hits, and the mirrored
    # additional hit scales with however many Beautiful stacks exist by the
    # (first) burst-fire time.
    deck = [
        {"slug": "buffer", "burst_tier": 1, "element": "Iron", "cooldown": 20.0},
        {"slug": "midtier", "burst_tier": 2, "element": "Iron", "cooldown": 20.0},
        {"slug": "cinderella", "burst_tier": 3, "element": "Fire", "cooldown": 40.0},
    ]
    base_stats = {
        "buffer": {"atk": 0, "def": 0, "max_hp": 0},
        "midtier": {"atk": 0, "def": 0, "max_hp": 0},
        "cinderella": {"atk": 10000, "def": 0, "max_hp": CASTER_MAX_HP},
    }
    weapon_stats = {
        "cinderella": {"weapon": "RL", "damage_percent": 10.0, "max_ammo": 20,
                       "reload_time": 1.0, "charge_time": 1.0, "charge_damage_percent": 100.0},
    }
    result = simulate_raid(
        deck,
        {"buffer": [], "midtier": [], "cinderella": build_flawless_glass_rules(CINDERELLA, CASTER_MAX_HP)},
        burst_damage_percents={"cinderella": glass_slippers_burst_percent(CINDERELLA)},
        base_stats=base_stats,
        enemy_def=0, gauge_charge_time=9.0, fight_duration=15.0, mode="auto", base_crit_rate=0.0,
        weapon_stats=weapon_stats,
        per_shot_rules={"cinderella": build_flawless_glass_per_shot_rules(CINDERELLA)},
        resource_specs={"cinderella": build_beautiful_resources(CINDERELLA)},
        resource_scaled_nukes={"cinderella": build_glass_slippers_resource_scaled_nuke(CINDERELLA)},
        burst_hit_counts={"cinderella": GLASS_SLIPPERS_HIT_COUNT},
    )
    burst_hits = [e for e in result["damage_log"] if e["source"] == "burst"]
    mirrored = [e for e in result["damage_log"] if e["source"] == "resource_scaled_nuke"]
    per_shot_hits = [e for e in result["damage_log"] if e["source"] == "per_shot_nuke"]
    # Flawless Glass's flat_atk (2.71% of 50000 = 1355) fires in the SAME
    # on_tier_fire call as the burst nuke and the mirrored hit, so both are
    # boosted by it: offense = 10000 + 1355 = 11355.
    offense = 10000 + 50000 * 0.0271
    assert len(burst_hits) == GLASS_SLIPPERS_HIT_COUNT
    assert all(round(h["damage"], 4) == round(offense * 13.6592, 4) for h in burst_hits)
    # burst fires at t=9 (gauge_charge_time); Beautiful ticks at t=3,6,9 -> 3
    # stacks by then -> mirrored hit percent = 28.9 * 3.
    assert len(mirrored) == 1
    assert round(mirrored[0]["damage"], 4) == round(offense * (28.9 * 3 / 100), 4)
    assert len(per_shot_hits) > 0  # every full-charge shot deals the 136.6% additional hit


# Module-level fixture aliases so the assembly verification harness
# (test_skill_value_assembly.py) can resolve each sub-skill fixture by name.
FLAWLESS_GLASS = CINDERELLA["flawless_glass"]
DIRT_RESISTANT_MIRROR = CINDERELLA["dirt_resistant_mirror"]
GLASS_SLIPPERS = CINDERELLA["glass_slippers"]


def test_flawless_glass_charge_speed_is_the_raw_skill_value():
    # No back-solving any more: attack_rate models the real shortening rule and
    # carries the floor, so the skill's own +100% is what gets handed over.
    assert flawless_glass_charge_speed(CINDERELLA) == pytest.approx(1.0)


def test_flawless_glass_reproduces_the_measured_shots_per_ten_seconds():
    """Fienn measured 29-30 shots in 10 sec with the buff up and no reload.

    Her charge really does reach zero, so what the reading actually timed was
    her weapon's own 180 rounds/min - 0.33333 sec, exactly 30 shots, the top of
    that range. The engine used to read it as a pause of 10/29 sec and generalise
    it to every charge weapon (attack_rate.CHARGE_ROUNDS_PER_MINUTE)."""
    from app.attack_rate import charge_interval_floor_for, charge_time_with_speed
    interval = charge_time_with_speed(
        1.0, flawless_glass_charge_speed(CINDERELLA),
        interval_floor=charge_interval_floor_for("cinderella"))
    assert 10.0 / interval == pytest.approx(29.5, abs=0.5)  # measured 29-30


def test_flawless_glass_charge_speed_is_a_permanent_self_buff():
    rules = {"cinderella": build_flawless_glass_charge_speed_rules(CINDERELLA)}
    ctx = SquadContext([
        SquadMember("cinderella", burst_tier=3, element="Fire"),
        SquadMember("ally", burst_tier=1, element="Iron"),
    ])
    reg = EffectRegistry()
    fire_trigger("battle_start", rules, ctx, reg, time=0.0)

    cind = {"slug": "cinderella", "element": "Fire"}
    assert reg.total_for("charge_speed_percent", cind, now=170.0) == pytest.approx(1.0)
    # self-scoped: an ally's cadence is untouched
    assert reg.total_for("charge_speed_percent", {"slug": "ally", "element": "Iron"}, now=0.0) == 0.0
