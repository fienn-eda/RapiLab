"""Measure raid-recommendation wall time as a function of candidate-pool size.

Why: the user "units to use" pool selector (docs/decisions.md 2026-07-23) lets a
player exclude un-fielded Nikkes, shrinking the search pool at the source. Its
whole premise is that a smaller pool is enough to make raid-from-scratch (the
~597 s / 78-unit pain) tolerable WITHOUT the deferred 2-stage search rewrite. This
script grounds that premise: it times the hot paths across several pool sizes so we
can read the speed-vs-size curve and decide whether the 2-stage algorithm is still
needed (roadmap Phase 5 perf backlog).

What it measures, per --sizes entry N (first N supported units; per-sim cost is
stat-independent, so pool SIZE is what matters, not which units):
  - zerobase: one `allocate_decks(roster, boss, workers="auto")` — the zero-base
    raid path (no draft), 5 greedy-peel decks + swap. This is the 597 s case.
  - draft:    `recommend_from_draft` on a COMPLETE draft (warm + within_draft `s`),
    the ~216 s complete-draft path. (Expensive; opt in with --mode draft/both.)

Output is a table: N, loadable, zero-base s, [draft s]. No cProfile overhead.

MUST keep every SimPool-constructing call under `if __name__ == "__main__"`:
Windows spawn re-imports this module in each worker, so reaching allocate_decks
at import time would fork-bomb (same rule as profile_recommend_allocation.py).

Usage (any cwd):
    python3 scripts/measure_pool_size_speed.py [--sizes 77,50,40,30,25]
                                               [--mode zerobase|draft|both]
                                               [--workers auto|N]
"""
import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app.models import UserNikkeState  # noqa: E402
from app.user_roster import load_roster  # noqa: E402
from app.supported_units import supported_units  # noqa: E402
from app.deck_search import BossProfile  # noqa: E402
import app.deck_allocation as da  # noqa: E402


def _nikke(slug):
    # Placeholder investment: stats don't change per-sim cost, only feasibility.
    return UserNikkeState.model_validate({
        "character_slug": slug, "level": 200, "core_level": 0,
        "hp": 1_000_000.0, "atk": 60_000.0, "def_": 3_000.0,
        "skill_levels": {"skill1": 10, "skill2": 10, "burst": 10},
    })


def _build_roster(max_units):
    slugs = [u["slug"] for u in supported_units()][:max_units]
    specs, excluded = load_roster([_nikke(s) for s in slugs])
    return specs, excluded


def _time_zerobase(specs, boss, workers):
    t0 = time.perf_counter()
    da.allocate_decks(specs, boss, workers=workers)
    return time.perf_counter() - t0


def _time_draft(specs, boss, workers):
    # Build a feasible complete draft from a zero-base allocation's 5 decks,
    # then time the full three-tier recommend_from_draft on it.
    base = da.allocate_decks(specs, boss, workers=workers)
    by_slug = {u.slug: u for u in specs}
    draft = [[by_slug[s] for s in d["deck"]] for d in base["decks"]]
    t0 = time.perf_counter()
    da.recommend_from_draft(specs, boss, num_decks=5, draft=draft, workers=workers)
    return time.perf_counter() - t0


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--sizes", default="77,50,40,30,25",
                        help="comma-separated pool sizes (default 77,50,40,30,25)")
    parser.add_argument("--mode", choices=("zerobase", "draft", "both"),
                        default="zerobase", help="which path(s) to time")
    parser.add_argument("--workers", default="auto",
                        help='"auto" (default) or an int worker count')
    args = parser.parse_args()

    workers = args.workers if args.workers == "auto" else int(args.workers)
    sizes = [int(s) for s in args.sizes.split(",") if s.strip()]
    boss = BossProfile(element="Water", fight_duration=180.0)

    header = f"{'N':>4} {'loadable':>8} {'zerobase_s':>11}"
    if args.mode in ("draft", "both"):
        header += f" {'draft_s':>9}"
    print(header, flush=True)
    print("-" * len(header), flush=True)

    for n in sizes:
        specs, excluded = _build_roster(n)
        row = f"{n:>4} {len(specs):>8}"
        if args.mode in ("zerobase", "both"):
            row += f" {_time_zerobase(specs, boss, workers):>11.1f}"
        else:
            row += f" {'-':>11}"
        if args.mode in ("draft", "both"):
            row += f" {_time_draft(specs, boss, workers):>9.1f}"
        print(row, flush=True)


if __name__ == "__main__":
    main()
