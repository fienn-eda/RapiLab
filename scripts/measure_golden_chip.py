"""Soda: Twinkling Bunny's Golden Chip stack count through a fight, per deck.

Her burst spends 17 chip (floored at 1) and a Full Burst refills only a few, so
the count DRAINS - which cycles clear the >=30 ATK gate is a property of the
whole deck's burst schedule, not of Soda alone. That makes "how many stacks does
she have when it matters" a question only a simulated fight can answer, and the
answer moves with the company she keeps.

The first thing it answers is whether she bursts AT ALL: only one Burst-3 unit
takes the seat per cycle, so in a deck with two other Burst 3s the scheduler may
never pick her - and a Golden Chip with no spend point sits pinned at its cap.
`--soda-bursts` scores the opposite extreme (the other Burst 3s hold, she takes
every seat) so the drain is visible; read the two totals as bracketing the real
run, not as a fair comparison, since holding a burst removes its damage too.

Per burst cycle it prints who took the Burst-3 seat and Soda's chip an instant
before it - what her own burst would spend, and what Beginner's Rewards reads
on entering Burst Stage 3 (that extension is NOT modeled; the column is there
to size what the deferral costs - see `soda_twinkling_bunny.py`).

Usage (any cwd):
    python3 scripts/measure_golden_chip.py --deck a,b,c,d,e
    python3 scripts/measure_golden_chip.py --deck a,b,c,d,e --soda-bursts
"""
import argparse
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.deck_search import BossProfile, evaluate_deck, feasible_orderings  # noqa: E402
from app.squad_engine import SquadContext  # noqa: E402
from app.user_roster import load_roster  # noqa: E402
from raid_record import RECORD_BOSS, RECORD_CUBES  # noqa: E402
from roster_fixture import real_roster  # noqa: E402

SODA = "soda-twinkling-bunny"
CAP = 50
ATK_GATE = 30       # Onward, Soda! stage 3: ATK +65.25%/15s
HIT_RATE_GATE = 20  # stage 2: Hit Rate (inert - the engine consumes no hit rate)
EXT_I, EXT_II = 10, 20  # Beginner's Rewards stages (NOT modeled - see docstring)


def _run(deck, boss, max_bursts=None):
    """Score `deck` while capturing Soda's chip machinery. Returns the result,
    the SquadContext (so the chip can be queried at any instant afterward), the
    reset log and the fill times."""
    captured = {}
    resets, fills = [], []
    original_reset, original_fill = SquadContext.reset_resource, SquadContext.fill_resource

    def spy_reset(self, slug, name, time, pre_value, post_value):
        if slug == SODA:
            captured["ctx"] = self
            resets.append((time, pre_value, post_value))
        return original_reset(self, slug, name, time, pre_value, post_value)

    def spy_fill(self, slug, name, amount, time):
        if slug == SODA:
            captured["ctx"] = self
            fills.append(time)
        return original_fill(self, slug, name, amount, time)

    SquadContext.reset_resource, SquadContext.fill_resource = spy_reset, spy_fill
    try:
        result = evaluate_deck(list(deck), boss, max_bursts=max_bursts)
    finally:
        SquadContext.reset_resource, SquadContext.fill_resource = original_reset, original_fill
    return result, captured.get("ctx"), resets, fills


