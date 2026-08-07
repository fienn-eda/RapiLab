"""GET /api/raid-rotations - 회차 보스 카드가 읽는 표면."""
from fastapi.testclient import TestClient

from app.api import app
from app.raid_rotations import load_rotations

client = TestClient(app)


def get():
    response = client.get("/api/raid-rotations")
    assert response.status_code == 200
    return response.json()


def test_the_route_serves_the_file_as_is():
    # 서버가 회차를 골라 자르지 않는다. 어느 회차를 보여줄지는 화면의 판단이고,
    # 서버가 미리 자르면 과거 회차를 보려는 다음 요구에서 양쪽을 고쳐야 한다.
    assert get() == load_rotations()


def test_every_boss_carries_a_weakness_field():
    for rotation in get()["rotations"]:
        for boss in rotation["bosses"]:
            assert "weakness" in boss


def test_stated_survives_the_wire_untouched():
    # stated는 자유 형식이라 pydantic이 조용히 떨어뜨리기 쉬운 자리다. 공지 원문이
    # 화면까지 그대로 가는지가 이 기능의 요점이므로 값으로 확인한다.
    solo = next(r for r in get()["rotations"] if r["id"] == "solo-39")
    stated = solo["bosses"][0]["stated"]
    assert stated["스쿼드 추천"] == "머신건 니케"
    assert len(stated["랩쳐 주요 공격"]) == 3


def test_a_union_rotation_carries_all_five_bosses():
    union = next(r for r in get()["rotations"] if r["id"] == "union-2026-07-31")
    assert len(union["bosses"]) == 5
