"""How good the greedy peel's decks are BEFORE the swap phase touches them.

`measure_swap_phase.py` shows the swap hill-climb lifting summed damage by
tens of percent, most of it from swapping bench units in. That has two possible
causes with opposite fixes:

  greedy      peeling's classic mistake - it stacks the best units into deck 1
              and starves later decks. Swap exists to fix exactly this, so a
              large gain here is the design working, and the fix is to give the
              swap phase enough throughput to finish
  cascade     the cascade only ever seats WIDE_TIER_CAPS units (22 of a 79-unit
              roster) as search candidates, so a unit outside that pool cannot
              enter a deck until swap pulls it off the bench. Then the gain is
              the cascade's narrowing being paid back late, and the fix belongs
              in the pool, not in swap

This runs the peel both ways with the swap phase disabled (swap_budget=0),
so the comparison isolates the decks peeling itself produces. Cascade-off is
the pre-cascade shipped path (pruned exhaustive), reached by making the fit
return None.

Usage (any cwd):
    python3 scripts/measure_peel_quality.py [--units 41] [--decks 5]
"""
import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

import app.deck_allocation as da  # noqa: E402
import app.deck_search as ds  # noqa: E402
from app.cascade import clear_fit_cache  # noqa: E402
from app.deck_search import BossProfile  # noqa: E402
from app.models import UserNikkeState  # noqa: E402
from app.supported_units import supported_units  # noqa: E402
from app.user_roster import load_roster  # noqa: E402


def _nikke(slug):
    return UserNikkeState.model_validate({
        "character_slug": slug, "level": 200, "core_level": 0,
        "hp": 1_000_000.0, "atk": 60_000.0, "def_": 3_000.0,
        "skill_levels": {"skill1": 10, "skill2": 10, "burst": 10},
    })


def _run(specs, boss, decks, cascade_on, real_fit):
    da.cached_fit_surrogate = real_fit if cascade_on else (lambda *a, **k: None)
    clear_fit_cache()
    sims = [0]
    real_evaluate = ds.evaluate_deck

    def counting_evaluate(deck, profile):
        sims[0] += 1
        return real_evaluate(deck, profile)

    ds.evaluate_deck = counting_evaluate
    da.evaluate_deck = counting_evaluate
    try:
        started = time.perf_counter()
        out = da.allocate_decks(specs, boss, num_decks=decks,
                                swap_budget=0, workers=1)
        elapsed = time.perf_counter() - started
    finally:
        ds.evaluate_deck = real_evaluate
        da.evaluate_deck = real_evaluate
    return out, sims[0], elapsed


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--units", type=int, default=41)
    p.add_argument("--decks", type=int, default=5)
    args = p.parse_args()

    slugs = [u["slug"] for u in supported_units()][:args.units]
    specs, _ = load_roster([_nikke(s) for s in slugs])
    boss = BossProfile(element="Water", fight_duration=180.0)
    print(f"roster {len(specs)} units; {args.decks} decks; swap disabled (serial)",
          flush=True)

    real_fit = da.cached_fit_surrogate
    results = {}
    for label, cascade_on in (("cascade", True), ("exhaustive", False)):
        out, sims, elapsed = _run(specs, boss, args.decks, cascade_on, real_fit)
        total = sum(d["total_damage"] for d in out["decks"])
        results[label] = total
        print(f"\n{label}: {total:.6g} total, {len(out['decks'])} decks, "
              f"{sims} sims, {elapsed:.0f}s", flush=True)
        for i, d in enumerate(out["decks"]):
            print(f"  deck {i}: {d['total_damage']:>12.6g}  {d['deck']}", flush=True)

    ratio = results["cascade"] / results["exhaustive"]
    print(f"\ncascade peel keeps {ratio:.2%} of the exhaustive peel's damage",
          flush=True)


if __name__ == "__main__":
    main()
