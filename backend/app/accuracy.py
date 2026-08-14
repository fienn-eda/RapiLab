"""탄착군(bullet spread)의 크기와, 그로부터 나오는 코어 히트 확률.

명중률 스탯은 탄착군의 지름을 좁힌다. 무기별로 따로 측정된 회귀식 셋
(SG y=-2.18x+240 · AR y=-0.69x+76 · SMG y=-1x+110 — 아카라이브 니케 채널
96243965)은 전부 명중 110%에서 지름 0에 닿으므로 같은 한 식이다:

    지름 = 기본지름 x (1 - 명중/1.10)

코어에 드는 비율은 탄착이 그 원 안에 균등 분포한다고 보고 면적비로 낸다.
글이 준 실측 네 점은 그 가정에서 코어 지름 51.1px +- 6.1%로 모이고(중앙
집중 분포로 풀면 37.9~59.0px로 흩어진다), 그 51.1px는 이 프로젝트가 따로
세운 50px 가정과 2% 차이다.

지름을 정하는 축은 둘이다. 명중률이 하나고, **탄창 안에서의 발 위치**가
다른 하나다 — MG는 탄창을 250px로 열어 발당 7px씩 조여 10px에 수렴한다
(`SPREAD_CONVERGENCE`). 두 축은 곱해진다.
"""

# 탄착군이 한 점으로 수렴하는 명중률. 세 무기의 측정된 회귀식이 모두 여기서
# 만나므로 무기별 상수가 아니라 게임 전체의 상수다.
ZERO_SPREAD_HIT_RATE = 1.10

# 탄창이 다 나갔을 때 각 무기가 명중 0%에서 그리는 탄착군의 지름(px).
#
# `data/shiftypad/raw/*.json`의 `shot_detail.end_accuracy_circle_scale`에서
# 온 값이고, 수집된 77유닛에서 클래스 내 분산이 0이다. 손으로 유지되는 표라
# `scripts/audit_weapon_accuracy_scales.py`가 데이터와 대조한다.
#
# 다섯 클래스는 start와 end가 같아 이 값이 탄창 내내 유지된다. MG만 다르고,
# 그 차이는 `SPREAD_CONVERGENCE`가 든다.
WEAPON_SPREAD_DIAMETER = {
    "AR": 75.0,
    "SG": 250.0,
    "SMG": 110.0,
    "MG": 10.0,
    "SR": 10.0,
    "RL": 10.0,
}

# 탄창 안에서 조준이 조여지는 무기: {무기: (첫 발의 지름, 발당 감소)}.
#
# 같은 `shot_detail`의 start_accuracy_circle_scale / accuracy_change_pershot이고,
# MG는 250에서 시작해 발당 7씩 좁아져 34.3발 만에 수렴값 10에 닿는다. 수집
# 데이터에서 start != end인 클래스는 MG뿐이며 나머지 다섯은 발당 변화도 0이라
# 이 표에 오르지 않는다 — 그래서 여기 없는 무기는 탄창 위치를 물어도 같은
# 지름을 낸다.
#
# 이것이 딜에서 중요한 이유: 코어(애니힐리오 48.89px)보다 넓은 구간이 탄창 앞
# 29발이고, 그 발들의 코어히트율은 0.038에서 시작한다. 수렴값만 보면 MG의
# 코어히트율은 어떤 명중률에서도 1.0이라 탄착군 항이 아예 작동하지 않는다.
SPREAD_CONVERGENCE = {
    "MG": (250.0, 7.0),
}


def spread_diameter(weapon, hit_rate, magazine_index=None):
    """이 무기가 이 명중률에서 그리는 탄착군의 지름(px).

    `magazine_index`는 이 발이 탄창의 몇 번째인가다. 주지 않으면 수렴값을
    쓴다 — 탄창 위치를 모르는 호출자(변형 세그먼트, 프론트 미러)가 근거 없는
    넓은 지름을 받지 않게 하려는 중립값이다.

    명중이 `ZERO_SPREAD_HIT_RATE`를 넘어도 지름은 음수가 되지 않는다 —
    도로시: 세렌디피티가 두 버프를 겹쳐 실제로 넘는다. 명중이 음수면
    (마스트: 로맨틱 메이드의 Drunken) 반대로 지름이 커진다. 명중 계수는
    탄창 어느 지점의 지름에든 곱한다 — 명중이 수렴값만 움직이는지 곡선
    전체를 움직이는지 가르는 판독은 없다(미측정).

    모르는 무기는 KeyError. 조용히 넓거나 좁은 기본값을 주면 그 유닛의
    코어히트율이 근거 없이 정해진다.
    """
    base = WEAPON_SPREAD_DIAMETER[weapon]
    if magazine_index is not None:
        start, per_shot = SPREAD_CONVERGENCE.get(weapon, (base, 0.0))
        base = max(base, start - per_shot * magazine_index)
    return base * max(0.0, 1.0 - hit_rate / ZERO_SPREAD_HIT_RATE)


def core_hit_rate(weapon, hit_rate, core_diameter, magazine_index=None):
    """조준점이 코어 중심에 있을 때 코어에 드는 발의 비율.

    탄착군 전체가 코어 안에 들어가면 전부 맞고, 그렇지 않으면 두 원의
    면적비다.
    """
    diameter = spread_diameter(weapon, hit_rate, magazine_index)
    if diameter <= core_diameter:
        return 1.0
    return (core_diameter / diameter) ** 2
