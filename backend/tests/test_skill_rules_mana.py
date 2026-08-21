import pytest

"""Real max-level (base-skill) figures from lootandwaifus, slots numbered
left-to-right per skill (fixed reference counts are not data slots).
"""
from app.effects import EffectRegistry
from app.raid_simulator import simulate_raid
from app.skill_rules.mana import (
    build_fatal_error_dot,
    build_metal_sigma_charge_rules,
    build_fatal_error_self_buff_rules,
    build_metal_gamma_rules,
    build_metal_sigma_rules,
)
from app.squad_engine import SquadContext, SquadMember, fire_trigger

MANA_VALUES = {
    "metal_gamma": {
        "description_value_01": "58.08", "description_value_02": "2.04", "description_value_03": "96",
    },
    "metal_sigma": {
        "description_value_01": "70.4", "description_value_02": "21.12",
        "description_value_03": "10", "description_value_04": "63.36",
        "description_value_05": "0.18", "description_value_06": "10",
        "description_value_07": "70.4",
    },
    "fatal_error": {
        "description_value_01": "52.8", "description_value_02": "10",
        "description_value_03": "396", "description_value_04": "10",
    },
}

MANA = {"slug": "mana", "element": "Wind"}
ALLY = {"slug": "ally", "element": "Iron"}


def make_context():
    return SquadContext([
        SquadMember("mana", burst_tier=3, element="Wind"),
        SquadMember("ally", burst_tier=1, element="Iron"),
    ])


def test_metal_gamma_grants_permanent_self_atk_buff_from_battle_start():
    rules = build_metal_gamma_rules(MANA_VALUES)
    assert len(rules) == 1
    assert rules[0].trigger == "battle_start"
    reg = EffectRegistry()
    rules[0].action(make_context(), "mana", 0.0, reg)
    assert round(reg.total_for("atk_percent", MANA, now=0.0), 4) == 0.5808
    assert round(reg.total_for("atk_percent", MANA, now=180.0), 4) == 0.5808  # never expires


def _run_cycle(ctx, rules, reg, time, mana_bursts):
    """One burst cycle: the tier-3 cast, Full Burst entry, Full Burst end.

    Mirrors raid_simulator's ordering, including that `burst_used_this_cycle`
    is still populated while `full_burst_end` rules run and cleared after.
    """
    if mana_bursts:
        ctx.burst_used_this_cycle.add("mana")
    fire_trigger("full_burst_enter", {"mana": rules}, ctx, reg, time)
    fire_trigger("full_burst_end", {"mana": rules}, ctx, reg, time + 10.0)
    ctx.burst_used_this_cycle.clear()


def test_metal_sigma_is_spent_at_full_burst_and_restored_only_if_she_cast():
    """Metal sigma is a STATUS that carries across cycles, not a per-cycle check.

    Fienn's in-game reading (2026-08-17), in a deck where a second Burst 3
    shares the slot:

        battle start -> sigma ON
        cycle 1, Mana bursts   -> FB entry: sigma present, buffs fire, sigma OFF
                               -> FB end:   she cast this window, sigma ON again
        cycle 2, the OTHER B3  -> FB entry: sigma present, buffs fire, sigma OFF
                               -> FB end:   she did not cast, sigma stays OFF
        cycle 3, Mana bursts   -> FB entry: no sigma, NO buffs

    So the buff lands on the cycle AFTER the one she bursts in. Reading it as
    `own_burst_fired_this_cycle()` put it on exactly the wrong cycles: her own
    burst damage collected an ATK buff the game gives the next window instead.
    Only a deck with two Burst 3s can tell the difference - alone she casts
    every cycle, so sigma is restored every cycle and the two readings agree.
    """
    ctx = make_context()
    rules = build_metal_sigma_rules(MANA_VALUES)
    reg = EffectRegistry()
    fire_trigger("battle_start", {"mana": rules}, ctx, reg, 0.0)

    # Cycle 1 - she bursts. Sigma was up from battle start, so the buffs fire.
    _run_cycle(ctx, rules, reg, time=5.0, mana_bursts=True)
    assert round(reg.total_for("attack_damage_up", MANA, now=5.0), 4) == 0.2112
    assert round(reg.total_for("atk_percent", MANA, now=5.0), 4) == 0.6336

    # Cycle 2 - the other Burst 3 takes the slot. Sigma was restored at cycle
    # 1's Full Burst end, so the buffs fire again even though she did not cast.
    _run_cycle(ctx, rules, reg, time=35.0, mana_bursts=False)
    assert round(reg.total_for("attack_damage_up", MANA, now=35.0), 4) == 0.2112
    assert round(reg.total_for("atk_percent", MANA, now=35.0), 4) == 0.6336

    # Cycle 3 - she bursts, but cycle 2 did not restore sigma, so nothing fires.
    _run_cycle(ctx, rules, reg, time=65.0, mana_bursts=True)
    assert reg.total_for("attack_damage_up", MANA, now=65.0) == 0.0
    assert reg.total_for("atk_percent", MANA, now=65.0) == 0.0

    # Cycle 4 - cycle 3's cast restored it, so it is up again.
    _run_cycle(ctx, rules, reg, time=95.0, mana_bursts=False)
    assert round(reg.total_for("attack_damage_up", MANA, now=95.0), 4) == 0.2112


