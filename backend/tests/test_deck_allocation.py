"""Allocation layer: greedy peeling picks disjoint decks best-first; the
same-tier swap pass recovers the classic greedy mistake (stacking two strong
supporters in deck 1 when splitting them wins). All search/sim calls are
stubbed - real sims live in the API end-to-end test."""
from dataclasses import dataclass
import inspect

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
    # Only the seat-order tie-break reads this, and only to ask the registry for
    # a burst_delay - a fake slug has no builder, and Diesel's ignores its
    # argument - so an empty dict serves every fixture here.
    skill_values: dict = None

    def __post_init__(self):
        if self.base_stats is None:
            object.__setattr__(self, "base_stats", {"atk": 1000.0})
        if self.weapon_stats is None:
            object.__setattr__(self, "weapon_stats", {"damage_percent": 1.0})
        if self.skill_values is None:
            object.__setattr__(self, "skill_values", {})


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
    out = da.allocate_decks(roster, BossProfile(), num_decks=5, swap_budget=0)
    assert len(out["decks"]) == 2                      # 10 units -> 2 decks
    assert sorted(out["decks"][0]["deck"]) == ["a1", "a2", "a3", "a4", "a5"]
    used = [slug for d in out["decks"] for slug in d["deck"]]
    assert len(used) == len(set(used))                 # disjoint
    assert out["leftover_slugs"] == []


def test_partial_roster_returns_fewer_decks(monkeypatch):
    roster = roster_of({"a1": 1, "a2": 2, "a3": 3, "a4": 3, "a5": 3, "x": 3})
    # decks containing x score lower, so the leftover is deterministically x
    patch_scorer(monkeypatch, lambda s: 0.5 if "x" in s else 1.0)
    out = da.allocate_decks(roster, BossProfile(), num_decks=5, swap_budget=0)
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
    out = da.allocate_decks(roster, BossProfile(), num_decks=2, swap_budget=10_000)
    per_deck = [set(d["deck"]) & {"m", "n"} for d in out["decks"]]
    assert all(len(x) == 1 for x in per_deck)          # one buffer per deck
    assert sum(d["total_damage"] for d in out["decks"]) == 200.0


def _swap_fixture():
    """One deck plus a two-unit bench, where both bench units improve the deck
    but only the better one should end up seated."""
    deck = roster_of({"x1": 1, "x2": 2, "x3": 3, "x4": 3, "x5": 3})
    return deck, [Unit("y", 3), Unit("z", 3)]


def _bench_scorer(slugs):
    # y is worth more than z, and z beats the deck it would replace x3 in - so
    # z improves on the ORIGINAL deck but not on the one y produces.
    if "y" in slugs:
        return 120.0
    if "z" in slugs:
        return 110.0
    return 100.0


def test_an_accepted_swap_invalidates_the_rest_of_its_batch(monkeypatch):
    """Candidates are scored a batch ahead of the walk that judges them, so an
    accepted swap leaves the rest of that batch scored against a deck that no
    longer exists. Here z improves on the original deck (110 > 100) but not on
    the one y just produced (110 < 120): trusting the stale score would seat
    the worse unit."""
    deck, bench = _swap_fixture()
    patch_scorer(monkeypatch, _bench_scorer)

    da._swap_pass([deck], bench, BossProfile(),
                  10_000, batch=8)

    assert {u.slug for u in deck} == {"x1", "x2", "y", "x4", "x5"}
    assert sorted(u.slug for u in bench) == ["x3", "z"]


def test_batch_width_never_changes_the_outcome(monkeypatch):
    """Batching decides only how many candidates are scored at once; the accept
    rule and the candidate order stay the serial ones. batch=1 IS the old
    one-at-a-time walk, so it must agree with a batch wide enough to span every
    candidate at once."""
    outcomes = []
    for batch in (1, 2, 3, 64):
        deck, bench = _swap_fixture()
        patch_scorer(monkeypatch, _bench_scorer)
        da._swap_pass([deck], bench, BossProfile(),
                      10_000, batch=batch)
        outcomes.append(([u.slug for u in deck], [u.slug for u in bench]))

    assert len(set(map(str, outcomes))) == 1, outcomes


