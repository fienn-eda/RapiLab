"""Allocation layer: greedy peeling picks disjoint decks best-first; the
same-tier swap pass recovers the classic greedy mistake (stacking two strong
supporters in deck 1 when splitting them wins). All search/sim calls are
stubbed - real sims live in the API end-to-end test."""
from dataclasses import dataclass

import app.deck_allocation as da
from app.deck_search import BossProfile


@dataclass(frozen=True)
class Unit:
    slug: str
    burst_tier: int


def roster_of(tiers_by_slug):
    return [Unit(s, t) for s, t in tiers_by_slug.items()]


def patch_scorer(monkeypatch, scorer):
    # allocate_decks calls evaluate_deck both directly AND through
    # search_best_decks (deck_search's own module binding) - patch both.
    import app.deck_search as ds

    def fake_evaluate(ordered_deck, boss):
        return {"total_damage": scorer({u.slug for u in ordered_deck}),
                "damage_log": []}

    monkeypatch.setattr(ds, "evaluate_deck", fake_evaluate)
    monkeypatch.setattr(da, "evaluate_deck", fake_evaluate)


def test_greedy_peels_disjoint_decks_best_first(monkeypatch):
    roster = roster_of({
        "a1": 1, "a2": 2, "a3": 3, "a4": 3, "a5": 3,
        "b1": 1, "b2": 2, "b3": 3, "b4": 3, "b5": 3,
    })
    # unambiguous optimum (no score ties): exactly the a-deck, then the b-deck
    def score(slugs):
        if slugs == {"a1", "a2", "a3", "a4", "a5"}:
            return 100.0
        if slugs == {"b1", "b2", "b3", "b4", "b5"}:
            return 50.0
        return 10.0

    patch_scorer(monkeypatch, score)
    out = da.allocate_decks(roster, BossProfile(), num_decks=5, time_budget_sec=0.0)
    assert len(out["decks"]) == 2                      # 10 units -> 2 decks
    assert sorted(out["decks"][0]["deck"]) == ["a1", "a2", "a3", "a4", "a5"]
    used = [slug for d in out["decks"] for slug in d["deck"]]
    assert len(used) == len(set(used))                 # disjoint
    assert out["leftover_slugs"] == []


def test_partial_roster_returns_fewer_decks(monkeypatch):
    roster = roster_of({"a1": 1, "a2": 2, "a3": 3, "a4": 3, "a5": 3, "x": 3})
    # decks containing x score lower, so the leftover is deterministically x
    patch_scorer(monkeypatch, lambda s: 0.5 if "x" in s else 1.0)
    out = da.allocate_decks(roster, BossProfile(), num_decks=5, time_budget_sec=0.0)
    assert len(out["decks"]) == 1                      # only one feasible deck
    assert out["leftover_slugs"] == ["x"]              # honest leftover report


def test_swap_pass_fixes_a_greedy_split(monkeypatch):
    # Two B2 buffers m/n; greedy stacks both winners into deck 1 context via
    # (1,2,2), but the optimum puts one per deck. Scores: a deck with exactly
    # one of {m,n} scores 100; with both, 120; with neither, 10. Greedy total
    # = 120 + 10 = 130; swapped total = 100 + 100 = 200.
    roster = roster_of({
        "m": 2, "n": 2, "a1": 1, "a3": 3, "a4": 3,
        "b1": 1, "b2": 2, "b3": 3, "b4": 3, "b5": 3,
    })

    def score(slugs):
        both = {"m", "n"} <= slugs
        one = bool({"m", "n"} & slugs) and not both
        return 120.0 if both else 100.0 if one else 10.0

    patch_scorer(monkeypatch, score)
    out = da.allocate_decks(roster, BossProfile(), num_decks=2, time_budget_sec=30.0)
    per_deck = [set(d["deck"]) & {"m", "n"} for d in out["decks"]]
    assert all(len(x) == 1 for x in per_deck)          # one buffer per deck
    assert sum(d["total_damage"] for d in out["decks"]) == 200.0


def test_allocate_decks_workers_parity():
    # Real 5-spec roster (stubs can't cross the SimPool process/module
    # boundary); time_budget_sec=0 keeps the wall-clock-capped swap phase out
    # of the comparison.
    from tests.test_deck_search import real_five_roster, short_boss

    roster, boss = real_five_roster(), short_boss()
    serial = da.allocate_decks(roster, boss, num_decks=2, time_budget_sec=0.0)
    pooled = da.allocate_decks(roster, boss, num_decks=2, time_budget_sec=0.0, workers=2)
    assert [d["deck"] for d in pooled["decks"]] == [d["deck"] for d in serial["decks"]]
    assert [d["total_damage"] for d in pooled["decks"]] == [d["total_damage"] for d in serial["decks"]]
    assert pooled["leftover_slugs"] == serial["leftover_slugs"]


from app.cascade import clear_fit_cache


