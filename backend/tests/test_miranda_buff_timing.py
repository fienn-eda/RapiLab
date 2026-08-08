"""미란다의 두 대상형 불릿이 언제 대상을 정하고, 그 순간의 「최종 공격력」이
무엇을 세는가.

2026-08-08에 확인한 사실을 고정한다:
- 파워업!(버스트)은 B1 시전 순간에 판정한다 - 같은 순간 뒤이어 터지는 B2/B3의
  버스트 효과는 아직 없다.
- 웨이크업! 3번불릿은 풀버스트 진입 순간에 판정한다 - 같은 사이클 파워업!의
  공격력 버프가 이미 실려 있다.
- 랭킹은 오버로드 공격력을 센다. 표시 공격력에 접혀 있는 값이 아니라 엔진이
  따로 얹는 영구 효과다(app/overload_effects.py).
"""
from app.deck_search import BossProfile, evaluate_deck
from app.models import OverloadOption, SkillLevels, UserNikkeState
from app.user_roster import load_roster

DECK = ["miranda-signature", "crown", "ada-wong", "cinderella", "isabel"]
MAXED = SkillLevels(skill1=10, skill2=10, burst=10)


def a_state(slug, overload_atk=0.0):
    options = ([OverloadOption(name="공격력 증가", value=overload_atk)]
               if overload_atk else [])
    return UserNikkeState(
        character_slug=slug, level=400, hp=500_000.0, atk=100_000.0, def_=10_000.0,
        skill_levels=MAXED, overload_options=options,
    )


def a_run(overload_on=None, overload_atk=12.0):
    """DECK 순서 그대로 좌석을 고정해 한 번 돌린다 - 이 파일이 묻는 것은
    타이밍이지 최적 배치가 아니다."""
    states = [a_state(slug, overload_atk if slug == overload_on else 0.0)
              for slug in DECK]
    specs, _excluded = load_roster(states)
    by_slug = {spec.slug: spec for spec in specs}
    ordered = [by_slug[slug] for slug in DECK]
    return evaluate_deck(ordered, BossProfile(fight_duration=40.0),
                         collect_target_grants=True)


def _grants(result):
    powering_up = [g for g in result["target_grants"]
                   if g["caster"] == "miranda-signature" and "atk_percent" in g["stats"]]
    wake_up = [g for g in result["target_grants"]
               if g["caster"] == "miranda-signature" and "crit_rate" in g["stats"]]
    return powering_up, wake_up


def test_powering_up_judges_at_the_burst_1_cast():
    result = a_run()
    powering_up, _ = _grants(result)
    b1_times = [e["time"] for e in result["events"]
                if e["type"] == "burst" and e["slug"] == "miranda-signature"]
    assert powering_up, "파워업!이 한 번도 판정되지 않았다"
    assert [g["time"] for g in powering_up] == b1_times


def test_wake_up_third_bullet_judges_at_full_burst_entry():
    result = a_run()
    _, wake_up = _grants(result)
    starts = [e["time"] for e in result["events"] if e["type"] == "full_burst_start"]
    assert wake_up, "웨이크업!3이 한 번도 판정되지 않았다"
    assert [g["time"] for g in wake_up] == starts


def test_wake_up_ranks_after_powering_up_landed():
    # 같은 사이클 안에서 파워업!이 먼저다. 두 시각이 같은 순간으로 접히면
    # 웨이크업!의 랭킹이 파워업!의 공격력 버프를 못 보게 된다.
    result = a_run()
    powering_up, wake_up = _grants(result)
    assert len(powering_up) == len(wake_up)
    for p, w in zip(powering_up, wake_up):
        assert w["time"] > p["time"]


def test_overload_atk_alone_decides_the_ranking():
    # 표시 공격력이 다섯 다 같으면 랭킹이 전부 동점이고, 동점은 좌석 순서로
    # 갈린다(안정 정렬). 그래서 오버로드를 받는 쪽은 **덱의 맨 뒤**여야 한다 -
    # isabel은 동점일 때 절대 안 뽑히는 자리에 있으므로, 그녀가 1순위로
    # 올라오는 것은 오버로드 말고 설명할 길이 없다.
    #
    # 측정값(2026-08-08): 오버로드 없이 ['crown', 'ada-wong'],
    # isabel에게 +12%를 주면 ['isabel', 'crown'].
    without = a_run()
    with_overload = a_run(overload_on="isabel")
    powering_up_without, _ = _grants(without)
    powering_up_with, wake_up_with = _grants(with_overload)
    assert "isabel" not in powering_up_without[0]["targets"]
    assert powering_up_with[0]["targets"][0] == "isabel"
    assert wake_up_with[0]["targets"] == ["isabel"]


def test_miranda_never_targets_herself_in_a_five_unit_deck():
    # 원문이 "except caster"이고 후보가 넷이므로 그녀가 채울 빈자리가 없다.
    result = a_run(overload_on="ada-wong")
    powering_up, wake_up = _grants(result)
    for grant in powering_up + wake_up:
        assert "miranda-signature" not in grant["targets"]
