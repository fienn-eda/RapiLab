"""게이지가 보스 상수가 아니라 **덱**에서 계산되는지 - 산술로 단언한다.

**총합으로 단언하지 않는다.** 2026-08-05에 게이지를 2.0에서 2.4로 옮겼을 때
1871개 테스트 중 아무것도 안 깨졌다. 총합 테스트는 상수 변화에 둔감하다.

표 자체의 산술(키·값·이월·톡톡이)은 `tests/test_burst_gauge.py`에 있다. 여기
있는 것은 그 표가 **시뮬레이터의 사이클을 실제로 정하는가**다.
"""
import math

import pytest

from app.burst_cycle import FULL_BURST_OPEN_DELAY
from app.burst_gauge import GAUGE_FULL, quantize
from app.deck_search import (BossProfile, deck_is_valid, evaluate_deck,
                             feasible_orderings)
from app.models import UserNikkeState
from app.raid_simulator import simulate_raid
from app.skill_rules._helpers import instant_nuke_pulse_rule
from app.user_roster import load_roster

# 직전 창 종료에서 다음 창 시작까지, 게이지 말고 붙는 것: manual 모드의 티어 간격
# 0.1초 둘(티어 1 -> 티어 3), 그리고 그 B3의 캐스트가 확정된 뒤 창이 열리는 순서.
# 게이지 하한에 붙은 사이클의 간격은 정확히 `게이지 + 이 값`이다.
CYCLE_OVERHEAD = 0.2 + FULL_BURST_OPEN_DELAY

# 실측 기록의 덱 3(docs/measurements/burst-gauge-fill.md) - 게이지 판독이
# 2.55~3.5초로 상수 2.4보다 확실히 느린 편성이다.
MEASURED_DECK_3 = ["liter", "nayuta", "cinderella-crystal-wave-mg",
                   "cinderella", "modernia"]
# Fienn의 사격장 런(2026-07-27). 볼륨의 Drop the Beat가 **누적형** CDR이라
# 사이클마다 쿨이 짧아지고, 그래서 병목이 전투 중간에 쿨다운에서 게이지로
# 넘어간다 - 그 전환이 「첫 사이클만 보고 게이지를 건너뛴다」류의 최적화를
# 기각한 근거다.
VOLUME_DECK = ["volume", "prika", "mint", "snow-white-heavy-arms", "cinderella"]

# 합성 덱들이 도는 전투 길이. 「전투가 끝날 때까지 못 채운다」를 단언하려면 이
# 값이 상수로 보여야 한다.
SYNTHETIC_FIGHT_SEC = 180.0


def _nikke(slug):
    return UserNikkeState.model_validate({
        "character_slug": slug, "level": 200, "core_level": 0, "hp": 1_000_000.0,
        "atk": 60_000.0, "def_": 3_000.0,
        "skill_levels": {"skill1": 10, "skill2": 10, "burst": 10}})


def _ordering(slugs):
    specs, excluded = load_roster([_nikke(s) for s in slugs])
    assert not excluded, excluded
    return next(o for o in feasible_orderings(specs)
                if {u.slug for u in o} == set(slugs) and deck_is_valid(o))


def _boss():
    """실측이 이뤄진 환경 - 잡몹 없는 단일 보스, 180초."""
    return BossProfile(element="Iron", fight_duration=180.0)


@pytest.fixture(scope="module")
def real_deck_and_boss():
    return _ordering(MEASURED_DECK_3), _boss()


@pytest.fixture(scope="module")
def volume_deck():
    return _ordering(VOLUME_DECK)


def _cycle_starts_and_ends(result):
    return ([e["time"] for e in result["events"] if e["type"] == "full_burst_start"],
            [e["time"] for e in result["events"] if e["type"] == "full_burst_end"])


def _synthetic_deck(weapon, burst_energy):
    """무기와 타격당 게이지값만 다른 3인 최소 덱.

    차지 대미지는 실제 데이터를 그대로 따른다 - 수집된 105정에서 SR은 250%(또는
    앨리스의 350%)이고 **비차지 무기는 전부 정확히 100%**다. 비차지 무기에 배율을
    주면 `energy_per_hit`이 그것을 풀차지 배율로 읽어 이 대조가 무너진다.
    """
    deck = [{"slug": f"u{tier}", "burst_tier": tier, "element": "Iron",
             "cooldown": 20.0} for tier in (1, 2, 3)]
    stats = {member["slug"]: {"weapon": weapon, "damage_percent": 10.0,
                              "max_ammo": 60, "reload_time": 1.0,
                              "charge_time": 1.0,
                              "charge_damage_percent": 250.0 if weapon == "SR" else 100.0,
                              "burst_energy_pershot": burst_energy}
             for member in deck}
    return deck, stats


