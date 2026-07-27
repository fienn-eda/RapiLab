#!/usr/bin/env python
"""동기화된 계정의 소장품이 실제로 엔진에 반영되는지 감사한다.

왜: 소장품은 배선돼 있어도 데이터가 없거나 tid가 테이블에 없으면 **경고 한 줄만
찍고 조용히 0을 기여한다**. gap #17이 정확히 그 상태로 오래 있었고, 배선 전후
캘리브레이션이 완전히 동일했던 것이 그 증거다. 이 스크립트는 그 침묵을 깬다.

언제: 로스터를 재동기화한 뒤, 소장품 테이블을 갱신한 뒤
(`scripts/update_collectible_table.py`), 그리고 새 무기군·등급이 나왔을 때.

무엇을: 실계정의 소장품 상태(`backend/tests/fixtures/stat_ground_truth.json` -
GetUserCharacterDetails의 favorite_item_tid/lv)를 유닛별 슬러그로 조인해
`load_roster`를 소장품 있음/없음 두 번 태우고 무기 스탯 차이를 본다. 프로덕션
경로를 그대로 통과하므로 "테이블엔 있는데 엔진이 안 읽더라"를 잡아낸다.

종료 코드는 소장품을 착용했는데 아무것도 못 받는 유닛이 있으면 1이다.
"""
import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "backend"))

from app.models import UserNikkeState  # noqa: E402
from app.stat_assembly import FAVORITE_ITEM_TID_BASE, load_stat_tables  # noqa: E402
from app.user_roster import load_roster  # noqa: E402

GROUND_TRUTH = REPO / "backend" / "tests" / "fixtures" / "stat_ground_truth.json"
DIRECTORY = REPO / "tools" / "collect-blablalink" / "nikke-directory.json"
SLUG_MAP_TS = REPO / "frontend" / "src" / "lib" / "resourceIdSlugMap.ts"


def slug_by_resource_id() -> dict[int, str]:
    """프론트의 resource_id -> 슬러그 맵. 파이썬 사본을 두면 갈라지므로 원본을
    읽는다 - `backend/tests/test_resource_id_slug_map.py`와 같은 방식이다."""
    body = SLUG_MAP_TS.read_text(encoding="utf-8")
    body = body.split("Record<number, string> = {", 1)[1].split("\n}", 1)[0]
    return {int(rid): slug for rid, slug in re.findall(r"(\d+)\s*:\s*'([^']+)'", body)}


def derive_slug(name_en: str) -> str:
    """이름에서 바로 유도한 슬러그 - 프론트 `exiaImport.deriveSlug`와 같은 규칙.
    resource_id 맵은 모호한 유닛만 담으므로 나머지는 앱도 이 경로로 온다."""
    lowered = name_en.lower().replace("(", "").replace(")", "").replace(":", "")
    return "-".join(lowered.split())


def account_units() -> list[dict]:
    """실계정 유닛: 슬러그 + 소장품 상태."""
    directory = json.loads(DIRECTORY.read_text(encoding="utf-8"))
    rid_by_name = {e["name_en"]: e["resource_id"] for e in directory}
    slugs = slug_by_resource_id()
    units = []
    for unit in json.loads(GROUND_TRUTH.read_text(encoding="utf-8"))["units"]:
        rid = rid_by_name.get(unit["name_en"])
        slug = slugs.get(rid) if rid is not None else None
        if slug is None:
            slug = derive_slug(unit["name_en"])
        units.append({
            "name_en": unit["name_en"],
            "slug": slug,
            "atk": unit["measured"]["raid400_atk"],
            "hp": unit["measured"]["raid400_hp"],
            "tid": unit["favorite_item_tid"],
            "level": unit["favorite_item_lv"],
        })
    return units


