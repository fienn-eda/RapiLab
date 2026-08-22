"""단독편성 실측이 그대로 단언이 된다 - docs/measurements/burst-gauge-fill.md.

앨리스 5발 / 에이드 7발 / 드레이크 10발 / 블랑 250발 / 리타 500발 / 크라운 1000발이
각각 게이지를 채운다. 여섯이 독립적으로 같은 총량을 준다.
"""
import math

import pytest

from app.burst_gauge import (GAUGE_FULL, GAUGE_QUANTUM_SEC, energy_per_hit,
                             fill_times, quantize)
from app.deck_search import BossProfile


def _weapon(burst_energy, pellets=1, charge_damage_percent=0.0):
    return {"burst_energy_pershot": burst_energy, "pellets_per_shot": pellets,
            "charge_damage_percent": charge_damage_percent}


def test_alice_fills_the_gauge_in_five_full_charges():
    # SR 28,000 x 3.5배(차지 대미지 350%) = 98,000. 5발 = 490,000 = 156.8px 판독 156.
    alice = _weapon(28_000, charge_damage_percent=350.0)
    assert energy_per_hit(alice, full_charge=True) == pytest.approx(98_000)
    assert 5 * energy_per_hit(alice, full_charge=True) == pytest.approx(490_000)


def test_alice_and_ade_differ_only_by_the_charge_multiplier():
    """총량을 몰라도 성립하는 검증 - 같은 무기·같은 발당값에 배율만 3.5 대 2.5인데
    실측 발수가 5 대 7이다."""
    alice = energy_per_hit(_weapon(28_000, charge_damage_percent=350.0), full_charge=True)
    ade = energy_per_hit(_weapon(28_000, charge_damage_percent=250.0), full_charge=True)
    assert alice / ade == pytest.approx(3.5 / 2.5)
    assert 5 * alice == pytest.approx(7 * ade)


def test_tap_fire_takes_the_base_value_not_the_charge_multiplier():
    """헬름을 차지 113%와 106%로 쏜 두 발이 합쳐 18px(= 17.92px 예상). 차지 비율에
    비례한다면 두 발이 서로 다른 값을 줬어야 한다."""
    helm = _weapon(28_000, charge_damage_percent=250.0)
    assert energy_per_hit(helm, full_charge=False) == pytest.approx(28_000)


def test_shotgun_pellets_multiply():
    # 드레이크 4,500 x 10펠릿 = 45,000. 10발 = 450,000 = 144px 판독 145.
    drake = _weapon(4_500, pellets=10)
    assert energy_per_hit(drake, full_charge=False) == pytest.approx(45_000)


@pytest.mark.parametrize("burst_energy,shots", [(2_000, 250), (1_000, 500), (500, 1_000)])
def test_magazine_weapons_fill_at_the_measured_shot_counts(burst_energy, shots):
    """블랑(AR) 250발 / 리타(SMG) 500발 / 크라운(MG) 1000발이 각각 버충 완료."""
    assert shots * energy_per_hit(_weapon(burst_energy), full_charge=False) == GAUGE_FULL


def test_quantize_snaps_to_the_grid():
    """게이지 -> 사이클 길이 -> 재장전 위치 -> 게이지의 고리가 연속값이면 진동할 수
    있다. 격자로 유한 상태를 만든다.

    격자 폭 자체를 못박는 것은 그것이 취향이 아니라 수렴 조건이기 때문이다:
    0.05에서는 표본 400덱 중 18덱이 32패스 안에 안 멈춘다(GAUGE_QUANTUM_SEC 참조).
    """
    assert quantize(3.1799) == pytest.approx(3.20)
    assert quantize(2.4) == pytest.approx(2.40)
    assert quantize(3.14) == pytest.approx(3.10)   # 0.05 격자라면 3.15다
    assert GAUGE_QUANTUM_SEC == 0.1


