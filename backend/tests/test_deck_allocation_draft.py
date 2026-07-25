"""Draft-seeded allocation: allocate_decks can start from a partial draft
(units the player already placed) and complete each seeded deck around them,
while `locked` slugs are masked out of the swap hill-climb so a pinned seat
never moves. All search/sim calls are stubbed via the same fixtures
test_deck_allocation.py uses - real sims live in the API end-to-end test."""
import pytest

import app.deck_allocation as da
from app.deck_search import BossProfile
from tests.test_deck_allocation import roster_of, patch_scorer

BOSS = BossProfile()


def _roster():
    # Kept small (10 units, like test_deck_allocation.py's fixtures): a
    # roster big enough to trip prune_candidate_pool's sim_budget would call
    # _prior, which needs base_stats/weapon_stats the stub Unit doesn't have.
    tiers = {}
    for i in range(2):
        tiers[f"b1{i}"] = 1
    for i in range(2):
        tiers[f"b2{i}"] = 2
    for i in range(6):
        tiers[f"b3{i}"] = 3
    return roster_of(tiers)


def test_draft_none_matches_plain_allocation(monkeypatch):
    r = _roster()
    patch_scorer(monkeypatch, lambda slugs: sum(len(s) for s in slugs))
    with_draft = da.allocate_decks(r, BOSS, num_decks=2, draft=None, workers=None)
    plain = da.allocate_decks(r, BOSS, num_decks=2, workers=None)
    assert with_draft == plain


def test_locked_unit_stays_in_its_deck(monkeypatch):
    # Built so the leftover-swap hill-climb WOULD dislodge the locked unit if
    # the mask were missing: "weak3" is strictly the worst B3 (quality 1),
    # z3 is a strictly better leftover (quality 5) - swapping them in is a
    # real score improvement (21 -> 25), so only `locked` stops it. A scorer
    # that's constant across every 5-unit deck (e.g. sum(len(slug))) can't
    # tell this apart from a deleted mask, since no swap is ever accepted
    # either way - see review fix, 2026-07-22.
    r = roster_of({"solo_b1": 1, "solo_b2": 2,
                   "weak3": 3, "z3": 3, "x3": 3, "y3": 3})
    quality = {"weak3": 1, "z3": 5, "x3": 10, "y3": 10}
    patch_scorer(monkeypatch, lambda slugs: sum(quality.get(s, 0) for s in slugs))
    weak3 = next(u for u in r if u.slug == "weak3")
    out = da.allocate_decks(r, BOSS, num_decks=1, draft=[[weak3]],
                             locked={"weak3"}, time_budget_sec=30.0, workers=None)
    assert "weak3" in out["decks"][0]["deck"]


def _wide_roster():
    """Big enough that completing a one-seat draft blows SEARCH_SIM_BUDGET -
    the shape of draft a player produces by dropping a single chip."""
    tiers = {f"b1{i}": 1 for i in range(4)}
    tiers |= {f"b2{i}": 2 for i in range(6)}
    tiers |= {f"b3{i}": 3 for i in range(14)}
    return roster_of(tiers)


def _spy_on_completions(monkeypatch):
    """Record the `cascade` each best_completions call receives, returning a
    completion built by hand (the real search would need investment fields the
    stub Unit lacks)."""
    seen = []

    def fake(required, candidates, boss, top_n=1, pool=None, cascade=None, **kw):
        seen.append(cascade)
        by_tier = {t: [u for u in candidates if u.burst_tier == t] for t in (1, 2, 3)}
        held = {u.burst_tier for u in required}
        fill = ([by_tier[1][0]] if 1 not in held else []) \
            + ([by_tier[2][0]] if 2 not in held else [])
        deck = list(required) + fill
        deck += [u for u in by_tier[3] if u not in deck][:5 - len(deck)]
        return [{"deck": [u.slug for u in deck], "total_damage": 1.0,
                 "burst_damage": 0.0, "normal_attack_damage": 0.0,
                 "result": {"total_damage": 1.0, "damage_log": []}}]

    monkeypatch.setattr(da, "best_completions", fake)
    return seen


def test_a_thin_seed_is_completed_with_the_cascade(monkeypatch):
    """A one-seat draft blows the completion budget, so the seed must be
    completed against the ranked shortlist rather than prune's cut alone -
    otherwise the thinnest draft, the one a player reaches first, gets the
    worst recommendation."""
    r = _wide_roster()
    patch_scorer(monkeypatch, lambda slugs: 1.0)
    monkeypatch.setattr(da, "cached_fit_surrogate", lambda *a, **kw: object())
    seen = _spy_on_completions(monkeypatch)
    seed = [next(u for u in r if u.slug == "b30")]

    da.allocate_decks(r, BOSS, num_decks=1, draft=[seed], workers=None,
                      time_budget_sec=0.0)

    assert seen and all(c is not None for c in seen)


