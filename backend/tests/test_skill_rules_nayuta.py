from app.effects import EffectRegistry
from app.skill_rules.nayuta import (
    asceticism_burst_percent,
    build_memory_incineration_scheduled_nukes,
    build_memory_incineration_weapon_mode_schedule,
    build_nayuta_rules,
)
from app.squad_engine import SquadContext, SquadMember, fire_trigger

# Real skill level 10 values from lootandwaifus.com. Migrated off dotgg (whose
# abbreviated text has no slot at all for Memory Incineration's charge time or
# Full Charge multiplier - the rapi-red-hood precedent), so the slot numbering
# below is lootandwaifus' left-to-right order.
HYPOCRISY = {
    "description_value_01": "9",       # self Indomitability sec (not modeled)
    "description_value_02": "1",       # activation count (not modeled)
    "description_value_03": "25.15",   # squad core-damage %
    "description_value_04": "5",       # duration
    "description_value_05": "30.16",   # squad ATK % of caster's ATK
    "description_value_06": "5",       # duration
    "description_value_07": "5",       # HP-recovery share sec (not modeled)
    "description_value_08": "25",      # self HP recovery % (not modeled)
    "description_value_09": "150",     # Full-Charge-in-Memory-Incineration nuke %
    "description_value_10": "380.46",  # stage-target additional %
}
IMPERMANENCE = {
    "description_value_01": "3",       # stack interval sec
    "description_value_02": "1.4",     # Hit Rate % (not modeled)
    "description_value_03": "30",      # max stacks
    "description_value_04": "1",       # "Stage 1" label, not a value
    "description_value_05": "2",       # Stage 1 threshold
    "description_value_06": "15.2",    # Stage 1 self ATK %
    "description_value_07": "2",       # "Stage 2" label, not a value
    "description_value_08": "10",      # Stage 2 threshold
    "description_value_09": "20.27",   # Stage 2 self Attack Damage %
    "description_value_10": "3",       # "Stage 3" label, not a value
    "description_value_11": "30",      # Stage 3 threshold (== cap)
    "description_value_12": "21.05",   # Stage 3 self core-damage %
}
ASCETICISM = {
    "description_value_01": "35.45",   # squad Attack Damage %
    "description_value_02": "15",      # duration
    "description_value_03": "645.33",  # burst nuke % of final ATK
    "description_value_04": "1.8",     # Memory Incineration charge time (fixed)
    "description_value_05": "275.18",  # Memory Incineration damage %
    "description_value_06": "250",     # Full Charge Damage, % of that damage
    "description_value_07": "10",      # Memory Incineration duration
    "description_value_08": "10",      # unlimited-ammo duration (same window)
}


def make_context():
    return SquadContext([
        SquadMember("nayuta", burst_tier=2, element="Wind"),
        SquadMember("ally", burst_tier=3, element="Fire"),
    ])


def build(caster_atk=10000):
    return build_nayuta_rules({
        "hypocrisy": HYPOCRISY,
        "impermanence": IMPERMANENCE,
        "asceticism": ASCETICISM,
        "caster_atk": caster_atk,
    })


NAYUTA = {"slug": "nayuta", "element": "Wind"}
ALLY = {"slug": "ally", "element": "Fire"}


def test_burst_percent_is_64533():
    assert asceticism_burst_percent({"asceticism": ASCETICISM}) == 645.33


def test_hypocrisy_squad_buffs_are_active_from_the_first_trigger_at_3_sec():
    ctx = make_context()
    registry = EffectRegistry()
    fire_trigger("battle_start", {"nayuta": build()}, ctx, registry, time=0.0)

    assert registry.total_for("other_core_damage_sources", ALLY, now=2.9) == 0.0
    assert round(registry.total_for("other_core_damage_sources", ALLY, now=3.0), 4) == 0.2515
    assert registry.total_for("flat_atk", ALLY, now=3.0) == 3016.0  # 30.16% of 10000
    # stays active for the rest of the fight (overlapping re-triggers)
    assert round(registry.total_for("other_core_damage_sources", ALLY, now=179.0), 4) == 0.2515