# --- 채움 시간 표 ---------------------------------------------------------
# `fill_times`는 덱의 발사 타임라인을 사이클별 게이지 하한으로 바꾼다. 여기 있는
# 것은 전부 산술이다 - 총합은 상수 변화에 둔감하다는 것이 2026-08-05의 교훈이라
# 이 표는 값과 키를 직접 못박는다.


def test_the_table_is_keyed_by_the_cycle_the_fill_leads_INTO():
    """풀 버스트 k의 종료에서 잰 채움 시간이 지배하는 것은 **사이클 k+1**이다.

    `simulate_burst_cycle`의 `gauge_ready = time + gauge[cycle_index]`에서
    `time`은 직전 풀 버스트의 종료이고 `cycle_index`는 지금 발사하려는
    사이클이다. 그래서 `enumerate(full_burst_ends)`의 인덱스 0(첫 창의 종료)이
    정하는 것은 **두 번째** 사이클이다.

    정상상태에서는 사이클마다 채움 시간이 거의 같아 한 칸 밀려도 총딜로는 안
    드러난다 - 그래서 두 창의 채움을 1초와 5초로 **다르게** 만들어 키를 값으로
    못박는다.
    """
    stats = {"u": _weapon(GAUGE_FULL)}
    shots = {"u": [(11.0, False), (25.0, False)]}
    assert fill_times(shots, [10.0, 20.0], weapon_stats=stats,
                      fight_duration=100.0) == {1: 1.0, 2: 5.0}


def test_the_full_burst_window_itself_does_not_charge():
    """게이지는 창 **밖에서만** 찬다. 창 안에서도 찬다고 보면 다섯 덱 전부 창이
    끝나기 전에 가득 차서 덱2의 3.7초 판독이 존재할 수 없다."""
    stats = {"u": _weapon(GAUGE_FULL)}
    shots = {"u": [(5.0, False), (12.0, False)]}
    assert fill_times(shots, [10.0], weapon_stats=stats,
                      fight_duration=100.0) == {1: 2.0}


def test_overflow_does_not_carry_into_the_next_cycle():
    """초과분은 이월되지 않는다 - 게이지 두 개를 채우는 샷이 있어도 다음 사이클은
    자기 몫을 0에서 다시 채운다."""
    stats = {"u": _weapon(2 * GAUGE_FULL)}
    shots = {"u": [(11.0, False), (23.0, False)]}
    assert fill_times(shots, [10.0, 20.0], weapon_stats=stats,
                      fight_duration=100.0) == {1: 1.0, 2: 3.0}


def test_a_cycle_that_never_fills_is_reported_as_infinite():
    """전투가 끝날 때까지 못 채운 사이클은 **무한대**로 싣는다 - 키를 빼면 안 된다.

    `burst_cycle`은 표에 없는 사이클을 `.get(cycle_index, gauge_charge_time)`으로
    읽어 **보스 시드**(`BossProfile.gauge_charge_time`, 2.4초)에 떨어뜨린다.
    그래서 키를 빼는 구현에서는 「이 사이클은 절대 못 찬다」가 「2.4초면 찬다」로
    뒤집혀 그 사이클이 공짜로 터진다 - 시드보다 **느린** 값이 나와야 할 자리에서
    거의 모든 실덱보다 **빠른** 값이 나오는 것이라, 부호가 뒤집힌 버그다.

    그래서 「비어 있지 않다」로 끝내지 않고 시드와 직접 대조한다: `{}`를 돌려주는
    옛 구현도, 시드보다 작은 아무 유한값을 채워 넣는 구현도 여기서 걸린다.
    """
    stats = {"u": _weapon(1.0)}
    table = fill_times({"u": [(11.0, False)]}, [10.0],
                       weapon_stats=stats, fight_duration=100.0)
    assert table == {1: math.inf}
    assert table[1] > BossProfile.gauge_charge_time


