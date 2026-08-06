from types import SimpleNamespace

import numpy as np

from app.cascade import (DEFAULT_TOP_K, FIT_CACHE_SIZE, WIDE_TIER_CAPS,
                         Cascade, SurrogateModel, cached_fit_surrogate,
                         clear_fit_cache, fit_surrogate, roster_fingerprint,
                         widened_pool)
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


class _FakeModel:
    """Coefficients straight from a dict, so pool tests don't need a real fit."""

    def __init__(self, values):
        self.values = values

    def coefficient(self, slug):
        return self.values.get(slug, 0.0)


def test_widened_pool_keeps_every_pruned_unit(monkeypatch):
    roster = _roster()
    pruned = [roster[0], roster[4], roster[10], roster[11], roster[12]]
    monkeypatch.setattr("app.cascade.prune_candidate_pool",
                        lambda r, b, p=None: pruned)

    out = widened_pool(roster, BOSS, _FakeModel({}))

    assert set(u.slug for u in pruned) <= set(u.slug for u in out)


def test_widened_pool_respects_the_tier_caps(monkeypatch):
    roster = _roster(n1=8, n2=10, n3=20)
    # prune's picks fit within their tiers' caps here (2 per tier), so this
    # exercises the coefficient pass topping up to the cap in the ordinary
    # case; a tier where prune's own picks exceed the cap is covered by
    # test_widened_pool_keeps_every_pruned_unit_past_its_tier_cap below.
    monkeypatch.setattr(
        "app.cascade.prune_candidate_pool",
        lambda r, b, p=None: list(r)[:2] + list(r)[8:10] + list(r)[18:20])

    out = widened_pool(roster, BOSS, _FakeModel({}))

    counts = {t: sum(1 for u in out if u.burst_tier == t) for t in (1, 2, 3)}
    assert counts == WIDE_TIER_CAPS


def test_widened_pool_keeps_every_pruned_unit_past_its_tier_cap(monkeypatch):
    # caps are a FLOOR on prune's output, not a ceiling: a tier prune fills
    # past its cap (e.g. a synergy pull-in) must keep every one of those
    # picks, or the safety net silently drops exactly the units it exists to
    # protect - see widened_pool's docstring.
    roster = _roster(n1=8, n2=10, n3=20)
    over_cap = list(roster)[18:31]  # 13 tier-3 units; cap[3] is 12
    assert len(over_cap) > WIDE_TIER_CAPS[3]
    monkeypatch.setattr("app.cascade.prune_candidate_pool",
                        lambda r, b, p=None: over_cap)

    out = widened_pool(roster, BOSS, _FakeModel({}))
    slugs = {u.slug for u in out}

    assert {u.slug for u in over_cap} <= slugs
    tier3_count = sum(1 for u in out if u.burst_tier == 3)
    assert tier3_count == len(over_cap)  # the coefficient pass added nothing


def test_widened_pool_fills_remaining_seats_by_coefficient_within_tier(monkeypatch):
    roster = _roster(n1=8, n2=10, n3=20)
    monkeypatch.setattr("app.cascade.prune_candidate_pool", lambda r, b, p=None: [])
    # c19 is the best tier-3 unit; a7 the best tier-1. Both must be picked even
    # though a tier-blind sort by coefficient would fill up on tier 3 alone.
    model = _FakeModel({f"c{i}": i for i in range(20)} | {"a7": 1000.0})

    out = widened_pool(roster, BOSS, model)
    slugs = {u.slug for u in out}

    assert "c19" in slugs and "c8" in slugs   # top 12 of tier 3
    assert "c7" not in slugs                  # 13th, cut
    assert "a7" in slugs