def test_a_tie_seats_an_opening_skipper_behind_her_tier_mate(monkeypatch):
    """`burst_cycle` fires the leftmost READY member of a tier, and so does the
    game. A `skip_cycles` delay makes a unit unready for the opening cycles -
    which the SEAT cannot express, so both orders score identically here while
    only one of them can be fielded literally.

    Fienn, 2026-08-04: deck 4 came back with 디젤: 윈터 스위츠(후버) LEFT of her
    tier-mate. Played as shown, the game bursts her into the opening Full Burst
    and locks Intro - the state her Highlight build is scored as NOT having. The
    two orderings were tied to the digit (4,195,637,343), so preferring the
    playable one costs nothing.
    """
    units = [Unit("a1", 1), Unit("b1", 2), Unit("b2", 2),
             Unit("diesel-winter-sweets-highlight", 3), Unit("mate", 3)]
    patch_scorer(monkeypatch, lambda slugs: 100.0)      # every ordering ties

    summary = da.best_ordering_summary(units, BossProfile())

    tier3 = [s for s in summary["deck"]
             if next(u for u in units if u.slug == s).burst_tier == 3]
    assert tier3 == ["mate", "diesel-winter-sweets-highlight"]


def test_a_zero_budget_leaves_the_decks_untouched(monkeypatch):
    """allocate_decks relies on this to return a valid (if unimproved)
    allocation when the swap phase is given nothing to spend."""
    deck, bench = _swap_fixture()
    before = [u.slug for u in deck]
    patch_scorer(monkeypatch, _bench_scorer)

    da._swap_pass([deck], bench, BossProfile(), 0)

    assert [u.slug for u in deck] == before


def test_the_swap_budget_default_is_the_named_constant():
    """The climb's ceiling is a MEASURED number, and the measurement that chose
    it is written beside the constant. Every test in this file passes an
    explicit budget, so nothing else here would notice the default drifting back
    to a bare literal - and a literal in the signature is exactly how the number
    and the note justifying it come apart."""
    default = inspect.signature(da.allocate_decks).parameters["swap_budget"].default
    assert default is da.SWAP_CANDIDATE_BUDGET


def test_the_climb_never_swaps_a_taste_variant_into_a_deck_that_cannot_induce_it(monkeypatch):
    """A same-tier swap skips `deck_is_valid` - it cannot change the deck's
    shape, so the check was pure cost. But a Taste variant's rule is about
    MEMBERSHIP, not shape: Bready needs a deck-mate whose buff puts her in the
    state her whole kit is gated on.

    Measured on Fienn's roster (2026-08-04): fixing only the three generators
    left the climb free to walk her straight back into a deck holding no
    sustained-damage buffer, and it did."""
    deck = roster_of({"x1": 1, "x2": 2, "x3": 3, "x4": 3, "x5": 3})
    bench = [Unit("bready-lingering", 3)]
    patch_scorer(monkeypatch,
                 lambda slugs: 500.0 if "bready-lingering" in slugs else 100.0)

    da._swap_pass([deck], bench, BossProfile(), 10_000, batch=8)

    assert [u.slug for u in deck] == ["x1", "x2", "x3", "x4", "x5"]
    assert [u.slug for u in bench] == ["bready-lingering"]


