"""What Flora's Petunia "stack count +1" is worth, per holder.

Petunia's 2nd bullet raises the CURRENT stack count of every Electric ally's
stackable buffs by 1, every 100 of Flora's normal attacks. Whether that is worth
anything depends entirely on whether the holder's counter sits below its cap -
a stack the engine already pins at its maximum gains nothing.

Run this after touching Flora, `ResourceSpec.stackable_buff`, or any holder's
fill rate. It keeps the deck FIXED and toggles only the contribution, so the
number is the bullet's own worth and not a deck comparison.

    python scripts/measure_flora_stack_bump.py
    python scripts/measure_flora_stack_bump.py --flora flora-signature

Reads the encoded roster directly; needs no collected data dump.
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app.deck_search import (  # noqa: E402
    BossProfile, deck_is_valid, evaluate_deck, feasible_orderings,
)
from app.models import UserNikkeState  # noqa: E402
from app.skill_rules import registry  # noqa: E402
from app.user_roster import load_roster  # noqa: E402

# 보유자별 덱메이트 셋. 플로라가 넷째로 붙어 5인이 되고, 티어 구성이 합법이어야
# 하므로 보유자의 버스트 티어에 따라 짝이 다르다(츠바이는 B1이라 B3이 하나 더 든다).
HOLDER_DECKMATES = {
    "cinderella": ["crown", "liter", "helm"],
    # Frame Analysis의 크리 스택은 애장품 불릿이라 시그니처 빌드에만 있다.
    "zwei-signature": ["crown", "helm", "red-hood"],
    "maiden-ice-rose": ["crown", "liter", "helm"],
}


def _nikke(slug):
    return UserNikkeState.model_validate({
        "character_slug": slug, "level": 200, "core_level": 0,
        "hp": 1_000_000.0, "atk": 60_000.0, "def_": 3_000.0,
        "skill_levels": {"skill1": 10, "skill2": 10, "burst": 10},
    })


def best_deck(slugs, boss, must_include):
    specs, excluded = load_roster([_nikke(s) for s in slugs])
    if excluded:
        raise SystemExit(f"이 슬러그들이 인코딩돼 있지 않다: {excluded}")
    best = None
    for ordering in feasible_orderings(specs):
        if not deck_is_valid(ordering):
            continue
        seated = {u.slug for u in ordering}
        if any(s not in seated for s in must_include):
            continue
        result = evaluate_deck(ordering, boss)
        if best is None or result["total_damage"] > best["total_damage"]:
            best = result
    return best


def per_slug(result):
    totals = {}
    for entry in result["damage_log"]:
        totals[entry["slug"]] = totals.get(entry["slug"], 0.0) + entry["damage"]
    return totals


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--flora", default="flora",
                        choices=["flora", "flora-signature"],
                        help="which Flora build to seat (default: flora)")
    parser.add_argument("--fight-duration", type=float, default=180.0)
    args = parser.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    boss = BossProfile(element="Water", fight_duration=args.fight_duration,
                       enemy_def=8000.0)
    original = registry._RESOURCE_CONTRIBUTION_BUILDERS[args.flora]

    print(f"플로라 빌드: {args.flora} · 보스 Water · {args.fight_duration:.0f}초\n")
    for holder, deckmates in HOLDER_DECKMATES.items():
        deck = [holder, *deckmates, args.flora]
        with_bump = best_deck(deck, boss, must_include=(holder, args.flora))
        if with_bump is None:
            print(f"{holder:22s} 합법 덱이 없다: {deck}")
            continue

        registry._RESOURCE_CONTRIBUTION_BUILDERS[args.flora] = lambda sv: None
        try:
            without = best_deck(deck, boss, must_include=(holder, args.flora))
        finally:
            registry._RESOURCE_CONTRIBUTION_BUILDERS[args.flora] = original

        a, b = per_slug(without), per_slug(with_bump)
        holder_delta = b.get(holder, 0.0) / a.get(holder, 1.0) - 1
        deck_delta = with_bump["total_damage"] / without["total_damage"] - 1
        print(f"{holder:22s} 보유자 {a.get(holder, 0):14,.0f} -> {b.get(holder, 0):14,.0f} "
              f"({holder_delta:+.3%})   덱 {deck_delta:+.3%}")
        for slug in sorted(set(a) | set(b)):
            if slug != holder and abs(b.get(slug, 0) - a.get(slug, 0)) > 1:
                print(f"{'':22s}   그 밖에 움직인 것: {slug} "
                      f"{b[slug] / a[slug] - 1:+.3%}")


if __name__ == "__main__":
    main()
