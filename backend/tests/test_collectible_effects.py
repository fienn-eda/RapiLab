"""소장품 해석기 - 단계에서 스킬레벨로, 스킬레벨에서 수치로.

수치의 근거는 Fienn의 인게임 확인이다: MG 소장품 최대단계가 최대 장탄 수 9.5%
(Flora, SSR 5단계에서도 동일)이고, SR 소장품 5단계가 차지 대미지 6.31% 배율
(에이드 사격장). docs/engine-gaps.md #15.
"""
import pytest

from app.collectible_effects import collectible_modifiers, skill_percents


MG_RECORD = {
    "id": 100202,
    "weapon_type": "MG",
    # 단계 0~15 -> 스킬레벨. 수치는 0/5/10/15단계에서만 오른다.
    "level1": [1, 1, 1, 1, 1, 2, 2, 2, 2, 2, 3, 3, 3, 3, 3, 4],
    "level2": [1, 1, 1, 1, 1, 2, 2, 2, 2, 2, 3, 3, 3, 3, 3, 4],
    "collection_skill_group_data": [
        {"group_id": 712401, "description_value_list": [
            {"description_value": ["4.74", "6.32", "7.91", "9.5"]},   # 최대 장탄 수
            {"description_value": ["30", "32", "35", "37"]},          # 방어력 (미매핑)
        ]},
        {"group_id": 712002, "description_value_list": [              # 둘 다 방어 스탯
            {"description_value": ["10", "12", "14", "17"]},
            {"description_value": ["12", "18", "24", "30"]},
        ]},
    ],
}


def test_level_five_reads_the_second_rung_not_the_fifth():
    """단계 -> 스킬레벨은 사다리를 한 번 거친다. 배열은 0-based(단계 0이 존재)라
    큐브의 1-based 인덱싱을 그대로 가져오면 한 칸씩 밀린다."""
    percents = skill_percents(MG_RECORD, item_level=5, is_favorite=False)
    assert percents == {("max_ammo_percent", "effect"): 6.32}


def test_level_zero_is_a_real_level_not_an_empty_slot():
    percents = skill_percents(MG_RECORD, item_level=0, is_favorite=False)
    assert percents == {("max_ammo_percent", "effect"): 4.74}


def test_a_favorite_item_reads_the_top_reachable_rung_whatever_its_own_level():
    """애장품은 SR 15단계에서만 승급할 수 있으므로 무기군 스킬은 항상 최대치다.
    자기 SSR 단계는 유닛 스킬 해금만 움직인다 - Flora가 SSR 5단계에서도 9.5%를
    유지하는 것이 실증이다."""
    percents = skill_percents(MG_RECORD, item_level=5, is_favorite=True)
    assert percents == {("max_ammo_percent", "effect"): 9.5}


def test_unknown_skill_group_is_skipped_not_guessed(caplog):
    record = dict(MG_RECORD, collection_skill_group_data=[
        {"group_id": 999999, "description_value_list": [
            {"description_value": ["1", "2", "3", "4"]}]},
    ])
    assert skill_percents(record, item_level=15, is_favorite=False) == {}
    assert "999999" in caplog.text


def test_no_collectible_equipped_contributes_nothing():
    assert collectible_modifiers(0, 0, "ade-agent-bunny") == ({}, [])
