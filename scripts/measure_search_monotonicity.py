"""Does a BIGGER roster produce a better five-deck recommendation?

Adding a unit the allocation does not seat cannot legitimately change the
answer, so any delta here is the search moving for no reason. The measurement
runs the full roster once for the reference, then drops disjoint sets of
BENCHED characters - taken from that reference run's own leftovers, so by
construction none of them held a seat - and re-runs.

Read it as a size, not a verdict: greedy peeling plus a local climb is a
heuristic and cannot promise monotonicity. What this answers is how much the
answer moves for input that should not move it, which is what decides whether
the wobble is worth a redesign. Measured 2026-08-06 on Fienn's roster (78
usable, Wind boss, DEF 31,784, 180 s): +0.28% / +0.22% / +0.27% / -0.51%
against a reference of 41,056,070,026 - a third of a percent, where the
figure on record was 2.09%.

Prints the dropped slugs of every set. The 2.09% on record cannot be
reproduced because nobody wrote down which units it excluded.

A hypothesis this tool has already ruled out, so nobody re-runs it: pinning
the surrogate's fit basis to the full roster and searching the subset with it.
It does restore monotonicity on the pair that motivated it, by collapsing the
subset's answer 12.5% - and that run's second deck is worse on its own terms
(6.71B against 8.57B), so the fit is mis-RANKING the space, not looking past
it. See docs/roadmap.md.

Usage (any cwd):
    python3 scripts/measure_search_monotonicity.py [--sets 4] [--drop 3]
                                                   [--element Wind] [--decks 5]
                                                   [--workers auto]
                                                   [--elemental-interrupt]
"""
import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import app.deck_allocation as da  # noqa: E402
from app.deck_search import BossProfile, character_of  # noqa: E402
from app.elements import weakness_of  # noqa: E402
from app.user_roster import load_roster  # noqa: E402
from roster_fixture import add_roster_argument, real_roster  # noqa: E402


def _allocate(specs, boss, decks, workers):
    started = time.perf_counter()
    out = da.allocate_decks(specs, boss, num_decks=decks, workers=workers)
    total = sum(deck["total_damage"] for deck in out["decks"])
    return total, out, time.perf_counter() - started


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    add_roster_argument(parser)
    parser.add_argument("--sets", type=int, default=4,
                        help="how many disjoint drop sets to try (default 4)")
    parser.add_argument("--drop", type=int, default=3,
                        help="benched characters per set (default 3)")
    parser.add_argument("--decks", type=int, default=5)
    parser.add_argument("--workers", default="auto",
                        help='"auto" (default), 1 for serial, or N')
    # The boss's OWN element, which is NOT what the app asks for - its picker
    # takes the WEAKNESS and converts. A 수냉 약점 boss is `--element Fire`.
    parser.add_argument("--element", default="Wind",
                        choices=["Fire", "Water", "Wind", "Iron", "Electric"])
    parser.add_argument("--enemy-def", type=float, default=31784.0)
    parser.add_argument("--duration", type=float, default=180.0)
    parser.add_argument("--no-core", action="store_true",
                        help="the boss cannot be core-hit (default: it can)")
    parser.add_argument("--elemental-interrupt", action="store_true",
                        help="every deck must hold a unit of the boss's "
                             "weakness element (the app's 속성 저지 필수 box). "
                             "It constrains the search, so answers measured "
                             "without it do not carry over.")
    args = parser.parse_args()

    workers = args.workers if args.workers == "auto" else int(args.workers)
    states = real_roster(args.roster)
    if states is None:
        raise SystemExit(f"no synced roster at {args.roster} - see roster_fixture.py")
    specs, unloadable = load_roster(states)
    boss = BossProfile(element=args.element, core_hittable=not args.no_core,
                       enemy_def=args.enemy_def, fight_duration=args.duration,
                       elemental_interrupt_required=args.elemental_interrupt)

    gimmick = (f"약점 {weakness_of(args.element)} 필수"
               if args.elemental_interrupt else "off")
    print(f"roster {len(specs)} usable ({len(unloadable)} unloadable); "
          f"{args.decks} decks; workers={workers}")
    print(f"boss {args.element} def={args.enemy_def:,.0f} {args.duration:.0f}s "
          f"core={'no' if args.no_core else 'yes'} 속성저지={gimmick}\n")

    reference, out, secs = _allocate(specs, boss, args.decks, workers)
    print(f"reference (full roster): {reference:,.0f}  {secs:.0f}s")

    seated = {character_of(slug) for deck in out["decks"] for slug in deck["deck"]}
    bench = sorted({character_of(slug) for slug in out["leftover_slugs"]} - seated)
    print(f"{len(bench)} benched characters to draw from\n")
    if len(bench) < args.sets * args.drop:
        print(f"only enough bench for {len(bench) // args.drop} set(s)")

    for index in range(args.sets):
        dropped = set(bench[index * args.drop:(index + 1) * args.drop])
        if len(dropped) < args.drop:
            break
        subset = [u for u in specs if character_of(u.slug) not in dropped]
        total, _, secs = _allocate(subset, boss, args.decks, workers)
        print(f"drop {sorted(dropped)}")
        print(f"  -> {total:,.0f}  {(total / reference - 1) * 100:+.2f}%  {secs:.0f}s")


if __name__ == "__main__":
    main()