def _synthetic_result(deck_and_stats, **extra):
    deck, weapon_stats = deck_and_stats
    return simulate_raid(
        deck,
        {member["slug"]: [] for member in deck},
        burst_damage_percents={},
        base_stats={member["slug"]: {"atk": 10_000, "def": 0, "max_hp": 0}
                    for member in deck},
        enemy_def=0,
        gauge_charge_time=BossProfile.gauge_charge_time,
        fight_duration=SYNTHETIC_FIGHT_SEC,
        mode="manual",
        weapon_stats=weapon_stats,
        **extra,
    )


def _computed_gauge(deck_and_stats, **extra):
    return _synthetic_result(deck_and_stats, **extra)["gauge_charge_times"]


def test_the_table_is_keyed_by_the_cycle_the_fill_leads_INTO(real_deck_and_boss):
    """풀 버스트 k의 종료에서 잰 채움이 지배하는 것은 **사이클 k+1**이다.

    사이클 0(개전 -> 첫 버스트)은 표에 없다: 개전 게이지 0에서의 채움은 이
    모델의 범위 밖이라 `BossProfile.gauge_charge_time` 시드가 그대로 답한다.
    키가 0에서 시작하면 모든 덱의 게이지가 한 사이클씩 밀려 걸리는데, 정상상태에서는
    값이 거의 같아 **총딜로는 안 드러난다** - 그래서 키를 직접 본다.
    """
    ordered, boss = real_deck_and_boss
    result = evaluate_deck(ordered, boss)

    computed = result["gauge_charge_times"]
    _, ends = _cycle_starts_and_ends(result)
    assert computed, "덱이 자기 게이지를 계산해야 한다"
    assert 0 not in computed
    assert set(computed) <= set(range(1, len(ends) + 1))


def test_gauge_bound_cycles_use_the_computed_gauge(real_deck_and_boss):
    """게이지가 병목인 사이클의 간격은 정확히 `계산된 게이지 + 티어갭`이고,
    아닌 사이클은 그보다 길다(쿨다운이 정한다). 그 하한이 사이클마다 자기 키의
    값이라는 것이 이 변경의 요지다.

    「병목」과 **밀림**(`gauge_bound_cycles`)은 같은 수가 아니다 - 게이지와
    쿨다운이 같은 시각인 사이클은 병목이지만 아무것도 안 밀렸다. 그래서 여기서
    다시 센 병목 수는 밀림 수의 **상한**이다. 등호로 못박으면 동점이 생기는 날
    엉뚱한 이유로 빨개진다.
    """
    ordered, boss = real_deck_and_boss
    result = evaluate_deck(ordered, boss)

    computed = result["gauge_charge_times"]
    starts, ends = _cycle_starts_and_ends(result)
    bottleneck = 0
    for cycle_index, seconds in sorted(computed.items()):
        if cycle_index >= len(starts):
            continue        # 채움은 쟀지만 그 사이클은 전투 안에서 안 일어났다
        gap = starts[cycle_index] - ends[cycle_index - 1]
        assert gap >= seconds + CYCLE_OVERHEAD - 1e-6, "게이지는 하한이다"
        if gap == pytest.approx(seconds + CYCLE_OVERHEAD, abs=1e-6):
            bottleneck += 1
    assert bottleneck, "이 편성은 게이지가 병목인 사이클이 있어야 한다"
    assert result["gauge_bound_cycles"], "이 편성은 실제로 밀리는 사이클이 있다"
    assert result["gauge_bound_cycles"] <= bottleneck


