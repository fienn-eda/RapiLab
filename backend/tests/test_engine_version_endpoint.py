"""엔진 버전은 결과 캐시의 무효화 축이다. 클라이언트는 요청을 보내기 전에
캐시를 조회하므로 GET으로도 받을 수 있어야 하고, 응답에 실린 값과 같아야
한다 - 두 값이 어긋나면 캐시가 영원히 미스하거나 영원히 낡는다."""
from fastapi.testclient import TestClient

from app.api import app
from app.engine_version import engine_version
from tests.test_api_recommend import BOSS, FEASIBLE, _nikke

client = TestClient(app)


def test_engine_version_endpoint_returns_the_running_version():
    response = client.get("/api/engine-version")
    assert response.status_code == 200
    assert response.json() == {"engine_version": engine_version()}


def test_recommend_reports_the_same_version_as_the_endpoint():
    roster = [_nikke(slug) for slug in FEASIBLE]
    response = client.post("/api/recommend",
                           json={"roster": roster, "boss": BOSS, "top_n": 1})
    assert response.status_code == 200
    assert response.json()["engine_version"] == engine_version()


def test_recommend_raid_reports_the_same_version_as_the_endpoint():
    roster = [_nikke(slug) for slug in FEASIBLE]
    response = client.post("/api/recommend-raid",
                           json={"roster": roster, "boss": BOSS, "num_decks": 1})
    assert response.status_code == 200
    assert response.json()["engine_version"] == engine_version()
