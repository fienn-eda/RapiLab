from dataclasses import dataclass

import pytest

from app.deck_search import BossProfile, feasible_orderings, find_best_decks
from tests.test_roster import anis_star_spec, crown_spec, helm_spec


@dataclass
class FakeUnit:
    slug: str
    burst_tier: int


def fake_roster(tiers):
    return [FakeUnit(f"u{i}", t) for i, t in enumerate(tiers)]


def test_feasible_orderings_requires_one_of_each_burst_tier():
    # 3x burst1, no burst2/3 -> no feasible deck
    assert list(feasible_orderings(fake_roster([1, 1, 1, 1, 1]))) == []


def test_feasible_orderings_yields_the_standard_composition():
    roster = fake_roster([1, 2, 3, 3, 3])  # exactly one feasible combo
    decks = list(feasible_orderings(roster))
    # only the 3 burst-3 units permute (3! = 6); tiers 1 and 2 have one each
    assert len(decks) == 6
    for deck in decks:
        tiers = [u.burst_tier for u in deck]
        assert tiers == [1, 2, 3, 3, 3]  # canonical tier order


def test_feasible_orderings_picks_5_from_a_larger_pool():
    # 2x b1, 2x b2, 3x b3 = 7 units. Every feasible deck still has all 3 tiers.
    roster = fake_roster([1, 1, 2, 2, 3, 3, 3])
    decks = list(feasible_orderings(roster))
    assert len(decks) > 0
    for deck in decks:
        present = {u.burst_tier for u in deck}
        assert {1, 2, 3} <= present
        assert len(deck) == 5


def test_feasible_orderings_intra_tier_order_varies():
    roster = fake_roster([1, 2, 3, 3, 3])
    decks = list(feasible_orderings(roster))
    tier3_orders = {tuple(u.slug for u in deck if u.burst_tier == 3) for deck in decks}
    assert len(tier3_orders) == 6  # all permutations of the three burst-3 units


def test_mode_variants_never_share_a_deck(monkeypatch):
    from app import deck_search
    monkeypatch.setattr(deck_search, "_CHARACTER_OF",
                        {"unit-a-mg": "unit-a", "unit-a-snipe": "unit-a"})
    roster = [
        FakeUnit("b1", 1), FakeUnit("b2", 2),
        FakeUnit("unit-a-mg", 3), FakeUnit("unit-a-snipe", 3), FakeUnit("b3", 3),
    ]
    for deck in deck_search.shape_combinations(roster):
        slugs = {u.slug for u in deck}
        assert not {"unit-a-mg", "unit-a-snipe"} <= slugs
    for deck in deck_search.feasible_orderings(roster):
        slugs = {u.slug for u in deck}
        assert not {"unit-a-mg", "unit-a-snipe"} <= slugs


def test_a_favorite_item_build_is_the_same_character_as_its_base():
    # The Favorite Item is equipment on one owned unit, so her base and
    # -signature encodings are two builds of one character and cannot both hold
    # a seat. They are NOT candidates the engine may choose between - owning the
    # item is settled before the search runs.
    from app import deck_search

    assert deck_search.character_of("miranda-signature") == "miranda"
    assert deck_search.character_of("miranda") == "miranda"
    assert not deck_search._no_character_clash(
        [FakeUnit("miranda", 1), FakeUnit("miranda-signature", 1)])


def test_a_slug_with_no_sibling_build_is_its_own_character():
    from app import deck_search

    assert deck_search.character_of("crown") == "crown"
    assert deck_search._no_character_clash([FakeUnit("crown", 2), FakeUnit("blanc", 1)])


def test_reference_deck_never_seats_two_variants_of_one_base(monkeypatch):
    # prune_candidate_pool's reference-deck construction calls evaluate_deck
    # directly and doesn't go through shape_combinations/feasible_orderings,
    # so it never sees _no_character_clash on its own - _reference_deck must be
    # clash-aware itself (deck_search.py's controller-added Task 6 item).
    import app.deck_search as ds
    monkeypatch.setattr(ds, "_CHARACTER_OF",
                        {"unit-a-mg": "unit-a", "unit-a-snipe": "unit-a"})
    by_tier = {
        1: [FakeUnit("b1", 1)],
        2: [FakeUnit("b2", 2)],
        # prior-ranked with both clashing variants ahead of the distinct picks.
        3: [FakeUnit("unit-a-mg", 3), FakeUnit("unit-a-snipe", 3),
            FakeUnit("b3c", 3), FakeUnit("b3d", 3)],
    }
    reference = ds._reference_deck(by_tier, by_tier[1][0])
    b3_slugs = {u.slug for u in reference[2:]}
    assert not {"unit-a-mg", "unit-a-snipe"} <= b3_slugs
    assert len(reference) == 5  # still fills all 3 B3 slots despite the clash
    assert b3_slugs == {"unit-a-mg", "b3c", "b3d"}  # kept the higher-prior variant


def test_reference_deck_never_seats_a_cross_tier_variant_sibling(monkeypatch):
    # _character_safe_top only guards the B3 picks against EACH OTHER - it
    # doesn't know the B1 slot is occupied too. A MODE_VARIANTS pair spanning
    # tiers (VARIANT_BURST_TIERS, e.g. Rapi: Red Hood's Combat Assist B1
    # stand-in vs. her Burst-3 self) needs the B1's own sibling filtered out
    # of the B3 pool, or _reference_deck can seat both variants of one base
    # at once - the exact clash _no_character_clash forbids for real candidate
    # decks (found by exercising this path with real Rapi data, Task 7).
    import app.deck_search as ds
    monkeypatch.setattr(ds, "_CHARACTER_OF",
                        {"unit-a-b1": "unit-a", "unit-a-b3": "unit-a"})
    by_tier = {
        1: [FakeUnit("unit-a-b1", 1)],
        2: [FakeUnit("b2", 2)],
        # unit-a-b3 (the B1's own sibling) is prior-ranked FIRST among B3s.
        3: [FakeUnit("unit-a-b3", 3), FakeUnit("b3c", 3),
            FakeUnit("b3d", 3), FakeUnit("b3e", 3)],
    }
    reference = ds._reference_deck(by_tier, by_tier[1][0])
    slugs = {u.slug for u in reference}
    assert "unit-a-b3" not in slugs
    assert len(reference) == 5
    assert slugs == {"unit-a-b1", "b2", "b3c", "b3d", "b3e"}


