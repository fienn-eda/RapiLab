"""Where an allocate_decks run actually spends its simulations.

The cascade can only pay off if it is wired into the phase that dominates. This
attributes every evaluate_deck call in a zero-base `allocate_decks` to the phase
that issued it:

  prune       prune_candidate_pool's marginal-contribution passes (a
              reference-deck surrogate, and the cascade's safety net - it seats
              its picks first in the widened pool)
  fit         fitting the cascade's surrogate: sampled decks simulated once per
              allocation, then reused across every greedy-peel iteration
  search      scoring the intra-tier orderings the search actually judges
  swap        _swap_pass' hill-climb, which is serial and deadline-capped
  summary     the final per-deck best-ordering polish

Serial by default so every call lands in this process and the sim counts are
complete. Run before designing a cascade integration, and again afterwards to
confirm the phase actually shrank.

`--workers` measures the production path instead. Sims issued inside SimPool
workers are NOT counted (they run in other processes and never reach this
module's binding), so read the per-phase SECONDS there, not the sims - which is
the point of running it pooled: the swap phase is the only one SimPool does not
serve, so pooling is what reveals its true share of a real request.

Usage (any cwd):
    python3 scripts/measure_allocation_phase_split.py [--units 40] [--decks 5]
                                                      [--workers auto]
"""
import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

import app.cascade as cascade  # noqa: E402
import app.deck_allocation as da  # noqa: E402
import app.deck_search as ds  # noqa: E402
from app.deck_search import BossProfile  # noqa: E402
from app.models import UserNikkeState  # noqa: E402
from app.supported_units import supported_units  # noqa: E402
from app.user_roster import load_roster  # noqa: E402


def _nikke(slug):
    return UserNikkeState.model_validate({
        "character_slug": slug, "level": 200, "core_level": 0,
        "hp": 1_000_000.0, "atk": 60_000.0, "def_": 3_000.0,
        "skill_levels": {"skill1": 10, "skill2": 10, "burst": 10},
    })


class _PhaseCounter:
    """Counts evaluate_deck calls, attributing each to the innermost phase."""

    def __init__(self):
        self.phase = "search"     # anything outside a marked phase is the search
        self.counts = {}
        self.seconds = {}

    def count(self):
        self.counts[self.phase] = self.counts.get(self.phase, 0) + 1

    def wrap(self, func, phase):
        """Run `func` with `phase` marked as current, restoring it afterwards."""
        def wrapped(*args, **kwargs):
            previous = self.phase
            self.phase = phase
            started = time.perf_counter()
            try:
                return func(*args, **kwargs)
            finally:
                self.seconds[phase] = (self.seconds.get(phase, 0.0)
                                       + time.perf_counter() - started)
                self.phase = previous
        return wrapped


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--units", type=int, default=40)
    p.add_argument("--decks", type=int, default=5)
    p.add_argument("--workers", default=1,
                   help='1 (default, serial and fully counted) or "auto"/N to '
                        "time the production path - see the module docstring")
    args = p.parse_args()
    workers = args.workers if args.workers == "auto" else int(args.workers)

    slugs = [u["slug"] for u in supported_units()][:args.units]
    specs, _ = load_roster([_nikke(s) for s in slugs])
    boss = BossProfile(element="Water", fight_duration=180.0)
    how = "serial" if workers == 1 else f"workers={workers}"
    print(f"roster {len(specs)} units; allocating {args.decks} decks ({how})", flush=True)

    counter = _PhaseCounter()
    real_evaluate = ds.evaluate_deck

    def counting_evaluate(deck, profile):
        counter.count()
        return real_evaluate(deck, profile)

    ds.evaluate_deck = counting_evaluate
    # deck_allocation imported these by value, so both bindings must be replaced.
    da.evaluate_deck = counting_evaluate
    ds.prune_candidate_pool = counter.wrap(ds.prune_candidate_pool, "prune")
    # cascade imported prune by value too, and widened_pool calls it through
    # that binding - without this the safety net's cost lands under "search".
    cascade.prune_candidate_pool = counter.wrap(cascade.prune_candidate_pool, "prune")
    da.cached_fit_surrogate = counter.wrap(da.cached_fit_surrogate, "fit")
    da._swap_pass = counter.wrap(da._swap_pass, "swap")
    da.best_ordering_summary = counter.wrap(da.best_ordering_summary, "summary")

    started = time.perf_counter()
    da.allocate_decks(specs, boss, num_decks=args.decks, workers=workers)
    elapsed = time.perf_counter() - started

    total = sum(counter.counts.values())
    print(f"\ntotal simulations {total} in {elapsed:.0f}s"
          f"{'' if workers == 1 else ' (parent-side sims only)'}\n", flush=True)
    print(f"{'phase':<10}{'sims':>9}{'sims%':>9}{'seconds':>10}{'time%':>9}", flush=True)
    for phase in ("prune", "fit", "search", "swap", "summary"):
        sims = counter.counts.get(phase, 0)
        seconds = counter.seconds.get(phase, 0.0)
        print(f"{phase:<10}{sims:>9}{sims / max(total, 1):>8.1%}"
              f"{seconds:>10.0f}{seconds / elapsed:>8.1%}", flush=True)


if __name__ == "__main__":
    main()
