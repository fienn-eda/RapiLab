"""Reference-free sample-regression surrogate for deck damage (cascade Phase 1).

Predicts a 5-unit combination's best-ordering total damage from a cheap linear
model over membership + restricted tier-pair indicators, fit by ridge regression
to a random sample of truly-simulated decks. Lets a cascade rank all combinations
for free and simulate only the top-K (docs/superpowers/specs/2026-07-23-cascade-
surrogate-deck-search-design.md). Feasibility rules are reused from deck_search.
"""
from dataclasses import dataclass
from itertools import combinations

import numpy as np

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
