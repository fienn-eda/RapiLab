"""Validate the sample-regression surrogate's ranking recall (cascade Phase 1).

Fits the surrogate on a random sample of truly-simulated feasible decks, then on
a held-out set measures whether the true-best combinations land in the surrogate's
top-K (and the Spearman rank correlation). This is the go/no-go signal for the
cheap-filter -> sim-top-K cascade (docs/superpowers/specs/2026-07-23-cascade-
surrogate-deck-search-design.md). No engine change; pure measurement.

Keep SimPool construction under __main__ (Windows spawn re-imports this module).

Usage (any cwd):
    python3 scripts/validate_surrogate_recall.py [--units 40] [--fit 1500]
                                                 [--holdout 400] [--lam 1.0]
                                                 [--seed 7]
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

import numpy as np  # noqa: E402

from app.models import UserNikkeState  # noqa: E402
from app.user_roster import load_roster  # noqa: E402
from app.supported_units import supported_units  # noqa: E402
from app.deck_search import BossProfile  # noqa: E402
from app.sim_pool import SimPool  # noqa: E402
from app.surrogate import (make_feature_space, build_matrix, fit_ridge, predict,
                           sample_feasible_combinations, best_ordering_damage)  # noqa: E402


def _nikke(slug):
    return UserNikkeState.model_validate({
        "character_slug": slug, "level": 200, "core_level": 0,
        "hp": 1_000_000.0, "atk": 60_000.0, "def_": 3_000.0,
        "skill_levels": {"skill1": 10, "skill2": 10, "burst": 10},
    })


def _spearman(a, b):
    ra = np.argsort(np.argsort(a))
    rb = np.argsort(np.argsort(b))
    return float(np.corrcoef(ra, rb)[0, 1])


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--units", type=int, default=40)
    p.add_argument("--fit", type=int, default=1500)
    p.add_argument("--holdout", type=int, default=400)
    p.add_argument("--lam", type=float, default=1.0)
    p.add_argument("--seed", type=int, default=7)
    args = p.parse_args()

    slugs = [u["slug"] for u in supported_units()][:args.units]
    specs, _ = load_roster([_nikke(s) for s in slugs])
    boss = BossProfile(element="Water", fight_duration=180.0)
    print(f"roster {len(specs)} units; sampling {args.fit} fit + {args.holdout} holdout",
          flush=True)

    # Disjoint fit/holdout samples: draw fit+holdout, split.
    combos = sample_feasible_combinations(specs, args.fit + args.holdout, seed=args.seed)
    fit_combos = combos[:args.fit]
    hold_combos = combos[args.fit:]
    print(f"got {len(fit_combos)} fit + {len(hold_combos)} holdout combos", flush=True)

    if len(fit_combos) < 1 or len(hold_combos) < 5:
        print(f"\nERROR: feasible space too small for a trustworthy signal "
              f"(got {len(fit_combos)} fit + {len(hold_combos)} holdout; need "
              f">= 1 fit and >= 5 holdout). Increase --units, or lower "
              f"--fit/--holdout to fit the feasible space.", flush=True)
        sys.exit(1)

    with SimPool(specs, boss, workers="auto") as pool:
        scorer = pool.score_many
        y_fit = best_ordering_damage(fit_combos, boss, scorer)
        y_hold = np.array(best_ordering_damage(hold_combos, boss, scorer))

    fs = make_feature_space(specs)
    if len(fit_combos) < fs.n_features:
        print(f"NOTE: fit sample ({len(fit_combos)}) is smaller than the feature "
              f"space ({fs.n_features}); ridge fit is underdetermined.", flush=True)
    beta = fit_ridge(build_matrix(fit_combos, fs), np.array(y_fit), lam=args.lam)
    pred_hold = predict(build_matrix(hold_combos, fs), beta)

    order = np.argsort(-pred_hold)          # surrogate ranking (best first)
    surrogate_rank_of_true_best = int(np.where(order == int(np.argmax(y_hold)))[0][0])

    print(f"\nSpearman(surrogate, true) = {_spearman(pred_hold, y_hold):.3f}", flush=True)
    print(f"true-best surrogate rank = {surrogate_rank_of_true_best} "
          f"(of {len(hold_combos)})", flush=True)
    print(f"\n{'K':>5} {'true-top1 in top-K':>18} {'true-top5 in top-K':>18}", flush=True)
    top1 = int(np.argmax(y_hold))
    top5 = set(np.argsort(-y_hold)[:5].tolist())
    for k in (10, 20, 50, 100):
        topk = set(order[:k].tolist())
        print(f"{k:>5} {str(top1 in topk):>18} "
              f"{str(len(top5 & topk)) + '/5':>18}", flush=True)


if __name__ == "__main__":
    main()
