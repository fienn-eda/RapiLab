"""Benchmark one evaluate_deck call (a full 180 s raid simulation).

Why: deck-search cost = (number of sims) x (per-sim cost). This measures the
second factor so search-budget constants (candidate-pool size M, permutation
top-K, allocation swap budget) can be tuned against real numbers instead of
guesses. Run after any engine perf change and record the result in
docs/roadmap.md. Baseline before the segment-table rewrite (2026-07-17):
~2410 ms/sim, 93% of it in EffectRegistry.total_for linear scans.

Usage (any cwd):
    python3 scripts/bench_evaluate_deck.py [-n CALLS]
"""
import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app.models import UserNikkeState  # noqa: E402
from app.user_roster import load_roster  # noqa: E402
from app.deck_search import BossProfile, evaluate_deck, feasible_orderings  # noqa: E402

# Loadable tier-1/2/3 mix with heavy per-shot activity (MG attackers).
SLUGS = ["little-mermaid", "arcana", "grave", "drake", "modernia"]


def _nikke(slug):
    return UserNikkeState.model_validate({
        "character_slug": slug, "level": 200, "core_level": 0,
        "hp": 1_000_000.0, "atk": 60_000.0, "def_": 3_000.0,
        "skill_levels": {"skill1": 10, "skill2": 10, "burst": 10},
    })


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("-n", type=int, default=50, help="timed calls (default 50)")
    args = parser.parse_args()

    specs, excluded = load_roster([_nikke(s) for s in SLUGS])
    if excluded:
        sys.exit(f"ERROR: benchmark roster units failed to load: {excluded}")
    orderings = list(feasible_orderings(specs))
    if not orderings:
        sys.exit("ERROR: benchmark roster produced no feasible deck ordering")
    boss = BossProfile(element="Water", fight_duration=180.0)

    evaluate_deck(orderings[0], boss)  # warmup
    t0 = time.perf_counter()
    for i in range(args.n):
        evaluate_deck(orderings[i % len(orderings)], boss)
    per_call_ms = (time.perf_counter() - t0) / args.n * 1000

    print(f"deck: {[s.slug for s in orderings[0]]}")
    print(f"avg evaluate_deck over {args.n} calls: {per_call_ms:.2f} ms")
    for budget_s in (10, 60):
        print(f"  -> sims per {budget_s}s budget: {int(budget_s * 1000 / per_call_ms):,}")


if __name__ == "__main__":
    main()
