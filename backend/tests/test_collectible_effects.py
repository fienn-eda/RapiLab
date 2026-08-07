"""소장품 해석기 - 단계에서 스킬레벨로, 스킬레벨에서 수치로.

수치의 근거는 Fienn의 인게임 확인이다: MG 소장품 최대단계가 최대 장탄 수 9.5%
(Flora, SSR 5단계에서도 동일)이고, SR 소장품 5단계가 차지 대미지 6.31% 배율
(에이드 사격장). docs/engine-gaps.md #17.
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
            # 사다리가 5칸이지만 도달 가능한 스킬레벨은 4까지뿐이다(위 level1의
            # 최댓값) - ladder[-1]과 ladder[skill_level - 1]이 갈라지게 일부러
            # 벌려 놓았다. 큐브의 사다리도 자기 상한을 넘어 이어지는 전례가
            # 있다(docs/insights.md) - 이 격차가 없으면 이 픽스처는 모듈
            # docstring이 경고하는 ladder[-1] 버그를 못 잡는다.
            {"description_value": ["4.74", "6.32", "7.91", "9.5", "11.09"]},   # 최대 장탄 수
            {"description_value": ["30", "32", "35", "37", "40"]},            # 방어력 (미매핑)
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
    assert collectible_modifiers(0, 0, "ade-agent-bunny", weapon="MG") == ({}, [])


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


# Pinned rather than discovered by weapon_type/favorite_rare scan: a scan
# returns whichever record happens to come first, and both rarities of a weapon
# group answer the same scan, so it would silently decide what the 265.775
# acceptance test below reads. Pinning also means a renumber or deletion of
# either record fails the presence check below LOUDLY, rather than skip-green
# like the scan-and-skip helper this replaced.
MG_COLLECTIBLE_TID = 100202   # SR rarity, MG group - in-game verified (Flora)
SR_COLLECTIBLE_TID = 100602   # SR rarity, SR group - in-game verified (에이드)
R_SR_COLLECTIBLE_TID = 100601  # R rarity, SR group
SG_COLLECTIBLE_TID = 100402   # SR rarity, SG group - 포츈메이트가 실제로 낀 것


def test_the_pinned_collectible_tids_are_still_in_the_committed_table():
    """If any pinned tid above is renumbered or removed, this must fail -
    not skip - so the acceptance tests below can't quietly go green-by-skip."""
    from app.stat_assembly import load_stat_tables

    table = load_stat_tables()["collectibles"]
    assert table[str(MG_COLLECTIBLE_TID)]["weapon_type"] == "MG"
    assert table[str(SR_COLLECTIBLE_TID)]["weapon_type"] == "SR"
    assert table[str(MG_COLLECTIBLE_TID)]["favorite_rare"] == "SR"
    assert table[str(R_SR_COLLECTIBLE_TID)]["favorite_rare"] == "R"


def test_every_weapon_group_has_both_rarities_committed():
    """소장품은 무기군 6 x 등급 2다. 하나라도 비면 그 무기군을 쓰는 유닛이
    조용히 아무 효과도 못 받는다 - 이것이 gap #17의 원래 상태였다."""
    from app.stat_assembly import load_stat_tables

    table = load_stat_tables()["collectibles"]
    committed = {(r["favorite_rare"], r["weapon_type"]) for r in table.values()}
    for weapon in ("AR", "SMG", "SG", "RL", "SR", "MG"):
        assert ("R", weapon) in committed, weapon
        assert ("SR", weapon) in committed, weapon


def test_every_committed_skill_group_has_a_mapping():
    """새 레코드를 넣고 COLLECTIBLE_SKILL_STATS 매핑을 빠뜨리면 경고 한 줄만
    찍고 조용히 건너뛴다 - 그 침묵을 여기서 깨뜨린다."""
    from app.collectible_effects import COLLECTIBLE_SKILL_STATS
    from app.stat_assembly import load_stat_tables

    for record in load_stat_tables()["collectibles"].values():
        for group in record["collection_skill_group_data"]:
            assert group["group_id"] in COLLECTIBLE_SKILL_STATS, (
                f"{record['id']} ({record['favorite_rare']} {record['weapon_type']})"
                f" 의 그룹 {group['group_id']}")


