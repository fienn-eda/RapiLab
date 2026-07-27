"""소장품·애장품 레코드를 tables.json["collectibles"]에 병합한다.

언제 쓰나: 게임이 소장품 수치를 조정했거나 새 애장품이 나왔을 때. 먼저 수집하고
(브라우저·로그인 불필요) 이 스크립트로 병합한다.

    cd tools/collect-blablalink && node collect.js --collectibles
    python3 scripts/update_collectible_table.py

원본 레코드는 애장품 고유 스킬 텍스트까지 담고 있어 272KB - tables.json 전체보다
크다. 엔진이 읽는 것은 무기군 스킬(collection_skill_group_data)과 스탯 커브뿐이므로
그것만 남긴다. `favoriteitem_skill_group_data`(애장품 고유 스킬)는 통째로 버린다:
그쪽은 `-signature` 슬러그로 손으로 인코딩하는 영역이고, 이 테이블의 소비자가 없다.

description_value_list의 빈 칸(`{}`)은 지우지 않는다 - 슬롯 위치가 곧 키라서
(COLLECTIBLE_SKILL_STATS가 위치로 매핑한다) 압축하면 인덱스가 밀린다.
"""
import argparse
import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[1]
CAPTURE = REPO / "tools" / "collect-blablalink" / "collectibles.json"
TABLES = REPO / "data" / "nikke-stat-tables" / "tables.json"

IDENTITY = ("id", "favorite_rare", "favorite_type", "weapon_type", "name_code", "max_level")
CURVES = ("atk", "hp", "def", "grade")
GROUP_FIELDS = ("group_id", "name_localkey", "description_localkey", "description_value_list")
WEAPON_GROUPS = ("AR", "SMG", "SG", "RL", "SR", "MG")


def trim(record: dict) -> dict:
    out = {k: record[k] for k in IDENTITY if k in record}
    out.update({k: record[k] for k in CURVES if k in record})
    # 단계 -> 스킬레벨 사다리. 슬롯 수만큼 있고(R은 1개, SR/SSR은 2개) 이름이
    # collection_skill_group_data의 위치와 짝지어진다.
    for slot in range(1, len(record.get("collection_skill_group_data", [])) + 1):
        key = f"level{slot}"
        if key in record:
            out[key] = record[key]
    out["collection_skill_group_data"] = [
        {k: group[k] for k in GROUP_FIELDS if k in group}
        for group in record.get("collection_skill_group_data", [])
    ]
    return out


def check(records: dict[str, dict]) -> list[str]:
    """수집이 반쪽이 아닌지. 등급별 무기군 6개가 다 있어야 한다."""
    problems = []
    for rare in ("R", "SR"):
        groups = {r["weapon_type"] for r in records.values() if r["favorite_rare"] == rare}
        missing = [w for w in WEAPON_GROUPS if w not in groups]
        if missing:
            problems.append(f"{rare} 등급에 없는 무기군: {', '.join(missing)}")
    if not any(r["favorite_rare"] == "SSR" for r in records.values()):
        problems.append("SSR(애장품) 레코드가 하나도 없다")
    return problems


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--capture", type=Path, default=CAPTURE,
                        help=f"collect.js --collectibles 의 출력 (기본: {CAPTURE})")
    parser.add_argument("--tables", type=Path, default=TABLES,
                        help=f"병합 대상 (기본: {TABLES})")
    parser.add_argument("--dry-run", action="store_true", help="쓰지 않고 요약만")
    args = parser.parse_args()

    if not args.capture.exists():
        print(f"없음: {args.capture}\n먼저 실행: cd tools/collect-blablalink && "
              f"node collect.js --collectibles", file=sys.stderr)
        return 1
    captured = json.loads(args.capture.read_text(encoding="utf-8"))
    problems = check(captured)
    if problems:
        for p in problems:
            print(f"수집 불완전: {p}", file=sys.stderr)
        return 1

    tables = json.loads(args.tables.read_text(encoding="utf-8"))
    before = set(tables.get("collectibles", {}))
    trimmed = {tid: trim(record) for tid, record in
               sorted(captured.items(), key=lambda kv: int(kv[0]))}
    tables["collectibles"] = trimmed

    added = sorted(set(trimmed) - before)
    removed = sorted(before - set(trimmed))
    print(f"소장품 {len(trimmed)}개 (R/SR {sum(1 for r in trimmed.values() if r['favorite_type'] == 'Collection')} · "
          f"애장품 {sum(1 for r in trimmed.values() if r['favorite_type'] == 'Favorite')})")
    if added:
        print(f"  추가: {', '.join(added)}")
    if removed:
        print(f"  제거: {', '.join(removed)}")
    if args.dry_run:
        print("(dry-run - 쓰지 않음)")
        return 0
    args.tables.write_text(json.dumps(tables, ensure_ascii=False, indent=2) + "\n",
                           encoding="utf-8")
    print(f"기록함: {args.tables}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
