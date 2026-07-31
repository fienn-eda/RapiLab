"""동기화 북마클릿이 로컬 서버를 부를 수 있는가.

2026-07-31 라이브 확인: blablalink 페이지(https)에서 http://127.0.0.1로 보낸
요청은 **통과했고 서버가 200을 냈다** - 브라우저가 loopback을 안전한 출처로
치므로 혼합 콘텐츠에 걸리지 않는다. 막고 있던 것은 CORS 헤더 하나였고, 그것은
이쪽 설정이다. 그래서 이 파일이 지키는 것은 그 설정이다.
"""
from fastapi.testclient import TestClient

from app.api import ALLOWED_ORIGINS, app

BLABLALINK = "https://www.blablalink.com"
client = TestClient(app)


def test_the_bookmarklet_origin_is_allowed():
    assert BLABLALINK in ALLOWED_ORIGINS


def test_a_request_from_blablalink_gets_the_header_back():
    response = client.get("/api/supported-units", headers={"Origin": BLABLALINK})
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == BLABLALINK


def test_the_preflight_for_a_roster_post_is_allowed():
    # 북마클릿은 JSON을 POST하므로 브라우저가 먼저 OPTIONS를 보낸다.
    response = client.options(
        "/api/assemble-roster",
        headers={
            "Origin": BLABLALINK,
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == BLABLALINK


def test_an_unlisted_origin_gets_nothing():
    # 로컬 서버가 열려 있는 동안 아무 사이트나 부를 수 있으면 안 된다.
    response = client.get("/api/supported-units",
                          headers={"Origin": "https://example.com"})
    assert "access-control-allow-origin" not in response.headers
