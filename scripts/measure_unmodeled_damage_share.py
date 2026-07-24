"""How much of a deck's real damage a static (timeline-free) scorer cannot see.

app/closed_form.py estimates a deck's damage from a single snapshot of its
buffs, so it can only account for normal attacks and burst nukes. Every other
damage source in the engine - per-shot, periodic, scheduled, instant and
resource-driven nukes - needs the shot timeline that scorer exists to avoid.

This measures that blind spot directly: simulate a sample of real decks, split
`damage_log` by source, and report both the aggregate share and the per-deck
spread. The SPREAD is the important number - a constant bias would cancel out
of a ranking, a deck-dependent one destroys it.

Re-run this after adding a damage source to the engine, or before reconsidering
a cheap formula-based scorer, to see whether the blind spot has moved. Results
as of 2026-07-24 are recorded in docs/insights.md ("Deck search").

Usage (any cwd):
    python3 scripts/measure_unmodeled_damage_share.py [--units 40] [--decks 60]
                                                      [--seed 7]
"""
import argparse
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app.deck_search import BossProfile, evaluate_deck  # noqa: E402
from app.models import UserNikkeState  # noqa: E402
from app.supported_units import supported_units  # noqa: E402
from app.surrogate import sample_feasible_combinations  # noqa: E402
from app.user_roster import load_roster  # noqa: E402

# The only two sources a buff snapshot can price without a shot timeline.
STATICALLY_MODELED = ("normal_attack", "burst")


def _nikke(slug):
    """A uniformly-invested unit, so the split reflects the ENGINE's sources
    rather than one roster's investment."""
    return UserNikkeState.model_validate({
        "character_slug": slug, "level": 200, "core_level": 0,
        "hp": 1_000_000.0, "atk": 60_000.0, "def_": 3_000.0,
        "skill_levels": {"skill1": 10, "skill2": 10, "burst": 10},
    })


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--units", type=int, default=40)
    p.add_argument("--decks", type=int, default=60)
    p.add_argument("--seed", type=int, default=7)
    args = p.parse_args()

    slugs = [u["slug"] for u in supported_units()][:args.units]
    specs, _ = load_roster([_nikke(s) for s in slugs])
    boss = BossProfile(element="Water", fight_duration=180.0)
    combos = sample_feasible_combinations(specs, args.decks, seed=args.seed)
    if not combos:
        print("ERROR: no feasible decks sampled; raise --units.", flush=True)
        sys.exit(1)
    print(f"roster {len(specs)} units; simulating {len(combos)} decks", flush=True)

    by_source = Counter()
    grand_total = 0.0
    unseen_shares = []
    for combo in combos:
        result = evaluate_deck(list(combo), boss)
        grand_total += result["total_damage"]
        unseen = 0.0
        for event in result["damage_log"]:
            by_source[event["source"]] += event["damage"]
            if event["source"] not in STATICALLY_MODELED:
                unseen += event["damage"]
        if result["total_damage"] > 0:
            unseen_shares.append(unseen / result["total_damage"])

    print("\ndamage by source (share of all damage in the sample):", flush=True)
    for source, damage in by_source.most_common():
        seen = "visible" if source in STATICALLY_MODELED else "INVISIBLE"
        print(f"  {source:<28} {damage / grand_total:>7.1%}   {seen}", flush=True)

    unseen_shares.sort()
    n = len(unseen_shares)
    print("\nper-deck share a static scorer cannot see:", flush=True)
    print(f"  min {unseen_shares[0]:.1%} | median {unseen_shares[n // 2]:.1%} "
          f"| max {unseen_shares[-1]:.1%}", flush=True)


if __name__ == "__main__":
    main()