def test_reference_deck_accepts_the_clash_when_no_legal_b3_pool_remains(monkeypatch):
    # Degenerate roster: exactly 3 total B3 units and one of them IS the B1's
    # own sibling - there is no way to fill all 3 B3 slots without it, so
    # _reference_deck must fall back to seating it rather than shorting the
    # reference below 5 units (breaking _TIER_SLOT's fixed slot-4 assumption
    # downstream).
    import app.deck_search as ds
    monkeypatch.setattr(ds, "_CHARACTER_OF",
                        {"unit-a-b1": "unit-a", "unit-a-b3": "unit-a"})
    by_tier = {
        1: [FakeUnit("unit-a-b1", 1)],
        2: [FakeUnit("b2", 2)],
        3: [FakeUnit("unit-a-b3", 3), FakeUnit("b3c", 3), FakeUnit("b3d", 3)],
    }
    reference = ds._reference_deck(by_tier, by_tier[1][0])
    assert len(reference) == 5
    assert {u.slug for u in reference} == {"unit-a-b1", "b2", "unit-a-b3", "b3c", "b3d"}


def test_reference_deck_tops_up_b3_when_same_tier_dedup_shorts_the_pool(monkeypatch):
    # The len(b3_pool) < 3 fallback above only covers the CROSS-TIER filter
    # shortening b3_pool itself. _character_safe_top's SAME-TIER dedup (two
    # variants of one base both surviving that filter, e.g. Cinderella:
    # Crystal Wave's MG/Snipe modes) can independently return fewer than 3
    # picks even though b3_pool has 3+ units - _reference_deck must top back
    # up from b3_pool, accepting the clash, rather than return a 4-unit
    # reference.
    import app.deck_search as ds
    monkeypatch.setattr(ds, "_CHARACTER_OF", {"cw-mg": "cw", "cw-snipe": "cw"})
    by_tier = {
        1: [FakeUnit("b1", 1)],
        2: [FakeUnit("b2", 2)],
        3: [FakeUnit("cw-mg", 3), FakeUnit("cw-snipe", 3), FakeUnit("b3x", 3)],
    }
    reference = ds._reference_deck(by_tier, by_tier[1][0])
    assert len(reference) == 5
    assert [u.burst_tier for u in reference] == [1, 2, 3, 3, 3]


def real_five_roster():
    # anis-star(b1), crown(b2) + three burst-3 attackers so ordering matters.
    # (rapi/privaty specs are built here to keep this test self-contained.)
    from tests.test_roster import NikkeSpec

    rapi = NikkeSpec(
        slug="rapi-red-hood", burst_tier=3, burst_cooldown=40.0, element="Fire", weapon="MG",
        base_stats={"atk": 417623, "def": 55374, "max_hp": 9699014},
        skill_values={
            "battlefield_assessment": {
                "description_value_01": "1", "description_value_02": "1", "description_value_03": "1",
                "description_value_04": "7.48", "description_value_05": "8.02", "description_value_06": "10",
                "description_value_07": "95.04", "description_value_08": "10", "description_value_09": "48",
                "description_value_10": "10",
            },
            "attachable_projectiles": {
                "description_value_01": "150.72", "description_value_02": "100.6",
                "description_value_03": "120", "description_value_04": "88.11",
                "description_value_05": "88.11",
            },
            "power_of_inheritance": {
                "description_value_08": "2808",
                "description_value_11": "421.2", "description_value_12": "10",
                "description_value_14": "60", "description_value_15": "10",
            },
        },
        weapon_stats={
            "weapon": "MG", "damage_percent": 5.57, "max_ammo": 300,
            "reload_time": 2.5, "charge_time": 0.0, "charge_damage_percent": 100.0,
        },
    )
    privaty = NikkeSpec(
        slug="privaty", burst_tier=3, burst_cooldown=40.0, element="Water", weapon="AR",
        base_stats={"atk": 395070, "def": 60980, "max_hp": 9159693},
        skill_values={
            "ex_magazine": {
                "description_value_01": "23.61", "description_value_02": "10", "description_value_03": "51.16",
                "description_value_04": "10", "description_value_05": "50.66", "description_value_06": "10",
                "description_value_07": "20.16", "description_value_08": "10",
            },
            "ak_missile": {
                "description_value_01": "1215.69", "description_value_02": "3", "description_value_03": "4.33",
                "description_value_04": "10", "description_value_05": "112.28", "description_value_06": "10",
            },
            "ld_assault": {
                "description_value_01": "8.65", "description_value_02": "10",
                "description_value_03": "221.24", "description_value_04": "1456.96",
            },
        },
        weapon_stats={
            "weapon": "AR", "damage_percent": 13.65, "max_ammo": 60,
            "reload_time": 1.0, "charge_time": 0.0, "charge_damage_percent": 100.0,
        },
    )
    return [anis_star_spec(), crown_spec(), helm_spec(), rapi, privaty]


def short_boss():
    # short fight keeps the 6 evaluations fast while still exercising >=2 cycles
    return BossProfile(element=None, core_hittable=False, fight_duration=40.0)


def test_find_best_decks_ranks_by_total_damage_descending():
    results = find_best_decks(real_five_roster(), short_boss(), top_n=6)
    totals = [r["total_damage"] for r in results]
    assert totals == sorted(totals, reverse=True)
    assert all(t > 0 for t in totals)


