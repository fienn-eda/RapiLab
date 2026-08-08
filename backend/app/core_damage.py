"""코어 히트 한 발이 몇 배를 때리는가 — 유닛별 상수.

게임 데이터의 `shot_detail.core_damage_rate`가 이 값이고, 같은 `shot_detail`의
원문이 뜻을 적어 준다: "Deals {core_damage_rate}% damage when attacking core."
만분율이라 20000은 200% = 2.0배다. 엔진의 major modifier는 가산 버킷이라
`1 + 1.0 = 2.0`이 되므로 더할 값은 `rate/10000 - 1`이다.

**무기 클래스에서 유도할 수 없다.** SMG 7유닛이 3(20000)/4(25000)로 갈린다 —
나유타·볼륨·리타는 2.0배, 아래 넷은 2.5배다. `accuracy.WEAPON_SPREAD_DIAMETER`가
클래스 내 분산 0이라 클래스별 표로 끝나는 것과 갈리는 지점이다.

**수집 데이터를 타고 오지 못하는 이유:** 이 값이 있는 곳은 ShiftyPad raw뿐인데
(`data/shiftypad/raw/*.json`), 그 파일은 rid로 키가 잡혀 있고 슬러그 매핑은
데이터가 아니라 사람이 준다. 로더가 읽는 dotgg 파일에는 필드 자체가 없고,
인코딩 101슬러그 중 83개가 무기를 dotgg에서 읽는다 — 아래 다섯도 전부 그쪽이다.

그래서 표는 손으로 적고, 낡는 것은 `scripts/audit_core_damage_rate.py`가
수집 데이터와 대조해 막는다.
"""

# 200% = 2.0배. 오늘 수집된 83유닛 중 79유닛이 이 값이다.
DEFAULT_CORE_DAMAGE_RATE = 20000

# 250%인 유닛들. 미란다 애장품 빌드는 base의 무기 파일을 읽으므로 같이 오른다.
CORE_DAMAGE_RATE = {
    "miranda": 25000,
    "miranda-signature": 25000,
    "quency-escape-queen": 25000,
    "little-mermaid": 25000,
    "chisato-nishikigi": 25000,
}


def core_hit_bonus_for(slug):
    """이 유닛의 코어 히트가 major modifier에 더하는 값."""
    return CORE_DAMAGE_RATE.get(slug, DEFAULT_CORE_DAMAGE_RATE) / 10000 - 1
