"""`core_damage.CORE_DAMAGE_RATE`를 수집 데이터와 대조한다.

언제 쓰나: 로스터를 재동기화한 뒤, 새 니케를 온보딩한 뒤, 그리고 코어 관련
값을 만지기 전에. 표는 손으로 적혀 있고 데이터는 갱신되므로 둘이 갈라지는 날이
온다.

무엇을 보나: `data/shiftypad/raw/*.json`의 `shot_detail.core_damage_rate`를
인코딩된 슬러그마다 찾아 표와 대조한다. raw 번들은 rid로 키가 잡혀 있어
슬러그가 없으므로, 캐릭터 데이터의 영문 이름으로 잇는다.

이름이 안 풀리는 슬러그는 **통과가 아니라 실패다.** 매칭이 조용히 비면 감사가
아무것도 안 보고 초록을 낸다.

테스트가 아니라 스크립트인 이유: `data/`는 gitignore라 워크트리나 CI에서 없을
수 있고, 조건부 테스트로 만들면 데이터가 없는 곳에서 조용히 skip된다.
"""
import argparse
import json
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "backend"))

from app.core_damage import CORE_DAMAGE_RATE, DEFAULT_CORE_DAMAGE_RATE  # noqa: E402
from app.skill_rules.registry import ENCODED_SLUGS, get_skill_value_manifest  # noqa: E402
from app.skill_values import load_character_data  # noqa: E402

# 콜라보 유닛은 raw 쪽 이름이 짧다. 우리 슬러그가 쓰는 성까지 붙은 이름과 이어야
# 한다 - 이 아홉만 예외이고, 나머지는 영문 이름이 그대로 일치한다.
RAW_NAME_ALIASES = {
    "ada-wong": "Ada",
    "asuka-shikinami-langley-wille": "Asuka: WILLE",
    "chisato-nishikigi": "Chisato",
    "jill-valentine": "Jill",
    "queen-makoto-nijima": "Queen (Makoto)",
    "rei-ayanami": "Rei",
    "rei-ayanami-tentative-name": "Rei (Tentative Name)",
    "takina-inoue": "Takina",
    "yukiko-amagi": "Yukiko",
}


def collect(raw_dir):
    """{영문 이름: (rid, core_damage_rate)} - 수집된 번들이 적은 배율."""
    observed = {}
    for path in sorted(raw_dir.glob("*.json")):
        bundle = json.loads(path.read_text(encoding="utf-8"))
        name = bundle["directory"]["name_localkey"]["name"].strip()
        observed[name] = (path.stem, bundle["detail"]["shot_detail"]["core_damage_rate"])
    return observed


def character_name(slug):
    """이 슬러그의 영문 캐릭터 이름, 못 찾으면 None.

    ShiftyPad 소스의 정규화 파일에는 `name`이 없으므로 lootandwaifus로 떨어진다.
    """
    manifest = get_skill_value_manifest(slug) or {}
    data_slug = manifest.get("data_slug", slug)
    for source in (manifest.get("source"), "lootandwaifus"):
        if source is None:
            continue
        try:
            data = load_character_data(source, data_slug)
        except (FileNotFoundError, KeyError):
            continue
        if data.get("name"):
            return data["name"].strip()
    return None


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
        print(f"{args.raw_dir}에서 번들을 하나도 못 읽었다", file=sys.stderr)
        return 1

    problems, checked, differing = [], 0, []
    for slug in sorted(ENCODED_SLUGS):
        name = RAW_NAME_ALIASES.get(slug) or character_name(slug)
        if name is None:
            problems.append(f"{slug}: 캐릭터 이름을 못 읽었다")
            continue
        if name not in observed:
            problems.append(f"{slug}: raw에 {name!r}가 없다")
            continue
        rid, rate = observed[name]
        expected = CORE_DAMAGE_RATE.get(slug, DEFAULT_CORE_DAMAGE_RATE)
        checked += 1
        if rate != expected:
            problems.append(
                f"{slug}: 데이터는 {rate}(rid {rid})인데 표는 {expected}")
        if rate != DEFAULT_CORE_DAMAGE_RATE:
            differing.append(f"{slug} {rate} (rid {rid})")

    print(f"{checked}/{len(ENCODED_SLUGS)}슬러그 대조, 기본값 {DEFAULT_CORE_DAMAGE_RATE}")
    for line in differing:
        print(f"  {line}")

    for slug in sorted(set(CORE_DAMAGE_RATE) - set(ENCODED_SLUGS)):
        print(f"  (표에만 있고 인코딩 안 된 슬러그: {slug})")

    if problems:
        print("\n어긋남:", file=sys.stderr)
        for line in problems:
            print(f"  {line}", file=sys.stderr)
        return 1
    print("\ncore_damage.CORE_DAMAGE_RATE는 수집 데이터와 일치한다.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
