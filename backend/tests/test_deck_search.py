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


def real_five_roster():
    # anis-star(b1), crown(b2) + three burst-3 attackers so ordering matters.
    # (rapi/privaty specs are built here to keep this test self-contained.)
    from tests.test_roster import NikkeSpec

    rapi = NikkeSpec(
        slug="rapi-red-hood", burst_tier=3, burst_cooldown=40.0, element="Fire", weapon="MG",
        base_stats={"atk": 417623, "def": 55374, "max_hp": 9699014},
        skill_values={
            "battlefield_assessment": {
                "description_value_01": "1", "description_value_02": "7.48", "description_value_03": "95.04",
                "description_value_04": "10", "description_value_05": "48", "description_value_06": "10",
                "description_value_07": "8.02", "description_value_08": "10",
            },
            "power_of_inheritance": {"description_value_05": "2808"},
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
    # 4 canonical combos for this roster; only ONE combo's orderings refined.
    canonical_calls = 4
    refined_orderings = 2  # the (1,2,2) shape's B2 pair permutes 2! ways
    assert len(calls) <= canonical_calls + refined_orderings
