"""Where the sim/record residual sits, and what core hit rate would close it.

Why this exists: `measure_record_calibration.py` scores whole decks and
`measure_deck_breakdown.py` breaks ONE deck into sources. Neither answers the
question gap #21 asks - "is the overshoot in the normal-attack path, and if so
which term?" - because that needs the per-source split of all 25 recorded units
side by side with the record.

Three columns carry the argument:

    k       the factor normal-attack damage alone would need for this unit to
            land on its record, if every other source is taken as correct:
            k = (record - other_sim) / normal_sim
    f       the same for "too many shots", which also shrinks per-shot riders
            (a rider fires once per shot): f = (record - rest) / (normal + riders)
    p       the core hit rate that would land the unit on its record. The engine
            assumes every core-eligible shot hits the core; damage is linear in
            CORE_HIT_BONUS, so one run at 1.0 and one at 0.0 give every p in
            between by interpolation.

Reading them: a term shared across units shows as a shared value; a per-weapon
constant (rate of fire) shows as k sorting by weapon class; a play-condition
shows as neither, scattering within weapon class and within deck.

What this measured (2026-07-31, gap #21): k and p scatter from 0.60 to 1.24
with MG spanning 0.77-0.96 on its own, so no weapon constant explains it. f
scores WORSE than k (log-sd 0.090 vs 0.082, within-15% 19 vs 21 of 23), so the
residual is not shot count - shrinking the riders alongside overshoots. The
residual is normal-attack-ONLY, and `raid_simulator.core_eligible` makes the
core bonus the only normal-attack-only term there is.

Fienn's reading of that (2026-07-31): the recorded raid was fought on a boss
with both a core and destructible parts, and a deck that had to hit PARTS
directly gave up core hits to do it, while a deck whose area damage broke parts
incidentally kept them. So p is a property of the run, not of the engine - which
is why nothing here proposes changing CORE_HIT_BONUS.

Usage (any cwd):
    python3 scripts/measure_normal_attack_residual.py
    python3 scripts/measure_normal_attack_residual.py --roster PATH
"""
import argparse
import math
import statistics
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app import raid_simulator  # noqa: E402
from app.deck_search import BossProfile, evaluate_deck  # noqa: E402
from app.user_roster import load_roster  # noqa: E402
from raid_record import (  # noqa: E402
    RECORD_BOSS, RECORD_CAVEATS, RECORD_CUBES, RECORD_DECKS, RECORD_ROTATIONS)
from roster_fixture import add_roster_argument, real_roster  # noqa: E402

# Sources that fire once per normal-attack shot, so a shot-count error moves
# them in lockstep with the normal attacks themselves.
SHOT_LINKED_SOURCES = frozenset({"per_shot_nuke", "dynamic_hit_count_nuke"})


def _base_owner(by_slug, slug):
    """The owned state behind a variant slug, longest base first."""
    for base in sorted(by_slug, key=len, reverse=True):
        if slug.startswith(base + "-"):
            return by_slug[base]
    return None


