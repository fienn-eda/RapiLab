"""Can every deck the deck search simulates actually be simulated?

The cascade's surrogate fit draws `FIT_SAMPLE_DECKS` legal decks from the
roster and simulates all of them, so ONE deck the engine cannot evaluate
takes down the whole recommendation - a 500 out of /api/recommend-raid, not a
degraded answer. That is how the transform-window overlap crash reached
production on 2026-08-06: legal deck, legal roster, and the fight raised
"weapon mode segments overlap or are unsorted".

Input-dependent by nature, which is what makes it hard to see: the sample is
a deterministic function of the roster, so the same account crashes or does
not depending on which units are in play. Hence `--rounds`: round 0 is the
whole roster, and each later round drops a deterministic slice of it, which
redraws the sample and covers different combinations. Rounds are cheap
(FIT_SAMPLE_DECKS simulations each, no search), so this is the sweep to run
after touching burst timing, weapon transforms, or anything that changes how
fast a deck can cycle.

Reports every deck that raised, with the exception - not just the first, so
one bad interaction does not hide another.

Usage (any cwd):
    python3 scripts/check_sampled_decks_simulate.py [--rounds 8]
                                                    [--element Wind]
                                                    [--duration 180]
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.cascade import FIT_SAMPLE_DECKS, FIT_SEED  # noqa: E402
from app.deck_search import BossProfile, evaluate_deck  # noqa: E402
from app.surrogate import sample_feasible_combinations  # noqa: E402
from app.user_roster import load_roster  # noqa: E402
from roster_fixture import add_roster_argument, real_roster  # noqa: E402


def _round_roster(specs, index, rounds):
    """Round 0 is the whole roster; later rounds drop one deterministic slice.

    Slicing by sorted slug rather than by what the allocation benches keeps a
    round cheap - finding the bench costs a full five-deck search - and the
    point is only to redraw the sample, not to drop units nobody uses.
    """
    if index == 0:
        return specs, "full roster"
    ordered = sorted(specs, key=lambda unit: unit.slug)
    width = max(1, len(ordered) // rounds)
    start = (index - 1) * width
    dropped = {unit.slug for unit in ordered[start:start + width]}
    return ([unit for unit in specs if unit.slug not in dropped],
            f"minus {sorted(dropped)[0]}..{sorted(dropped)[-1]} ({len(dropped)})")


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    add_roster_argument(parser)
    parser.add_argument("--rounds", type=int, default=8,
                        help="roster variants to sample from (default 8); "
                             "round 0 is the whole roster")
    parser.add_argument("--element", default="Wind",
                        choices=["Fire", "Water", "Wind", "Iron", "Electric"])
    parser.add_argument("--enemy-def", type=float, default=31784.0)
    parser.add_argument("--duration", type=float, default=180.0)
    parser.add_argument("--no-core", action="store_true")
    args = parser.parse_args()

    states = real_roster(args.roster)
    if states is None:
        raise SystemExit(f"no synced roster at {args.roster} - see roster_fixture.py")
    specs, _ = load_roster(states)
    boss = BossProfile(element=args.element, core_hittable=not args.no_core,
                       enemy_def=args.enemy_def, fight_duration=args.duration)
    print(f"roster {len(specs)} usable; boss {args.element} "
          f"{args.duration:.0f}s; {args.rounds} rounds x "
          f"{FIT_SAMPLE_DECKS} sampled decks (seed {FIT_SEED})\n")

    failures = 0
    simulated = 0
    for index in range(args.rounds):
        subset, label = _round_roster(specs, index, args.rounds)
        combos = sample_feasible_combinations(subset, FIT_SAMPLE_DECKS, seed=FIT_SEED)
        raised = 0
        for combo in combos:
            simulated += 1
            try:
                evaluate_deck(list(combo), boss)
            except Exception as exc:  # noqa: BLE001 - reporting them IS the job
                raised += 1
                failures += 1
                print(f"  {[unit.slug for unit in combo]}")
                print(f"    {type(exc).__name__}: {exc}")
        print(f"round {index} ({label}): {len(combos)} decks, {raised} raised")

    print(f"\n{failures} of {simulated} sampled decks could not be simulated")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
