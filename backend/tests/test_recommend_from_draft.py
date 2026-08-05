"""Three-tier draft orchestrator: `recommend_from_draft` layers baseline (the
exact drafted groupings, scored as-is) <= within_draft (best reshuffle of
ONLY the drafted units) <= recommended (best over the full roster, which can
also pull in bench units) - and keeps the no-draft path a single
`allocate_decks` call (see `test_zero_base_recommended_matches_plain_allocation`).
All search/sim calls are stubbed, like test_deck_allocation.py - real sims
live in the API end-to-end test."""
from unittest.mock import patch

import app.deck_allocation as da
from app.deck_search import SOLE_TIER1_SLUGS, BossProfile
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
    # (102). `recommended` is now max(warm, within_draft) - no full-roster
    # scratch pass. warm's seed step reproduces the draft's two decks
    # unchanged (both already full, so best_completions has nothing to add),
    # then its swap-improvement hill-climb (i) trades a drafted B3 seat for
    # bench unit "t3x" against the leftover pool (t1a/t2a/t3x/t3a2/t3b2 = 90)
    # and (ii) separately co-locates the synergy pair via a same-tier pair
    # swap (t1b/t2b/t3b1/t3a1/t3b3 = 61), reaching the same 151 the old
    # full-roster scratch pass found - so the value is unchanged even though
    # the path that produces it is.
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


# Quality per slug for the locked-unit test (mirrors Task 2's
# test_locked_unit_stays_in_its_deck, scaled to a 2-deck draft): "pweak" is
# deliberately the WORST unit on the roster, so an unconstrained from-scratch
# search would always bench it (it's the unique global-min, so no leftover
# tie-break makes this test flaky) - only honoring `locked` keeps it seated.
# "bx" is a bench unit (quality 50, undrafted) an unconstrained search would
# rather pull in over the weak locked unit.
LOCKED_QUALITY = {
    "p1": 10, "q1": 10,
    "p2": 10, "q2": 10,
    "pweak": 1, "pz": 5,
    "g1": 10, "g2": 10, "g3": 10, "g4": 10,
    "bx": 50,
}


def _locked_score(slugs):
    return sum(LOCKED_QUALITY.get(s, 0) for s in slugs)


def _locked_roster():
    return roster_of({
        "p1": 1, "q1": 1,
        "p2": 2, "q2": 2,
        "pweak": 3, "pz": 3, "g1": 3, "g2": 3, "g3": 3, "g4": 3, "bx": 3,
    })


def _locked_draft(roster):
    by_slug = {u.slug: u for u in roster}
    deck0 = [by_slug["p1"], by_slug["p2"], by_slug["pweak"], by_slug["pz"], by_slug["g1"]]
    deck1 = [by_slug["q1"], by_slug["q2"], by_slug["g2"], by_slug["g3"], by_slug["g4"]]
    return [deck0, deck1]


def test_locked_unit_stays_in_recommended_even_though_it_is_the_weakest(monkeypatch):
    # For a complete draft, `recommended` is warm (or within_draft if it
    # scores higher; it doesn't here). Without the lock, warm's leftover-swap
    # hill-climb benches "pweak" (quality 1, the unique roster minimum) in
    # favor of the bench unit "bx" (quality 50) - proven below, so this test
    # has teeth rather than being a tautology. Locking "pweak" into deck 0
    # must keep it seated in `recommended` via warm's swap mask (locked slugs
    # are never chosen as a swap source), even at a lower total than the
    # unconstrained optimum, and it must show up in `pinned_by_deck`.
    patch_scorer(monkeypatch, _locked_score)
    r = _locked_roster()
    draft = _locked_draft(r)

    unlocked = da.recommend_from_draft(r, BOSS, num_decks=2, draft=draft, workers=None)
    assert not any("pweak" in d["deck"] for d in unlocked["recommended"]["decks"]), (
        "test setup: without a lock, warm must bench pweak, or this test is a tautology")

    out = da.recommend_from_draft(r, BOSS, num_decks=2, draft=draft,
                                  locked={"pweak"}, workers=None)
    hit = [i for i, d in enumerate(out["recommended"]["decks"])
           if "pweak" in d["deck"]]
    assert len(hit) == 1, "locked unit must be seated in exactly one recommended deck"
    assert "pweak" in out["pinned_by_deck"][hit[0]]


