"""랭킹용 패스 캡이 순위를 바꾸는가, 그리고 얼마나 빨라지는가.

탐색 한 판의 비용은 (시뮬 수) x (시뮬당 고정점 패스 수)다. `SEARCH_SIM_BUDGET`이
앞 항을 잡고 `deck_search.RANKING_MAX_PASSES`가 뒤 항을 잡는데, 뒤 항을 자르는 것은
**근사**라서 값이 공짜가 아니다 - 이 스크립트가 그 값을 잰다.

`check_gauge_convergence.py`가 「고정점이 멈추는가」를 묻는다면 이쪽은 「멈추기 전에
끊어도 **순위가 같은가**」를 묻는다. 표본도 같은 것(cascade의 FIT_SAMPLE_DECKS,
FIT_SEED)을 써서 두 측정을 나란히 읽을 수 있게 한다.

**언제 쓰나:** `RANKING_MAX_PASSES`를 정하거나 다시 정할 때, 그리고 게이지 채움이
세는 것을 바꿔 패스 분포가 움직였을 때.

**합성 로스터로 재지 말 것.** 균일 스탯은 같은 티어 유닛을 서로 바꿔치기 가능하게
만드는데, 그게 바로 랭킹 오차를 숨기는 조건이다. 합성 30덱이 평균 오차 0.189%를
줬는데 실제 로스터 400덱은 0.560%였다 - **3배 과소평가**다. `--roster`는 기본이
동기화된 실물이고(`roster_fixture.py`), 그대로 두는 것이 맞다.

**어떻게 읽나 - 세 숫자가 캡의 생사를 가른다.**

- `exact`: 캡 안에서 진짜로 수렴한 덱 수. 이들에게 캡은 근사가 아니라 아무 일도
  아니다. 이 수가 높을수록 오차가 꼬리에만 갇힌다.
- `inversions`: 고정점 순위 대비 뒤바뀐 쌍의 수. 탐색이 실제로 지불하는 대가는
  평균 오차가 아니라 **이쪽**이다 - 총딜이 조금 틀려도 순서가 같으면 추천은 안
  바뀐다.
- `top-N kept`: 플레이어에게 보여 줄 상위 N을 놓쳤는가. 놓치지 않았다면 보고
  경로가 그들을 고정점까지 다시 재므로 **표시되는 숫자는 정확하다.**

기준선(캡 없음)에도 안 멈추는 덱이 있을 수 있다 - 그 덱의 「고정점」은 고정점이
아니라 상한에서 끊긴 값이고, 따로 세어 보고한다. 대조의 기준이 흔들리는 만큼은
결론에서 빼고 읽어야 한다.

Usage (any cwd):
    python3 scripts/measure_ranking_pass_cap.py
    python3 scripts/measure_ranking_pass_cap.py --caps 1,2,3 --decks 200
    python3 scripts/measure_ranking_pass_cap.py --element Iron --top-n 5
"""
import argparse
import collections
import sys
import time
import warnings
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.cascade import FIT_SAMPLE_DECKS, FIT_SEED  # noqa: E402
from app.deck_search import BossProfile, RANKING_MAX_PASSES, evaluate_deck  # noqa: E402
from app.raid_simulator import FullBurstConvergenceWarning  # noqa: E402
from app.surrogate import sample_feasible_combinations  # noqa: E402
from app.user_roster import load_roster  # noqa: E402
from roster_fixture import add_roster_argument, real_roster  # noqa: E402


def _score(decks, boss, max_passes):
    """각 덱의 총딜·패스 수와, 벽시계 시간·안 멈춘 덱 수.

    경고를 에러로 올리지 않고 덱마다 `record=True`로 받는다: 올리면 기준선이
    첫 정지 덱에서 끊겨 나머지를 못 잰다. 기본 필터가 (텍스트, 카테고리, 위치)로
    중복을 접으므로 `always`가 아니면 두 번째 덱부터 조용해진다.
    """
    totals, passes, stalled = [], [], 0
    t0 = time.perf_counter()
    for deck in decks:
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            result = evaluate_deck(list(deck), boss, max_passes=max_passes)
        if any(isinstance(w.message, FullBurstConvergenceWarning) for w in caught):
            stalled += 1
        totals.append(result["total_damage"])
        passes.append(result["full_burst_passes"]["passes"])
    return totals, passes, time.perf_counter() - t0, stalled


