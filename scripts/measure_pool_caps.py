"""Does a WIDER candidate pool produce a better five-deck recommendation?

The cascade cuts the roster to `cascade.WIDE_TIER_CAPS` units per burst tier
before it ranks combinations, so every guard that exists to save a unit from
that cut - SYNERGY_SETS' pair scoring and its companion pull-in - is really
buying pool membership. This sweeps the cap directly, which bounds what ANY
such guard can be worth: if seating everybody changes nothing, no curated pair
can either.

Reports the summed damage of all five decks, because that is the objective
(see measure_swap_budget.py). A wider pool costs a bigger matrix multiply and
a bigger combination enumeration, not more simulations - the shortlist handed
to the simulator stays at DEFAULT_TOP_K - so wall time is reported too.

Caps are given as B1/B2/B3. "all" seats the whole roster at every tier, the
ceiling no guard can beat; it enumerates every legal combination in Python and
is much slower than the others.

Usage (any cwd):
    python3 scripts/measure_pool_caps.py [--caps 4/6/12,6/9/18,8/12/24,all]
                                         [--exclude slug,slug] [--workers auto]
"""
import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

import app.cascade as cascade  # noqa: E402
from app.deck_allocation import allocate_decks  # noqa: E402
from app.deck_search import BossProfile  # noqa: E402
from app.user_roster import load_roster  # noqa: E402
from roster_fixture import add_roster_argument, real_roster  # noqa: E402


def _parse_caps(text, specs):
    if text == "all":
        return {t: sum(1 for u in specs if u.burst_tier == t) for t in (1, 2, 3)}
    b1, b2, b3 = (int(x) for x in text.split("/"))
    return {1: b1, 2: b2, 3: b3}


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    add_roster_argument(p)
    p.add_argument("--caps", default="4/6/12,6/9/18,8/12/24",
                   help="B1/B2/B3 pool caps to sweep, comma separated; "
                        "'all' seats the whole roster (default 4/6/12 is "
                        "production's WIDE_TIER_CAPS)")
    p.add_argument("--decks", type=int, default=5)
    p.add_argument("--budget", type=float, default=45.0,
                   help="swap budget in seconds (default: production's 45)")
    p.add_argument("--workers", default="auto")
    p.add_argument("--exclude", default="")
    p.add_argument("--element", default="Wind",
                   choices=["Fire", "Water", "Wind", "Iron", "Electric"])
    p.add_argument("--enemy-def", type=float, default=31784.0)
    p.add_argument("--duration", type=float, default=180.0)
    p.add_argument("--no-core", action="store_true")
    args = p.parse_args()

    workers = args.workers if args.workers == "auto" else int(args.workers)
    excluded = {s.strip() for s in args.exclude.split(",") if s.strip()}
    states = real_roster(args.roster)
    if states is None:
        raise SystemExit(f"no synced roster at {args.roster}")
    specs, dropped = load_roster([s for s in states
                                  if s.character_slug not in excluded])
    boss = BossProfile(element=args.element, core_hittable=not args.no_core,
                       enemy_def=args.enemy_def, fight_duration=args.duration)

    print(f"roster {len(specs)} usable ({len(dropped)} unloadable, "
          f"{len(excluded)} excluded); {args.decks} decks; "
          f"swap budget {args.budget:.0f}s; workers={workers}")
    print(f"{'caps':>12} {'combined total':>18} {'vs production':>14} {'wall':>8}")

    production = None
    original = cascade.WIDE_TIER_CAPS
    for text in args.caps.split(","):
        caps = _parse_caps(text.strip(), specs)
        cascade.WIDE_TIER_CAPS = caps
        # Cascade defaults its `caps` field to None and reads WIDE_TIER_CAPS at
        # call time, so rebinding the module attribute is enough - but the fit
        # cache is keyed on roster+boss only, which is what we want here: the
        # model is identical across cap settings, only the pool changes.
        started = time.perf_counter()
        try:
            out = allocate_decks(specs, boss, num_decks=args.decks,
                                 time_budget_sec=args.budget, workers=workers)
        finally:
            cascade.WIDE_TIER_CAPS = original
        elapsed = time.perf_counter() - started
        total = sum(d["total_damage"] for d in out["decks"])
        if production is None:
            production = total
        label = f"{caps[1]}/{caps[2]}/{caps[3]}"
        print(f"{label:>12} {total:>18,.0f} {total / production - 1:>+13.2%} "
              f"{elapsed:>7.0f}s", flush=True)


if __name__ == "__main__":
    main()