def test_deck_ordering_changes_the_score_role_assignment():
    # Same five Nikkes, six burst-3 orderings: who ends up nuking vs backup
    # buffer changes with order, so the scores must not be all identical.
    results = find_best_decks(real_five_roster(), short_boss(), top_n=6)
    distinct = {round(r["total_damage"], 2) for r in results}
    assert len(distinct) > 1


def test_find_best_decks_returns_deck_slug_order_and_breakdown():
    results = find_best_decks(real_five_roster(), short_boss(), top_n=1)
    best = results[0]
    assert len(best["deck"]) == 5
    assert best["deck"][0] == "anis-star"  # burst 1 always leftmost (canonical)
    assert "burst_damage" in best and "normal_attack_damage" in best


def test_breakdown_accounts_for_every_point_of_the_total():
    # A breakdown that only names two of the simulator's eight damage sources
    # leaves most of a deck's damage unexplained, which reads as a broken
    # number on screen rather than as an incomplete one.
    best = find_best_decks(real_five_roster(), short_boss(), top_n=1)[0]
    parts = best["burst_damage"] + best["normal_attack_damage"] + best["skill_damage"]
    assert parts == pytest.approx(best["total_damage"])


def test_skill_damage_collects_the_sources_that_are_neither_burst_nor_normal():
    best = find_best_decks(real_five_roster(), short_boss(), top_n=1)[0]
    other = sum(
        e["damage"] for e in best["result"]["damage_log"]
        if e["source"] not in ("burst", "normal_attack")
    )
    assert best["skill_damage"] == pytest.approx(other)
    assert best["skill_damage"] > 0  # this roster's DoTs/periodics are real damage


def test_boss_element_advantage_raises_a_decks_score():
    roster = real_five_roster()
    # privaty & helm are Water; a Fire boss gives Water attackers +10%.
    neutral = find_best_decks(roster, BossProfile(element=None, fight_duration=40.0), top_n=1)[0]
    advantaged = find_best_decks(roster, BossProfile(element="Fire", fight_duration=40.0), top_n=1)[0]
    assert advantaged["total_damage"] > neutral["total_damage"]


def test_shape_combinations_yields_only_the_three_real_shapes():
    from app.deck_search import shape_combinations
    roster = fake_roster([1, 1, 1, 2, 2, 2, 3, 3, 3, 3])
    shapes = {tuple(sum(1 for u in c if u.burst_tier == t) for t in (1, 2, 3))
              for c in shape_combinations(roster)}
    assert shapes == {(1, 1, 3), (1, 2, 2), (2, 1, 2)}


def test_shape_combinations_count_and_canonical_order():
    from app.deck_search import shape_combinations
    roster = fake_roster([1, 1, 2, 2, 3, 3, 3])  # 2 B1, 2 B2, 3 B3
    combos = list(shape_combinations(roster))
    # (1,1,3): 2*2*C(3,3)=4 · (1,2,2): 2*1*C(3,2)=6 · (2,1,2): 1*2*3=6
    assert len(combos) == 16
    for combo in combos:
        assert [u.burst_tier for u in combo] == sorted(u.burst_tier for u in combo)


def test_shape_combinations_empty_when_a_tier_is_missing():
    from app.deck_search import shape_combinations
    assert list(shape_combinations(fake_roster([1, 1, 3, 3, 3]))) == []


def _fake_scorer(scores_by_key):
    # Stand-in for evaluate_deck: scores keyed by (frozenset of slugs, tuple of
    # slugs) with fallbacks, so tests can rank combinations and orderings
    # without running 103ms sims.
    def fake_evaluate(ordered_deck, boss):
        key_exact = tuple(u.slug for u in ordered_deck)
        key_set = frozenset(key_exact)
        total = scores_by_key.get(key_exact, scores_by_key.get(key_set, 1.0))
        return {"total_damage": total, "damage_log": []}
    return fake_evaluate


def test_search_best_decks_finds_a_better_non_canonical_order(monkeypatch):
    import app.deck_search as ds
    roster = fake_roster([1, 2, 2, 3, 3, 3])
    # Canonical order of the {u1,u2} B2 pair is (u1, u2); make the swapped
    # order strictly better so only ordering search can find it.
    best_set = frozenset({"u0", "u1", "u2", "u3", "u4"})
    scores = {best_set: 100.0, ("u0", "u2", "u1", "u3", "u4"): 130.0}
    monkeypatch.setattr(ds, "evaluate_deck", _fake_scorer(scores))
    results = ds.search_best_decks(roster, BossProfile(), top_n=1)
    assert results[0]["total_damage"] == 130.0
    assert results[0]["deck"][1:3] == ["u2", "u1"]


@dataclass
class FakeSpec:
    slug: str
    burst_tier: int
    weapon: str = "AR"
    base_stats: dict = None
    weapon_stats: dict = None

    def __post_init__(self):
        self.base_stats = self.base_stats or {"atk": 1000.0}
        self.weapon_stats = self.weapon_stats or {"damage_percent": 100.0}


def _big_fake_roster():
    units = [FakeSpec(f"b1_{i}", 1) for i in range(4)]
    units += [FakeSpec(f"b2_{i}", 2) for i in range(6)]
    units += [FakeSpec(f"b3_{i}", 3) for i in range(12)]
    return units


def test_prune_candidate_pool_respects_tier_caps_without_sole_tier1_slug(monkeypatch):
    # Cap invariant holds for rosters without sole-tier-1 slugs; the widened
    # case is covered by test_prune_keeps_a_legal_tier1_pair_when_a_sole_tier1_slug_tops_the_pool.
    import app.deck_search as ds
    monkeypatch.setattr(ds, "evaluate_deck", _fake_scorer({}))
    pool = ds.prune_candidate_pool(_big_fake_roster(), BossProfile())
    counts = {t: sum(1 for u in pool if u.burst_tier == t) for t in (1, 2, 3)}
    assert counts[1] <= ds.PRUNED_TIER_CAPS[1]
    assert counts[2] <= ds.PRUNED_TIER_CAPS[2]
    assert counts[3] <= ds.PRUNED_TIER_CAPS[3]


