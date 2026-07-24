from types import SimpleNamespace
from dataclasses import replace as _dc_replace

import numpy as np
import pytest

from app.cascade import (FIT_CACHE_SIZE, SurrogateModel, cached_fit_surrogate,
                         clear_fit_cache, fit_surrogate, roster_fingerprint)
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


def _investable(slug, tier):
    """A roster unit carrying the investment fields the fingerprint reads."""
    return SimpleNamespace(
        slug=slug, burst_tier=tier, burst_cooldown=20.0, element="Water",
        weapon="AR", base_stats={"atk": 60000.0, "def": 3000.0, "max_hp": 1e6},
        skill_values={"s": {"description_value_01": "10"}},
        weapon_stats={"weapon": "AR", "damage_percent": 100.0},
        overload_options=[])


def _investable_roster():
    return ([_investable(f"a{i}", 1) for i in range(4)]
            + [_investable(f"b{i}", 2) for i in range(6)]
            + [_investable(f"c{i}", 3) for i in range(12)])


def test_fingerprint_is_stable_across_roster_order():
    roster = _investable_roster()
    assert roster_fingerprint(roster, BOSS) == roster_fingerprint(roster[::-1], BOSS)


def test_fingerprint_changes_when_investment_changes():
    roster = _investable_roster()
    before = roster_fingerprint(roster, BOSS)
    roster[0].skill_values = {"s": {"description_value_01": "11"}}
    assert roster_fingerprint(roster, BOSS) != before


def test_fingerprint_changes_when_overload_changes():
    roster = _investable_roster()
    before = roster_fingerprint(roster, BOSS)
    roster[0].overload_options = [{"stat": "atk_percent", "value": 0.1}]
    assert roster_fingerprint(roster, BOSS) != before


def test_fingerprint_changes_with_the_boss():
    roster = _investable_roster()
    assert (roster_fingerprint(roster, BOSS)
            != roster_fingerprint(roster, BossProfile(element="Fire")))


def test_cached_fit_reuses_the_model_for_the_same_roster_and_boss():
    clear_fit_cache()
    roster = _investable_roster()
    score, calls = _scorer_favouring({"c0"})

    first = cached_fit_surrogate(roster, BOSS, score)
    decks_after_first = calls["decks"]
    second = cached_fit_surrogate(roster, BOSS, score)

    assert second is first                      # same object, not an equal one
    assert calls["decks"] == decks_after_first  # no second round of simulation


def test_cached_fit_refits_when_a_skill_level_changes():
    clear_fit_cache()
    roster = _investable_roster()
    score, calls = _scorer_favouring({"c0"})

    cached_fit_surrogate(roster, BOSS, score)
    decks_after_first = calls["decks"]
    roster[0].skill_values = {"s": {"description_value_01": "11"}}
    cached_fit_surrogate(roster, BOSS, score)

    assert calls["decks"] > decks_after_first


def test_cache_evicts_the_oldest_entry_past_its_bound():
    clear_fit_cache()
    score, _ = _scorer_favouring({"c0"})
    rosters = []
    for i in range(FIT_CACHE_SIZE + 1):
        roster = _investable_roster()
        roster[0].slug = f"a0-variant{i}"      # a distinct fingerprint each time
        rosters.append(roster)
        cached_fit_surrogate(roster, BOSS, score)

    # the first roster fell out, so asking again re-simulates
    score2, calls2 = _scorer_favouring({"c0"})
    cached_fit_surrogate(rosters[0], BOSS, score2)
    assert calls2["decks"] > 0
