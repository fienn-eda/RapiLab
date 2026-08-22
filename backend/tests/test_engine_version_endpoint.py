"""엔진 버전은 결과 캐시의 무효화 축이다. 클라이언트는 요청을 보내기 전에
캐시를 조회하므로 GET으로도 받을 수 있어야 하고, 응답에 실린 값과 같아야
한다 - 두 값이 어긋나면 캐시가 영원히 미스하거나 영원히 낡는다."""
from fastapi.testclient import TestClient

from app.api import app
from app.app_version import app_version
from app.engine_version import engine_version
from tests.test_api_recommend import BOSS, FEASIBLE, _nikke

client = TestClient(app)


def test_engine_version_endpoint_returns_the_running_version():
    response = client.get("/api/engine-version")
    assert response.status_code == 200
    assert response.json() == {
        "engine_version": engine_version(),
        "app_version": app_version(),
    }


def test_engine_version_endpoint_also_reports_the_release():
    """유저가 「검은 화면이 났다」고 제보할 때 가장 값나가는 한 줄이 어느 릴리스냐다.
    화면이 그것을 진단에 적으려면 어딘가에서 받아야 하는데, 이미 마운트 시 도는
    이 왕복에 얹는 것이 새 엔드포인트를 만드는 것보다 싸다. 개발 실행에서는
    None이고(태그 없는 빌드), 그것도 참인 답이라 감추지 않는다."""
    response = client.get("/api/engine-version")
    assert response.status_code == 200
    assert "app_version" in response.json()
    assert response.json()["app_version"] == app_version()


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
