import pytest

from app.effects import EffectRegistry
from app.skill_rules.anis_star import (
    build_shooting_stars_scheduled_nukes,
    build_star_anis_burst_rules,
    build_starfall_full_charge_nuke_rules,
    build_starfall_rules,
    build_stardust_rules,
)
from app.squad_engine import SquadContext, SquadMember, fire_trigger

# Real skill level 10 values pulled from api.dotgg.gg for anis-star's Starfall skill.
LEVEL_10_VALUES = {
    "description_value_01": "1",
    "description_value_02": "40.01",
    "description_value_03": "7.48",
    "description_value_04": "120.13",
    "description_value_05": "6",
}

# Stardust (skills[1]) and Star Anis (burst) - real Lv.10 values from
# lootandwaifus.com, slots numbered left-to-right by appearance.
STARDUST = {
    "description_value_01": "35.01",  # My Own Star: squad ATK % of caster's ATK
    "description_value_02": "10",     # duration
    "description_value_03": "1.26",   # Everyone's Star heal % (not modeled)
    "description_value_04": "92.03",  # squad Projectile Explosion Damage %
    "description_value_05": "10",     # duration
    "description_value_06": "34",     # squad Attack Damage %
    "description_value_07": "10",     # duration
}
# Star Anis (burst), dotgg native slots after drop_tokens [2, 3, 6, 7] removes
# Explosion Radius 100, DEF 55.01 and the Everyone's Star Max HP pair (15.02/10).
STAR_ANIS = {
    "description_value_01": "40.01",  # Shooting Stars damage % of final ATK
    "description_value_02": "10",     # Shooting Stars duration (shared by the window's other effects)
    "description_value_03": "35.2",   # My Own Star: self Attack Damage %
    "description_value_04": "10",     # duration
    "description_value_05": "0.7",    # charge time is fixed at this for the window
}
# Her RL's real base charge time (data/dotgg/char_anis-star.json), injected by
# the assembly layer as `caster_weapon_stats` (see roster.py).
BURST_VALUES = {**STAR_ANIS, "caster_weapon_stats": {"charge_time": 1.0}}
ALLY = {"slug": "crown", "element": "Iron"}
ANIS = {"slug": "anis-star", "element": "Electric"}


def alone_context():
    return SquadContext(
        [
            SquadMember("anis-star", burst_tier=1, element="Electric"),
            SquadMember("crown", burst_tier=2, element="Iron"),
        ]
    )


def with_ally_context():
    return SquadContext(
        [
            SquadMember("anis-star", burst_tier=1, element="Electric"),
            SquadMember("other-burst1", burst_tier=1, element="Fire"),
        ]
    )


def test_gauge_fill_speed_applies_to_squad_at_battle_start():
    ctx = alone_context()
    registry = EffectRegistry()
    rules = {"anis-star": build_starfall_rules(LEVEL_10_VALUES)}

    fire_trigger("battle_start", rules, ctx, registry, time=0.0)

    crown = {"slug": "crown", "element": "Iron"}
    assert round(registry.total_for("burst_gauge_fill_speed_percent", crown, now=0.0), 4) == 0.06


def test_alone_branch_grants_my_own_star_atk_buff_and_sets_status():
    ctx = alone_context()
    registry = EffectRegistry()
    rules = {"anis-star": build_starfall_rules(LEVEL_10_VALUES)}

    fire_trigger("battle_start", rules, ctx, registry, time=0.0)

    anis = {"slug": "anis-star", "element": "Electric"}
    assert round(registry.total_for("atk_percent", anis, now=0.0), 4) == 0.4001
    assert ctx.has_status("anis-star", "My Own Star") is True
    assert ctx.has_status("anis-star", "Everyone's Star") is False


def test_alone_branch_emits_burst_cooldown_reduction_pulse():
    ctx = alone_context()
    registry = EffectRegistry()
    rules = {"anis-star": build_starfall_rules(LEVEL_10_VALUES)}

    fire_trigger("battle_start", rules, ctx, registry, time=0.0)

    pulses = registry.drain_pulses("burst_cooldown_reduction_sec")
    assert len(pulses) == 1
    assert pulses[0].value == 7.48
    assert pulses[0].scope == "squad"


def test_atk_buff_is_not_reapplied_on_repeated_full_burst_end_but_pulse_recurs():
    ctx = alone_context()
    registry = EffectRegistry()
    rules = {"anis-star": build_starfall_rules(LEVEL_10_VALUES)}

    fire_trigger("battle_start", rules, ctx, registry, time=0.0)
    fire_trigger("full_burst_end", rules, ctx, registry, time=15.0)
    fire_trigger("full_burst_end", rules, ctx, registry, time=30.0)

    anis = {"slug": "anis-star", "element": "Electric"}
    # still exactly one atk_percent worth of buff, not stacked 3x
    assert round(registry.total_for("atk_percent", anis, now=30.0), 4) == 0.4001

    # but the cooldown-reduction pulse fires every time (drain across all three firings)
    pulses = registry.drain_pulses("burst_cooldown_reduction_sec")
    assert len(pulses) == 3


def test_with_ally_branch_sets_everyones_star_and_clears_my_own_star():
    ctx = with_ally_context()
    registry = EffectRegistry()
    rules = {"anis-star": build_starfall_rules(LEVEL_10_VALUES)}

    fire_trigger("battle_start", rules, ctx, registry, time=0.0)

    assert ctx.has_status("anis-star", "Everyone's Star") is True
    assert ctx.has_status("anis-star", "My Own Star") is False

    anis = {"slug": "anis-star", "element": "Electric"}
    assert registry.total_for("atk_percent", anis, now=0.0) == 0.0