def test_the_pinned_sg_collectible_tid_is_still_in_the_committed_table():
    from app.stat_assembly import load_stat_tables

    table = load_stat_tables()["collectibles"]
    assert table[str(SG_COLLECTIBLE_TID)]["weapon_type"] == "SG"
    assert table[str(SG_COLLECTIBLE_TID)]["favorite_rare"] == "SR"


def test_an_sg_collectible_grants_the_normal_attack_multiplier_not_a_weapon_scale():
    """SG·SMG 소장품이 올리는 것은 「일반 공격 대미지 배율」이고, 그것은 청춘의
    기록 같은 스킬이 주는 것과 **같은 스탯**이다(damage-formula-reference.md:75).
    같은 스탯이면 같은 가산 버킷에 들어가야 한다 - 무기 스탯을 따로 곱하면 두
    소스가 곱셈으로 붙어 포츈메이트 실측(스택당 0.0913573)과 0.87% 어긋난다."""
    weapon_multipliers, effects = collectible_modifiers(
        SG_COLLECTIBLE_TID, 15, "arcana-fortune-mate", weapon="SG")

    assert weapon_multipliers == {}
    assert [(e.stat, round(e.value, 6), e.scope, e.duration) for e in effects] == [
        ("normal_attack_damage_multiplier", 0.0946, "self", None)]


def test_ades_charge_damage_matches_her_range_test():
    """사격장 실측: SR 소장품 5단계가 차지 대미지 6.31% 배율을 준다. 「배율」은
    무기 기본 250%에 비례하므로 265.775%가 되어야 한다 - 256.31%가 아니다."""
    from app.models import UserNikkeState
    from app.user_roster import load_roster

    state = UserNikkeState.model_validate({
        "character_slug": "ade-agent-bunny", "level": 200,
        "hp": 1_000_000.0, "atk": 305_667.0, "def_": 3_000.0,
        "skill_levels": {"skill1": 10, "skill2": 7, "burst": 10},
        "collectible_tid": SR_COLLECTIBLE_TID, "collectible_level": 5,
    })
    specs, _ = load_roster([state])
    assert specs[0].weapon_stats["charge_damage_percent"] == pytest.approx(265.775, abs=0.01)


def test_a_maxed_mg_collectible_grants_max_ammo_as_a_plain_effect():
    """평범한 %는 무기 스탯이 아니라 버프로 간다. Flora의 MG 최대치 9.5%."""
    from app.collectible_effects import collectible_modifiers

    weapon, effects = collectible_modifiers(MG_COLLECTIBLE_TID, 15, "flora", weapon="MG")
    assert weapon == {}
    assert [(e.stat, round(e.value, 5)) for e in effects] == [("max_ammo_percent", 0.095)]


def test_a_favorite_item_holder_reads_the_top_rung_through_collectible_modifiers():
    """Finding 1 regression: the two tests above (and
    test_a_favorite_item_reads_the_top_reachable_rung_whatever_its_own_level)
    all drive is_favorite=True straight into skill_percents, which never
    exercises the tid lookup that actually breaks in production - a promoted
    unit's tid is >= FAVORITE_ITEM_TID_BASE and tables.json["collectibles"]
    has no key that high, so `collectible_modifiers` must resolve a favorite
    item by WEAPON GROUP instead of by tid. Any tid >= the threshold works
    here - resolution no longer depends on the specific value."""
    from app.stat_assembly import FAVORITE_ITEM_TID_BASE

    weapon, effects = collectible_modifiers(
        FAVORITE_ITEM_TID_BASE + 34567, 5, "flora", weapon="MG")
    assert weapon == {}
    assert [(e.stat, round(e.value, 5)) for e in effects] == [("max_ammo_percent", 0.095)]


