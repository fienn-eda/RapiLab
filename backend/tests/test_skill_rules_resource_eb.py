"""Burst-3 resource batch (gap #2 Pattern A beachheads): Modernia (timed capped
stacks) and Guillotine: Winter Slayer (permanent-accumulate + count-scaled +
derived level + core-conditional fill). Real max-level base-skill figures from
lootandwaifus, slots numbered left-to-right per skill.
"""
from app.effects import EffectRegistry
from app.raid_simulator import simulate_raid
from app.skill_rules.guillotine_winter_slayer import (
    _hero_level,
    build_guillotine_resource_scaled_nukes,
    build_guillotine_resources,
    build_guillotine_rules,
)
from app.skill_rules.modernia import build_modernia_per_shot_rules, build_modernia_resources
from app.squad_engine import SquadContext, SquadMember, fire_trigger


def deck_ctx(src_slug, element):
    return SquadContext([
        SquadMember(src_slug, burst_tier=3, element=element),
        SquadMember("water-ally", burst_tier=1, element="Water"),
        SquadMember("iron-ally", burst_tier=2, element="Iron"),
    ])


# --- Modernia (MG/Fire): timed capped stacks ---
MODERNIA = {
    "high_speed_evolution": {
        "description_value_01": "3.05", "description_value_02": "200",
        "description_value_03": "14.25", "description_value_04": "5", "description_value_05": "10",
        "description_value_06": "5.04", "description_value_07": "5", "description_value_08": "10",
    },
    "giant_leap": {
        "description_value_01": "8.56",   # all-ally Hit Rate % (inert, not modeled)
        "description_value_02": "15",     # its duration
        "description_value_03": "200",    # normal-attack-hit threshold
        "description_value_04": "29.38",  # self ATK %
        "description_value_05": "10",     # its duration
    },
}

# Module-level aliases so the assembly verification harness
# (test_skill_value_assembly.py) can resolve the fixtures by name.
HIGH_SPEED_EVOLUTION = MODERNIA["high_speed_evolution"]
GIANT_LEAP = MODERNIA["giant_leap"]


def test_modernia_evolution_resource_is_timed_capped_crit_and_ammo():
    specs = build_modernia_resources(MODERNIA)
    assert len(specs) == 1
    spec = specs[0]
    assert spec.name == "evolution"
    assert spec.fill == ("per_shot_every", 200)
    assert spec.cap == 5
    crit, ammo = spec.buffs
    assert crit.stat == "other_critical_damage_sources"
    assert crit.lifetime == 10.0  # timed, not permanent
    # value_fn scales by the (already-capped) stack count; capping is the
    # resolution pass's job (resource_count clamps before value_fn).
    assert round(crit.value_fn(3), 4) == round(0.1425 * 3, 4)
    assert ammo.stat == "max_ammo_percent"
    assert ammo.lifetime == 10.0
    assert round(ammo.value_fn(5), 4) == round(0.0504 * 5, 4)


def test_modernia_per_hit_additional_damage_every_shot():
    ps = build_modernia_per_shot_rules(MODERNIA)
    assert len(ps) == 2
    threshold, mode, rules = ps[0]
    assert (threshold, mode) == (1, "every")
    reg = EffectRegistry()
    rules[0].action(deck_ctx("modernia", "Fire"), "modernia", 0.0, reg)
    pulses = reg.drain_pulses("instant_damage_percent")
    assert len(pulses) == 1 and pulses[0].value == 3.05


def test_modernia_giant_leap_self_atk_every_200_hits_from_battle_start():
    # Giant Leap's self ATK fires on every 200th normal hit counted from
    # battle start, NOT window-gated on the Hit Rate status (Fienn
    # 2026-07-18, in-game behaviour overrides the skill text).
    _, (threshold, mode, rules) = build_modernia_per_shot_rules(MODERNIA)
    assert (threshold, mode) == (200, "every")
    ctx = deck_ctx("modernia", "Fire")
    reg = EffectRegistry()
    for rule in rules:
        rule.action(ctx, "modernia", 5.0, reg)

    modernia = {"slug": "modernia", "element": "Fire"}
    ally = {"slug": "iron-ally", "element": "Iron"}
    assert round(reg.total_for("atk_percent", modernia, now=5.0), 4) == 0.2938
    assert reg.total_for("atk_percent", ally, now=5.0) == 0.0  # self-only
    assert reg.total_for("atk_percent", modernia, now=15.1) == 0.0  # 10s duration

    # MG fires 60/s, so consecutive 200-hit marks land within the 10s window
    # and must refresh, not stack.
    for rule in rules:
        rule.action(ctx, "modernia", 8.0, reg)
    assert round(reg.total_for("atk_percent", modernia, now=8.0), 4) == 0.2938


