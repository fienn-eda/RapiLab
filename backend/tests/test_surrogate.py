import numpy as np
import pytest
from types import SimpleNamespace
from app.surrogate import (make_feature_space, featurize, build_matrix,
                           sample_feasible_combinations, fit_ridge, predict,
                           best_ordering_damage)
from app.deck_search import ALLOWED_SHAPES


def _u(slug, tier):
    return SimpleNamespace(slug=slug, burst_tier=tier)


ROSTER = [_u("b1a", 1), _u("b1b", 1), _u("b2a", 2), _u("b3a", 3), _u("b3b", 3)]


def test_feature_space_has_intercept_units_and_allowed_pairs():
    fs = make_feature_space(ROSTER)
    # intercept col 0 + 5 unit cols + allowed pairs
    assert fs.unit_col.keys() == {"b1a", "b1b", "b2a", "b3a", "b3b"}
    assert 0 not in fs.unit_col.values()  # col 0 reserved for intercept
    # (1,1) is NOT an allowed pair type -> b1a,b1b excluded; (3,3) IS -> b3a,b3b included
    assert ("b1a", "b1b") not in fs.pair_col
    assert ("b3a", "b3b") in fs.pair_col
    assert ("b1a", "b3a") in fs.pair_col  # (1,3) allowed
    assert fs.n_features == 1 + 5 + len(fs.pair_col)


def test_feature_space_without_pairs_keeps_only_intercept_and_units():
    fs = make_feature_space(ROSTER, include_pairs=False)
    assert fs.pair_col == {}
    assert fs.n_features == 1 + len(ROSTER)
    # featurize must agree with the narrowed space, not index past it
    v = featurize([ROSTER[0], ROSTER[2], ROSTER[3]], fs)
    assert v.shape == (fs.n_features,)
    assert v[0] == 1.0 and v[fs.unit_col["b1a"]] == 1.0 and v[fs.unit_col["b3b"]] == 0.0


def test_featurize_marks_intercept_membership_and_pairs():
    fs = make_feature_space(ROSTER)
    combo = [ROSTER[0], ROSTER[2], ROSTER[3]]  # b1a, b2a, b3a
    v = featurize(combo, fs)
    assert v[0] == 1.0
    assert v[fs.unit_col["b1a"]] == 1.0 and v[fs.unit_col["b3a"]] == 1.0
    assert v[fs.unit_col["b1b"]] == 0.0
    assert v[fs.pair_col[("b1a", "b3a")]] == 1.0  # present pair
    assert v[fs.pair_col[("b3a", "b3b")]] == 0.0  # b3b not in combo


def test_build_matrix_shape():
    fs = make_feature_space(ROSTER)
    X = build_matrix([[ROSTER[0], ROSTER[2], ROSTER[3]], ROSTER[:3]], fs)
    assert X.shape == (2, fs.n_features)


# A roster big enough to form many feasible decks across shapes.
BIG = ([_u(f"a{i}", 1) for i in range(3)] +
       [_u(f"b{i}", 2) for i in range(3)] +
       [_u(f"c{i}", 3) for i in range(6)])


def test_sampled_combos_are_feasible_and_deterministic():
    s1 = sample_feasible_combinations(BIG, n_samples=20, seed=7)
    s2 = sample_feasible_combinations(BIG, n_samples=20, seed=7)
    assert [[u.slug for u in c] for c in s1] == [[u.slug for u in c] for c in s2]
    shapes = set(ALLOWED_SHAPES)
    for combo in s1:
        assert len(combo) == 5
        tiers = tuple(sorted(u.burst_tier for u in combo))
        # canonical-order combo: tiers non-decreasing
        assert [u.burst_tier for u in combo] == sorted(u.burst_tier for u in combo)
        counts = (tiers.count(1), tiers.count(2), tiers.count(3))
        assert counts in shapes
        assert len({u.slug for u in combo}) == 5  # distinct units


def test_sample_count_capped_by_request():
    s = sample_feasible_combinations(BIG, n_samples=5, seed=1)
    assert len(s) == 5


def test_ridge_recovers_linear_signal_with_small_lambda():
    rng = np.random.default_rng(0)
    X = np.column_stack([np.ones(200), rng.normal(size=(200, 3))])
    true_beta = np.array([2.0, 1.5, -3.0, 0.5])
    y = X @ true_beta
    beta = fit_ridge(X, y, lam=1e-6)
    assert np.allclose(beta, true_beta, atol=1e-3)
    assert np.allclose(predict(X, beta), y, atol=1e-3)


def test_ridge_does_not_penalize_intercept():
    # Constant target -> intercept should equal the constant, others ~0.
    X = np.column_stack([np.ones(50), np.random.default_rng(1).normal(size=(50, 2))])
    y = np.full(50, 7.0)
    beta = fit_ridge(X, y, lam=10.0)
    assert abs(beta[0] - 7.0) < 1e-6
    assert np.allclose(beta[1:], 0.0, atol=1e-6)


def test_ridge_rejects_nonpositive_lambda():
    X = np.column_stack([np.ones(10), np.random.default_rng(2).normal(size=(10, 2))])
    y = np.random.default_rng(3).normal(size=10)
    with pytest.raises(ValueError):
        fit_ridge(X, y, lam=0)


def test_best_ordering_damage_takes_max_per_combo():
    combos = [BIG[:5], BIG[3:8]]
    calls = {"count": 0, "n": 0}

    def fake_scorer(ordered_decks):
        calls["count"] += 1
        calls["n"] = len(ordered_decks)
        return [float(i) for i in range(len(ordered_decks))]

    out = best_ordering_damage(combos, boss=None, score_orderings=fake_scorer)
    # Exactly ONE flattened call over all orderings of both combos.
    assert calls["count"] == 1
    # Each combo has 12 valid intra-tier orderings (3!*2!); fake scores are
    # 0..23 in flatten order, so per-combo max = [11, 23].
    assert calls["n"] == 24
    assert out == [11.0, 23.0]
