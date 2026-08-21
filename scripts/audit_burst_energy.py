"""원본 번들 대 배선된 값 - 게이지 상수가 어긋나면 잡는다.

왜 테스트가 아니라 스크립트인가: `data/shiftypad/raw/`는 gitignore라 릴리즈에도
CI에도 없다. 수집을 새로 한 뒤 사람이 돌리는 감사다.

검사 둘:
  1. dotgg의 `burstGen` x 10000 == 원본의 `burst_energy_pershot`
  2. 원본의 `full_charge_burst_energy` == `full_charge_damage`
     (`burst_gauge.energy_per_hit`이 후자를 차지 배율로 쓰는 근거)

Usage: python3 scripts/audit_burst_energy.py
"""
import glob
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def main():
    ts = (ROOT / "frontend/src/lib/resourceIdSlugMap.ts").read_text(encoding="utf-8")
    slug_of = {int(rid): slug for rid, slug
               in re.findall(r"^\s*(\d+):\s*'([a-z0-9-]+)'", ts, re.M)}

    mismatched, checked = [], 0
    for path in sorted(glob.glob(str(ROOT / "data/shiftypad/raw/*.json"))):
        detail = json.loads(Path(path).read_text(encoding="utf-8"))["detail"]
        shot = detail.get("shot_detail") or {}
        if not shot:
            continue
        slug = slug_of.get(detail["resource_id"])
        # 검사 #2: 차지 무기만 대상 (full_charge_burst_energy=0은 비차지 무기의 센티널)
        if shot.get("full_charge_burst_energy") and shot.get("full_charge_burst_energy") != shot.get("full_charge_damage"):
            mismatched.append(f"{slug}: full_charge_burst_energy "
                              f"{shot['full_charge_burst_energy']} != "
                              f"full_charge_damage {shot['full_charge_damage']}")
        dotgg = ROOT / "data/dotgg" / f"char_{slug}.json"
        if slug and dotgg.exists():
            gen = json.loads(dotgg.read_text(encoding="utf-8")).get("burstGen")
            if gen is not None:
                checked += 1
                wired = float(str(gen).rstrip("%")) * 10_000
                if abs(wired - shot["burst_energy_pershot"]) > 1e-6:
                    mismatched.append(f"{slug}: dotgg burstGen {gen} -> {wired:,.0f} "
                                      f"!= raw {shot['burst_energy_pershot']:,}")

    print(f"대조한 유닛: {checked}")
    for line in mismatched:
        print("  MISMATCH", line)
    print("어긋남 없음" if not mismatched else f"어긋남 {len(mismatched)}건")
    return 1 if mismatched else 0


if __name__ == "__main__":
    sys.exit(main())
