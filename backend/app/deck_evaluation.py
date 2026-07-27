"""유저가 이미 짜놓은 고정 편성 N개를, 덱마다 자기 보스로 채점한다.

`deck_allocation`과의 차이는 방향이다. 저기는 로스터에서 덱을 만들어내고,
여기는 만들어진 덱을 채점만 한다 - 탐색도, 배분도, 스왑도 없다. 그래서
덱끼리 상호작용이 없고, 합계는 덱별 점수의 단순 합이며, 덱마다 보스가 달라도
그 성질이 그대로 성립한다(유니온 레이드가 그 경우다).

채점은 `deck_allocation.best_ordering_summary`에 위임한다. 딜을 계산하는 두
번째 경로를 만들지 않는 것이 이 모듈의 설계 제약이다 - 엔진을 고쳤을 때 평가
결과가 추천 결과와 어긋나면 유저가 두 수치 중 어느 쪽도 믿을 수 없게 된다.
"""
from app.deck_allocation import _seed_choices, best_ordering_summary
from app.deck_search import _intra_tier_orderings


class InfeasibleDeck(ValueError):
    """이 5인으로는 legal한 버스트 티어 배치가 하나도 없다. `deck_index`는
    호출자가 유저에게 몇 번째 덱인지 말해줄 수 있게 들고 있는 값이다."""

    def __init__(self, deck_index: int):
        super().__init__(f"deck {deck_index} has no feasible burst-tier ordering")
        self.deck_index = deck_index


def evaluate_decks(decks, bosses, alternatives=None):
    """`decks[i]`를 `bosses[i]`로 채점한 요약들과 그 합계.

    `alternatives`는 엔진이 여러 모드로 모델링하는 캐릭터(MODE_VARIANTS)의
    좌석을 위한 것이다. 어떤 모드로 도는지는 유저가 고르는 것이 아니므로
    모든 해석을 채점해 최선을 채택한다 - `recommend_from_draft`의
    `baseline_total_damage`가 쓰는 것과 같은 기준이라, 두 화면의 수치가 서로
    비교 가능하게 남는다.
    """
    if len(decks) != len(bosses):
        raise ValueError(f"got {len(decks)} decks but {len(bosses)} bosses")

    summaries = []
    for index, (deck, boss) in enumerate(zip(decks, bosses)):
        readings = _seed_choices(deck, alternatives)
        # 어떤 해석으로도 legal한 배치가 없을 때만 불가능한 덱이다. 좌석의
        # 모드는 티어를 바꿀 수 있으므로(VARIANT_BURST_TIERS) 해석마다 따로 본다.
        scored = [best_ordering_summary(reading, boss) for reading in readings
                  if next(_intra_tier_orderings(reading), None) is not None]
        if not scored:
            raise InfeasibleDeck(index)
        summaries.append(max(scored, key=lambda s: s["total_damage"]))

    return {"decks": summaries,
            "combined_total_damage": sum(s["total_damage"] for s in summaries)}