def test_widened_pool_seats_prunes_pick_before_a_contested_coefficient_seat(monkeypatch):
    # One more tier-1 unit than WIDE_TIER_CAPS[1] (4), so the tier-1 bucket is
    # contested: prune's pick and the coefficient ranking can't both fully fit.
    roster = _roster(n1=5)
    pruned = [roster[0]]  # a0: prune's sole tier-1 pick
    monkeypatch.setattr("app.cascade.prune_candidate_pool",
                        lambda r, b, p=None: pruned)
    # a0 is the worst tier-1 coefficient; a1..a4 outrank it and each other.
    model = _FakeModel({"a0": -100.0, "a1": 10.0, "a2": 20.0, "a3": 30.0, "a4": 40.0})

    out = widened_pool(roster, BOSS, model)
    slugs = {u.slug for u in out}

    assert "a0" in slugs   # prune's pick survives despite the worst coefficient
    assert "a1" not in slugs  # the coefficient loop's weakest pick loses the contested seat to a0


def test_widened_pool_returns_units_in_tier_order(monkeypatch):
    roster = _roster()
    monkeypatch.setattr("app.cascade.prune_candidate_pool", lambda r, b, p=None: [])
    out = widened_pool(roster, BOSS, _FakeModel({}))
    tiers = [u.burst_tier for u in out]
    assert tiers == sorted(tiers)


def test_widened_pool_handles_a_roster_smaller_than_the_caps(monkeypatch):
    roster = _roster(n1=1, n2=1, n3=3)
    monkeypatch.setattr("app.cascade.prune_candidate_pool", lambda r, b, p=None: [])
    out = widened_pool(roster, BOSS, _FakeModel({}))
    assert len(out) == 5


def test_shortlist_returns_top_k_combinations(monkeypatch):
    roster = _roster()
    monkeypatch.setattr("app.cascade.prune_candidate_pool", lambda r, b, p=None: [])
    model = fit_surrogate(roster, BOSS, _scorer_favouring({"c0"})[0], samples=120)

    combos = Cascade(model, top_k=7).shortlist(roster, BOSS)

    assert len(combos) == 7
    assert all(len(c) == 5 for c in combos)


def test_shortlist_is_ordered_by_predicted_score(monkeypatch):
    roster = _roster()
    monkeypatch.setattr("app.cascade.prune_candidate_pool", lambda r, b, p=None: [])
    model = fit_surrogate(roster, BOSS, _scorer_favouring({"c0", "b0"})[0], samples=120)

    combos = Cascade(model, top_k=10).shortlist(roster, BOSS)
    scores = model.score_combos(combos)

    assert list(scores) == sorted(scores, reverse=True)


def test_shortlist_declines_a_roster_the_model_does_not_cover(monkeypatch):
    roster = _roster()
    monkeypatch.setattr("app.cascade.prune_candidate_pool", lambda r, b, p=None: [])
    model = fit_surrogate(roster, BOSS, _scorer_favouring({"c0"})[0], samples=120)

    assert Cascade(model).shortlist(roster + [_u("stranger", 3)], BOSS) is None


def test_shortlist_declines_when_no_legal_combination_exists(monkeypatch):
    roster = _roster()
    model = fit_surrogate(roster, BOSS, _scorer_favouring({"c0"})[0], samples=120)
    monkeypatch.setattr("app.cascade.prune_candidate_pool", lambda r, b, p=None: [])
    # a subset with no tier-2 unit can form no legal deck
    tierless = [u for u in roster if u.burst_tier != 2]

    assert Cascade(model).shortlist(tierless, BOSS) is None


def test_shortlist_returns_everything_when_k_exceeds_the_pool(monkeypatch):
    roster = _roster(n1=1, n2=1, n3=3)
    monkeypatch.setattr("app.cascade.prune_candidate_pool", lambda r, b, p=None: [])
    model = _FakeModel({})
    model.covers = lambda r: True
    model.score_combos = lambda combos: np.zeros(len(combos))

    combos = Cascade(model, top_k=1000).shortlist(roster, BOSS)
    assert len(combos) == 1


