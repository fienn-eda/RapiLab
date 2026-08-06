"""Which charge-weapon Nikkes have had their fire-to-charge delay settled?

Why this exists: a charge weapon (SR/RL) may or may not pause between firing a
charged shot and starting the next charge, and it is a property of the UNIT, not
of the weapon class - Liberalio and Neon have none, Snow White has 0.4 sec. The
engine defaults to none, so a unit nobody has checked is silently modelled as
having no pause, and its damage comes out too high by however long the pause
really is. Mint was reading 1.502x of her recorded damage for exactly that
reason.

So "no delay registered" has two very different meanings - checked and found to
have none, or never checked - and this script separates them. Run it after
encoding any SR/RL Nikke.

An unchecked unit no longer sits at zero: she carries the frame-resolved 22
frames Bready and Centi share (registry.ASSUMED_CHARGE_MOTION_DELAY_SECONDS),
which is a better guess than "no pause at all" but is still a guess - the real
values run 0.34 to 0.43 and four units have none. So BOTH `assumed` and
`UNVERIFIED` are questions for Fienn, and the exit code stays non-zero while
either is non-empty.

How Fienn times one (see docs/insights.md): read the Full Burst clock at the
instant the charged bullet leaves and again when the next charge gauge starts
filling. NOT the gap between damage numbers - an RL grenade's travel time varies
with distance and contaminates those. The reading checks itself: shot-to-shot
gap must come out as charge time + delay.

Usage (any cwd):
    python3 scripts/audit_charge_motion_delay.py
    python3 scripts/audit_charge_motion_delay.py --all   # include non-charge weapons
"""
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))

from app.skill_rules.registry import (  # noqa: E402
    NO_CHARGE_MOTION_DELAY,
    TIMED_CHARGE_MOTION_DELAY,
    _BUILDERS,
    get_charge_motion_delay,
)

CHARGE_WEAPONS = ("SR", "RL")


def _weapon(slug):
    """The unit's weapon class from collected data, or None if not collected.

    A MODE_VARIANTS slug (`cinderella-crystal-wave-mg`) has no file of its own,
    so fall back to the longest base slug that does.
    """
    for candidate in _base_candidates(slug):
        for source in ("lootandwaifus", "dotgg"):
            path = ROOT / "data" / source / f"char_{candidate}.json"
            if path.exists():
                weapon = json.loads(path.read_text(encoding="utf-8")).get("weapon")
                if weapon:
                    return weapon
    return None


def _base_candidates(slug):
    parts = slug.split("-")
    for cut in range(len(parts), 0, -1):
        yield "-".join(parts[:cut])


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--all", action="store_true",
                   help="list every encoded unit, not only the charge weapons")
    args = p.parse_args()

    rows = []
    for slug in sorted(_BUILDERS):
        weapon = _weapon(slug)
        if not args.all and weapon not in CHARGE_WEAPONS:
            continue
        if slug in TIMED_CHARGE_MOTION_DELAY:
            status = "TIMED"
        elif slug in NO_CHARGE_MOTION_DELAY:
            status = "none (confirmed)"
        elif get_charge_motion_delay(slug):
            status = "assumed"
        else:
            status = "UNVERIFIED"
        rows.append((status, slug, weapon or "?", get_charge_motion_delay(slug)))

    order = {"TIMED": 0, "assumed": 1, "none (confirmed)": 2, "UNVERIFIED": 3}
    print(f"{'status':<17} {'unit':<38} {'wpn':<4} {'delay':>6}")
    for status, slug, weapon, delay in sorted(rows, key=lambda r: (order[r[0]], r[1])):
        print(f"{status:<17} {slug:<38} {weapon:<4} {delay:>6.2f}")

    unverified = [r for r in rows if r[0] == "UNVERIFIED"]
    assumed = [r for r in rows if r[0] == "assumed"]
    print(f"\n{len(rows)} charge-weapon units: "
          f"{sum(1 for r in rows if r[0] == 'TIMED')} timed, {len(assumed)} assumed, "
          f"{sum(1 for r in rows if r[0].startswith('none'))} confirmed none, "
          f"{len(unverified)} UNVERIFIED")
    unanswered = unverified + assumed
    if unanswered:
        print("\nASK FIENN whether these pause between a charged shot and the next charge.")
        print("An `assumed` row is carrying a stand-in, not an answer - it is still wrong")
        print("for whoever turns out to have no pause at all, as four checked units do.")
        print("   " + ", ".join(sorted(r[1] for r in unanswered)))
    return 1 if unanswered else 0


if __name__ == "__main__":
    sys.exit(main())
