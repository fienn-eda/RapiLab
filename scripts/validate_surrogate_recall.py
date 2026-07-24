"""Validate a cheap deck-ranking surrogate's recall (cascade Phase 1).

On a held-out set of truly-simulated feasible decks, measures whether the
true-best combinations land in the surrogate's top-K (and the Spearman rank
correlation). This is the go/no-go signal for the cheap-filter -> sim-top-K
cascade (docs/superpowers/specs/2026-07-23-cascade-surrogate-deck-search-
design.md). No engine change; pure measurement.

Two surrogates, selected with --surrogate:

  regression   surrogate.py's sample regression - fit on a random sample of
               SIMULATED decks. Accurate in principle, but the fit costs
               thousands of sims per roster+boss, and grows with the roster.
  closed-form  closed_form.py's fit-free estimate - no simulation at all, so
               its cost is independent of roster size.
  both         both, on the SAME holdout (pays the regression's fit cost).

The holdout depends only on --units/--fit/--holdout/--seed, so runs of
different surrogates with matching arguments are directly comparable.

Keep SimPool construction under __main__ (Windows spawn re-imports this module).

Usage (any cwd):
    python3 scripts/validate_surrogate_recall.py [--units 40] [--fit 1500]
                                                 [--holdout 400] [--lam 1.0]
                                                 [--seed 7]
                                                 [--surrogate both]
"""
import argparse
import os
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

# Force single-threaded BLAS BEFORE importing numpy. On this Windows/anaconda
# build, multi-threaded OpenBLAS deadlocks np.linalg.solve on the ~790x790
# ridge system (fit_ridge spins every core forever after the sims finish).
# Single-threaded solve is instant (0.03s) and the fit is tiny, so there is no
# throughput loss. numpy reads these vars at import time, so they must be set
# first.
os.environ.setdefault("OPENBLAS_NUM_THREADS", "1")
os.environ.setdefault("OMP_NUM_THREADS", "1")
os.environ.setdefault("MKL_NUM_THREADS", "1")

import numpy as np  # noqa: E402

from app.models import UserNikkeState  # noqa: E402
from app.user_roster import load_roster  # noqa: E402
from app.supported_units import supported_units  # noqa: E402
from app.deck_search import BossProfile, evaluate_deck  # noqa: E402
from app.sim_pool import SimPool, resolve_workers  # noqa: E402
from app.closed_form import score_with_diagnostics  # noqa: E402
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


def _report(name, pred_hold, y_hold):
    """Print one surrogate's recall table against the shared ground truth."""
    order = np.argsort(-pred_hold)          # surrogate ranking (best first)
    top1 = int(np.argmax(y_hold))
    top5 = set(np.argsort(-y_hold)[:5].tolist())
    rank_of_true_best = int(np.where(order == top1)[0][0])

    print(f"\n=== {name} ===", flush=True)
    print(f"Spearman(surrogate, true) = {_spearman(pred_hold, y_hold):.3f}", flush=True)
    print(f"true-best surrogate rank = {rank_of_true_best} (of {len(y_hold)})", flush=True)
    print(f"\n{'K':>5} {'true-top1 in top-K':>18} {'true-top5 in top-K':>18}", flush=True)
    all_ks = (10, 20, 50, 100)
    meaningful_ks = [k for k in all_ks if k < len(y_hold)]
    for k in meaningful_ks:
        topk = set(order[:k].tolist())
        print(f"{k:>5} {str(top1 in topk):>18} "
              f"{str(len(top5 & topk)) + '/5':>18}", flush=True)
    skipped_ks = [k for k in all_ks if k not in meaningful_ks]
    if skipped_ks:
        print(f"note: skipped K >= holdout ({len(y_hold)}) -- not meaningful: "
              f"{', '.join(str(k) for k in skipped_ks)}", flush=True)


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--units", type=int, default=40)
    p.add_argument("--fit", type=int, default=1500)
    p.add_argument("--holdout", type=int, default=400)
    p.add_argument("--lam", type=float, default=1.0)
    p.add_argument("--seed", type=int, default=7)
    p.add_argument("--surrogate", choices=("regression", "closed-form", "both"),
                   default="both",
                   help="which cheap ranker to measure; 'closed-form' needs no "
                        "fit, so it skips simulating the fit sample entirely")
    p.add_argument("--workers", default="1",
                   help='"auto" (all-but-one core) or an int; default "1" = serial. '
                        "The SimPool parallel path oversubscribes BLAS threads on "
                        "this workload -- keep serial until that is fixed.")
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
              f">= 1 fit and >= 5 holdout, which is the minimum for DEFINED "
              f"metrics -- for a MEANINGFUL signal use a holdout well above the "
              f"largest K printed below). Increase --units, or lower "
              f"--fit/--holdout to fit the feasible space.", flush=True)
        sys.exit(1)

    needs_regression = args.surrogate in ("regression", "both")

    workers = args.workers if args.workers == "auto" else int(args.workers)
    pool = SimPool(specs, boss, workers=workers) if resolve_workers(workers) > 1 else None
    try:
        scorer = (pool.score_many if pool is not None
                  else lambda decks: [evaluate_deck(d, boss)["total_damage"] for d in decks])
        # The fit sample is drawn either way (it decides where the holdout
        # starts, so holdouts stay comparable across --surrogate choices), but
        # only the regression has to pay for simulating it.
        y_fit = best_ordering_damage(fit_combos, boss, scorer) if needs_regression else None
        y_hold = np.array(best_ordering_damage(hold_combos, boss, scorer))
    finally:
        if pool is not None:
            pool.close()

    if needs_regression:
        fs = make_feature_space(specs)
        if len(fit_combos) < fs.n_features:
            print(f"NOTE: fit sample ({len(fit_combos)}) is smaller than the feature "
                  f"space ({fs.n_features}); ridge fit is underdetermined.", flush=True)
        beta = fit_ridge(build_matrix(fit_combos, fs), np.array(y_fit), lam=args.lam)
        _report(f"sample regression (fit on {len(fit_combos)} simulated decks)",
                predict(build_matrix(hold_combos, fs), beta), y_hold)

    if args.surrogate in ("closed-form", "both"):
        started = time.perf_counter()
        scored = [score_with_diagnostics(list(combo), boss) for combo in hold_combos]
        elapsed = time.perf_counter() - started
        skipped = sum(len(failures) for _, failures in scored)
        print(f"\nclosed-form scored {len(hold_combos)} combos in {elapsed:.2f}s "
              f"({elapsed / len(hold_combos) * 1000:.2f} ms/combo); "
              f"{skipped} skill bullets skipped", flush=True)
        _report("closed-form (no fit, no simulation)",
                np.array([score for score, _ in scored]), y_hold)


if __name__ == "__main__":
    main()
