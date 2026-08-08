"""덱 5인 중 누가 미란다의 파워업!(버스트)과 웨이크업! 3번불릿을 받는가.

두 불릿 다 「최종 공격력 상위 N명(시전자 제외)」을 대상으로 하고, 그 순위는
판정 순간 살아 있는 공격력 버프까지 반영한 값이다 - 로스터의 표시 공격력만
보고는 답이 안 나온다. 그래서 이 모듈은 순위를 다시 구현하지 않고 엔진이 이미
한 판정의 기록(SquadContext.target_grants)을 읽는다.

좌석 순서는 evaluate_decks가 정한다. 유니온 탭이 채점에 쓰는 것과 같은
함수라, 이 화면이 보여주는 배치와 그 탭이 매기는 점수가 어긋날 수 없다.
"""
import math
from dataclasses import replace

from app.deck_evaluation import evaluate_decks
from app.deck_search import evaluate_deck
from app.models import OverloadOption
from app.overload_effects import max_atk_percent
from app.stat_assembly import load_stat_tables

MIRANDA_SLUGS = ("miranda", "miranda-signature")

# 미란다의 기록(캐스터로 이미 걸러진 뒤)에서 두 불릿을 가르는 스탯. 미란다의
# 다른 불릿들도 같은 스탯을 주지만(애장품 헬스업!의 자신 ATK, 웨이크업! 2번불릿의
# 자신 크확) 그것들은 top-N 룰이 아니라서 미란다의 기록에도 안 들어온다 - 그래서
# 이 두 줄로 충분하다.
POWERING_UP_STAT = "atk_percent"
WAKE_UP_CRIT_RATE_STAT = "crit_rate"

FAVORITE_ITEM_SLUG = "miranda-signature"

NO_THIRD_BULLET_NOTE = (
    "이 미란다는 애장품이 없어서 웨이크업!에 3번불릿이 아예 없어요 — "
    "크확 버프를 받는 니케가 없는 게 정상이에요."
)
NO_FULL_BURST_NOTE = "이 편성으로는 풀 버스트가 한 번도 열리지 않아요."

# 블라블라링크가 오버로드를 소수 둘째 자리로 보여주므로 그보다 가늘 이유가 없다.
THRESHOLD_PRECISION = 0.01
OVERLOAD_ATK_NAME = "공격력 증가"


def miranda_slug_in(slugs):
    """`slugs` 안의 미란다 슬러그, 없으면 None. 어느 빌드인지가 답을 바꾸므로
    (애장품이면 파워업! 2명 + 웨이크업!3, 아니면 파워업! 1명뿐) 존재 여부가
    아니라 슬러그 자체를 돌려준다."""
    for slug in slugs:
        if slug in MIRANDA_SLUGS:
            return slug
    return None


def _cycle_end_times(events):
    """풀 버스트가 닫히는 시각들. 사이클 k는 (직전 종료, 이번 종료] 구간이다."""
    return [event["time"] for event in events if event["type"] == "full_burst_end"]


def _first_targets(window, stat):
    for grant in window:
        if stat in grant["stats"]:
            return list(grant["targets"])
    return []


def cycles_from_result(result, miranda_slug):
    """시뮬 결과 하나를 사이클별 대상 목록으로 접는다."""
    grants = [g for g in result.get("target_grants", ())
              if g["caster"] == miranda_slug]
    cycles = []
    start = float("-inf")
    for index, end in enumerate(_cycle_end_times(result["events"]), start=1):
        window = [g for g in grants if start < g["time"] <= end]
        cycles.append({
            "index": index,
            "powering_up": _first_targets(window, POWERING_UP_STAT),
            "wake_up_crit_rate": _first_targets(window, WAKE_UP_CRIT_RATE_STAT),
        })
        start = end
    return cycles


def order_deck(deck_specs, boss, spec_index, alternatives=None):
    """유니온 탭과 같은 기준으로 고른 좌석 순서의 스펙 목록.

    `spec_index`는 로스터의 **모든** 로드 가능한 스펙이어야 한다({slug: NikkeSpec},
    load_roster의 출력). 엔진이 MODE_VARIANTS 좌석을 `deck_specs`에 없는 변형으로
    확정할 수 있어서, 다섯만 담은 색인으로는 되짚을 수 없다."""
    summary = evaluate_decks([deck_specs], [boss], alternatives=alternatives)["decks"][0]
    return [spec_index[slug] for slug in summary["deck"]]


