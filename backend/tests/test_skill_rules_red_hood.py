"""Real max-level figures from lootandwaifus for Red Hood (slug "red-hood"),
slots numbered left-to-right per skill (full transcription, no skips).
"""
from types import SimpleNamespace

import pytest

from app.effects import EffectRegistry
from app.raid_simulator import simulate_raid
from app.skill_rules._helpers import buff_rule
from app.skill_rules.red_hood import (
    TRANSFORM_SHOTS,
    build_red_hood_rules,
    build_red_wolf_weapon_mode_schedule,
)
from app.squad_engine import SquadContext, SquadMember, fire_trigger

GLARING_EYES = {
    "description_value_01": "3.81",   # Charge Speed per stack %
    "description_value_02": "10",     # stack cap
    "description_value_03": "5",      # stack lifetime sec (refreshed per shot - never lapses)
    "description_value_04": "100",    # conversion threshold (excess over 100%)
    "description_value_05": "240",    # conversion rate (% of excess -> Charge Damage)
}
WILD_TOOTH = {
    "description_value_01": "50.68",  # Beast Cage squad DEF % of caster DEF (skipped)
    "description_value_02": "10",     # its duration
    "description_value_03": "23.04",  # Last Howl self heal % (skipped)
    "description_value_04": "10",     # its duration
    "description_value_05": "71.42",  # Red Wolf cast: self ATK %
    "description_value_06": "10",     # its duration
}
RED_WOLF = {
    "description_value_01": "1",      # "Step 1" label
    "description_value_02": "77.55",  # Beast Cage squad ATK % of caster ATK (unreachable: B3-pinned)
    "description_value_03": "10",     # its duration
    "description_value_04": "40",     # Step 1 burst CD reduction (unreachable)
    "description_value_05": "2",      # "Step 2" label
    "description_value_06": "10",     # taunt duration (unreachable)
    "description_value_07": "74.88",  # incoming healing % (unreachable)
    "description_value_08": "10",     # its duration
    "description_value_09": "40",     # Step 2 burst CD reduction (unreachable)
    "description_value_10": "3",      # "Step 3" label
    "description_value_11": "51.46",  # transformed weapon damage % of final ATK
    "description_value_12": "250",    # transformed Full Charge Damage %
    "description_value_13": "10",     # transform duration sec
    "description_value_14": "100",    # Pierce range expansion % (deferred)
    "description_value_15": "10",     # its duration
    "description_value_16": "100.8",  # Charge Speed % during transform
    "description_value_17": "10",     # its duration
}
RED_HOOD_VALUES = {
    "glaring_eyes": GLARING_EYES,
    "wild_tooth": WILD_TOOTH,
    "red_wolf": RED_WOLF,
}
RED_HOOD = {"slug": "red-hood", "element": "Iron"}
ALLY = {"slug": "ally", "element": "Fire"}


def make_context():
    return SquadContext([
        SquadMember("red-hood", burst_tier=3, element="Iron"),
        SquadMember("ally", burst_tier=1, element="Fire"),
    ])


def test_glaring_eyes_steady_state_charge_speed_is_continuous_self():
    ctx = make_context()
    registry = EffectRegistry()
    rules = {"red-hood": build_red_hood_rules(RED_HOOD_VALUES)}

    fire_trigger("battle_start", rules, ctx, registry, time=0.0)

    # 10 stacks x 3.81% held permanently (SR cadence never lets the 5s
    # lifetime lapse - Raven counter precedent).
    assert round(registry.total_for("charge_speed_percent", RED_HOOD, now=100.0), 4) == 0.381
    assert registry.total_for("charge_speed_percent", ALLY, now=100.0) == 0.0


def test_wild_tooth_red_wolf_cast_grants_self_atk():
    ctx = make_context()
    registry = EffectRegistry()
    rules = {"red-hood": build_red_hood_rules(RED_HOOD_VALUES)}

    fire_trigger("own_burst_activate", rules, ctx, registry, time=50.0)

    assert round(registry.total_for("atk_percent", RED_HOOD, now=50.0), 4) == 0.7142
    assert registry.total_for("atk_percent", RED_HOOD, now=60.1) == 0.0
    assert registry.total_for("atk_percent", ALLY, now=50.0) == 0.0