def _report(label, deck, boss, max_bursts=None):
    result, ctx, resets, fills = _run(deck, boss, max_bursts)
    per_unit = defaultdict(float)
    for event in result["damage_log"]:
        per_unit[event["slug"]] += event["damage"]

    tier3 = [e for e in result["events"] if e.get("type") == "burst" and e.get("tier") == 3]
    soda_bursts = [e["time"] for e in tier3 if e["slug"] == SODA]

    print(f"\n{'=' * 78}\n{label}\n{'=' * 78}")
    print(f"total: {result['total_damage']:,.0f}    "
          f"soda: {per_unit[SODA]:,.0f} ({per_unit[SODA] / result['total_damage']:.1%})")
    print(f"Soda bursts: {len(soda_bursts)} of {len(tier3)} Burst-3 fires    "
          f"chip fills: {len(fills)}")
    # `refill` is the fills since the previous Burst-3 fire - what the Full
    # Burst put back before this spend. It is printed because a chip pinned at
    # its cap looks exactly like one that never fills, and only this column
    # tells the two apart.
    print(f"\n{'cycle':>5} {'t (sec)':>9}  {'B3 seat':<22} {'chip':>6} {'refill':>8}  "
          f"{'ATK+65.25%':>11}  {'FB ext':>7}")
    for i, event in enumerate(tier3, 1):
        # The chip an instant BEFORE the burst - what her own burst would spend
        # and what Beginner's Rewards reads on entering Burst Stage 3.
        chip = ctx.resource_count(SODA, "chip", event["time"] - 1e-6, CAP)
        previous = tier3[i - 2]["time"] if i > 1 else 0.0
        gained = sum(1 for f in fills if previous <= f < event["time"])
        mine = event["slug"] == SODA
        gate = ("OPEN" if chip >= ATK_GATE else "shut") if mine else "-"
        ext = "+5s" if chip >= EXT_II else ("+2s" if chip >= EXT_I else "none")
        seat = event["slug"] + (" <- SODA" if mine else "")
        refill = f"+{gained}" + ("*" if chip >= CAP else "")
        print(f"{i:>5} {event['time']:9.2f}  {seat:<22} {chip:6.1f} {refill:>8}  "
              f"{gate:>11}  {ext:>7}")
    if any(ctx.resource_count(SODA, "chip", e["time"] - 1e-6, CAP) >= CAP for e in tier3):
        print(f"  * chip was at its {CAP} cap, so those fills were discarded")

    if resets:
        print(f"\nchip resets (battle start + each of her own bursts):")
        for time, pre, post in resets:
            print(f"  t={time:7.2f}   {pre:5.1f} -> {post:5.1f}")


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--deck", required=True, help="comma-separated slugs, exactly 5")
    p.add_argument("--duration", type=float, default=RECORD_BOSS["fight_duration"])
    p.add_argument("--soda-bursts", action="store_true",
                   help="also score the run where the OTHER Burst-3 units hold their "
                        "bursts, so Soda takes the seat every cycle")
    args = p.parse_args()

    slugs = [s.strip() for s in args.deck.split(",") if s.strip()]
    roster = real_roster()
    if roster is None:
        sys.exit("ERROR: no synced roster found.")
    by_slug = {s.character_slug: s for s in roster}
    missing = [s for s in slugs if s not in by_slug]
    if missing:
        sys.exit(f"ERROR: not in the synced roster: {', '.join(missing)}")
    specs, excluded = load_roster([by_slug[s] for s in slugs])
    if excluded:
        sys.exit(f"ERROR: not usable: {', '.join(excluded)}")
    for spec in specs:
        spec.cube = RECORD_CUBES.get(spec.slug, spec.cube)

    boss = BossProfile(**{**RECORD_BOSS, "fight_duration": args.duration})
    orderings = list(feasible_orderings(specs))
    if not orderings:
        sys.exit("ERROR: this 5-unit set has no feasible burst ordering.")
    best = max(orderings, key=lambda d: _run(d, boss)[0]["total_damage"])

    print(f"boss:     {boss.element}, DEF {boss.enemy_def:,.0f}, {boss.fight_duration:.0f}s, "
          f"core hittable={boss.core_hittable}")
    print(f"ordering: {' > '.join(s.slug for s in best)}  (best of {len(orderings)} feasible)")
    _report("as the scheduler plays it", best, boss)

    if args.soda_bursts:
        others = [s.slug for s in best if s.burst_tier == 3 and s.slug != SODA]
        _report(f"forcing Soda into the Burst-3 seat (held: {', '.join(others)})",
                best, boss, max_bursts={slug: 0 for slug in others})


if __name__ == "__main__":
    main()
