"""버스트 게이지 고정점이 실제로 멈추는가 - 표본 덱으로 훑는다.

게이지 채움 시간은 `simulate_raid`의 세 번째 수렴량이다(`burst_gauge.fill_times`).
게이지가 사이클 길이를 바꾸고 사이클 길이가 재장전·예열 위치를 바꿔 다시 게이지를
바꾸는 고리라, 어떤 덱에서는 값이 격자 두 칸 사이를 오가며 **영영 안 멈춘다**.
그런 덱은 `MAX_FULL_BURST_PASSES`(32)를 다 쓰고 `FullBurstConvergenceWarning`과
함께 **고정점이 아닌 total_damage**를 돌려준다 - 조용히 틀린 점수다.

`check_sampled_decks_simulate.py`가 「이 덱을 시뮬할 수 있는가」를 묻는다면 이쪽은
「멈추는가, 몇 패스에」를 묻는다. 표본은 같은 것(cascade의 FIT_SAMPLE_DECKS)을 쓴다.

**언제 쓰나:** `burst_gauge.fill_times`가 세는 것을 바꿀 때마다 - 새 충전원(아군
소모탄 트리거·선언된 타격 수), 에너지 배율, `GAUGE_QUANTUM_SEC` 조정. 충전이
빨라지면 사이클이 짧아지고, 그 고리가 어느 덱을 진동으로 밀어 넣는지는 돌려 봐야
안다. 2026-08-21 측정: 격자 0.05에서 400덱 중 18덱이 안 멈췄고 0.1에서 3덱이다.

**어떻게 읽나 - 덱은 세 갈래로 갈린다.**

- `converged`: 패스가 자기 입력을 재생산했다. 진짜 고정점이다.
- `damped`: 격자 한 칸짜리 **주기 2 진동**을 `simulate_raid`가 감지해 사이클마다
  느린 쪽으로 감쇠하고 한 패스 더 돌려 답을 정했다. 고정점은 **아니고** 오차가
  격자 한 칸 안이다. 이 수가 **늘면** 봐야 한다 - 자연 수렴하던 덱이 감쇠 경로로
  넘어갔다면 가드가 헐거워진 것이다.
- `stalled`: 감쇠로도 안 잡혔다(주기 3 이상, 또는 값이 격자 한 칸보다 크게 뛰어
  감쇠 가드가 걸린 경우). 그 덱들은 조용히 틀린 점수를 받고 있다.

격자를 굵게 하는 것이 언제나 답은 아니다 - 0.2·0.25에서 다시 늘어난다. 패스
히스토그램은 비용도 알려준다: 게이지가 한 사이클도 안 무는 덱은 2패스에 멈추고,
무는 덱은 무는 사이클 수만큼 산다.

Usage (any cwd):
    python3 scripts/check_gauge_convergence.py
    python3 scripts/check_gauge_convergence.py --rounds 4 --element Iron
    python3 scripts/check_gauge_convergence.py --quantum 0.05   # 격자를 재 보기

안 멈춘 덱이 하나라도 있으면 종료 코드 1.
"""
import argparse
import collections
import sys
import warnings
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app import burst_gauge  # noqa: E402
from app.cascade import FIT_SAMPLE_DECKS, FIT_SEED  # noqa: E402
from app.deck_search import BossProfile, evaluate_deck  # noqa: E402
from app.surrogate import sample_feasible_combinations  # noqa: E402
from app.user_roster import load_roster  # noqa: E402
from roster_fixture import add_roster_argument, real_roster  # noqa: E402