def test_the_charge_multiplier_only_reaches_full_charge_shots():
    """앨리스(SR 28,000 x 3.5배)의 풀차지 6발 대 톡톡이 18발. 톡톡이를 배율로
    세면 덱5가 2.01초 대신 0.95초로 나온다(측정 기록에서 실제로 밟은 오류)."""
    alice = {"u": _weapon(28_000, charge_damage_percent=350.0)}
    full = {"u": [(10.0 + i, False) for i in range(1, 40)]}
    tap = {"u": [(10.0 + i, True) for i in range(1, 40)]}
    assert fill_times(full, [10.0], weapon_stats=alice,
                      fight_duration=100.0) == {1: 6.0}
    assert fill_times(tap, [10.0], weapon_stats=alice,
                      fight_duration=100.0) == {1: 18.0}


def test_a_deck_with_no_gauge_data_at_all_gets_no_table():
    """채움원이 하나도 없는 입력의 「안 참」은 **덱의 성질이 아니라 입력의
    부재**다 - 표를 비워 시드가 답하게 둔다. 무한대로 답하면 게이지 데이터를 안
    주는 호출자(손으로 만든 무기 프로필)의 전투가 사이클 0에서 끝난다.

    실제 유닛은 값이 없으면 `load_roster`가 아예 제외하므로 실덱은 이 가지에 못
    들어오고, 그래서 이 관용이 「못 채우는 사이클은 무한대」를 약화시키지 않는다."""
    assert fill_times({"u": [(11.0, False)]}, [10.0],
                      weapon_stats={"u": {"weapon": "AR"}},
                      fight_duration=100.0) == {}


def test_one_seat_without_gauge_data_does_not_disarm_the_rest():
    """위 관용은 **덱 전체**에 채움원이 없을 때만 열린다. 한 좌석만 값이 없으면
    나머지는 그대로 세고, 못 채우면 무한대가 나온다 - 좌석 단위로 관용하면 값이
    없는 좌석 하나가 그 덱의 게이지 판정을 통째로 꺼 버린다."""
    stats = {"quiet": {"weapon": "AR"}, "loud": _weapon(1.0)}
    shots = {"quiet": [(11.0, False)], "loud": [(12.0, False)]}
    assert fill_times(shots, [10.0], weapon_stats=stats,
                      fight_duration=100.0) == {1: math.inf}


# --- 아군 소모탄 트리거 채움원 (bonus_fills) -------------------------------
# 무기 타격과 다른 채움원: 아군 누적 소모탄이 문턱을 넘을 때마다 fraction *
# GAUGE_FULL이 한 번에 붙는다(인어공주 Bubble Order, 신데렐라: 크리스탈 웨이브
# Beauty-Full). 카운터는 `ammo_rounds_by_slug`로 온다 - `shots_by_slug`와
# 나란한 {슬러그: [발당 라운드, ...]}.


def test_bonus_fill_adds_gauge_when_ally_rounds_cross_the_threshold():
    stats = {"u": _weapon(1.0)}  # 타격 자체는 무시할 만큼 작다
    shots = {"u": [(11.0, False), (12.0, False), (13.0, False)]}
    rounds = {"u": [1.0, 1.0, 1.0]}
    fills = [{"every_ally_rounds": 3.0, "fraction": 1.0}]
    assert fill_times(shots, [10.0], weapon_stats=stats, fight_duration=100.0,
                      ammo_rounds_by_slug=rounds, bonus_fills=fills) == {1: 3.0}


def test_bonus_fill_can_cross_several_thresholds_in_one_shot():
    """탄약 주머니 발 하나가 수백 라운드를 회계하면 한 발로 문턱을 여러 번 넘을
    수 있다 - 인어공주 Bubble Barrage(`build_bubble_barrage_scheduled_nukes`)의
    기존 `while` 다중 크로싱과 같은 규칙."""
    stats = {"u": _weapon(1.0)}
    shots = {"u": [(11.0, False)]}
    rounds = {"u": [900.0]}
    fills = [{"every_ally_rounds": 400.0, "fraction": 0.5}]
    # 900 // 400 = 문턱을 두 번 넘는다 -> 0.5 x 2 = 1.0 x GAUGE_FULL, 한 발로 꽉 찬다.
    assert fill_times(shots, [10.0], weapon_stats=stats, fight_duration=100.0,
                      ammo_rounds_by_slug=rounds, bonus_fills=fills) == {1: 1.0}


