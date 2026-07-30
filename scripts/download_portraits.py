#!/usr/bin/env python
"""Download character portrait icons for every engine-supported Nikke.

WHY
    The deck-builder palette UI wants a portrait for each Nikke the engine can
    simulate. The repo ships stat captures (data/capturedimages/) but no
    portraits. lootandwaifus.com — the project's primary character-data source —
    renders a portrait on each character page, and every collected character
    HTML embeds the exact CDN path in its `data-default-src` attribute. We read
    that path straight out of the already-collected HTML (no URL guessing), then
    download the asset locally so the frontend never hotlinks a CDN that can 404
    or rotate.

WHEN TO USE
    - After encoding new Nikkes (registry grows) — re-run to fetch their icons.
    - After re-collecting lootandwaifus HTML (portrait paths may change).
    - One-shot to (re)populate frontend/public/portraits/.

    Requires the collected HTML in data/lootandwaifus/. In a worktree, run
    `python scripts/sync_worktree_data.py` first (data/ is gitignored).

WHAT IT DOES
    1. Reads the authoritative slug list from the engine registry
       (backend/app/skill_rules/registry.py `_BUILDERS`).
    2. Maps each slug to its lootandwaifus HTML file (direct match, or an alias
       for engine-only build variants that share one character portrait).
    3. Extracts the portrait path from `data-default-src`.
    4. Downloads each unique asset once into frontend/public/portraits/,
       keeping the CDN basename (natural dedupe across variants).
    5. Writes frontend/public/portraits/manifest.json mapping slug -> filename.

    Idempotent: skips assets already on disk unless --force is given.

USAGE
    python scripts/download_portraits.py            # download missing + write manifest
    python scripts/download_portraits.py --force     # re-download everything
    python scripts/download_portraits.py --dry-run   # report plan, fetch nothing
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import time
import urllib.request
from datetime import date
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
LOOT_DIR = REPO / "data" / "lootandwaifus"
OUT_DIR = REPO / "frontend" / "public" / "portraits"
MANIFEST = OUT_DIR / "manifest.json"

SOURCE_NAME = "lootandwaifus.com"
BASE_URL = "https://lootandwaifus.com"

# Engine build-variants that have no character page of their own; they share the
# base character's portrait. Keyed engine-slug -> lootandwaifus html slug.
SLUG_ALIASES = {
    "bready-lingering": "bready",
    "bready-recommended": "bready",
    "centi-signature": "centi",
    "cinderella-crystal-wave-mg": "cinderella-crystal-wave",
    "cinderella-crystal-wave-snipe": "cinderella-crystal-wave",
    "diesel-winter-sweets-highlight": "diesel-winter-sweets",
    "diesel-winter-sweets-intro": "diesel-winter-sweets",
    "drake-signature": "drake",
    "flora-signature": "flora",
    "helm-signature": "helm",
    "julia-signature": "julia",
    "laplace-signature": "laplace",
    "miranda-signature": "miranda",
    "moran-signature": "moran",
    "phantom-signature": "phantom",
    "privaty": "privaty-nikke",
    "privaty-signature": "privaty-nikke",
    "rapi-red-hood-b1": "rapi-red-hood",
    "rosanna-signature": "rosanna",
    "sugar-signature": "sugar",
    "tove-signature": "tove",
    "zwei-signature": "zwei",
    "laplace-ultimate-hero": "laplace-ultimate-hero-nikke",
    "maxwell-ordinary-mechanic": "maxwell-ordinary-mechanic-nikke",
}

PORTRAIT_RE = re.compile(r'data-default-src="(/characters/nikke/[^"]+)"')


def registry_slugs() -> list[str]:
    """Every slug the frontend may ask a portrait for, from the registry.

    That is the engine's candidate slugs PLUS the OWNED slug of a character the
    roster loader fans out into several of them (MODE_VARIANTS). The palette
    keys on what the player owns (`bready`), while results name candidates
    (`bready-lingering`) - the same two vocabularies app/supported_units.py
    serves, and a manifest covering only one of them leaves the other drawing
    an empty portrait box.
    """
    sys.path.insert(0, str(REPO / "backend"))
    from app.skill_rules import registry  # noqa: E402

    slugs = set(registry._BUILDERS) | set(registry.MODE_VARIANTS)
    return sorted(slugs)


def portrait_path_for(html_slug: str) -> str | None:
    """Return the CDN path (e.g. /characters/nikke/mi_c840_00_s.webp) or None."""
    html_file = LOOT_DIR / f"char_{html_slug}.html"
    if not html_file.exists():
        return None
    m = PORTRAIT_RE.search(html_file.read_text(encoding="utf-8", errors="replace"))
    return m.group(1) if m else None


def download(url: str, dest: Path) -> int:
    """Fetch url -> dest. Returns bytes written. Raises on HTTP error."""
    req = urllib.request.Request(url, headers={"User-Agent": "NikkeDeckBuilder/portraits"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        data = resp.read()
    dest.write_bytes(data)
    return len(data)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--force", action="store_true", help="re-download even if the file exists")
    ap.add_argument("--dry-run", action="store_true", help="print the plan; download nothing")
    args = ap.parse_args()

    if not LOOT_DIR.exists():
        print(f"ERROR: {LOOT_DIR} not found. Run scripts/sync_worktree_data.py first.", file=sys.stderr)
        return 2

    OUT_DIR.mkdir(parents=True, exist_ok=True)

    slugs = registry_slugs()
    manifest: dict[str, str] = {}
    missing: list[str] = []      # no HTML / no portrait path
    failed: list[str] = []       # download error
    to_fetch: dict[str, str] = {}  # filename -> full url (deduped)

    # A slug whose portrait can't be resolved from lootandwaifus HTML may still
    # have a hand-placed icon recorded in the existing manifest (ShiftyPad-sourced
    # units have no character page here). Keep those entries: rebuilding the
    # manifest from scratch would silently delete their portraits.
    kept: dict[str, str] = {}
    if MANIFEST.exists():
        existing = json.loads(MANIFEST.read_text(encoding="utf-8")).get("portraits", {})
    else:
        existing = {}

    for slug in slugs:
        html_slug = SLUG_ALIASES.get(slug, slug)
        path = portrait_path_for(html_slug)
        if path is None:
            if slug in existing and (OUT_DIR / existing[slug]).exists():
                manifest[slug] = existing[slug]
                kept[slug] = existing[slug]
            else:
                missing.append(slug)
            continue
        filename = path.rsplit("/", 1)[-1]
        manifest[slug] = filename
        to_fetch.setdefault(filename, BASE_URL + path)

    print(f"{len(slugs)} engine slugs -> {len(manifest)} mapped, "
          f"{len(to_fetch)} unique portraits, {len(kept)} kept from manifest, "
          f"{len(missing)} unmapped")
    if kept:
        print("  KEPT (no HTML, icon already present):",
              ", ".join(f"{slug}={name}" for slug, name in sorted(kept.items())))
    if missing:
        print("  UNMAPPED (no portrait found):", ", ".join(missing))

    fetched = skipped = 0
    for filename, url in sorted(to_fetch.items()):
        dest = OUT_DIR / filename
        if dest.exists() and not args.force:
            skipped += 1
            continue
        if args.dry_run:
            print(f"  would fetch {url} -> {dest.relative_to(REPO)}")
            continue
        try:
            n = download(url, dest)
            print(f"  fetched {filename} ({n:,} bytes)")
            fetched += 1
            time.sleep(0.2)  # be polite to the CDN
        except Exception as exc:  # noqa: BLE001
            failed.append(f"{filename}: {exc}")
            print(f"  FAILED {url}: {exc}", file=sys.stderr)

    if args.dry_run:
        print(f"dry-run: would fetch {len(to_fetch) - skipped}, skip {skipped} existing")
        return 0

    payload = {
        "source": SOURCE_NAME,
        "base_url": BASE_URL,
        "generated": date.today().isoformat(),
        "note": "Portrait paths read from data/lootandwaifus/char_<slug>.html "
                "(data-default-src); regenerate via scripts/download_portraits.py.",
        "portraits": dict(sorted(manifest.items())),
    }
    MANIFEST.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {MANIFEST.relative_to(REPO)} ({len(manifest)} slugs)")
    print(f"done: fetched {fetched}, skipped {skipped}, failed {len(failed)}, unmapped {len(missing)}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