# --- Guillotine: Winter Slayer (AR/Water): permanent + count-scaled ---
GUILLOTINE = {
    "heros_fate": {
        "description_value_01": "10", "description_value_02": "11",
        "description_value_03": "10.26", "description_value_04": "2.44",
        "description_value_05": "1.16", "description_value_06": "0.91",
    },
    "heros_gift": {
        "description_value_01": "6", "description_value_02": "1.81", "description_value_03": "100",
        "description_value_04": "3", "description_value_05": "1.81", "description_value_06": "100",
        "description_value_07": "2", "description_value_08": "7.46",
    },
    "extermination": {
        "description_value_01": "10.14", "description_value_02": "10",
        "description_value_03": "18.75", "description_value_04": "10",
        "description_value_05": "1", "description_value_06": "20.87", "description_value_07": "10",
    },
    "caster_atk": 80000,
}


def test_hero_level_starts_at_one_and_caps_at_eleven():
    assert _hero_level(0) == 1
    assert _hero_level(9) == 1
    assert _hero_level(10) == 2
    assert _hero_level(100) == 11
    assert _hero_level(200) == 11  # capped


def test_guillotine_exp_resource_fill_is_core_conditional_capped_at_100():
    spec = build_guillotine_resources(GUILLOTINE)[0]
    assert spec.name == "exp"
    assert spec.fill == ("per_shot_every_core", 3, 6)
    assert spec.cap == 100


def test_guillotine_exp_grants_linear_self_atk():
    spec = build_guillotine_resources(GUILLOTINE)[0]
    exp_atk = spec.buffs[0]
    assert exp_atk.stat == "atk_percent" and exp_atk.scope == "self" and exp_atk.lifetime is None
    assert round(exp_atk.value_fn(50), 4) == round(0.0181 * 50, 4)


def test_guillotine_self_elem_advantage_gates_on_hero_level_two():
    spec = build_guillotine_resources(GUILLOTINE)[0]
    level_gate = spec.buffs[1]
    assert level_gate.stat == "other_elemental_bonus" and level_gate.scope == "self"
    assert level_gate.value_fn(5) == 0.0        # EXP 5 -> level 1 -> off
    assert round(level_gate.value_fn(15), 4) == 0.0746  # EXP 15 -> level 2 -> on


def test_guillotine_water_allies_get_level_scaled_elem_and_atk():
    spec = build_guillotine_resources(GUILLOTINE)[0]
    water_elem, water_atk = spec.buffs[2], spec.buffs[3]
    assert water_elem.stat == "other_elemental_bonus" and water_elem.scope == "element:Water"
    assert round(water_elem.value_fn(25), 4) == round(0.0116 * 3, 4)   # EXP 25 -> level 3
    assert water_atk.stat == "flat_atk" and water_atk.scope == "element:Water"
    # ATK buff is 0.91% of the caster's 80000 ATK, per level.
    assert round(water_atk.value_fn(25), 2) == round(0.0091 * 80000 * 3, 2)


def test_guillotine_burst_buffs_water_allies_attack_and_elem_for_ten_sec():
    rules = {"guillotine-winter-slayer": build_guillotine_rules(GUILLOTINE)}
    reg = EffectRegistry()
    ctx = deck_ctx("guillotine-winter-slayer", "Water")
    fire_trigger("own_burst_activate", rules, ctx, reg, 0.0)
    water = {"slug": "water-ally", "element": "Water"}
    iron = {"slug": "iron-ally", "element": "Iron"}
    assert round(reg.total_for("attack_damage_up", water, 0.0), 4) == 0.1014
    assert round(reg.total_for("other_elemental_bonus", water, 0.0), 4) == 0.1875
    assert reg.total_for("attack_damage_up", iron, 0.0) == 0.0  # non-Water excluded
    assert reg.total_for("attack_damage_up", water, 11.0) == 0.0  # 10s expired


def test_guillotine_extermination_dot_spec_ticks_ten_times_scaled_by_hero_level():
    specs = build_guillotine_resource_scaled_nukes(GUILLOTINE)
    assert len(specs) == 1
    spec = specs[0]
    assert spec["resource"] == "exp"
    assert spec["cap"] == 100
    assert spec["base_percent"] == 20.87
    assert (spec["tick_count"], spec["tick_interval"]) == (10, 1.0)
    assert spec["damage_type"] == "sustained"
    assert spec["scale_fn"](25) == _hero_level(25)  # Hero Level derived, not raw EXP
    # Confirmed in-game (Fienn, 2026-07-12): a repeating-tick DoT gets the
    # Full Burst Bonus even without "as additional damage" in its own text
    # (first established via Mana's Fatal Error!) - each tick after the very
    # first is inherently computed after cast time, landing inside the same
    # Full Burst window her burst opens.
    assert spec["resolves_after_cast"] is True


