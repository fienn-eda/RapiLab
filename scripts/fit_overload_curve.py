"""오버로드 효과 타입의 레벨→값 곡선을, 수집한 두 읽기를 대조해 유도한다.

언제 쓰나: 새 오버로드 효과가 `tables.json`에 없어서 `assemble_overload`가
드롭할 때, 또는 기존 곡선이 게임 패치로 움직였는지 확인할 때.

무엇을 대조하나 — 같은 로스터에 대한 서로 독립인 두 읽기다:

- `details.json`  (`node collect.js --details`) — blablalink API가 주는
  `{slot}_equip_option{n}_id`. 여기엔 **효과 타입과 레벨**이 있고 값은 없다.
- `roster.json`   (`node collect.js`) — ShiftyPad 페이지에서 읽은 **합계 %**.
  여기엔 값이 있고 레벨은 없다.

굴림이 하나뿐인 유닛은 그 합계가 곧 그 레벨의 값이므로 표를 **직접** 준다.
굴림이 여럿인 유닛은 그 표의 검증에 쓴다(합이 맞아야 한다). 두 읽기가
어긋나면 exit 1 — 그것이 라벨 개편이 로스터의 오버로드를 통째로 날린 것을
잡은 방식이다(2026-08-07, `tools/collect-blablalink/RECIPE.md` §f).

레벨을 값으로 바꾸는 규칙은 여기서 재구현하지 않는다. `decode_option`이
id를 (타입, 레벨)로 푸는 유일한 자리다.

예:
    python scripts/fit_overload_curve.py --type 6
    python scripts/fit_overload_curve.py --type 6 --name "명중률 증가"
"""
import argparse
import json
import pathlib
import sys

# 이 저장소의 콘솔은 cp949다. 한글과 em dash를 그대로 쓰면 인코딩 에러로 죽는데,
# 그건 결과가 아니라 표시의 문제이므로 죽는 대신 대체 문자로 흘린다. 출력을
# 눈으로 읽어야 할 때는 `python ... > out.txt` 후 UTF-8로 열 것.
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
sys.stderr.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "backend"))

from app.overload_decode import GEAR_SLOTS, decode_option  # noqa: E402

TOOLS = pathlib.Path("tools/collect-blablalink")
# 합계는 소수 둘째 자리까지 표시되므로, 굴림 여럿을 더한 예측과의 허용 오차는
# 굴림 수만큼의 반올림 폭이면 충분하다.
ROUNDING = 0.005


def rolls_by_resource_id(details, directory, effect_type):
    """{resource_id: [레벨, ...]} — 이 효과 타입의 굴림만."""
    rid_by_code = {d["name_code"]: d["resource_id"] for d in directory}
    out = {}
    for unit in details["character_details"]:
        rid = rid_by_code.get(unit.get("name_code"))
        if rid is None:
            continue
        levels = []
        for slot in GEAR_SLOTS:
            for n in (1, 2, 3):
                decoded = decode_option(unit.get(f"{slot}_equip_option{n}_id", 0))
                if decoded and decoded[0] == effect_type:
                    levels.append(decoded[1])
        if levels:
            out[rid] = sorted(levels)
    return out


