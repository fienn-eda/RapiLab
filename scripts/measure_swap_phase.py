"""What the swap hill-climb actually gets done inside its time budget.

The cascade pinned the search's cost to K, which leaves `_swap_pass` as the
biggest phase that never got optimized: it is serial, it never touches the
SimPool, and it stops at a wall-clock deadline rather than at convergence. Three
numbers decide what to do about it, and none of them are in the phase split:

  coverage    how many of a full pass' swap candidates it evaluates before the
              deadline (a pass it cannot finish is also a biased pass - the
              nested loops always start at deck 0, slot 0)
  gain curve  when the accepted improvements actually land. Gains that stop
              early argue for a smaller budget; gains still accruing at the
              deadline argue the phase is starved and needs batching/parallelism
  split       how the sims divide between deck-to-deck and leftover swaps

Run before changing the swap phase, and again afterwards. Sims are counted
where the batch is BUILT, in this process, so the counts stay honest under
`--workers` - unlike the phase split, which can only time a pooled run.

Runs against the real synced roster by default (see roster_fixture.py for why
the uniform-investment stand-in flatters the hill-climb).

Usage (any cwd):
    python3 scripts/measure_swap_phase.py [--decks 5] [--budget 45]
                                          [--workers auto] [--units N] [--synthetic]
"""
import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

import app.deck_allocation as da  # noqa: E402
from app.deck_allocation import _swap_is_fieldable  # noqa: E402
from app.deck_search import BossProfile  # noqa: E402
from app.supported_units import supported_units  # noqa: E402
from app.user_roster import load_roster  # noqa: E402
from roster_fixture import (add_roster_argument, real_roster,  # noqa: E402
                            synthetic_roster)


class _SwapTrace:
    """Records the swap phase's sims and accepted improvements over time."""

    def __init__(self):
        self.started = None          # set when _swap_pass begins
        self.sims = {"pair": 0, "leftover": 0}
        self.kind = None             # which _try_* is currently running
        self.checkpoints = []        # (seconds_into_swap, summed_score)
        self.accepted = 0
        self.passes = 0
        self.elapsed = 0.0
        self.candidates_per_pass = 0

    def since_start(self):
        return time.perf_counter() - self.started

    def wrap_score_batch(self, func):
        """Count the decks each batch actually simulates. Batches issued
        outside a _try_swaps call (the swap phase's own opening scores, and the
        final ordering polish) are not the hill-climb's cost and are skipped."""
        def wrapped(decks, boss, pool):
            if self.kind is not None:
                self.sims[self.kind] += len(decks)
            return func(decks, boss, pool)
        return wrapped

    def wrap_try(self, func):
        """Attribute a _try_swaps call's sims to the kind of swap it tries
        (`j is None` means the partner is the leftover bench), and checkpoint
        the summed score it leaves behind."""
        def wrapped(decks, scores, i, partner, j, *args, **kwargs):
            before = list(scores)
            self.kind = "leftover" if j is None else "pair"
            try:
                return func(decks, scores, i, partner, j, *args, **kwargs)
            finally:
                self.kind = None
                self.accepted += sum(1 for b, a in zip(before, scores) if a != b)
                self.checkpoints.append((self.since_start(), sum(scores)))
        return wrapped

    def wrap_pass(self, func, budget):
        def wrapped(decks, leftovers, boss, deadline, **kwargs):
            self.started = time.perf_counter()
            self.candidates_per_pass = _full_pass_candidates(decks, leftovers)
            try:
                return func(decks, leftovers, boss, deadline, **kwargs)
            finally:
                self.elapsed = self.since_start()
                self.hit_deadline = self.elapsed >= budget * 0.99
        return wrapped


