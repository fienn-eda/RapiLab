"""The whole calibration table in one run - every deck, every unit, one number.

Why this exists: per-unit ratios were being quoted from a table in
docs/roadmap.md that nobody could reproduce, because the record's deck list
lived only in old conversations. `raid_record.py` now holds the record and this
script scores the simulator against all of it, so "Cinderella reads 0.88x" is a
command anyone can re-run rather than a number copied forward.

Use `measure_deck_breakdown.py` instead when you want one deck's per-SOURCE
split (burst vs normal_attack vs per_shot_nuke) to chase a specific unit. This
script is the wide view: which decks and units are off, and by how much.

Usage (any cwd):
    python3 scripts/measure_record_calibration.py
    python3 scripts/measure_record_calibration.py --deck deck2
    python3 scripts/measure_record_calibration.py --element Water   # what-if
    python3 scripts/measure_record_calibration.py --roster tools/collect-blablalink/roster-drafts-kr.json

`--roster` names another account's export - one blablalink account can hold a
roster on several game servers and each is exported separately (RECIPE.md).
"""
import argparse
import sys
import textwrap
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.deck_search import BossProfile, evaluate_deck, feasible_orderings  # noqa: E402
from app.user_roster import load_roster  # noqa: E402
from raid_record import (  # noqa: E402
    RECORD_BOSS, RECORD_CAVEATS, RECORD_CUBES, RECORD_DECKS, RECORD_ROTATIONS,
    deck_total)
from roster_fixture import (REAL_ROSTER_JSON, add_roster_argument,  # noqa: E402
                            real_roster)


def _states_for(slugs, by_slug):
    """Roster states for the named slugs. A MODE_VARIANTS slug
    (`cinderella-crystal-wave-mg`) is owned under its base name, so the roster
    is matched on the base and the variant slug is handed to load_roster."""
    states, missing = [], []
    for slug in slugs:
        owned = by_slug.get(slug) or _base_owner(by_slug, slug)
        if owned is None:
            missing.append(slug)
            continue
        states.append(owned.model_copy(update={"character_slug": slug}))
    return states, missing


def _record_roster(states):
    """load_roster, plus the cube each unit actually wore in the record.

    The engine assumes a Resilience cube for everyone, which is the right
    default for a recommendation but not for scoring a fight that was fought
    with something else - see RECORD_CUBES.
    """
    specs, excluded = load_roster(states)
    for spec in specs:
        spec.cube = RECORD_CUBES.get(spec.slug, spec.cube)
    return specs, excluded


def _base_owner(by_slug, slug):
    """Longest base first, so `-crystal-wave-mg` resolves to
    `cinderella-crystal-wave` rather than to `cinderella`."""
    for base in sorted(by_slug, key=len, reverse=True):
        if slug.startswith(base + "-"):
            return by_slug[base]
    return None


def _per_unit(result):
    per_unit = defaultdict(float)
    for event in result["damage_log"]:
        per_unit[event["slug"]] += event["damage"]
    return per_unit


def measure(name, boss, by_slug):
    """(deck ratio, {slug: ratio}, {slug: weapon}, note) for one recorded deck.

    The weapon class rides along because the residual turned out to be ordered
    by it (see `_print_by_weapon`), and re-deriving it would mean assembling
    the roster a second time.

    A deck whose rotation Fienn recorded is scored on THAT rotation alone - the
    seat order he played and the bursts he actually spent. Without one, the best
    of the feasible orderings is taken and its spread reported, so the choice
    stays visible rather than hidden; that spread reached 0.793-1.081x, which is
    why the rotations were worth asking for.
    """
    record = RECORD_DECKS[name]
    states, missing = _states_for(record, by_slug)
    if missing:
        return None, f"not in the synced roster: {', '.join(missing)}"
    specs, excluded = _record_roster(states)
    if excluded:
        return None, f"not encoded / not usable: {', '.join(excluded)}"
    total = deck_total(name)

    rotation = RECORD_ROTATIONS.get(name)
    if rotation:
        by_spec = {spec.slug: spec for spec in specs}
        order = [by_spec[slug] for slug in rotation["order"]]
        if order not in list(feasible_orderings(specs)):
            return None, f"recorded seat order is not a feasible ordering: {rotation['order']}"
        result = evaluate_deck(order, boss, max_bursts=rotation["max_bursts"])
        per_unit = _per_unit(result)
        held = ", ".join(f"{slug} x{n}" for slug, n in rotation["max_bursts"].items())
        note = f"as played, bursts held: {held}" if held else "as played, every burst spent"
        return (result["total_damage"] / total,
                {slug: per_unit[slug] / rec for slug, rec in record.items()},
                _weapons(specs), note), None

    orderings = list(feasible_orderings(specs))
    if not orderings:
        return None, "no feasible burst ordering"
    scored = []
    for order in orderings:
        result = evaluate_deck(list(order), boss)
        scored.append((result["total_damage"], _per_unit(result)))
    best_total, best_per_unit = max(scored, key=lambda s: s[0])
    note = (f"seat order unrecorded, best of {len(orderings)} spanning "
            f"{min(s[0] for s in scored) / total:.3f}-{max(s[0] for s in scored) / total:.3f}x")
    return (best_total / total,
            {slug: best_per_unit[slug] / rec for slug, rec in record.items()},
            _weapons(specs), note), None


