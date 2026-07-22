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
    r = _roster()
    patch_scorer(monkeypatch, lambda slugs: sum(len(s) for s in slugs))
    draft = [[next(u for u in r if u.slug == "b30")]]  # seed deck 0 with b30, locked
    out = da.allocate_decks(r, BOSS, num_decks=2, draft=draft,
                             locked={"b30"}, workers=None)
    assert "b30" in out["decks"][0]["deck"]


def test_infeasible_draft_raises():
    # 3 tier-1 units: no ALLOWED_SHAPES has n1 > 2, so no completion exists.
    # best_completions rejects this on tier counts alone, before touching
    # search_best_decks/prune_candidate_pool, so the roster's size doesn't
    # matter here the way it does for the other tests in this file.
    r = roster_of({"b10": 1, "b11": 1, "b12": 1})
    with pytest.raises(da.InfeasibleDraft):
        da.allocate_decks(r, BOSS, num_decks=1, draft=[r], locked=set(), workers=None)
