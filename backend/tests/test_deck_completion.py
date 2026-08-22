"""best_completions finds the best 5-unit deck that CONTAINS a required unit
set, searching every ALLOWED_SHAPES-compatible completion (Task 1 of
draft-based deck allocation)."""
from dataclasses import dataclass, field

import app.deck_search as ds
from app.deck_search import (BossProfile, _all_intra_tier_orderings,
                             _shape_completions, best_completions)

BOSS = BossProfile()


@dataclass(frozen=True)
class Unit:
    slug: str
    burst_tier: int
    # prune_candidate_pool's round-0 prior reads these; uniform values keep the
    # ranking decided by the (patched) simulated deltas rather than by stats.
    base_stats: dict = field(default_factory=lambda: {"atk": 60_000.0})
    weapon_stats: dict = field(default_factory=lambda: {"damage_percent": 1.0})


def patch_scorer(monkeypatch, scorer):
    # best_completions only calls evaluate_deck via deck_search's own module
    # binding (through _score_batch/_summarize), so patching it here suffices.
    def fake_evaluate(ordered_deck, boss, **kwargs):
        return {"total_damage": scorer({u.slug for u in ordered_deck}),
                "damage_log": []}

    monkeypatch.setattr(ds, "evaluate_deck", fake_evaluate)


def test_completion_includes_all_required_and_fills_all_tiers(monkeypatch):
    # required = one Burst-3; completion must add B1+B2 (+ more) to a legal shape
    required = [Unit("b3a", 3)]
    candidates = [Unit("b1a", 1), Unit("b2a", 2), Unit("b3b", 3), Unit("b3c", 3)]
    patch_scorer(monkeypatch, lambda slugs: 1.0)

    out = best_completions(required, candidates, BOSS, top_n=1)

    assert out, "expected at least one completion"
    deck = set(out[0]["deck"])
    assert "b3a" in deck                     # required always present
    assert len(deck) == 5
    tier_by_slug = {u.slug: u.burst_tier for u in required + candidates}
    tiers = {tier_by_slug[slug] for slug in deck}
    assert tiers == {1, 2, 3}                # all three tiers represented


def test_completion_infeasible_returns_empty():
    # three B1 required cannot fit any ALLOWED_SHAPES (max B1 per deck is 2)
    required = [Unit("b1a", 1), Unit("b1b", 1), Unit("b1c", 1)]
    candidates = [Unit("b2a", 2), Unit("b3a", 3), Unit("b3b", 3)]
    assert best_completions(required, candidates, BOSS) == []


def _roster(n1, n2, n3):
    return ([Unit(f"b1{i}", 1) for i in range(n1)]
            + [Unit(f"b2{i}", 2) for i in range(n2)]
            + [Unit(f"b3{i}", 3) for i in range(n3)])


def test_a_thinly_drafted_deck_stays_inside_the_simulation_budget(monkeypatch):
    """A draft with one seat placed leaves nearly the whole roster to draw
    from, and every completion of it is a legal deck - on a real roster that
    is ~1.8M orderings, hours of simulation for a single deck. The completion
    search has to cut the pool the way search_best_decks does rather than
    simulate all of them."""
    required = [Unit("b3a", 3)]
    candidates = _roster(4, 6, 14)
    exhaustive = len(_all_intra_tier_orderings(_shape_completions(required, candidates)))
    assert exhaustive > 1000, "fixture must actually blow the budget"

    scored = []
    patch_scorer(monkeypatch, lambda slugs: scored.append(slugs) or float(len(scored)))

    out = best_completions(required, candidates, BOSS, top_n=1, sim_budget=200)

    assert out, "a reduced search must still return a legal completion"
    assert "b3a" in out[0]["deck"]
    assert len(scored) < exhaustive // 10, (
        f"scored {len(scored)} decks; the exhaustive path scores {exhaustive}")


class _FakeCascade:
    """Hands back a fixed shortlist (or declines), recording what it was asked."""

    def __init__(self, combos):
        self.combos = combos
        self.asked = []

    def shortlist_completions(self, required, candidates, boss, pool=None):
        self.asked.append(([u.slug for u in required], len(candidates)))
        return self.combos


def test_a_blown_budget_simulates_the_cascades_shortlist(monkeypatch):
    """Over budget, the ranker picks which completions are worth simulating -
    the same escape hatch search_best_decks uses, and for the same reason: a
    cut that only measures marginal contribution in a reference deck the draft
    is absent from has worse recall than one that also ranks whole decks."""
    required = [Unit("b3a", 3)]
    candidates = _roster(4, 6, 14)
    by_slug = {u.slug: u for u in candidates}
    picked = [required[0], by_slug["b10"], by_slug["b20"], by_slug["b30"], by_slug["b31"]]
    cascade = _FakeCascade([picked])
    scored = []
    patch_scorer(monkeypatch, lambda slugs: scored.append(slugs) or 1.0)

    out = best_completions(required, candidates, BOSS, top_n=1, sim_budget=200,
                           cascade=cascade)

    assert cascade.asked == [(["b3a"], len(candidates))]
    assert set(out[0]["deck"]) == {u.slug for u in picked}
    assert all(s == {u.slug for u in picked} for s in scored), "only the shortlist is simulated"


def test_a_declining_cascade_falls_back_to_the_pruned_pool(monkeypatch):
    """The ranker may refuse (a roster its fit never saw, no legal completion),
    and refusing must not cost the player a recommendation."""
    required = [Unit("b3a", 3)]
    candidates = _roster(4, 6, 14)
    cascade = _FakeCascade(None)
    patch_scorer(monkeypatch, lambda slugs: 1.0)

    out = best_completions(required, candidates, BOSS, top_n=1, sim_budget=200,
                           cascade=cascade)

    assert cascade.asked, "the cascade was consulted"
    assert out and "b3a" in out[0]["deck"]


def test_completions_within_budget_never_consult_the_cascade(monkeypatch):
    """The ranker is a budget escape hatch. A pool small enough to enumerate
    must still be searched exhaustively, or a cheap draft silently pays for a
    surrogate fit it does not need."""
    required = [Unit("b3a", 3)]
    candidates = _roster(2, 2, 3)
    cascade = _FakeCascade(None)
    patch_scorer(monkeypatch, lambda slugs: 1.0)

    best_completions(required, candidates, BOSS, top_n=1, cascade=cascade)

    assert cascade.asked == []


def test_completions_within_budget_are_still_searched_exhaustively(monkeypatch):
    """The cut is a budget escape hatch, not the normal path: a pool small
    enough to enumerate must still find the true best completion."""
    required = [Unit("b3a", 3)]
    candidates = _roster(2, 2, 3)
    patch_scorer(monkeypatch, lambda slugs: 2.0 if "b11" in slugs else 1.0)

    out = best_completions(required, candidates, BOSS, top_n=1)

    assert out[0]["total_damage"] == 2.0
    assert "b11" in out[0]["deck"]