def test_prune_swap_in_never_measures_two_variants_together(monkeypatch):
    # If the reference deck seats one mode variant in a non-last B3 slot
    # (index 2 or 3, not the "weakest B3" slot 4 that swap-ins normally
    # replace), swapping its sibling into slot 4 would seat both variants at
    # once - the exact clash _character_safe_top exists to keep out of the
    # reference itself. Every deck the swap-in loop measures must stay clash-free.
    import app.deck_search as ds
    monkeypatch.setattr(ds, "_CHARACTER_OF",
                        {"unit-a-mg": "unit-a", "unit-a-snipe": "unit-a"})
    roster = [
        FakeSpec("b1", 1),
        FakeSpec("b2", 2),
        # prior order (by atk, descending): unit-a-mg lands in the reference's
        # first (non-last) B3 slot; b3d lands in the last B3 slot that
        # swap-ins default to; unit-a-snipe ranks lowest, so it's a swap-in
        # candidate rather than a reference pick.
        FakeSpec("unit-a-mg", 3, base_stats={"atk": 400.0}),
        FakeSpec("b3c", 3, base_stats={"atk": 300.0}),
        FakeSpec("b3d", 3, base_stats={"atk": 200.0}),
        FakeSpec("unit-a-snipe", 3, base_stats={"atk": 100.0}),
    ]

    seen_decks = []

    def scorer(ordered_deck, boss):
        seen_decks.append([u.slug for u in ordered_deck])
        return {"total_damage": 1.0, "damage_log": []}

    monkeypatch.setattr(ds, "evaluate_deck", scorer)
    ds.prune_candidate_pool(roster, BossProfile())

    assert seen_decks  # sanity: the swap-in loop actually ran
    for deck in seen_decks:
        assert not {"unit-a-mg", "unit-a-snipe"} <= set(deck)


def test_swap_slot_refuses_a_cross_tier_variant_sibling(monkeypatch):
    # VARIANT_BURST_TIERS lets one base's two variants sit in different
    # burst tiers (e.g. Rapi: Red Hood's B1 stand-in vs. its B3 self). If the
    # tier-1 variant already seats the reference's tier-1 slot, _swap_slot
    # must not hand back that slot for the tier-3 sibling - overwriting it
    # would drop the reference to zero tier-1 units (deck_search.py's
    # controller-added Task 6 item). The tier-3 default slot isn't safe
    # either: it would leave the tier-1 sibling seated too, so no clean
    # single-slot swap exists and _swap_slot must say so.
    import app.deck_search as ds
    monkeypatch.setattr(ds, "_CHARACTER_OF",
                        {"unit-a-b1": "unit-a", "unit-a-b3": "unit-a"})
    reference = [
        FakeUnit("unit-a-b1", 1),  # tier-1 variant seated at the tier-1 slot
        FakeUnit("b2", 2),
        FakeUnit("b3x", 3), FakeUnit("b3y", 3), FakeUnit("b3z", 3),
    ]
    unit = FakeUnit("unit-a-b3", 3)  # its tier-3 sibling
    assert ds._swap_slot(reference, unit) is None


def test_prune_cross_tier_variant_never_breaks_shape_or_clashes(monkeypatch):
    # Integration version of the above through the real swap-in loop:
    # prune_candidate_pool must never hand evaluate_deck a deck that either
    # drops below one tier-1 unit (shape violation) or seats both "unit-a"
    # variants at once (the exact clash _no_character_clash forbids for real
    # candidate decks).
    import app.deck_search as ds
    monkeypatch.setattr(ds, "_CHARACTER_OF",
                        {"unit-a-b1": "unit-a", "unit-a-b3": "unit-a"})
    roster = [
        FakeSpec("unit-a-b1", 1),  # sole tier-1 unit -> seats the reference's tier-1 slot
        FakeSpec("b2", 2),
        FakeSpec("b3c", 3, base_stats={"atk": 300.0}),
        FakeSpec("b3d", 3, base_stats={"atk": 200.0}),
        FakeSpec("b3e", 3, base_stats={"atk": 100.0}),
        # lowest prior of the tier-3 group -> a swap-in candidate, not a
        # reference occupant; its base sibling is unit-a-b1 above.
        FakeSpec("unit-a-b3", 3, base_stats={"atk": 50.0}),
    ]

    seen_decks = []

    def scorer(ordered_deck, boss):
        seen_decks.append(list(ordered_deck))
        return {"total_damage": 1.0, "damage_log": []}

    monkeypatch.setattr(ds, "evaluate_deck", scorer)
    ds.prune_candidate_pool(roster, BossProfile())

    assert seen_decks  # sanity: at least the reference baseline was scored
    for deck in seen_decks:
        slugs = {u.slug for u in deck}
        assert not {"unit-a-b1", "unit-a-b3"} <= slugs
        tiers = [u.burst_tier for u in deck]
        assert tiers[0] == 1 and tiers[1] == 2 and tiers[2:] == [3, 3, 3]


