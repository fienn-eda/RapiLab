"""Did an engine change make the RECOMMENDATION worse, or only rescore it?

After an engine change the five-deck total moves, and the raw before/after
numbers cannot answer why: they are the optima of two DIFFERENT objective
functions, so a lower "after" is equally consistent with (a) the search
converging worse and (b) the old number having been an overestimate the change
removed. Comparing them directly is a category error.

This settles it by scoring ONE composition under BOTH engines:

    # on the old code
    python3 scripts/measure_engine_change_delta.py --dump before.json
    # on the new code
    python3 scripts/measure_engine_change_delta.py --score before.json
    python3 scripts/measure_engine_change_delta.py --dump after.json
    # back on the old code
    python3 scripts/measure_engine_change_delta.py --score after.json

Read it as: if the new engine scores the OLD composition BELOW what the new
search found, the search is fine and the old total was inflated. If it scores
it ABOVE, the search genuinely regressed and the budget or the move set is the
thing to look at.

`--dump` writes the seat order too, so the rescore seats them exactly as the
allocator did rather than re-deciding the order (seat order is worth several
percent - see docs/insights.md on argmax ordering).
"""
import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))
sys.path.insert(0, str(Path(__file__).resolve().parent))

from app.deck_allocation import SWAP_CANDIDATE_BUDGET, allocate_decks  # noqa: E402
from app.deck_search import BossProfile, evaluate_deck  # noqa: E402
from app.user_roster import load_roster  # noqa: E402
from roster_fixture import add_roster_argument, real_roster  # noqa: E402


def _boss(args):
    return BossProfile(element=args.element, core_hittable=not args.no_core,
                       enemy_def=args.enemy_def, fight_duration=args.duration)


def _specs(args):
    states = real_roster(args.roster)
    if states is None:
        raise SystemExit(f"no synced roster at {args.roster}")
    specs, dropped = load_roster(states)
    print(f"roster {len(specs)} usable ({len(dropped)} unloadable)")
    return specs


def _dump(args):
    specs = _specs(args)
    started = time.perf_counter()
    out = allocate_decks(specs, _boss(args), num_decks=args.decks,
                         swap_budget=args.budget, workers=args.workers)
    elapsed = time.perf_counter() - started
    decks = [list(d["deck"]) for d in out["decks"]]
    totals = [d["total_damage"] for d in out["decks"]]
    payload = {
        "decks": decks,
        "search_total": sum(totals),
        "per_deck": totals,
        "boss": {"element": args.element, "core_hittable": not args.no_core,
                 "enemy_def": args.enemy_def, "duration": args.duration},
        "swap_budget": args.budget,
    }
    Path(args.dump).write_text(json.dumps(payload, indent=1), encoding="utf-8")
    print(f"search total {sum(totals):,.0f} in {elapsed:.0f}s -> {args.dump}")
    for slugs, total in zip(decks, totals):
        print(f"  {total:>18,.0f}  {', '.join(slugs)}")


def _score(args):
    payload = json.loads(Path(args.score).read_text(encoding="utf-8"))
    specs = {s.slug: s for s in _specs(args)}
    saved = payload["boss"]
    boss = BossProfile(element=saved["element"], core_hittable=saved["core_hittable"],
                       enemy_def=saved["enemy_def"], fight_duration=saved["duration"])
    total = 0.0
    print(f"{'saved':>18} {'rescored':>18} {'delta':>9}  deck")
    for slugs, was in zip(payload["decks"], payload["per_deck"]):
        missing = [s for s in slugs if s not in specs]
        if missing:
            raise SystemExit(f"roster no longer has {', '.join(missing)}")
        now = evaluate_deck([specs[s] for s in slugs], boss)["total_damage"]
        total += now
        print(f"{was:>18,.0f} {now:>18,.0f} {now / was - 1:>+8.2%}  {', '.join(slugs)}")
    was_total = payload["search_total"]
    print(f"{was_total:>18,.0f} {total:>18,.0f} {total / was_total - 1:>+8.2%}  TOTAL")


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    add_roster_argument(p)
    mode = p.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dump", metavar="FILE",
                     help="run the allocator and save its compositions")
    mode.add_argument("--score", metavar="FILE",
                     help="rescore a saved composition with the current code")
    p.add_argument("--decks", type=int, default=5)
    p.add_argument("--budget", type=int, default=SWAP_CANDIDATE_BUDGET,
                   help="swap budget in candidate exchanges (default: the "
                        "production ceiling)")
    p.add_argument("--workers", default=None)
    p.add_argument("--element", default="Wind",
                   choices=["Fire", "Water", "Wind", "Iron", "Electric"])
    p.add_argument("--enemy-def", type=float, default=31784.0)
    p.add_argument("--duration", type=float, default=180.0)
    p.add_argument("--no-core", action="store_true")
    args = p.parse_args()
    if args.workers is not None and args.workers != "auto":
        args.workers = int(args.workers)
    (_dump if args.dump else _score)(args)


if __name__ == "__main__":
    main()
