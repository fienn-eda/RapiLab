from dataclasses import dataclass

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
    monkeypatch.setattr(deck_search, "_VARIANT_GROUP",
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


def test_reference_deck_never_seats_two_variants_of_one_base(monkeypatch):
    # prune_candidate_pool's reference-deck construction calls evaluate_deck
    # directly and doesn't go through shape_combinations/feasible_orderings,
    # so it never sees _no_variant_clash on its own - _reference_deck must be
    # clash-aware itself (deck_search.py's controller-added Task 6 item).
    import app.deck_search as ds
    monkeypatch.setattr(ds, "_VARIANT_GROUP",
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
    # _variant_safe_top only guards the B3 picks against EACH OTHER - it
    # doesn't know the B1 slot is occupied too. A MODE_VARIANTS pair spanning
    # tiers (VARIANT_BURST_TIERS, e.g. Rapi: Red Hood's Combat Assist B1
    # stand-in vs. her Burst-3 self) needs the B1's own sibling filtered out
    # of the B3 pool, or _reference_deck can seat both variants of one base
    # at once - the exact clash _no_variant_clash forbids for real candidate
    # decks (found by exercising this path with real Rapi data, Task 7).
    import app.deck_search as ds
    monkeypatch.setattr(ds, "_VARIANT_GROUP",
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
    monkeypatch.setattr(ds, "_VARIANT_GROUP",
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
    # shortening b3_pool itself. _variant_safe_top's SAME-TIER dedup (two
    # variants of one base both surviving that filter, e.g. Cinderella:
    # Crystal Wave's MG/Snipe modes) can independently return fewer than 3
    # picks even though b3_pool has 3+ units - _reference_deck must top back
    # up from b3_pool, accepting the clash, rather than return a 4-unit
    # reference.
    import app.deck_search as ds
    monkeypatch.setattr(ds, "_VARIANT_GROUP", {"cw-mg": "cw", "cw-snipe": "cw"})
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


def test_search_best_decks_refines_order_only_for_top_combos(monkeypatch):
    import app.deck_search as ds
    roster = fake_roster([1, 2, 2, 3, 3, 3])
    # Canonical order of the {u1,u2} B2 pair is (u1, u2); make the swapped
    # order strictly better so only permutation refinement can find it.
    best_set = frozenset({"u0", "u1", "u2", "u3", "u4"})
    scores = {best_set: 100.0, ("u0", "u2", "u1", "u3", "u4"): 130.0}
    monkeypatch.setattr(ds, "evaluate_deck", _fake_scorer(scores))
    results = ds.search_best_decks(roster, BossProfile(), top_n=1)
    assert results[0]["total_damage"] == 130.0
    assert results[0]["deck"][1:3] == ["u2", "u1"]


def test_search_best_decks_respects_permutation_top_k(monkeypatch):
    import app.deck_search as ds
    roster = fake_roster([1, 2, 2, 3, 3, 3])
    calls = []

    def counting_evaluate(ordered_deck, boss):
        calls.append(tuple(u.slug for u in ordered_deck))
        return {"total_damage": 1.0, "damage_log": []}

    monkeypatch.setattr(ds, "evaluate_deck", counting_evaluate)
    ds.search_best_decks(roster, BossProfile(), top_n=1, permutation_top_k=1)
    # 5 canonical combos for this roster ((1,1,3): 2, (1,2,2): 3); with
    # permutation_top_k=1 exactly ONE combo is refined - 4 orderings if it is
    # a (1,2,2) (2!x2!), 6 if a (1,1,3) (3!). All-refined would be 29 calls.
    assert 5 < len(calls) <= 5 + 6


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
    # once - the exact clash _variant_safe_top exists to keep out of the
    # reference itself. Every deck the swap-in loop measures must stay clash-free.
    import app.deck_search as ds
    monkeypatch.setattr(ds, "_VARIANT_GROUP",
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
    monkeypatch.setattr(ds, "_VARIANT_GROUP",
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
    # variants at once (the exact clash _no_variant_clash forbids for real
    # candidate decks).
    import app.deck_search as ds
    monkeypatch.setattr(ds, "_VARIANT_GROUP",
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
    monkeypatch.setattr(ds, "_VARIANT_GROUP",
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
    monkeypatch.setattr(ds, "_VARIANT_GROUP", {
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
        assert ds._no_variant_clash(deck)


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


def test_prune_includes_sg_theme_around_tove(monkeypatch):
    import app.deck_search as ds
    roster = _big_fake_roster()  # all AR
    roster += [FakeSpec("tove", 1, weapon="AR")]
    roster += [FakeSpec(f"sg_{i}", 3, weapon="SG",
                        base_stats={"atk": 1.0}) for i in range(2)]  # tiny prior

    monkeypatch.setattr(ds, "evaluate_deck", _fake_scorer({}))
    pool_slugs = {u.slug for u in ds.prune_candidate_pool(roster, BossProfile())}
    assert "tove" in pool_slugs
    assert {"sg_0", "sg_1"} <= pool_slugs  # anchored theme survives the cut


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
