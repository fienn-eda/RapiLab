"""Does a surrogate cascade actually save simulations? Counts both budgets.

The sample-regression surrogate ranks decks well (see
validate_surrogate_recall.py), but it is only worth wiring into the search if
the simulations it SAVES outnumber the ones its fit COSTS. That is not obvious:
the fit needs at least as many sampled decks as the feature space has columns,
and the feature space grows with the roster - so the fit gets more expensive on
exactly the big rosters the cascade is meant to rescue.

This counts both sides for one roster size:

  current   simulations a real zero-base `allocate_decks` issues today, counted
            by intercepting evaluate_deck (forced serial, so every call lands in
            this process). This is the number a cascade would replace.
  cascade   simulations the fit would need (feature columns -> sampled decks ->
            their intra-tier orderings), plus the top-K it still has to judge
            for real.

Run it at a few --units values: the ratio is what decides whether the cascade is
worth building, and it moves with roster size.

Usage (any cwd):
    python3 scripts/measure_cascade_budget.py [--units 40] [--top-k 20]
                                              [--sample-decks N] [--skip-current]
"""
import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

import app.deck_search as ds  # noqa: E402
from app.deck_search import BossProfile, _intra_tier_orderings  # noqa: E402
from app.models import UserNikkeState  # noqa: E402
from app.supported_units import supported_units  # noqa: E402
from app.surrogate import make_feature_space, sample_feasible_combinations  # noqa: E402
from app.user_roster import load_roster  # noqa: E402

# How many sampled decks per feature column. A ridge fit is determined once the
# sample exceeds the column count; 1.5x is the margin validate_surrogate_recall
# was run at (1200 decks against 790 columns).
FIT_SAMPLES_PER_FEATURE = 1.5


def _nikke(slug):
    return UserNikkeState.model_validate({
        "character_slug": slug, "level": 200, "core_level": 0,
        "hp": 1_000_000.0, "atk": 60_000.0, "def_": 3_000.0,
        "skill_levels": {"skill1": 10, "skill2": 10, "burst": 10},
    })


def _count_current_simulations(specs, boss):
    """Simulations one zero-base allocate_decks issues, forced serial so the
    counter sees every call (pool workers are separate processes)."""
    import app.deck_allocation as da

    real = ds.evaluate_deck
    counter = {"n": 0}

    def counting(deck, profile):
        counter["n"] += 1
        return real(deck, profile)

    ds.evaluate_deck = counting
    try:
        started = time.perf_counter()
        da.allocate_decks(specs, boss, workers=1)
        elapsed = time.perf_counter() - started
    finally:
        ds.evaluate_deck = real
    return counter["n"], elapsed


def _orderings_per_deck(specs, sample, seed):
    """Average intra-tier orderings per combination - the fit pays for all of
    them, since its target is a combination's best ordering."""
    combos = sample_feasible_combinations(specs, sample, seed=seed)
    if not combos:
        return 0.0, 0
    total = sum(sum(1 for _ in _intra_tier_orderings(combo)) for combo in combos)
    return total / len(combos), len(combos)


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--units", type=int, default=40)
    p.add_argument("--top-k", type=int, default=20,
                   help="decks the cascade still simulates for real (default 20, "
                        "the K that recovered 100%% of best damage at 40 units)")
    p.add_argument("--sample-decks", type=int, default=200,
                   help="decks sampled just to average orderings-per-deck")
    p.add_argument("--seed", type=int, default=7)
    p.add_argument("--fit-decks", type=int, default=0,
                   help="budget an explicitly chosen fit size instead of the "
                        "column-derived one - use the size recall was actually "
                        "validated at, so the budget matches a measured accuracy")
    p.add_argument("--no-pairs", action="store_true",
                   help="budget a unit-only feature space (columns grow linearly "
                        "with the roster instead of quadratically)")
    p.add_argument("--skip-current", action="store_true",
                   help="skip the (slow) real allocate_decks count")
    args = p.parse_args()

    slugs = [u["slug"] for u in supported_units()][:args.units]
    specs, _ = load_roster([_nikke(s) for s in slugs])
    boss = BossProfile(element="Water", fight_duration=180.0)
    print(f"roster {len(specs)} units", flush=True)

    features = make_feature_space(specs, include_pairs=not args.no_pairs).n_features
    per_deck, sampled = _orderings_per_deck(specs, args.sample_decks, args.seed)
    fit_decks = args.fit_decks or int(features * FIT_SAMPLES_PER_FEATURE)
    fit_sims = int(fit_decks * per_deck)
    # The cascade still simulates its shortlist, once per allocated deck slot.
    topk_sims = int(args.top_k * per_deck * 5)
    cascade = fit_sims + topk_sims

    print(f"\ncascade budget:", flush=True)
    print(f"  feature columns          {features}", flush=True)
    print(f"  fit decks (x{FIT_SAMPLES_PER_FEATURE})        {fit_decks}", flush=True)
    print(f"  orderings per deck       {per_deck:.2f}  (over {sampled} sampled decks)",
          flush=True)
    print(f"  fit simulations          {fit_sims}", flush=True)
    print(f"  top-{args.top_k} x 5 deck slots      {topk_sims}", flush=True)
    print(f"  TOTAL                    {cascade}", flush=True)

    if args.skip_current:
        return
    print(f"\ncounting today's allocate_decks (serial, this may take minutes)...",
          flush=True)
    current, elapsed = _count_current_simulations(specs, boss)
    print(f"\ncurrent budget:", flush=True)
    print(f"  simulations              {current}", flush=True)
    print(f"  serial wall time         {elapsed:.0f}s", flush=True)
    if cascade > 0:
        print(f"\nspeedup if the cascade replaced it: {current / cascade:.2f}x", flush=True)


if __name__ == "__main__":
    main()
