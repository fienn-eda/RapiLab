"""회차 데이터 파일의 검증 규칙.

파일이 깨졌을 때 조용히 빈 목록이 되면 화면에 피커가 안 그려질 뿐이라 아무도
모른다. 그래서 로드가 터지는 편을 택했고, 아래 테스트들이 어떤 깨짐이 터지는지를
못박는다.
"""
import json

import pytest

from app.elements import ELEMENTS
from app.raid_rotations import load_rotations, validate_rotations


def a_rotation(**overrides):
    doc = {
        "id": "solo-1", "raid": "solo", "title": "솔로 레이드 1시즌",
        "starts_at": "2026-01-01T12:00:00+09:00",
        "ends_at": "2026-01-08T04:59:00+09:00",
        "source_url": "https://example.test/1", "source_locale": "ko",
        "read_on": "2026-01-01",
        "bosses": [{"name": "보스", "weakness": "Iron", "stated": {}}],
    }
    doc.update(overrides)
    return doc


def a_doc(*rotations):
    return {"schema_version": 1, "rotations": list(rotations)}


def test_elements_are_the_five_the_wheel_knows():
    assert ELEMENTS == {"Fire", "Water", "Wind", "Iron", "Electric"}


def test_a_valid_document_comes_back_unchanged():
    doc = a_doc(a_rotation())
    assert validate_rotations(doc) is doc


def test_duplicate_ids_are_rejected():
    with pytest.raises(ValueError, match="solo-1"):
        validate_rotations(a_doc(a_rotation(), a_rotation()))


def test_an_unknown_raid_kind_is_rejected():
    with pytest.raises(ValueError, match="ultra"):
        validate_rotations(a_doc(a_rotation(raid="ultra")))


def test_an_unknown_weakness_is_rejected():
    boss = [{"name": "보스", "weakness": "Poison", "stated": {}}]
    with pytest.raises(ValueError, match="Poison"):
        validate_rotations(a_doc(a_rotation(bosses=boss)))


def test_a_boss_with_no_weakness_is_allowed():
    # 무속성 보스가 나오면 약점 칸이 비어야 한다 - 5속성 중 하나를 억지로 고르면
    # 그 순간 없는 약점특효가 붙는다.
    boss = [{"name": "보스", "weakness": None, "stated": {}}]
    assert validate_rotations(a_doc(a_rotation(bosses=boss)))


def test_an_unparseable_time_is_rejected():
    with pytest.raises(ValueError, match="7/23"):
        validate_rotations(a_doc(a_rotation(ends_at="7/23 4:59")))


def test_a_rotation_that_ends_before_it_starts_is_rejected():
    with pytest.raises(ValueError, match="solo-1"):
        validate_rotations(a_doc(a_rotation(
            starts_at="2026-01-08T12:00:00+09:00",
            ends_at="2026-01-01T04:59:00+09:00")))


def test_a_missing_start_is_allowed():
    # 본문 텍스트만으로 들어오는 경로에서는 종료 시각만 적혀 있을 수 있다.
    assert validate_rotations(a_doc(a_rotation(starts_at=None)))


def test_the_shipped_file_loads():
    doc = load_rotations()
    assert doc["schema_version"] == 1
    assert {r["id"] for r in doc["rotations"]} >= {"solo-39", "union-2026-07-31"}


def test_the_shipped_union_rotation_has_one_boss_per_element():
    doc = load_rotations()
    union = next(r for r in doc["rotations"] if r["id"] == "union-2026-07-31")
    assert {b["weakness"] for b in union["bosses"]} == ELEMENTS


def test_the_shipped_file_is_the_one_the_app_bundles(tmp_path):
    # 로더의 기본 경로가 paths.data_dir()이어야 얼린 앱에서도 같은 파일을 읽는다.
    from app.paths import data_dir
    assert json.loads((data_dir() / "raid-rotations.json").read_text(encoding="utf-8"))