def _round_roster(specs, index, rounds):
    """라운드 0은 로스터 전체, 이후는 결정적으로 한 조각씩 뺀다 - 표본을 다시
    뽑아 다른 조합을 덮으려는 것뿐이다(`check_sampled_decks_simulate.py`와 같은 규칙)."""
    if index == 0:
        return specs, "full roster"
    ordered = sorted(specs, key=lambda unit: unit.slug)
    width = max(1, len(ordered) // rounds)
    dropped = {unit.slug for unit in ordered[(index - 1) * width:index * width]}
    return ([unit for unit in specs if unit.slug not in dropped],
            f"minus {sorted(dropped)[0]}..{sorted(dropped)[-1]} ({len(dropped)})")


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    add_roster_argument(parser)
    parser.add_argument("--rounds", type=int, default=2,
                        help="표본을 다시 뽑을 로스터 변형 수 (기본 2); "
                             "라운드 0은 로스터 전체")
    parser.add_argument("--element", default="Wind",
                        choices=["Fire", "Water", "Wind", "Iron", "Electric"])
    parser.add_argument("--enemy-def", type=float, default=31784.0)
    parser.add_argument("--duration", type=float, default=180.0)
    parser.add_argument("--quantum", type=float, default=None,
                        help=f"양자화 격자를 이 값으로 덮어쓴다 "
                             f"(기본 {burst_gauge.GAUGE_QUANTUM_SEC}); 격자를 바꾸면 "
                             f"수렴이 어떻게 달라지는지 보려는 용도")
    args = parser.parse_args()

    states = real_roster(args.roster)
    if states is None:
        raise SystemExit(f"no synced roster at {args.roster} - see roster_fixture.py")
    if args.quantum is not None:
        burst_gauge.GAUGE_QUANTUM_SEC = args.quantum
    specs, _ = load_roster(states)
    boss = BossProfile(element=args.element, core_hittable=True,
                       enemy_def=args.enemy_def, fight_duration=args.duration)
    print(f"roster {len(specs)} usable; boss {args.element} {args.duration:.0f}s; "
          f"{args.rounds} rounds x {FIT_SAMPLE_DECKS} sampled decks "
          f"(seed {FIT_SEED}); grid {burst_gauge.GAUGE_QUANTUM_SEC}\n")

    # 경고를 에러로 올려 잡는다: `FullBurstConvergenceWarning`은 파이썬 기본
    # 필터가 (텍스트, 카테고리, 위치)로 접어 버려, 그냥 두면 두 번째 덱부터
    # 조용해진다 - 세는 것이 목적인 여기서는 정확히 반대가 필요하다.
    warnings.simplefilter("error")
    passes = collections.Counter()
    damped = []
    stalled = []
    for index in range(args.rounds):
        subset, label = _round_roster(specs, index, args.rounds)
        combos = sample_feasible_combinations(subset, FIT_SAMPLE_DECKS, seed=FIT_SEED)
        raised = 0
        for combo in combos:
            slugs = [unit.slug for unit in combo]
            try:
                result = evaluate_deck(list(combo), boss)
            except Warning:
                raised += 1
                stalled.append(slugs)
                print(f"  STALLED {slugs}")
                continue
            except Exception as exc:  # noqa: BLE001 - 시뮬 자체가 깨진 것도 보고한다
                raised += 1
                print(f"  RAISED  {slugs}\n    {type(exc).__name__}: {exc}")
                continue
            entry = result["full_burst_passes"]
            passes[entry["passes"]] += 1
            if entry.get("gauge_oscillation_damped"):
                damped.append(slugs)
                print(f"  DAMPED  {slugs} ({entry['passes']} passes)")
        print(f"round {index} ({label}): {len(combos)} decks, {raised} did not converge")

    # 히스토그램·평균은 답을 낸 덱 전부(자연 수렴 + 감쇠)를 센다 - 비용은 감쇠
    # 덱도 똑같이 지불한다. 「몇 덱이 진짜 고정점인가」는 그 아래 줄이 따로 답한다.
    answered = sum(passes.values())
    if answered:
        counts = sorted(passes.items())
        ordered = [n for n, count in counts for _ in range(count)]
        mean = sum(n * count for n, count in counts) / answered
        print(f"\npasses: {dict(counts)}")
        print(f"answered {answered}: two-pass {100 * passes[2] / answered:.0f}%, "
              f"median {ordered[answered // 2]}, mean {mean:.2f}, max {max(passes)}")
    sampled = answered + len(stalled)
    print(f"of {sampled} sampled decks: {answered - len(damped)} converged, "
          f"{len(damped)} settled by damping a period-2 oscillation, "
          f"{len(stalled)} never settled at all")
    return 1 if stalled else 0


if __name__ == "__main__":
    sys.exit(main())