def _full_pass_candidates(decks, leftovers):
    """Swap candidates one complete hill-climb pass would try.

    Deck-to-deck candidates cost two sims each (both decks are re-scored);
    leftover candidates cost one. Counted in candidates, not sims.

    Admissibility is asked of `_swap_is_fieldable` rather than restated here.
    This denominator IS the coverage figure, so a copy of the rule that drifts
    from the phase it measures reports a coverage the run never had - which is
    exactly what a same-tier copy did once cross-tier swaps were allowed.
    `locked` and `seated` are left out: this counts the space of a pass, and
    both of those depend on run state rather than on the decks alone.
    """
    pair = sum(1
               for i in range(len(decks))
               for j in range(i + 1, len(decks))
               for a in range(len(decks[i])) for b in range(len(decks[j]))
               if _swap_is_fieldable(decks, i, a, decks[j], b, j))
    leftover = sum(1
                   for i in range(len(decks))
                   for a in range(len(decks[i])) for k in range(len(leftovers))
                   if _swap_is_fieldable(decks, i, a, leftovers, k, None))
    return pair + leftover


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    add_roster_argument(p)
    p.add_argument("--units", type=int, default=None,
                   help="cap the roster size (default: the whole synced roster)")
    p.add_argument("--decks", type=int, default=5)
    p.add_argument("--budget", type=float, default=45.0,
                   help="swap phase time budget in seconds (default: production's 45)")
    p.add_argument("--workers", default=1,
                   help='1 (default) or "auto"/N to run the pooled path')
    p.add_argument("--synthetic", action="store_true",
                   help="uniform-investment stand-in instead of the synced roster "
                        "- only for comparing against pre-2026-07-25 numbers")
    args = p.parse_args()
    workers = args.workers if args.workers == "auto" else int(args.workers)

    states = None if args.synthetic else real_roster(args.roster, limit=args.units)
    source = "real synced roster"
    if states is None:
        states = synthetic_roster(args.units, supported_units())
        source = ("synthetic (uniform investment)" if args.synthetic
                  else "synthetic - NO synced roster saved, see roster_fixture.py")
    specs, _ = load_roster(states)
    boss = BossProfile(element="Water", fight_duration=180.0)
    print(f"roster {len(specs)} loadable of {len(states)} ({source}); "
          f"{args.decks} decks; swap budget {args.budget:.0f}s "
          f"({'serial' if workers == 1 else f'workers={workers}'})", flush=True)

    trace = _SwapTrace()
    da._score_batch = trace.wrap_score_batch(da._score_batch)
    da._try_swaps = trace.wrap_try(da._try_swaps)
    da._swap_pass = trace.wrap_pass(da._swap_pass, args.budget)

    started = time.perf_counter()
    da.allocate_decks(specs, boss, num_decks=args.decks,
                      time_budget_sec=args.budget, workers=workers)
    total_elapsed = time.perf_counter() - started

    sims = trace.sims["pair"] + trace.sims["leftover"]
    # Sims per candidate: pair swaps re-score both decks, leftover swaps one.
    tried = trace.sims["pair"] / 2 + trace.sims["leftover"]
    baseline = trace.checkpoints[0][1] if trace.checkpoints else 0.0
    final = trace.checkpoints[-1][1] if trace.checkpoints else 0.0
    # The first checkpoint is already post-improvement, so read the pre-swap
    # total off the run's own start instead of inferring it.
    print(f"\nallocation {total_elapsed:.0f}s; swap phase {trace.elapsed:.1f}s "
          f"(deadline hit: {trace.hit_deadline})", flush=True)
    print(f"swap sims {sims} (pair {trace.sims['pair']}, "
          f"leftover {trace.sims['leftover']})", flush=True)
    print(f"candidates tried ~{tried:.0f} of {trace.candidates_per_pass} "
          f"in ONE full pass = {tried / max(trace.candidates_per_pass, 1):.0%}",
          flush=True)
    print(f"accepted deck-score improvements: {trace.accepted}", flush=True)
    if baseline:
        print(f"summed damage {baseline:.4g} -> {final:.4g} "
              f"({(final / baseline - 1):+.2%} across the checkpoints)", flush=True)

    print(f"\n{'t(s)':>8}{'summed damage':>18}{'gain vs first':>15}", flush=True)
    for t, total in trace.checkpoints:
        print(f"{t:>8.1f}{total:>18.6g}{(total / baseline - 1):>14.2%}", flush=True)


if __name__ == "__main__":
    main()
