"""단독편성 실측이 그대로 단언이 된다 - docs/measurements/burst-gauge-fill.md.

앨리스 5발 / 에이드 7발 / 드레이크 10발 / 블랑 250발 / 리타 500발 / 크라운 1000발이
각각 게이지를 채운다. 여섯이 독립적으로 같은 총량을 준다.
"""
import pytest

from app.burst_gauge import (GAUGE_FULL, GAUGE_QUANTUM_SEC, energy_per_hit,
                             fill_times, quantize)


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


def test_a_cycle_that_never_fills_is_left_out_of_the_table():
    """전투가 끝날 때까지 못 채운 사이클은 표에 안 싣는다. 무한대를 스케줄러에
    넘기면 하한 계산이 통째로 뒤집힌다."""
    stats = {"u": _weapon(1.0)}
    assert fill_times({"u": [(11.0, False)]}, [10.0],
                      weapon_stats=stats, fight_duration=100.0) == {}


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


def test_a_weapon_with_no_gauge_data_charges_nothing():
    """실제 유닛은 값이 없으면 `load_roster`가 아예 제외하므로 여기 오지 않는다.
    이 관용이 받는 것은 손으로 만든 무기 프로필뿐이고, 그런 좌석은 게이지에
    기여하지 않는다."""
    assert fill_times({"u": [(11.0, False)]}, [10.0],
                      weapon_stats={"u": {"weapon": "AR"}},
                      fight_duration=100.0) == {}
