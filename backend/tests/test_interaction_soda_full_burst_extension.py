"""소다의 확장이 두 운영에서 다르게 나오는지 - 이 인코딩의 핵심 주장.

확장 단계는 골든칩으로 정해지고, 칩은 그녀의 버스트 1회당 17이 나가고 풀 버스트
창 1회당 얼마쯤이 찬다. 그래서 궤적을 정하는 것은 벽시계가 아니라 **"그녀의
버스트 1회당 창 몇 개"**, 즉 덱의 Burst 3 좌석 수다.

- `_alternating_deck`: B3가 둘이라 그녀는 격 사이클에만 버스트한다. spend 1회당
  창 2회(리필 약 +7씩)를 받아 200초 열 창이 전부 15초, 단계도 II에서 안 내려온다.
- `_every_cycle_deck`: B3가 그녀뿐이라 매 창이 그녀의 spend를 동반한다. 창 1회당
  +7 대 spend 17이라 확실히 밀리고, 창이 15 -> 12 -> 10으로 내려간다.

B3가 하나인 덱에서 쿨다운만 40으로 늘리는 것은 이 대비를 만들지 못한다 -
그녀의 버스트도 창도 함께 절반이 되어 비가 그대로이므로, 벽시계로 느릴 뿐
똑같이 고갈된다. (이 파일의 이전 판이 그 덱을 "격 사이클"이라 부르고 있었다.)

## 이 픽스처는 실측의 재현이 아니다

`_alternating_deck`이 테스트 구간에서 최상위 단계를 유지하는 것은 사실이지만,
**평형이어서가 아니라 아직 안 떨어져서**다. 리필 약 +7이 두 창이면 +14이고
spend는 17이라 한 쌍마다 **-3씩 천천히 줄어든다**(톱니를 그리며). 200초는 열
창뿐이라 칩이 II단계 임계(20) 위에 머물 뿐이고, 전투를 늘리면 실제로 내려간다 -
`fight_duration=700`으로 재보면 27번째 창(t=545)에서 처음 I단계로 떨어지고,
800초 이후로는 II/I이 아니라 I/0을 오간다.

실제 유닛은 종류가 다르다. Fienn 실측(docs/measurements/soda-golden-chip-in-play.md)의
창당 리필은 8스택(확장 주입 시뮬은 9~10)이라 두 창이면 16~20으로 spend 17을
**덮는다** - 그래서 33 -> 40/41 -> 49/50 -> 33이 반복되는 자립적인 밴드가 된다.
여기 쓰는 합성 무기 스탯(SG 1.5발/초·재장전 없음)은 그 리필 속도를 내지 못하므로
이 파일은 그 밴드를 재현하지 않는다.

그러므로 이 테스트들이 증명하는 것은 **확장이 사이클마다 칩 상태를 따라간다는
것, 그래서 상수 하나로 접을 수 없다는 것**이다. 평형의 존재가 아니다.
`fight_duration`을 늘렸다가 감소를 보고 회귀로 오해하지 말 것 - 그것이 이
픽스처의 정상 거동이다.
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
    """그녀가 격 사이클로만 버스트하면 spend 1회당 창 2회의 리필이 붙어 칩이
    II단계 임계 위에 머문다 - 200초 열 창이 전부 15초다. 매 사이클 버스트하는
    아래 테스트와 정확히 갈리는 지점이고, 그 대비가 이 인코딩의 핵심 주장이다.

    이 덱도 한 쌍마다 -3씩 천천히 줄어든다(모듈 docstring 참조). 200초 안에서
    최상위 단계를 유지한다는 것이지 평형이라는 뜻이 아니다."""
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
