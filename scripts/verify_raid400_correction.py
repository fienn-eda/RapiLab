#!/usr/bin/env python3
"""Prove the solo-raid level-400 stat correction actually reaches recommendations.

WHEN TO USE
    Once, to close the blablalink stat-collector plan's last open item, and again
    whenever the collector's stat semantics change. It answers one question:
    does feeding level-400 stats instead of real-level (663) stats change what
    the recommender returns?

WHY IT EXISTS
    Solo raid normalizes every account to character level 400, but the roster
    convention before the collector shipped was real-level stats - measured ~2.9x
    too high (Rapi: 418,862 actual vs 143,543 at level 400). docs/decisions.md
    therefore warns that every solo-raid recommendation made before the collector
    "should be treated as suspect until re-collected at level 400".

    The collector shipped and collects both numbers, but nobody ever checked that
    the corrected numbers change the ANSWER. A data fix nobody verified downstream
    is a fix on paper. This script runs the same roster both ways and diffs the
    rankings, so the correction is demonstrated rather than assumed.

WHAT IT DOES NOT DO
    It does not decide which ranking is right - level-400 is right by definition
    of solo raid. It measures how much the old convention distorted the output.

USAGE
    python scripts/verify_raid400_correction.py [--top-n 5] [--element Fire]

    Reads tools/collect-blablalink/roster.json (gitignored, produced by the
    collector) and frontend/src/lib/resourceIdSlugMap.ts for identity.

    In a worktree, run scripts/sync_worktree_data.py FIRST - the roster loader
    reads gitignored data/ and silently degrades without it.
"""
import argparse
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

from app.deck_search import BossProfile, search_best_decks  # noqa: E402
from app.models import UserNikkeState  # noqa: E402
from app.user_roster import load_roster  # noqa: E402

ROSTER_JSON = ROOT / "tools" / "collect-blablalink" / "roster.json"
MAP_TS = ROOT / "frontend" / "src" / "lib" / "resourceIdSlugMap.ts"


def resource_id_to_slug() -> dict[int, str]:
    """Parse the frontend identity map (the single source of truth for slugs)."""
    text = MAP_TS.read_text(encoding="utf-8")
    body = text.split("Record<number, string> = {", 1)[1].split("\n}", 1)[0]
    return {int(i): s for i, s in re.findall(r"(\d+):\s*'([a-z0-9-]+)'", body)}


def build_states(units, slugs, *, stat_key: str) -> list[UserNikkeState]:
    """One UserNikkeState per mapped unit, reading stats from `stat_key`.

    `raid400` is the solo-raid truth; `actual` reproduces the pre-collector
    convention so the two can be compared.
    """
    states = []
    for u in units:
        slug = slugs.get(u["resource_id"])
        stats = u.get(stat_key)
        if slug is None or not stats:
            continue
        cube = u.get("pve_cube")
        states.append(
            UserNikkeState(
                character_slug=slug,
                level=400,
                core_level=0,
                hp=stats["hp"],
                atk=stats["atk"],
                def_=stats["def"],
                skill_levels=u["skill_levels"],
                overload_options=u.get("overload") or [],
                pve_cube=cube if cube else None,
            )
        )
    return states


def rank(states, boss, top_n):
    specs, excluded = load_roster(states)
    results = search_best_decks(specs, boss, top_n=top_n)
    return results, specs, excluded


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--top-n", type=int, default=5)
    ap.add_argument("--element", default=None, help="boss element, e.g. Fire (default: none)")
    args = ap.parse_args()

    if not ROSTER_JSON.exists():
        print(f"missing {ROSTER_JSON} - run the collector first", file=sys.stderr)
        return 1

    units = json.loads(ROSTER_JSON.read_text(encoding="utf-8"))["units"]
    slugs = resource_id_to_slug()
    boss = BossProfile(element=args.element)

    print(f"roster units: {len(units)} | mapped to encoded slugs: "
          f"{sum(1 for u in units if u['resource_id'] in slugs)}")

    out = {}
    for key, label in (("raid400", "level 400 (solo raid, correct)"),
                       ("actual", "real level (pre-collector convention)")):
        states = build_states(units, slugs, stat_key=key)
        results, specs, excluded = rank(states, boss, args.top_n)
        out[key] = results
        print(f"\n=== {label} ===")
        print(f"  usable units: {len(specs)} (excluded {len(excluded)})")
        for i, r in enumerate(results, 1):
            print(f"  {i}. {r['total_damage']:>16,.0f}  {' / '.join(r['deck'])}")

    a = [tuple(r["deck"]) for r in out["raid400"]]
    b = [tuple(r["deck"]) for r in out["actual"]]
    print("\n=== verdict ===")
    print(f"  top-1 same deck : {a[:1] == b[:1]}")
    print(f"  top-{args.top_n} order same: {a == b}")
    print(f"  top-{args.top_n} set same  : {set(a) == set(b)}")
    if out["raid400"] and out["actual"]:
        ratio = out["actual"][0]["total_damage"] / out["raid400"][0]["total_damage"]
        print(f"  top-1 damage inflation using real-level stats: {ratio:.2f}x")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
