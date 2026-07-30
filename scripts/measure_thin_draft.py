"""Measure the recommendation path a player reaches by dropping a FEW chips.

Why: the fewer seats a draft fills, the more ways there are to complete it, so
the thinnest drafts are the most expensive - the exact opposite of what a user
expects, and the first thing they try. Before `best_completions` took a
simulation budget, one drafted seat on the real 77-unit roster enumerated
1,830,670 orderings (~6.5 h at 8 workers) and the request never returned.

This measures the real `recommend_from_draft` wall time for 1..5 drafted seats
and prints the completion count the search actually faced, so a regression that
re-opens the enumeration shows up as minutes, not as a silent hang.

MUST stay under `if __name__ == "__main__":` - Windows spawn re-imports this
module in every worker; reaching a SimPool at import time would fork-bomb.

Usage (any cwd):
    python3 scripts/measure_thin_draft.py [--seats 1 2 3] [--workers auto]
"""
import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.deck_search import (BossProfile, SEARCH_SIM_BUDGET,  # noqa: E402
                             _all_intra_tier_orderings, _shape_completions,
                             character_of)
from app.user_roster import load_roster  # noqa: E402
import app.deck_allocation as da  # noqa: E402
from roster_fixture import add_roster_argument, real_roster  # noqa: E402


def _draft_seats(specs, n):
    """`n` units a player would plausibly drop first: the strongest-looking of
    each tier, cycling, so every seat count exercises a different shape."""
    by_tier = {t: [u for u in specs if u.burst_tier == t] for t in (1, 2, 3)}
    order = [(3, 0), (2, 0), (1, 0), (3, 1), (2, 1)]
    return [by_tier[t][i] for t, i in order[:n]]


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    add_roster_argument(parser)
    parser.add_argument("--seats", type=int, nargs="+", default=[1, 2, 3],
                        help="drafted seat counts to measure (default 1 2 3)")
    parser.add_argument("--workers", default="auto", help='worker count or "auto"')
    args = parser.parse_args()

    states = real_roster(args.roster)
    if states is None:
        print("no synced roster (tools/collect-blablalink/roster-drafts.json); aborting")
        return 1
    specs, excluded = load_roster(states)
    boss = BossProfile(element="Water", fight_duration=180.0)
    print(f"roster: {len(specs)} loadable specs (excluded {len(excluded)}), "
          f"budget={SEARCH_SIM_BUDGET}", flush=True)

    for n in args.seats:
        seats = _draft_seats(specs, n)
        placed = {character_of(u.slug) for u in seats}
        rest = [u for u in specs if character_of(u.slug) not in placed]
        exhaustive = len(_all_intra_tier_orderings(_shape_completions(seats, rest)))

        t0 = time.perf_counter()
        out = da.recommend_from_draft(specs, boss, num_decks=5, draft=[seats],
                                      workers=args.workers)
        dt = time.perf_counter() - t0
        total = sum(d["total_damage"] for d in out["recommended"]["decks"])
        print(f"  seats={n}  exhaustive_completions={exhaustive:,}  "
              f"wall={dt:.1f}s  total_damage={total:,.0f}", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
