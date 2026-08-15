"""`attack_rate`의 연사 표 셋을 수집 데이터와 대조한다.

언제 쓰나: 로스터를 재동기화한 뒤, 새 니케를 온보딩한 뒤, 그리고 연사가 관련된
값을 만지기 전에. 표는 손으로 적혀 있고 데이터는 갱신되므로 둘이 갈라지는 날이
온다.

무엇을 보나: `data/shiftypad/raw/*.json`의 `shot_detail.rate_of_fire`(**분당**
발수)를 인코딩된 슬러그마다 찾아 —

- 무기군의 rpm이 클래스 안에서 균일하고 `RATE_OF_FIRE_60FPS`와 맞는가
- 클래스 rpm과 다른 유닛이 `ROUNDS_PER_MINUTE`에 정확히 그 값으로 올라 있는가
- 표에 있는 슬러그가 실제로 클래스와 다른가 (같아졌으면 표에서 빠져야 한다)

를 본다. 어긋나면 exit 1.

**두 번째 항목이 이 스크립트의 존재 이유다.** 질: 발렌타인은 9발짜리 AR을
150발/분으로 쏘는데(Fienn 실측 24±1프레임/발) 엔진은 클래스 상수 720을 줘서
평타가 4.8배였다. 아무도 이 필드를 안 보고 있었기 때문에 조용히 통과했고, 같은
모양의 유닛이 온보딩되면 또 통과한다.

차지 무기(RL/SR)도 같은 세 가지를 보되 표는 `CHARGE_ROUNDS_PER_MINUTE`다. 그쪽의
`rate_of_fire`는 케이던스가 아니라 **바닥값**이다 — 차지가 0이 돼도 남는 가장 짧은
발 간격이고, 멈춤이 없는 유닛에게만 걸린다. 그래서 클래스 기본값(60)과 엔진 상수를
맞춰 보는 검사는 차지 무기엔 돌리지 않는다: 스칼렛: 블랙 섀도우가 그 기본값을
가진 채 0.7325초마다 쏘므로 60은 바닥값이 아니다.

테스트가 아니라 스크립트인 이유: `data/`는 gitignore라 워크트리나 CI에서 없을 수
있고, 조건부 테스트로 만들면 데이터가 없는 곳에서 조용히 skip된다.
"""
import argparse
import collections
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "backend"))

from app.attack_rate import (CHARGE_ROUNDS_PER_MINUTE, CHARGE_WEAPONS,  # noqa: E402
                             RATE_OF_FIRE_60FPS, ROUNDS_PER_MINUTE,
                             rounds_per_second)
from app.skill_rules.registry import ENCODED_SLUGS  # noqa: E402
from audit_core_damage_rate import RAW_NAME_ALIASES, character_name  # noqa: E402