def test_level_zero_is_equipped_and_pays_both_its_skill_and_its_stat():
    """레벨 0 소장품은 **착용된 상태**이고, 스킬과 스탯을 둘 다 사다리 1단으로 낸다.

    착용 여부를 말하는 것은 레벨이 아니라 **tid**다 - 빈 슬롯은 tid가 0이다. 두
    함수가 tid로 판정하는 것이 우연이 아님을 한 자리에 못 박는다.

    - 스킬: Fienn이 레벨 0 보유 9유닛을 인게임에서 전수 확인했다(2026-07-27) -
      헬름: 아쿠아마린 코어 대미지 +10.22%, 볼륨·리터 평타 배율 4.73%,
      D: 킬러 와이프 차지 배율 4.74%, R등급 코어 +5.67% / 최대 장탄 +1.56%.
      전부 사다리 **1단**이고 전부 **적용 중**이었다.
    - 스탯: 레벨 0 착용 31기가 커브 index 0을 정확히 요구한다(SR 3,029 · R 638).
      리터의 인게임 표시값이 이 읽기를 확정했다(Fienn, 2026-08-07).
    """
    from app.stat_assembly import collectible_atk, collectible_hp, load_stat_tables

    tables = load_stat_tables()
    # 헬름: 아쿠아마린과 같은 상태: SR 등급 AR 소장품, 레벨 0.
    weapon, effects = collectible_modifiers(100102, 0, "helm-aquamarine", weapon="AR")
    assert weapon == {}
    assert [(e.stat, round(e.value, 5)) for e in effects] == [
        ("other_core_damage_sources", 0.1022)]
    # 같은 슬롯이 스탯도 사다리 1단으로 낸다.
    assert collectible_atk(tables, 100102, 0) == 3029
    assert collectible_hp(tables, 100102, 0) == 94000
    # 빈 슬롯은 둘 다 없다 - 판별자는 레벨이 아니라 tid.
    assert collectible_modifiers(0, 0, "helm-aquamarine", weapon="AR") == ({}, [])
    assert collectible_atk(tables, 0, 0) == 0
    assert collectible_hp(tables, 0, 0) == 0
    # 레벨이 오르면 사다리를 따라 올라간다.
    assert collectible_atk(tables, 100102, 1) == 3370


def test_a_favorite_item_holder_with_no_record_for_their_weapon_group_degrades_safely():
    """무기군을 못 찾으면 예외가 아니라 무효로 떨어져야 한다 - 모르는 평범한
    tid와 같은 처리다. 여섯 무기군이 전부 커밋된 지금은 게임이 새 무기군을
    내놓는 경우가 이 경로다."""
    from app.stat_assembly import FAVORITE_ITEM_TID_BASE

    assert collectible_modifiers(
        FAVORITE_ITEM_TID_BASE + 1, 5, "some-future-unit", weapon="BOW") == ({}, [])


def test_a_real_favorite_item_tid_resolves_to_its_own_record():
    """애장품 tid(2xxxxx)도 이제 테이블의 키다. 무기군 폴백과 같은 값이 나와야
    한다 - 애장품 레코드는 자기 무기군 SR의 스킬 그룹을 그대로 싣고 사다리가
    최상단에 고정돼 있기 때문이다."""
    from app.stat_assembly import FAVORITE_ITEM_TID_BASE, load_stat_tables

    table = load_stat_tables()["collectibles"]
    mg_favorite = next(int(tid) for tid, r in table.items()
                       if r["favorite_rare"] == "SSR" and r["weapon_type"] == "MG")
    assert mg_favorite >= FAVORITE_ITEM_TID_BASE
    by_tid = collectible_modifiers(mg_favorite, 2, "flora", weapon="MG")
    by_weapon_group = collectible_modifiers(
        FAVORITE_ITEM_TID_BASE + 34567, 2, "flora", weapon="MG")
    assert [(e.stat, e.value) for e in by_tid[1]] == [
        (e.stat, e.value) for e in by_weapon_group[1]]
    assert by_tid[0] == by_weapon_group[0]


def test_the_r_rarity_ladder_is_weaker_than_the_sr_one():
    """R과 SR은 같은 스탯을 다른 사다리로 준다. 등급을 무시하고 한 사다리만
    읽으면 R 보유자가 과대평가된다."""
    r_weapon, _ = collectible_modifiers(R_SR_COLLECTIBLE_TID, 15, "ade-agent-bunny",
                                        weapon="SR")
    sr_weapon, _ = collectible_modifiers(SR_COLLECTIBLE_TID, 15, "ade-agent-bunny",
                                         weapon="SR")
    assert r_weapon["charge_damage_percent"] == pytest.approx(1.0631, abs=1e-4)
    assert sr_weapon["charge_damage_percent"] == pytest.approx(1.0947, abs=1e-4)


