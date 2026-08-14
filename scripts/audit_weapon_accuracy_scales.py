"""`accuracy`의 탄착군 표 둘을 수집 데이터와 대조한다.

언제 쓰나: 로스터를 재동기화한 뒤, 새 니케를 온보딩한 뒤, 그리고 탄착군이
관련된 값을 만지기 전에. 표는 손으로 적혀 있고 데이터는 갱신되므로 둘이
갈라지는 날이 온다.

무엇을 보나: `data/shiftypad/raw/*.json`의 `shot_detail`에서 무기 클래스별로
`(start_accuracy_circle_scale, end_accuracy_circle_scale,
accuracy_change_pershot)` 세 값을 모아 —

- 클래스 안에서 셋이 균일한가
- `end`가 `WEAPON_SPREAD_DIAMETER`와 같은가 (수렴값)
- start != end인 클래스가 `SPREAD_CONVERGENCE`에 정확히 그 `(start, 발당)`으로
  올라 있고, start == end인 클래스는 거기 없는가

를 본다. 어긋나면 exit 1. 수렴 여부를 데이터가 정하게 두는 것이 요점이다 —
어느 클래스가 수렴하는지를 여기 손으로 적으면 새로 수렴하기 시작한 클래스를
이 스크립트가 못 본다.
"""
import argparse
import collections
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "backend"))

from app.accuracy import SPREAD_CONVERGENCE, WEAPON_SPREAD_DIAMETER  # noqa: E402


def _shot_detail(node):
    """이 JSON 어딘가에 있는 무기 shot 레코드, 없으면 None."""
    if isinstance(node, dict):
        if "weapon_type" in node and "start_accuracy_circle_scale" in node:
            return node
        for value in node.values():
            found = _shot_detail(value)
            if found is not None:
                return found
    elif isinstance(node, list):
        for value in node:
            found = _shot_detail(value)
            if found is not None:
                return found
    return None


def collect(raw_dir):
    """{무기: {(start, end, 발당): [파일명, ...]}} - 관측된 조합과 그 출처."""
    observed = collections.defaultdict(lambda: collections.defaultdict(list))
    for path in sorted(raw_dir.glob("*.json")):
        detail = _shot_detail(json.loads(path.read_text(encoding="utf-8")))
        if detail is None:
            continue
        shape = (float(detail["start_accuracy_circle_scale"]),
                 float(detail["end_accuracy_circle_scale"]),
                 float(detail.get("accuracy_change_pershot", 0.0)))
        observed[detail["weapon_type"]][shape].append(path.stem)
    return observed


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--raw-dir", type=pathlib.Path,
                        default=pathlib.Path("data/shiftypad/raw"),
                        help="수집된 ShiftyPad raw 번들 디렉터리")
    args = parser.parse_args()

    if not args.raw_dir.is_dir():
        print(f"수집 데이터가 없다: {args.raw_dir}", file=sys.stderr)
        return 1

    observed = collect(args.raw_dir)
    if not observed:
        print(f"{args.raw_dir}에서 shot_detail을 하나도 못 읽었다", file=sys.stderr)
        return 1

    problems = []
    for weapon in sorted(observed):
        shapes = observed[weapon]
        converged = WEAPON_SPREAD_DIAMETER.get(weapon)
        units = sum(len(v) for v in shapes.values())
        print(f"{weapon:4} {units:3}유닛  관측 start/end/발당 {sorted(shapes)}  "
              f"수렴값 표 {converged}  수렴 표 {SPREAD_CONVERGENCE.get(weapon)}")
        if converged is None:
            problems.append(f"{weapon}: 표에 없는 무기 클래스가 데이터에 있다")
            continue
        if len(shapes) > 1:
            split = {s: sorted(u)[:3] for s, u in shapes.items()}
            problems.append(f"{weapon}: 클래스 안에서 탄착군이 갈린다 - {split}")
            continue
        start, end, per_shot = next(iter(shapes))
        if end != converged:
            problems.append(f"{weapon}: 데이터의 수렴값은 {end}인데 표는 {converged}")
        if start == end:
            if weapon in SPREAD_CONVERGENCE:
                problems.append(
                    f"{weapon}: 데이터는 탄창 안에서 안 좁아지는데 "
                    f"SPREAD_CONVERGENCE에 {SPREAD_CONVERGENCE[weapon]}로 올라 있다")
            if per_shot:
                problems.append(
                    f"{weapon}: start == end인데 발당 변화가 {per_shot}이다")
        elif SPREAD_CONVERGENCE.get(weapon) != (start, per_shot):
            problems.append(
                f"{weapon}: 데이터는 ({start}, 발당 {per_shot})로 좁아지는데 "
                f"SPREAD_CONVERGENCE는 {SPREAD_CONVERGENCE.get(weapon)}")

    for weapon in sorted(set(WEAPON_SPREAD_DIAMETER) - set(observed)):
        print(f"{weapon:4}   0유닛  (수집 데이터에 없음 - 표만 존재)")
    for weapon in sorted(set(SPREAD_CONVERGENCE) - set(observed)):
        problems.append(f"{weapon}: SPREAD_CONVERGENCE에 있는데 수집 데이터에 없다")

    if problems:
        print("\n어긋남:", file=sys.stderr)
        for line in problems:
            print(f"  {line}", file=sys.stderr)
        return 1
    print("\naccuracy의 탄착군 표 둘 다 수집 데이터와 일치한다.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