def _weapons(specs):
    return {spec.slug: (spec.weapon_stats or {}).get("weapon", "?") for spec in specs}


def _print_orderings(name, boss, by_slug):
    """Every feasible seat order for one deck, scored per unit.

    Decks 1 and 2 are still graded by taking whichever ordering totals highest,
    which is a known bias - when decks 3/4/5 were graded that way most of the
    over-reading units sat at the TOP of their own range. Recovering the real
    order needs Fienn, and this is what makes that answerable from the numbers
    rather than from memory alone: a unit whose recorded damage only one
    ordering reproduces identifies the ordering.
    """
    record = RECORD_DECKS[name]
    if name in RECORD_ROTATIONS:
        print(f"{name}: seat order already recorded "
              f"({' -> '.join(RECORD_ROTATIONS[name]['order'])})\n")
        return
    states, missing = _states_for(record, by_slug)
    if missing:
        print(f"{name}: SKIPPED - not in the synced roster: {', '.join(missing)}\n")
        return
    specs, excluded = _record_roster(states)
    if excluded:
        print(f"{name}: SKIPPED - not encoded: {', '.join(excluded)}\n")
        return
    total = deck_total(name)

    print(f"{name}   record {total / 1e9:.3f}B")
    for index, order in enumerate(feasible_orderings(specs), start=1):
        result = evaluate_deck(list(order), boss)
        per_unit = _per_unit(result)
        seats = " -> ".join(f"{spec.slug}(B{spec.burst_tier})" for spec in order)
        print(f"\n  [{index}] {result['total_damage'] / total:.3f}x   {seats}")
        for slug, rec in sorted(record.items(), key=lambda kv: -kv[1]):
            ratio = per_unit[slug] / rec
            print(f"        {slug:<34} {ratio:>6.3f}x   "
                  f"sim {per_unit[slug] / 1e9:.3f}B vs record {rec / 1e9:.3f}B")
    print()


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    add_roster_argument(p)
    p.add_argument("--deck", help="one deck name (default: all)")
    p.add_argument("--orderings", action="store_true",
                   help="for decks whose seat order was never recorded, print "
                        "every feasible ordering with its per-unit ratios so "
                        "the one actually played can be recognised")
    p.add_argument("--element", default=RECORD_BOSS["element"],
                   help="override the boss's code - for what-if sweeps only")
    args = p.parse_args()

    roster = real_roster(args.roster)
    if roster is None:
        # Naming the path matters once --roster exists: a typo and an unsynced
        # worktree fail identically, and only one of them wants the sync script.
        sys.exit(f"ERROR: no roster at {args.roster}"
                 + ("" if args.roster != REAL_ROSTER_JSON
                    else " - run scripts/sync_worktree_data.py"))
    by_slug = {state.character_slug: state for state in roster}

    # Spread rather than field-by-field: RECORD_BOSS's keys ARE BossProfile's
    # field names, so a new fact about the encounter reaches this script
    # without an edit here.
    boss = BossProfile(**{**RECORD_BOSS, "element": args.element})
    names = [args.deck] if args.deck else list(RECORD_DECKS)
    if args.deck and args.deck not in RECORD_DECKS:
        sys.exit(f"ERROR: unknown deck {args.deck!r} - have {', '.join(RECORD_DECKS)}")

    print(f"boss:   {args.element}, DEF {boss.enemy_def:,.0f}, "
          f"{boss.fight_duration:.0f}s, core hittable, parts destructible")
    print(f"roster: real synced roster ({len(roster)} units)\n")

    if args.orderings:
        for name in names:
            _print_orderings(name, boss, by_slug)
        return

    all_ratios, sim_sum, record_sum = [], 0.0, 0.0
    weapons = {}
    for name in names:
        measured, problem = measure(name, boss, by_slug)
        if problem:
            print(f"{name}   SKIPPED - {problem}\n")
            continue
        deck_ratio, ratios, deck_weapons, note = measured
        record = deck_total(name)
        sim_sum += deck_ratio * record
        record_sum += record
        print(f"{name}   {deck_ratio:.3f}x   (record {record / 1e9:.3f}B, {note})")
        for slug, ratio in sorted(ratios.items(), key=lambda kv: -abs(kv[1] - 1)):
            if slug in RECORD_CAVEATS:
                flag = "  (caveat, see below)"
            else:
                flag = "  <--" if abs(ratio - 1) >= 0.25 else ""
            print(f"      {slug:<34} {ratio:>6.3f}x{flag}")
            all_ratios.append((ratio, slug, RECORD_DECKS[name][slug]))
        print()
        weapons.update(deck_weapons)

    if record_sum:
        print(f"combined   {sim_sum / record_sum:.3f}x   "
              f"over {len(all_ratios)} units")
        # Two core terms pull this in opposite directions: the modelled spread
        # term assumes the shots were not aimed, so it under-reads a player who
        # tracks the core, while a seat that had to hit parts directly gave up
        # core hits the engine still grants. See raid_record's "What sim/record
        # is, and is not".
        print("           (aiming and parts-hitting pull this opposite ways - "
              "1.0 is not what this should read)")
        # Caveated units top this list by construction - their record does not
        # describe the modelled rotation - so leaving them in sends every
        # session after a number that cannot be fixed in the engine.
        chaseable = [r for r in all_ratios if r[1] not in RECORD_CAVEATS]
        worst = sorted(chaseable, key=lambda r: -abs(r[0] - 1))[:5]
        print("worst by ratio: " + ", ".join(f"{s} {r:.2f}x" for r, s, _ in worst)
              + f"   (excludes {len(all_ratios) - len(chaseable)} caveated)")
        within = sum(1 for r, _, _ in all_ratios if abs(r - 1) < 0.15)
        print(f"within +-15%: {within}/{len(all_ratios)}")
        _print_absolute_errors(all_ratios, record_sum)
        _print_by_weapon(all_ratios, weapons)
        _print_caveats(all_ratios)


