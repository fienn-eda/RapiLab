"""POST /api/evaluate-decks - 탐색 없는 평가 전용 경로. 실제 시뮬을 돌린다
(스텁 없음): 이 엔드포인트가 추천 경로와 같은 프리미티브를 쓴다는 주장은
스텁으로는 검증되지 않는다."""
import pytest
from fastapi.testclient import TestClient

from app.api import app
from app.engine_version import engine_version
from tests.test_api_recommend import _nikke

client = TestClient(app)

# B1/B2/B3를 모두 덮는 실제 로더블 유닛 5명. 확인:
#   python -c "from app.supported_units import supported_units as s; \
#              print(sorted((u['burst_tier'], u['slug']) for u in s()))"
DECK = ["liter", "blanc", "crown", "modernia", "privaty"]
ROSTER = [_nikke(s) for s in DECK]


def _request(decks, roster=None):
    return {"roster": roster if roster is not None else ROSTER, "decks": decks}


def test_evaluates_one_deck_and_reports_the_engine_version():
    response = client.post("/api/evaluate-decks",
                           json=_request([{"units": DECK, "boss": {}}]))

    assert response.status_code == 200
    body = response.json()
    assert len(body["decks"]) == 1
    deck = body["decks"][0]
    assert sorted(deck["deck"]) == sorted(DECK)
    assert deck["total_damage"] > 0
    # _summarize의 계약: 세 갈래가 총딜을 남김없이 덮는다. 시뮬레이터가 total과
    # 갈래별 합을 서로 다른 덧셈 순서로 누적하므로 부동소수 오차만큼은 approx로
    # 눈감아준다 - 같은 계약을 검증하는 test_api_recommend.py도 approx를 쓴다.
    assert (deck["burst_damage"] + deck["normal_attack_damage"]
            + deck["skill_damage"]) == pytest.approx(deck["total_damage"])
    assert body["combined_total_damage"] == deck["total_damage"]
    assert body["excluded_slugs"] == []
    assert body["engine_version"] == engine_version()


def test_matches_the_draft_baseline_for_the_same_deck_and_boss():
    """같은 편성·같은 보스라면 평가 경로와 추천 경로의 baseline은 같은
    프리미티브를 통과하므로 정확히 같은 값이어야 한다. 두 경로가 갈라지면
    이 테스트가 먼저 터진다."""
    boss = {"element": "Iron"}
    evaluated = client.post(
        "/api/evaluate-decks",
        json=_request([{"units": DECK, "boss": boss}])).json()
    drafted = client.post("/api/recommend-raid", json={
        "roster": ROSTER, "boss": boss, "num_decks": 1,
        "draft": [{"units": [{"slug": s} for s in DECK]}],
    }).json()

    assert evaluated["combined_total_damage"] == drafted["baseline_total_damage"]


def test_boss_element_changes_the_result():
    iron = client.post("/api/evaluate-decks",
                       json=_request([{"units": DECK, "boss": {"element": "Iron"}}])).json()
    none = client.post("/api/evaluate-decks",
                       json=_request([{"units": DECK, "boss": {}}])).json()

    assert iron["combined_total_damage"] != none["combined_total_damage"]


def test_rejects_an_empty_deck_list():
    response = client.post("/api/evaluate-decks", json=_request([]))
    assert response.status_code == 422


def test_rejects_a_deck_that_is_not_five_units():
    response = client.post("/api/evaluate-decks",
                           json=_request([{"units": DECK[:4], "boss": {}}]))
    assert response.status_code == 422
    assert "1번" in response.json()["detail"]


def test_rejects_a_slug_used_in_two_decks():
    extra = ["rouge", "volume", "mint", "grave", "noir"]
    roster = [_nikke(s) for s in DECK + extra]
    second = ["liter", "rouge", "volume", "mint", "grave"]
    response = client.post("/api/evaluate-decks", json=_request(
        [{"units": DECK, "boss": {}}, {"units": second, "boss": {}}], roster=roster))

    assert response.status_code == 422
    assert "liter" in response.json()["detail"]


def test_rejects_a_slug_the_engine_cannot_use():
    response = client.post("/api/evaluate-decks", json=_request(
        [{"units": ["not-a-nikke"] + DECK[1:], "boss": {}}]))

    assert response.status_code == 422
    assert "not-a-nikke" in response.json()["detail"]


def test_rejects_a_deck_with_no_feasible_burst_ordering():
    """B1이 없는 5인은 legal한 배치가 없다(ALLOWED_SHAPES 어디에도 안 맞음)."""
    b3_only = ["modernia", "privaty", "noir", "drake", "helm"]
    roster = [_nikke(s) for s in b3_only]
    response = client.post("/api/evaluate-decks",
                           json=_request([{"units": b3_only, "boss": {}}], roster=roster))

    assert response.status_code == 422
    assert "1번" in response.json()["detail"]


def test_seats_a_dual_tier_character_in_the_tier_the_deck_needs():
    """라피: 레드후드는 B3 좌석과 Combat Assist의 B1 좌석 둘 다로 모델링된다
    (MODE_VARIANTS). 나머지 넷이 B2 하나 + B3 셋이면 성립하는 대형은 그녀가
    B1로 앉는 1·1·3 하나뿐이라, 좌석의 모드를 엔진이 고르지 못하면 유저가
    인게임에서 실제로 굴리는 편성이 422로 거절된다."""
    deck = ["rapi-red-hood", "nayuta", "helm", "ludmilla-winter-owner",
            "quency-escape-queen"]
    roster = [_nikke(s) for s in deck]
    response = client.post("/api/evaluate-decks",
                           json=_request([{"units": deck, "boss": {}}], roster=roster))

    assert response.status_code == 200, response.json()
    assert "rapi-red-hood-b1" in response.json()["decks"][0]["deck"]


def test_infeasible_message_does_not_claim_a_missing_tier_it_has():
    """1×B1·3×B2·1×B3처럼 세 티어가 다 있어도 ALLOWED_SHAPES 밖이면 여전히
    불가능한 조합이다 - 메시지가 "티어가 없다"고 잘못 말하면 안 되고, 실제
    허용 대형을 구체적으로 말해줘야 한다."""
    not_a_shape = ["liter", "blanc", "crown", "grave", "modernia"]
    roster = [_nikke(s) for s in not_a_shape]
    response = client.post("/api/evaluate-decks",
                           json=_request([{"units": not_a_shape, "boss": {}}], roster=roster))

    assert response.status_code == 422
    detail = response.json()["detail"]
    assert "1번" in detail
    # 이 덱은 B1/B2/B3를 모두 가졌으므로 "모두 필요하다"는 말은 거짓이다.
    assert "모두 필요" not in detail
    # 실제 허용 대형(ALLOWED_SHAPES)을 구체적으로 알려줘야 actionable하다.
    assert "1·2·2" in detail
