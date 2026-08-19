"""Milk: Blooming Bunny, against her real max-level skill values.

Her Embarrassment loop is entirely derived - entry offset from her burst's
immunity plus a charge plus the arming hold, forced-reload length from her own
weapon's reload time through the two-directional reload-speed formula - so the
tests assert the derivation, not transcribed constants.
"""
import pytest

from app.effects import EffectRegistry
from app.raid_simulator import UNTIL_NEXT_OWN_BURST
from app.skill_rules.milk_blooming_bunny import (
    build_milk_burst_anchored_buffs,
    build_milk_rules,
    build_milk_scheduled_nukes,
    build_milk_weapon_mode_schedule,
    embarrassment_entry_offset,
)
from app.squad_engine import SquadContext, SquadMember, fire_trigger

SLUG = "milk-blooming-bunny"

# After drop_tokens [2, 4, 6, 9, 10]: "Pierce for 6 sec", "0.5 sec or more",
# "290% Distributed", "Removes 100% of ammo", "50% reduction", "1 reload(s)",
# "ATK 118.7%", "for 40 sec"
EMBARRASSMENT_SUPPRESSION = {
    "description_value_01": "6",
    "description_value_02": "0.5",
    "description_value_03": "290",
    "description_value_04": "100",
    "description_value_05": "50",
    "description_value_06": "1",
    "description_value_07": "118.7",
    "description_value_08": "40",
}
# "Pierce Damage 64.7%", "every 2 sec", "447.7% Distributed"
OUTBURST = {
    "description_value_01": "64.7",
    "description_value_02": "2",
    "description_value_03": "447.7",
}
# "Immunity for 10 sec", "Pierce Damage 117.64%", "for 10 sec", "ATK 220%",
# "for 10 sec"
EMBARRASSMENT_EXPLOSION = {
    "description_value_01": "10",
    "description_value_02": "117.64",
    "description_value_03": "10",
    "description_value_04": "220",
    "description_value_05": "10",
}

# dotgg: SR, 6 rounds, 2s reload, 1s charge
WEAPON = {
    "weapon": "SR", "damage_percent": 69.04, "max_ammo": 6,
    "reload_time": 2.0, "charge_time": 1.0, "charge_damage_percent": 250.0,
}

VALUES = {
    "embarrassment_suppression": EMBARRASSMENT_SUPPRESSION,
    "outburst": OUTBURST,
    "embarrassment_explosion": EMBARRASSMENT_EXPLOSION,
    "caster_weapon_stats": WEAPON,
}


class _Context:
    def __init__(self, burst_times):
        self.burst_times = {SLUG: burst_times}


def test_entry_offset_is_immunity_plus_a_charge_plus_the_arming_hold():
    # 10s Overconfident immunity + 1s full charge + 0.5s hold
    assert embarrassment_entry_offset(VALUES) == pytest.approx(11.5)


def test_burst_grants_overconfidents_two_self_buffs_for_ten_seconds():
    registry = EffectRegistry()
    context = SquadContext([SquadMember(SLUG, 3, "Iron", "SR")])
    fire_trigger("own_burst_activate", {SLUG: build_milk_rules(VALUES)}, context, registry, 20.0)

    assert registry.total_for("pierce_damage_up", {"slug": SLUG}, 25.0) == pytest.approx(1.1764)
    assert registry.total_for("atk_percent", {"slug": SLUG}, 25.0) == pytest.approx(2.20)
    assert registry.total_for("atk_percent", {"slug": SLUG}, 30.5) == pytest.approx(0.0)


def test_embarrassment_atk_buff_has_its_own_fixed_forty_seconds():
    atk, _pierce = build_milk_burst_anchored_buffs(VALUES)

    assert atk["stat"] == "atk_percent"
    assert atk["value"] == pytest.approx(1.187)
    assert atk["offset"] == pytest.approx(11.5)
    assert atk["duration"] == pytest.approx(40.0)


def test_embarrassment_pierce_lasts_until_her_next_burst():
    # Fienn (2026-07-20): only the next burst's immunity clears the state.
    _atk, pierce = build_milk_burst_anchored_buffs(VALUES)

    assert pierce["stat"] == "pierce_damage_up"
    assert pierce["value"] == pytest.approx(0.647)
    assert pierce["duration"] == UNTIL_NEXT_OWN_BURST


