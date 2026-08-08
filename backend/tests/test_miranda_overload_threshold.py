"""어떤 니케가 웨이크업!3을 받으려면 오버로드 공격력이 얼마나 필요한가.

닫힌형(격차 나누기 표시공격력)은 필요치를 과대평가한다 - 오버로드가 오르면
파워업!(B1 시전) 판정도 같이 움직여, 상위 N에 새로 들어가는 계단이 생기기
때문이다. 그래서 실제로 돌려서 이진탐색한다. 이 파일이 보는 것은 「보고된
값에서 실제로 받고, 한 눈금 아래에서는 못 받는가」다.
"""
from app.deck_search import BossProfile
from app.miranda_targets import (THRESHOLD_PRECISION, cycles_from_result,
                                 miranda_target_report, order_deck,
                                 with_overload_atk)
from app.deck_search import evaluate_deck
from app.models import OverloadOption, SkillLevels, UserNikkeState
from app.overload_effects import max_atk_percent
from app.stat_assembly import load_stat_tables
from app.user_roster import load_roster

MAXED = SkillLevels(skill1=10, skill2=10, burst=10)
BOSS = BossProfile(fight_duration=180.0)
DECK = ["miranda-signature", "crown", "ada-wong", "cinderella", "isabel"]


def a_state(slug, atk, overload_atk=0.0):
    options = ([OverloadOption(name="공격력 증가", value=overload_atk)]
               if overload_atk else [])
    return UserNikkeState(
        character_slug=slug, level=400, hp=500_000.0, atk=atk, def_=10_000.0,
        skill_levels=MAXED, overload_options=options,
    )


def a_report(atk_by_slug, overload_by_slug=None):
    overload_by_slug = overload_by_slug or {}
    states = [a_state(slug, atk_by_slug[slug], overload_by_slug.get(slug, 0.0))
              for slug in DECK]
    specs, _excluded = load_roster(states)
    spec_index = {spec.slug: spec for spec in specs}
    deck_specs = [spec_index[slug] for slug in DECK]
    return miranda_target_report(deck_specs, BOSS, spec_index), spec_index, deck_specs


def receives_all_cycles(spec_index, deck_specs, slug, percent):
    """`slug`의 오버로드 공격력을 `percent`로 놓고 돌렸을 때 전 사이클
    웨이크업!3을 받는가."""
    ordered = order_deck(deck_specs, BOSS, spec_index)
    trial = [with_overload_atk(spec, percent) if spec.slug == slug else spec
             for spec in ordered]
    result = evaluate_deck(trial, BOSS, collect_target_grants=True)
    cycles = cycles_from_result(result, "miranda-signature")
    return bool(cycles) and all(slug in c["wake_up_crit_rate"] for c in cycles)


# ada-wong의 우위는 오버로드 상한(58.52%) 안에서 뒤집을 수 있을 만큼만 둔다.
# 필요치는 표시 공격력 격차를 단순히 나눈 값보다 훨씬 크다 - 경계가 「전
# 사이클에서 받는가」이고 사이클마다 이기는 쪽이 갈리므로 가장 빡센 사이클이
# 값을 정하기 때문이다. 120,000이면 교차점이 62~76%로 상한 밖이라 도달 가능한
# gain 후보가 하나도 없고, 그러면 「필요치가 실제로 통한다」를 잴 수가 없다.
# 실측(2026-08-08) 105,000에서: crown 49.03% · cinderella 35.48% · isabel 49.03%.
ATK = {"miranda-signature": 100_000.0, "crown": 100_000.0,
       "ada-wong": 105_000.0, "cinderella": 100_000.0, "isabel": 100_000.0}


def by_slug(thresholds):
    return {t["slug"]: t for t in thresholds}


def test_the_recipient_gets_a_keep_threshold_and_the_others_a_gain_one():
    report, _index, _deck = a_report(ATK)
    thresholds = by_slug(report["overload_thresholds"])
    # 미란다는 자기 대상이 될 수 없으므로 목록에 없다.
    assert "miranda-signature" not in thresholds
    assert set(thresholds) == {"crown", "ada-wong", "cinderella", "isabel"}
    winner = report["cycles"][0]["wake_up_crit_rate"][0]
    assert thresholds[winner]["kind"] == "keep"
    for slug, entry in thresholds.items():
        if slug != winner:
            assert entry["kind"] == "gain"


