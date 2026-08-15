"""For which untimed charge weapons does the stand-in delay actually matter?

Why this exists: 17 encoded charge weapons carry a STAND-IN fire-to-charge
delay (registry.ASSUMED_CHARGE_MOTION_DELAY_SECONDS, 22 frames) rather than a
measurement, and timing 17 units in game is expensive. The list length is not
the size of the problem - the same lesson the weapon-transform spread gap taught,
where 20 slugs turned out to be 7 and then 0. This scores each of them across
the range real delays actually span (0.34 to 0.43, from the 14 timed units) and
reports how much damage moves, so the timing effort goes where it changes an
answer.

A row's swing is an upper bound on what timing that unit can buy: measure her
and the true value lands somewhere inside the range, so the damage moves by at
most this much. Rows near zero are units the stand-in already describes well
enough - not because the delay is unimportant, but because their damage barely
depends on it.

None of these 17 appear in the recorded five decks, so calibration cannot check
this work at all; the payoff is recommendation accuracy, which is why the sweep
shell is the right measuring stick here rather than measure_record_calibration.

The control rows are the point of the `--controls` output: units with a TIMED
delay must not move at all. If they do, the patch leaked past the units under
test and every number here is meaningless.

Usage (any cwd):
    python3 scripts/measure_charge_delay_sensitivity.py
    python3 scripts/measure_charge_delay_sensitivity.py --low 0.30 --high 0.45
    python3 scripts/measure_charge_delay_sensitivity.py --json out.json
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "scripts"))

from app.skill_rules import registry  # noqa: E402
from app.user_roster import load_roster  # noqa: E402

import sweep_slug_damage as sweep  # noqa: E402
from roster_fixture import real_roster  # noqa: E402

# The span of delays actually measured on the 14 timed units. Raven's 1.01 is
# left out deliberately: she is an outlier the stand-in was never meant to cover,
# and including her would inflate every row's swing into meaninglessness.
DEFAULT_LOW = 0.34
DEFAULT_HIGH = 0.43

# Timed units used as controls - patching the untimed ones must not move these.
CONTROLS = ("mint", "prika", "ade-agent-bunny")


def _measure_at(slugs, delay, targets):
    """Damage for each slug with every TARGET unit's delay forced to `delay`.

    The registry builds `_CHARGE_MOTION_DELAY` once at import, so the stand-in
    constant cannot be re-read - the dict itself is what gets patched, and only
    for the units under test.
    """
    saved = {slug: registry._CHARGE_MOTION_DELAY.get(slug) for slug in targets}
    try:
        for slug in targets:
            registry._CHARGE_MOTION_DELAY[slug] = delay
        return {slug: sweep.measure(slug) for slug in slugs}
    finally:
        for slug, value in saved.items():
            if value is None:
                registry._CHARGE_MOTION_DELAY.pop(slug, None)
            else:
                registry._CHARGE_MOTION_DELAY[slug] = value


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--low", type=float, default=DEFAULT_LOW,
                   help=f"shortest delay to try (default {DEFAULT_LOW}, the "
                        f"smallest value measured on a real unit)")
    p.add_argument("--high", type=float, default=DEFAULT_HIGH,
                   help=f"longest delay to try (default {DEFAULT_HIGH})")
    p.add_argument("--json", metavar="PATH", help="also write the table as JSON")
    args = p.parse_args()
    if args.low >= args.high:
        sys.exit(f"ERROR: --low ({args.low}) must be below --high ({args.high})")

    targets = sorted(registry._ASSUMED_CHARGE_MOTION_DELAY)
    stand_in = registry.ASSUMED_CHARGE_MOTION_DELAY_SECONDS
    owned = {state.character_slug for state in (real_roster() or [])}
    print(f"{len(targets)} units carrying the {stand_in:.4f}s stand-in "
          f"({stand_in * 60:.0f} frames)")
    print(f"sweeping delays {args.low} .. {args.high}\n")

    measured = sorted(set(targets) | set(CONTROLS))
    low = _measure_at(measured, args.low, targets)
    high = _measure_at(measured, args.high, targets)

    rows = []
    for slug in targets:
        lo, hi = low.get(slug), high.get(slug)
        if lo is None or hi is None:
            rows.append({"slug": slug, "swing": None, "owned": slug in owned})
            continue
        # A longer delay means fewer shots, so `high` is the smaller number.
        rows.append({"slug": slug, "low_damage": lo, "high_damage": hi,
                     "swing": lo / hi - 1.0 if hi else None,
                     "owned": slug in owned})
    rows.sort(key=lambda r: -(r["swing"] or -1))

    print(f"{'unit':<34} {'@0.34':>16} {'@0.43':>16} {'swing':>8}  owned")
    for row in rows:
        if row["swing"] is None:
            print(f"{row['slug']:<34} {'(not measurable in the sweep shell)':>42}")
            continue
        print(f"{row['slug']:<34} {row['low_damage']:>16,.0f} "
              f"{row['high_damage']:>16,.0f} {row['swing']:>7.2%}"
              f"  {'yes' if row['owned'] else '-'}")

    print("\ncontrols (TIMED units - these must not move):")
    ok = True
    for slug in CONTROLS:
        lo, hi = low.get(slug), high.get(slug)
        if lo is None or hi is None:
            print(f"   {slug:<31} (not measurable)")
            continue
        moved = abs(lo - hi) > 1e-6
        ok = ok and not moved
        print(f"   {slug:<31} {lo:>16,.0f} {hi:>16,.0f}"
              f"   {'MOVED - patch leaked!' if moved else 'unchanged'}")
    if not ok:
        sys.exit("\nERROR: a timed control moved. The delays under test leaked "
                 "into units that already have a measurement, so the swings "
                 "above do not mean what they say.")

    if args.json:
        Path(args.json).write_text(json.dumps(
            {"low": args.low, "high": args.high, "stand_in": stand_in,
             "rows": rows}, indent=2), encoding="utf-8")
        print(f"\nwrote {args.json}")


if __name__ == "__main__":
    main()