def test_full_charge_nuke_fires_every_shot_for_final_atk_percent():
    rules = build_starfall_full_charge_nuke_rules(LEVEL_10_VALUES)
    assert len(rules) == 1
    threshold, mode, skill_rules = rules[0]
    assert (threshold, mode) == (1, "every")  # every full charge (RL)

    ctx = alone_context()
    registry = EffectRegistry()
    for rule in skill_rules:
        rule.action(ctx, "anis-star", 3.0, registry)
    pulses = registry.drain_pulses("instant_damage_percent")
    assert len(pulses) == 1
    assert pulses[0].value == 120.13
    assert pulses[0].source_slug == "anis-star"


def test_stardust_my_own_star_atk_is_squad_caster_scaled_only_while_my_own_star():
    rules = {"anis-star": build_stardust_rules({**STARDUST, "caster_atk": 300000})}
    # Not in My Own Star -> no ATK buff.
    ctx = with_ally_context()
    registry = EffectRegistry()
    fire_trigger("full_burst_enter", rules, ctx, registry, time=5.0)
    assert registry.total_for("flat_atk", ALLY, now=5.0) == 0.0

    # In My Own Star -> squad flat ATK = 35.01% of caster's ATK, 10s.
    ctx2 = alone_context()
    ctx2.set_status("anis-star", "My Own Star")
    registry2 = EffectRegistry()
    fire_trigger("full_burst_enter", rules, ctx2, registry2, time=5.0)
    assert round(registry2.total_for("flat_atk", ALLY, now=5.0), 2) == round(300000 * 0.3501, 2)
    assert registry2.total_for("flat_atk", ALLY, now=15.1) == 0.0


def test_stardust_grants_squad_projectile_explosion_and_attack_damage():
    rules = {"anis-star": build_stardust_rules({**STARDUST, "caster_atk": 300000})}
    ctx = alone_context()
    registry = EffectRegistry()
    fire_trigger("full_burst_enter", rules, ctx, registry, time=5.0)
    assert round(registry.total_for("projectile_explosion_damage_up", ALLY, now=5.0), 4) == 0.9203
    assert round(registry.total_for("attack_damage_up", ALLY, now=5.0), 4) == 0.34
    assert registry.total_for("projectile_explosion_damage_up", ALLY, now=15.1) == 0.0


def test_burst_grants_self_attack_damage_only_while_my_own_star():
    rules = {"anis-star": build_star_anis_burst_rules(BURST_VALUES)}
    ctx = alone_context()
    ctx.set_status("anis-star", "My Own Star")
    registry = EffectRegistry()
    fire_trigger("own_burst_activate", rules, ctx, registry, time=5.0)
    assert round(registry.total_for("attack_damage_up", ANIS, now=5.0), 4) == 0.352
    # self-scoped -> does not reach an ally
    assert registry.total_for("attack_damage_up", ALLY, now=5.0) == 0.0

    # Not in My Own Star -> no buff.
    ctx2 = with_ally_context()
    registry2 = EffectRegistry()
    fire_trigger("own_burst_activate", rules, ctx2, registry2, time=5.0)
    assert registry2.total_for("attack_damage_up", ANIS, now=5.0) == 0.0


class _BurstContext:
    def __init__(self, burst_times):
        self.burst_times = {"anis-star": burst_times}


def test_shooting_stars_ticks_every_quarter_second_across_the_ten_second_window():
    (stars,) = build_shooting_stars_scheduled_nukes(STAR_ANIS)

    assert stars["percent"] == pytest.approx(40.01)
    # "as damage", not "as additional damage" -> no Full Burst bonus.
    assert stars.get("full_burst_bonus_eligible") is not True

    times = stars["schedule"](_BurstContext([20.0]), 180.0)
    # 10 sec / 0.25 sec interval, first tick one interval after the burst.
    assert len(times) == 40
    assert times[0] == pytest.approx(20.25)
    assert times[-1] == pytest.approx(30.0)


def test_shooting_stars_repeat_each_burst_and_are_clipped_by_fight_end():
    (stars,) = build_shooting_stars_scheduled_nukes(STAR_ANIS)

    times = stars["schedule"](_BurstContext([20.0, 70.0]), 180.0)
    assert len(times) == 80

    # A burst late enough that its window runs past the fight only keeps the
    # ticks that land inside it: 178 + 0.25k < 180 -> k = 1..7.
    tail = stars["schedule"](_BurstContext([178.0]), 180.0)
    assert len(tail) == 7
    assert tail[-1] == pytest.approx(179.75)


def test_burst_fixes_charge_time_via_an_equivalent_charge_speed_buff():
    # Her RL charges in 1.0 sec; "fixed at 0.7 sec" is 1/0.7 - 1 of charge speed.
    rules = {"anis-star": build_star_anis_burst_rules(BURST_VALUES)}
    ctx = alone_context()
    registry = EffectRegistry()
    fire_trigger("own_burst_activate", rules, ctx, registry, time=5.0)

    assert registry.total_for("charge_speed_percent", ANIS, now=5.0) == pytest.approx(1.0 / 0.7 - 1)
    # self-scoped, and only for the stated window
    assert registry.total_for("charge_speed_percent", ALLY, now=5.0) == 0.0
    assert registry.total_for("charge_speed_percent", ANIS, now=15.1) == 0.0