def test_a_gain_threshold_is_a_value_that_actually_works():
    report, index, deck = a_report(ATK)
    thresholds = by_slug(report["overload_thresholds"])
    loser = next(t for t in thresholds.values()
                 if t["kind"] == "gain" and t["threshold_percent"] is not None)
    at = loser["threshold_percent"]
    assert receives_all_cycles(index, deck, loser["slug"], at)
    assert not receives_all_cycles(index, deck, loser["slug"],
                                   at - 2 * THRESHOLD_PRECISION)


def test_a_keep_threshold_is_the_edge_of_still_receiving():
    # 받고 있는 유닛이 표시 공격력만으로도 이미 1위면 오버로드를 0으로 내려도
    # 계속 받아 경계가 0이 되고, 그러면 「한 눈금 아래에서는 놓친다」가 아무것도
    # 재지 않는다. 경계를 재려면 오버로드가 있어야만 1위인 배치여야 한다 -
    # ada-wong의 표시 공격력을 나머지보다 낮춰 두고 오버로드로 뒤집는다.
    # 실측(2026-08-08): 경계 7.4%.
    report, index, deck = a_report({**ATK, "ada-wong": 95_000.0},
                                   overload_by_slug={"ada-wong": 40.0})
    thresholds = by_slug(report["overload_thresholds"])
    keeper = next(t for t in thresholds.values() if t["kind"] == "keep")
    floor = keeper["threshold_percent"]
    assert floor > 0, "경계가 0이면 아래 두 줄이 아무것도 재지 않는다"
    assert receives_all_cycles(index, deck, keeper["slug"], floor)
    assert not receives_all_cycles(index, deck, keeper["slug"],
                                   floor - 2 * THRESHOLD_PRECISION)


def test_an_unreachable_unit_reports_no_threshold():
    # 다른 넷보다 압도적으로 낮은 공격력이면 상한(58.52%)으로도 못 넘는다.
    atk = dict(ATK)
    atk["isabel"] = 10_000.0
    report, index, deck = a_report(atk)
    thresholds = by_slug(report["overload_thresholds"])
    assert thresholds["isabel"]["threshold_percent"] is None
    cap = max_atk_percent(load_stat_tables())
    assert not receives_all_cycles(index, deck, "isabel", cap)


def test_current_percent_is_read_off_the_roster():
    report, _index, _deck = a_report(ATK, overload_by_slug={"crown": 7.25})
    thresholds = by_slug(report["overload_thresholds"])
    assert thresholds["crown"]["current_percent"] == 7.25
    assert thresholds["isabel"]["current_percent"] == 0.0


def test_the_base_build_has_no_thresholds_at_all():
    # 애장품이 없으면 웨이크업!3이 스킬에 없으므로 넘어설 경계가 없다.
    deck = ["miranda", "crown", "ada-wong", "cinderella", "isabel"]
    states = [a_state(slug, ATK.get(slug, 100_000.0)) for slug in deck]
    specs, _excluded = load_roster(states)
    spec_index = {spec.slug: spec for spec in specs}
    report = miranda_target_report([spec_index[s] for s in deck], BOSS, spec_index)
    assert report["overload_thresholds"] == []


def test_with_overload_atk_replaces_only_the_atk_line():
    states = [a_state("crown", 100_000.0, 5.0)]
    specs, _excluded = load_roster(states)
    spec = specs[0]
    spec.overload_options.append(OverloadOption(name="크리티컬 확률 증가", value=3.0))
    swapped = with_overload_atk(spec, 12.0)
    names = [o.name for o in swapped.overload_options]
    assert names.count("공격력 증가") == 1
    assert "크리티컬 확률 증가" in names
    atk_line = next(o for o in swapped.overload_options if o.name == "공격력 증가")
    assert atk_line.value == 12.0
    # 0을 주면 라인이 통째로 사라진다 - 0%짜리 라인은 없는 라인과 같다.
    assert all(o.name != "공격력 증가" for o in with_overload_atk(spec, 0.0).overload_options)
