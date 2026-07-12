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