def test_two_fill_sources_share_one_ally_rounds_counter():
    """컨트롤러 룰링 R2 회귀: 충전원이 둘인 덱(인어공주 + 신데렐라: 크리스탈
    웨이브)에서 아군 소모탄은 **한 번만** 세어져야 한다. 증가가 `for fill`
    루프 안에 있으면(브리프 샘플의 결함) 소스 수만큼 중복 계상되어 게이지가
    실제보다 빨리 찬다 - 8발째(누적 800발)가 아니라 더 일찍 꽉 찬다."""
    stats = {"u": _weapon(0.0)}  # 무기 타격은 게이지에 기여하지 않는다 - 이 축만 본다
    shots = {"u": [(11.0 + i, False) for i in range(8)]}      # 11.0..18.0
    rounds = {"u": [100.0] * 8}                                # 누적 100..800
    fills = [
        {"every_ally_rounds": 400.0, "fraction": 0.37},  # 인어공주 Bubble Order (lv10)
        {"every_ally_rounds": 200.0, "fraction": 0.12},  # 신데렐라: CW Beauty-Full (lv10)
    ]
    # 200 문턱은 4번(shots 2,4,6,8), 400 문턱은 2번(shots 4,8) 넘는다:
    # 4*0.12 + 2*0.37 = 1.22 x GAUGE_FULL >= 1.0 - 8발째(누적 800)에 꽉 찬다.
    # 증가가 소스마다 중복되면 누적이 실제보다 두 배로 빨리 불어나 이 경계 안에
    # 못 들어온다(수동 대조: 이 시나리오에서 8발 안에 표에 실리지 않는다).
    assert fill_times(shots, [10.0], weapon_stats=stats, fight_duration=100.0,
                      ammo_rounds_by_slug=rounds, bonus_fills=fills) == {1: 8.0}


def test_bonus_fill_defaults_to_one_round_per_shot_when_rounds_are_not_given():
    """`ammo_rounds_by_slug`를 안 주면(그런 유닛이 없는 덱) 발당 1라운드로
    센다 - `context.shot_ammo_rounds`의 기본과 같다."""
    stats = {"u": _weapon(0.0)}
    shots = {"u": [(11.0 + i, False) for i in range(4)]}
    fills = [{"every_ally_rounds": 4.0, "fraction": 1.0}]
    assert fill_times(shots, [10.0], weapon_stats=stats,
                      fight_duration=100.0, bonus_fills=fills) == {1: 4.0}


def test_ally_rounds_carry_across_cycles_not_reset_per_window():
    """리뷰 Finding 2: 아군 누적 소모탄은 게임에서 전투 내내 안 비는 카운터다
    (원문 "total ammo expended by allies") - Bubble Barrage의 기존 구현과 같은
    회계. 창마다 0에서 다시 세면 이전 창에서 쌓인 라운드가 사라져 다음 창의
    위상이 어긋난다."""
    stats = {"u": _weapon(0.0)}
    # 첫 창(10~20) 안에서 300발이 쌓이고, 둘째 창(20~)이 열린 뒤 100발이 더
    # 온다 - 누적이면 둘째 창은 시작부터 이미 300발을 이어받아 이 한 발로 곧장
    # 400 문턱을 넘는다. 창마다 리셋이면 둘째 창은 0부터 다시 세므로 100발로는
    # 어림도 없다(이 표에는 실리지도 않는다).
    shots = {"u": [(12.0, False), (21.0, False)]}
    rounds = {"u": [300.0, 100.0]}
    fills = [{"every_ally_rounds": 400.0, "fraction": 1.0}]
    result = fill_times(shots, [10.0, 20.0], weapon_stats=stats, fight_duration=100.0,
                        ammo_rounds_by_slug=rounds, bonus_fills=fills)
    assert result == {1: 11.0, 2: 1.0}