def test_a_binding_budget_still_reaches_the_last_deck(monkeypatch):
    """The climb walks deck 1's partners, then deck 2's, and so on, and each
    work item may spend everything that is left. A budget that binds was
    therefore spent ENTIRELY on the first deck, and the decks after it got no
    swap at all - not a worse swap, none.

    Fienn hit this on 2026-08-04: a 5-deck run left a bench unit worth
    +969,725,138 unseated beside deck 3, because the budget was gone before
    deck 3 was ever looked at. Here `w` is worth double to the LAST deck and
    worthless anywhere else, so it can only be found by an item the old walk
    never reached.
    """
    decks = [[Unit(f"{p}1", 3), Unit(f"{p}2", 1), Unit(f"{p}3", 2),
              Unit(f"{p}4", 3), Unit(f"{p}5", 3)] for p in "abc"]
    # `w` first, so it is the first candidate the last deck's bench pass judges
    # once that pass gets any budget at all.
    bench = [Unit("w", 3)] + [Unit(f"f{i}", 3) for i in range(11)]

    def score(slugs):
        if "w" in slugs:
            # Only the last deck wants her; everywhere else she is a downgrade,
            # so no earlier item can seat her and end the test by accident.
            return 200.0 if any(s.startswith("c") for s in slugs) else 10.0
        if any(s.startswith("f") for s in slugs):
            return 10.0
        return 100.0

    patch_scorer(monkeypatch, score)
    # Six work items ((0,1) (0,2) (0,bench) (1,2) (1,bench) (2,bench)), so a
    # budget of 60 gives each of them ten candidates - enough for the last one
    # to reach `w`, who is the first bench unit it judges. Spending it all on
    # the first item, the way an unfair split does, never gets there.
    converged = da._swap_pass(decks, bench, BossProfile(), 60)

    assert not converged, (
        "the budget never bound, so this fixture proves nothing about a climb "
        "that is cut off")
    assert "w" in [u.slug for u in decks[2]], (
        "the last deck never got a swap - the budget was spent before its turn")


# One owned character, several candidate slugs (registry's MODE_VARIANTS). The
# real slugs are used rather than a stubbed mapping, since the mapping IS what
# these tests check, so the pair has to be one that carries NO extra seating
# rule of its own - otherwise these tests stop isolating the character rule and
# start failing for someone else's reason. Cinderella: Crystal Wave's two firing
# modes are that pair today. Bready's was, until her Taste variants gained
# TASTE_INDUCER_SLUGS; rapi-red-hood-b1 never was (SOLE_TIER1_SLUGS).
MODE_A, MODE_B = "cinderella-crystal-wave-mg", "cinderella-crystal-wave-snipe"


def test_peeling_never_spends_one_character_on_two_decks(monkeypatch):
    """The decks are fielded simultaneously, so two MODE_VARIANTS candidates of
    one base cannot each hold a seat - the player owns one Bready. Slug-keyed
    peeling used to allow it: here the a-deck wants her Lingering candidate and
    the b-deck her Recommended one, and both scored best-in-pool at the time
    they were picked."""
    roster = roster_of({
        "a1": 1, "a2": 2, "a3": 3, "a4": 3,
        "b1": 1, "b2": 2, "b3": 3, "b4": 3, "b5": 3,
        MODE_A: 3, MODE_B: 3,
    })

    def score(slugs):
        if slugs == {"a1", "a2", "a3", "a4", MODE_A}:
            return 100.0
        if slugs == {"b1", "b2", "b3", "b4", MODE_B}:
            return 90.0
        return 10.0

    patch_scorer(monkeypatch, score)
    out = da.allocate_decks(roster, BossProfile(), num_decks=2, swap_budget=0)

    seated = [slug for d in out["decks"] for slug in d["deck"]]
    assert MODE_A in seated                       # the 100-point deck still wins
    assert MODE_B not in seated
    # ...and her other candidate is not a benched unit either: Bready IS fielded,
    # so listing her among the leftovers would offer the player a unit she has
    # already committed.
    assert MODE_B not in out["leftover_slugs"]


