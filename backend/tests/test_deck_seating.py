"""좌석 배치 축: "자신과 양 옆 아군 2명"을 대상으로 하는 불릿이 있는 덱은
누구를 옆에 앉히느냐가 총딜을 바꾼다.

이 축은 덱 리스트 순서와 다르다. 리스트 순서는 버스트 우선순위이고(티어별로
묶이고 `_buffer_seat_valid`가 그 위에 규칙을 건다), 게임에서 좌석과 버스트
순서는 독립이다. 그래서 좌석은 `adjacency`로 따로 들어간다.

탐색은 요청당 ~1200 시뮬을 돌아 배치마다 6번씩 재줄 수 없으므로 결정적
정책(최고 ATK 아군 2명)을 쓰고, 보고 단계만 6가지를 전수로 재서 진짜 최적을
고른다. 여기서 가장 중요한 성질은 **보고된 숫자가 재현 가능하다**는 것이다 -
결과에 실린 좌석대로 앉히면 정확히 그 숫자가 나와야 한다.
"""
from itertools import combinations

from app.deck_allocation import best_ordering_summary
from app.deck_search import (BossProfile, evaluate_deck,
                             evaluate_deck_best_seating, search_best_decks)
from app.models import UserNikkeState
from app.user_roster import load_roster

BOSS = BossProfile(enemy_def=0, fight_duration=60.0, element="Iron",
                   gauge_charge_time=2.4, core_hittable=False,
                   part_destructible=False, effective_range_band=None)

# (1,1,3) 덱. 루주 외 4명이 무기군도 역할도 서로 달라 어느 둘을 옆에 앉히느냐가
# 실제로 총딜을 가른다.
ROUGE_DECK = ["rouge", "arcana", "drake", "modernia", "maxwell"]
ALLIES = [slug for slug in ROUGE_DECK if slug != "rouge"]


def _specs(slugs):
    states = [
        UserNikkeState.model_validate({
            "character_slug": slug, "level": 200,
            "hp": 1_000_000.0, "atk": 60_000.0, "def_": 3_000.0,
            "skill_levels": {"skill1": 10, "skill2": 10, "burst": 10},
        })
        for slug in slugs
    ]
    specs, excluded = load_roster(states)
    assert not excluded, f"not usable: {excluded}"
    by_slug = {spec.slug: spec for spec in specs}
    return [by_slug[slug] for slug in slugs]


def test_explicit_seating_changes_the_total():
    # 좌석이 시뮬까지 닿는가. 닿지 않으면 두 배치가 같은 숫자를 낸다.
    deck = _specs(ROUGE_DECK)
    first = evaluate_deck(deck, BOSS, adjacency={"rouge": ["modernia", "maxwell"]})
    second = evaluate_deck(deck, BOSS, adjacency={"rouge": ["arcana", "drake"]})
    assert first["total_damage"] != second["total_damage"]


def _totals_for_every_pair(deck):
    return {pair: evaluate_deck(deck, BOSS, adjacency={"rouge": list(pair)})["total_damage"]
            for pair in combinations(ALLIES, 2)}


def test_best_seating_is_the_maximum_over_every_neighbor_pair():
    # 백로우 좌석(2번/4번)의 양 옆은 나머지 넷 중 어느 둘이든 될 수 있으므로
    # 후보는 정확히 C(4,2)=6이고, 전수라 근사가 아니다.
    deck = _specs(ROUGE_DECK)
    by_pair = _totals_for_every_pair(deck)
    assert len(by_pair) == 6

    best = evaluate_deck_best_seating(deck, BOSS)

    assert best["total_damage"] == max(by_pair.values())
    assert sorted(best["seating"]["rouge"]) == sorted(max(by_pair, key=by_pair.get))


def test_reported_seating_reproduces_the_reported_total():
    # 보고된 숫자는 플레이어가 그 좌석대로 앉히면 나오는 값이어야 한다 - 이게
    # 성립하지 않으면 최적화가 아니라 부풀리기다.
    deck = _specs(ROUGE_DECK)
    best = evaluate_deck_best_seating(deck, BOSS)

    replay = evaluate_deck(deck, BOSS, adjacency=best["seating"])

    assert replay["total_damage"] == best["total_damage"]


def _reordered(roster, slugs):
    by_slug = {unit.slug: unit for unit in roster}
    return [by_slug[slug] for slug in slugs]


def test_search_reports_the_best_seating_of_the_deck_it_returns():
    # 랭킹은 정책으로 싸게 돌지만, 보고되는 숫자는 최적 좌석의 것이어야 한다.
    roster = _specs(ROUGE_DECK)

    reported = search_best_decks(roster, BOSS, top_n=1)[0]

    ordered = _reordered(roster, reported["deck"])
    assert reported["seating"] == {"rouge": ["drake", "modernia"]}
    assert reported["total_damage"] == evaluate_deck_best_seating(ordered, BOSS)["total_damage"]


def test_fixed_deck_evaluation_reports_the_best_seating_too():
    # 고정 편성 평가(`best_ordering_summary`)도 같은 보고 경로다 - 여기만 정책에
    # 머무르면 같은 덱이 화면마다 다른 숫자를 낸다.
    roster = _specs(ROUGE_DECK)

    summary = best_ordering_summary(roster, BOSS)

    ordered = _reordered(roster, summary["deck"])
    assert summary["seating"] == {"rouge": ["drake", "modernia"]}
    assert summary["total_damage"] == evaluate_deck_best_seating(ordered, BOSS)["total_damage"]


# 루주가 유일한 Burst 1이라 이 로스터의 모든 덱이 좌석 재채점을 받는다 - 덱마다
# 최적 좌석이 버는 양이 달라, 랭킹 순서와 보고 순서가 갈릴 수 있는 배치다.
SEATED_ROSTER = ["rouge", "arcana", "grave", "brid-silent-track",
                 "drake", "modernia", "maxwell"]


def test_reported_decks_stay_ranked_after_the_seating_re_score():
    # 랭킹은 정책 값으로 매기고 보고는 최적 좌석 값으로 내므로, 다시 정렬하지
    # 않으면 목록이 내림차순이 아니게 된다 - 응답 계약이 깨진다.
    totals = [deck["total_damage"]
              for deck in search_best_decks(_specs(SEATED_ROSTER), BOSS, top_n=5)]

    assert totals == sorted(totals, reverse=True)


def test_a_deck_with_no_seated_buff_keeps_the_plain_result():
    # 좌석형 불릿이 없는 덱은 좌석을 고를 것도, 6배를 낼 것도 없다.
    deck = _specs(["little-mermaid", "arcana", "drake", "modernia", "maxwell"])

    best = evaluate_deck_best_seating(deck, BOSS)

    assert "seating" not in best
    assert best["total_damage"] == evaluate_deck(deck, BOSS)["total_damage"]