# --- 게이지 충전 속도 배율 (speed_multiplier_at) -----------------------------
# 아니스: 스타·그레이브·마나가 등록하는 `burst_gauge_fill_speed_percent`를
# 실제로 곱한다. 스칼라 하나가 아니라 (슬러그, 시각) -> 배율 콜백인 이유:
# 스코프가 스쿼드(아니스·그레이브)와 self(마나) 둘 다 있고, 값이 전투 도중
# 켜지고 꺼진다(그레이브의 Heat Emission, 마나의 Metal σ)ㅡ창 전체에 쓰는
# 상수 하나로는 이 셋을 같은 자리에서 표현할 수 없다.


def test_speed_multiplier_shortens_the_fill():
    """+50% 배율이면 같은 무기가 게이지를 더 적은 발로 채운다 - 발 하나가
    GAUGE_FULL의 1/3이면 배율 없이 3발, +50%면 2발째에 채운다."""
    stats = {"u": _weapon(GAUGE_FULL / 3)}
    shots = {"u": [(10.0 + i, False) for i in range(1, 5)]}
    assert fill_times(shots, [10.0], weapon_stats=stats,
                      fight_duration=100.0) == {1: 3.0}
    assert fill_times(shots, [10.0], weapon_stats=stats, fight_duration=100.0,
                      speed_multiplier_at=lambda slug, time: 1.5) == {1: 2.0}


def test_speed_multiplier_can_vary_by_time():
    """마나의 Metal σ처럼 배율이 창 도중에 꺼질 수 있다 - 뒤쪽 절반만 배율이
    붙으면 그 구간의 몫만 빨리 찬다."""
    stats = {"u": _weapon(GAUGE_FULL / 4)}
    shots = {"u": [(11.0, False), (12.0, False), (13.0, False), (14.0, False)]}
    assert fill_times(shots, [10.0], weapon_stats=stats,
                      fight_duration=100.0) == {1: 4.0}
    # 13초부터 배율 2배: 세 번째 발(13초)이 1/4 x 2 = 1/2를 더해 앞 두 발의
    # 1/2와 합쳐 정확히 채운다 - 네 번째 발이 필요 없다.
    assert fill_times(shots, [10.0], weapon_stats=stats, fight_duration=100.0,
                      speed_multiplier_at=lambda slug, time: 2.0 if time >= 13.0 else 1.0
                      ) == {1: 3.0}


def test_speed_multiplier_can_vary_by_slug():
    """self 스코프(마나)와 squad 스코프(아니스·그레이브)를 같은 콜백 하나로
    가른다 - 슬러그별로 다른 값을 돌려줄 수 있어야 한다.

    리뷰 Important 2: 배율 0인 슬러그를 **먼저** 쏘게 한다. 배율 1인 슬러그가
    먼저면 그 한 발로 게이지가 다 차서 `break`하고 배율 0인 슬러그의 발은
    아예 안 평가된다 - slug를 통째로 무시하는 구현도 통과하는 항진명제였다
    (2026-08-22 리뷰에서 지적, 두 구현을 실제로 돌려 `{1: 1.0}`으로 구분 못
    함을 확인). b(배율 0)가 먼저면: 배율을 슬러그별로 제대로 가르는 구현은
    b의 발을 0으로 세어 안 차고 a(배율 1)의 발에서 채워 사이클 **2.0**초 -
    slug를 무시해 모두에게 a의 배율(1.0)을 주는 구현은 b의 발부터 이미 다
    채워 **1.0**초로 갈린다."""
    stats = {"a": _weapon(GAUGE_FULL), "b": _weapon(GAUGE_FULL)}
    shots = {"b": [(11.0, False)], "a": [(12.0, False)]}
    per_slug = fill_times(shots, [10.0], weapon_stats=stats, fight_duration=100.0,
                          speed_multiplier_at=lambda slug, time: 1.0 if slug == "a" else 0.0)
    assert per_slug == {1: 2.0}