def test_metal_sigma_fires_every_cycle_when_she_is_the_only_burst_3():
    """Alone in her tier she casts every cycle, so Full Burst end restores sigma
    every cycle and the buffs never miss one. This is the shape the old
    per-cycle reading was validated against, and it is unchanged."""
    ctx = make_context()
    rules = build_metal_sigma_rules(MANA_VALUES)
    reg = EffectRegistry()
    fire_trigger("battle_start", {"mana": rules}, ctx, reg, 0.0)
    for cycle, start in enumerate((5.0, 35.0, 65.0)):
        _run_cycle(ctx, rules, reg, time=start, mana_bursts=True)
        assert round(reg.total_for("atk_percent", MANA, now=start), 4) == 0.6336, cycle


def test_metal_sigma_buffs_last_ten_seconds():
    ctx = make_context()
    rules = build_metal_sigma_rules(MANA_VALUES)
    reg = EffectRegistry()
    fire_trigger("battle_start", {"mana": rules}, ctx, reg, 0.0)
    _run_cycle(ctx, rules, reg, time=5.0, mana_bursts=True)
    assert reg.total_for("attack_damage_up", MANA, now=15.1) == 0.0


def test_metal_sigma_gauge_fill_speed_is_self_scoped_and_toggles_with_the_status():
    """Metal σ's own payload - Burst Gauge filling speed +70.4%, "Affects
    self" - rides the same battle_start / full_burst_enter (spend) /
    full_burst_end (restore) lifecycle as the status flag. Closed at the
    spend by `truncate_open_ended` rather than a fixed duration, because the
    window until the NEXT Full Burst entry is not known when it is granted."""
    ctx = make_context()
    rules = build_metal_sigma_rules(MANA_VALUES)
    reg = EffectRegistry()
    fire_trigger("battle_start", {"mana": rules}, ctx, reg, 0.0)
    assert round(reg.total_for("burst_gauge_fill_speed_percent", MANA, now=0.0), 4) == 0.704
    assert reg.total_for("burst_gauge_fill_speed_percent", ALLY, now=0.0) == 0.0  # self only

    _run_cycle(ctx, rules, reg, time=5.0, mana_bursts=True)  # spent at 5.0, restored at 15.0
    assert reg.total_for("burst_gauge_fill_speed_percent", MANA, now=5.0) == 0.0
    assert round(reg.total_for("burst_gauge_fill_speed_percent", MANA, now=15.0), 4) == 0.704


def test_fatal_error_self_buff_triggers_on_own_burst_activate():
    rules = build_fatal_error_self_buff_rules(MANA_VALUES)
    assert len(rules) == 1
    assert rules[0].trigger == "own_burst_activate"
    reg = EffectRegistry()
    rules[0].action(make_context(), "mana", 5.0, reg)
    assert round(reg.total_for("sustained_damage_up", MANA, now=5.0), 4) == 0.528
    assert reg.total_for("sustained_damage_up", MANA, now=15.1) == 0.0  # 10s duration


def test_fatal_error_dot_spec_is_a_flat_396_percent_per_second_for_10_ticks():
    specs = build_fatal_error_dot(MANA_VALUES)
    assert len(specs) == 1
    spec = specs[0]
    assert spec["base_percent"] == 396.0
    assert spec["tick_count"] == 10
    assert spec["tick_interval"] == 1.0
    assert spec["damage_type"] == "sustained"
    assert spec["resolves_after_cast"] is True
    assert "resource" not in spec


