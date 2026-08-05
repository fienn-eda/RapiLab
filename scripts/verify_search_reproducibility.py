"""Cross-process determinism check for the deck-allocation search.

The swap hill-climb's budget is counted in candidate exchanges, not
wall-clock seconds, specifically so the same roster and boss produce the
same decks on any machine (see SWAP_CANDIDATE_BUDGET's docstring in
backend/app/deck_allocation.py). That change closes the ONE nondeterminism a
wall clock introduces, but does not by itself prove no OTHER nondeterminism
is hiding behind it - Python randomizes string-hash seeding per process, so
any dict/set iteration order that leaked into deck ordering would still
disagree between runs. This runs recommend_from_draft against the same
roster and boss twice, in two SEPARATE subprocesses under different
PYTHONHASHSEED values, and diffs their output byte-for-byte.

Run this after any change to deck_allocation.py's search/swap code, or
whenever a "why did my recommendation change between runs" report needs
hash randomization ruled in or out without reading through the whole search.

Usage (from repo root):
    python scripts/verify_search_reproducibility.py [--units 25] [--decks 2]
                                                     [--workers auto]
                                                     [--element Wind]
                                                     [--enemy-def 31784]
                                                     [--duration 180]
                                                     [--no-core]
                                                     [--elemental-interrupt]

Exits non-zero (and prints a diff) if the two runs disagree.
"""
import argparse
import difflib
import os
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.deck_search import BossProfile  # noqa: E402
from app.user_roster import load_roster  # noqa: E402
from roster_fixture import add_roster_argument, real_roster  # noqa: E402

# Arbitrary and merely distinct - the two subprocesses only need different
# string-hash seeds so a hidden dependence on iteration order would surface
# as a diff between them.
_SEED_A = "1"
_SEED_B = "2"


def _build_parser():
    p = argparse.ArgumentParser(
        description=__doc__.splitlines()[0],
        formatter_class=argparse.RawDescriptionHelpFormatter)
    add_roster_argument(p)
    p.add_argument("--decks", type=int, default=5)
    p.add_argument("--workers", default="auto",
                   help='"auto" (default), 1 for serial, or N')
    p.add_argument("--units", type=int, default=None,
                   help="cap the roster to the first N usable units, for a "
                        "quick run")
    # Same flags, defaults and help text as measure_swap_budget.py, so the
    # two tools describe the same boss the same way.
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
                        "the UI.")
    # Internal: set only on the subprocess invocations this script launches
    # of itself, so a re-invocation runs ONE allocation and prints, instead
    # of orchestrating another pair of subprocesses.
    p.add_argument("--_run-once", dest="run_once", action="store_true",
                   help=argparse.SUPPRESS)
    return p


def _run_allocation(args):
    """Load the roster, run recommend_from_draft once, print a machine-
    comparable dump: each deck's seat order, each deck's total_damage at full
    float precision, the leftover slugs, and whether the swap climb
    converged inside its candidate-exchange ceiling."""
    # Imported here, not at module scope: this path runs only inside the
    # worker subprocess, and workers > 1 constructs a SimPool. Windows spawn
    # re-imports THIS FILE in that pool's own workers, so nothing that
    # reaches a SimPool may run outside the __main__ guard below - importing
    # inside a function called only from there keeps it out of module scope,
    # where a bare import would otherwise still be harmless here but the
    # allocation call itself would not be.
    from app.deck_allocation import recommend_from_draft

    states = real_roster(args.roster, limit=args.units)
    if states is None:
        raise SystemExit(f"no synced roster at {args.roster} - see roster_fixture.py")
    specs, _dropped = load_roster(states)
    boss = BossProfile(element=args.element, core_hittable=not args.no_core,
                       enemy_def=args.enemy_def, fight_duration=args.duration,
                       elemental_interrupt_required=args.elemental_interrupt)
    workers = args.workers if args.workers == "auto" else int(args.workers)

    out = recommend_from_draft(specs, boss, num_decks=args.decks, workers=workers)
    rec = out["recommended"]

    total = 0.0
    for i, deck in enumerate(rec["decks"]):
        print(f"deck {i}: {deck['deck']}")
        print(f"  total_damage = {deck['total_damage']!r}")
        total += deck["total_damage"]
    print(f"summed total = {total!r}")
    print(f"leftover_slugs = {rec['leftover_slugs']}")
    print(f"swap_converged = {out['swap_converged']}")


def _run_subprocess(argv, seed):
    """Re-invoke this script as a FRESH process under PYTHONHASHSEED=`seed`,
    with --_run-once appended so it runs the allocation instead of
    orchestrating another pair. A real subprocess, not multiprocessing - the
    __main__ guard below is about SimPool's OWN workers, not this call."""
    env = dict(os.environ, PYTHONHASHSEED=seed)
    result = subprocess.run(
        [sys.executable, str(Path(__file__).resolve()), *argv, "--_run-once"],
        env=env, capture_output=True, text=True)
    if result.returncode != 0:
        raise SystemExit(
            f"worker under PYTHONHASHSEED={seed} failed (exit {result.returncode}):\n"
            f"{result.stderr}")
    return result.stdout


def main():
    args = _build_parser().parse_args()

    if args.run_once:
        _run_allocation(args)
        return

    # Forward the original arguments as given - _run_subprocess appends its
    # own --_run-once to each copy, so this list must not carry one already.
    forward_argv = [a for a in sys.argv[1:] if a != "--_run-once"]
    print(f"comparing PYTHONHASHSEED={_SEED_A} vs {_SEED_B}: {args.decks} decks, "
          f"workers={args.workers}, roster capped to "
          f"{args.units if args.units is not None else 'all'} units", flush=True)
    out_a = _run_subprocess(forward_argv, _SEED_A)
    out_b = _run_subprocess(forward_argv, _SEED_B)

    if out_a == out_b:
        print(out_a, end="")
        print("MATCH - byte-identical output under both hash seeds")
        return

    print(f"MISMATCH - output differs under PYTHONHASHSEED={_SEED_A} vs {_SEED_B}:")
    sys.stdout.writelines(difflib.unified_diff(
        out_a.splitlines(keepends=True), out_b.splitlines(keepends=True),
        fromfile=f"seed={_SEED_A}", tofile=f"seed={_SEED_B}"))
    raise SystemExit(1)


if __name__ == "__main__":
    main()
