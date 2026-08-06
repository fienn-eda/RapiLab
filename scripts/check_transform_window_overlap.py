"""Does every weapon-transform unit survive beside a Full Burst length changer?

A weapon_mode_schedule anchored on its owner's bursts emits one window per
burst, and nothing makes her burst interval longer than her window. It was
longer by accident until 2026-08-05: a cycle cost at least
FULL_BURST_DURATION plus the gauge, which exceeded every window in the
registry. FULL_BURST_DURATION_DELTA removed that floor - Isabel's -5 sec lets
a cooldown-heavy deck cycle in 9.45 sec against Nayuta's 10-sec window - and
the fight raised instead of running (fixed 2026-08-06; the window now ends
where the next one opens).

This walks the matrix: every slug with a schedule, seated beside every slug
that changes the Full Burst length, with cooldown units to make the deck cycle
as fast as it can. A unit at the SAME burst tier as the length changer shares
its seat and bursts every OTHER cycle, so it has twice as long and cannot
overlap - which is why the crash only ever reached the two Burst 2 units.

Run it when a new transform unit is encoded, when a unit joins
FULL_BURST_DURATION_DELTA, or when anything changes how fast a deck cycles.

Usage (any cwd):
    python3 scripts/check_transform_window_overlap.py [--element Wind]
                                                      [--duration 180]
"""
import argparse
import sys
from itertools import combinations
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.deck_search import BossProfile, deck_is_valid, evaluate_deck  # noqa: E402
from app.skill_rules.registry import (  # noqa: E402
    _WEAPON_MODE_SCHEDULE_BUILDERS, FULL_BURST_DURATION_DELTA)
from app.user_roster import load_roster  # noqa: E402
from roster_fixture import add_roster_argument, real_roster  # noqa: E402

# Burst-1 cooldown holders, to pull the cycle down to where a window can be
# re-opened early. Without them the cooldowns bind before the shortened Full
# Burst does and no window overlaps whatever Isabel is doing.
COOLDOWN_CORE = ("liter", "soline-frost-ticket", "blanc", "dolla")


def _deck_around(specs, by_slug, members):
    """A legal five-unit deck holding `members`, or None if none exists.

    The members are usually four (two cooldown holders, the length changer,
    the transform unit), so this is a search for one filler - but it takes
    whatever is short, since a roster may not own both cooldown units.
    """
    seated = [by_slug[slug] for slug in members if slug in by_slug]
    if len(seated) != len(members) or len(seated) > 5:
        return None
    available = [unit for unit in specs if unit.slug not in members]
    for fillers in combinations(available, 5 - len(seated)):
        trial = seated + list(fillers)
        if deck_is_valid(trial):
            return trial
    return None


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    add_roster_argument(parser)
    parser.add_argument("--element", default="Wind",
                        choices=["Fire", "Water", "Wind", "Iron", "Electric"])
    parser.add_argument("--enemy-def", type=float, default=31784.0)
    parser.add_argument("--duration", type=float, default=180.0)
    args = parser.parse_args()

    states = real_roster(args.roster)
    if states is None:
        raise SystemExit(f"no synced roster at {args.roster} - see roster_fixture.py")
    specs, _ = load_roster(states)
    by_slug = {unit.slug: unit for unit in specs}
    boss = BossProfile(element=args.element, core_hittable=True,
                       enemy_def=args.enemy_def, fight_duration=args.duration)
    cooldown = [slug for slug in COOLDOWN_CORE if slug in by_slug][:2]
    print(f"roster {len(specs)} usable; boss {args.element} {args.duration:.0f}s; "
          f"cooldown core {cooldown}\n")

    failures = 0
    for changer, delta in sorted(FULL_BURST_DURATION_DELTA.items()):
        if changer not in by_slug:
            print(f"{changer} ({delta:+.0f}s): not owned, skipped")
            continue
        print(f"--- beside {changer} ({delta:+.0f}s Full Burst)")
        for slug in sorted(_WEAPON_MODE_SCHEDULE_BUILDERS):
            if slug not in by_slug:
                continue
            # A Burst 1 transform unit cannot sit beside two Burst 1 cooldown
            # holders - no ALLOWED_SHAPES has three - so drop them one at a
            # time rather than leave her untested. Fewer cooldown units means
            # a slower cycle and a weaker test, so say how many were used.
            for held in range(len(cooldown), -1, -1):
                deck = _deck_around(specs, by_slug,
                                    [*cooldown[:held], changer, slug])
                if deck is not None:
                    break
            if deck is None:
                print(f"  {slug:28} no legal deck holds her beside {changer}")
                continue
            note = "" if held == len(cooldown) else f"  ({held} cooldown unit(s))"
            try:
                evaluate_deck(deck, boss)
                print(f"  {slug:28} ok{note}")
            except Exception as exc:  # noqa: BLE001 - reporting them IS the job
                failures += 1
                print(f"  {slug:28} {type(exc).__name__}: {exc}")
                print(f"  {'':28} deck: {[unit.slug for unit in deck]}")

    print(f"\n{failures} combination(s) could not be simulated")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
