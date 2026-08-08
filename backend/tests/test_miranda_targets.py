"""덱 5인 중 누가 미란다의 파워업!과 웨이크업!3을 받는가."""
from app.deck_search import BossProfile
from app.miranda_targets import (
    MIRANDA_SLUGS, NO_FULL_BURST_NOTE, miranda_slug_in, miranda_target_report,
)
from app.models import SkillLevels, UserNikkeState
from app.user_roster import load_roster

MAXED = SkillLevels(skill1=10, skill2=10, burst=10)
BOSS = BossProfile(fight_duration=180.0)


def a_state(slug, atk=100_000.0):
    return UserNikkeState(
        character_slug=slug, level=400, hp=500_000.0, atk=atk, def_=10_000.0,
        skill_levels=MAXED, overload_options=[],
    )


def a_report(deck, atk_by_slug=None, boss=None):
    atk_by_slug = atk_by_slug or {}
    states = [a_state(slug, atk_by_slug.get(slug, 100_000.0)) for slug in deck]
    specs, _excluded = load_roster(states)
    spec_index = {spec.slug: spec for spec in specs}
    deck_specs = [spec_index[slug] for slug in deck]
    return miranda_target_report(deck_specs, boss or BOSS, spec_index)


def test_miranda_slug_in_finds_either_build():
    assert miranda_slug_in(["crown", "miranda"]) == "miranda"
    assert miranda_slug_in(["crown", "miranda-signature"]) == "miranda-signature"
    assert miranda_slug_in(["crown", "isabel"]) is None
    assert set(MIRANDA_SLUGS) == {"miranda", "miranda-signature"}


def test_favorite_item_build_grants_two_and_one():
    report = a_report(["miranda-signature", "crown", "ada-wong", "cinderella", "isabel"])
    assert report["miranda_slug"] == "miranda-signature"
    assert report["has_favorite_item"] is True
    assert report["cycles"], "풀 버스트가 한 번도 안 열렸다"
    for cycle in report["cycles"]:
        assert len(cycle["powering_up"]) == 2
        assert len(cycle["wake_up_crit_rate"]) == 1
        assert cycle["wake_up_crit_rate"][0] in cycle["powering_up"]


def test_base_build_grants_one_and_has_no_third_bullet():
    report = a_report(["miranda", "crown", "ada-wong", "cinderella", "isabel"])
    assert report["has_favorite_item"] is False
    assert report["cycles"], "풀 버스트가 한 번도 안 열렸다"
    for cycle in report["cycles"]:
        assert len(cycle["powering_up"]) == 1
        assert cycle["wake_up_crit_rate"] == []
    assert any("애장품" in note for note in report["notes"])


def test_miranda_is_never_her_own_target():
    report = a_report(["miranda-signature", "crown", "ada-wong", "cinderella", "isabel"])
    assert report["cycles"], "풀 버스트가 한 번도 안 열렸다"
    for cycle in report["cycles"]:
        assert "miranda-signature" not in cycle["powering_up"]
        assert "miranda-signature" not in cycle["wake_up_crit_rate"]


def test_cycles_are_numbered_from_one_and_are_contiguous():
    report = a_report(["miranda-signature", "crown", "ada-wong", "cinderella", "isabel"])
    assert report["cycles"], "풀 버스트가 한 번도 안 열렸다"
    assert [c["index"] for c in report["cycles"]] == list(
        range(1, len(report["cycles"]) + 1))


def test_seats_report_the_engines_own_ordering():
    report = a_report(["miranda-signature", "crown", "ada-wong", "cinderella", "isabel"])
    assert len(report["seats"]) == 5
    assert {s["slug"] for s in report["seats"]} == {
        "miranda-signature", "crown", "ada-wong", "cinderella", "isabel"}
    tiers = sorted(s["burst_tier"] for s in report["seats"])
    assert tiers == [1, 2, 3, 3, 3]


def test_a_cycle_miranda_does_not_burst_has_no_powering_up_but_still_wakes_up():
    # 1티어가 둘이면 스케줄러는 덱 순서상 먼저인 하나만 쏜다. 웨이크업!은
    # 미란다의 버스트와 무관하게 매 풀버스트마다 발동하므로 계속 채워진다.
    #
    # 2·1·2 대형이다 - 미란다와 리터가 B1, 크라운이 B2, 나머지 둘이 B3.
    # B1 둘에 B3 셋(2·0·3)은 ALLOWED_SHAPES에 없어 InfeasibleDeck으로 죽는다.
    report = a_report(["miranda-signature", "liter", "crown", "ada-wong", "cinderella"])
    assert report["cycles"]
    # 이것이 이 테스트가 증명하는 것이다: 웨이크업!의 방아쇠는 풀버스트 진입이지
    # 미란다의 버스트가 아니므로, 그녀가 못 쏜 사이클에도 3번불릿은 나간다.
    assert all(cycle["wake_up_crit_rate"] for cycle in report["cycles"])
    # 두 B1은 쿨다운이 같아 스케줄러가 매번 같은 하나를 고른다 - 즉 한쪽은
    # 전부 쏘고 다른 쪽은 한 번도 못 쏜다. best_ordering_summary(deck_allocation.py)가
    # B1 두 순열(미란다 먼저 / 리터 먼저)을 총딜로 채점해 더 높은 쪽을 고르고,
    # 그 채점에는 무작위성이 없다 - 두 유닛의 스탯이 고정이면 승자도 고정이다.
    # 이 스탯에서는 리터가 먼저인 순열이 항상 이겨 유일한 B1 좌석에 앉으므로
    # 미란다는 이 덱에서 한 번도 못 쏜다(파워업! 0회). "리터가 이긴다"는
    # 사실 자체가 아니라 "결과가 결정적이다"가 이 assert의 요점이다.
    bursts = sum(1 for c in report["cycles"] if c["powering_up"])
    assert bursts == 0


def test_a_fight_shorter_than_the_gauge_never_opens_full_burst():
    # gauge_charge_time 기본값(BossProfile, 2.4초) 안에서 끝나는 전투는 첫
    # 사이클의 fire_time조차 못 넘긴다 - burst_cycle.simulate_burst_cycle은
    # `fire_time >= fight_duration`이면 이벤트를 하나도 안 남기고 break한다
    # (full_burst_missed도 아니다). cycles가 통째로 비어야 하고, 그 사실이
    # notes에 실려야 빈 결과가 고장으로 안 읽힌다.
    short_boss = BossProfile(fight_duration=1.0)
    report = a_report(
        ["miranda-signature", "crown", "ada-wong", "cinderella", "isabel"],
        boss=short_boss,
    )
    assert report["cycles"] == []
    assert NO_FULL_BURST_NOTE in report["notes"]