def test_peeling_never_spends_a_favorite_item_character_on_two_decks(monkeypatch):
    """A Favorite Item build and its base are the same owned unit, so the five
    raid decks - fielded simultaneously - can seat her only once. A roster
    holding both encodings (a hand-edited roster.json) must not buy two seats."""
    roster = roster_of({
        "a1": 1, "a2": 2, "a3": 3, "a4": 3,
        "b1": 1, "b2": 2, "b3": 3, "b4": 3, "b5": 3,
        "miranda": 3, "miranda-signature": 3,
    })

    def score(slugs):
        if slugs == {"a1", "a2", "a3", "a4", "miranda"}:
            return 100.0
        if slugs == {"b1", "b2", "b3", "b4", "miranda-signature"}:
            return 90.0
        return 10.0

    patch_scorer(monkeypatch, score)
    out = da.allocate_decks(roster, BossProfile(), num_decks=2, swap_budget=0)

    seated = [slug for d in out["decks"] for slug in d["deck"]]
    assert "miranda" in seated                       # the 100-point deck still wins
    assert "miranda-signature" not in seated
    # She is fielded, so her other build is not a benched unit either.
    assert "miranda-signature" not in out["leftover_slugs"]


def test_a_bench_swap_never_seats_a_character_already_holding_a_seat(monkeypatch):
    """The peel leaves a character entirely benched when neither candidate makes
    a deck; the hill-climb can then pull one into each deck one bench swap at a
    time. Deck 2 would gain 50 by seating the Recommended candidate, and takes it
    only if the rule is not enforced per swap as well as per peel."""
    deck_a = roster_of({"x1": 1, "x2": 2, "x3": 3, "x4": 3, "x5": 3})
    deck_b = roster_of({"w1": 1, "w2": 2, "w3": 3, "w4": 3, "w5": 3})
    bench = [Unit(MODE_A, 3), Unit(MODE_B, 3)]

    def score(slugs):
        if MODE_A in slugs:
            return 200.0
        if MODE_B in slugs:
            return 150.0
        return 100.0

    patch_scorer(monkeypatch, score)
    da._swap_pass([deck_a, deck_b], bench, BossProfile(),
                  10_000, batch=8)

    seated = [u.slug for u in deck_a] + [u.slug for u in deck_b]
    assert MODE_A in seated                       # deck 1 takes the better one
    assert MODE_B not in seated
    assert MODE_B in [u.slug for u in bench]


def test_a_bench_swap_may_change_the_decks_burst_tier_shape(monkeypatch):
    """(1,1,3) and (2,1,2) are both shapes real play uses, so the unit that wins
    a seat is often not the tier of the one it displaces - a Burst-1 cooldown
    holder earns her place by taking a Burst 3's chair, not another Burst 1's.
    Restricting the climb to same-tier exchanges puts every such move outside
    the search: here y is worth double, and no same-tier swap reaches her."""
    deck = roster_of({"x1": 1, "x2": 2, "x3": 3, "x4": 3, "x5": 3})
    bench = [Unit("y", 1)]

    def score(slugs):
        # y pays off as an ADDITIONAL Burst 1, so displacing the deck's existing
        # one - the only same-tier swap available - is a loss, not a gain.
        if "y" not in slugs:
            return 100.0
        return 200.0 if "x1" in slugs else 90.0

    patch_scorer(monkeypatch, score)
    da._swap_pass([deck], bench, BossProfile(), 10_000, batch=8)

    assert "y" in [u.slug for u in deck]
    assert sorted(u.burst_tier for u in deck) == [1, 1, 2, 3, 3]


def test_a_cross_tier_swap_that_leaves_an_unfieldable_shape_is_refused(monkeypatch):
    """A same-tier exchange cannot change a deck's B1/B2/B3 shape, which is why
    the climb never had to ask whether its result was legal. A cross-tier one
    can, and (2,0,3) - a deck with no Burst 2 - can never reach Full Burst. The
    only improving swap here produces exactly that, so the deck must stand."""
    deck = roster_of({"x1": 1, "x2": 2, "x3": 3, "x4": 3, "x5": 3})
    before = [u.slug for u in deck]
    bench = [Unit("y", 1)]

    # 200 only in the seat that leaves the deck without a Burst 2; every legal
    # landing spot for y costs one of x3/x4/x5 and is worth no more than staying.
    patch_scorer(monkeypatch,
                 lambda slugs: 200.0 if {"y", "x1", "x3", "x4", "x5"} <= slugs
                 else 100.0)
    da._swap_pass([deck], bench, BossProfile(), 10_000, batch=8)

    assert [u.slug for u in deck] == before
    assert [u.slug for u in bench] == ["y"]


