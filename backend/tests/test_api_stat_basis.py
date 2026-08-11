"""stat_basis: 어느 스탯 벌로 딜을 잴지 요청이 정한다.

솔로레이드는 전원 레벨 400 보정, 유니온레이드는 레벨 보정 자체가 없어 계정
싱크로 레벨로 싸운다. 엔드포인트로 가르지 않는 이유는 `/api/recommend-raid`가
이름과 달리 솔로 탭의 5덱 배분이기 때문이다.
"""
from fastapi.testclient import TestClient

from app.api import app

client = TestClient(app)


def _unit(slug, **extra):
    """A minimal valid UserNikkeState body for `slug`, level-400 stats only."""
    state = {
        "character_slug": slug, "level": 400,
        "hp": 1_000_000, "atk": 100_000, "def_": 0,
        "skill_levels": {"skill1": 10, "skill2": 10, "burst": 10},
        "overload_options": [],
    }
    state.update(extra)
    return state


def test_actual_basis_is_rejected_when_a_unit_has_no_real_level_stats():
    """400 값으로 폴백하면 유닛 간 상대 ATK가 최대 24% 뒤틀린다 - 레벨은 base
    커브에만 들어가고 장비·큐브·소장품은 레벨과 무관하게 더해지기 때문이다.
    그래서 근사하지 않고 거절한다."""
    response = client.post("/api/evaluate-decks", json={
        "roster": [_unit("drake")],
        "decks": [],
        "stat_basis": "actual",
    })

    assert response.status_code == 422
    assert "drake" in response.json()["detail"]


def test_the_rejection_names_only_the_units_that_are_missing():
    response = client.post("/api/evaluate-decks", json={
        "roster": [_unit("drake", actual_atk=300_000, actual_hp=3_000_000),
                   _unit("blanc")],
        "decks": [],
        "stat_basis": "actual",
    })

    detail = response.json()["detail"]
    assert "blanc" in detail and "drake" not in detail


def test_the_default_basis_does_not_require_real_level_stats():
    """`actual`이 없는 로스터는 지금 되는 곳에서 계속 돼야 한다 - 이 필드의
    기본값이 곧 현행 동작이다."""
    response = client.post("/api/evaluate-decks", json={
        "roster": [_unit("drake")],
        "decks": [],
    })

    # 덱이 비어 어차피 422지만, 그 이유가 스탯이 아니라 덱이어야 한다.
    assert "실제 레벨" not in response.json()["detail"]
