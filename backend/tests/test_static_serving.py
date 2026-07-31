"""빌드된 프론트가 있으면 API와 같은 origin에서 서빙된다.

앱에는 Vite 프록시가 없으므로 이것이 프론트가 `/api/*`에 닿는 유일한 방법이다
(프론트는 전부 상대경로를 쓴다 - 그래서 프론트 소스는 이 변경에 등장하지 않는다).

dist가 없는 개발 환경에서는 마운트하지 않아야 한다. 그때는 :5173이 서빙하고,
백엔드는 API만 답하는 지금 모습 그대로여야 한다.
"""
from fastapi.testclient import TestClient

from app import api


def _bundle(tmp_path):
    (tmp_path / "index.html").write_text("<!doctype html>rapilab", encoding="utf-8")
    (tmp_path / "assets").mkdir()
    (tmp_path / "assets" / "app.js").write_text("console.log(1)", encoding="utf-8")
    return tmp_path


def test_api_routes_still_answer_when_a_bundle_is_mounted(tmp_path, monkeypatch):
    # 마운트 순서를 틀리면 "/"에 걸린 정적 서빙이 /api/* 를 전부 삼킨다.
    monkeypatch.setattr(api, "frontend_dist", lambda: _bundle(tmp_path))
    client = TestClient(api.build_app())
    assert client.get("/api/supported-units").status_code == 200


def test_the_index_is_served_at_the_root(tmp_path, monkeypatch):
    monkeypatch.setattr(api, "frontend_dist", lambda: _bundle(tmp_path))
    client = TestClient(api.build_app())
    response = client.get("/")
    assert response.status_code == 200
    assert "rapilab" in response.text


def test_an_asset_is_served(tmp_path, monkeypatch):
    monkeypatch.setattr(api, "frontend_dist", lambda: _bundle(tmp_path))
    client = TestClient(api.build_app())
    assert client.get("/assets/app.js").status_code == 200


def test_a_client_route_falls_back_to_index_html(tmp_path, monkeypatch):
    # 앱 안에서 새로고침하거나 딥링크로 들어오면 서버가 모르는 경로가 온다.
    # SPA이므로 index.html을 주고 라우팅은 클라이언트에 맡긴다.
    monkeypatch.setattr(api, "frontend_dist", lambda: _bundle(tmp_path))
    client = TestClient(api.build_app())
    response = client.get("/some/client/route")
    assert response.status_code == 200
    assert "rapilab" in response.text


def test_an_unknown_api_route_is_still_a_404_not_the_index(tmp_path, monkeypatch):
    # 폴백이 /api/* 까지 삼키면 클라이언트가 오타 난 엔드포인트에서 HTML을 받고
    # JSON 파싱 오류를 보게 된다 - 원인에서 한참 떨어진 증상이다.
    monkeypatch.setattr(api, "frontend_dist", lambda: _bundle(tmp_path))
    client = TestClient(api.build_app())
    assert client.get("/api/no-such-endpoint").status_code == 404


def test_no_bundle_means_no_mount(tmp_path, monkeypatch):
    monkeypatch.setattr(api, "frontend_dist", lambda: tmp_path / "absent")
    client = TestClient(api.build_app())
    assert client.get("/some/client/route").status_code == 404
    assert client.get("/api/supported-units").status_code == 200


def test_a_missing_asset_is_a_404_not_the_index(tmp_path, monkeypatch):
    """없는 자산에 index.html을 200으로 주면 화면이 조용히 검게 뜬다.

    브라우저는 `<script src="/assets/app.js">`가 돌려준 HTML을 파싱하다 실패하고
    아무것도 그리지 않는다 - 증상에 원인이 한 마디도 안 남는다. 2026-07-31에
    실제로 이 모양의 검은 화면을 겪었고, 그때 이 테스트가 없었다.
    """
    monkeypatch.setattr(api, "frontend_dist", lambda: _bundle(tmp_path))
    client = TestClient(api.build_app())
    assert client.get("/assets/index-DOESNOTEXIST.js").status_code == 404
    assert client.get("/favicon-missing.svg").status_code == 404


def test_a_client_route_with_no_extension_still_falls_back(tmp_path, monkeypatch):
    # 자산 판별은 확장자로 하므로, 확장자 없는 SPA 라우트는 그대로 폴백해야 한다.
    monkeypatch.setattr(api, "frontend_dist", lambda: _bundle(tmp_path))
    client = TestClient(api.build_app())
    response = client.get("/deck/3/edit")
    assert response.status_code == 200
    assert "rapilab" in response.text
