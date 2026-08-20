"""회차 데이터 파일의 검증 규칙을 못박는다.

깨진 파일이 런타임까지 가도 프런트(`useRaidRotations`)가 예외를 빈 목록으로
삼켜 화면은 피커만 안 뜬 채 조용하다. 그 파일이 사용자에게 닿기 전에 걸러내는
자리가 여기다 — 데스크톱 앱 번들에 실리기 전, 이 테스트들이 어떤 깨짐을
잡아야 하는지를 규칙별로 못박는다.
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
        "bosses": [
            {"name": "보스", "weakness": "Iron", "range_band": None, "stated": {}},
        ],
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
    boss = [{"name": "보스", "weakness": "Poison", "range_band": None, "stated": {}}]
    with pytest.raises(ValueError, match="Poison"):
        validate_rotations(a_doc(a_rotation(bosses=boss)))


def test_a_boss_with_no_weakness_is_rejected():
    # 약점은 카드를 골랐을 때 반드시 채워지는 값이다. 그것이 비면 카드를 눌러도
    # 화면에는 거의 아무 일도 안 일어난 것처럼 보이면서 나머지 필드는 조용히
    # 초기화된다 (Fienn, 2026-08-07).
    boss = [{"name": "보스", "weakness": None, "range_band": None, "stated": {}}]
    with pytest.raises(ValueError, match="보스"):
        validate_rotations(a_doc(a_rotation(bosses=boss)))


def test_an_unknown_range_band_is_rejected():
    # 공지의 「거리」는 판독 시점에 엔진 어휘로 옮겨 적힌다. 한글이 그대로 들어오면
    # 옮기는 단계를 건너뛴 것이므로 화면이 그 값을 적정거리에 얹을 수 없다.
    boss = [{"name": "보스", "weakness": "Iron", "range_band": "근거리", "stated": {}}]
    with pytest.raises(ValueError, match="근거리"):
        validate_rotations(a_doc(a_rotation(bosses=boss)))


def test_a_boss_with_no_range_band_is_allowed():
    # 솔로 공지는 거리를 적지 않는다 - 그때 적정거리는 「모름」으로 남는다.
    boss = [{"name": "보스", "weakness": "Iron", "range_band": None, "stated": {}}]
    assert validate_rotations(a_doc(a_rotation(bosses=boss)))


def test_a_non_positive_core_diameter_is_rejected():
    # 0은 「코어가 없다」가 아니다 - 그건 BossProfile.core_hittable이 표현한다.
    # 여기 0이 들어오면 판독이 값을 못 읽고 자리만 채운 것이다.
    boss = [{"name": "보스", "weakness": "Iron", "range_band": None,
             "core_diameter_px": 0, "stated": {}}]
    with pytest.raises(ValueError, match="보스"):
        validate_rotations(a_doc(a_rotation(bosses=boss)))


def test_a_measured_core_diameter_is_allowed():
    boss = [{"name": "보스", "weakness": "Iron", "range_band": None,
             "core_diameter_px": 33.33, "stated": {}}]
    assert validate_rotations(a_doc(a_rotation(bosses=boss)))


def test_a_boss_with_no_core_diameter_key_is_allowed():
    # 코어는 재야만 존재하는 값이라 weakness/range_band와 성격이 다르다 - 안 잰
    # 보스의 dict에는 키 자체가 없을 수 있다. 번들 파일에 키가 빠지는 것은
    # test_api_raid_rotations.test_the_route_serves_the_file_as_is가 막는다.
    boss = [{"name": "보스", "weakness": "Iron", "range_band": None, "stated": {}}]
    assert validate_rotations(a_doc(a_rotation(bosses=boss)))


def test_declared_part_destruction_times_are_allowed():
    boss = [{"name": "보스", "weakness": "Iron", "range_band": None,
             "part_destruction_times": [1, 61, 126], "stated": {}}]
    assert validate_rotations(a_doc(a_rotation(bosses=boss)))


def test_a_negative_part_destruction_time_is_rejected():
    # 전투가 시작하기 전에 깨지는 파츠는 없다. 음수가 들어오면 판독이 시각이
    # 아닌 것을 시각 자리에 넣은 것이다.
    boss = [{"name": "보스", "weakness": "Iron", "range_band": None,
             "part_destruction_times": [1, -5], "stated": {}}]
    with pytest.raises(ValueError, match="보스"):
        validate_rotations(a_doc(a_rotation(bosses=boss)))


def test_a_boss_with_no_part_destruction_times_key_is_allowed():
    # 코어 지름과 같은 계열이다 - 관측해야만 존재하는 값이라 키 자체가 없을 수 있고,
    # 그때 파괴에 반응하는 스킬은 part_destructible 불리언만 보던 근사로 돈다.
    boss = [{"name": "보스", "weakness": "Iron", "range_band": None, "stated": {}}]
    assert validate_rotations(a_doc(a_rotation(bosses=boss)))


def test_the_shipped_union_bosses_all_carry_a_range_band():
    # 유니온 공지는 보스마다 거리를 적으므로, 비어 있으면 판독에서 빠뜨린 것이다.
    doc = load_rotations()
    for union in [r for r in doc["rotations"] if r["raid"] == "union"]:
        for boss in union["bosses"]:
            assert boss["range_band"] in {"near", "mid", "far"}, boss["name"]


def test_an_empty_boss_list_is_rejected():
    # 빈 목록이 검증을 통과하면 화면에는 카드 상자만 뜨고 카드가 하나도 없이
    # 그려진다 - 회차 자체가 없는 것과 구별이 안 된다.
    with pytest.raises(ValueError, match="solo-1"):
        validate_rotations(a_doc(a_rotation(bosses=[])))


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


def test_every_shipped_union_rotation_has_one_boss_per_element():
    doc = load_rotations()
    unions = [r for r in doc["rotations"] if r["raid"] == "union"]
    assert unions
    for union in unions:
        assert {b["weakness"] for b in union["bosses"]} == ELEMENTS, union["id"]


def test_the_shipped_file_is_the_one_the_app_bundles():
    # 로더의 기본 경로가 paths.data_dir()이어야 얼린 앱에서도 같은 파일을 읽는다.
    from app.paths import data_dir
    assert json.loads((data_dir() / "raid-rotations.json").read_text(encoding="utf-8"))
