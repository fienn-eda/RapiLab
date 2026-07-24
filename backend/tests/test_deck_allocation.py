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
    # prune_candidate_pool's _prior heuristic reads these (unit.base_stats["atk"]
    # * unit.weapon_stats["damage_percent"]) to seed its reference deck. Most of
    # this file's tests stub prune_candidate_pool away and never touch these, so
    # a uniform default keeps roster_of's bare-unit fixture working unchanged;
    # only the units that let prune run for real need them to differ.
    base_stats: dict = None
    weapon_stats: dict = None

    def __post_init__(self):
        if self.base_stats is None:
            object.__setattr__(self, "base_stats", {"atk": 1000.0})
        if self.weapon_stats is None:
            object.__setattr__(self, "weapon_stats", {"damage_percent": 1.0})


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


def test_complete_draft_never_fits_a_surrogate(monkeypatch):
    """A draft that already supplies every requested deck never reaches the
    greedy-peel loop, so the (would-be ~940-simulation) fit must never run -
    fitting here would score nothing, since no search ever consults it."""
    clear_fit_cache()
    patch_scorer(monkeypatch, lambda slugs: float(len(slugs)))
    fits = {"n": 0}
    monkeypatch.setattr(da, "cached_fit_surrogate",
                        lambda *a, **k: fits.__setitem__("n", fits["n"] + 1))

    roster = _wide_roster()  # big enough to blow the search budget if reached
    by_slug = {u.slug: u for u in roster}
    draft = [
        [by_slug["w1-0"], by_slug["w2-0"], by_slug["w3-0"], by_slug["w3-1"], by_slug["w3-2"]],
        [by_slug["w1-1"], by_slug["w2-1"], by_slug["w3-3"], by_slug["w3-4"], by_slug["w3-5"]],
        [by_slug["w1-2"], by_slug["w2-2"], by_slug["w3-6"], by_slug["w3-7"], by_slug["w3-8"]],
    ]

    out = da.allocate_decks(roster, BossProfile(), num_decks=3, draft=draft,
                            time_budget_sec=0.0)

    assert len(out["decks"]) == 3
    assert fits["n"] == 0


from app.cascade import Cascade, fit_surrogate
from app.deck_search import _score_batch, prune_candidate_pool, search_best_decks

# Per-unit values plus a synergy the unit-only surrogate cannot represent, so
# the test probes the cascade's actual failure mode rather than a model it fits
# perfectly. A single fixed-partner bonus ("q1-0 + q3-9 is good") is *not*
# such a synergy: it's representable by an additive model, since q1-0 always
# co-occurs with the bonus and ridge just folds it into q1-0's coefficient.
# Using a cancelling pair on the same unit - q1-0 good with q3-9, bad with
# q3-8 - denies the model that escape hatch: q1-0 appears in both high- and
# low-damage decks in roughly equal measure, so no per-unit coefficient can
# encode which partner it actually needs.
_UNIT_VALUE = {f"q3-{i}": 100.0 + 10 * i for i in range(10)}
_UNIT_VALUE.update({f"q2-{i}": 50.0 + 5 * i for i in range(5)})
_UNIT_VALUE.update({f"q1-{i}": 30.0 + 3 * i for i in range(5)})
_SYNERGY_BONUS = frozenset({"q1-0", "q3-9"})
_SYNERGY_PENALTY = frozenset({"q1-0", "q3-8"})


def _quality_scorer(slugs):
    total = sum(_UNIT_VALUE.get(s, 0.0) for s in slugs)
    if _SYNERGY_BONUS <= set(slugs):
        total += 100.0
    if _SYNERGY_PENALTY <= set(slugs):
        total -= 100.0
    return total


# _reference_deck seeds its 3 tier-3 slots from by_tier[3], which
# prune_candidate_pool sorts by _prior (base_stats["atk"] * damage_percent),
# highest first, then takes the top 3 (_variant_safe_top). q3-9 is placed
# highest so it always seeds that reference deck; q3-8 is placed LOWEST so it
# never does. That is what makes prune's marginal-contribution measurement
# for q1-0 see the bare +100 synergy bonus (q1-0 swapped in against a
# reference that already contains q3-9) rather than the cancelling -100
# penalty (which only fires when q3-8 is the one seated) - without this
# ordering, prune could measure the wrong sign and this fixture would no
# longer demonstrate that prune rescues q1-0 from the coefficient-ranked cut.
# The other tier-3 ATKs, and every tier-1/tier-2 ATK, only need to be
# distinct within their own tier (prune_candidate_pool ranks per-tier): a tie
# would make sorted()'s stability fall back to dict-literal insertion order -
# an accident, not a real prior - so each tier below is numbered explicitly.
_TIER3_ATK = {
    "q3-9": 5000.0,  # highest: guarantees a reference-deck seat
    "q3-7": 4800.0,
    "q3-6": 4600.0,
    "q3-5": 4400.0,
    "q3-4": 4200.0,
    "q3-3": 4000.0,
    "q3-2": 3800.0,
    "q3-1": 3600.0,
    "q3-0": 3400.0,
    "q3-8": 3200.0,  # lowest: guarantees NOT a reference-deck seat
}
_TIER1_ATK = {f"q1-{i}": 1000.0 + 50.0 * i for i in range(5)}
_TIER2_ATK = {f"q2-{i}": 2000.0 + 50.0 * i for i in range(5)}