def test_red_wolf_schedule_is_33_shot_window_per_own_burst():
    schedule = build_red_wolf_weapon_mode_schedule(RED_HOOD_VALUES)
    context = SimpleNamespace(burst_times={"red-hood": [20.0]})
    segments = schedule(context, 180.0)
    assert len(segments) == 1
    seg = segments[0]
    assert seg["start"] == 20.0
    assert seg["until_shots"] == 33
    profile = seg["profile"]
    assert profile["rate_of_fire"] == pytest.approx(3.3)
    assert profile["damage_percent"] == 51.46
    # 250% full charge + 93.36%p Glaring conversion, folded into charge_damage
    # (no subtraction - the engine genuinely silences the base SR now).
    assert profile["charge_damage_percent"] == pytest.approx(343.36, abs=0.01)


def test_red_wolf_profile_scales_only_the_weapon_full_charge_term():
    """Her transform's charge damage is a SUM of two things, and the
    collectible's 배율 scales only the transformed weapon's own full-charge
    multiplier. The Glaring conversion term is a skill effect, not a weapon base
    stat - the same split snow_white_heavy_arms already makes."""
    def charge_damage(values):
        schedule = build_red_wolf_weapon_mode_schedule(values)
        segments = schedule(SimpleNamespace(burst_times={"red-hood": [20.0]}), 180.0)
        return segments[0]["profile"]["charge_damage_percent"]

    plain = charge_damage(RED_HOOD_VALUES)
    scaled = charge_damage(
        {**RED_HOOD_VALUES, "caster_charge_damage_multiplier": 1.0947})

    weapon_term = float(RED_WOLF["description_value_12"])
    converted_term = plain - weapon_term
    assert scaled == pytest.approx(weapon_term * 1.0947 + converted_term)
    # Scaling the whole sum would be the other reading, and it is not this one.
    assert scaled != pytest.approx(plain * 1.0947)


SR_WEAPON = {
    "weapon": "SR", "damage_percent": 69.04, "max_ammo": 6,
    "reload_time": 2.0, "charge_time": 1.0, "charge_damage_percent": 250.0,
}


def _red_wolf_sim_deck():
    # Tiers 1/2 are inert placeholders so the burst cycle can complete (a
    # deck missing any tier never fires) - only red-hood (tier 3) carries
    # rules/a weapon. Cooldowns are large enough that only one cycle
    # completes inside fight_duration, so her one burst - and its 10s
    # transform window - lands at a known, deterministic time (t=5.0).
    return [
        {"slug": "b1", "burst_tier": 1, "element": "Iron", "cooldown": 20.0},
        {"slug": "b2", "burst_tier": 2, "element": "Iron", "cooldown": 20.0},
        {"slug": "red-hood", "burst_tier": 3, "element": "Iron", "cooldown": 40.0},
    ]


def test_red_wolf_deck_charge_damage_buff_now_scales_transform_shots():
    # End-to-end: with the old scheduled_nukes model the transform's 250%+
    # 93.36%p was a folded constant a deck's Charge Damage buffs couldn't
    # touch. The weapon-mode segment's charge_damage_percent now rides the
    # same extra_charge_bonus path a normal charge-weapon shot uses, so a
    # squad Charge Damage buff should raise the transform window's damage -
    # locking in the fix as a regression test.
    deck = _red_wolf_sim_deck()
    base_stats = {m["slug"]: {"atk": 10000.0} for m in deck}
    kwargs = dict(
        deck=deck, burst_damage_percents={}, base_stats=base_stats,
        enemy_def=0.0, gauge_charge_time=5.0, fight_duration=30.0,
        weapon_stats={"red-hood": SR_WEAPON},
        weapon_mode_schedules={"red-hood": build_red_wolf_weapon_mode_schedule(RED_HOOD_VALUES)},
    )

    plain_rules = {"red-hood": build_red_hood_rules(RED_HOOD_VALUES)}
    buffed_rules = {
        "red-hood": build_red_hood_rules(RED_HOOD_VALUES) + [
            buff_rule("battle_start", [("charge_damage_bonus", 0.5, "self", None)]),
        ],
    }
    without = simulate_raid(rules_by_slug=plain_rules, **kwargs)
    with_buff = simulate_raid(rules_by_slug=buffed_rules, **kwargs)

    # Burst fires at t=5.0 (gauge_charge_time floor, no prior cooldowns) -
    # the transform window is [5.0, 15.0].
    def window_sum(result):
        return sum(
            e["damage"] for e in result["damage_log"]
            if e["source"] == "normal_attack" and 5.0 <= e["time"] <= 15.0
        )

    without_sum = window_sum(without)
    with_buff_sum = window_sum(with_buff)
    assert without_sum > 0.0
    assert with_buff_sum > without_sum
