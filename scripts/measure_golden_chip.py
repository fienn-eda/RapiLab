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

Per burst cycle it prints who took the Burst-3 seat, Soda's chip an instant
before it - what her own burst would spend, and what Beginner's Rewards reads on
entering Burst Stage 3 - and the Full Burst window that chip bought. The window
is read back out of the simulation rather than predicted from the thresholds, so
the column disagrees with the chip if the extension ever stops being derived
from it.

`--hold` is what reproduces Fienn's in-play rotation. With three Burst-3 units
the scheduler may hand every seat to the other two; holding ONE of them leaves
Soda alternating with the other, which is how the fight in
`docs/measurements/soda-golden-chip-in-play.md` was actually played. That
rotation is the one whose chip band (50 -> 33 -> 42 -> 50) matches the reading -
`--soda-bursts` holds ALL the others and so removes the intervening cycles
entirely, which is a different operating pattern, not a slower version of it.

Usage (any cwd):
    python3 scripts/measure_golden_chip.py --deck a,b,c,d,e
    python3 scripts/measure_golden_chip.py --deck a,b,c,d,e --soda-bursts
    python3 scripts/measure_golden_chip.py --deck a,b,c,d,e --hold some-other-b3
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
    windows = list(zip(
        (e["time"] for e in result["events"] if e["type"] == "full_burst_start"),
        (e["time"] for e in result["events"] if e["type"] == "full_burst_end"),
    ))

    print(f"\n{'=' * 78}\n{label}\n{'=' * 78}")
    print(f"total: {result['total_damage']:,.0f}    "
          f"soda: {per_unit[SODA]:,.0f} ({per_unit[SODA] / result['total_damage']:.1%})")
    print(f"Soda bursts: {len(soda_bursts)} of {len(tier3)} Burst-3 fires    "
          f"chip fills: {len(fills)}    "
          f"fixed point: {result['full_burst_passes']}")
    # `refill` is the fills since the previous Burst-3 fire - what the Full
    # Burst put back before this spend. It is printed because a chip pinned at
    # its cap looks exactly like one that never fills, and only this column
    # tells the two apart.
    print(f"\n{'cycle':>5} {'t (sec)':>9}  {'B3 seat':<22} {'chip':>6} {'refill':>8}  "
          f"{'ATK+65.25%':>11}  {'FB window':>9}")
    for i, event in enumerate(tier3, 1):
        # The chip an instant BEFORE the burst - what her own burst would spend
        # and what Beginner's Rewards reads on entering Burst Stage 3.
        chip = ctx.resource_count(SODA, "chip", event["time"] - 1e-6, CAP)
        previous = tier3[i - 2]["time"] if i > 1 else 0.0
        gained = sum(1 for f in fills if previous <= f < event["time"])
        mine = event["slug"] == SODA
        gate = ("OPEN" if chip >= ATK_GATE else "shut") if mine else "-"
        # The window this cycle actually got, taken from the simulation. A cycle
        # whose window never opened prints "-" rather than borrowing a neighbour's.
        window = (f"{windows[i - 1][1] - windows[i - 1][0]:.2f}s"
                  if i <= len(windows) else "-")
        seat = event["slug"] + (" <- SODA" if mine else "")
        refill = f"+{gained}" + ("*" if chip >= CAP else "")
        print(f"{i:>5} {event['time']:9.2f}  {seat:<22} {chip:6.1f} {refill:>8}  "
              f"{gate:>11}  {window:>9}")
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
    p.add_argument("--hold", default="",
                   help="comma-separated slugs whose burst is held. Holding one of two "
                        "other Burst-3 units leaves Soda alternating with the remaining "
                        "one - Fienn's in-play rotation")
    args = p.parse_args()

    slugs = [s.strip() for s in args.deck.split(",") if s.strip()]
    held = [s.strip() for s in args.hold.split(",") if s.strip()]
    stray = [s for s in held if s not in slugs]
    if stray:
        sys.exit(f"ERROR: --hold names units that are not in --deck: {', '.join(stray)}")
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

    if held:
        _report(f"holding {', '.join(held)}", best, boss,
                max_bursts={slug: 0 for slug in held})

    if args.soda_bursts:
        others = [s.slug for s in best if s.burst_tier == 3 and s.slug != SODA]
        _report(f"forcing Soda into the Burst-3 seat (held: {', '.join(others)})",
                best, boss, max_bursts={slug: 0 for slug in others})


if __name__ == "__main__":
    main()
