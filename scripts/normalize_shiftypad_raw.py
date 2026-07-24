#!/usr/bin/env python
"""Normalize a raw ShiftyPad bundle into the dotgg-shape file the roster loader reads.

WHY
    Non-signature new units are onboarded from ShiftyPad (public blablalink data),
    which supplies weapon stats + skill base values in one fetch — no manual weapon
    entry, no dependency on dotgg (dead since 2026-05). `collect.js --nikke <rid>
    --headless` writes the raw bundle to data/shiftypad/raw/<rid>.json; this script
    turns that into data/shiftypad/<slug>.json via `normalize_shiftypad`, the pure
    function whose parity with dotgg's shape is proven by the test suite.

WHEN TO USE
    Right after `collect.js --nikke` during new-Nikke onboarding
    (see docs/new-nikke-detection.md step 2). The unit's SKILL_VALUE_MANIFESTS
    then declares `source: "shiftypad"`.

USAGE
    python scripts/normalize_shiftypad_raw.py <rid>:<slug> [<rid>:<slug> ...]

    e.g. python scripts/normalize_shiftypad_raw.py 103:laplace-ultimate-hero \
                                                    105:maxwell-ordinary-mechanic
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
RAW_DIR = REPO / "data" / "shiftypad" / "raw"
OUT_DIR = REPO / "data" / "shiftypad"


def main(argv: list[str]) -> int:
    if not argv or any(":" not in a for a in argv):
        print(__doc__)
        print("ERROR: give one or more <rid>:<slug> pairs.", file=sys.stderr)
        return 2

    sys.path.insert(0, str(REPO / "backend"))
    from app.shiftypad_normalize import normalize_shiftypad  # noqa: E402

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    failed = 0
    for pair in argv:
        rid, slug = pair.split(":", 1)
        raw = RAW_DIR / f"{rid}.json"
        if not raw.exists():
            print(f"  MISSING {raw.relative_to(REPO)} — run collect.js --nikke {rid} --headless first",
                  file=sys.stderr)
            failed += 1
            continue
        try:
            bundle = json.loads(raw.read_text(encoding="utf-8"))
            normalized = normalize_shiftypad(bundle)
        except Exception as exc:  # noqa: BLE001
            print(f"  FAILED {rid}:{slug}: {exc}", file=sys.stderr)
            failed += 1
            continue
        dest = OUT_DIR / f"{slug}.json"
        dest.write_text(json.dumps(normalized, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        w = normalized["weapon"]
        print(f"  wrote {dest.relative_to(REPO)}  (weapon={w}, element={normalized['element']}, "
              f"burst={normalized['burst']})")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