def _inversions(order, totals):
    """`order`(기준선 순위)의 쌍 중 `totals`에서 순서가 뒤집힌 쌍의 수.

    켄달 타우 거리다. 평균 오차보다 이쪽이 탐색이 지불하는 진짜 대가인 이유:
    총딜이 1% 틀려도 모든 덱이 같은 방향으로 틀리면 추천은 한 글자도 안 바뀐다.
    """
    bad = 0
    for i in range(len(order)):
        for j in range(i + 1, len(order)):
            a, b = order[i], order[j]
            if totals[a] <= totals[b]:
                bad += 1
    return bad


def _season_subset(specs, path):
    """제외 목록(한글 표시명, 한 줄에 하나, `#`는 주석)을 뺀 로스터.

    캡 값 자체는 **전체 로스터**로 정해야 한다 - 상수는 모두에게 나가고, 탐색이
    실제로 채점하는 덱은 전체 로스터에서 나온 풀이다. 이 부분집합은 그 다음
    질문에 답한다: 「내가 이번 시즌 실제로 쓸 유닛들 안에서도 캡이 편성을 안
    바꾸는가.」

    이름 -> 슬러그는 `app.display_names`가 유일한 출처이고, 「같은 캐릭터인가」는
    `deck_search.character_of`가 답한다. 접두사 문자열로 판정하면 안 된다:
    「브래디(지딜)」은 브래디와 **같은 캐릭터**(모드 변형)지만 「레이(가칭)」은
    「레이」와 **다른 캐릭터**다. 한 목록에 둘 다 들어 있었고, 접두사 규칙은 한쪽을
    반드시 틀린다.

    못 찾은 이름이 하나라도 있으면 멈춘다. 조용히 빠뜨리면 제외했다고 믿은 유닛이
    편성에 들어간 결과를 재게 되고, 그 결과는 아무것도 안 말한다.
    """
    import unicodedata

    from app.deck_search import character_of
    from app.display_names import DISPLAY_NAMES

    def norm(name):
        # 「은화: 택티컬 업」과 「엠마:택티컬 업」이 콜론 뒤 공백에서만 갈린다.
        return unicodedata.normalize("NFC", name).replace(" ", "").strip()

    by_name = {}
    for slug, korean in DISPLAY_NAMES.items():
        if korean:
            by_name.setdefault(norm(korean), []).append(slug)

    wanted = [line.strip()
              for line in Path(path).read_text(encoding="utf-8").splitlines()]
    wanted = [name for name in wanted if name and not name.startswith("#")]
    characters, missing = set(), []
    for name in wanted:
        slugs = by_name.get(norm(name))
        if not slugs:
            missing.append(name)
            continue
        characters.update(character_of(slug) for slug in slugs)
    if missing:
        raise SystemExit(f"제외 목록에서 못 찾은 이름 {len(missing)}개 - "
                         f"추측하지 않는다: {', '.join(missing)}")
    kept = [unit for unit in specs if character_of(unit.slug) not in characters]
    print(f"제외 목록 {len(wanted)}개 -> 캐릭터 {len(characters)}명; "
          f"로스터 {len(specs)} -> 시즌 셋 {len(kept)}유닛")
    return kept