def test_an_accepted_cross_tier_swap_re_judges_the_candidates_behind_it(monkeypatch):
    """Legality is decided when the candidate list is built, but a cross-tier
    swap changes the shape it was decided against. Here y and z are both Burst
    1s worth having: seating y takes the deck from (1,1,3) to (2,1,2), which
    leaves z's own candidate - legal when the list was built - pointing at a
    third Burst 1 and a (3,1,1) deck the game cannot field."""
    deck = roster_of({"x1": 1, "x2": 2, "x3": 3, "x4": 3, "x5": 3})
    bench = [Unit("y", 1), Unit("z", 1)]

    def score(slugs):
        # Both pay off as ADDITIONAL Burst 1s, so the more of them the better -
        # nothing but the shape rule stands between the deck and seating both.
        if "x1" not in slugs:
            return 90.0
        return 100.0 + 50.0 * len({"y", "z"} & slugs)

    patch_scorer(monkeypatch, score)
    da._swap_pass([deck], bench, BossProfile(), 10_000, batch=8)

    assert sorted(u.burst_tier for u in deck) == [1, 1, 2, 3, 3]
    assert len({"y", "z"} & {u.slug for u in deck}) == 1


def test_a_drafted_character_is_seated_in_the_mode_that_scores_best(monkeypatch):
    """A drafted seat can name a character the engine models in several modes;
    which one she runs in is the ENGINE's call. The seat arrives as one
    representative candidate plus `alternatives`, and the deck is completed each
    way - so the representative loses when the other mode is worth more."""
    by_slug = {u.slug: u for u in roster_of({
        "a1": 1, "a2": 2, "a3": 3, "a4": 3,
        MODE_A: 3, MODE_B: 3,
    })}
    seed = [by_slug[s] for s in ("a1", "a2", "a3", "a4", MODE_A)]

    def score(slugs):
        return 200.0 if MODE_B in slugs else 100.0

    patch_scorer(monkeypatch, score)
    out = da.allocate_decks(
        list(by_slug.values()), BossProfile(), num_decks=1, draft=[seed],
        alternatives={MODE_A: (by_slug[MODE_A], by_slug[MODE_B])},
        swap_budget=0)

    seated = out["decks"][0]["deck"]
    assert MODE_B in seated                     # the better mode won
    assert MODE_A not in seated                   # ...and only one mode is seated
    assert out["decks"][0]["total_damage"] == 200.0


def test_a_lock_on_a_drafted_character_holds_whichever_mode_was_chosen(monkeypatch):
    """The player locks the slug they own (`cinderella-crystal-wave`); the seat
    ends up holding a candidate slug (`-snipe`). Comparing locks by slug would
    silently unpin her."""
    # A (1,2,2) deck - a shape real play uses, so every seat is a swap the climb
    # may legally make - and a bench unit worth having in exactly one of them:
    # the locked one. The lock is the single thing standing between them.
    deck = roster_of({"x1": 1, "x2": 2, "x5": 2, MODE_B: 3, "x4": 3})
    bench = [Unit("y", 3)]

    def score(slugs):
        return 500.0 if "y" in slugs and MODE_B not in slugs else 100.0

    patch_scorer(monkeypatch, score)
    da._swap_pass([deck], bench, BossProfile(), 10_000,
                  locked=frozenset({"cinderella-crystal-wave"}), batch=8)

    assert MODE_B in [u.slug for u in deck]      # the lock held
    assert [u.slug for u in bench] == ["y"]


