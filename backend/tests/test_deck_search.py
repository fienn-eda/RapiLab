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


def test_prune_candidate_pool_respects_tier_caps(monkeypatch):
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
