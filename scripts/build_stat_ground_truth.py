#!/usr/bin/env python3
"""Join measured stats with investment inputs into the stat-calculator fixture.

WHEN TO USE
    After re-collecting the roster (collector) or re-dumping character details,
    to refresh backend/tests/fixtures/stat_ground_truth.json.

WHY IT EXISTS
    The calculator is only trustworthy against measurements. Two collected files
    hold the halves of each observation and neither is committable:

      tools/collect-blablalink/roster.json   measured ATK at level 400 AND at the
                                             unit's real level (both scraped)
      tools/collect-blablalink/details.json  the investment that produced them
                                             (grade, core, gear, cube, affinity)

    Joining them yields a unit's inputs beside its outputs, at two levels - which
    is what separates a base-scaled percentage term from a flat one. A one-level
    fixture cannot: it ratifies any formula that happens to fit at that level,
    which is exactly how the earlier purely-additive draft survived review.

WHAT IT OMITS
    Account identifiers (intl_open_id, role_name, uid) are never read. The
    fixture is character investment plus measured stats - enough to test with,
    and committed deliberately (Fienn, 2026-07-18) so the check runs in CI rather
    than only on the one machine holding the raw dumps.

USAGE
    python scripts/build_stat_ground_truth.py [--out PATH]
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ROSTER = ROOT / "tools" / "collect-blablalink" / "roster.json"
DETAILS = ROOT / "tools" / "collect-blablalink" / "details.json"
OUTPOST = ROOT / "tools" / "collect-blablalink" / "outpost.json"
DIRECTORY = ROOT / "tools" / "collect-blablalink" / "nikke-directory.json"
DEFAULT_OUT = ROOT / "backend" / "tests" / "fixtures" / "stat_ground_truth.json"

SLOTS = ("head", "torso", "arm", "leg")


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    ap.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = ap.parse_args()

    for p in (ROSTER, DETAILS, DIRECTORY, OUTPOST):
        if not p.exists():
            print(f"missing {p}", file=sys.stderr)
            return 1

    directory = {e["name_code"]: e for e in json.loads(DIRECTORY.read_text(encoding="utf-8"))}
    by_rid = {e["resource_id"]: e for e in directory.values()}
    raw = json.loads(DETAILS.read_text(encoding="utf-8"))
    details = {d["name_code"]: d for d in raw["character_details"]}
    owned = {o["name_code"]: o for o in raw["owned"]}

    units = []
    for u in json.loads(ROSTER.read_text(encoding="utf-8"))["units"]:
        entry = by_rid.get(u["resource_id"])
        if entry is None:
            continue
        d = details.get(entry["name_code"])
        o = owned.get(entry["name_code"])
        if d is None or o is None:
            continue
        units.append(
            {
                "name_en": entry["name_en"],
                "class": entry["class"],
                "corporation": entry["corporation"],
                "level": o["lv"],
                "grade": d["grade"],
                "core": d["core"],
                "attractive_lv": d.get("attractive_lv", 0),
                "favorite_item_lv": d.get("favorite_item_lv", 0),
                "harmony_cube_lv": d.get("harmony_cube_lv", 0),
                "equip": [
                    {
                        "slot": s,
                        "tier": d.get(f"{s}_equip_tier", 0),
                        "lv": d.get(f"{s}_equip_lv", 0),
                    }
                    for s in SLOTS
                ],
                "measured": {"raid400_atk": u["raid400"]["atk"], "actual_atk": u["actual"]["atk"]},
            }
        )

    units.sort(key=lambda x: x["name_en"])
    args.out.parent.mkdir(parents=True, exist_ok=True)
    research = json.loads(OUTPOST.read_text(encoding="utf-8"))["recycle_room_researches"]
    payload = {"account_research": {str(r["tid"]): r["lv"] for r in research}, "units": units}
    args.out.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    levels = sorted({u["level"] for u in units})
    print(f"wrote {args.out}: {len(units)} units, levels {levels}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
