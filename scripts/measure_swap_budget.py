"""What the swap phase's time budget buys, measured on the thing we actually
want: the SUMMED damage of all five decks.

`measure_swap_phase.py` answers "what does the phase get done inside 45s" in
candidates and sims. This answers the question those numbers only hint at: is
the 45s budget leaving damage on the table, and how much more would a bigger
one recover? Sweep the budget, print the combined total, and say whether the
hill-climb converged or was cut off - a run that converges has stopped
improving, so a longer budget cannot help it and the number is a ceiling.

Budget 0 is included by default as the peel-only baseline: allocate_decks
returns a valid allocation with no budget at all, so it isolates what the
climb contributes from what greedy peeling already had.

Why sum rather than per-deck: the five decks are fielded together against one
boss, so the total is the objective. Improving a single deck's search can move
the total the WRONG way - a better deck found early spends units the later
decks needed (measured 2026-08-02: shape-diversifying the shortlist found a
deck worth 8.47B one peel earlier and cost 0.51% of the total).

Runs against the real synced roster; the boss defaults to the one Fienn's
2026-08-02 report used, so its numbers are reproducible.

Usage (any cwd):
    python3 scripts/measure_swap_budget.py [--budgets 0,45,90,180]
                                           [--decks 5] [--workers auto]
                                           [--exclude slug,slug] [--element Wind]
"""
import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import app.deck_allocation as da  # noqa: E402
from app.deck_search import BossProfile  # noqa: E402
from app.elements import weakness_of  # noqa: E402
from app.user_roster import load_roster  # noqa: E402
from roster_fixture import add_roster_argument, real_roster  # noqa: E402


def _timed_swap_pass(original, record):
    def wrapped(*a, **kw):
        started = time.perf_counter()
        try:
            return original(*a, **kw)
        finally:
            record.append(time.perf_counter() - started)
    return wrapped


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    add_roster_argument(p)
    p.add_argument("--budgets", default="0,45,90,180",
                   help="swap budgets in seconds, comma separated "
                        "(default 0,45,90,180; 45 is production's)")
    p.add_argument("--decks", type=int, default=5)
    p.add_argument("--workers", default="auto",
                   help='"auto" (default), 1 for serial, or N')
    p.add_argument("--exclude", default="",
                   help="comma-separated slugs to leave out of the roster, "
                        "the way the app's exclusion list does")
    # The boss's OWN element, which is NOT what the app asks for - its picker
    # takes the WEAKNESS and converts. A 수냉 약점 boss is `--element Fire`.
    p.add_argument("--element", default="Wind",
                   choices=["Fire", "Water", "Wind", "Iron", "Electric"])
    p.add_argument("--enemy-def", type=float, default=31784.0)
    p.add_argument("--duration", type=float, default=180.0)
    p.add_argument("--no-core", action="store_true",
                   help="the boss cannot be core-hit (default: it can)")
    p.add_argument("--elemental-interrupt", action="store_true",
                   help="the boss gates a phase on an elemental interrupt, so "
                        "every deck must hold a unit of its weakness element "
                        "(the app's 속성 저지 필수 box). Off by default, like "
                        "the UI. It constrains the search, so budget answers "
                        "measured without it do not carry over.")
    args = p.parse_args()

    workers = args.workers if args.workers == "auto" else int(args.workers)
    budgets = [float(b) for b in args.budgets.split(",")]
    excluded = {s.strip() for s in args.exclude.split(",") if s.strip()}

    states = real_roster(args.roster)
    if states is None:
        raise SystemExit(f"no synced roster at {args.roster} - see roster_fixture.py")
    states = [s for s in states if s.character_slug not in excluded]
    specs, dropped = load_roster(states)
    boss = BossProfile(element=args.element, core_hittable=not args.no_core,
                       enemy_def=args.enemy_def, fight_duration=args.duration,
                       elemental_interrupt_required=args.elemental_interrupt)

    print(f"roster {len(specs)} usable ({len(dropped)} unloadable, "
          f"{len(excluded)} excluded); {args.decks} decks; workers={workers}")
    gimmick = (f"약점 {weakness_of(args.element)} 필수"
               if args.elemental_interrupt else "off")
    print(f"boss {args.element} def={args.enemy_def:,.0f} {args.duration:.0f}s "
          f"core={'no' if args.no_core else 'yes'} 속성저지={gimmick}\n")
    print(f"{'budget':>8} {'combined total':>18} {'vs peel':>9} "
          f"{'swap took':>10} {'end-to-end':>11}  converged")

    baseline = None
    original = da._swap_pass
    for budget in budgets:
        elapsed = []
        da._swap_pass = _timed_swap_pass(original, elapsed)
        started = time.perf_counter()
        try:
            out = da.allocate_decks(specs, boss, num_decks=args.decks,
                                    time_budget_sec=budget, workers=workers)
        finally:
            da._swap_pass = original
        # What the player actually waits for: the peel is unbudgeted, so a
        # bigger swap budget does not buy time one-for-one and the ceiling has
        # to be chosen against THIS column, not against `swap took`.
        end_to_end = time.perf_counter() - started
        total = sum(d["total_damage"] for d in out["decks"])
        if baseline is None:
            baseline = total
        took = elapsed[0] if elapsed else 0.0
        # Converged means the climb ran out of improving swaps before the
        # deadline, so a larger budget cannot change this row.
        converged = budget == 0 or took < budget * 0.99
        print(f"{budget:>7.0f}s {total:>18,.0f} {total / baseline - 1:>+8.2%} "
              f"{took:>9.1f}s {end_to_end:>10.1f}s  "
              f"{'yes' if converged else 'NO - cut off'}", flush=True)


if __name__ == "__main__":
    main()