def with_overload_atk(spec, percent):
    """`spec`의 오버로드 공격력 라인만 `percent`로 바꾼 사본. 다른 라인은 그대로
    둔다 - 이 탐색이 묻는 것은 공격력 하나를 움직였을 때의 답이다.

    0이면 라인을 아예 뺀다: 0%짜리 라인은 없는 라인과 같고, 값 0을 남기면
    overload_options_to_effects가 값 0짜리 효과를 하나 더 만든다."""
    others = [o for o in spec.overload_options if o.name != OVERLOAD_ATK_NAME]
    if percent > 0:
        others = others + [OverloadOption(name=OVERLOAD_ATK_NAME, value=percent)]
    return replace(spec, overload_options=others)


def current_overload_atk(spec):
    return sum(o.value for o in spec.overload_options if o.name == OVERLOAD_ATK_NAME)


def _smallest_true(predicate, false_at, true_at):
    """`predicate`가 참인 가장 작은 값. `false_at`은 거짓이 확인된 쪽,
    `true_at`은 참이 확인된 쪽이고 `false_at < true_at`이다.

    돌려주는 값은 **실제로 돌려서 참으로 확인된 쪽 끝을 올림한 것**이라, 반올림
    때문에 「모자란데 된다고 적힌」 값이 나오지 않는다. 술어는 단조라고 가정한다
    (설계문서 §5.2: 공격력을 순위로 나눠주는 규칙이 저장소에 없다)."""
    while true_at - false_at > THRESHOLD_PRECISION:
        middle = (false_at + true_at) / 2
        if predicate(middle):
            true_at = middle
        else:
            false_at = middle
    return math.ceil(true_at * 100) / 100


def overload_thresholds(ordered, boss, miranda_slug, cap):
    """좌석마다 「전 사이클 웨이크업!3을 받는」 오버로드 공격력의 경계.

    좌석 순서는 여기서 고정이다 - 값마다 배치를 다시 고르면 다른 덱의 답이 된다.
    시전자는 자기 대상이 될 수 없으므로 빠진다."""
    def receives_all(slug, percent):
        trial = [with_overload_atk(spec, percent) if spec.slug == slug else spec
                 for spec in ordered]
        result = evaluate_deck(trial, boss, collect_target_grants=True)
        cycles = cycles_from_result(result, miranda_slug)
        return bool(cycles) and all(slug in c["wake_up_crit_rate"] for c in cycles)

    rows = []
    for spec in ordered:
        if spec.slug == miranda_slug:
            continue
        current = current_overload_atk(spec)
        predicate = lambda percent, slug=spec.slug: receives_all(slug, percent)
        if predicate(current):
            # 지금 받고 있다 - 어디까지 떨어져도 유지되는가.
            threshold = 0.0 if predicate(0.0) else _smallest_true(predicate, 0.0, current)
            rows.append({"slug": spec.slug, "current_percent": current,
                         "kind": "keep", "threshold_percent": threshold})
            continue
        # 지금 못 받는다 - 상한에서도 못 받으면 오버로드로는 답이 없다.
        threshold = _smallest_true(predicate, current, cap) if predicate(cap) else None
        rows.append({"slug": spec.slug, "current_percent": current,
                     "kind": "gain", "threshold_percent": threshold})
    return rows


def miranda_target_report(deck_specs, boss, spec_index, alternatives=None):
    ordered = order_deck(deck_specs, boss, spec_index, alternatives)
    miranda_slug = miranda_slug_in(spec.slug for spec in ordered)
    if miranda_slug is None:
        raise ValueError("이 덱에는 미란다가 없다")

    result = evaluate_deck(ordered, boss, collect_target_grants=True)
    cycles = cycles_from_result(result, miranda_slug)

    notes = []
    if miranda_slug != FAVORITE_ITEM_SLUG:
        notes.append(NO_THIRD_BULLET_NOTE)
    if not cycles:
        notes.append(NO_FULL_BURST_NOTE)

    cap = max_atk_percent(load_stat_tables())
    thresholds = (overload_thresholds(ordered, boss, miranda_slug, cap)
                  if miranda_slug == FAVORITE_ITEM_SLUG and cycles else [])

    return {
        "seats": [{"slug": spec.slug, "burst_tier": spec.burst_tier} for spec in ordered],
        "miranda_slug": miranda_slug,
        "has_favorite_item": miranda_slug == FAVORITE_ITEM_SLUG,
        "cycles": cycles,
        "overload_thresholds": thresholds,
        "overload_atk_cap_percent": cap,
        "notes": notes,
    }
