"""단독편성 실측이 그대로 단언이 된다 - docs/measurements/burst-gauge-fill.md.

앨리스 5발 / 에이드 7발 / 드레이크 10발 / 블랑 250발 / 리타 500발 / 크라운 1000발이
각각 게이지를 채운다. 여섯이 독립적으로 같은 총량을 준다.
"""
import pytest

from app.burst_gauge import GAUGE_FULL, energy_per_hit, quantize


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
    있다. 격자로 유한 상태를 만든다."""
    assert quantize(3.1799) == pytest.approx(3.20)
    assert quantize(2.4) == pytest.approx(2.40)
