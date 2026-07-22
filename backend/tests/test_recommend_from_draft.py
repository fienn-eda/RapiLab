"""Three-tier draft orchestrator: `recommend_from_draft` layers baseline (the
exact drafted groupings, scored as-is) <= within_draft (best reshuffle of
ONLY the drafted units) <= recommended (best over the full roster, which can
also pull in bench units) - and keeps the no-draft path a single
`allocate_decks` call (see `test_zero_base_recommended_matches_plain_allocation`).
All search/sim calls are stubbed, like test_deck_allocation.py - real sims
live in the API end-to-end test."""
import app.deck_allocation as da
from app.deck_search import BossProfile
from tests.test_deck_allocation import Unit, roster_of, patch_scorer

BOSS = BossProfile()

# Every drafted unit is worth 10 (fillers "a3"/"b3" are worth 1, so a swap
# that trades a filler for a bench unit is a clear win), plus a +20 synergy
# bonus when the two strongest B3s ("t3a1" and "t3b1") land in the SAME deck -
# the draft's exact grouping keeps them apart, so reshuffling (within_draft)
# strictly beats the baseline. One bench B3 ("t3x", worth 50) sits outside the
# draft entirely, so the full-roster search (recommended) strictly beats
# within_draft by swapping it in for a filler. Roster stays at 11 units (2/2/7)
# so shape_combinations' orderings (1176) stay under search_best_decks'
# sim_budget=1200 - a bigger roster trips prune_candidate_pool, which needs
# base_stats/weapon_stats this stub Unit doesn't have.
POWER = {
    "t1a": 10, "t1b": 10,
    "t2a": 10, "t2b": 10,
    "t3a1": 10, "t3a2": 10, "t3a3": 1,
    "t3b1": 10, "t3b2": 10, "t3b3": 1,
    "t3x": 50,
}
SYNERGY_PAIR = {"t3a1", "t3b1"}
SYNERGY_BONUS = 20


def _score(slugs):
    total = sum(POWER.get(s, 0) for s in slugs)
    if SYNERGY_PAIR <= slugs:
        total += SYNERGY_BONUS
    return total


def _roster():
    return roster_of({
        "t1a": 1, "t1b": 1,
        "t2a": 2, "t2b": 2,
        "t3a1": 3, "t3a2": 3, "t3a3": 3,
        "t3b1": 3, "t3b2": 3, "t3b3": 3,
        "t3x": 3,
    })


def _complete_draft(roster):
    # Exact (1,1,3) x 2 grouping that keeps the synergy pair split across
    # decks, and leaves the bench unit "t3x" undrafted.
    by_slug = {u.slug: u for u in roster}
    deck0 = [by_slug["t1a"], by_slug["t2a"], by_slug["t3a1"], by_slug["t3a2"], by_slug["t3a3"]]
    deck1 = [by_slug["t1b"], by_slug["t2b"], by_slug["t3b1"], by_slug["t3b2"], by_slug["t3b3"]]
    return [deck0, deck1]


def test_complete_draft_yields_monotone_tiers(monkeypatch):
    patch_scorer(monkeypatch, _score)
    r = _roster()
    draft = _complete_draft(r)
    out = da.recommend_from_draft(r, BOSS, num_decks=2, draft=draft, workers=None)

    base = out["baseline_total_damage"]
    within = sum(d["total_damage"] for d in out["within_draft"]["decks"])
    rec = sum(d["total_damage"] for d in out["recommended"]["decks"])

    assert base is not None and out["within_draft"] is not None
    assert base <= within + 1e-6
    assert within <= rec + 1e-6
    # Exact values (verified analytically): draft-as-given never co-locates
    # the synergy pair (82); reshuffling the 10 drafted units co-locates it
    # (102); pulling in the bench unit beats that too (151).
    assert base == 82.0
    assert within == 102.0
    assert rec == 151.0


def test_incomplete_draft_has_no_baseline(monkeypatch):
    patch_scorer(monkeypatch, _score)
    r = _roster()
    t1a = next(u for u in r if u.slug == "t1a")
    draft = [[t1a]]  # one partial deck; second deck not started
    out = da.recommend_from_draft(r, BOSS, num_decks=2, draft=draft, workers=None)
    assert out["baseline_total_damage"] is None
    assert out["within_draft"] is None
    assert out["recommended"]["decks"]


def test_zero_base_recommended_matches_plain_allocation(monkeypatch):
    # no draft: recommended must be the single from-scratch allocation (no
    # doubled warm pass), bit-identical to allocate_decks with no draft.
    patch_scorer(monkeypatch, _score)
    r = _roster()
    out = da.recommend_from_draft(r, BOSS, num_decks=2, draft=None, workers=None)
    assert out["recommended"] == da.allocate_decks(r, BOSS, num_decks=2, workers=None)
    assert out["within_draft"] is None
    assert out["baseline_total_damage"] is None


def test_pinned_by_deck_reports_locked_slugs_per_recommended_deck(monkeypatch):
    patch_scorer(monkeypatch, _score)
    r = _roster()
    t1a = next(u for u in r if u.slug == "t1a")
    draft = [[t1a]]
    out = da.recommend_from_draft(r, BOSS, num_decks=2, draft=draft,
                                  locked={"t1a"}, workers=None)
    pinned = out["pinned_by_deck"]
    assert len(pinned) == len(out["recommended"]["decks"])
    # t1a is locked and must appear in exactly one deck's pinned list
    hit = [p for p in pinned if "t1a" in p]
    assert len(hit) == 1