def test_the_opening_cycle_is_not_counted_as_gauge_bound():
    """첫 사이클은 **모든 덱에서** 게이지가 정한다 - 돌고 있던 쿨다운이 아예
    없어서 게이지가 유일한 시작 조건이다. 그래서 세지 않는다: 세면 어떤 덱도
    0이 될 수 없고, 「밀림 0」이라는 말이 아예 못 나온다.

    SR 덱은 창마다 게이지를 2초대에 채워 두 번째 사이클부터는 쿨다운이 병목이다.
    스케줄러는 첫 사이클을 여전히 「게이지가 정했다」고 선언하는데(아래 첫
    단언), 그런데도 집계는 **0**이어야 한다 - 첫 사이클을 세는 구현은 여기서 1을
    낸다.
    """
    result = _synthetic_result(_synthetic_deck("SR", burst_energy=28_000))
    tier1 = [e for e in result["events"]
             if e["type"] == "burst" and e["tier"] == 1]

    assert tier1[0]["gauge_bound"] is True
    assert result["gauge_bound_cycles"] == 0
    # 첫 사이클엔 돌고 있던 쿨다운이 없어 그 차이가 **무한대**다. 그대로 실으면
    # 합계가 통째로 inf가 되므로 스케줄러가 그 자리에서 0으로 못박는다.
    assert tier1[0]["gauge_delay"] == 0.0
    assert result["gauge_delay_seconds"] == 0.0


def test_a_cycle_the_deck_cannot_fill_does_not_fire_at_the_boss_seed():
    """반대 방향 - 타격당 500짜리 MG 덱은 게이지가 20초대라 20초 쿨다운을 매
    사이클 이긴다. **마지막 창은 전투가 끝나기 전에 게이지를 못 채운다**: 그
    사이클은 일어나지 않고, 표는 그것을 무한대로 말한다.

    이 테스트의 옛 기대값(`[True] * (n-1) + [False]`)은 버그를 정답으로 적고
    있었다. 못 채우는 사이클을 표에서 **빼면** `burst_cycle`이
    `.get(cycle_index, gauge_charge_time)`으로 보스 시드(2.4초)를 읽는데, 아래
    첫 단언이 보이듯 그 시드는 남은 전투 시간에 **넉넉히 들어간다**. 그래서
    20초를 못 채우는 덱이 2.4초 만에 채운 것처럼 한 사이클을 더 터뜨렸고, 그
    공짜 사이클만 「게이지가 안 밀었다(False)」로 보였다 - 마지막 사이클이
    유일하게 시드를 탄 사이클이었기 때문이다. 이 편성에서 그 사이클은 총딜
    **+0.87%**다(2026-08-22 대조). 편향의 방향이 이 기능의 존재 이유와 반대인
    것이 요점이다: 이득을 보는 것이 하필 게이지를 못 채우는 덱이다.

    첫 사이클을 빼고 세므로 밀린 사이클 수는 사이클 수보다 하나 작다.
    """
    result = _synthetic_result(_synthetic_deck("MG", burst_energy=500))
    tier1 = [e for e in result["events"]
             if e["type"] == "burst" and e["tier"] == 1]
    computed = result["gauge_charge_times"]
    ends = [e["time"] for e in result["events"] if e["type"] == "full_burst_end"]

    assert computed[len(ends)] == math.inf, "마지막 창은 전투 안에 못 채운다"
    # 시드로 떨어지는 구현이 정말로 사이클을 하나 더 얻는지 확인한다 - 이
    # 부등식이 깨지면(마지막 창이 전투 끝에 너무 붙으면) 시드도 못 들어가므로
    # 이 테스트는 아무것도 안 재게 되고 옛 구현도 그대로 통과한다.
    assert ends[-1] + BossProfile.gauge_charge_time < SYNTHETIC_FIGHT_SEC
    assert computed[1] > BossProfile.gauge_charge_time, "이 덱은 시드보다 훨씬 느리다"
    assert [e["gauge_bound"] for e in tier1] == [True] * len(tier1)
    assert result["gauge_bound_cycles"] == len(tier1) - 1
    # 게이지가 20초대인데 쿨다운이 20초라, 밀린 사이클마다 초 단위로 민다.
    # 합계는 유한하고(첫 사이클의 -inf가 안 샜다는 뜻) 사이클 수보다 크다.
    assert math.isfinite(result["gauge_delay_seconds"])
    assert result["gauge_delay_seconds"] > result["gauge_bound_cycles"]


