"""What the swap hill-climb's canonical-order scoring actually costs.

`_swap_pass` judges a swap by scoring the deck in ONE order - the positions the
seats happen to be in. `search_best_decks`' own docstring says that is worth up
to 78% low, which is why the search scores every intra-tier ordering of every
combination. The hill-climb never got the same treatment, and the error is not
symmetric: decks arrive from the search already at their BEST ordering, while a
unit swapped into a seat may want a different one. So challengers are scored
low and get rejected. The final `best_ordering_summary` re-optimizes ordering,
which makes the REPORTED damage honest while the DECISIONS behind it were made
on understated numbers.

This measures the consequence rather than the mechanism. It runs the whole
allocation twice against the same roster and boss:

  canonical    production: the hill-climb judges on one order
  by-ordering  the hill-climb judges each candidate on its BEST intra-tier
               ordering (the same standard the search holds combinations to)

Both report through `best_ordering_summary`, so both totals already include
optimal ordering - the only difference is which decks the hill-climb chose. The
gap is what canonical-order judging leaves on the table, and it decides whether
the fix is worth building at all.

Cost: judging by ordering multiplies the swap phase's simulations by the number
of intra-tier orderings per deck (~27), so the by-ordering run takes far longer
in wall time to spend the same candidate budget. That expense is the reason
this is a one-off measurement and not how production would ship it - if the gap
is real, the shipping shape is two-stage (rank on one order, re-score a
shortlist across orderings), not this.

Usage (any cwd):
    python3 scripts/audit_swap_ordering.py [--decks 5] [--budget 1000000]
                                           [--workers auto]
"""
import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

import app.deck_allocation as da  # noqa: E402
from app.cascade import clear_fit_cache  # noqa: E402
from app.deck_search import BossProfile, _intra_tier_orderings  # noqa: E402
from app.supported_units import supported_units  # noqa: E402
from app.user_roster import load_roster  # noqa: E402
from roster_fixture import (add_roster_argument, real_roster,  # noqa: E402
                            synthetic_roster)


def _by_ordering_scorer(real_score_batch, counter):
    """`_score_batch` that returns each deck's best intra-tier ordering score.

    Every ordering of every deck goes out in ONE batch so the pool still sees a
    wide job, rather than one small batch per deck.
    """
    def scored(decks, boss, pool):
        expanded, spans = [], []
        for deck in decks:
            orderings = list(_intra_tier_orderings(deck))
            spans.append((len(expanded), len(orderings)))
            expanded.extend(orderings)
        counter[0] += len(expanded)
        totals = real_score_batch(expanded, boss, pool)
        return [max(totals[start:start + n]) for start, n in spans]
    return scored


def _run(specs, boss, decks, budget, workers, by_ordering):
    """One allocation. `by_ordering` swaps the scorer in for the swap phase only,
    so the peel and the final polish stay exactly production's."""
    clear_fit_cache()
    real_score_batch = da._score_batch
    real_swap_pass = da._swap_pass
    sims = [0]

    if by_ordering:
        def swap_pass(*args, **kwargs):
            da._score_batch = _by_ordering_scorer(real_score_batch, sims)
            try:
                return real_swap_pass(*args, **kwargs)
            finally:
                da._score_batch = real_score_batch
        da._swap_pass = swap_pass
    try:
        started = time.perf_counter()
        out = da.allocate_decks(specs, boss, num_decks=decks,
                                swap_budget=budget, workers=workers)
        elapsed = time.perf_counter() - started
    finally:
        da._score_batch = real_score_batch
        da._swap_pass = real_swap_pass
    total = sum(d["total_damage"] for d in out["decks"])
    return out, total, elapsed, sims[0]


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    add_roster_argument(p)
    p.add_argument("--decks", type=int, default=5)
    p.add_argument("--budget", type=int, default=da.SWAP_CANDIDATE_BUDGET,
                   help="swap budget per run, in candidate exchanges (default: "
                        "the production ceiling, large enough that both runs "
                        "converge instead of being cut off)")
    p.add_argument("--workers", default="auto")
    p.add_argument("--units", type=int, default=None)
    p.add_argument("--synthetic", action="store_true")
    # The answer is one number on one landscape, so vary the boss before
    # trusting it: element decides who has elemental advantage and duration
    # decides how many burst cycles a deck gets, which is what reorders decks.
    p.add_argument("--element", default="Water")
    p.add_argument("--duration", type=float, default=180.0)
    args = p.parse_args()
    workers = args.workers if args.workers == "auto" else int(args.workers)

    states = None if args.synthetic else real_roster(args.roster, limit=args.units)
    source = "real synced roster"
    if states is None:
        states = synthetic_roster(args.units, supported_units())
        source = "synthetic (uniform investment)"
    specs, _ = load_roster(states)
    boss = BossProfile(element=args.element, fight_duration=args.duration)
    print(f"roster {len(specs)} loadable of {len(states)} ({source}); "
          f"{args.decks} decks; boss {args.element}/{args.duration:.0f}s; "
          f"swap budget {args.budget:,} candidates; workers={workers}", flush=True)

    results = {}
    for label, by_ordering in (("canonical", False), ("by-ordering", True)):
        out, total, elapsed, sims = _run(specs, boss, args.decks, args.budget,
                                         workers, by_ordering)
        results[label] = total
        extra = f", {sims} ordering sims" if sims else ""
        print(f"\n{label}: {total:.6g} total in {elapsed:.0f}s{extra}", flush=True)
        for i, d in enumerate(out["decks"]):
            print(f"  deck {i}: {d['total_damage']:>12.6g}  {d['deck']}", flush=True)

    gain = results["by-ordering"] / results["canonical"] - 1
    print(f"\njudging swaps by best ordering: {gain:+.2%} total damage", flush=True)
    print("A gain near zero means canonical-order judging is good enough and the "
          "follow-up can be closed; a large one sizes the two-stage design.",
          flush=True)


if __name__ == "__main__":
    main()
