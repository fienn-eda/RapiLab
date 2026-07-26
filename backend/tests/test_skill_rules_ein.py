"""Ein - Burst-3 Electric SR. Her Near Feathers are summoned entities whose
attack cadence rises with how many are alive; the schedule is precomputed and
fed to the engine's `scheduled_nukes`.

The headline assertion is `test_full_burst_hit_count_matches_measurement`, which
pins Fienn's video measurement (2026-07-17): 31 feather hits inside a Full
Burst, first at +0.8s, ~0.3s apart.
"""
import pytest

from app.effects import EffectRegistry
from app.skill_rules.ein import (
    _attack_cooldown,
    _feather_count_at,
    _feather_hit_times,
    _hit_interval,
    build_ein_per_shot_rules,
    build_ein_rules,
    build_ein_scheduled_nukes,
    feather_all_range_burst_percent,
)
from app.squad_engine import SquadContext, SquadMember

FEATHER_STANDBY = {
    "description_value_01": "4",      # Near Feathers summoned at battle start
    "description_value_02": "70.12",  # self ATK %
    "description_value_03": "10",     # duration
}
FEATHER_SHOT = {
    "description_value_01": "1",      # "1 random enemy unit(s)"
    "description_value_02": "90.81",  # Near Feather Attack, true damage
    "description_value_03": "80",     # self Charge Damage %
    "description_value_04": "1",      # for 1 shot(s)
}
FEATHER_ALL_RANGE = {
    "description_value_01": "6",      # Near Feathers summoned by the burst
    "description_value_02": "55.3",   # self True Damage %
    "description_value_03": "10",     # duration
    "description_value_04": "140.68",  # self Charge Damage %
    "description_value_05": "10",     # duration
    "description_value_06": "10",     # "10 enemy unit(s) with the highest final DEF"
    "description_value_07": "300.02",  # burst nuke, true damage
}

VALUES = {
    "feather_standby": FEATHER_STANDBY,
    "feather_shot": FEATHER_SHOT,
    "feather_all_range": FEATHER_ALL_RANGE,
}


class _Context:
    def __init__(self, burst_times):
        self.burst_times = burst_times


def test_attack_cooldown_reduces_16_percent_per_extra_feather_additively():
    assert _attack_cooldown(1) == pytest.approx(8.0)
    assert _attack_cooldown(4) == pytest.approx(4.16)
    assert _attack_cooldown(6) == pytest.approx(1.6)


def test_hit_interval_is_throttled_only_at_six_feathers():
    # 5 feathers already ask for 0.576s, above the 0.3s floor - untouched.
    assert _hit_interval(5) == pytest.approx(2.88 / 5)
    # 6 feathers ask for 0.267s, below the floor - clamped to the observed 0.3s.
    assert _hit_interval(6) == pytest.approx(0.3)


def test_battle_start_has_four_feathers_and_burst_brings_six():
    summons = [0.0, 50.0]
    assert _feather_count_at(0.0, summons) == 4
    assert _feather_count_at(25.9, summons) == 4   # F4 expires at 26
    assert _feather_count_at(26.1, summons) == 3
    assert _feather_count_at(49.0, summons) == 1   # only unlimited F1 left by now
    assert _feather_count_at(50.0, summons) == 6   # burst re-summons all six
    assert _feather_count_at(59.9, summons) == 6   # F5/F6 last 10s


def test_short_lived_feathers_expire_ten_seconds_after_the_burst():
    summons = [0.0, 50.0]
    assert _feather_count_at(60.1, summons) == 4   # F5/F6 gone, F1-F4 reset at 50
    assert _feather_count_at(76.1, summons) == 3   # F4 expires at 50+26
    assert _feather_count_at(82.1, summons) == 2   # F3 expires at 50+32
    assert _feather_count_at(88.1, summons) == 1   # F2 expires at 50+38; F1 forever


def test_full_burst_hit_count_matches_measurement():
    """Fienn's recording: 31 hits inside the 10s Full Burst, first at +0.8s."""
    burst = 50.0
    hits = _feather_hit_times(_Context({"ein": [burst]}), 180.0)
    in_window = [t for t in hits if burst <= t < burst + 10.0]
    assert len(in_window) == 31
    assert in_window[0] == pytest.approx(burst + 0.8)
    gaps = [b - a for a, b in zip(in_window, in_window[1:])]
    assert all(g == pytest.approx(0.3) for g in gaps)


def test_hits_stop_at_fight_duration():
    hits = _feather_hit_times(_Context({"ein": []}), 30.0)
    assert hits
    assert max(hits) < 30.0


def test_burst_percent_is_the_true_damage_nuke():
    assert feather_all_range_burst_percent(VALUES) == pytest.approx(300.02)


def test_scheduled_nuke_is_true_damage_at_the_feather_percent():
    spec = build_ein_scheduled_nukes(VALUES)[0]
    assert spec["percent"] == pytest.approx(90.81)
    assert spec["damage_type"] == "true"
    assert spec["schedule"] is _feather_hit_times


def test_burst_grants_self_atk_true_damage_and_charge_damage():
    rules = build_ein_rules(VALUES)
    assert len(rules) == 1
    assert rules[0].trigger == "own_burst_activate"


def test_full_charge_grants_one_round_of_charge_damage():
    rules = build_ein_per_shot_rules(VALUES)
    assert len(rules) == 1
    threshold, mode, shot_rules = rules[0]
    assert (threshold, mode) == (1, "every")
    assert shot_rules[0].trigger == "per_shot"


def test_her_charge_damage_lands_under_the_name_the_engine_reads():
    """Both of her Charge Damage buffs must register as `charge_damage_bonus`.

    Structure-only tests let this one hide: the rules existed, fired, and put
    an Effect in the registry - under `charge_damage_up`, which nothing in the
    damage path ever queries (`damage_formula` takes `charge_damage_bonus`, and
    every other encoding writes that). She is an SR, so charge damage is a
    multiplier on every normal attack she takes.
    """
    reg = EffectRegistry()
    ctx = SquadContext([
        SquadMember("ein", burst_tier=3, element="Electric"),
        SquadMember("ally", burst_tier=1, element="Iron"),
    ])
    ein = {"slug": "ein", "element": "Electric"}
    for rule in build_ein_rules(VALUES):
        rule.action(ctx, "ein", 2.0, reg)
    assert reg.total_for("charge_damage_bonus", ein, 5.0) == pytest.approx(1.4068)
    assert reg.total_for("charge_damage_up", ein, 5.0) == 0.0
