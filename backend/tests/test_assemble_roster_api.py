"""The bookmarklet sync endpoint: raw blablalink payloads in, assembled roster out.

Assembly correctness is already covered by the 77/77 overload and 159/159 stat
parity suites; these tests cover the HTTP contract and the statelessness the
privacy posture depends on.
"""
import json
import logging
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.api import app

ROOT = Path(__file__).resolve().parents[2]
DETAILS = ROOT / "tools" / "collect-blablalink" / "details.json"

client = TestClient(app)


def test_assembles_a_real_payload_into_roster_units():
    if not DETAILS.exists():
        pytest.skip("local collector dumps not synced")
    raw = json.loads(DETAILS.read_text(encoding="utf-8"))
    response = client.post("/api/assemble-roster", json={
        "owned": raw["owned"],
        "character_details": raw["character_details"],
        "recycle_room_researches": raw["recycle_room_researches"],
    })
    assert response.status_code == 200
    units = response.json()["units"]
    assert len(units) > 100
    first = units[0]
    assert first["raid400"]["atk"] > 0
    assert first["raid400"]["hp"] > 0
    assert "skill_levels" in first and "overload" in first


def test_an_account_with_no_research_rows_still_assembles():
    """멀티유저 전제조건: 미연구 계정도 크래시 없이 조립된다."""
    response = client.post("/api/assemble-roster", json={
        "owned": [], "character_details": [], "recycle_room_researches": [],
    })
    assert response.status_code == 200
    assert response.json() == {"units": []}


def test_a_missing_field_is_a_422_not_a_500():
    response = client.post("/api/assemble-roster", json={"owned": []})
    assert response.status_code == 422


def test_telemetry_logs_aggregates_but_never_the_roster_or_open_id(caplog):
    """프라이버시 규율: 집계 수치만, 원시 데이터·식별자는 절대 안 남는다."""
    payload = {
        "owned": [{"name_code": 5001, "lv": 400, "core": 3, "grade": 3}],
        "character_details": [{"name_code": 5001, "grade": 3, "core": 3}],
        "recycle_room_researches": [],
    }
    with caplog.at_level(logging.INFO):
        response = client.post(
            "/api/assemble-roster", json=payload,
            headers={"X-Client-Id": "anon-abc"},
        )
    assert response.status_code == 200
    text = caplog.text
    assert "roster_sync" in text
    assert "anon-abc" in text          # 익명 id는 남는다
    assert "5001" not in text          # 원시 유닛 데이터는 안 남는다
    assert "intl_open_id" not in text  # open_id는 애초에 서버로 오지도 않는다
