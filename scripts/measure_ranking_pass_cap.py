"""랭킹용 패스 캡이 순위를 바꾸는가, 그리고 얼마나 빨라지는가.

탐색 한 판의 비용은 (시뮬 수) x (시뮬당 고정점 패스 수)다. `SEARCH_SIM_BUDGET`이
앞 항을 잡고 `deck_search.RANKING_MAX_PASSES`가 뒤 항을 잡는데, 뒤 항을 자르는 것은
**근사**라서 값이 공짜가 아니다 - 이 스크립트가 그 값을 잰다.

`check_gauge_convergence.py`가 「고정점이 멈추는가」를 묻는다면 이쪽은 「멈추기 전에
끊어도 **순위가 같은가**」를 묻는다. 표본도 같은 것(cascade의 FIT_SAMPLE_DECKS,
FIT_SEED)을 써서 두 측정을 나란히 읽을 수 있게 한다.

**언제 쓰나:** `RANKING_MAX_PASSES`를 정하거나 다시 정할 때, 그리고 게이지 채움이
세는 것을 바꿔 패스 분포가 움직였을 때. 분포는 로스터와 보스에 강하게 의존한다 -
표본 셋에서 평균 패스가 3.13 / 5.88 / 7.41로 갈렸다. 그러니 **캡 값을 계획에 박기
전에 자기 로스터로 한 번 돌릴 것.**

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
    args = parser.parse_args()

    states = real_roster(args.roster)
    if states is None:
        raise SystemExit(f"no synced roster at {args.roster} - see roster_fixture.py")
    specs, _ = load_roster(states)
    boss = BossProfile(element=args.element, core_hittable=True,
                       enemy_def=args.enemy_def, fight_duration=args.duration)
    decks = sample_feasible_combinations(specs, args.decks, seed=FIT_SEED)
    print(f"roster {len(specs)} usable; boss {args.element} {args.duration:.0f}s; "
          f"{len(decks)} sampled decks (seed {FIT_SEED})\n")

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


if __name__ == "__main__":
    main()
