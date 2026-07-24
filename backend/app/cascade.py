"""Cheap-filter stage for deck search: rank candidate combinations with a
fitted surrogate and simulate only the top-K.

Measured on a 41-unit roster, 91.5% of an allocate_decks run's simulations go
into scoring every intra-tier ordering of the pruned candidate pool. This module
replaces that exhaustive pass with a ranking that costs a matrix multiply, so
simulation cost is pinned to K instead of to the pool's size.

The surrogate is unit-only (no pair terms) by design, not by simplification:
pair columns grow quadratically with the roster and a determined ridge fit needs
at least as many SIMULATED sample decks as it has columns, so pairs cost about
as many simulations as the search they would replace (measured 1.22x). Unit
columns grow linearly, so a 200-deck fit serves a 78-unit roster as easily as a
41-unit one - see docs/decisions.md.

Because the coefficients are per-unit and the model is additive, a fit made on
the FULL roster scores any subset of it. That is what lets one fit serve every
iteration of allocate_decks' greedy peel.

This module may import deck_search; deck_search must NOT import this one
(surrogate.py already imports deck_search, so the reverse edge would be a
cycle). search_best_decks receives a Cascade by injection instead - the same
shape as its duck-typed `pool` argument.
"""
from collections import OrderedDict
from dataclasses import astuple, dataclass
import hashlib
import json

import numpy as np

from app.surrogate import (best_ordering_damage, build_matrix, fit_ridge,
                           make_feature_space, predict,
                           sample_feasible_combinations)
from app.deck_search import prune_candidate_pool, shape_combinations

# Decks sampled and truly simulated to fit the model. 200 comfortably exceeds
# the 79 unit columns a full 78-unit roster produces, which is what a
# determined ridge fit needs.
FIT_SAMPLE_DECKS = 200
FIT_SEED = 20260724
FIT_LAMBDA = 1.0

# Combinations handed to the real simulator. The Phase 2 recall gate measured
# a 78-unit roster across 5 seeds, drawing combinations from the widened pool
# (the distribution this ranking actually faces): the truly best deck landed at
# rank 0-4 every time, so K=10 already recovered 100% of its damage on all five.
# 20 is deliberately double that floor - the extra ~220 simulations are ~0.4% of
# what the exhaustive search they replace spends, which buys headroom for
# rosters and bosses the five seeds did not cover.
DEFAULT_TOP_K = 20

# The cascade's candidate pool, wider than deck_search.PRUNED_TIER_CAPS. The
# tight caps there exist only because everything in that pool gets simulated;
# once simulation cost is pinned to K, a wider pool costs a matrix multiply.
WIDE_TIER_CAPS = {1: 4, 2: 6, 3: 12}


@dataclass
class SurrogateModel:
    """Fitted coefficients plus the column layout they were fit in."""

    feature_space: object
    beta: np.ndarray

    def coefficient(self, slug):
        """The unit's learned value; 0.0 for a unit the fit never saw."""
        col = self.feature_space.unit_col.get(slug)
        return 0.0 if col is None else float(self.beta[col])

    def covers(self, roster):
        return all(u.slug in self.feature_space.unit_col for u in roster)

    def score_combos(self, combos):
        return predict(build_matrix(combos, self.feature_space), self.beta)


def fit_surrogate(roster, boss, score_orderings, samples=FIT_SAMPLE_DECKS,
                  seed=FIT_SEED, lam=FIT_LAMBDA):
    """Fit the ranking model, or None when the roster is too small to support it.

    `score_orderings` is the same injected batch scorer best_ordering_damage
    takes: a callable from a list of ordered decks to their total damages.

    Returning None rather than a weak model is deliberate - the caller falls
    back to the exhaustive path, which is correct but slower. A model fit on a
    handful of decks would instead silently mis-rank.
    """
    combos = sample_feasible_combinations(roster, samples, seed=seed)
    feature_space = make_feature_space(roster, include_pairs=False)
    if len(combos) <= feature_space.n_features:
        return None
    y = best_ordering_damage(combos, boss, score_orderings)
    beta = fit_ridge(build_matrix(combos, feature_space), np.array(y), lam=lam)
    return SurrogateModel(feature_space=feature_space, beta=beta)