def collect(raw_dir):
    """{영문 이름: (rid, 무기, 분당 발수)} - 수집된 번들이 적은 연사.

    MG의 `rate_of_fire`는 예열 램프의 시작값이라 공칭 최대는
    `end_rate_of_fire`다. 그것을 안 읽으면 MG 전원이 1발/초로 읽힌다.
    """
    observed = {}
    for path in sorted(raw_dir.glob("*.json")):
        bundle = json.loads(path.read_text(encoding="utf-8"))
        name = bundle["directory"]["name_localkey"]["name"].strip()
        detail = bundle["detail"]["shot_detail"]
        weapon = detail["weapon_type"]
        field = "end_rate_of_fire" if weapon == "MG" else "rate_of_fire"
        observed[name] = (path.stem, weapon, float(detail[field]))
    return observed


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--raw-dir", type=pathlib.Path,
                        default=pathlib.Path("data/shiftypad/raw"),
                        help="수집된 ShiftyPad raw 번들 디렉터리")
    args = parser.parse_args()

    if not args.raw_dir.is_dir():
        print(f"수집 데이터가 없다: {args.raw_dir}", file=sys.stderr)
        return 1
    observed = collect(args.raw_dir)
    if not observed:
        print(f"{args.raw_dir}에서 번들을 하나도 못 읽었다", file=sys.stderr)
        return 1

    # 클래스의 rpm은 데이터가 정한다: 그 클래스에서 가장 흔한 값을 클래스 값으로
    # 읽고, 거기서 벗어난 유닛만 유닛별 표의 대상이다. 손으로 적으면 클래스가
    # 통째로 바뀐 날을 못 본다.
    per_weapon = collections.defaultdict(collections.Counter)
    for _, weapon, rpm in observed.values():
        per_weapon[weapon][rpm] += 1

    problems, checked, overrides_seen = [], 0, {}
    for slug in sorted(ENCODED_SLUGS):
        name = RAW_NAME_ALIASES.get(slug) or character_name(slug)
        if name is None:
            problems.append(f"{slug}: 캐릭터 이름을 못 읽었다")
            continue
        if name not in observed:
            problems.append(f"{slug}: raw에 {name!r}가 없다")
            continue
        rid, weapon, rpm = observed[name]
        checked += 1
        charge = weapon in CHARGE_WEAPONS
        table_name = "CHARGE_ROUNDS_PER_MINUTE" if charge else "ROUNDS_PER_MINUTE"
        table = CHARGE_ROUNDS_PER_MINUTE if charge else ROUNDS_PER_MINUTE
        class_rpm = per_weapon[weapon].most_common(1)[0][0]
        listed = table.get(slug)
        if rpm == class_rpm:
            if listed is not None:
                problems.append(
                    f"{slug}: 데이터가 클래스와 같은 {rpm:.0f}인데 "
                    f"{table_name}에 {listed}로 올라 있다")
            continue
        overrides_seen[slug] = (rid, weapon, rpm, class_rpm)
        if listed is None:
            problems.append(
                f"{slug}: {weapon} 클래스는 {class_rpm:.0f}인데 데이터는 "
                f"{rpm:.0f}(rid {rid}) - {table_name}에 없다")
        elif float(listed) != rpm:
            problems.append(
                f"{slug}: 데이터는 {rpm:.0f}(rid {rid})인데 표는 {listed}")

    print(f"{checked}슬러그 대조")
    for weapon, counts in sorted(per_weapon.items()):
        class_rpm = counts.most_common(1)[0][0]
        derived = rounds_per_second(class_rpm)
        if weapon in CHARGE_WEAPONS:
            # 차지 무기의 클래스 값은 바닥값이 아니다 - 위 독스트링 참고.
            print(f"  {weapon:<4} 클래스 {class_rpm:>6.0f}발/분 -> {derived:>5.2f}발/초"
                  f"  (바닥값 아님, 유닛별 표만 쓴다)")
            continue
        engine = RATE_OF_FIRE_60FPS.get(weapon)
        mark = "" if engine == derived else f"  <-- 표는 {engine}"
        print(f"  {weapon:<4} 클래스 {class_rpm:>6.0f}발/분 -> {derived:>5.2f}발/초"
              f"  (엔진 {engine}){mark}")
        if engine is None:
            problems.append(f"{weapon}: RATE_OF_FIRE_60FPS에 없는 무기군이 데이터에 있다")
        elif engine != derived:
            problems.append(
                f"{weapon}: 데이터는 {derived}발/초인데 RATE_OF_FIRE_60FPS는 {engine}")

    print(f"\n클래스와 다른 유닛 {len(overrides_seen)}개:")
    for slug, (rid, weapon, rpm, class_rpm) in sorted(overrides_seen.items()):
        print(f"  {slug:<28}{weapon:<4} {rpm:>6.0f}발/분 -> "
              f"{rounds_per_second(rpm):>5.2f}발/초  (클래스 {class_rpm:.0f}, rid {rid})")

    listed_slugs = set(ROUNDS_PER_MINUTE) | set(CHARGE_ROUNDS_PER_MINUTE)
    for slug in sorted(listed_slugs - set(ENCODED_SLUGS)):
        print(f"  (표에만 있고 인코딩 안 된 슬러그: {slug})")

    if problems:
        print("\n어긋남:", file=sys.stderr)
        for line in problems:
            print(f"  {line}", file=sys.stderr)
        return 1
    print("\nattack_rate의 연사 표 셋 다 수집 데이터와 일치한다.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