# --- 스킬이 만드는 타격 (skill_hits_by_slug) --------------------------------
# 라이더·드론·오토파이어·주기 타격은 무기가 쏜 샷이 아니지만 게이지를 채운다.
# 값은 유닛별 표가 아니라 **그 유닛 무기의 기본값** 하나다(실측 세 유닛이
# 독립적으로 확인, docs/measurements/burst-gauge-fill.md 「정정」).


def test_skill_hits_fill_the_gauge_at_the_units_base_energy():
    """스킬이 만드는 타격도 게이지를 채운다 - 그 유닛 무기의 기본값으로.

    라이더든 드론이든 오토파이어든 값은 하나다(실측 세 유닛 독립 확인,
    docs/measurements/burst-gauge-fill.md 「정정」). 풀차지 배율은 무기가 쏜
    샷에만 붙으므로 스킬 타격은 배율을 안 받는다.
    """
    stats = {"a": {"burst_energy_pershot": 100_000, "charge_damage_percent": 250.0}}
    # 무기 샷 둘(각 100,000) + 스킬 타격 셋(각 100,000) = 500,000 = 가득
    got = fill_times(
        {"a": [(11.0, True), (12.0, True)]}, [10.0],
        weapon_stats=stats, fight_duration=60.0,
        skill_hits_by_slug={"a": [(13.0, 3)]})
    assert got == {1: pytest.approx(3.0)}


def test_skill_hit_count_multiplies():
    """접힌 볼리 한 행이 N타로 세어진다. 헤비암즈의 오토파이어가 그 모양이다."""
    stats = {"a": {"burst_energy_pershot": 100_000, "charge_damage_percent": 250.0}}
    one = fill_times({"a": []}, [10.0], weapon_stats=stats, fight_duration=60.0,
                     skill_hits_by_slug={"a": [(11.0, 1), (12.0, 5)]})
    # 11.0에 1타(100,000)뿐이면 아직 부족하고, 12.0의 5타로 넘긴다.
    assert one == {1: pytest.approx(2.0)}


def test_skill_hits_never_take_the_charge_multiplier():
    """풀차지 배율은 **그 유닛의 무기가 쏜 샷**에만 붙는다. 스킬 타격에도 걸면
    차지 무기를 든 유닛의 게이지가 배율만큼 빨라진다.

    위의 두 테스트는 이것을 못 가른다 - 배율이 붙어도 같은 발에서 채워져 값이
    같다. 여기서는 배율(2.5배)이 붙는 구현이 **첫 타격에서** 채워 1.0초가 되고,
    기본값으로 세는 구현만 3.0초가 나온다.
    """
    stats = {"a": {"burst_energy_pershot": 100_000, "charge_damage_percent": 250.0}}
    hits = {"a": [(11.0, 2), (12.0, 2), (13.0, 1)]}
    assert fill_times({"a": []}, [10.0], weapon_stats=stats, fight_duration=60.0,
                      skill_hits_by_slug=hits) == {1: pytest.approx(3.0)}


def test_skill_hits_take_the_gauge_fill_speed_multiplier():
    """「버스트 게이지 충전 속도」가 무기 타격만 빠르게 한다고 볼 근거가 없다 -
    스킬 타격에도 같은 배율이 걸린다(컨트롤러 결정 D6).

    배율을 스킬 타격에 안 거는 구현은 배율을 줘도 3타격을 다 써서 두 단언이
    같은 3.0초가 된다.
    """
    stats = {"a": {"burst_energy_pershot": 200_000, "charge_damage_percent": 250.0}}
    hits = {"a": [(11.0, 1), (12.0, 1), (13.0, 1)]}
    assert fill_times({"a": []}, [10.0], weapon_stats=stats, fight_duration=60.0,
                      skill_hits_by_slug=hits) == {1: pytest.approx(3.0)}
    assert fill_times({"a": []}, [10.0], weapon_stats=stats, fight_duration=60.0,
                      skill_hits_by_slug=hits,
                      speed_multiplier_at=lambda slug, time: 1.5) == {1: pytest.approx(2.0)}