def test_prune_measures_cross_tier_sibling_instead_of_starving_it(monkeypatch):
    # Refusing the swap (_swap_slot -> None) must not mean "never measured".
    # Force the single-pass path _reference_b1_variants takes when the
    # top-prior B1 is ALSO the best-measured B1 (a constant fake scorer makes
    # every swap-in delta 0.0, so the tie always resolves to the first/
    # top-prior candidate and pass 2 is skipped) - the exact scenario where
    # unit-a-b1 alone occupies the reference's tier-1 slot for the entire
    # prune. unit-a-b3, its cross-tier sibling, can't swap into that
    # reference at all, but it must still be handed to evaluate_deck at
    # least once (measured against an alternate reference) rather than
    # scored an unmeasured 0.0 that would sort it out of the pool as an
    # artifact of measurement order, not weakness.
    import app.deck_search as ds
    monkeypatch.setattr(ds, "_CHARACTER_OF",
                        {"unit-a-b1": "unit-a", "unit-a-b3": "unit-a"})
    roster = [
        FakeSpec("unit-a-b1", 1, base_stats={"atk": 500.0}),  # top-prior B1
        FakeSpec("b1x", 1, base_stats={"atk": 100.0}),  # tier-1 alternative
        FakeSpec("b2", 2),
        FakeSpec("b3c", 3, base_stats={"atk": 300.0}),
        FakeSpec("b3d", 3, base_stats={"atk": 200.0}),
        FakeSpec("b3e", 3, base_stats={"atk": 100.0}),
        # lowest prior of the tier-3 group -> cross-tier sibling of unit-a-b1
        FakeSpec("unit-a-b3", 3, base_stats={"atk": 50.0}),
    ]

    seen_decks = []

    def scorer(ordered_deck, boss):
        seen_decks.append(list(ordered_deck))
        return {"total_damage": 1.0, "damage_log": []}  # constant -> every delta is 0.0

    monkeypatch.setattr(ds, "evaluate_deck", scorer)
    ds.prune_candidate_pool(roster, BossProfile())

    measured = any(u.slug == "unit-a-b3" for deck in seen_decks for u in deck)
    assert measured, "unit-a-b3 must be simulated at least once, not scored an unmeasured 0.0"


def test_cross_tier_reference_rejects_an_alternative_that_clashes_elsewhere(monkeypatch):
    # _cross_tier_reference picks an "alternative" to swap into the sibling's
    # slot from by_tier[sibling.burst_tier]. The old filter only excluded
    # units already seated in `reference` and units sharing the CANDIDATE's
    # own base - it did not check whether the alternative's OWN mode-variant
    # sibling was already seated elsewhere in `reference` under a third,
    # unrelated base. Two variant groups here: unit-a-b1/unit-a-b3 span tiers
    # (forces the _cross_tier_reference path for candidate unit-a-b1, whose
    # sibling unit-a-b3 seats a reference B3 slot), and unit-c-mg/unit-c-snipe
    # are a same-tier B3 pair living among the alternatives themselves -
    # unit-c-mg seats another reference B3 slot, so its unseated sibling
    # unit-c-snipe (higher prior than the only clash-free option) is exactly
    # the illegal pick the old filter would have accepted.
    import app.deck_search as ds
    monkeypatch.setattr(ds, "_CHARACTER_OF", {
        "unit-a-b1": "unit-a", "unit-a-b3": "unit-a",
        "unit-c-mg": "unit-c", "unit-c-snipe": "unit-c",
    })
    roster = [
        FakeSpec("b1x", 1, base_stats={"atk": 1000.0}),  # top-prior B1 -> seats the reference
        FakeSpec("unit-a-b1", 1, base_stats={"atk": 500.0}),  # cross-tier candidate
        FakeSpec("b2", 2),
        FakeSpec("unit-a-b3", 3, base_stats={"atk": 500.0}),  # seats a reference B3 slot
        FakeSpec("unit-c-mg", 3, base_stats={"atk": 400.0}),  # seats another reference B3 slot
        FakeSpec("b3z", 3, base_stats={"atk": 300.0}),  # seats the last reference B3 slot
        FakeSpec("unit-c-snipe", 3, base_stats={"atk": 200.0}),  # illegal alternative pick
        FakeSpec("b3w", 3, base_stats={"atk": 100.0}),  # the only clash-free alternative
    ]

    seen_decks = []

    def scorer(ordered_deck, boss):
        seen_decks.append(list(ordered_deck))
        return {"total_damage": 1.0, "damage_log": []}  # constant -> keeps the pass single

    monkeypatch.setattr(ds, "evaluate_deck", scorer)
    ds.prune_candidate_pool(roster, BossProfile())

    assert seen_decks  # sanity: the cross-tier path actually ran
    for deck in seen_decks:
        slugs = {u.slug for u in deck}
        assert not {"unit-a-b1", "unit-a-b3"} <= slugs
        assert not {"unit-c-mg", "unit-c-snipe"} <= slugs
        assert ds._no_character_clash(deck)


def test_prune_keeps_synergy_partners_together(monkeypatch):
    import app.deck_search as ds
    roster = _big_fake_roster()
    roster += [FakeSpec("mint", 2), FakeSpec("prika", 2)]

    def scorer(ordered_deck, boss):
        slugs = [u.slug for u in ordered_deck]
        # Prika must burst before Mint for Encore to fire - the pair only
        # measures its synergy when prika precedes mint in burst order.
        if "prika" in slugs and "mint" in slugs and slugs.index("prika") < slugs.index("mint"):
            return {"total_damage": 10_000.0, "damage_log": []}
        if "mint" in set(slugs):
            return {"total_damage": 1.0, "damage_log": []}
        return {"total_damage": 100.0, "damage_log": []}

    monkeypatch.setattr(ds, "evaluate_deck", scorer)
    pool_slugs = {u.slug for u in ds.prune_candidate_pool(roster, BossProfile())}
    assert {"mint", "prika"} <= pool_slugs


