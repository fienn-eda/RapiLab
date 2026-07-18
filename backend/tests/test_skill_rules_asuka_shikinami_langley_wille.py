"""Real max-level (base-skill) figures from lootandwaifus, slots numbered
left-to-right per skill (fixed reference counts like "1 enemy unit(s)" or
"for 1 time(s)" are not data slots).
"""
from app.effects import EffectRegistry
from app.raid_simulator import simulate_raid
from app.skill_rules.asuka_shikinami_langley_wille import (
    build_anti_at_field_per_shot_rules,
    build_anti_at_field_resources,
    build_annihilation_dynamic_hit_count_nukes,
    build_annihilation_state_rules,
    build_emergency_repair_rules,
)
from app.squad_engine import SquadContext, SquadMember, fire_trigger

ASUKA_VALUES = {
    # Full left-to-right transcription (no skips): 50-shot nuke threshold,
    # its 471.86% damage, "2 enemy unit(s)", "every 10 shot(s)", the windowed
    # 15.62% damage, and the 0.83%/30s/30-stack Damage Taken debuff.
    "anti_at_field": {
        "description_value_01": "50", "description_value_02": "471.86",
        "description_value_03": "2", "description_value_04": "10",
        "description_value_05": "15.62", "description_value_06": "0.83",
        "description_value_07": "30", "description_value_08": "30",
    },
    "emergency_repair": {
        "description_value_01": "30.97", "description_value_02": "10",
        "description_value_03": "100", "description_value_04": "3",
        "description_value_05": "100", "description_value_06": "3.77",
        "description_value_07": "3", "description_value_08": "60",
        "description_value_09": "1",
    },
    "annihilation_state": {
        "description_value_01": "40", "description_value_02": "9",
        "description_value_03": "21", "description_value_04": "46.8",
        "description_value_05": "36", "description_value_06": "6.62",
    },
}

# Module-level fixture names for the assembly verification harness.
ANTI_AT_FIELD = ASUKA_VALUES["anti_at_field"]
EMERGENCY_REPAIR = ASUKA_VALUES["emergency_repair"]
ANNIHILATION_STATE = ASUKA_VALUES["annihilation_state"]

ASUKA = {"slug": "asuka-shikinami-langley-wille", "element": "Wind"}
ALLY = {"slug": "ally", "element": "Iron"}


def make_context():
    return SquadContext([
        SquadMember("asuka-shikinami-langley-wille", burst_tier=3, element="Wind"),
        SquadMember("ally", burst_tier=1, element="Iron"),
    ])


def test_anti_at_field_resource_fills_during_own_status_window_and_resets_delayed():
    specs = build_anti_at_field_resources(ASUKA_VALUES)
    assert len(specs) == 1
    spec = specs[0]
    assert spec.name == "anti_at_field"
    assert spec.fill == ("per_shot_every_during_own_status_window", 10, 9.0)
    assert spec.cap == 30
    assert spec.resets == [{"trigger": "own_burst_delayed", "delay": 9.0, "value": 0}]


def test_anti_at_field_damage_taken_buff_is_per_stack_and_squad_scoped():
    spec = build_anti_at_field_resources(ASUKA_VALUES)[0]
    assert len(spec.buffs) == 1
    buff = spec.buffs[0]
    assert buff.stat == "damage_taken_up"
    assert buff.scope == "squad"
    assert buff.lifetime == 30.0
    assert round(buff.value_fn(10), 4) == round(0.083, 4)  # 10 stacks * 0.83%


def test_anti_at_field_per_shot_nuke_fires_every_50_shots_full_burst_bonus_eligible():
    ps = build_anti_at_field_per_shot_rules(ASUKA_VALUES)
    assert len(ps) == 2
    threshold, mode, rules = ps[0]
    assert (threshold, mode) == (50, "every")
    reg = EffectRegistry()
    rules[0].action(make_context(), "asuka-shikinami-langley-wille", 0.0, reg)
    pulses = reg.drain_pulses("instant_damage_percent")
    assert len(pulses) == 1
    assert pulses[0].value == 471.86
    assert pulses[0].full_burst_bonus_eligible is True


def test_anti_at_field_windowed_nuke_gated_to_annihilation_state():
    ps = build_anti_at_field_per_shot_rules(ASUKA_VALUES)
    threshold, mode, rules = ps[1]
    # (N, window_duration) - every 10 shots inside her own 9s status window
    assert threshold == (10, 9.0)
    assert mode == "every_during_own_status_window"
    reg = EffectRegistry()
    rules[0].action(make_context(), "asuka-shikinami-langley-wille", 5.0, reg)
    pulses = reg.drain_pulses("instant_damage_percent")
    assert len(pulses) == 1
    assert pulses[0].value == 15.62
    # "as damage", not "as additional damage" - no Full Burst Bonus
    assert pulses[0].full_burst_bonus_eligible is False