def test_skill_hits_do_not_spend_ammunition():
    """스킬 타격은 탄약을 안 쓰므로 아군 누적 소모탄 카운터에 **0을 기여**한다.
    발당 1라운드로 합류시키면 문턱이 실제보다 일찍 당겨져 게이지가 빨리 찬다.

    무기 에너지를 0으로 둬 이 축만 본다: 문턱은 무기 샷 4발(누적 4라운드)에서
    넘어야 한다. 스킬 타격이 라운드를 내면 12.5초에 이미 넘어 2.5초로 갈린다.
    """
    stats = {"u": _weapon(0.0)}
    shots = {"u": [(11.0, False), (12.0, False), (13.0, False), (14.0, False)]}
    hits = {"u": [(11.5, 1), (12.5, 1), (13.5, 1)]}
    fills = [{"every_ally_rounds": 4.0, "fraction": 1.0}]
    assert fill_times(shots, [10.0], weapon_stats=stats, fight_duration=100.0,
                      bonus_fills=fills,
                      skill_hits_by_slug=hits) == {1: pytest.approx(4.0)}


def test_a_skill_hit_from_a_unit_with_no_gauge_data_charges_nothing():
    """스킬 타격도 무기 타격과 **같은 관용**을 받는다 - 게이지값이 없는 프로필의
    타격은 0으로 센다. 실제 유닛은 값이 없으면 `load_roster`가 제외하므로 여기
    오지 않지만, 스킬 타격은 `damage_log`에서 유도되는 새 입력 경로라 그 관용이
    이쪽에도 있다는 것을 못박는다. `per_hit`에 없는 슬러그를 KeyError로 죽는
    구현이 여기서 걸린다.
    """
    stats = {"u": {"weapon": "AR"}, "other": _weapon(1.0)}
    assert fill_times({"u": [], "other": [(12.0, False)]}, [10.0],
                      weapon_stats=stats, fight_duration=100.0,
                      skill_hits_by_slug={"u": [(11.0, 99)]}) == {1: math.inf}


# --- 자기 풀차지 트리거 채움원 (bonus_fills) --------------------------------
# 두 번째 트리거 종류: 「자신이 풀차지로 공격할 때마다 아군 전체 게이지 X%」
# (헬름 애장품 Frontline Command 14.31%, 매치스 맥스웰 Output Switching
# Sequence 7.15%). 아군 소모탄 문턱과 같은 개념 - 어떤 트리거에 게이지의 X%를
# 얹는다 - 이라 같은 `bonus_fills` 목록에 산다.


def test_own_full_charge_grants_a_flat_squad_fill_once():
    """「풀차지마다 아군 전체 게이지 X%」는 팀 게이지에 **한 번** 들어간다.

    게이지는 스쿼드 하나의 값이므로 「Affects all allies」가 5배를 뜻하지 않는다.
    5배로 세면 헬름 한 명이 풀차지 두 발로 게이지를 채워, 실측(풀차지 3발로
    완료)과 정면으로 어긋난다.
    """
    stats = {"a": _weapon(50_000, charge_damage_percent=100.0),
             "b": _weapon(50_000, charge_damage_percent=100.0)}
    # a가 풀차지 4발. 무기만이면 200,000이고, 발마다 +15%(75,000)면 4발째에
    # 정확히 500,000이 된다.
    got = fill_times(
        {"a": [(11.0, False), (12.0, False), (13.0, False), (14.0, False)],
         "b": []},
        [10.0], weapon_stats=stats, fight_duration=60.0,
        bonus_fills=[{"every_own_full_charge": "a", "fraction": 0.15}])
    assert got == {1: pytest.approx(4.0)}
    # 5배로 세는 구현은 2발째(2 x 50,000 + 2 x 375,000)에 이미 넘어 2.0이 된다.