def test_sole_tier1_slug_rejected_next_to_another_b1():
    # rapi-red-hood-b1's Combat Assist only holds when she is the deck's ONLY
    # Burst-1 unit - seating her next to a real B1 (liter) simulates a
    # formation the game never lets Combat Assist survive in, so both
    # enumeration paths must exclude that pairing (SOLE_TIER1_SLUGS).
    from app import deck_search
    roster = [FakeUnit("rapi-red-hood-b1", 1), FakeUnit("liter", 1),
              FakeUnit("b2", 2), FakeUnit("d1", 3), FakeUnit("d2", 3), FakeUnit("d3", 3)]
    for deck in deck_search.shape_combinations(roster):
        slugs = {u.slug for u in deck}
        assert not {"rapi-red-hood-b1", "liter"} <= slugs
    for deck in deck_search.feasible_orderings(roster):
        slugs = {u.slug for u in deck}
        assert not {"rapi-red-hood-b1", "liter"} <= slugs


def test_prune_keeps_a_legal_tier1_pair_when_a_sole_tier1_slug_tops_the_pool(monkeypatch):
    # rapi-red-hood-b1 can't co-seat with any other B1 (_tier1_seating_valid,
    # SOLE_TIER1_SLUGS). If she fills one of only PRUNED_TIER_CAPS[1]=2
    # tier-1 slots, the pool's only tier-1 pair is illegal and
    # shape_combinations can never produce a (2,1,2) deck - the cap must
    # widen so a real B1 pair also survives the cut alongside her.
    import app.deck_search as ds
    roster = _big_fake_roster()
    roster += [FakeSpec("rapi-red-hood-b1", 1, base_stats={"atk": 2000.0})]  # top-prior B1

    monkeypatch.setattr(ds, "evaluate_deck", _fake_scorer({}))
    pool = ds.prune_candidate_pool(roster, BossProfile())
    shapes = {tuple(sum(1 for u in c if u.burst_tier == t) for t in (1, 2, 3))
              for c in ds.shape_combinations(pool)}
    assert (2, 1, 2) in shapes


def test_search_best_decks_pool_parity():
    from app.deck_search import search_best_decks
    from app.sim_pool import SimPool
    roster, boss = real_five_roster(), short_boss()
    serial = search_best_decks(roster, boss, top_n=3)
    with SimPool(roster, boss, workers=2, spawn_threshold=1) as pool:
        pooled = search_best_decks(roster, boss, top_n=3, pool=pool)
    assert [d["deck"] for d in pooled] == [d["deck"] for d in serial]
    assert [d["total_damage"] for d in pooled] == [d["total_damage"] for d in serial]
    assert all("result" in d for d in pooled)  # return contract kept


def test_search_scores_every_intra_tier_ordering_of_every_combination(monkeypatch):
    # The ordering-blind failure this replaces: a combination was ranked on ONE
    # arbitrary intra-tier order, and only a top-K shortlist ever got permuted,
    # so a deck that is only good in a different order could be cut before its
    # order was tried. Measured on real data that gap reached 78%, with the
    # true best (1,1,3) ranking #21 canonically - intra-tier order decides
    # which member never bursts (Fienn's Mint-before-Prika / silent-Velvet
    # cases), so no combination may be ranked on a single order.
    import app.deck_search as ds
    roster = fake_roster([1, 2, 2, 3, 3, 3])
    scored = []

    def recording_evaluate(ordered_deck, boss):
        scored.append(tuple(u.slug for u in ordered_deck))
        return {"total_damage": 1.0, "damage_log": []}

    monkeypatch.setattr(ds, "evaluate_deck", recording_evaluate)
    ds.search_best_decks(roster, BossProfile(), top_n=1)

    expected = {tuple(u.slug for u in ordered)
                for combo in ds.shape_combinations(roster)
                for ordered in ds._intra_tier_orderings(combo)}
    assert expected <= set(scored)


def test_search_returns_a_winning_order_its_combination_only_reaches_when_permuted(monkeypatch):
    import app.deck_search as ds
    roster = fake_roster([1, 2, 2, 3, 3, 3])
    # Every other order scores 1.0; the winner is a NON-canonical B2 order.
    winner = ("u0", "u2", "u1", "u3", "u4")
    monkeypatch.setattr(ds, "evaluate_deck", _fake_scorer({winner: 500.0}))

    results = ds.search_best_decks(roster, BossProfile(), top_n=1)

    assert results[0]["total_damage"] == 500.0
    assert tuple(results[0]["deck"]) == winner


def test_search_budget_counts_orderings_not_just_combinations(monkeypatch):
    # sim_budget caps SIMS, and scoring every ordering costs several sims per
    # combination - so the budget must be compared against the ordering count,
    # or the pool is never pruned and the budget is silently blown.
    import app.deck_search as ds
    roster = fake_roster([1, 2, 2, 3, 3, 3])
    pruned = []

    def fake_prune(roster_arg, boss, pool=None):
        pruned.append(True)
        return list(roster_arg)[:5]

    monkeypatch.setattr(ds, "prune_candidate_pool", fake_prune)
    monkeypatch.setattr(ds, "evaluate_deck", _fake_scorer({}))
    # 5 combinations but 16 orderings: a budget between the two must prune.
    ds.search_best_decks(roster, BossProfile(), top_n=1, sim_budget=6)

    assert pruned, "budget compared against combinations only, not orderings"


# --- Cascade injection: search_best_decks never imports app.cascade (see its
# module docstring) -- these stand in for a real Cascade via duck typing.
# prune_candidate_pool needs real base_stats/weapon_stats to rank on (_prior),
# so these use FakeSpec (like the prune tests above), not fake_roster's bare
# FakeUnit.
def _cascade_test_roster():
    return [FakeSpec(f"u{i}", t) for i, t in enumerate([1, 1, 2, 2, 3, 3, 3, 3])]