# Fits are keyed by content, so nothing ever needs explicit invalidation - a
# changed skill level or overload simply produces a different key. Bounded so a
# long-lived server process cannot grow without limit.
FIT_CACHE_SIZE = 8

_fit_cache = OrderedDict()


def roster_fingerprint(roster, boss):
    """A stable digest of everything that changes a deck's damage.

    Cube effects are assumed uniform per slug (roster._passive_effects), so the
    slug covers them. Sorted by slug and dumped with sorted keys, so the digest
    does not depend on roster order or dict insertion order.
    """
    units = [
        {
            "slug": unit.slug,
            "burst_tier": unit.burst_tier,
            "burst_cooldown": getattr(unit, "burst_cooldown", None),
            "element": getattr(unit, "element", None),
            "weapon": getattr(unit, "weapon", None),
            "base_stats": getattr(unit, "base_stats", None),
            "skill_values": getattr(unit, "skill_values", None),
            "weapon_stats": getattr(unit, "weapon_stats", None),
            "overload_options": getattr(unit, "overload_options", None),
        }
        for unit in sorted(roster, key=lambda u: u.slug)
    ]
    payload = json.dumps({"units": units, "boss": astuple(boss)},
                         sort_keys=True, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def cached_fit_surrogate(roster, boss, score_orderings):
    """fit_surrogate, reusing a previous fit for the same roster state and boss.

    Safe on two counts: the engine has no RNG, so an identical key with a fixed
    sample seed yields an identical fit; and the model only chooses WHICH decks
    to simulate, so even a wrong hit would cost ranking quality, never the
    correctness of a reported damage number.
    """
    key = roster_fingerprint(roster, boss)
    if key in _fit_cache:
        _fit_cache.move_to_end(key)
        return _fit_cache[key]
    model = fit_surrogate(roster, boss, score_orderings)
    _fit_cache[key] = model
    _fit_cache.move_to_end(key)
    while len(_fit_cache) > FIT_CACHE_SIZE:
        _fit_cache.popitem(last=False)
    return model


def clear_fit_cache():
    _fit_cache.clear()


def widened_pool(roster, boss, model, pool=None, caps=WIDE_TIER_CAPS):
    """The cascade's candidate pool: prune's picks, widened by coefficient.

    prune_candidate_pool goes in first because it is a genuinely different
    heuristic - marginal contribution measured in a reference deck, not a fitted
    coefficient - so the two filters' blind spots do not coincide. That is the
    safety net: a deck the surrogate undervalues can still reach the shortlist.

    Seats are filled PER TIER. A legal deck needs all three burst tiers, so a
    tier-blind sort by coefficient could starve one of them entirely.
    """
    chosen = {tier: [] for tier in caps}
    taken = set()

    def offer(unit):
        bucket = chosen.get(unit.burst_tier)
        if bucket is None or unit.slug in taken or len(bucket) >= caps[unit.burst_tier]:
            return
        bucket.append(unit)
        taken.add(unit.slug)

    for unit in prune_candidate_pool(roster, boss, pool):
        offer(unit)
    for unit in sorted(roster, key=lambda u: model.coefficient(u.slug), reverse=True):
        offer(unit)
    return [unit for tier in sorted(chosen) for unit in chosen[tier]]


@dataclass
class Cascade:
    """Ranks a roster's combinations and hands back only the top-K to simulate.

    Injected into search_best_decks rather than imported by it: surrogate.py
    already imports deck_search, so a deck_search -> cascade edge would be a
    cycle. This mirrors how `pool` is threaded in.
    """

    model: SurrogateModel
    top_k: int = DEFAULT_TOP_K
    caps: dict = None

    def shortlist(self, roster, boss, pool=None):
        """The combinations worth simulating, or None to defer to the caller's
        own (exhaustive) path."""
        if not self.model.covers(roster):
            return None
        units = widened_pool(roster, boss, self.model, pool,
                             self.caps or WIDE_TIER_CAPS)
        combos = list(shape_combinations(units))
        if not combos:
            return None
        ranking = np.argsort(-self.model.score_combos(combos))[:self.top_k]
        return [combos[i] for i in ranking]
