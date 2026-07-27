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


def test_the_spec_carries_the_collectible_identity_from_the_state():
    """소장품은 유닛별 투자다 - 큐브처럼 전역 가정으로 뭉갤 수 없다.
    에이드가 5단계인 것이 반례고, 그 5단계가 사격장 실측의 근거다."""
    from app.models import UserNikkeState
    from app.user_roster import load_roster

    state = UserNikkeState.model_validate({
        "character_slug": "ade-agent-bunny", "level": 200,
        "hp": 1_000_000.0, "atk": 305_667.0, "def_": 3_000.0,
        "skill_levels": {"skill1": 10, "skill2": 7, "burst": 10},
        "collectible_tid": 100202, "collectible_level": 5,
    })
    specs, excluded = load_roster([state])
    assert not excluded
    assert specs[0].collectible_tid == 100202
    assert specs[0].collectible_level == 5


def test_a_roster_without_the_field_defaults_to_no_collectible():
    """필드가 없던 시절의 roster.json을 읽어도 아무도 안 변한다."""
    from app.models import UserNikkeState

    state = UserNikkeState.model_validate({
        "character_slug": "ade-agent-bunny", "level": 200,
        "hp": 1_000_000.0, "atk": 305_667.0, "def_": 3_000.0,
        "skill_levels": {"skill1": 10, "skill2": 7, "burst": 10},
    })
    assert state.collectible_tid == 0
    assert state.collectible_level == 0


def _tid_for(weapon_type, rare):
    """The committed table's collectible for one weapon group and rarity."""
    from app.stat_assembly import load_stat_tables
    for tid, record in load_stat_tables().get("collectibles", {}).items():
        if record["weapon_type"] == weapon_type and record["favorite_rare"] == rare:
            return int(tid)
    pytest.skip(f"no {rare} collectible collected for {weapon_type}")


def test_ades_charge_damage_matches_her_range_test():
    """사격장 실측: SR 소장품 5단계가 차지 대미지 6.31% 배율을 준다. 「배율」은
    무기 기본 250%에 비례하므로 265.775%가 되어야 한다 - 256.31%가 아니다."""
    from app.models import UserNikkeState
    from app.user_roster import load_roster

    tid = _tid_for("SR", "SR")
    state = UserNikkeState.model_validate({
        "character_slug": "ade-agent-bunny", "level": 200,
        "hp": 1_000_000.0, "atk": 305_667.0, "def_": 3_000.0,
        "skill_levels": {"skill1": 10, "skill2": 7, "burst": 10},
        "collectible_tid": tid, "collectible_level": 5,
    })
    specs, _ = load_roster([state])
    assert specs[0].weapon_stats["charge_damage_percent"] == pytest.approx(265.775, abs=0.01)


def test_a_maxed_mg_collectible_grants_max_ammo_as_a_plain_effect():
    """평범한 %는 무기 스탯이 아니라 버프로 간다. Flora의 MG 최대치 9.5%."""
    from app.collectible_effects import collectible_modifiers

    tid = _tid_for("MG", "SR")
    weapon, effects = collectible_modifiers(tid, 15, "flora")
    assert weapon == {}
    assert [(e.stat, round(e.value, 5)) for e in effects] == [("max_ammo_percent", 0.095)]


def test_a_mode_variant_spec_still_carries_the_weapon_multiplier():
    """cinderella-crystal-wave-snipe swaps its whole weapon_stats profile via
    get_weapon_profile_override (an SR profile at that). The collectible
    multiplier must land AFTER that swap, on both variant specs the loader
    produces, not just the MG-default one - a differential against the same
    roster with no collectible equipped, so a silently-skipped multiply shows
    up as a ratio of 1.0 instead of 1.0631."""
    from app.models import UserNikkeState
    from app.user_roster import load_roster

    tid = _tid_for("SR", "SR")
    base_state = {
        "character_slug": "cinderella-crystal-wave", "level": 200,
        "hp": 1_000_000.0, "atk": 300_000.0, "def_": 3_000.0,
        "skill_levels": {"skill1": 10, "skill2": 10, "burst": 10},
    }
    bare_specs, excluded = load_roster(
        [UserNikkeState.model_validate(base_state)])
    equipped_specs, excluded_equipped = load_roster([UserNikkeState.model_validate(
        {**base_state, "collectible_tid": tid, "collectible_level": 5})])
    assert not excluded and not excluded_equipped
    bare_by_slug = {spec.slug: spec for spec in bare_specs}
    equipped_by_slug = {spec.slug: spec for spec in equipped_specs}
    assert set(bare_by_slug) == set(equipped_by_slug) == {
        "cinderella-crystal-wave-mg", "cinderella-crystal-wave-snipe"}
    for slug in bare_by_slug:
        bare = bare_by_slug[slug].weapon_stats["charge_damage_percent"]
        equipped = equipped_by_slug[slug].weapon_stats["charge_damage_percent"]
        assert equipped / bare == pytest.approx(1.0631, abs=1e-4), slug