def test_only_the_units_own_full_charge_shots_trigger_the_fill():
    """원문이 「Full Charge attack」이고 시전자는 그 유닛이다 - 톡톡이(부분
    차지)도, 그 유닛의 스킬이 만든 타격도, **다른 좌석의** 풀차지도 트리거가
    아니다.

    무기 에너지를 무시할 만큼 작게 둬 이 축만 본다. 트리거를 넓게 잡는 세 가지
    잘못된 구현이 각각 여기서 걸린다: 톡톡이에도 얹으면 a의 2발로, 슬러그를
    안 보면 b의 2발로, 스킬 타격에도 얹으면 a의 2행으로 각각 0.6 x 2 = 1.2배가
    쌓여 표에 실린다.
    """
    stats = {"a": _weapon(1.0), "b": _weapon(1.0)}
    shots = {"a": [(11.0, True), (12.0, True)], "b": [(13.0, False), (14.0, False)]}
    hits = {"a": [(15.0, 1), (16.0, 1)]}
    assert fill_times(shots, [10.0], weapon_stats=stats, fight_duration=60.0,
                      skill_hits_by_slug=hits,
                      bonus_fills=[{"every_own_full_charge": "a", "fraction": 0.6}]
                      ) == {1: math.inf}


def test_own_full_charge_fill_is_not_scaled_by_the_fill_speed_multiplier():
    """아군 소모탄 문턱 점프와 **같은 이유로** 배율이 안 걸린다 - 곱해지는 항이
    아니라 별개로 더해지는 항이고, 스킬이 주는 플랫 충전에 「버스트 게이지 충전
    속도」가 걸리는지는 미측정이다. 두 종류가 다르게 굴면 그 자체가 설명 못 할
    불일치다.

    배율을 얹는 구현은 3배가 걸려 첫 발에서 채워 1.0초가 된다.
    """
    stats = {"a": _weapon(0.0)}
    shots = {"a": [(11.0, False), (12.0, False), (13.0, False)]}
    fills = [{"every_own_full_charge": "a", "fraction": 0.34}]
    assert fill_times(shots, [10.0], weapon_stats=stats, fight_duration=60.0,
                      bonus_fills=fills,
                      speed_multiplier_at=lambda slug, time: 3.0) == {1: pytest.approx(3.0)}


def test_the_two_trigger_kinds_coexist_in_one_list():
    """한 덱에 두 종류가 같이 앉을 수 있다(인어공주 + 헬름 애장품). 종류를
    구분하지 않고 `every_ally_rounds`를 모든 원소에서 읽는 구현은 KeyError로
    죽고, 반대로 새 종류만 읽는 구현은 문턱 점프를 잃는다.
    """
    stats = {"a": _weapon(0.0), "b": _weapon(0.0)}
    shots = {"a": [(11.0, False), (13.0, False)], "b": [(12.0, False), (14.0, False)]}
    rounds = {"a": [100.0, 100.0], "b": [100.0, 100.0]}
    fills = [
        {"every_ally_rounds": 200.0, "fraction": 0.3},    # 12.0과 14.0에 각 0.3
        {"every_own_full_charge": "a", "fraction": 0.2},  # 11.0과 13.0에 각 0.2
    ]
    # 11.0: 0.2 · 12.0: 0.5 · 13.0: 0.7 · 14.0: 1.0 -> 14.0에 정확히 가득 찬다.
    assert fill_times(shots, [10.0], weapon_stats=stats, fight_duration=60.0,
                      ammo_rounds_by_slug=rounds,
                      bonus_fills=fills) == {1: pytest.approx(4.0)}