def test_search_best_decks_uses_the_cascade_when_over_budget(monkeypatch):
    """The cascade's shortlist must be what gets simulated, not the pruned pool."""
    import app.deck_search as ds
    roster = _cascade_test_roster()
    chosen = [[roster[0], roster[2], roster[4], roster[5], roster[6]]]
    monkeypatch.setattr(ds, "evaluate_deck", _fake_scorer({}))

    class _StubCascade:
        def shortlist(self, r, b, pool=None):
            return chosen

    found = ds.search_best_decks(roster, BossProfile(element="Water"), top_n=1,
                                 sim_budget=1, cascade=_StubCascade())

    assert {u.slug for u in chosen[0]} == set(found[0]["deck"])


def test_search_best_decks_falls_back_when_the_cascade_declines(monkeypatch):
    import app.deck_search as ds
    roster = _cascade_test_roster()
    monkeypatch.setattr(ds, "evaluate_deck", _fake_scorer({}))

    class _DecliningCascade:
        def shortlist(self, r, b, pool=None):
            return None

    found = ds.search_best_decks(roster, BossProfile(element="Water"), top_n=1,
                                 sim_budget=1, cascade=_DecliningCascade())

    assert len(found) == 1          # the exhaustive path still produced a deck
    assert len(found[0]["deck"]) == 5  # deck has exactly 5 units
    assert set(found[0]["deck"]) <= {u.slug for u in roster}  # all slugs come from the roster


# --- Non-bursting buffer ("totem") seating: Modernia and Velvet ---------------
# Their bursts are a DPS loss / buff-only, so they yield the burst to a same-tier
# ally. Encoded as a SEAT rule only (Fienn, 2026-07-22): they must sit LAST in
# their tier (burst_cycle fires the leftmost eligible), so a tier-mate takes the
# burst. The shape is NOT hard-restricted - the shape that lets them never burst
# ((1,1,3) for Modernia, (1,2,2) for Velvet) simply scores highest, so the
# search picks it, without making a thin roster infeasible. See
# deck_search._BUFFER_SEAT_SLUGS.
from collections import Counter

from app.burst_cycle import simulate_burst_cycle
from app.deck_search import (
    _buffer_seat_valid,
    feasible_orderings,
)


def test_modernia_always_seated_last_among_burst3():
    # She may appear in any shape now, but never with a Burst-3 ally after her.
    roster = [
        FakeUnit("b1", 1),
        FakeUnit("b2a", 2), FakeUnit("b2b", 2),
        FakeUnit("b3a", 3), FakeUnit("b3b", 3), FakeUnit("modernia", 3),
    ]
    orderings = list(feasible_orderings(roster))
    assert any(any(u.slug == "modernia" for u in o) for o in orderings)  # not filtered out
    for ordered in orderings:
        b3 = [u.slug for u in ordered if u.burst_tier == 3]
        if "modernia" in b3:
            assert b3[-1] == "modernia"  # last B3 seat


def test_velvet_always_seated_last_among_burst2():
    roster = [
        FakeUnit("b1", 1),
        FakeUnit("b2a", 2), FakeUnit("velvet", 2),
        FakeUnit("b3a", 3), FakeUnit("b3b", 3), FakeUnit("b3c", 3),
    ]
    orderings = list(feasible_orderings(roster))
    assert any(any(u.slug == "velvet" for u in o) for o in orderings)
    for ordered in orderings:
        b2 = [u.slug for u in ordered if u.burst_tier == 2]
        if "velvet" in b2:
            assert b2[-1] == "velvet"  # last B2 seat


def test_buffer_unit_stays_feasible_in_a_thin_roster():
    # Only two Burst-3s total (no (1,1,3) possible), a (1,2,2) roster. The seat
    # rule must NOT make it infeasible - Modernia is still seatable (as the last
    # B3), just not guaranteed never to burst without a third B3 to cover the
    # cycle. This is the case the earlier hard shape lock turned into a 422.
    roster = [
        FakeUnit("b1", 1), FakeUnit("b2a", 2), FakeUnit("b2b", 2),
        FakeUnit("b3a", 3), FakeUnit("modernia", 3),
    ]
    orderings = list(feasible_orderings(roster))
    assert orderings  # a deck still forms
    assert all(any(u.slug == "modernia" for u in o) for o in orderings)  # she's in every deck
    for ordered in orderings:
        b3 = [u.slug for u in ordered if u.burst_tier == 3]
        assert b3[-1] == "modernia"  # still seated last


def test_buffer_seat_helper_leaves_ordinary_decks_untouched():
    plain = [FakeUnit("b1", 1), FakeUnit("b2", 2),
             FakeUnit("b3a", 3), FakeUnit("b3b", 3), FakeUnit("b3c", 3)]
    assert _buffer_seat_valid(plain)


def _burst_counts(deck, cdr=None):
    on_fb_end = (lambda t: cdr) if cdr else None
    events = simulate_burst_cycle(
        deck, gauge_charge_time=2.0, fight_duration=180.0, mode="manual",
        on_full_burst_end=on_fb_end)
    bursts = Counter(e["slug"] for e in events if e["type"] == "burst")
    full_bursts = sum(1 for e in events if e["type"] == "full_burst_start")
    return bursts, full_bursts


def test_modernia_never_bursts_as_the_last_b3_of_a_113():
    deck = [
        {"slug": "b1", "burst_tier": 1, "cooldown": 20.0},
        {"slug": "b2", "burst_tier": 2, "cooldown": 20.0},
        {"slug": "b3a", "burst_tier": 3, "cooldown": 40.0},
        {"slug": "b3b", "burst_tier": 3, "cooldown": 40.0},
        {"slug": "modernia", "burst_tier": 3, "cooldown": 40.0},  # last B3 = buffer
    ]
    bursts, full_bursts = _burst_counts(deck)
    assert bursts["modernia"] == 0            # never takes the burst
    assert full_bursts > 0                    # deck still reaches Full Burst
    # the two real B3s alternate to cover every cycle a B3 fires.
    assert bursts["b3a"] + bursts["b3b"] == full_bursts
    # holds with cooldown reduction too (more cycles, still zero Modernia bursts).
    bursts_cdr, _ = _burst_counts(deck, cdr={m["slug"]: 6.0 for m in deck})
    assert bursts_cdr["modernia"] == 0