def test_annihilation_state_self_buffs_trigger_on_own_burst_activate():
    ctx = make_context()
    reg = EffectRegistry()
    for rule in build_annihilation_state_rules(ASUKA_VALUES, caster_atk=10000):
        assert rule.trigger == "own_burst_activate"
        rule.action(ctx, "asuka-shikinami-langley-wille", 5.0, reg)
    assert round(reg.total_for("flat_atk", ASUKA, now=5.0), 4) == round(0.468 * 10000, 4)
    assert round(reg.total_for("attack_damage_up", ASUKA, now=5.0), 4) == 0.36
    assert reg.total_for("flat_atk", ASUKA, now=14.1) == 0.0  # 9s duration


def test_emergency_repair_buff_only_fires_if_own_burst_fired_this_cycle():
    ctx = make_context()
    rules = build_emergency_repair_rules(ASUKA_VALUES)

    reg_without = EffectRegistry()
    fire_trigger("full_burst_enter", {"asuka-shikinami-langley-wille": rules}, ctx, reg_without, time=5.0)
    assert reg_without.total_for("attack_damage_up", ASUKA, now=5.0) == 0.0

    ctx.burst_used_this_cycle.add("asuka-shikinami-langley-wille")
    reg_with = EffectRegistry()
    fire_trigger("full_burst_enter", {"asuka-shikinami-langley-wille": rules}, ctx, reg_with, time=5.0)
    assert round(reg_with.total_for("attack_damage_up", ASUKA, now=5.0), 4) == 0.3097
    assert reg_with.total_for("attack_damage_up", ASUKA, now=15.1) == 0.0  # 10s duration


def test_annihilation_dynamic_hit_count_nuke_spec():
    specs = build_annihilation_dynamic_hit_count_nukes(ASUKA_VALUES)
    assert len(specs) == 1
    spec = specs[0]
    assert spec["resource"] == "anti_at_field"
    assert spec["base_percent"] == 6.62
    assert spec["fire_delay"] == 9.0
    assert spec["full_burst_bonus_eligible"] is True


def test_asuka_end_to_end_annihilation_nuke_scales_with_capped_stacks_and_gets_full_burst_bonus():
    # MG fires 60/s; her burst at t=5.0 opens a 9s Annihilation window
    # [5.0, 14.0) during which Anti A.T. Field fills every 10 shots - it caps
    # at 30 stacks well before the window closes (300 of ~540 possible
    # in-window shots), so Annihilation's hit count is deterministically 30.
    # The delayed nuke fires at t=14.0, inside the Full Burst window
    # [5.0, 15.0), so it also gets the +50% Full Burst Bonus.
    deck = [
        {"slug": "buffer", "burst_tier": 1, "element": "Iron", "cooldown": 20.0},
        {"slug": "midtier", "burst_tier": 2, "element": "Iron", "cooldown": 20.0},
        {"slug": "asuka-shikinami-langley-wille", "burst_tier": 3, "element": "Wind", "cooldown": 40.0},
    ]
    base_stats = {
        "buffer": {"atk": 0, "def": 0, "max_hp": 0},
        "midtier": {"atk": 0, "def": 0, "max_hp": 0},
        "asuka-shikinami-langley-wille": {"atk": 10000, "def": 0, "max_hp": 0},
    }
    weapon_stats = {
        "asuka-shikinami-langley-wille": {
            "weapon": "MG", "damage_percent": 5.0, "max_ammo": 3000,
            "reload_time": 1.0, "charge_time": 0.0, "charge_damage_percent": 0.0,
        },
    }
    result = simulate_raid(
        deck,
        {"buffer": [], "midtier": [], "asuka-shikinami-langley-wille": []},
        burst_damage_percents={}, base_stats=base_stats,
        enemy_def=0, gauge_charge_time=5.0, fight_duration=20.0, mode="auto", base_crit_rate=0.0,
        weapon_stats=weapon_stats,
        resource_specs={"asuka-shikinami-langley-wille": build_anti_at_field_resources(ASUKA_VALUES)},
        dynamic_hit_count_nukes={
            "asuka-shikinami-langley-wille": build_annihilation_dynamic_hit_count_nukes(ASUKA_VALUES)
        },
    )
    hits = [e for e in result["damage_log"] if e["source"] == "dynamic_hit_count_nuke"]
    assert len(hits) == 30
    assert all(round(h["time"], 4) == 14.0 for h in hits)
    # 10000 * 6.62% * (1 + full_burst_bonus*0.5) = 662 * 1.5
    assert all(round(h["damage"], 4) == 993.0 for h in hits)
