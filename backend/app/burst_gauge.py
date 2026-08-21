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
#
# 0.05가 아니라 0.1인 것은 실측이다: 표본 400덱(cascade의 FIT_SAMPLE_DECKS)에서
# 0.05는 18덱이 `MAX_FULL_BURST_PASSES`(32) 안에 안 멈추고 0.1은 3덱이다.
# **더 굵을수록 안전한 것은 아니다** - 0.2와 0.25에서도 안 멈추는 덱이 남는다.
#
# 남는 3덱은 **주기 2의 극한 순환**이다(추적: 사이클 두 개의 값이 격자 한 칸씩
# 번갈아 뛴다). 진짜 고정점이 격자점 둘 사이에 있으면 양자화된 사상에는 고정점이
# 아예 없으므로, 격자를 바꾸는 것으로는 어느 덱이 그 경계에 앉는가만 바뀐다.
# 그 덱들은 기존 `FullBurstConvergenceWarning`이 잡는다.
GAUGE_QUANTUM_SEC = 0.1


def energy_per_hit(weapon_stats, *, full_charge):
    """이 무기의 타격 하나가 넣는 게이지 에너지.

    산탄은 펠릿이 개별로 세어진다. 풀차지 샷만 차지 배율을 받는다 - 부분 차지
    (톡톡이)는 차지 비율과 무관하게 기본값이고, 그것이 헬름을 113%와 106%로 쏜 두
    발이 합쳐 정확히 기본값 두 개였던 판독이다.

    차지 배율에 `charge_damage_percent`를 쓰는 것은 우연이 아니다 - 원본 데이터의
    `full_charge_burst_energy`가 `full_charge_damage`와 **차지 무기에서 값이 같다**.
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


def fill_times(shots_by_slug, full_burst_ends, *, weapon_stats, fight_duration):
    """풀 버스트가 끝난 뒤 게이지가 다시 가득 차기까지 걸리는 시간, 사이클마다.

    `shots_by_slug`는 `{슬러그: [(시각, 톡톡이 여부), ...]}`. 대미지 경로와
    직교한다 - 코어히트도 크리티컬도 ATK도 적 DEF도 여기 안 들어온다.

    **세는 단위는 샷 레코드 하나, 즉 방아쇠 하나다.** 실측이 정한 단위는 방아쇠가
    아니라 **타격**이고(measurements/burst-gauge-fill.md), 둘이 갈리는 자리가 둘
    있다. 산탄은 `energy_per_hit`이 `pellets_per_shot`을 곱해 맞춘다.
    **관통은 아직 안 맞춘다** - 「관통으로 n개 객체를 타격하면 게이지도 n배」가
    실측에 있지만 여기서는 방아쇠 하나가 곱해지지 않은 채 한 번 세어진다.
    보류인 이유: 엔진의 관통 2인스턴스는 `pierce_hits_body_behind_core`에
    게이트돼 있고 게이지를 잰 인카운터는 그 값이 거짓이라(코어도 못 맞히는
    환경) 실측 덱들에서 관통은 애초에 발동하지 않았다. 지금 배선하면 측정되지
    않은 상호작용 위에 짓는 것이다. `docs/engine-gaps.md` 참조.

    키는 `full_burst_ends`의 인덱스에 **+1**이다. 풀 버스트 k의 종료에서 잰
    채움이 지배하는 것은 사이클 k+1이기 때문이다 - `burst_cycle`의
    `gauge_ready = time + gauge[cycle_index]`에서 `time`이 직전 풀 버스트의
    종료다. 사이클 0(개전 -> 첫 버스트)은 표에 없고 시드가 답한다: 개전 게이지
    0에서의 채움은 이 모델의 범위 밖이다.

    게이지는 **창 밖에서만** 찬다(창 안에서도 찬다는 가설은 실측으로 기각됐다 -
    그러면 다섯 덱 전부가 창 종료 전에 가득 차서 덱2의 3.7초 판독을 설명 못 한다).
    초과분은 다음 사이클로 이월되지 않는다.

    전투가 끝날 때까지 못 채우는 사이클은 표에 안 싣는다 - 그 사이클은 어차피
    일어나지 않고, 무한대를 스케줄러에 넘기면 하한 계산이 통째로 뒤집힌다.
    `fight_duration` 검사는 그 약속을 이 함수가 **스스로** 지키게 한다: 오늘의
    발사 생성기는 종료 시각을 넘겨 쏘지 않으므로(실측 175,259발 중 0발) 검사가
    걸리는 일은 없지만, 그 성질은 이 함수의 것이 아니라 호출자의 것이다.
    """
    # 게이지값이 없는 무기 프로필은 아무것도 안 채운다. 실제 유닛은 값이 없으면
    # `load_roster`가 아예 제외하므로 여기 오지 않는다 - 이 관용이 받는 것은
    # 손으로 만든 무기 프로필(테스트·스텁)뿐이다.
    per_hit = {
        slug: (energy_per_hit(stats, full_charge=False),
               energy_per_hit(stats, full_charge=True))
        for slug, stats in weapon_stats.items()
        if stats.get("burst_energy_pershot")
    }
    merged = sorted(
        (time, slug, is_tap)
        for slug, shots in shots_by_slug.items()
        for time, is_tap in shots
    )
    out = {}
    for cycle_index, end in enumerate(full_burst_ends):
        gauge = 0.0
        for time, slug, is_tap in merged:
            if time < end:
                continue
            if time >= fight_duration:
                break
            base, charged = per_hit.get(slug, (0.0, 0.0))
            gauge += base if is_tap else charged
            if gauge >= GAUGE_FULL:
                out[cycle_index + 1] = quantize(time - end)
                break
    return out