def test_complete_draft_makes_exactly_three_allocate_decks_calls(monkeypatch):
    # Locks in the optimization: a complete draft must call allocate_decks
    # exactly THREE times - warm (`recommended`) plus within_draft's `w` and
    # `s` - NOT four. A regression back to also computing the full-roster
    # scratch pass for `recommended` would show up here as a 4th call, even
    # if the two candidate allocations happened to agree on the winner.
    patch_scorer(monkeypatch, _score)
    r = _roster()
    draft = _complete_draft(r)
    with patch.object(da, "allocate_decks", wraps=da.allocate_decks) as spy:
        da.recommend_from_draft(r, BOSS, num_decks=2, draft=draft, workers=None)
    assert spy.call_count == 3


def test_zero_base_makes_exactly_one_allocate_decks_call(monkeypatch):
    # Finding 3: the zero-base short-circuit must stay a SINGLE allocate_decks
    # call - not just bit-identical output, but one real search pass. Wraps
    # the real function with a call counter instead of stubbing it away, so a
    # regression back to a warm+scratch double-call would be caught here even
    # if the two calls happened to agree on the winning allocation.
    patch_scorer(monkeypatch, _score)
    r = _roster()
    with patch.object(da, "allocate_decks", wraps=da.allocate_decks) as spy:
        da.recommend_from_draft(r, BOSS, num_decks=2, draft=None, workers=None)
    assert spy.call_count == 1


def test_baseline_filters_out_a_reading_the_search_would_never_field(monkeypatch):
    # Final-review finding 1: baseline_total_damage used to score every
    # candidate reading of a drafted seat with best_ordering_summary alone,
    # which enforces only the buffer-seat rule (_intra_tier_orderings) - not
    # ALLOWED_SHAPES or tier-1 seating. A seat whose alternate reading swaps in
    # a SOLE_TIER1_SLUGS unit next to another Burst-1 unit produces a deck
    # deck_is_valid rejects (two Burst-1s, one of them sole-seat-only) but
    # best_ordering_summary would happily score - and score higher here, so an
    # unfiltered max() would take it. This has teeth: without the
    # deck_is_valid filter added to recommend_from_draft, this assertion fails
    # (baseline comes out 999.0, the illegal reading's score).
    sole_tier1_slug = next(iter(SOLE_TIER1_SLUGS))
    by_slug = {u.slug: u for u in roster_of({
        "t1": 1, "t2": 2, "t3a": 3, "t3b": 3, "rep": 3,
    })}
    rep = by_slug["rep"]
    alt = Unit(sole_tier1_slug, 1)  # rep's alternate reading: a second Burst-1
    seed = [by_slug["t1"], by_slug["t2"], by_slug["t3a"], by_slug["t3b"], rep]

    def score(slugs):
        return 999.0 if sole_tier1_slug in slugs else 50.0

    patch_scorer(monkeypatch, score)
    roster = list(by_slug.values()) + [alt]
    out = da.recommend_from_draft(
        roster, BOSS, num_decks=1, draft=[seed],
        alternatives={"rep": (rep, alt)}, workers=None)

    assert out["baseline_total_damage"] == 50.0


def test_a_converged_allocation_reports_that_it_converged(monkeypatch):
    """The flag is what the UI uses to decide whether to warn, so a run that
    finished must not carry the warning."""
    roster = roster_of({
        "a1": 1, "a2": 2, "a3": 3, "a4": 3, "a5": 3,
        "b1": 1, "b2": 2, "b3": 3, "b4": 3, "b5": 3,
    })
    patch_scorer(monkeypatch, lambda slugs: 100.0)

    out = da.recommend_from_draft(roster, BOSS, num_decks=2)

    assert out["swap_converged"] is True


def test_a_budget_that_binds_reports_that_it_did_not_converge(monkeypatch):
    """allocate_decks' flag has to survive the trip up through
    recommend_from_draft - including the branch that rebuilds `recommended`
    from within_draft, which carries only the keys it is handed."""
    roster = roster_of({
        "a1": 1, "a2": 2, "a3": 3, "a4": 3, "a5": 3,
        "b1": 1, "b2": 2, "b3": 3, "b4": 3, "b5": 3,
    })
    patch_scorer(monkeypatch, lambda slugs: 100.0)

    alloc = da.allocate_decks(roster, BOSS, num_decks=2, swap_budget=1)

    assert alloc["swap_converged"] is False