def test_a_seed_within_budget_never_pays_for_a_fit(monkeypatch):
    """The ranker is a budget escape hatch: a draft whose completions are
    cheap to enumerate must not trigger a 200-deck surrogate fit."""
    r = _roster()
    patch_scorer(monkeypatch, lambda slugs: 1.0)
    fits = []
    monkeypatch.setattr(da, "cached_fit_surrogate",
                        lambda *a, **kw: fits.append(1) or object())
    seen = _spy_on_completions(monkeypatch)
    seed = [next(u for u in r if u.slug == "b30")]

    da.allocate_decks(r, BOSS, num_decks=1, draft=[seed], workers=None,
                      time_budget_sec=0.0)

    assert seen == [None]
    assert fits == []


def test_infeasible_draft_raises():
    # 3 tier-1 units: no ALLOWED_SHAPES has n1 > 2, so no completion exists.
    # best_completions rejects this on tier counts alone, before touching
    # search_best_decks/prune_candidate_pool, so the roster's size doesn't
    # matter here the way it does for the other tests in this file.
    r = roster_of({"b10": 1, "b11": 1, "b12": 1})
    with pytest.raises(da.InfeasibleDraft):
        da.allocate_decks(r, BOSS, num_decks=1, draft=[r], locked=set(), workers=None)


def _cancel_after(n_calls, token):
    """Trip `token` once the search has scored `n_calls` batches - a stand-in
    for the user pressing Cancel partway through."""
    calls = {"n": 0}

    def scorer(slugs):
        calls["n"] += 1
        if calls["n"] >= n_calls:
            token.cancel()
        return 1.0

    return scorer, calls


def test_a_cancelled_allocation_stops_instead_of_finishing(monkeypatch):
    """Cancel has to reach the search, not just the response: the point is that
    the work stops, so allocate_decks abandons the run rather than returning a
    result nobody is waiting for.

    Coarse here on purpose. A serial run has no pool, so it can only be asked
    BETWEEN batches and the batch already in flight still finishes. The parallel
    path the API actually uses is folded mid-batch by SimPool.cancel instead -
    see test_sim_pool's cancelled-batch tests.
    """
    from app.cancellation import CancelToken, Cancelled

    r = _wide_roster()
    full = {"n": 0}
    patch_scorer(monkeypatch, lambda slugs: full.__setitem__("n", full["n"] + 1) or 1.0)
    da.allocate_decks(r, BOSS, num_decks=3, workers=None)

    token = CancelToken()
    scorer, calls = _cancel_after(1, token)
    patch_scorer(monkeypatch, scorer)

    with pytest.raises(Cancelled):
        da.allocate_decks(r, BOSS, num_decks=3, workers=None, cancel=token)

    assert calls["n"] < full["n"], (
        f"cancelled run scored {calls['n']} decks, a full one {full['n']}")


def test_an_uncancelled_allocation_is_unchanged(monkeypatch):
    """The token defaults to a do-nothing one, so every existing caller - and
    every test above - keeps the exact behaviour it had."""
    r = _roster()
    patch_scorer(monkeypatch, lambda slugs: sum(len(s) for s in slugs))

    with_token = da.allocate_decks(r, BOSS, num_decks=2, workers=None,
                                   cancel=None)
    plain = da.allocate_decks(r, BOSS, num_decks=2, workers=None)

    assert with_token == plain


def test_the_pool_is_attached_so_a_cancel_reaches_the_workers(monkeypatch):
    """The loops can be asked between iterations, but the workers are blocked
    inside a batch. They only stop if the pool itself is registered with the
    token - so allocate_decks must hand its pool over as soon as it builds one.
    """
    from app.cancellation import CancelToken

    class _FakePool:
        def __init__(self, *a, **kw):
            self.cancelled = 0

        def score_many(self, decks):
            # Stands in for the process pool; the scores themselves are not
            # what this test is about.
            return [1.0 for _ in decks]

        def cancel(self):
            self.cancelled += 1

        def close(self):
            pass

    built = []
    monkeypatch.setattr(da, "SimPool", lambda *a, **kw: built.append(_FakePool()) or built[-1])
    monkeypatch.setattr(da, "resolve_workers", lambda w: 2)
    patch_scorer(monkeypatch, lambda slugs: 1.0)
    token = CancelToken()

    da.allocate_decks(_roster(), BOSS, num_decks=1, workers=2, cancel=token,
                      time_budget_sec=0.0)
    token.cancel()

    assert built and built[0].cancelled == 1, "the pool was never registered"