def test_shortlist_completions_seats_every_drafted_unit(monkeypatch):
    roster = _roster()
    monkeypatch.setattr("app.cascade.prune_candidate_pool", lambda r, b, p=None: [])
    model = fit_surrogate(roster, BOSS, _scorer_favouring({"c0"})[0], samples=120)
    required = [u for u in roster if u.slug == "c5"]
    candidates = [u for u in roster if u.slug != "c5"]

    combos = Cascade(model, top_k=7).shortlist_completions(required, candidates, BOSS)

    assert len(combos) == 7
    assert all(len(c) == 5 for c in combos)
    assert all("c5" in {u.slug for u in c} for c in combos)


def test_shortlist_completions_is_ordered_by_predicted_score(monkeypatch):
    roster = _roster()
    monkeypatch.setattr("app.cascade.prune_candidate_pool", lambda r, b, p=None: [])
    model = fit_surrogate(roster, BOSS, _scorer_favouring({"c0", "b0"})[0], samples=120)
    required = [u for u in roster if u.slug == "c5"]
    candidates = [u for u in roster if u.slug != "c5"]

    combos = Cascade(model, top_k=10).shortlist_completions(required, candidates, BOSS)
    scores = model.score_combos(combos)

    assert list(scores) == sorted(scores, reverse=True)


def test_shortlist_completions_declines_a_drafted_unit_the_model_never_saw(monkeypatch):
    # The drafted units are scored as deck members, not just honored as a
    # constraint, so a unit with no column would KeyError in featurize.
    roster = _roster()
    monkeypatch.setattr("app.cascade.prune_candidate_pool", lambda r, b, p=None: [])
    model = fit_surrogate(roster, BOSS, _scorer_favouring({"c0"})[0], samples=120)

    assert Cascade(model).shortlist_completions([_u("stranger", 3)], roster, BOSS) is None


def test_shortlist_completions_declines_when_the_draft_fits_no_shape(monkeypatch):
    # three Burst-1s exceed every ALLOWED_SHAPES tier-1 slot count
    roster = _roster()
    monkeypatch.setattr("app.cascade.prune_candidate_pool", lambda r, b, p=None: [])
    model = fit_surrogate(roster, BOSS, _scorer_favouring({"c0"})[0], samples=120)
    required = [u for u in roster if u.slug in ("a0", "a1", "a2")]

    assert Cascade(model).shortlist_completions(required, roster, BOSS) is None


def test_the_pool_width_and_the_shortlist_width_are_one_setting():
    """These two numbers are not independent knobs, and the pair is measured.

    The pool decides what can be ranked; K decides how much of that ranking the
    simulator gets to overrule. Widen the pool without widening K and the
    shortlist fills with combinations the unit-only surrogate overrates, which
    pushes the genuinely best deck out of the twenty that get simulated. On
    Fienn's roster (78 usable, 5 decks, Wind boss, DEF 31,784, 180 s), measured
    2026-08-06 with `python3 scripts/measure_pool_caps.py`:

        caps      K=20                    K=100
        2/4/8     40.932B  (-0.30%)       -
        3/5/10    41.579B  (+1.27%)       -
        4/6/12    41.056B  (shipped)      41.228B  (+0.42%)
        6/9/18    36.408B  (-11.32%)      40.846B  (-0.51%)
        8/12/24   36.408B  (-11.32%)      40.846B  (-0.51%)

    So quality is NOT monotone in the caps and the shipped pair is not a peak -
    3/5/10 beat it by 1.27% in the same wall time on that one roster. Two
    stale roadmap notes read the other way ("widening the pool is worth 0",
    "widen it so the pool stops missing CDR units"); both were measured before
    the swap budget became a candidate count, and following either one today
    costs 11% unless K moves with it.

    Change either constant and this test fails on purpose: re-run the sweep on
    a real roster, on at least two bosses, and put the new table here.
    """
    assert (WIDE_TIER_CAPS, DEFAULT_TOP_K) == ({1: 4, 2: 6, 3: 12}, 20), (
        "pool caps and shortlist width are a measured pair - see this test's "
        "docstring and re-run scripts/measure_pool_caps.py before changing them"
    )
