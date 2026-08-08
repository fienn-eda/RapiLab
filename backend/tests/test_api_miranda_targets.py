"""POST /api/miranda-targets - 미란다 계산기의 surface."""
from fastapi.testclient import TestClient

from app.api import app

client = TestClient(app)

MAXED = {"skill1": 10, "skill2": 10, "burst": 10}
DECK = ["miranda-signature", "crown", "ada-wong", "cinderella", "isabel"]


def a_unit(slug, atk=100_000):
    return {"character_slug": slug, "level": 400, "hp": 500_000, "atk": atk,
            "def_": 10_000, "skill_levels": MAXED, "overload_options": []}


def post(units, roster=None):
    roster = roster if roster is not None else [a_unit(slug) for slug in DECK]
    return client.post("/api/miranda-targets", json={"roster": roster, "units": units})


def test_a_full_deck_reports_cycles_seats_and_thresholds():
    response = post(DECK)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["miranda_slug"] == "miranda-signature"
    assert body["has_favorite_item"] is True
    assert len(body["seats"]) == 5
    assert body["cycles"]
    assert [c["index"] for c in body["cycles"]] == list(range(1, len(body["cycles"]) + 1))
    assert {t["slug"] for t in body["overload_thresholds"]} == set(DECK) - {"miranda-signature"}
    assert body["overload_atk_cap_percent"] > 0
    # 고정한 보스 전제는 언제나 화면에 닿아야 한다.
    assert any("무속성" in note for note in body["notes"])


def test_a_deck_that_is_not_five_units_is_rejected():
    response = post(DECK[:4])
    assert response.status_code == 422
    assert "5" in response.json()["detail"]


def test_a_deck_without_miranda_is_rejected():
    deck = ["liter", "crown", "ada-wong", "cinderella", "isabel"]
    response = post(deck, roster=[a_unit(slug) for slug in deck])
    assert response.status_code == 422
    assert "미란다" in response.json()["detail"]


def test_a_slug_the_engine_cannot_use_is_rejected():
    deck = ["miranda-signature", "crown", "ada-wong", "cinderella", "not-a-nikke"]
    roster = [a_unit(slug) for slug in DECK[:4]] + [a_unit("not-a-nikke")]
    response = post(deck, roster=roster)
    assert response.status_code == 422
    assert "not-a-nikke" in response.json()["detail"]


def test_a_deck_with_a_repeated_slug_is_rejected():
    deck = ["miranda-signature", "crown", "ada-wong", "cinderella", "cinderella"]
    response = post(deck)
    assert response.status_code == 422
    assert "cinderella" in response.json()["detail"]


def test_a_deck_with_no_feasible_burst_order_is_rejected():
    # 미란다(B1) + B3 넷 - 1·1·3 / 1·2·2 / 2·1·2 중 어느 모양도 아니다.
    deck = ["miranda-signature", "ada-wong", "cinderella", "isabel", "julia"]
    response = post(deck, roster=[a_unit(slug) for slug in deck])
    assert response.status_code == 422
    assert "성립하는 버스트 순서가 없어요" in response.json()["detail"]