def test_a_mode_variant_spec_still_carries_the_weapon_multiplier():
    """cinderella-crystal-wave-snipe swaps its whole weapon_stats profile via
    get_weapon_profile_override (an SR profile at that). The collectible
    multiplier must land AFTER that swap, on both variant specs the loader
    produces, not just the MG-default one - a differential against the same
    roster with no collectible equipped, so a silently-skipped multiply shows
    up as a ratio of 1.0 instead of 1.0631."""
    from app.models import UserNikkeState
    from app.user_roster import load_roster

    base_state = {
        "character_slug": "cinderella-crystal-wave", "level": 200,
        "hp": 1_000_000.0, "atk": 300_000.0, "def_": 3_000.0,
        "skill_levels": {"skill1": 10, "skill2": 10, "burst": 10},
    }
    bare_specs, excluded = load_roster(
        [UserNikkeState.model_validate(base_state)])
    equipped_specs, excluded_equipped = load_roster([UserNikkeState.model_validate(
        {**base_state, "collectible_tid": SR_COLLECTIBLE_TID, "collectible_level": 5})])
    assert not excluded and not excluded_equipped
    bare_by_slug = {spec.slug: spec for spec in bare_specs}
    equipped_by_slug = {spec.slug: spec for spec in equipped_specs}
    assert set(bare_by_slug) == set(equipped_by_slug) == {
        "cinderella-crystal-wave-mg", "cinderella-crystal-wave-snipe"}
    for slug in bare_by_slug:
        bare = bare_by_slug[slug].weapon_stats["charge_damage_percent"]
        equipped = equipped_by_slug[slug].weapon_stats["charge_damage_percent"]
        assert equipped / bare == pytest.approx(1.0631, abs=1e-4), slug


def test_the_stat_table_is_parsed_once_across_many_lookups(monkeypatch):
    """`collectible_modifiers` sits on deck_search's combinatorial ordering
    loop (`feasible_orderings` calls `roster._passive_effects` once per unit
    per candidate ordering) - the identical hot path `cube_effects` already
    solved for the harmony cube via `@lru_cache` on the parsed table. A
    regression here would reparse the ~369KB stat table per unit per
    ordering instead of once."""
    from app import collectible_effects

    collectible_effects._collectibles_table.cache_clear()
    real_loader = collectible_effects.load_stat_tables
    calls = []

    def counting_loader(*args, **kwargs):
        calls.append(1)
        return real_loader(*args, **kwargs)

    monkeypatch.setattr(collectible_effects, "load_stat_tables", counting_loader)
    for _ in range(5):
        collectible_effects.collectible_modifiers(
            SR_COLLECTIBLE_TID, 5, "ade-agent-bunny", weapon="SR")
    assert len(calls) == 1
    collectible_effects._collectibles_table.cache_clear()


def test_a_collectible_charge_damage_multiplier_reaches_a_transform_profile():
    """무기변형 프로파일은 스킬 슬롯에서 만들어져 weapon_stats를 안 거친다. 배율이
    값 딕셔너리를 타고 가야 그 프로파일이 소장품을 받는다 - 맥스웰이 그 경로다.
    (Fienn 실측 2026-08-03, docs/measurements/collectible-charge-damage-in-transform.md)"""
    from types import SimpleNamespace

    from app.models import UserNikkeState
    from app.roster import assemble_simulation_inputs
    from app.user_roster import load_roster

    def transform_charge_damage(tid, level):
        state = UserNikkeState.model_validate({
            "character_slug": "maxwell", "level": 200,
            "hp": 1_000_000.0, "atk": 300_000.0, "def_": 3_000.0,
            "skill_levels": {"skill1": 1, "skill2": 1, "burst": 1},
            "collectible_tid": tid, "collectible_level": level,
        })
        specs, excluded = load_roster([state])
        assert not excluded
        schedule = assemble_simulation_inputs(specs)["weapon_mode_schedules"]["maxwell"]
        segment = schedule(SimpleNamespace(burst_times={"maxwell": [20.0]}), 180.0)[0]
        return segment["profile"]["charge_damage_percent"]

    bare = transform_charge_damage(0, 0)
    equipped = transform_charge_damage(SR_COLLECTIBLE_TID, 5)
    assert equipped == pytest.approx(bare * 1.0631)
