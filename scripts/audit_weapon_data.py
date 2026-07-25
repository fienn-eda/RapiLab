#!/usr/bin/env python
"""Audit every encoded Nikke's weapon stats against live ShiftyPad data.

WHY: the engine's per-shot damage, ammo cycle and reload timing all come from six
weapon fields (weapon type, damage%, maxAmmo, reloadTime, chargeTime,
chargeDamage%). For 83 of the 93 encoded slugs those fields still come from
`data/dotgg/`, a feed frozen since 2026-05, or from a hand-typed stub. Nothing
has ever checked them against the game. ShiftyPad's character-detail payload is
public live data (no account), so a whole-roster comparison is possible - this
script is that comparison.

The 2026-07-21 decision that rejected a wholesale dotgg->ShiftyPad backfill
rejected it as churn, on the assumption existing data was accurate. This script
tests that assumption instead of trusting it.

WHEN TO RUN: after a game balance patch touching weapons, before trusting an
old encoding's damage numbers, or any time you want evidence the weapon inputs
are still the game's. Collect the payloads first:

    cd tools/collect-blablalink
    node collect.js --nikke <rid,rid,...> --headless   # -> data/shiftypad/raw/

USAGE
    python scripts/audit_weapon_data.py [--raw-dir data/shiftypad/raw] [--json out.json]

VERDICTS (per encoded slug):
  ok        every weapon field matches ShiftyPad
  MISMATCH  at least one field differs - the engine is running on a wrong input
  no-live   no ShiftyPad bundle collected for this unit's resource_id
  no-local  the unit's current weapon file is missing/unreadable

Exit code is 1 when any slug is MISMATCH, so this can gate a commit.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO / "backend"))

from app.shiftypad_normalize import normalize_shiftypad  # noqa: E402
from app.skill_rules.registry import ENCODED_SLUGS  # noqa: E402
from app.skill_rules.registry import get_skill_value_manifest  # noqa: E402
from app.skill_values import DATA_DIR, load_character_data, load_weapon_data  # noqa: E402

SLUG_MAP_TS = REPO / "frontend" / "src" / "lib" / "resourceIdSlugMap.ts"

# The engine's weapon inputs (backend/app/user_roster.py `_weapon_stats`), plus the
# two identity fields a wrong weapon file would also corrupt. Percent fields are
# compared numerically: "8.73%" and "8.73 %" are the same number, and dotgg wrote
# some of them as bare numbers.
WEAPON_FIELDS = ("weapon", "maxAmmo", "damage", "reloadTime", "chargeTime", "chargeDamage")
META_FIELDS = ("element", "burst")


def parse_slug_map(path: Path = SLUG_MAP_TS) -> dict[int, str]:
    """resource_id -> base slug, parsed from the frontend's identity map.

    Regex-parsed rather than imported (it is TypeScript); the backend drift test
    test_resource_id_slug_map.py parses the same literal, so a rename breaks both.
    """
    text = path.read_text(encoding="utf-8")
    body = text.split("Record<number, string> = {", 1)[1].split("\n}", 1)[0]
    return {int(i): s for i, s in re.findall(r"(\d+):\s*'([a-z0-9-]+)'", body)}


def _number(value):
    """A weapon field as a comparable number, or the raw value if it is not one.

    dotgg stores percents as strings ("8.73%") and ShiftyPad as fixed-point
    ints that `normalize_shiftypad` re-renders as strings, so both sides arrive
    as text and must be compared as numbers to avoid formatting false positives.
    """
    if isinstance(value, str):
        stripped = value.strip().rstrip("%").strip()
        try:
            return float(stripped)
        except ValueError:
            return value
    if isinstance(value, (int, float)):
        return float(value)
    return value


def compare(local: dict, live: dict, fields: tuple[str, ...]) -> dict[str, tuple]:
    """Fields whose local value differs from the live one, as {field: (local, live)}."""
    diffs = {}
    for field in fields:
        if field not in live:
            continue
        local_value = local.get(field, "<missing>")
        if _number(local_value) != _number(live[field]):
            diffs[field] = (local_value, live[field])
    return diffs


def meta_source(manifest: dict, slug: str, weapon_data: dict, data_dir: Path) -> dict:
    """The file the loader reads element/burst/cooldown from, per load_nikke_spec.

    Not the same file as the weapon stats: a lootandwaifus-sourced unit takes its
    weapon from dotgg but its meta from lootandwaifus. Comparing the weapon file's
    meta would report differences the engine never sees - dotgg records Red Hood's
    burst as "p" while lootandwaifus (what the engine reads) says "3".
    """
    try:
        return load_character_data("lootandwaifus", manifest.get("data_slug", slug), data_dir)
    except FileNotFoundError:
        return weapon_data


def burst_cooldown(meta: dict):
    """The burst cooldown the loader would use, resolved exactly as load_nikke_spec does.

    Not a weapon field, but it comes free with the same payload and a wrong value
    distorts every simulated rotation, so the audit reports it alongside.
    """
    try:
        return float(meta.get("cooldown") or meta["skills"][2]["cooldown"])
    except (KeyError, IndexError, TypeError, ValueError):
        return None


def load_live(raw_dir: Path) -> dict[int, dict]:
    """resource_id -> normalized ShiftyPad character data, for every collected bundle."""
    live = {}
    for path in sorted(raw_dir.glob("*.json")):
        bundle = json.loads(path.read_text(encoding="utf-8"))
        live[int(path.stem)] = normalize_shiftypad(bundle)
    return live


def audit(raw_dir: Path, data_dir: Path = DATA_DIR) -> list[dict]:
    id_to_slug = parse_slug_map()
    slug_to_rid: dict[str, int] = {}
    for rid, slug in sorted(id_to_slug.items()):
        slug_to_rid.setdefault(slug, rid)
    live_by_rid = load_live(raw_dir)

    rows = []
    for slug in ENCODED_SLUGS:
        manifest = get_skill_value_manifest(slug)
        if manifest is None:
            continue
        data_slug = manifest.get("data_slug", slug)
        # A Favorite-Item build shares its base unit's weapon, and a mode variant
        # shares its base unit's file (the mode override is applied downstream in
        # load_nikke_spec), so both resolve through the base slug.
        rid = (
            slug_to_rid.get(slug)
            or slug_to_rid.get(data_slug)
            or slug_to_rid.get(slug.replace("-signature", ""))
        )
        row = {
            "slug": slug,
            "resource_id": rid,
            "weapon_source": manifest.get("weapon_source", manifest["source"]),
        }
        try:
            local = load_weapon_data(manifest, slug, data_dir)
        except (FileNotFoundError, KeyError):
            rows.append({**row, "verdict": "no-local"})
            continue
        live = live_by_rid.get(rid)
        if live is None:
            rows.append({**row, "verdict": "no-live"})
            continue
        weapon_diffs = compare(local, live, WEAPON_FIELDS)
        meta = meta_source(manifest, slug, local, data_dir)
        meta_diffs = compare(meta, live, META_FIELDS)
        ours_cd = burst_cooldown(meta)
        live_cd = live["skills"][2].get("cooldown") if len(live.get("skills", [])) > 2 else None
        cooldown_diff = (
            (ours_cd, live_cd)
            if ours_cd is not None and live_cd is not None and float(ours_cd) != float(live_cd)
            else None
        )
        rows.append(
            {
                **row,
                "verdict": "MISMATCH" if weapon_diffs else "ok",
                "weapon_diffs": weapon_diffs,
                "meta_diffs": meta_diffs,
                "burst_cooldown_diff": cooldown_diff,
            }
        )
    return rows


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--raw-dir", type=Path, default=REPO / "data" / "shiftypad" / "raw")
    parser.add_argument("--json", type=Path, help="also write the full report here")
    parser.add_argument("--quiet-ok", action="store_true", help="print only non-ok rows")
    args = parser.parse_args(argv)

    rows = audit(args.raw_dir)
    counts: dict[str, int] = {}
    for row in rows:
        counts[row["verdict"]] = counts.get(row["verdict"], 0) + 1

    cooldown_mismatches = [r for r in rows if r.get("burst_cooldown_diff")]
    for row in rows:
        interesting = row["verdict"] != "ok" or row.get("meta_diffs") or row.get("burst_cooldown_diff")
        if args.quiet_ok and not interesting:
            continue
        line = f"{row['verdict']:9} {row['slug']:34} rid={row['resource_id']} src={row['weapon_source']}"
        print(line)
        for field, (local, live) in row.get("weapon_diffs", {}).items():
            print(f"            {field}: ours={local!r} shiftypad={live!r}")
        for field, (local, live) in row.get("meta_diffs", {}).items():
            print(f"            (meta) {field}: ours={local!r} shiftypad={live!r}")
        if row.get("burst_cooldown_diff"):
            ours, live = row["burst_cooldown_diff"]
            print(f"            (burst cooldown) ours={ours} shiftypad={live}")

    print("\n" + "  ".join(f"{k}={v}" for k, v in sorted(counts.items())))
    print(f"burst-cooldown mismatches={len(cooldown_mismatches)}")
    if args.json:
        args.json.write_text(json.dumps(rows, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"wrote {args.json}")
    return 1 if counts.get("MISMATCH") else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
