"""Measure how much intra-tier ordering moves a deck's damage.

Why this exists
---------------
`simulate_burst_cycle` fires the FIRST ready member of each burst tier, so the
order units sit in within a tier decides which member never bursts at all.
That is a real strategy (a (1,1,3) often runs its rightmost Burst 3 as a
buffer that never bursts; Prika must burst before Mint for Encore to hand
Mint the slot), not a tie-break - so a deck search that ranks a combination
on ONE arbitrary order mis-scores it.

This script quantifies that: for every combination of `--tier3` units it
scores all intra-tier orderings and reports the spread between the arbitrary
"canonical" (input-order) score and the best one, plus whether ranking by
canonical score preserves the true ranking. It is what justified scoring
every ordering in `search_best_decks` (2026-07-19).

When to use it
--------------
Re-run after changing burst_cycle, the deck search's scoring, or after
encoding units whose value depends on NOT bursting - to confirm the ordering
sensitivity is still handled and to re-derive the numbers in
docs/decisions.md.

Usage
-----
    python scripts/measure_intra_tier_ordering_impact.py
    python scripts/measure_intra_tier_ordering_impact.py --tier1 liter --tier2 crown \
        --tier3 modernia scarlet-black-shadow isabel --boss-element Wind
"""
import argparse
import itertools
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.deck_search import BossProfile, evaluate_deck  # noqa: E402
from app.models import UserNikkeState  # noqa: E402
from app.user_roster import load_nikke_spec  # noqa: E402

DEFAULT_TIER3 = [
    "mihara-bonding-chain", "modernia", "scarlet-black-shadow", "elegg-boom-and-shock",
    "guillotine-winter-slayer", "isabel", "julia", "liberalio",
]


def _state(slug, level, skill_level):
    return UserNikkeState(
        character_slug=slug, level=level, core_level=0, hp=1_000_000.0,
        atk=60_000.0, def_=3_000.0,
        skill_levels={"skill1": skill_level, "skill2": skill_level, "burst": skill_level},
    )


def _load(slugs, level, skill_level):
    specs = {}
    for slug in slugs:
        spec = load_nikke_spec(_state(slug, level, skill_level))
        if spec is None:
            raise SystemExit(
                f"could not load {slug!r} - is it encoded and does it have a skill-value "
                f"manifest? (see docs/encoded-nikkes.md)"
            )
        specs[slug] = spec
    return specs


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--tier1", default="liter", help="Burst 1 unit slug (default: liter)")
    parser.add_argument("--tier2", default="crown",
                        help="Burst 2 unit slug. Keep its cooldown at or under the Burst 3 "
                             "cooldown or the cycle grows long enough that one Burst 3 "
                             "monopolizes the slot (default: crown)")
    parser.add_argument("--tier3", nargs="+", default=DEFAULT_TIER3,
                        help="Burst 3 slugs to draw trios from")
    parser.add_argument("--boss-element", default="Wind")
    parser.add_argument("--enemy-def", type=float, default=8000.0)
    parser.add_argument("--fight-duration", type=float, default=180.0)
    parser.add_argument("--level", type=int, default=200)
    parser.add_argument("--skill-level", type=int, default=10)
    args = parser.parse_args()

    specs = _load([args.tier1, args.tier2] + list(args.tier3), args.level, args.skill_level)
    boss = BossProfile(element=args.boss_element, enemy_def=args.enemy_def,
                       fight_duration=args.fight_duration, gauge_charge_time=1.0, mode="auto")

    rows = []
    for trio in itertools.combinations(args.tier3, 3):
        scores = {}
        for order in itertools.permutations(trio):
            deck = [specs[args.tier1], specs[args.tier2]] + [specs[s] for s in order]
            scores[order] = evaluate_deck(deck, boss)["total_damage"]
        canonical = scores[trio]
        best_order, best = max(scores.items(), key=lambda kv: kv[1])
        rows.append((trio, canonical, best, best_order, (best - canonical) / canonical * 100))

    spreads = sorted(row[4] for row in rows)
    over_ten = sum(1 for s in spreads if s > 10)
    print(f"combinations measured: {len(rows)}  ({len(rows) * 6} sims)")
    print(f"spread of best vs canonical order: median {spreads[len(spreads) // 2]:.1f}%  "
          f"max {spreads[-1]:.1f}%  over 10%: {over_ten}/{len(spreads)}")

    by_best = sorted(rows, key=lambda row: row[2], reverse=True)
    canonical_rank = {row[0]: i for i, row in enumerate(sorted(rows, key=lambda r: r[1], reverse=True))}
    print("\ntrue top 5 (by best ordering), and where canonical-order scoring ranked them:")
    for i, row in enumerate(by_best[:5], start=1):
        trio, _canonical, best, best_order, spread = row
        print(f"  #{i:<2d} {'+'.join(s.split('-')[0] for s in trio):42s} "
              f"best={best:14,.0f} (+{spread:.1f}%)  as {'+'.join(s.split('-')[0] for s in best_order)}"
              f"  canonical rank #{canonical_rank[trio] + 1}")


if __name__ == "__main__":
    main()