def _print_by_weapon(all_ratios, weapons):
    """The residual rolled up by weapon class.

    Why this is in the standard output rather than a one-off: the per-unit list
    invites unit-by-unit hunts, and the 2026-08-07 Asuka investigation found the
    residual is not per-unit at all - it is ordered by weapon class, and the
    order is how fast that class fires. Chasing the top unit without this table
    is chasing one instance of a class-wide term.
    """
    chaseable = [(r, s) for r, s, _ in all_ratios if s not in RECORD_CAVEATS]
    if not chaseable or not weapons:
        return
    groups = {}
    for ratio, slug in chaseable:
        groups.setdefault(weapons.get(slug, "?"), []).append(ratio)
    print("\nby weapon class (caveated units excluded):")
    for weapon, ratios in sorted(groups.items(),
                                 key=lambda kv: -sum(kv[1]) / len(kv[1])):
        print(f"      {weapon:<5} n={len(ratios):<3} mean {sum(ratios) / len(ratios):.3f}x")


def _print_caveats(all_ratios):
    present = [slug for _, slug, _ in all_ratios if slug in RECORD_CAVEATS]
    if not present:
        return
    print("\ncaveated - the record, not the encoding, is what these measure:")
    for slug in sorted(set(present)):
        print(f"  {slug}")
        for line in textwrap.wrap(RECORD_CAVEATS[slug], 72):
            print(f"      {line}")


def _print_absolute_errors(all_ratios, record_sum):
    """Units ranked by how much damage the miss is WORTH, not by its ratio.

    A ratio divides by the unit's own recorded damage, so it makes the roster's
    smallest contributors look like its worst problems: Ade reads 1.63x - the
    worst ratio there is - on 0.102B, which is +0.064B, less than a quarter of
    what the median row here is worth. Ranking by ratio therefore sends every
    calibration session after the cheapest rows on the board. Sorting by
    absolute error is what puts the expensive ones first, and it is the order
    Fienn asked to work in (2026-07-27). See docs/insights.md for why the two
    orders disagree so violently (ratio correlates with recorded damage at
    r = -0.56).
    """
    errors = [(ratio * record - record, slug, record, ratio)
              for ratio, slug, record in all_ratios
              if slug not in RECORD_CAVEATS]
    print("\nby absolute error (sim - record), the order to work in "
          "(caveated units left out):")
    for delta, slug, record, ratio in sorted(errors, key=lambda e: -abs(e[0]))[:10]:
        print(f"      {slug:<34} {delta / 1e9:>+7.3f}B   "
              f"({ratio:.3f}x of {record / 1e9:.3f}B, {abs(delta) / record_sum:>5.1%} of the run)")
    under = sum(d for d, _, _, _ in errors if d < 0)
    over = sum(d for d, _, _, _ in errors if d > 0)
    # Caveated units are out of these sums too, so they are not comparable with
    # the totals recorded before 2026-07-29 (ark-ranger alone was +0.196B).
    print(f"      {'':<34} 미달 합계 {under / 1e9:+.3f}B · 과대 합계 {over / 1e9:+.3f}B"
          f"  (chaseable only)")


if __name__ == "__main__":
    main()