def test_forced_reload_segment_covers_three_seconds_and_fires_nothing():
    schedule = build_milk_weapon_mode_schedule(VALUES)
    segments = schedule(_Context([20.0]), 180.0)

    (segment,) = segments
    # "50% reduction" scales her 2s file value by 1.5, and the affine model
    # adds the fixed 0.148 segment on top: 3.148s, not the 4s a reciprocal
    # formula would give (reload_time_with_speed).
    assert segment["start"] == pytest.approx(31.5)
    assert segment["end"] == pytest.approx(34.648)
    # No shot can fit: the profile's interval is twice the window
    assert 1.0 / segment["profile"]["rate_of_fire"] > segment["end"] - segment["start"]


def test_forced_reload_segment_is_clipped_by_the_fight_end():
    schedule = build_milk_weapon_mode_schedule(VALUES)
    # Entry at 178.5 is inside the fight, but its 3s reload would run past it.
    segments = schedule(_Context([20.0, 167.0]), 180.0)

    assert segments[-1]["start"] == pytest.approx(178.5)
    assert segments[-1]["end"] == pytest.approx(180.0)


def test_no_segment_for_a_burst_whose_entry_falls_past_the_fight():
    schedule = build_milk_weapon_mode_schedule(VALUES)

    assert schedule(_Context([175.0]), 180.0) == []


def test_entry_nuke_is_one_distributed_hit_per_burst():
    entry, _overconfident = build_milk_scheduled_nukes(VALUES)

    assert entry["percent"] == pytest.approx(290.0)
    assert entry["damage_type"] == "distributed"
    assert entry["schedule"](_Context([20.0, 70.0]), 180.0) == [
        pytest.approx(31.5), pytest.approx(81.5)
    ]


def test_overconfident_ticks_five_times_across_the_ten_second_status():
    _entry, overconfident = build_milk_scheduled_nukes(VALUES)

    assert overconfident["percent"] == pytest.approx(447.7)
    assert overconfident["damage_type"] == "distributed"
    assert overconfident["schedule"](_Context([20.0]), 180.0) == [
        pytest.approx(t) for t in (22.0, 24.0, 26.0, 28.0, 30.0)
    ]


def test_milk_is_a_tap_fire_candidate():
    """그녀의 조작은 Pierce 창을 지키는 최소 비용으로 풀차지를 넣고 나머지를
    톡톡이로 쏘는 것이다 — docs/measurements/milk-blooming-bunny-tap-fire.md"""
    from app.skill_rules.registry import is_tap_fire_candidate
    assert is_tap_fire_candidate("milk-blooming-bunny")


def test_milks_cadence_actually_keeps_her_pierce_window():
    """Pierce를 영구로 두는 근사가 기대는 것 - 그녀의 케이던스가 창을 **실제로** 지킨다.

    `k >= 1`을 주장하는 것으로는 부족하다: 창이 있으면 엔진이 `k=0`을 아예 후보에서
    빼고 기본값이 `capacity`이므로 그것은 어떤 입력에서도 구조적으로 참이고, 최악
    간격 계산이 통째로 깨져도 초록이다. 그래서 **최악 간격 자체를 재서** 창과 비교한다.

    스윕은 그녀가 실제로 만날 수 있는 범위다 - 장탄은 오버로드·버프로 늘 수 있고,
    재장전은 버프로 짧아지거나 그녀의 강제 재장전(「50% 감소 고정」 = 3초)까지 길어진다.
    그 범위에서는 전부 풀차지의 최악 간격이 `1.3667 + 재장전 <= 4.37초 < 6초`라 창을
    지킬 수 있는 k가 언제나 있고, 따라서 엔진이 고른 k도 반드시 지켜야 한다.
    """
    from app.attack_rate import (FRAME_SECONDS, optimal_full_charges)
    charge, delay, tap = 1.0, 22 * FRAME_SECONDS, 15 * FRAME_SECONDS
    window = 6.0
    for capacity in range(1, 21):
        for reload_seconds in (0.5, 1.0, 2.0, 3.0):
            k = optimal_full_charges(
                capacity, reload_seconds, charge, delay, tap, 250.0, window)
            block = -(-capacity // k)
            worst_gap = charge + delay + (block - 1) * tap + reload_seconds
            assert worst_gap <= window, (capacity, reload_seconds, k, worst_gap)