def test_guillotine_extermination_dot_end_to_end_scales_with_hero_level_per_tick():
    # Full chain: EXP accumulates via per-shot fills while the 10-tick DoT is
    # active, so LATER ticks (higher Hero Level) deal more than earlier ones.
    deck = [
        {"slug": "guillotine-winter-slayer", "burst_tier": 3, "element": "Water", "cooldown": 40.0},
        {"slug": "midtier-ally", "burst_tier": 2, "element": "Iron", "cooldown": 20.0},
        {"slug": "iron-ally", "burst_tier": 1, "element": "Iron", "cooldown": 20.0},
    ]
    base_stats = {
        "guillotine-winter-slayer": {"atk": 10000, "def": 0, "max_hp": 0},
        "midtier-ally": {"atk": 0, "def": 0, "max_hp": 0},
        "iron-ally": {"atk": 0, "def": 0, "max_hp": 0},
    }
    ar = {"weapon": "AR", "damage_percent": 10.0, "max_ammo": 10000,
          "reload_time": 1.0, "charge_time": 0.0, "charge_damage_percent": 0.0}
    result = simulate_raid(
        deck,
        {
            "guillotine-winter-slayer": build_guillotine_rules(GUILLOTINE),
            "midtier-ally": [], "iron-ally": [],
        },
        burst_damage_percents={}, base_stats=base_stats,
        enemy_def=0, gauge_charge_time=5.0, fight_duration=20.0, mode="auto", base_crit_rate=0.0,
        core_hittable=True,  # EXP fills every 3 shots
        weapon_stats={"guillotine-winter-slayer": ar},
        resource_specs={"guillotine-winter-slayer": build_guillotine_resources(GUILLOTINE)},
        resource_scaled_nukes={"guillotine-winter-slayer": build_guillotine_resource_scaled_nukes(GUILLOTINE)},
    )
    ticks = sorted(
        [e for e in result["damage_log"] if e["source"] == "resource_scaled_nuke"],
        key=lambda e: e["time"],
    )
    assert len(ticks) == 10
    assert [round(t["time"], 4) for t in ticks] == [round(5.0 + i, 4) for i in range(10)]
    assert all(t["damage_type"] == "sustained" for t in ticks)
    # EXP keeps accumulating over the DoT's 10-sec window (AR fires 12/s, +1
    # EXP every 3 shots) -> Hero Level rises -> later ticks deal >= earlier ones.
    assert ticks[-1]["damage"] >= ticks[0]["damage"]
    assert ticks[-1]["damage"] > ticks[0]["damage"]  # strictly higher given the fire rate


def test_guillotine_exp_ramps_own_normal_attack_damage_end_to_end():
    # Full chain: real ResourceSpec -> resolution pass -> count-scaled self ATK ->
    # her own normal-attack damage climbs as EXP accumulates over the fight.
    deck = [
        {"slug": "guillotine-winter-slayer", "burst_tier": 3, "element": "Water", "cooldown": 40.0},
        {"slug": "iron-ally", "burst_tier": 1, "element": "Iron", "cooldown": 20.0},
    ]
    base_stats = {
        "guillotine-winter-slayer": {"atk": 10000, "def": 0, "max_hp": 0},
        "iron-ally": {"atk": 0, "def": 0, "max_hp": 0},
    }
    ar = {"weapon": "AR", "damage_percent": 10.0, "max_ammo": 10000,
          "reload_time": 1.0, "charge_time": 0.0, "charge_damage_percent": 0.0}
    result = simulate_raid(
        deck,
        {"guillotine-winter-slayer": [], "iron-ally": []},
        burst_damage_percents={}, base_stats=base_stats,
        enemy_def=0, gauge_charge_time=5.0, fight_duration=30.0, mode="auto", base_crit_rate=0.0,
        core_hittable=True,  # EXP fills every 3 shots
        weapon_stats={"guillotine-winter-slayer": ar},
        resource_specs={"guillotine-winter-slayer": build_guillotine_resources(GUILLOTINE)},
    )
    normals = [e["damage"] for e in result["damage_log"]
               if e["source"] == "normal_attack" and e["slug"] == "guillotine-winter-slayer"]
    # Base shot with no EXP = 10000 * 0.1 * 2 (core_hit_bonus) = 2000; later shots
    # are strictly higher as her self ATK ramps with accumulated EXP.
    assert normals[0] == 2000.0
    assert normals[-1] > normals[0]


# Module-level fixture aliases so the assembly verification harness
# (test_skill_value_assembly.py) can resolve each sub-skill fixture by name.
HEROS_FATE = GUILLOTINE["heros_fate"]
HEROS_GIFT = GUILLOTINE["heros_gift"]
EXTERMINATION = GUILLOTINE["extermination"]