def test_velvet_never_bursts_as_the_last_b2_of_a_122():
    deck = [
        {"slug": "b1", "burst_tier": 1, "cooldown": 20.0},
        {"slug": "b2a", "burst_tier": 2, "cooldown": 20.0},
        {"slug": "velvet", "burst_tier": 2, "cooldown": 20.0},  # last B2 = buffer
        {"slug": "b3a", "burst_tier": 3, "cooldown": 40.0},
        {"slug": "b3b", "burst_tier": 3, "cooldown": 40.0},
    ]
    bursts, full_bursts = _burst_counts(deck)
    assert bursts["velvet"] == 0              # never takes the burst
    assert full_bursts > 0
    assert bursts["b2a"] == full_bursts       # the other B2 carries every cycle
    bursts_cdr, _ = _burst_counts(deck, cdr={m["slug"]: 6.0 for m in deck})
    assert bursts_cdr["velvet"] == 0


def test_search_output_always_seats_modernia_last_among_b3(monkeypatch):
    # End-to-end through search_best_decks (prune -> enumerate -> rank): every
    # ranked deck containing Modernia seats her as the LAST Burst-3, so a
    # tier-mate is the leftmost-eligible burster. A tie-scoring stub keeps the
    # assertion about seating, not damage (seating is set by enumeration).
    import app.deck_search as ds
    roster = [
        FakeSpec("b1", 1), FakeSpec("b2", 2),
        FakeSpec("b3a", 3), FakeSpec("b3b", 3), FakeSpec("modernia", 3),
    ]
    b3_slugs = {"b3a", "b3b", "modernia"}
    monkeypatch.setattr(ds, "evaluate_deck", _fake_scorer({}))
    results = ds.search_best_decks(roster, BossProfile(), top_n=6)
    assert results
    saw_modernia = False
    for r in results:
        deck = r["deck"]
        if "modernia" not in deck:
            continue
        saw_modernia = True
        b3_positions = [i for i, s in enumerate(deck) if s in b3_slugs]
        assert deck[max(b3_positions)] == "modernia"  # last B3 seat
    assert saw_modernia  # she is actually in the recommendations, not filtered out


def test_search_output_always_seats_velvet_last_among_b2(monkeypatch):
    import app.deck_search as ds
    roster = [
        FakeSpec("b1", 1), FakeSpec("b2a", 2), FakeSpec("velvet", 2),
        FakeSpec("b3a", 3), FakeSpec("b3b", 3),
    ]
    b2_slugs = {"b2a", "velvet"}
    monkeypatch.setattr(ds, "evaluate_deck", _fake_scorer({}))
    results = ds.search_best_decks(roster, BossProfile(), top_n=6)
    assert results
    saw_velvet = False
    for r in results:
        deck = r["deck"]
        if "velvet" not in deck:
            continue
        saw_velvet = True
        b2_positions = [i for i, s in enumerate(deck) if s in b2_slugs]
        assert deck[max(b2_positions)] == "velvet"  # last B2 seat
    assert saw_velvet


def test_orderings_within_budget_returns_them_all_when_under():
    from app.deck_search import _all_intra_tier_orderings, _orderings_within_budget
    from app.deck_search import shape_combinations

    roster = fake_roster([1, 2, 3, 3, 3])
    out = _orderings_within_budget(roster, sim_budget=1000)
    assert out == _all_intra_tier_orderings(shape_combinations(roster))


def test_orderings_within_budget_returns_none_when_over():
    from app.deck_search import _orderings_within_budget

    roster = fake_roster([1, 2, 3, 3, 3])
    assert _orderings_within_budget(roster, sim_budget=2) is None


def test_orderings_within_budget_stops_early_instead_of_enumerating_everything():
    """A tiny budget against a large ordering space still returns None (over
    budget), not a partial/incorrect list - the actual early-exit mechanics
    (that the generator stops being pulled) are verified separately by
    test_orderings_within_budget_never_pulls_the_full_generator below."""
    from app.deck_search import _all_intra_tier_orderings, _orderings_within_budget
    from app.deck_search import shape_combinations

    roster = fake_roster([1, 1, 1, 2, 2, 2, 3, 3, 3, 3, 3, 3, 3, 3])
    full = len(_all_intra_tier_orderings(shape_combinations(roster)))
    assert full > 100                       # the space really is large
    assert _orderings_within_budget(roster, sim_budget=1) is None


def test_orderings_within_budget_never_pulls_the_full_generator(monkeypatch):
    # The other budget tests only check the RETURN VALUE, which an eager
    # implementation (enumerate everything, then compare len() to the budget)
    # would also satisfy. This test guards the actual point of the helper -
    # that it stops pulling from the ordering generator at the budget instead
    # of walking the whole space - by counting items as they're pulled
    # through a lazy wrapper (never materialized into a list, which would
    # destroy the very laziness being tested).
    import app.deck_search as ds

    roster = fake_roster([1, 1, 1, 2, 2, 2, 3, 3, 3, 3, 3, 3, 3, 3])
    full = len(ds._all_intra_tier_orderings(ds.shape_combinations(roster)))
    assert full > 1000  # the full space really does dwarf the budget below

    pulled = 0
    real_intra_tier_orderings = ds._intra_tier_orderings

    def counting_intra_tier_orderings(combo):
        nonlocal pulled
        for ordered in real_intra_tier_orderings(combo):
            pulled += 1
            yield ordered

    monkeypatch.setattr(ds, "_intra_tier_orderings", counting_intra_tier_orderings)
    sim_budget = 5
    assert ds._orderings_within_budget(roster, sim_budget=sim_budget) is None

    assert pulled == sim_budget + 1  # stopped the instant the budget was crossed
    assert pulled < full
