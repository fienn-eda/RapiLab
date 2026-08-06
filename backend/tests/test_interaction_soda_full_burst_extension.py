"""소다의 확장이 두 운영에서 다르게 나오는지 - 이 인코딩의 핵심 주장.

Fienn 실측(docs/measurements/soda-golden-chip-in-play.md): 그녀가 격 사이클로
버스트하면 골든칩은 고갈되지 않고 한 밴드 안에서 순환하고, 풀 버스트는 15초로
읽힌다. 반대로 그녀가 매 사이클 버스트하면 칩이 고갈되고 확장 단계도 따라
내려간다.

두 덱이 그 대비를 만든다. 가르는 것은 그녀의 쿨다운이 아니라 **덱의 Burst 3
좌석 수**다 - 칩은 그녀의 버스트 1회당 17이 나가고 풀 버스트 창 1회당 ~7이
차므로, 드레인은 벽시계가 아니라 "그녀의 버스트 대 창"의 비로 정해진다.

- `_alternating_deck`: B3가 둘이라 그녀는 격 사이클에만 버스트한다. spend 1회당
  창 2회를 받아 칩이 밴드 안에서 순환하고, 200초 열 창이 전부 15초다.
- `_every_cycle_deck`: B3가 그녀뿐이라 매 창이 그녀의 spend를 동반한다. 창 1회당
  spend 1회라 칩이 고갈되고 창이 15 -> 12 -> 10으로 내려간다.

B3가 하나인 덱에서 쿨다운만 40으로 늘리는 것은 이 대비를 만들지 못한다 -
그녀의 버스트도 창도 함께 절반이 되어 비가 그대로이므로, 벽시계로 느릴 뿐
똑같이 고갈된다.
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

# 넉 배율을 평타 배율로 나눈 값 -> Time Extension 단계. 상수로 박지 않고
# 스킬 값에서 끌어와 스킬 레벨이 바뀌어도 따라가게 한다. `_stage_per_cycle` 참조.
_REWARDS = SODA_VALUES["beginners_rewards"]
_STAGE_PERCENTS = (
    float(_REWARDS["description_value_10"]),
    float(_REWARDS["description_value_10"]) + float(_REWARDS["description_value_12"]),
)
_RATIO_TO_STAGE = {
    round(percent / SG["damage_percent"], 4): stage
    for stage, percent in enumerate(_STAGE_PERCENTS, start=1)
}


def _alternating_deck():
    """소다가 격 사이클에만 Burst 3 좌석을 잡는 덱: b3b가 나머지 사이클을 연다.
    확장은 "affects all allies"라 그녀가 그 사이클의 B3가 아니어도 걸린다."""
    return [
        {"slug": "b1", "burst_tier": 1, "element": "Iron", "cooldown": 20.0},
        {"slug": "b2", "burst_tier": 2, "element": "Iron", "cooldown": 20.0},
        {"slug": SODA, "burst_tier": 3, "element": "Iron", "cooldown": 40.0},
        {"slug": "b3b", "burst_tier": 3, "element": "Iron", "cooldown": 40.0},
    ]


def _every_cycle_deck():
    """B3가 소다뿐이라 매 사이클이 그녀의 버스트로 열린다."""
    return [
        {"slug": "b1", "burst_tier": 1, "element": "Iron", "cooldown": 20.0},
        {"slug": "b2", "burst_tier": 2, "element": "Iron", "cooldown": 20.0},
        {"slug": SODA, "burst_tier": 3, "element": "Iron", "cooldown": 20.0},
    ]


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


def _windows(result):
    starts = [e["time"] for e in result["events"] if e["type"] == "full_burst_start"]
    ends = [e["time"] for e in result["events"] if e["type"] == "full_burst_end"]
    return list(zip(starts, ends))


def _window_lengths(result):
    return [round(end - start, 3) for start, end in _windows(result)]


def _stage_per_cycle(result):
    """사이클별로 실제 걸린 Time Extension 단계를, 창 길이가 아니라 넉에서 읽는다.

    창 길이는 `raid_simulator._stage_seconds`가, 넉 배율은
    `build_beginners_rewards_per_shot_rules`가 같은 해석 결과를 각자 소비한다.
    그래서 둘을 함께 단언하면 창 길이가 단계에서 유도되기를 그만두는 날 조용히
    통과하지 않는다 - 한쪽만 보면 못 잡는다.

    한 발의 넉 피해를 같은 순간의 평타 피해로 나누면 배율만 남는다. ATK도 버프도
    양쪽에 똑같이 곱해져 약분되므로 남는 것은 137.06 / 10 = 13.706(II단계) 또는
    52.04 / 10 = 5.204(I단계)이고, 넉이 아예 없으면 확장이 없는 창이다."""
    normals = {round(e["time"], 6): e["damage"]
               for e in result["damage_log"] if e["source"] == "normal_attack"}
    nukes = [e for e in result["damage_log"] if e["source"] == "per_shot_nuke"]
    stages = []
    for start, end in _windows(result):
        ratios = {round(nuke["damage"] / normals[round(nuke["time"], 6)], 4)
                  for nuke in nukes if start <= nuke["time"] < end}
        if not ratios:
            stages.append(0)
            continue
        assert len(ratios) == 1, f"한 창 안에서 단계가 흔들렸다: {sorted(ratios)}"
        stages.append(_RATIO_TO_STAGE[ratios.pop()])
    return stages


def test_alternating_seats_hold_the_top_tier_for_the_whole_fight():
    """그녀가 격 사이클로만 버스트하면 리필이 spend를 덮어 칩이 밴드 안에서
    순환한다 - 200초 열 창이 전부 15초이고 단계도 II에서 안 내려온다.
    Fienn이 인게임에서 읽는 그림이 이것이다."""
    result = _run(_alternating_deck(), fight_duration=200.0)
    assert _window_lengths(result) == [15.0] * 10
    # 창 길이와 같은 사실을 더 직접적으로: 칩이 II단계 임계(20) 위에 머문다.
    assert _stage_per_cycle(result) == [2] * 10
    assert result["full_burst_passes"] == {"passes": 3, "converged": True}


def test_the_extension_falls_as_her_own_bursts_drain_the_chip():
    """매 사이클 버스트하면 -17 대 +fill로 고갈되고, 창 길이가 15 -> 12 -> 10으로
    내려간다. 상수로 접을 수 없다는 것의 실물."""
    result = _run(_every_cycle_deck(), fight_duration=200.0)
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
    result = _run(_alternating_deck(), fight_duration=200.0)
    nukes = [e for e in result["damage_log"] if e["source"] == "per_shot_nuke"]
    assert nukes, "확장이 걸린 창에서는 평타마다 넉이 나와야 한다"
    windows = _windows(result)
    for nuke in nukes:
        assert any(start <= nuke["time"] < end for start, end in windows), \
            "창 밖에서 넉이 나오면 안 된다"