def _allocation_ab(specs, boss, units, num_decks, caps):
    """추천 한 판을 캡 없이 / 캡 있이 돌려 벽시계와 **추천 결과 자체**를 대조한다.

    덱 표집이 답하는 것은 「점수의 순위가 같은가」지 「추천이 같은가」가 아니다.
    할당은 프루닝 · 캐스케이드 · 그리디 · 스왑 힐클라임을 거치며 매 단계가 랭킹
    점수를 읽으므로, 오차가 어디선가 증폭될 수도 상쇄될 수도 있다 - 그건 통째로
    돌려 봐야 안다.

    **직렬로** 돈다: 워커는 자기 인터프리터에서 `app.deck_search`를 다시
    import하므로 부모가 바꾼 `RANKING_MAX_PASSES`를 못 본다. 풀을 쓰면 「캡 없음」
    팔이 실제로는 캡을 쓰게 되어 A/B가 조용히 무너진다. 직렬이라 전체 로스터는
    몇 시간이므로 `units`개로 줄여 쓴다 - 전달 가능한 값은 절대 시간이 아니라
    **비율과 「추천이 같았는가」**다.
    """
    import random

    import app.deck_search as ds
    from app.deck_allocation import allocate_decks

    # 알파벳 앞쪽을 자르면 표본이 한쪽으로 쏠린다(그 함정에 한 번 빠졌다) -
    # 시드 고정 무작위 부분집합을 쓰고, 세 티어가 다 남았는지 확인한다.
    subset = random.Random(FIT_SEED).sample(specs, min(units, len(specs)))
    if {u.burst_tier for u in subset} < {1, 2, 3}:
        raise SystemExit(f"--end-to-end {units}: 부분집합에 티어가 다 없다 - 늘릴 것")

    shipped = ds.RANKING_MAX_PASSES
    print(f"\nend-to-end A/B: {len(subset)} units, {num_decks} decks, serial")

    def _run(cap):
        ds.RANKING_MAX_PASSES = cap
        t0 = time.perf_counter()
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", FullBurstConvergenceWarning)
            result = allocate_decks(subset, boss, num_decks=num_decks)
        return time.perf_counter() - t0, result

    try:
        base_t, base = _run(None)
    finally:
        ds.RANKING_MAX_PASSES = shipped
    base_damage = sum(d["total_damage"] for d in base["decks"])
    base_decks = [d["deck"] for d in base["decks"]]
    print(f"  {'uncapped':>10}: {base_t:7.1f}s   allocation damage {base_damage:,.0f}")

    for cap in caps:
        try:
            elapsed, result = _run(cap)
        finally:
            ds.RANKING_MAX_PASSES = shipped
        damage = sum(d["total_damage"] for d in result["decks"])
        decks = [d["deck"] for d in result["decks"]]
        mark = " <- shipped" if cap == shipped else ""
        print(f"  {f'cap {cap}':>10}: {elapsed:7.1f}s   allocation damage "
              f"{damage:,.0f}   speedup {base_t / elapsed:.2f}x{mark}")
        if decks == base_decks:
            print("      same recommendation, exactly")
            continue
        # 편성이 갈렸으면 총딜 차이가 그 대가다 - 두 총딜 모두 보고 경로(고정점)에서
        # 나오므로 비교 가능한 값이고, 부호도 뜻이 있다: 캡이 더 높은 총딜을 찾는
        # 일도 실제로 있다(탐색은 최적해를 보장하지 않는다).
        print(f"      DIFFERENT recommendation: "
              f"{(damage - base_damage) / base_damage * 100:+.3f}% damage")
        for i, (before_deck, after_deck) in enumerate(zip(base_decks, decks)):
            if before_deck != after_deck:
                print(f"      deck {i} uncapped: {before_deck}")
                print(f"      deck {i} capped:   {after_deck}")


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    add_roster_argument(parser)
    parser.add_argument("--caps", default=f"1,2,3,{RANKING_MAX_PASSES + 2}",
                        help=f"재 볼 패스 상한들 (기본은 1,2,3과 "
                             f"오늘 값+2; 오늘 값은 {RANKING_MAX_PASSES})")
    parser.add_argument("--decks", type=int, default=FIT_SAMPLE_DECKS,
                        help=f"표집할 덱 수 (기본 {FIT_SAMPLE_DECKS})")
    parser.add_argument("--top-n", type=int, default=5,
                        help="상위 몇 개를 「놓치면 안 되는 집합」으로 볼지 (기본 5)")
    parser.add_argument("--element", default="Wind",
                        choices=["Fire", "Water", "Wind", "Iron", "Electric"])
    parser.add_argument("--enemy-def", type=float, default=31784.0)
    parser.add_argument("--duration", type=float, default=180.0)
    parser.add_argument("--end-to-end", type=int, metavar="UNITS", default=None,
                        help="덱 표집 대신(또는 뒤이어) 추천 한 판을 캡 없이/있이 "
                             "돌려 벽시계와 추천 결과 자체를 대조한다. 직렬 A/B라 "
                             "로스터를 UNITS개로 줄여 쓴다")
    parser.add_argument("--end-to-end-decks", type=int, default=2,
                        help="--end-to-end가 배분할 덱 수 (기본 2)")
    parser.add_argument("--skip-sampling", action="store_true",
                        help="덱 표집 대조를 건너뛴다 (--end-to-end만 볼 때)")
    parser.add_argument("--exclude", metavar="PATH", default=None,
                        help="이번 시즌 안 쓸 니케의 한글 표시명 목록 파일 "
                             "(한 줄에 하나, #은 주석). 캡 값은 전체 로스터로 "
                             "정하고, 이 옵션은 「내 시즌 셋 안에서도 편성이 "
                             "같은가」를 확인할 때 쓴다")
    args = parser.parse_args()

    states = real_roster(args.roster)
    if states is None:
        raise SystemExit(f"no synced roster at {args.roster} - see roster_fixture.py")
    specs, _ = load_roster(states)
    boss = BossProfile(element=args.element, core_hittable=True,
                       enemy_def=args.enemy_def, fight_duration=args.duration)
    print(f"roster {len(specs)} usable; boss {args.element} {args.duration:.0f}s")
    if args.exclude:
        specs = _season_subset(specs, args.exclude)
    if args.skip_sampling:
        if args.end_to_end is None:
            raise SystemExit("--skip-sampling은 --end-to-end와 함께 쓸 때만 뜻이 있다")
        _allocation_ab(specs, boss, args.end_to_end, args.end_to_end_decks,
                       [int(c) for c in args.caps.split(",")])
        return
    decks = sample_feasible_combinations(specs, args.decks, seed=FIT_SEED)
    print(f"{len(decks)} sampled decks (seed {FIT_SEED})\n")

    base_totals, base_passes, base_t, base_stalled = _score(decks, boss, None)
    n = len(decks)
    hist = collections.Counter(base_passes)
    print(f"converged baseline: {base_t:.1f}s  ({base_t / n * 1000:.0f} ms/deck)")
    print(f"  passes: mean {sum(base_passes) / n:.2f}  median "
          f"{sorted(base_passes)[n // 2]}  max {max(base_passes)}")
    print("  histogram: " + "  ".join(f"{p}x{c}" for p, c in sorted(hist.items())))
    if base_stalled:
        print(f"  !! {base_stalled} deck(s) never converged - their 'fixed point' "
              f"is a ceiling cut, so that much of the comparison is soft")

    base_order = sorted(range(n), key=lambda i: -base_totals[i])
    base_top = set(base_order[:args.top_n])
    pairs = n * (n - 1) // 2
    for cap in [int(c) for c in args.caps.split(",")]:
        totals, passes, t, _ = _score(decks, boss, cap)
        exact = sum(1 for i in range(n) if base_passes[i] <= cap)
        err = [abs(totals[i] - base_totals[i]) / base_totals[i] * 100
               for i in range(n) if base_totals[i]]
        order = sorted(range(n), key=lambda i: -totals[i])
        moved = max(abs(order.index(d) - rank) for rank, d in enumerate(base_order))
        mark = "  <- shipped" if cap == RANKING_MAX_PASSES else ""
        print(f"\ncap {cap}:{mark} {t:.1f}s ({t / n * 1000:.0f} ms/deck)  "
              f"speedup {base_t / t:.2f}x  mean passes {sum(passes) / n:.2f}")
        print(f"  exact (converged inside the cap): {exact}/{n} "
              f"({exact / n * 100:.0f}%)")
        print(f"  damage error: mean {sum(err) / len(err):.3f}%  max {max(err):.3f}%")
        print(f"  top-1 kept: {order[0] == base_order[0]}   "
              f"top-{args.top_n} set kept: {set(order[:args.top_n]) == base_top}")
        print(f"  inversions {_inversions(base_order, totals)}/{pairs}   "
              f"largest rank move {moved}")

    if args.end_to_end is not None:
        _allocation_ab(specs, boss, args.end_to_end, args.end_to_end_decks,
                       [int(c) for c in args.caps.split(",")])


if __name__ == "__main__":
    main()