def test_impermanence_stage_buffs_activate_at_their_fixed_stack_threshold_times():
    ctx = make_context()
    registry = EffectRegistry()
    fire_trigger("battle_start", {"nayuta": build()}, ctx, registry, time=0.0)

    # Stage 1 (reaches 2 stacks) at t=6s, self-scoped ATK.
    assert registry.total_for("atk_percent", NAYUTA, now=5.9) == 0.0
    assert round(registry.total_for("atk_percent", NAYUTA, now=6.0), 4) == 0.152
    assert registry.total_for("atk_percent", ALLY, now=6.0) == 0.0  # self-only, not squad

    # Stage 2 (reaches 10 stacks) at t=30s, self-scoped Attack Damage.
    assert registry.total_for("attack_damage_up", NAYUTA, now=29.9) == 0.0
    assert round(registry.total_for("attack_damage_up", NAYUTA, now=30.0), 4) == 0.2027

    # Stage 3 (reaches the 30-stack cap) at t=90s, self-scoped core damage,
    # stacking on top of Hypocrisy's squad-wide core-damage share.
    assert round(registry.total_for("other_core_damage_sources", NAYUTA, now=89.9), 4) == 0.2515
    assert round(registry.total_for("other_core_damage_sources", NAYUTA, now=90.0), 4) == 0.462


def test_asceticism_grants_squad_attack_damage_on_own_burst():
    ctx = make_context()
    registry = EffectRegistry()
    fire_trigger("own_burst_activate", {"nayuta": build()}, ctx, registry, time=5.0)

    assert round(registry.total_for("attack_damage_up", ALLY, now=5.0), 4) == 0.3545
    assert registry.total_for("attack_damage_up", ALLY, now=20.1) == 0.0


def test_memory_incineration_segment_is_a_fixed_cadence_charge_window():
    schedule = build_memory_incineration_weapon_mode_schedule({"asceticism": ASCETICISM})
    ctx = make_context()
    ctx.burst_times["nayuta"] = [20.0, 60.0]

    segments = schedule(ctx, 180.0)
    assert [seg["start"] for seg in segments] == [20.0, 60.0]
    assert [seg["end"] for seg in segments] == [30.0, 70.0]  # 10 sec duration

    profile = segments[0]["profile"]
    assert profile["damage_percent"] == 275.18
    assert profile["charge_damage_percent"] == 250  # "250% of Damage" -> 2.5x
    # "Charge time: Fixed at 1.8 sec" - an explicit rate_of_fire takes no cadence
    # buffs, which is what "fixed" means; a charge_time profile would let an
    # ally's Charge Speed buff move it.
    assert profile["rate_of_fire"] == 1 / 1.8
    assert "charge_time" not in profile


def test_memory_incineration_full_charge_nukes_fire_once_per_charge_in_window():
    spec, = build_memory_incineration_scheduled_nukes(
        {"hypocrisy": HYPOCRISY, "asceticism": ASCETICISM})
    # 150% + 380.46% additional: the raid's only enemy IS the stage target.
    assert round(spec["percent"], 2) == 530.46
    # The trigger is a Full Charge that takes 1.8 sec and can only happen after
    # her burst, so the hit is always computed inside Full Burst - both halves
    # collect the bonus, whatever their wording (Fienn, 2026-07-26).
    assert spec["full_burst_bonus_eligible"] is True

    ctx = make_context()
    ctx.burst_times["nayuta"] = [20.0]
    ticks = [round(t, 2) for t in spec["schedule"](ctx, 180.0)]

    # Full charges land every 1.8 sec inside the 10-sec window: 5 of them.
    assert ticks == [21.8, 23.6, 25.4, 27.2, 29.0]


def test_memory_incineration_nukes_stop_at_the_end_of_the_fight():
    spec, = build_memory_incineration_scheduled_nukes(
        {"hypocrisy": HYPOCRISY, "asceticism": ASCETICISM})
    ctx = make_context()
    ctx.burst_times["nayuta"] = [20.0]

    assert [round(t, 2) for t in spec["schedule"](ctx, 25.0)] == [21.8, 23.6]