def _state(unit: dict, *, equipped: bool) -> dict:
    return {
        "character_slug": unit["slug"], "level": 200,
        "hp": float(unit["hp"]), "atk": float(unit["atk"]), "def_": 3000.0,
        "skill_levels": {"skill1": 10, "skill2": 10, "burst": 10},
        "collectible_tid": unit["tid"] if equipped else 0,
        "collectible_level": unit["level"] if equipped else 0,
    }


def rarity_of(tid: int, table: dict) -> str:
    if not tid:
        return "없음"
    record = table.get(str(tid))
    if record is not None:
        return record["favorite_rare"]
    return "SSR(미수록)" if tid >= FAVORITE_ITEM_TID_BASE else "미수록"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--verbose", action="store_true", help="유닛별로 전부 출력")
    args = parser.parse_args()

    table = load_stat_tables()["collectibles"]
    units = account_units()
    print(f"실계정 {len(units)}유닛 (슬러그 해석된 것만)")

    rarities = Counter(rarity_of(u["tid"], table) for u in units)
    print("소장품 등급 분포: " + " · ".join(f"{k} {v}" for k, v in rarities.most_common()))

    silent, moved, unencoded = [], [], []
    for unit in units:
        if not unit["tid"]:
            continue
        bare, _ = load_roster([UserNikkeState.model_validate(_state(unit, equipped=False))])
        held, _ = load_roster([UserNikkeState.model_validate(_state(unit, equipped=True))])
        if not bare or not held:
            # 인코딩이 없어 로스터에 못 들어가는 유닛. 소장품과 무관한 사유지만
            # 세지 않으면 합이 안 맞아 "조용히 0"과 구별이 안 된다.
            unencoded.append(unit)
            continue
        # 무기 배율과 permanent Effect 양쪽을 본다: 무기군에 따라 둘 중 하나로만
        # 나온다(차지·평타는 무기 스탯, 코어·장탄은 Effect).
        weapon_delta = {
            stat: round(held[0].weapon_stats[stat] / bare[0].weapon_stats[stat], 6)
            for stat in bare[0].weapon_stats
            if isinstance(bare[0].weapon_stats[stat], (int, float))
            and bare[0].weapon_stats[stat]
            and held[0].weapon_stats[stat] != bare[0].weapon_stats[stat]
        }
        from app.collectible_effects import collectible_modifiers
        _, effects = collectible_modifiers(
            unit["tid"], unit["level"], unit["slug"], held[0].weapon)
        row = (unit, weapon_delta, [(e.stat, round(e.value, 5)) for e in effects])
        (moved if (weapon_delta or effects) else silent).append(row)

    held_count = sum(1 for u in units if u["tid"])
    print(f"소장품 착용 {held_count}유닛 = 수치가 움직인 것 {len(moved)} · "
          f"아무것도 못 받은 것 {len(silent)} · 슬러그 미인코딩 {len(unencoded)}")
    by_rarity = Counter(rarity_of(u["tid"], table) for u, _, _ in moved)
    print("  움직인 것의 등급 분포: "
          + " · ".join(f"{k} {v}" for k, v in by_rarity.most_common()))
    zero_level = [u for u, _, _ in moved if u["level"] == 0]
    if zero_level:
        print(f"  ⚠ 그중 {len(zero_level)}유닛은 소장품 레벨이 0이다 - "
              "스탯 쪽은 레벨 0을 '미착용'으로 보고 0을 주는데 스킬 쪽은 1단을 준다")
    if args.verbose or silent:
        for unit, weapon_delta, effects in (moved if args.verbose else []) + silent:
            mark = "  " if (weapon_delta or effects) else "!!"
            print(f"{mark} {unit['name_en']:<28} {unit['slug']:<32} "
                  f"tid={unit['tid']} lv={unit['level']:<2} "
                  f"weapon={weapon_delta or '-'} effects={effects or '-'}")
    if silent:
        print("\n소장품을 착용했는데 아무 효과도 못 받는 유닛이 있다 - "
              "테이블에 레코드가 없거나 COLLECTIBLE_SKILL_STATS 매핑이 빠졌다.",
              file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