def test_a_draft_spending_one_character_twice_is_infeasible(monkeypatch):
    """A player CAN drag both candidates onto different decks - both are listed
    by /api/supported-units - so the request has to be rejected rather than
    silently answered with a formation the game cannot field."""
    import pytest

    by_slug = {u.slug: u for u in roster_of({
        "a1": 1, "a2": 2, "a3": 3, "a4": 3,
        "b1": 1, "b2": 2, "b3": 3, "b4": 3,
        MODE_A: 3, MODE_B: 3,
    })}
    draft = [[by_slug[s] for s in ("a1", "a2", "a3", "a4", MODE_A)],
             [by_slug[s] for s in ("b1", "b2", "b3", "b4", MODE_B)]]

    with pytest.raises(da.InfeasibleDraft, match="cinderella-crystal-wave"):
        da.allocate_decks(list(by_slug.values()), BossProfile(), num_decks=2,
                          draft=draft, swap_budget=0)


def test_allocate_decks_workers_parity():
    # Real 5-spec roster (stubs can't cross the SimPool process/module
    # boundary); swap_budget=0 keeps this comparison on the peel alone. The
    # climb's own worker-parity is asserted under a BINDING budget by
    # test_a_binding_budget_agrees_across_worker_counts.
    from tests.test_deck_search import real_five_roster, short_boss

    roster, boss = real_five_roster(), short_boss()
    serial = da.allocate_decks(roster, boss, num_decks=2, swap_budget=0)
    pooled = da.allocate_decks(roster, boss, num_decks=2, swap_budget=0, workers=2)
    assert [d["deck"] for d in pooled["decks"]] == [d["deck"] for d in serial["decks"]]
    assert [d["total_damage"] for d in pooled["decks"]] == [d["total_damage"] for d in serial["decks"]]
    assert pooled["leftover_slugs"] == serial["leftover_slugs"]


def test_a_cut_off_climb_returns_the_same_allocation_twice(monkeypatch):
    """Same input, same answer - the whole point. Asserted where it used to
    fail: a budget that binds, so the run is decided by where the climb stopped
    rather than by where it converged."""
    def run():
        decks = [[Unit(f"{p}1", 3), Unit(f"{p}2", 1), Unit(f"{p}3", 2),
                  Unit(f"{p}4", 3), Unit(f"{p}5", 3)] for p in "abc"]
        bench = [Unit(f"f{i}", 3) for i in range(11)]
        patch_scorer(monkeypatch, lambda slugs: 100.0 + len(
            [s for s in slugs if s.startswith("f")]) * 5.0)
        converged = da._swap_pass(decks, bench, BossProfile(), 40)
        return converged, [[u.slug for u in deck] for deck in decks]

    first, second = run(), run()

    assert first[0] is False, "the budget never bound - nothing is being proven"
    assert first == second


def test_an_item_spends_no_more_than_its_share(monkeypatch):
    """The equal split is what keeps a binding budget from being eaten by deck
    1, so `used` has to respect it exactly - the batch is truncated for this
    reason and nothing else asserts the truncation directly.

    The deck is (1,2,3,3,3) and every bench unit a Burst 3, so only the three
    Burst-3 seats yield admissible candidates: 3 x 20 = 60, far more than the
    share of 7 can reach."""
    decks = [roster_of({"x1": 1, "x2": 2, "x3": 3, "x4": 3, "x5": 3})]
    bench = [Unit(f"b{i}", 3) for i in range(20)]
    scores = [100.0]

    calls = []

    def fake_score_batch(trials, boss, pool):
        calls.append(len(trials))
        return [1.0] * len(trials)

    monkeypatch.setattr(da, "_score_batch", fake_score_batch)
    improved, used, exhausted = da._try_swaps(
        decks, scores, 0, bench, None, BossProfile(), 7,
        frozenset(), None, 4)

    assert improved is False          # every trial scores 1.0, below the 100 baseline
    assert used == 7                  # exactly the share, never over
    assert exhausted is False         # 5 x 20 candidates, so 7 cannot finish them
    assert calls == [4, 3]            # the second batch is truncated to what is left


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
                      swap_budget=0)

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
                      BossProfile(), num_decks=1, swap_budget=0)

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
                            swap_budget=0)

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
