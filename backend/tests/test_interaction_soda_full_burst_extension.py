"""소다의 확장이 두 운영에서 다르게 나오는지 - 이 인코딩의 핵심 주장.

Fienn 실측(docs/measurements/soda-golden-chip-in-play.md): B3가 셋인 덱에서
그녀가 격 사이클로 버스트하면 풀 버스트는 15초이고 칩은 33~50에서 순환한다.
반대로 그녀가 매 사이클 버스트하면 칩이 고갈되고 확장 단계도 따라 내려간다.
"""
from app.raid_simulator import simulate_raid
from app.skill_rules.soda_twinkling_bunny import (
    build_beginners_rewards_full_burst_delta,
    build_beginners_rewards_per_shot_rules,
    build_golden_chip_resources,
    build_lucky_golden_chip_per_shot_rules,
    build_onward_soda_resource_gated_buffs,
    onward_soda_burst_percent,
)
from tests.test_skill_rules_soda_twinkling_bunny import SODA_VALUES

SODA = "soda-twinkling-bunny"
SG = {"weapon": "SG", "damage_percent": 10.0, "max_ammo": 1000,
      "reload_time": 1.0, "charge_time": 0.0, "charge_damage_percent": 0.0}


def _run(deck, fight_duration):
    base_stats = {m["slug"]: {"atk": 10000 if m["slug"] == SODA else 0,
                              "def": 0, "max_hp": 0} for m in deck}
    return simulate_raid(
        deck,
        {m["slug"]: [] for m in deck},
        burst_damage_percents={SODA: onward_soda_burst_percent(SODA_VALUES)},
        base_stats=base_stats,
        enemy_def=0, gauge_charge_time=5.0, fight_duration=fight_duration,
        mode="auto", base_crit_rate=0.0,
        weapon_stats={SODA: SG},
        per_shot_rules={SODA: (build_lucky_golden_chip_per_shot_rules(SODA_VALUES)
                               + build_beginners_rewards_per_shot_rules(SODA_VALUES))},
        resource_specs={SODA: build_golden_chip_resources(SODA_VALUES)},
        resource_gated_buffs={SODA: build_onward_soda_resource_gated_buffs(SODA_VALUES)},
        conditional_full_burst_deltas={
            SODA: build_beginners_rewards_full_burst_delta(SODA_VALUES)},
    )


def _window_lengths(result):
    starts = [e["time"] for e in result["events"] if e["type"] == "full_burst_start"]
    ends = [e["time"] for e in result["events"] if e["type"] == "full_burst_end"]
    return [round(end - start, 3) for start, end in zip(starts, ends)]


def test_full_burst_runs_15_seconds_while_the_chip_stays_above_20():
    """전투 시작 칩이 캡(50)이라 첫 창부터 +5초다. 실측의 15초가 이것이다."""
    deck = [
        {"slug": "b1", "burst_tier": 1, "element": "Iron", "cooldown": 20.0},
        {"slug": "b2", "burst_tier": 2, "element": "Iron", "cooldown": 20.0},
        {"slug": SODA, "burst_tier": 3, "element": "Iron", "cooldown": 40.0},
    ]
    result = _run(deck, fight_duration=30.0)
    assert _window_lengths(result)[0] == 15.0
    assert result["full_burst_passes"]["converged"] is True


def test_the_extension_falls_as_her_own_bursts_drain_the_chip():
    """매 사이클 버스트하면 -17 대 +fill로 고갈되고, 창 길이가 15 -> 12 -> 10으로
    내려간다. 상수로 접을 수 없다는 것의 실물."""
    deck = [
        {"slug": "b1", "burst_tier": 1, "element": "Iron", "cooldown": 20.0},
        {"slug": "b2", "burst_tier": 2, "element": "Iron", "cooldown": 20.0},
        {"slug": SODA, "burst_tier": 3, "element": "Iron", "cooldown": 20.0},
    ]
    result = _run(deck, fight_duration=200.0)
    lengths = _window_lengths(result)
    assert lengths[0] == 15.0
    assert lengths[-1] < 15.0, "칩이 고갈되면 확장이 내려가야 한다"
    assert lengths == sorted(lengths, reverse=True), "단조 감소여야 한다"
    # 10사이클에 걸쳐 확장 단계가 셋(+5 / +2 / 없음) 다 나오는 덱인데도 고정점은
    # 3패스에 닫힌다. 상한은 `raid_simulator.MAX_FULL_BURST_PASSES` = 8이므로
    # 여유가 크다 - 이 숫자를 못박아 두면 수렴이 느려질 때 상한에 조용히
    # 다가가지 않고 여기서 걸린다.
    assert result["full_burst_passes"] == {"passes": 3, "converged": True}


def test_the_nuke_only_fires_inside_extended_windows():
    deck = [
        {"slug": "b1", "burst_tier": 1, "element": "Iron", "cooldown": 20.0},
        {"slug": "b2", "burst_tier": 2, "element": "Iron", "cooldown": 20.0},
        {"slug": SODA, "burst_tier": 3, "element": "Iron", "cooldown": 40.0},
    ]
    result = _run(deck, fight_duration=30.0)
    nukes = [e for e in result["damage_log"] if e["source"] == "per_shot_nuke"]
    assert nukes, "확장이 걸린 창에서는 평타마다 넉이 나와야 한다"
    starts = [e["time"] for e in result["events"] if e["type"] == "full_burst_start"]
    ends = [e["time"] for e in result["events"] if e["type"] == "full_burst_end"]
    windows = list(zip(starts, ends))
    for nuke in nukes:
        assert any(start <= nuke["time"] < end for start, end in windows), \
            "창 밖에서 넉이 나오면 안 된다"