def totals_by_resource_id(roster, name):
    """{resource_id: (이름, 합계%)} — 이 옵션 이름을 가진 유닛만.

    `name`이 None이면 이름을 하나로 좁힐 수 없으므로, 어떤 이름이 몇 유닛에
    붙어 있는지만 보고하고 끝낸다.
    """
    out = {}
    for unit in roster["units"]:
        for option in unit.get("overload") or []:
            if option["name"] == name:
                out[unit["resource_id"]] = (unit["name_en"], option["value"])
    return out


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--type", type=int, required=True, help="오버로드 효과 타입 번호")
    parser.add_argument("--name", help="스크래이프에 나타나는 옵션 이름(한글). 생략하면 후보를 나열한다")
    parser.add_argument("--details", type=pathlib.Path, default=TOOLS / "details.json")
    parser.add_argument("--roster", type=pathlib.Path, default=TOOLS / "roster.json")
    parser.add_argument("--directory", type=pathlib.Path, default=TOOLS / "nikke-directory.json")
    args = parser.parse_args()

    for path in (args.details, args.roster, args.directory):
        if not path.is_file():
            print(f"없는 파일: {path}\n"
                  f"  details.json  <- node collect.js --details\n"
                  f"  roster.json   <- node collect.js", file=sys.stderr)
            return 1

    details = json.loads(args.details.read_text(encoding="utf-8"))
    roster = json.loads(args.roster.read_text(encoding="utf-8"))
    directory = json.loads(args.directory.read_text(encoding="utf-8"))

    rolls = rolls_by_resource_id(details, directory, args.type)
    if not rolls:
        print(f"타입 {args.type}의 굴림이 이 로스터에 없다 — 곡선을 유도할 수 없다", file=sys.stderr)
        return 1

    if not args.name:
        counts = {}
        for unit in roster["units"]:
            for option in unit.get("overload") or []:
                counts[option["name"]] = counts.get(option["name"], 0) + 1
        print(f"타입 {args.type} 굴림 보유: {len(rolls)}유닛")
        print("스크래이프에 있는 옵션 이름(--name 으로 고를 것):")
        for n, c in sorted(counts.items(), key=lambda kv: -kv[1]):
            print(f"  {c:4}유닛  {n}")
        return 1

    totals = totals_by_resource_id(roster, args.name)
    only_ids = set(rolls) ^ set(totals)
    print(f"타입 {args.type} 굴림 {len(rolls)}유닛 · 「{args.name}」 합계 {len(totals)}유닛 "
          f"· 교집합 {len(set(rolls) & set(totals))}")
    if only_ids:
        # 한쪽에만 있으면 타입 번호와 이름이 같은 효과를 가리키지 않는다는 뜻이다.
        print(f"\n한쪽에만 있는 유닛 {len(only_ids)}건 — 타입과 이름이 안 맞는다:", file=sys.stderr)
        for rid in sorted(only_ids):
            where = "option_id만" if rid in rolls else "스크래이프만"
            print(f"  rid={rid} ({where})", file=sys.stderr)
        return 1

    curve = {}
    conflicts = []
    for rid, levels in rolls.items():
        if len(levels) != 1:
            continue
        level, value = levels[0], totals[rid][1]
        if level in curve and abs(curve[level] - value) > ROUNDING:
            conflicts.append(f"lv{level}: {curve[level]} vs {value} ({totals[rid][0]})")
        curve[level] = value

    print(f"\n단일 굴림이 직접 준 레벨 {len(curve)}종:")
    for level in sorted(curve):
        print(f"  lv{level:<3} {curve[level]:6.2f}")
    if conflicts:
        print("\n같은 레벨이 다른 값을 낸다:", file=sys.stderr)
        for c in conflicts:
            print(f"  {c}", file=sys.stderr)
        return 1

    # 다중 굴림은 표의 검증이자, 표에 없는 레벨의 유도다: 나머지 굴림이 전부
    # 알려진 레벨이면 남은 하나가 뺄셈으로 확정된다.
    print("\n다중 굴림 검증:")
    failures = derived = 0
    for rid, levels in sorted(rolls.items(), key=lambda kv: totals[kv[0]][0]):
        if len(levels) < 2:
            continue
        name, actual = totals[rid]
        unknown = [lv for lv in levels if lv not in curve]
        if len(unknown) == 1:
            known_sum = sum(curve[lv] for lv in levels if lv in curve)
            curve[unknown[0]] = round(actual - known_sum, 2)
            derived += 1
            print(f"  {name:26} lv{levels} -> lv{unknown[0]} = {curve[unknown[0]]:.2f} (뺄셈으로 유도)")
            continue
        if unknown:
            print(f"  {name:26} lv{levels} -- 미지 레벨 {unknown}, 건너뜀")
            continue
        predicted = round(sum(curve[lv] for lv in levels), 2)
        ok = abs(predicted - actual) <= ROUNDING * len(levels)
        failures += 0 if ok else 1
        print(f"  {name:26} lv{levels} 예측 {predicted:7.2f} 실제 {actual:7.2f} "
              f"{'OK' if ok else '어긋남'}")

    print(f"\n최종 곡선 (관측 {len(curve) - derived} + 유도 {derived} = {len(curve)}레벨):")
    print(json.dumps({str(lv): curve[lv] for lv in sorted(curve)}, ensure_ascii=False))
    missing = [lv for lv in range(1, 16) if lv not in curve]
    if missing:
        print(f"미관측 레벨 {missing} — `overload_value`의 산술 보간이 채운다"
              f"(다른 타입들도 같은 상태다).")

    if failures:
        print(f"\n다중 굴림 {failures}건이 어긋난다 — 곡선이 등차가 아니거나 "
              f"두 읽기가 다른 시점의 장비를 담고 있다.", file=sys.stderr)
        return 1
    print("\n두 읽기가 일치한다.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
