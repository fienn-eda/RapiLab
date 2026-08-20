"""GET /api/raid-rotations - 회차 보스 카드가 읽는 표면."""
from fastapi.testclient import TestClient

from app.api import RaidRotationsResponse, app
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


def test_a_guide_survives_the_wire_untouched():
    # stated와 같은 자리다: 응답 모델에 선언이 없으면 로더는 통과시키는데 라우트가
    # 조용히 떨어뜨린다. 그러면 데이터 파일에 가이드를 적어도 앱에는 안 뜨고,
    # 그 사실은 **가이드를 처음 적는 날에야** 드러난다 - 하필 릴리스 직전이다.
    #
    # 파일이 아직 가이드를 안 싣고 있으므로 모델에 직접 밀어 넣어 확인한다.
    doc = load_rotations()
    guide = [{"at": 12, "text": "탄막 - 엄폐"}, {"at": None, "text": "잡몹이 계속 나온다"}]
    doc["rotations"][0]["bosses"][0]["guide"] = guide

    served = RaidRotationsResponse(**doc).model_dump()

    assert served["rotations"][0]["bosses"][0]["guide"] == guide


def test_every_boss_carries_a_guide_key():
    # stated와 같은 이유로 키를 반드시 적는다 - 빼면 서버는 pydantic 기본값 []를
    # 채워 응답하는데 파일에는 키가 없어 test_the_route_serves_the_file_as_is가
    # 깨진다.
    for rotation in get()["rotations"]:
        for boss in rotation["bosses"]:
            assert "guide" in boss


def test_a_union_rotation_carries_all_five_bosses():
    union = next(r for r in get()["rotations"] if r["id"] == "union-2026-07-31")
    assert len(union["bosses"]) == 5
