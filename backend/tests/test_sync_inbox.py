"""북마클릿이 놓고 가면 앱이 집어가는 자리.

왜 필요한가: 네이티브 창(WebView2)과 유저 브라우저는 별개라 기존
`window.open` + `postMessage` 경로가 앱에 닿지 않는다. 그래서 북마클릿은
수집한 것을 로컬 서버에 두고, 앱이 그것을 가져간다.

한 칸짜리인 이유: 동기화는 유저가 의도적으로 한 번 하는 행위이고, 큐가
필요하다면 그것은 무언가 잘못됐다는 뜻이다. 새 것이 오면 앞의 것을 덮는다 -
두 번 눌렀을 때 유저가 기대하는 것은 마지막 결과다.
"""
from fastapi.testclient import TestClient

from app.api import app

client = TestClient(app)
PAYLOAD = {"owned": [{"name_code": 1}], "character_details": [], "recycle_room_researches": []}


def _drain():
    client.get("/api/sync-inbox")


def test_an_empty_inbox_says_so_rather_than_erroring():
    _drain()
    response = client.get("/api/sync-inbox")
    assert response.status_code == 200
    assert response.json() == {"payload": None}


def test_what_the_bookmarklet_posts_is_what_the_app_gets():
    _drain()
    assert client.post("/api/sync-inbox", json=PAYLOAD).status_code == 200
    assert client.get("/api/sync-inbox").json()["payload"] == PAYLOAD


def test_taking_it_empties_the_inbox():
    # 앱이 폴링하므로, 비우지 않으면 같은 로스터를 계속 다시 가져온다.
    _drain()
    client.post("/api/sync-inbox", json=PAYLOAD)
    client.get("/api/sync-inbox")
    assert client.get("/api/sync-inbox").json() == {"payload": None}


def test_a_second_sync_replaces_the_first():
    _drain()
    client.post("/api/sync-inbox", json=PAYLOAD)
    newer = {**PAYLOAD, "owned": [{"name_code": 2}]}
    client.post("/api/sync-inbox", json=newer)
    assert client.get("/api/sync-inbox").json()["payload"] == newer


def test_the_inbox_rejects_a_body_that_is_not_a_roster_payload():
    _drain()
    assert client.post("/api/sync-inbox", json={"owned": "not a list"}).status_code == 422
