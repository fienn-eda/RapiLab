"""`accuracy.WEAPON_SPREAD_DIAMETER`를 수집 데이터와 대조한다.

언제 쓰나: 로스터를 재동기화한 뒤, 새 니케를 온보딩한 뒤, 그리고 탄착군이
관련된 값을 만지기 전에. 표는 손으로 적혀 있고 데이터는 갱신되므로 둘이
갈라지는 날이 온다.

무엇을 보나: `data/shiftypad/raw/*.json`의 `shot_detail`에서 무기 클래스별
`start_accuracy_circle_scale`(MG는 `end_accuracy_circle_scale`)을 모아,
클래스 안에서 균일한지와 표의 값과 같은지를 본다. 어긋나면 exit 1.

MG를 다르게 보는 이유는 그것만 탄창 안에서 좁아지기 때문이다
(start 250 -> end 10, 발당 -7). 엔진은 수렴값만 모델한다.
"""
import argparse
import collections
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "backend"))

from app.accuracy import WEAPON_SPREAD_DIAMETER  # noqa: E402

# MG는 탄창 안에서 좁아지므로 표가 담은 것은 수렴값(`end`)이다.
CONVERGING_WEAPONS = {"MG"}


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
    """{무기: {지름: [파일명, ...]}} - 클래스별로 관측된 지름과 그 출처."""
    observed = collections.defaultdict(lambda: collections.defaultdict(list))
    for path in sorted(raw_dir.glob("*.json")):
        detail = _shot_detail(json.loads(path.read_text(encoding="utf-8")))
        if detail is None:
            continue
        weapon = detail["weapon_type"]
        field = ("end_accuracy_circle_scale" if weapon in CONVERGING_WEAPONS
                 else "start_accuracy_circle_scale")
        observed[weapon][float(detail[field])].append(path.stem)
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
        diameters = observed[weapon]
        expected = WEAPON_SPREAD_DIAMETER.get(weapon)
        units = sum(len(v) for v in diameters.values())
        print(f"{weapon:4} {units:3}유닛  관측 {sorted(diameters)}  표 {expected}")
        if expected is None:
            problems.append(f"{weapon}: 표에 없는 무기 클래스가 데이터에 있다")
            continue
        if len(diameters) > 1:
            spread = {d: sorted(u)[:3] for d, u in diameters.items()}
            problems.append(f"{weapon}: 클래스 안에서 지름이 갈린다 - {spread}")
            continue
        only = next(iter(diameters))
        if only != expected:
            problems.append(f"{weapon}: 데이터는 {only}인데 표는 {expected}")

    for weapon in sorted(set(WEAPON_SPREAD_DIAMETER) - set(observed)):
        print(f"{weapon:4}   0유닛  (수집 데이터에 없음 - 표만 존재)")

    if problems:
        print("\n어긋남:", file=sys.stderr)
        for line in problems:
            print(f"  {line}", file=sys.stderr)
        return 1
    print("\naccuracy.WEAPON_SPREAD_DIAMETER는 수집 데이터와 일치한다.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
