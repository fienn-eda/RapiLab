from types import SimpleNamespace

import numpy as np
import pytest

from app.cascade import SurrogateModel, fit_surrogate
from app.deck_search import BossProfile


def _u(slug, tier):
    return SimpleNamespace(slug=slug, burst_tier=tier)


def _roster(n1=4, n2=6, n3=12):
    return ([_u(f"a{i}", 1) for i in range(n1)]
            + [_u(f"b{i}", 2) for i in range(n2)]
            + [_u(f"c{i}", 3) for i in range(n3)])


BOSS = BossProfile(element="Water")


def _scorer_favouring(favoured, base=100.0, bonus=50.0):
    """Batch scorer: a deck scores `base` plus `bonus` per favoured member.
    Records every batch it was handed so tests can assert on the fit's cost."""
    calls = {"batches": 0, "decks": 0}

    def score(decks):
        calls["batches"] += 1
        calls["decks"] += len(decks)
        return [base + bonus * sum(1 for u in deck if u.slug in favoured)
                for deck in decks]

    return score, calls


def test_fit_surrogate_learns_which_units_are_valuable():
    roster = _roster()
    score, calls = _scorer_favouring({"c0", "b0"})

    model = fit_surrogate(roster, BOSS, score, samples=120)

    assert isinstance(model, SurrogateModel)
    # the favoured units must outrank their same-tier peers
    assert model.coefficient("c0") > model.coefficient("c5")
    assert model.coefficient("b0") > model.coefficient("b5")
    assert calls["decks"] > 0


def test_fit_surrogate_uses_unit_columns_only():
    model = fit_surrogate(_roster(), BOSS, _scorer_favouring({"c0"})[0], samples=120)
    assert model.feature_space.pair_col == {}
    assert model.feature_space.n_features == 1 + 22


def test_fit_surrogate_is_deterministic_for_a_seed():
    roster = _roster()
    first = fit_surrogate(roster, BOSS, _scorer_favouring({"c0"})[0], samples=120)
    second = fit_surrogate(roster, BOSS, _scorer_favouring({"c0"})[0], samples=120)
    assert np.allclose(first.beta, second.beta)


def test_fit_surrogate_returns_none_when_the_sample_is_too_thin():
    # one unit per tier -> a single feasible combination, nowhere near `samples`
    tiny = [_u("a0", 1), _u("b0", 2), _u("c0", 3), _u("c1", 3), _u("c2", 3)]
    assert fit_surrogate(tiny, BOSS, _scorer_favouring(set())[0], samples=120) is None


def test_coefficient_of_an_unknown_unit_is_zero():
    model = fit_surrogate(_roster(), BOSS, _scorer_favouring({"c0"})[0], samples=120)
    assert model.coefficient("not-in-roster") == 0.0


def test_covers_reports_whether_every_unit_has_a_column():
    roster = _roster()
    model = fit_surrogate(roster, BOSS, _scorer_favouring({"c0"})[0], samples=120)
    assert model.covers(roster[:5]) is True
    assert model.covers(roster[:4] + [_u("stranger", 3)]) is False


def test_score_combos_ranks_a_favoured_combo_above_a_plain_one():
    roster = _roster()
    model = fit_surrogate(roster, BOSS, _scorer_favouring({"c0"})[0], samples=120)
    favoured = [roster[0], roster[4], roster[10], roster[11], roster[12]]  # holds c0
    plain = [roster[1], roster[5], roster[13], roster[14], roster[15]]
    scores = model.score_combos([favoured, plain])
    assert scores.shape == (2,)
    assert scores[0] > scores[1]
