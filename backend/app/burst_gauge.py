"""버스트 게이지가 얼마나 차는가 - 상수와 산술이 사는 한 곳.

게이지는 **대미지가 아니라 타격 수**로 찬다. 코어 히트도, 크리티컬도, 적 DEF도
게이지를 안 바꾼다(Fienn 실측 2026-08-21, docs/measurements/burst-gauge-fill.md).
타격당 값은 무기군이 아니라 **유닛별**이고 같은 RL 안에서도 15배 벌어진다.

상수를 한곳에 두는 이유는 `paths.py`와 같다 - 흩어지면 같은 날 같은 방식으로 틀린다.
"""

# 게이지를 가득 채우는 데 필요한 에너지. 단독편성 여섯 유닛이 독립적으로 이 값을
# 준다(앨리스 5발 x 98,000 = 490,000 = 판독 156/160px; 블랑 250발 x 2,000 = 정확히
# 이 값에서 완료). UI 가로 160px가 이 값에 대응한다.
GAUGE_FULL = 500_000

# 채움 시간을 이 격자로 snap한다. 게이지가 사이클 길이를 바꾸고 사이클 길이가
# 재장전 위치를 바꿔 다시 게이지를 바꾸므로, 연속값이면 고정점이 진동할 수 있다.
# 실측 폭이 1초 가까이(덱3 2.55~3.5초)라 이 해상도로 잃는 것이 없다.
GAUGE_QUANTUM_SEC = 0.05


def energy_per_hit(weapon_stats, *, full_charge):
    """이 무기의 타격 하나가 넣는 게이지 에너지.

    산탄은 펠릿이 개별로 세어진다. 풀차지 샷만 차지 배율을 받는다 - 부분 차지
    (톡톡이)는 차지 비율과 무관하게 기본값이고, 그것이 헬름을 113%와 106%로 쏜 두
    발이 합쳐 정확히 기본값 두 개였던 판독이다.

    차지 배율에 `charge_damage_percent`를 쓰는 것은 우연이 아니다 - 원본 데이터의
    `full_charge_burst_energy`가 `full_charge_damage`와 **모든 유닛에서 값이 같다**.
    그 동일성은 `scripts/audit_burst_energy.py`가 지킨다.
    """
    energy = weapon_stats["burst_energy_pershot"] * weapon_stats.get("pellets_per_shot", 1)
    if not full_charge:
        return energy
    multiplier = weapon_stats.get("charge_damage_percent", 0.0) / 100
    return energy * multiplier if multiplier > 1 else energy


def quantize(seconds):
    """채움 시간을 고정점이 멈출 수 있는 격자로 내린다."""
    return round(seconds / GAUGE_QUANTUM_SEC) * GAUGE_QUANTUM_SEC
