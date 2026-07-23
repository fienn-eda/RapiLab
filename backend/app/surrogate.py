"""Reference-free sample-regression surrogate for deck damage (cascade Phase 1).

Predicts a 5-unit combination's best-ordering total damage from a cheap linear
model over membership + restricted tier-pair indicators, fit by ridge regression
to a random sample of truly-simulated decks. Lets a cascade rank all combinations
for free and simulate only the top-K (docs/superpowers/specs/2026-07-23-cascade-
surrogate-deck-search-design.md). Feasibility rules are reused from deck_search.
"""
from dataclasses import dataclass
from itertools import combinations
import random

import numpy as np

from app.deck_search import (ALLOWED_SHAPES, _no_variant_clash,
                             _tier1_seating_valid, _intra_tier_orderings)

# Buffer-attacker (1-3, 2-3), buffer-buffer (1-2), attacker-attacker (3-3).
# (1-1)/(2-2) omitted: real decks rarely pair those and it curbs feature count.
ALLOWED_PAIR_TYPES = frozenset({(1, 2), (1, 3), (2, 3), (3, 3)})


@dataclass
class FeatureSpace:
    unit_col: dict          # slug -> column index (>=1; col 0 is the intercept)
    pair_col: dict          # (slug_a, slug_b) sorted -> column index
    n_features: int


def make_feature_space(roster) -> FeatureSpace:
    slugs = sorted(u.slug for u in roster)
    tier = {u.slug: u.burst_tier for u in roster}
    unit_col = {slug: i + 1 for i, slug in enumerate(slugs)}  # col 0 = intercept
    pair_col = {}
    next_col = 1 + len(slugs)
    for a, b in combinations(slugs, 2):
        pair_type = tuple(sorted((tier[a], tier[b])))
        if pair_type in ALLOWED_PAIR_TYPES:
            pair_col[(a, b)] = next_col
            next_col += 1
    return FeatureSpace(unit_col=unit_col, pair_col=pair_col, n_features=next_col)


def featurize(combo, fs: FeatureSpace) -> np.ndarray:
    v = np.zeros(fs.n_features)
    v[0] = 1.0
    slugs = [u.slug for u in combo]
    for slug in slugs:
        v[fs.unit_col[slug]] = 1.0
    for a, b in combinations(sorted(slugs), 2):
        col = fs.pair_col.get((a, b))
        if col is not None:
            v[col] = 1.0
    return v


def build_matrix(combos, fs: FeatureSpace) -> np.ndarray:
    return np.vstack([featurize(c, fs) for c in combos])


def sample_feasible_combinations(roster, n_samples, seed):
    """Up to `n_samples` distinct feasible 5-unit combinations (canonical tier
    order), drawn uniformly over (shape, per-tier unit choice) and kept only if
    they pass the deck_search feasibility rules. Deterministic per seed; returns
    fewer only when the feasible space is exhausted by repeated rejection."""
    rng = random.Random(seed)
    by_tier = {1: [], 2: [], 3: []}
    for u in roster:
        if u.burst_tier in by_tier:
            by_tier[u.burst_tier].append(u)
    seen, out = set(), []
    # cap attempts so a tiny/infeasible roster can't loop forever
    attempts, max_attempts = 0, n_samples * 200 + 1000
    while len(out) < n_samples and attempts < max_attempts:
        attempts += 1
        n1, n2, n3 = rng.choice(ALLOWED_SHAPES)
        if len(by_tier[1]) < n1 or len(by_tier[2]) < n2 or len(by_tier[3]) < n3:
            continue
        picks = (rng.sample(by_tier[1], n1) + rng.sample(by_tier[2], n2)
                 + rng.sample(by_tier[3], n3))
        combo = sorted(picks, key=lambda u: u.burst_tier)
        key = tuple(u.slug for u in combo)
        if key in seen:
            continue
        if _no_variant_clash(combo) and _tier1_seating_valid(combo):
            seen.add(key)
            out.append(combo)
    return out


def fit_ridge(X, y, lam=1.0):
    """Ridge coefficients; the intercept column (0) is left unpenalized."""
    X = np.asarray(X, dtype=float)
    y = np.asarray(y, dtype=float)
    n_features = X.shape[1]
    penalty = np.eye(n_features)
    penalty[0, 0] = 0.0
    return np.linalg.solve(X.T @ X + lam * penalty, X.T @ y)


def predict(X, beta):
    return np.asarray(X, dtype=float) @ np.asarray(beta, dtype=float)


def best_ordering_damage(combos, boss, score_orderings):
    """Each combo's max total damage over its intra-tier orderings. `boss` is
    unused here (the injected scorer carries it) but kept for call-site clarity.
    All orderings are scored in ONE batch, then grouped back per combo."""
    flat, spans = [], []
    for combo in combos:
        orderings = list(_intra_tier_orderings(combo))
        spans.append((len(flat), len(flat) + len(orderings)))
        flat.extend(orderings)
    totals = score_orderings(flat)
    return [max(totals[a:b]) for a, b in spans]