def _quality_roster():
    """5 tier-1 / 5 tier-2 / 10 tier-3 units, carrying the base_stats ATK that
    prune_candidate_pool ranks by (see _TIER1_ATK / _TIER2_ATK / _TIER3_ATK
    above, where the seating this fixture depends on is spelled out)."""
    tiers = {f"q1-{i}": 1 for i in range(5)}
    tiers.update({f"q2-{i}": 2 for i in range(5)})
    tiers.update({f"q3-{i}": 3 for i in range(10)})
    atk_by_slug = {**_TIER1_ATK, **_TIER2_ATK, **_TIER3_ATK}
    roster = []
    for slug, tier in tiers.items():
        roster.append(Unit(slug, tier, base_stats={"atk": atk_by_slug[slug]},
                           weapon_stats={"damage_percent": 1.0}))
    return roster


def _cascade_vs_exhaustive_ratio(monkeypatch, real_prune_on_cascade):
    """Shared setup for the two safety-net tests below: fit a surrogate blind
    to the cancelling synergy, then compare the cascade's best deck against
    the true exhaustive optimum on the same roster and scorer."""
    patch_scorer(monkeypatch, _quality_scorer)
    roster, boss = _quality_roster(), BossProfile()

    if real_prune_on_cascade:
        # Guard the fixture's premise before trusting the ratio assertion
        # below: run the real, unpatched prune_candidate_pool (against the
        # scorer just patched in above) and check q1-0 actually survives its
        # PRUNED_TIER_CAPS[1] = 2 cut. If _quality_roster's tier-3 ATK
        # ordering, PRUNED_TIER_CAPS, or prune_candidate_pool itself ever
        # changes so that premise no longer holds, this fails with that exact
        # cause instead of surfacing only as a bare ratio mismatch below.
        pruned_pool = prune_candidate_pool(roster, boss)
        assert "q1-0" in {u.slug for u in pruned_pool}, (
            "fixture premise broken: prune_candidate_pool no longer keeps "
            "q1-0 in its pool - check _quality_roster's tier-3 ATK ordering "
            "(q3-9 must seed the reference deck, q3-8 must not)"
        )

    # The "exhaustive" call must see the true, unpruned optimum: production's
    # pruned-exhaustive fallback is a WEAKER baseline than the true unpruned
    # optimum this test needs, and pruning it here would let a cut ground
    # truth hide a real cascade regression. This bypass is unconditional in
    # both directions.
    monkeypatch.setattr("app.deck_search.prune_candidate_pool", lambda r, b, p=None: list(r))
    if not real_prune_on_cascade:
        # The historical shape of this test: the cascade's safety net
        # (widened_pool seating prune_candidate_pool's picks first) is
        # disabled, leaving only the coefficient-ranked pass.
        monkeypatch.setattr("app.cascade.prune_candidate_pool", lambda r, b, p=None: [])

    exhaustive = search_best_decks(roster, boss, top_n=1)
    model = fit_surrogate(roster, boss,
                          lambda decks: _score_batch(decks, boss, None),
                          samples=150)
    assert model is not None, "roster too small to fit - widen _quality_roster"
    cascaded = search_best_decks(roster, boss, top_n=1, sim_budget=1,
                                 cascade=Cascade(model))

    return cascaded[0]["total_damage"] / exhaustive[0]["total_damage"]


def test_cascade_with_prune_safety_net_stays_within_five_percent_of_exhaustive(monkeypatch):
    """The fitted surrogate cannot represent the cancelling q1-0/q3-9/q3-8
    synergy (see _quality_scorer), so widened_pool's coefficient-ranked pass
    alone would drop q1-0 - it is tier 1's cheapest unit by design, and the
    tier-1 cap (4 of 5) cuts exactly the cheapest. prune_candidate_pool is the
    production safety net for this: it measures marginal contribution by
    actually simulating decks, so it can see the synergy the surrogate can't.
    95% is the same bar the recall gate held K to, so the test and the gate
    cannot drift apart."""
    ratio = _cascade_vs_exhaustive_ratio(monkeypatch, real_prune_on_cascade=True)
    assert ratio >= 0.95


def test_cascade_without_prune_safety_net_falls_short_of_five_percent(monkeypatch):
    """Documents that the safety net above is load-bearing, not decorative:
    with prune_candidate_pool stubbed out of the cascade path (the historical
    shape of this test), widened_pool falls entirely to the coefficient-ranked
    pass, which cannot see the cancelling synergy and drops q1-0 - so the
    cascade misses the true optimum and falls short of the 95% floor."""
    ratio = _cascade_vs_exhaustive_ratio(monkeypatch, real_prune_on_cascade=False)
    assert ratio < 0.95