def test_a_deck_that_cannot_charge_gets_a_longer_gauge_than_one_that_can():
    """SR 덱과 MG 덱. 타격당 28,000 대 500이라 56배 차이가 나므로 MG 덱의
    게이지가 반드시 더 길다 - 이 부등식이 이 변경의 요지다.

    총딜을 비교하지 않는다: 두 덱은 딜도 다르고, 총합은 상수 변화에 둔감하다는
    것이 2026-08-05의 교훈이다.
    """
    sr_gauge = _computed_gauge(_synthetic_deck("SR", burst_energy=28_000))
    mg_gauge = _computed_gauge(_synthetic_deck("MG", burst_energy=500))
    assert sr_gauge and mg_gauge
    assert min(sr_gauge.values()) < min(mg_gauge.values())


def test_bottleneck_flips_from_cooldown_to_gauge_as_cdr_ramps(volume_deck):
    """누적형 CDR(볼륨의 예열 방식)에서는 초반이 쿨다운 병목이고 후반이 게이지
    병목이다. 실측 타임라인이 간격 7.56 -> 4.86 -> 2.40초로 3번째 사이클에서
    뒤집히고, 그 뒤가 전부 게이지 병목이다.

    이 전환이 존재한다는 것이 「첫 사이클만 보고 게이지를 건너뛴다」류의
    최적화를 기각한 근거다(스펙의 「조기 종료는 채택하지 않는다」).
    """
    result = evaluate_deck(volume_deck, _boss())

    starts, ends = _cycle_starts_and_ends(result)
    gaps = [nxt - end for end, nxt in zip(ends, starts[1:])]
    assert gaps[0] > gaps[-1], "누적 CDR이면 간격이 줄어야 한다"
    computed = result["gauge_charge_times"]
    # gaps[-1]은 ends[-2] -> starts[-1], 즉 **사이클 len(gaps)**의 간격이다.
    late = len(gaps)
    assert gaps[-1] == pytest.approx(computed[late] + CYCLE_OVERHEAD, abs=1e-6), (
        "정상상태에서는 게이지가 사이클을 정한다")


# --- 스킬이 만드는 타격 ------------------------------------------------------
# 라이더·드론·오토파이어·주기 타격은 `damage_log`에서 유도한다(`_gauge_skill_hits`).
# 여기 있는 것은 그 유도가 **덱의 게이지를 실제로 움직이는가**다 - 로그에 키만
# 실리고 `fill_times`가 안 읽으면 조용히 1타로 세어진다.


def _per_shot_pulse(deck, percent=100.0, **pulse_kwargs):
    """덱의 첫 좌석이 자기 평타마다 스킬 타격 하나를 만든다."""
    return {deck[0]["slug"]: [
        (1, "every", [instant_nuke_pulse_rule("per_shot", percent, **pulse_kwargs)])]}


def test_skill_hits_charge_the_gauge_and_the_declared_count_multiplies():
    """선언한 타격 수가 `record` -> `damage_log` -> `fill_times`까지 흐르는가.

    같은 덱·같은 펄스에 개수만 1과 8로 갈라 **게이지가 갈리는지** 본다. 로그 행에
    키만 싣고 `fill_times`가 안 읽는 구현은 두 게이지가 같아져 여기서 걸린다
    (스펙에만 넣고 조용히 1로 세는 것이 이 배선의 유일한 실패 모드다).
    """
    deck_and_stats = _synthetic_deck("MG", burst_energy=500)
    deck, _ = deck_and_stats
    one = _computed_gauge(deck_and_stats, per_shot_rules=_per_shot_pulse(deck))
    eight = _computed_gauge(deck_and_stats,
                            per_shot_rules=_per_shot_pulse(deck, gauge_hits=8))
    assert one and eight
    assert min(eight.values()) < min(one.values())

    logged = {entry["gauge_hits"]
              for entry in _synthetic_result(
                  deck_and_stats,
                  per_shot_rules=_per_shot_pulse(deck, gauge_hits=8))["damage_log"]
              if entry["source"] == "per_shot_nuke"}
    assert logged == {8}


