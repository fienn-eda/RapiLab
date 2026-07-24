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

Run before changing the swap phase, and again afterwards.

Usage (any cwd):
    python3 scripts/measure_swap_phase.py [--units 78] [--decks 5] [--budget 45]
"""
import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

import app.deck_allocation as da  # noqa: E402
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

    def wrap_score(self, func):
        def wrapped(units, boss):
            if self.kind is not None:
                self.sims[self.kind] += 1
            return func(units, boss)
        return wrapped

    def wrap_try(self, func, kind):
        """Attribute the sims a _try_* call issues, and checkpoint its result."""
        def wrapped(decks, scores, *args, **kwargs):
            before = list(scores)
            self.kind = kind
            try:
                return func(decks, scores, *args, **kwargs)
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
    """Same-tier swap candidates one complete hill-climb pass would try.

    Deck-to-deck candidates cost two sims each (both decks are re-scored);
    leftover candidates cost one. Counted in candidates, not sims.
    """
    pair = sum(1
               for i in range(len(decks))
               for j in range(i + 1, len(decks))
               for a in decks[i] for b in decks[j]
               if a.burst_tier == b.burst_tier)
    leftover = sum(1
                   for deck in decks
                   for a in deck for u in leftovers
                   if a.burst_tier == u.burst_tier)
    return pair + leftover


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--units", type=int, default=78)
    p.add_argument("--decks", type=int, default=5)
    p.add_argument("--budget", type=float, default=45.0,
                   help="swap phase time budget in seconds (default: production's 45)")
    args = p.parse_args()

    slugs = [u["slug"] for u in supported_units()][:args.units]
    specs, _ = load_roster([_nikke(s) for s in slugs])
    boss = BossProfile(element="Water", fight_duration=180.0)
    print(f"roster {len(specs)} units; {args.decks} decks; "
          f"swap budget {args.budget:.0f}s (serial)", flush=True)

    trace = _SwapTrace()
    da._score = trace.wrap_score(da._score)
    da._try_pair_swaps = trace.wrap_try(da._try_pair_swaps, "pair")
    da._try_leftover_swaps = trace.wrap_try(da._try_leftover_swaps, "leftover")
    da._swap_pass = trace.wrap_pass(da._swap_pass, args.budget)

    started = time.perf_counter()
    da.allocate_decks(specs, boss, num_decks=args.decks,
                      time_budget_sec=args.budget, workers=1)
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
