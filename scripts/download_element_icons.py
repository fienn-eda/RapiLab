#!/usr/bin/env python
"""Download the five element (code) icons the boss form draws.

WHY
    The boss form picks the boss's WEAKNESS by icon rather than by a dropdown,
    so the app needs the five code icons on disk. RapiLab ships as an installed
    WebView2 app, so hotlinking blablalink's CDN would leave the picker blank
    offline (and break outright if the CDN path rotates) - the same reason
    scripts/download_portraits.py exists.

WHEN TO USE
    - One-shot to populate frontend/public/elements/.
    - Again only if blablalink changes the asset paths below.

WHAT IT DOES
    Downloads five PNGs into frontend/public/elements/, named by the ENGINE's
    element names. blablalink calls the electric code "electronic"; that spelling
    is confined to this file's URL table, exactly as backend/app/shiftypad_normalize.py
    confines it on the data side.

    Idempotent: skips files already on disk unless --force is given.

USAGE
    python scripts/download_element_icons.py
    python scripts/download_element_icons.py --force
    python scripts/download_element_icons.py --dry-run
"""
from __future__ import annotations

import argparse
import sys
import time
import urllib.request
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
OUT_DIR = REPO / "frontend" / "public" / "elements"

BASE_URL = ("https://www.blablalink.com/assets/nikke/version/default"
            "/shiftysassets/images")

# engine element name -> blablalink's icon basename. "electronic" is
# blablalink's spelling of the engine's "Electric" and lives only here.
ICONS = {
    "fire": "icon-code-fire.png",
    "water": "icon-code-water.png",
    "wind": "icon-code-wind.png",
    "iron": "icon-code-iron.png",
    "electric": "icon-code-electronic.png",
}


def download(url: str, dest: Path) -> int:
    req = urllib.request.Request(url, headers={"User-Agent": "RapiLab/element-icons"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = resp.read()
    dest.write_bytes(data)
    return len(data)


def main() -> int:
    ap = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--force", action="store_true", help="re-download even if the file exists")
    ap.add_argument("--dry-run", action="store_true", help="print the plan; download nothing")
    args = ap.parse_args()

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    fetched = skipped = 0
    failed: list[str] = []
    for element, basename in sorted(ICONS.items()):
        dest = OUT_DIR / f"{element}.png"
        url = f"{BASE_URL}/{basename}"
        if dest.exists() and not args.force:
            skipped += 1
            continue
        if args.dry_run:
            print(f"  would fetch {url} -> {dest.relative_to(REPO)}")
            continue
        try:
            n = download(url, dest)
            print(f"  fetched {dest.name} ({n:,} bytes)")
            fetched += 1
            time.sleep(0.2)  # be polite to the CDN
        except Exception as exc:  # noqa: BLE001
            failed.append(f"{dest.name}: {exc}")
            print(f"  FAILED {url}: {exc}", file=sys.stderr)

    if args.dry_run:
        print(f"dry-run: would fetch {len(ICONS) - skipped}, skip {skipped} existing")
        return 0
    print(f"done: fetched {fetched}, skipped {skipped}, failed {len(failed)}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