def test_a_dot_tick_charges_nothing_but_a_distributed_hit_charges():
    """`GAUGE_INERT_DAMAGE_TYPES`가 실제로 갈라내는가 - **양쪽으로** 본다.

    `sustained`(초당 DoT)는 아무 영향이 없어야 하고 `distributed`(광역으로
    분산된 개별 타격)는 게이지를 앞당겨야 한다. 한쪽만 보면 「스킬 타격을 통째로
    안 세는」 구현도, 「아무것도 안 거르는」 구현도 통과한다.
    """
    deck_and_stats = _synthetic_deck("MG", burst_energy=500)
    deck, _ = deck_and_stats
    plain = _computed_gauge(deck_and_stats)
    dot = _computed_gauge(deck_and_stats,
                          per_shot_rules=_per_shot_pulse(deck, damage_type="sustained"))
    spread = _computed_gauge(deck_and_stats,
                             per_shot_rules=_per_shot_pulse(deck, damage_type="distributed"))
    assert plain and dot and spread
    assert dot == plain
    assert min(spread.values()) < min(plain.values())


def test_normal_attacks_are_not_counted_a_second_time_from_the_log():
    """평타는 `gauge_shots_by_slug`가 이미 세고 풀차지 여부까지 싣는다.
    `damage_log`에서 유도할 때 그 행을 안 빼면 평타가 **두 번** 세어진다.

    타격당 GAUGE_FULL/4라 창 종료 뒤 **4번째** 평타에서 정확히 차야 한다.
    두 번 세는 구현은 2번째에서 차서 값이 갈린다. (룰이 없는 덱이라 로그가
    전부 평타이고, `core_hittable`이 거짓이라 관통 2행 분할도 없다.)
    """
    deck_and_stats = _synthetic_deck("AR", burst_energy=GAUGE_FULL / 4)
    result = _synthetic_result(deck_and_stats)
    assert {entry["source"] for entry in result["damage_log"]} == {"normal_attack"}
    end = next(e["time"] for e in result["events"] if e["type"] == "full_burst_end")
    after = sorted(entry["time"] for entry in result["damage_log"]
                   if entry["time"] >= end)
    assert result["gauge_charge_times"][1] == pytest.approx(quantize(after[3] - end))


def test_heavy_arms_auto_fire_volley_declares_its_folded_hits():
    """접힌 볼리가 개수를 **기록하는 자리에서** 선언한다 - 오늘 그런 유닛은
    헤비암즈 하나뿐이다. 「장전된 탄약 수만큼 순차로」가 한 인스턴스에 값으로
    접혀 있어 행을 세면 5타·15타가 각각 1타로 세어진다.

    `damage_type == "sequential"`을 판별자로 쓰지 않는다는 것도 여기서 지킨다:
    개수는 로그 행이 **싣고 있어야** 하고, 타입에서 되읽는 것이 아니다.
    """
    from app.skill_rules.registry import (get_per_shot_rules,
                                          get_weapon_mode_schedules)
    from tests.test_skill_rules_snow_white_heavy_arms import (SWHA_VALUES,
                                                              SWHA_WEAPON_STATS,
                                                              _swha_sim_deck)

    slug = "snow-white-heavy-arms"
    deck = _swha_sim_deck()
    result = simulate_raid(
        deck=deck, rules_by_slug={}, burst_damage_percents={},
        base_stats={m["slug"]: {"atk": 10_000.0} for m in deck},
        enemy_def=0.0, gauge_charge_time=5.0, fight_duration=30.0, mode="auto",
        base_crit_rate=0.0,
        weapon_stats={slug: {**SWHA_WEAPON_STATS, "burst_energy_pershot": 28_000}},
        weapon_mode_schedules={slug: get_weapon_mode_schedules(slug, SWHA_VALUES)},
        per_shot_rules={slug: get_per_shot_rules(slug, SWHA_VALUES)},
    )
    volleys = [entry for entry in result["damage_log"]
               if entry["damage_type"] == "sequential"]
    assert volleys, "오토파이어 볼리가 나와야 한다"
    # 기본 케이던스는 장탄 5, Fully Active 창 안은 5 + ▲10 = 15.
    assert sorted({entry["gauge_hits"] for entry in volleys}) == [5, 15]
    # 같은 샷의 「모든 적」 추가타는 접히지 않은 1타다 - 볼리만 개수를 갖는다.
    sweeps = [entry for entry in result["damage_log"]
              if entry["source"] == "per_shot_nuke" and entry["damage_type"] == "attack"]
    assert sweeps and {entry["gauge_hits"] for entry in sweeps} == {1}
