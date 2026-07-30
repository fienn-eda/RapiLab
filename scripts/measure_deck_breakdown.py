"""Per-unit, per-source damage for a NAMED deck - the calibration workhorse.

Why this exists: comparing the simulator against Fienn's real solo-raid record
is a per-UNIT argument ("Cinderella reads 0.61x of what she really did"), but
the engine's public surfaces only report deck totals. Every calibration session
so far rebuilt this breakdown ad hoc and threw it away, so the next session
could not reproduce the number it was asked to explain. This script is that
missing baseline.

It seats exactly the deck you name - no search, no shell, no mode-picking - so
the simulator is scored on the composition Fienn actually played rather than on
one it chose for itself. Investment comes from the synced roster by default,
because per-unit ratios are meaningless against uniform stats.

The boss defaults to the recorded Annihilio solo raid (Iron element, core
hittable, parts destructible, DEF 31,784, 180 sec) - see docs/decisions.md for
the record itself.

Usage (any cwd):
    python3 scripts/measure_deck_breakdown.py --deck liter,volume,cinderella,mint,snow-white
    python3 scripts/measure_deck_breakdown.py --deck a,b,c,d,e --record 6_500_000_000
    python3 scripts/measure_deck_breakdown.py --deck a,b,c,d,e --synthetic
"""
import argparse
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.deck_search import BossProfile, evaluate_deck, feasible_orderings  # noqa: E402
from app.models import UserNikkeState  # noqa: E402
from app.user_roster import load_roster  # noqa: E402
from raid_record import (  # noqa: E402  (the record's source of truth)
    RECORD_BOSS, RECORD_CUBES, RECORD_ROTATIONS)
from roster_fixture import add_roster_argument, real_roster  # noqa: E402


def _synthetic(slug):
    return UserNikkeState.model_validate({
        "character_slug": slug, "level": 200, "core_level": 0,
        "hp": 1_000_000.0, "atk": 60_000.0, "def_": 3_000.0,
        "skill_levels": {"skill1": 10, "skill2": 10, "burst": 10},
    })


def _states_for(slugs, use_synthetic, roster_path):
    """UserNikkeStates for the named slugs, real investment where available.

    A MODE_VARIANTS slug (`cinderella-crystal-wave-mg`) is owned under its base
    name, so the roster is matched on the base and the variant slug is handed
    to load_roster - that is what makes naming a mode on the command line work.
    """
    if use_synthetic:
        return [_synthetic(s) for s in slugs], "synthetic (all ATK 60,000, skills 10/10/10)"
    roster = real_roster(roster_path)
    if roster is None:
        return [_synthetic(s) for s in slugs], "synthetic FALLBACK - no synced roster found"
    by_slug = {state.character_slug: state for state in roster}
    states, missing = [], []
    for slug in slugs:
        owned = by_slug.get(slug) or _base_owner(by_slug, slug)
        if owned is None:
            missing.append(slug)
            continue
        states.append(owned.model_copy(update={"character_slug": slug}))
    if missing:
        sys.exit(f"ERROR: not in the synced roster: {', '.join(missing)}\n"
                 f"       pass --synthetic to measure them at uniform investment.")
    return states, f"real synced roster ({len(roster)} units)"


def _recorded_rotation(slugs):
    """The rotation Fienn played, if these five units ARE one of the recorded
    decks. Naming a recorded deck must give the same numbers as
    `measure_record_calibration.py`, so the seat order and the held bursts have
    to follow the unit set rather than being asked for on the command line."""
    for rotation in RECORD_ROTATIONS.values():
        if set(rotation["order"]) == set(slugs):
            return rotation
    return None


def _base_owner(by_slug, slug):
    """The owned state behind a variant slug, longest base first so
    `-crystal-wave-mg` resolves to `cinderella-crystal-wave`, not `cinderella`."""
    for base in sorted(by_slug, key=len, reverse=True):
        if slug.startswith(base + "-"):
            return by_slug[base]
    return None


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    add_roster_argument(p)
    p.add_argument("--deck", required=True,
                   help="comma-separated slugs, exactly the 5 units to seat")
    p.add_argument("--record", type=float, default=None,
                   help="the real recorded deck damage, to print a sim/record ratio")
    p.add_argument("--synthetic", action="store_true",
                   help="uniform stats instead of the synced roster")
    p.add_argument("--duration", type=float, default=RECORD_BOSS["fight_duration"])
    p.add_argument("--enemy-def", type=float, default=RECORD_BOSS["enemy_def"])
    p.add_argument("--element", default=RECORD_BOSS["element"])
    args = p.parse_args()

    slugs = [s.strip() for s in args.deck.split(",") if s.strip()]
    states, roster_note = _states_for(slugs, args.synthetic, args.roster)
    specs, excluded = load_roster(states)
    if excluded:
        sys.exit(f"ERROR: not encoded / not usable: {', '.join(excluded)}")
    # Score a recorded unit with the cube it actually wore, exactly as
    # measure_record_calibration does - otherwise this script and that one
    # disagree about the same deck.
    for spec in specs:
        spec.cube = RECORD_CUBES.get(spec.slug, spec.cube)

    boss = BossProfile(element=args.element, core_hittable=RECORD_BOSS["core_hittable"],
                       part_destructible=RECORD_BOSS["part_destructible"],
                       enemy_def=args.enemy_def, fight_duration=args.duration)

    rotation = _recorded_rotation(slugs)
    if rotation:
        by_spec = {spec.slug: spec for spec in specs}
        best = [by_spec[slug] for slug in rotation["order"]]
        result = evaluate_deck(best, boss, max_bursts=rotation["max_bursts"])
        held = ", ".join(f"{slug} x{n}" for slug, n in rotation["max_bursts"].items())
        ordering_note = f"as played, bursts held: {held}"
    else:
        orderings = list(feasible_orderings(specs))
        if not orderings:
            sys.exit("ERROR: this 5-unit set has no feasible burst ordering.")
        best = max(orderings, key=lambda d: evaluate_deck(list(d), boss)["total_damage"])
        result = evaluate_deck(list(best), boss)
        ordering_note = f"best of {len(orderings)} feasible"

    print(f"roster:   {roster_note}")
    print(f"boss:     {args.element}, DEF {args.enemy_def:,.0f}, {args.duration:.0f}s, "
          f"core hittable, parts destructible")
    print(f"ordering: {' > '.join(spec.slug for spec in best)}  ({ordering_note})")

    per_unit = defaultdict(lambda: defaultdict(float))
    for event in result["damage_log"]:
        per_unit[event["slug"]][event["source"]] += event["damage"]

    total = result["total_damage"]
    print(f"\ntotal: {total:,.0f}", end="")
    if args.record:
        print(f"   record {args.record:,.0f}   sim/record {total / args.record:.3f}x", end="")
    print("\n")

    for spec in best:
        sources = per_unit[spec.slug]
        unit_total = sum(sources.values())
        share = unit_total / total if total else 0.0
        print(f"{spec.slug:<34} {unit_total:>16,.0f}  {share:>6.1%}")
        for source, damage in sorted(sources.items(), key=lambda kv: -kv[1]):
            print(f"    {source:<30} {damage:>16,.0f}  {damage / unit_total:>6.1%}")


if __name__ == "__main__":
    main()
