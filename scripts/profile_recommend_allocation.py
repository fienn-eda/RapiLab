"""Profile the deck-allocation hot path to ground the SimPool-sharing work.

Why: the complete-draft path (`recommend_from_draft`) was measured at ~202 s but
never broken down. Before optimizing (shared SimPool / evaluate memo / warm-skip)
we must know WHERE the time goes — spawn overhead vs parallel greedy sims vs the
serial swap hill-climb vs the redundant scratch+warm passes. Optimizing the wrong
phase is the worst outcome (docs/roadmap.md perf backlog, option 0).

What it does (all with workers="auto", the real parallel path):
  Phase A: cProfile ONE zero-base `allocate_decks` and dump top cumulative-time
           functions — the PARENT-side split (ProcessPoolExecutor spawn, waiting
           on pool.map for greedy peeling, the serial _swap_pass' inline
           evaluate_deck calls, final summary). Workers aren't profiled (spawn
           re-imports), which is fine: we want the parent breakdown.
  Phase B: wall-time `recommend_from_draft` on a COMPLETE draft, with every
           `allocate_decks` call wrapped so scratch / warm / within_draft show
           their individual wall time + roster size — confirms (or refutes) the
           "2x full-roster ~97 s pass" hypothesis.

MUST stay under `if __name__ == "__main__":` — Windows spawn re-imports this
module in every worker; reaching a SimPool at import time would fork-bomb.

Usage (any cwd):
    python3 scripts/profile_recommend_allocation.py [--units N] [--no-profile]
"""
import argparse
import cProfile
import io
import pstats
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
    # Placeholder investment (like bench_evaluate_deck): stats don't change the
    # per-sim cost, only which units are feasible, which is what we're timing.
    return UserNikkeState.model_validate({
        "character_slug": slug, "level": 200, "core_level": 0,
        "hp": 1_000_000.0, "atk": 60_000.0, "def_": 3_000.0,
        "skill_levels": {"skill1": 10, "skill2": 10, "burst": 10},
    })


def _build_roster(max_units):
    slugs = [u["slug"] for u in supported_units()][:max_units]
    specs, excluded = load_roster([_nikke(s) for s in slugs])
    return specs, excluded


def _install_call_logger():
    """Wrap deck_allocation.allocate_decks so recommend_from_draft's sub-calls
    each print their wall time + roster size (recommend_from_draft looks the
    name up in its module globals, so patching the attribute intercepts it)."""
    real = da.allocate_decks
    calls = []

    def logged(roster, boss, **kw):
        draft = kw.get("draft")
        locked = kw.get("locked", frozenset())
        tag = ("scratch/locked-seed" if draft and locked else
               "warm(draft)" if draft else "scratch(no-draft)")
        t0 = time.perf_counter()
        out = real(roster, boss, **kw)
        dt = time.perf_counter() - t0
        calls.append((tag, len(roster), dt))
        print(f"    allocate_decks[{tag}] roster={len(roster)} -> {dt:.1f}s", flush=True)
        return out

    da.allocate_decks = logged
    return real, calls


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--units", type=int, default=77, help="roster size (default 77 = full)")
    parser.add_argument("--no-profile", action="store_true", help="skip Phase A cProfile")
    args = parser.parse_args()

    specs, excluded = _build_roster(args.units)
    print(f"roster: {len(specs)} loadable units (excluded {len(excluded)})", flush=True)
    boss = BossProfile(element="Water", fight_duration=180.0)

    # ---- Phase A: cProfile one zero-base allocate_decks (parent breakdown) ----
    if not args.no_profile:
        print("\n=== Phase A: cProfile zero-base allocate_decks (workers=auto) ===", flush=True)
        pr = cProfile.Profile()
        t0 = time.perf_counter()
        pr.enable()
        da.allocate_decks(specs, boss, workers="auto")
        pr.disable()
        wall = time.perf_counter() - t0
        print(f"zero-base allocate_decks wall: {wall:.1f}s", flush=True)
        s = io.StringIO()
        pstats.Stats(pr, stream=s).sort_stats("cumulative").print_stats(30)
        print(s.getvalue(), flush=True)

    # ---- Phase B: complete-draft recommend_from_draft, per-call timed ----
    print("\n=== Phase B: recommend_from_draft on a COMPLETE draft (workers=auto) ===", flush=True)
    # Build a feasible complete draft from a fresh zero-base allocation's 5 decks.
    base = da.allocate_decks(specs, boss, workers="auto")
    by_slug = {u.slug: u for u in specs}
    draft = [[by_slug[s] for s in d["deck"]] for d in base["decks"]]
    print(f"complete draft: {len(draft)} decks x {[len(d) for d in draft]} units", flush=True)

    real, calls = _install_call_logger()
    try:
        t0 = time.perf_counter()
        da.recommend_from_draft(specs, boss, num_decks=5, draft=draft, workers="auto")
        total = time.perf_counter() - t0
    finally:
        da.allocate_decks = real
    print(f"\nrecommend_from_draft TOTAL: {total:.1f}s", flush=True)
    print("per allocate_decks call:", flush=True)
    for tag, n, dt in calls:
        print(f"  {tag:22s} roster={n:3d}  {dt:6.1f}s", flush=True)


if __name__ == "__main__":
    main()
