import numpy as np
from types import SimpleNamespace
from app.surrogate import (ALLOWED_PAIR_TYPES, make_feature_space, featurize,
                           build_matrix)


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