def test_mana_end_to_end_fatal_error_dot_ticks_ten_times_and_gets_full_burst_bonus():
    deck = [
        {"slug": "buffer", "burst_tier": 1, "element": "Iron", "cooldown": 20.0},
        {"slug": "midtier", "burst_tier": 2, "element": "Iron", "cooldown": 20.0},
        {"slug": "mana", "burst_tier": 3, "element": "Wind", "cooldown": 40.0},
    ]
    base_stats = {
        "buffer": {"atk": 0, "def": 0, "max_hp": 0},
        "midtier": {"atk": 0, "def": 0, "max_hp": 0},
        "mana": {"atk": 10000, "def": 0, "max_hp": 0},
    }
    result = simulate_raid(
        deck,
        {"buffer": [], "midtier": [], "mana": build_fatal_error_self_buff_rules(MANA_VALUES)},
        burst_damage_percents={}, base_stats=base_stats,
        enemy_def=0, gauge_charge_time=5.0, fight_duration=20.0, mode="auto", base_crit_rate=0.0,
        resource_scaled_nukes={"mana": build_fatal_error_dot(MANA_VALUES)},
    )
    hits = sorted(
        [e for e in result["damage_log"] if e["source"] == "resource_scaled_nuke"],
        key=lambda e: e["time"],
    )
    assert len(hits) == 10
    assert [round(h["time"], 4) for h in hits] == [round(5.0 + i, 4) for i in range(10)]
    # Fatal Error!'s own Sustained Damage +52.8% self-buff is active for every
    # tick (granted at the same instant, same-instant inclusive semantics
    # apply here since it's a self-buff boosting a LATER-computed damage type
    # bucket, not retroactively affecting cast-time damage like Maiden's).
    # Every tick also lands inside the Full Burst window [5.0, 15.0) that
    # opened at the same instant as her burst, and gets the +50% Full Burst
    # Bonus - confirmed in-game (Fienn, 2026-07-12), despite Fatal Error!'s
    # own text saying "as sustained damage" rather than "as additional
    # damage" (see mana.py's module docstring).
    assert all(round(h["damage"], 4) == round(10000 * 3.96 * 1.5 * 1.528, 4) for h in hits)


# Module-level fixture aliases so the assembly verification harness
# (test_skill_value_assembly.py) can resolve each sub-skill fixture by name.
METAL_GAMMA = MANA_VALUES["metal_gamma"]
METAL_SIGMA = MANA_VALUES["metal_sigma"]
FATAL_ERROR = MANA_VALUES["fatal_error"]


def test_metal_sigma_cuts_the_longest_basic_charge_allys_charge_time():
    # "1 ally with the longest basic Charge Time", -0.18 sec for 10 sec. The
    # cut is absolute seconds, which is why it needed the caster-based stat
    # rather than charge_speed_percent - see the module docstring.
    rules = {"mana": build_metal_sigma_charge_rules(MANA_VALUES)}
    ctx = SquadContext(
        [
            SquadMember("mana", burst_tier=3, element="Wind"),
            SquadMember("sr-ally", burst_tier=3, element="Wind"),
            SquadMember("rl-ally", burst_tier=1, element="Iron"),
        ],
        base_charge_time={"mana": 0.0, "sr-ally": 1.5, "rl-ally": 1.0},
    )
    reg = EffectRegistry()
    fire_trigger("full_burst_enter", rules, ctx, reg, time=5.0)

    assert reg.total_for("charge_time_reduction_sec",
                         {"slug": "sr-ally", "element": "Wind"}, now=5.0) == pytest.approx(0.18)
    # only one ally, and the shorter-charge one is not it
    assert reg.total_for("charge_time_reduction_sec",
                         {"slug": "rl-ally", "element": "Iron"}, now=5.0) == 0.0
    assert reg.total_for("charge_time_reduction_sec",
                         {"slug": "sr-ally", "element": "Wind"}, now=15.1) == 0.0


def test_metal_sigma_never_picks_a_magazine_weapon_ally():
    # Magazine weapons have a 0 basic charge time, so they cannot be "the
    # longest" unless the whole deck is magazine weapons.
    rules = {"mana": build_metal_sigma_charge_rules(MANA_VALUES)}
    ctx = SquadContext(
        [
            SquadMember("mana", burst_tier=3, element="Wind"),
            SquadMember("ar-ally", burst_tier=1, element="Iron"),
            SquadMember("charge-ally", burst_tier=2, element="Iron"),
        ],
        base_charge_time={"mana": 0.0, "ar-ally": 0.0, "charge-ally": 1.0},
    )
    reg = EffectRegistry()
    fire_trigger("full_burst_enter", rules, ctx, reg, time=5.0)
    assert reg.total_for("charge_time_reduction_sec",
                         {"slug": "charge-ally", "element": "Iron"}, now=5.0) == pytest.approx(0.18)
