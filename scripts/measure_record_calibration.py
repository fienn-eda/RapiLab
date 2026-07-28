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
"""
import argparse
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.deck_search import BossProfile, evaluate_deck, feasible_orderings  # noqa: E402
from app.user_roster import load_roster  # noqa: E402
from raid_record import RECORD_BOSS, RECORD_DECKS, RECORD_ROTATIONS, deck_total  # noqa: E402
from roster_fixture import real_roster  # noqa: E402


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
    """(deck ratio, {slug: ratio}, note) for one recorded deck, or None.

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
    specs, excluded = load_roster(states)
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
        note = f"as played, bursts held: {held}"
        return (result["total_damage"] / total,
                {slug: per_unit[slug] / rec for slug, rec in record.items()}, note), None

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
            {slug: best_per_unit[slug] / rec for slug, rec in record.items()}, note), None


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--deck", help="one deck name (default: all)")
    p.add_argument("--element", default=RECORD_BOSS["element"],
                   help="override the boss's code - for what-if sweeps only")
    args = p.parse_args()

    roster = real_roster()
    if roster is None:
        sys.exit("ERROR: no synced roster found - run scripts/sync_worktree_data.py")
    by_slug = {state.character_slug: state for state in roster}

    boss = BossProfile(element=args.element,
                       core_hittable=RECORD_BOSS["core_hittable"],
                       part_destructible=RECORD_BOSS["part_destructible"],
                       enemy_def=RECORD_BOSS["enemy_def"],
                       fight_duration=RECORD_BOSS["fight_duration"])
    names = [args.deck] if args.deck else list(RECORD_DECKS)
    if args.deck and args.deck not in RECORD_DECKS:
        sys.exit(f"ERROR: unknown deck {args.deck!r} - have {', '.join(RECORD_DECKS)}")

    print(f"boss:   {args.element}, DEF {boss.enemy_def:,.0f}, "
          f"{boss.fight_duration:.0f}s, core hittable, parts destructible")
    print(f"roster: real synced roster ({len(roster)} units)\n")

    all_ratios, sim_sum, record_sum = [], 0.0, 0.0
    for name in names:
        measured, problem = measure(name, boss, by_slug)
        if problem:
            print(f"{name}   SKIPPED - {problem}\n")
            continue
        deck_ratio, ratios, note = measured
        record = deck_total(name)
        sim_sum += deck_ratio * record
        record_sum += record
        print(f"{name}   {deck_ratio:.3f}x   (record {record / 1e9:.3f}B, {note})")
        for slug, ratio in sorted(ratios.items(), key=lambda kv: -abs(kv[1] - 1)):
            flag = "  <--" if abs(ratio - 1) >= 0.25 else ""
            print(f"      {slug:<34} {ratio:>6.3f}x{flag}")
            all_ratios.append((ratio, slug, RECORD_DECKS[name][slug]))
        print()

    if record_sum:
        print(f"combined   {sim_sum / record_sum:.3f}x   "
              f"over {len(all_ratios)} units")
        worst = sorted(all_ratios, key=lambda r: -abs(r[0] - 1))[:5]
        print("worst by ratio: " + ", ".join(f"{s} {r:.2f}x" for r, s, _ in worst))
        within = sum(1 for r, _, _ in all_ratios if abs(r - 1) < 0.15)
        print(f"within +-15%: {within}/{len(all_ratios)}")
        _print_absolute_errors(all_ratios, record_sum)


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
              for ratio, slug, record in all_ratios]
    print("\nby absolute error (sim - record), the order to work in:")
    for delta, slug, record, ratio in sorted(errors, key=lambda e: -abs(e[0]))[:10]:
        print(f"      {slug:<34} {delta / 1e9:>+7.3f}B   "
              f"({ratio:.3f}x of {record / 1e9:.3f}B, {abs(delta) / record_sum:>5.1%} of the run)")
    under = sum(d for d, _, _, _ in errors if d < 0)
    over = sum(d for d, _, _, _ in errors if d > 0)
    print(f"      {'':<34} 미달 합계 {under / 1e9:+.3f}B · 과대 합계 {over / 1e9:+.3f}B")


if __name__ == "__main__":
    main()
