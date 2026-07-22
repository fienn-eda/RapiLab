"""best_completions finds the best 5-unit deck that CONTAINS a required unit
set, searching every ALLOWED_SHAPES-compatible completion (Task 1 of
draft-based deck allocation)."""
from dataclasses import dataclass

import app.deck_search as ds
from app.deck_search import BossProfile, best_completions

BOSS = BossProfile()


@dataclass(frozen=True)
class Unit:
    slug: str
    burst_tier: int


def patch_scorer(monkeypatch, scorer):
    # best_completions only calls evaluate_deck via deck_search's own module
    # binding (through _score_batch/_summarize), so patching it here suffices.
    def fake_evaluate(ordered_deck, boss):
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
