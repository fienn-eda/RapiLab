"""The bookmarklet sync endpoint: raw blablalink payloads in, assembled roster out.

Assembly correctness is already covered by the 77/77 overload and 159/159 stat
parity suites; these tests cover the HTTP contract and the statelessness the
privacy posture depends on.
"""
import json
import logging
import subprocess
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.api import app

BACKEND_DIR = Path(__file__).resolve().parents[1]

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
    # name_code 5001 is Maxwell (resource_id 102): assert the assembled unit's
    # own identifying fields (name_en, resource_id) never reach the log, not
    # just the input name_code - a log line of the whole roster would still
    # omit "5001" (units carry name_en/resource_id, never name_code) and pass
    # a check that only excludes the input identifier.
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
    units = response.json()["units"]
    assert units and units[0]["resource_id"] == 102  # sanity: Maxwell assembled
    # Only our own log line, not httpx's request trace - a raw line number like
    # _client.py:1025 can incidentally contain "102" and would be a false positive.
    text = "\n".join(r.getMessage() for r in caplog.records if r.name == "app.api")
    assert "roster_sync" in text
    assert "anon-abc" in text          # 익명 id는 남는다
    assert "5001" not in text          # 원시 유닛 데이터는 안 남는다
    assert "Maxwell" not in text       # 조립된 유닛 이름도 안 남는다
    assert "102" not in text           # resource_id도 안 남는다
    assert "intl_open_id" not in text  # open_id는 애초에 서버로 오지도 않는다


def test_telemetry_actually_emits_under_a_real_default_logging_setup():
    """caplog.at_level(logging.INFO) forces the root logger's level for the
    duration of the test, which is exactly what hides this bug: uvicorn never
    touches the root logger, so a real run leaves it at the default WARNING
    and the roster_sync line is silently dropped despite pytest going green.
    Run the endpoint in a bare subprocess - no pytest, no caplog, no fixture
    magic, the same "nobody configured logging" situation uvicorn hands the
    app - and check the line actually lands on stderr.
    """
    script = (
        "from fastapi.testclient import TestClient\n"
        "from app.api import app\n"
        "client = TestClient(app)\n"
        "client.post('/api/assemble-roster', json={'owned': [], "
        "'character_details': [], 'recycle_room_researches': []}, "
        "headers={'X-Client-Id': 'subprocess-proof'})\n"
    )
    result = subprocess.run(
        [sys.executable, "-c", script],
        cwd=BACKEND_DIR, capture_output=True, text=True, timeout=60,
    )
    assert "roster_sync" in result.stderr, result.stderr
    assert "client=subprocess-proof" in result.stderr, result.stderr