def _wide_roster():
    """Big enough that search_best_decks blows its ordering budget."""
    tiers = {}
    for i in range(6):
        tiers[f"w1-{i}"] = 1
    for i in range(6):
        tiers[f"w2-{i}"] = 2
    for i in range(12):
        tiers[f"w3-{i}"] = 3
    return roster_of(tiers)


def test_allocation_fits_the_surrogate_once_for_the_whole_peel(monkeypatch):
    """One fit must serve every greedy-peel iteration - the additive model is
    what makes that valid, and refitting per iteration would erase the saving."""
    clear_fit_cache()
    patch_scorer(monkeypatch, lambda slugs: float(len(slugs)))
    # prune_candidate_pool ranks candidates by real base_stats/weapon_stats
    # (_prior), which this file's bare Unit(slug, burst_tier) fixture doesn't
    # carry (see test_deck_search.py's own note on the same limitation).
    # widened_pool's coefficient-ranked pass needs no such attributes, so an
    # empty prune result still lets the cascade produce a real shortlist.
    monkeypatch.setattr("app.cascade.prune_candidate_pool", lambda r, b, p=None: [])
    fits = {"n": 0}
    real_fit = da.cached_fit_surrogate

    def counting_fit(roster, boss, score_orderings):
        fits["n"] += 1
        return real_fit(roster, boss, score_orderings)

    monkeypatch.setattr(da, "cached_fit_surrogate", counting_fit)

    da.allocate_decks(_wide_roster(), BossProfile(), num_decks=3,
                      time_budget_sec=0.0)

    assert fits["n"] == 1


def test_small_rosters_never_fit_a_surrogate(monkeypatch):
    """Existing tests use tiny rosters and stub evaluate_deck; they must keep
    taking the untouched exhaustive path."""
    clear_fit_cache()
    patch_scorer(monkeypatch, lambda slugs: float(len(slugs)))
    fits = {"n": 0}
    monkeypatch.setattr(da, "cached_fit_surrogate",
                        lambda *a, **k: fits.__setitem__("n", fits["n"] + 1))

    da.allocate_decks(roster_of({"a1": 1, "a2": 2, "a3": 3, "a4": 3, "a5": 3}),
                      BossProfile(), num_decks=1, time_budget_sec=0.0)

    assert fits["n"] == 0


from app.cascade import Cascade, fit_surrogate
from app.deck_search import _score_batch, search_best_decks

# Per-unit values plus a synergy the unit-only surrogate cannot represent, so
# the test probes the cascade's actual failure mode rather than a model it fits
# perfectly.
_UNIT_VALUE = {f"q3-{i}": 100.0 + 10 * i for i in range(10)}
_UNIT_VALUE.update({f"q2-{i}": 50.0 + 5 * i for i in range(5)})
_UNIT_VALUE.update({f"q1-{i}": 30.0 + 3 * i for i in range(5)})
_SYNERGY = frozenset({"q1-0", "q3-9"})


def _quality_scorer(slugs):
    total = sum(_UNIT_VALUE.get(s, 0.0) for s in slugs)
    return total + (100.0 if _SYNERGY <= set(slugs) else 0.0)


def _quality_roster():
    tiers = {f"q1-{i}": 1 for i in range(5)}
    tiers.update({f"q2-{i}": 2 for i in range(5)})
    tiers.update({f"q3-{i}": 3 for i in range(10)})
    return roster_of(tiers)


def test_cascade_search_stays_within_five_percent_of_exhaustive(monkeypatch):
    """The cascade must not cost real damage. 95% is the same bar the recall
    gate held K to, so the test and the gate cannot drift apart."""
    patch_scorer(monkeypatch, _quality_scorer)
    # prune_candidate_pool ranks on base_stats/weapon_stats (_prior), which this
    # file's bare Unit(slug, burst_tier) fixture doesn't carry (same gap noted
    # on test_allocation_fits_the_surrogate_once_for_the_whole_peel above).
    # Bypass it on both call paths: the exhaustive call sees the unpruned
    # roster (a stronger baseline than production's pruned-exhaustive, never a
    # weaker one), and the cascade call falls entirely to widened_pool's
    # coefficient-ranked pass - the exact mechanism this test probes.
    monkeypatch.setattr("app.deck_search.prune_candidate_pool", lambda r, b, p=None: list(r))
    monkeypatch.setattr("app.cascade.prune_candidate_pool", lambda r, b, p=None: [])
    roster, boss = _quality_roster(), BossProfile()

    exhaustive = search_best_decks(roster, boss, top_n=1)
    model = fit_surrogate(roster, boss,
                          lambda decks: _score_batch(decks, boss, None),
                          samples=150)
    assert model is not None, "roster too small to fit - widen _quality_roster"
    cascaded = search_best_decks(roster, boss, top_n=1, sim_budget=1,
                                 cascade=Cascade(model))

    assert cascaded[0]["total_damage"] >= 0.95 * exhaustive[0]["total_damage"]
