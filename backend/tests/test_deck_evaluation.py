"""고정 편성 평가: 탐색도 배분도 없이, 덱마다 자기 보스로 채점하고 합산한다.
덱끼리 상호작용이 없다는 것이 합산의 근거이므로, 덱별 보스가 서로에게 새지
않는다는 것이 여기서 가장 중요한 성질이다. 시뮬은 스텁 - 실제 시뮬은 API
엔드투엔드 테스트에서 돈다."""
import pytest

import app.deck_allocation as da
import app.deck_search as ds
from app.deck_evaluation import InfeasibleDeck, evaluate_decks
from app.deck_search import BossProfile
from tests.test_deck_allocation import roster_of


def patch_boss_aware_scorer(monkeypatch, scorer):
    """`scorer(slugs, boss) -> float`. best_ordering_summary는 evaluate_deck을
    직접(da 바인딩) 그리고 _score_batch를 통해(ds 바인딩) 모두 부르므로 둘 다
    패치한다 - tests/test_deck_allocation.py의 patch_scorer와 같은 이유."""
    def fake_evaluate(ordered_deck, boss):
        return {"total_damage": scorer({u.slug for u in ordered_deck}, boss),
                "damage_log": []}

    monkeypatch.setattr(ds, "evaluate_deck", fake_evaluate)
    monkeypatch.setattr(da, "evaluate_deck", fake_evaluate)


def _deck(roster, *slugs):
    by_slug = {u.slug: u for u in roster}
    return [by_slug[s] for s in slugs]


def _two_decks():
    roster = roster_of({
        "t1a": 1, "t2a": 2, "t3a1": 3, "t3a2": 3, "t3a3": 3,
        "t1b": 1, "t2b": 2, "t3b1": 3, "t3b2": 3, "t3b3": 3,
    })
    return roster, [_deck(roster, "t1a", "t2a", "t3a1", "t3a2", "t3a3"),
                    _deck(roster, "t1b", "t2b", "t3b1", "t3b2", "t3b3")]


def test_combined_total_is_the_sum_of_the_decks(monkeypatch):
    patch_boss_aware_scorer(monkeypatch, lambda slugs, boss: 10.0)
    _, decks = _two_decks()

    out = evaluate_decks(decks, [BossProfile(), BossProfile()])

    assert [d["total_damage"] for d in out["decks"]] == [10.0, 10.0]
    assert out["combined_total_damage"] == 20.0


def test_each_deck_is_scored_against_its_own_boss(monkeypatch):
    # 1번 덱만 Iron 보스, 2번 덱은 Water. 스코어러가 보스 속성으로 갈리므로
    # 보스가 덱을 가로질러 새면 두 값이 같아진다.
    patch_boss_aware_scorer(
        monkeypatch, lambda slugs, boss: 100.0 if boss.element == "Iron" else 1.0)
    _, decks = _two_decks()

    out = evaluate_decks(decks, [BossProfile(element="Iron"),
                                 BossProfile(element="Water")])

    assert [d["total_damage"] for d in out["decks"]] == [100.0, 1.0]
    assert out["combined_total_damage"] == 101.0


def test_returned_deck_is_the_best_intra_tier_ordering(monkeypatch):
    # 같은 5인이라도 t3a1이 t3a2보다 앞설 때만 높은 점수가 나오게 만든다.
    def score(slugs, boss):
        return 10.0

    def fake_evaluate(ordered_deck, boss):
        order = [u.slug for u in ordered_deck]
        bonus = 5.0 if order.index("t3a1") < order.index("t3a2") else 0.0
        return {"total_damage": 10.0 + bonus, "damage_log": []}

    monkeypatch.setattr(ds, "evaluate_deck", fake_evaluate)
    monkeypatch.setattr(da, "evaluate_deck", fake_evaluate)
    roster, decks = _two_decks()

    out = evaluate_decks(decks[:1], [BossProfile()])

    deck = out["decks"][0]["deck"]
    assert deck.index("t3a1") < deck.index("t3a2")
    assert out["decks"][0]["total_damage"] == 15.0


def test_infeasible_deck_names_its_index(monkeypatch):
    patch_boss_aware_scorer(monkeypatch, lambda slugs, boss: 10.0)
    roster, decks = _two_decks()
    # modernia와 velvet은 버퍼 좌석(_BUFFER_SEAT_SLUGS)이라 같은 티어에 같이
    # 있으면 반드시 서로보다 먼저 앉는 쪽이 생겨 legal한 배치가 하나도 없다
    # (_buffer_seat_valid) - 둘을 같은 티어(3)로 채워 그 상태를 만든다.
    infeasible = roster_of({"t1a": 1, "t2a": 2, "t2b": 2, "modernia": 3, "velvet": 3})

    with pytest.raises(InfeasibleDeck) as excinfo:
        evaluate_decks([decks[0], infeasible],
                       [BossProfile(), BossProfile()])

    assert excinfo.value.deck_index == 1


def test_infeasible_shape_names_its_index(monkeypatch):
    # 5명 전원 B3면 (n1, n2, n3)가 ALLOWED_SHAPES 어디에도 안 들어 legal한
    # 배치가 없다 - _buffer_seat_valid와는 다른 규칙(shape 자체가 불법).
    patch_boss_aware_scorer(monkeypatch, lambda slugs, boss: 10.0)
    roster, decks = _two_decks()
    all_tier3 = roster_of({"x1": 3, "x2": 3, "x3": 3, "x4": 3, "x5": 3})

    with pytest.raises(InfeasibleDeck) as excinfo:
        evaluate_decks([decks[0], all_tier3],
                       [BossProfile(), BossProfile()])

    assert excinfo.value.deck_index == 1


def test_mode_variant_seat_is_scored_at_its_best_reading(monkeypatch):
    # 한 좌석이 두 후보(-mg / -snipe)를 갖는다. -snipe가 더 세므로 그쪽이 채택돼야
    # 한다 - baseline_total_damage가 쓰는 것과 같은 기준.
    patch_boss_aware_scorer(
        monkeypatch, lambda slugs, boss: 100.0 if "v-snipe" in slugs else 10.0)
    roster = roster_of({"t1a": 1, "t2a": 2, "t3a1": 3, "t3a2": 3,
                        "v-mg": 3, "v-snipe": 3})
    by_slug = {u.slug: u for u in roster}
    deck = [by_slug[s] for s in ("t1a", "t2a", "t3a1", "t3a2", "v-mg")]
    alternatives = {"v-mg": (by_slug["v-mg"], by_slug["v-snipe"])}

    out = evaluate_decks([deck], [BossProfile()], alternatives=alternatives)

    assert out["decks"][0]["total_damage"] == 100.0
    assert "v-snipe" in out["decks"][0]["deck"]


def test_deck_and_boss_counts_must_match():
    with pytest.raises(ValueError):
        evaluate_decks([[]], [BossProfile(), BossProfile()])
