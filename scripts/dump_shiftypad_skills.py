"""Print a ShiftyPad raw bundle's skill text alongside its max-level value slots.

Use this at the start of an encoding, after
`node collect.js --nikke <rid> --headless` has written
`data/shiftypad/raw/<rid>.json`.

Why this rather than reading lootandwaifus prose and numbering the slots by
hand: the raw bundle's `description_localkey` keeps the
`{description_value_NN}` placeholders in place, so each number is printed
beside the slot it fills. Hand-numbering is where slot errors come from - a
literal in the prose (Zwei's "Pierce Attacks 101") shifts every slot after it,
and the encoding then reads a duration where it meant a buff.

What it does NOT show: skill cooldowns (lootandwaifus prints those in the skill
title, and a Skill 1/2 cooldown is what decides `periodic_rules`).

    python scripts/dump_shiftypad_skills.py 95 202
    python scripts/dump_shiftypad_skills.py 382 --level 5
"""
import argparse
import json
import sys
from pathlib import Path

RAW_DIR = Path(__file__).resolve().parent.parent / "data" / "shiftypad" / "raw"
SKILLS = (("skill1_detail", "Skill 1"), ("skill2_detail", "Skill 2"),
          ("ulti_skill_detail", "Burst"))


def dump(rid, level):
    path = RAW_DIR / f"{rid}.json"
    if not path.exists():
        print(f"{rid}: no raw bundle at {path} - collect it first "
              f"(cd tools/collect-blablalink && node collect.js --nikke {rid} --headless)")
        return False

    bundle = json.loads(path.read_text(encoding="utf-8"))
    detail = bundle["detail"]
    shot = detail.get("shot_detail") or {}
    name = (bundle.get("directory") or {}).get("name_en") or detail.get("name_localkey")

    print("=" * 78)
    print(f"{name}  (resource_id {rid})  squad={detail.get('squad')}")
    print(f"  {shot.get('weapon_type')} · burst {detail.get('use_burst_skill')} · "
          f"max_ammo {shot.get('max_ammo')} · reload {shot.get('reload_time')} · "
          f"rof {shot.get('rate_of_fire')} · pellets {shot.get('shot_count')} · "
          f"charge {shot.get('charge_time')} · full_charge {shot.get('full_charge_damage')}")
    # 10000 means one uninterrupted reload; anything else is a clip weapon and
    # belongs in registry.CLIP_RELOAD_SPLITS or its cadence runs optimistic.
    reload_bullet = shot.get("reload_bullet")
    note = "" if reload_bullet == 10000 else "   <-- CLIP WEAPON, see registry.CLIP_RELOAD_SPLITS"
    print(f"  reload_bullet {reload_bullet}{note}")

    for key, label in SKILLS:
        skill = detail.get(key)
        if not skill:
            print(f"\n--- {label}: MISSING")
            continue
        print(f"\n--- {label}: {skill.get('name_localkey')}")
        print(skill.get("description_localkey", ""))
        print("  values:")
        for i, slot in enumerate(skill.get("description_value_list") or [], start=1):
            values = slot.get("description_value") or []
            if not values:
                continue
            index = min(level, len(values)) - 1
            print(f"    description_value_{i:02d} = {values[index]}"
                  f"   (lv1={values[0]}, levels={len(values)})")
    print()
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("resource_ids", nargs="+", help="blablalink resource_id(s)")
    parser.add_argument("--level", type=int, default=10,
                        help="skill level to print (default 10, the max)")
    args = parser.parse_args()

    sys.stdout.reconfigure(encoding="utf-8")
    ok = [dump(rid, args.level) for rid in args.resource_ids]
    return 0 if all(ok) else 1


if __name__ == "__main__":
    raise SystemExit(main())