def _run_decks(by_slug, core_hit_bonus):
    """Every recorded deck, seated as played, at the given core-hit bonus.

    Returns {slug: {source: damage}}. The bonus is a module attribute rather
    than an argument anywhere, so it is set here and restored by the caller.
    """
    raid_simulator.CORE_HIT_BONUS = core_hit_bonus
    per_unit = {}
    weapons = {}
    for records in RECORD_DECKS.values():
        states = []
        for slug in records:
            owned = by_slug.get(slug) or _base_owner(by_slug, slug)
            if owned is None:
                sys.exit(f"ERROR: not in the synced roster: {slug}")
            states.append(owned.model_copy(update={"character_slug": slug}))
        specs, excluded = load_roster(states)
        if excluded:
            sys.exit(f"ERROR: not encoded / not usable: {', '.join(excluded)}")
        for spec in specs:
            spec.cube = RECORD_CUBES.get(spec.slug, spec.cube)
        boss = BossProfile(element=RECORD_BOSS["element"],
                           core_hittable=RECORD_BOSS["core_hittable"],
                           part_destructible=RECORD_BOSS["part_destructible"],
                           enemy_def=RECORD_BOSS["enemy_def"],
                           fight_duration=RECORD_BOSS["fight_duration"])
        rotation = next(r for r in RECORD_ROTATIONS.values()
                        if set(r["order"]) == set(records))
        by_spec = {spec.slug: spec for spec in specs}
        result = evaluate_deck([by_spec[s] for s in rotation["order"]], boss,
                               max_bursts=rotation["max_bursts"])
        sources = defaultdict(lambda: defaultdict(float))
        for event in result["damage_log"]:
            sources[event["slug"]][event["source"]] += event["damage"]
        for slug in records:
            per_unit[slug] = dict(sources[slug])
            weapons[slug] = by_spec[slug].weapon
    return per_unit, weapons


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    add_roster_argument(p)
    args = p.parse_args()

    roster = real_roster(args.roster)
    if roster is None:
        sys.exit("ERROR: no synced roster - per-unit ratios need real investment.")
    by_slug = {state.character_slug: state for state in roster}

    live = raid_simulator.CORE_HIT_BONUS
    try:
        with_core, weapons = _run_decks(by_slug, live)
        without_core, _ = _run_decks(by_slug, 0.0)
    finally:
        raid_simulator.CORE_HIT_BONUS = live

    records = {slug: dmg for deck in RECORD_DECKS.values() for slug, dmg in deck.items()}
    rows = []
    for slug, record in records.items():
        sources = with_core[slug]
        normal = sources.get("normal_attack", 0.0)
        riders = sum(d for s, d in sources.items() if s in SHOT_LINKED_SOURCES)
        rest = sum(d for s, d in sources.items()
                   if s != "normal_attack" and s not in SHOT_LINKED_SOURCES)
        hi, lo = sum(sources.values()), sum(without_core[slug].values())
        rows.append(dict(
            slug=slug, record=record, sim=hi, weapon=weapons[slug],
            normal_share=normal / hi if hi else 0.0,
            core_share=(hi - lo) / hi if hi else 0.0,
            k=(record - riders - rest) / normal if normal else float("nan"),
            f=(record - rest) / (normal + riders) if normal + riders else float("nan"),
            p=(record - lo) / (hi - lo) if hi > lo else float("nan"),
            caveat=slug in RECORD_CAVEATS,
        ))

    print(f"{'unit':<32}{'wpn':>4}{'sim/rec':>9}{'NA share':>10}{'core%':>7}"
          f"{'k':>8}{'f':>8}{'p':>8}")
    print("-" * 87)
    for row in sorted(rows, key=lambda r: -(r["sim"] / r["record"])):
        mark = "  (caveat)" if row["caveat"] else ""
        print(f"{row['slug']:<32}{row['weapon']:>4}{row['sim'] / row['record']:>8.3f}x"
              f"{row['normal_share']:>9.0%}{row['core_share']:>7.0%}"
              f"{row['k']:>8.3f}{row['f']:>8.3f}{row['p']:>8.3f}{mark}")

    chaseable = [r for r in rows if not r["caveat"]]
    print("\nspread of each explanation within a weapon class "
          "(a per-class constant would show none):")
    by_weapon = defaultdict(list)
    for row in chaseable:
        by_weapon[row["weapon"]].append(row)
    for weapon, group in sorted(by_weapon.items()):
        ks = [r["k"] for r in group]
        print(f"    {weapon:<4} n={len(group)}  k {min(ks):.2f}-{max(ks):.2f}"
              f"  (spread {max(ks) - min(ks):.2f})")

    print("\nscored as one global correction, all three shapes on the same grid:")
    grid = [i / 100 for i in range(1, 121)]

    def sim_at(row, shape, value):
        """This unit's damage with one global correction of the named shape."""
        sources = with_core[row["slug"]]
        normal = sources.get("normal_attack", 0.0)
        riders = sum(d for s, d in sources.items() if s in SHOT_LINKED_SOURCES)
        rest = sum(d for s, d in sources.items()
                   if s != "normal_attack" and s not in SHOT_LINKED_SOURCES)
        lo = sum(without_core[row["slug"]].values())
        if shape == "normal-attack factor k":
            return value * normal + riders + rest
        if shape == "shot factor f":
            return value * (normal + riders) + rest
        return lo + value * (row["sim"] - lo)

    for shape in ("normal-attack factor k", "shot factor f", "core hit rate p"):
        def score(value, shape=shape):
            sims = [sim_at(r, shape, value) for r in chaseable]
            ratios = [s / r["record"] for s, r in zip(sims, chaseable)]
            return (sum(sims) / sum(r["record"] for r in chaseable),
                    statistics.pstdev([math.log(x) for x in ratios]),
                    sum(1 for x in ratios if 0.85 <= x <= 1.15))
        best = min(grid, key=lambda v: score(v)[1])
        combined, sd, within = score(best)
        print(f"    {shape:<24} best {best:.2f}  ->  combined {combined:.3f}x  "
              f"log-sd {sd:.3f}  within15 {within}/{len(chaseable)}")
    base = [r["sim"] / r["record"] for r in chaseable]
    print(f"    {'engine as it stands':<24} {'':9}  ->  combined "
          f"{sum(r['sim'] for r in chaseable) / sum(r['record'] for r in chaseable):.3f}x  "
          f"log-sd {statistics.pstdev([math.log(x) for x in base]):.3f}  "
          f"within15 {sum(1 for x in base if 0.85 <= x <= 1.15)}/{len(chaseable)}")


if __name__ == "__main__":
    main()
