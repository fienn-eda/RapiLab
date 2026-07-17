from app.deck_search import BossProfile, evaluate_deck
from app.sim_pool import SimPool, resolve_workers
from tests.test_deck_search import real_five_roster


def short_boss():
    return BossProfile(element=None, core_hittable=False, fight_duration=20.0)


def test_resolve_workers_serial_values():
    assert resolve_workers(None) == 1
    assert resolve_workers(0) == 1
    assert resolve_workers(1) == 1
    assert resolve_workers(4) == 4
    assert resolve_workers("auto") >= 1


def test_serial_score_many_matches_direct_evaluate_deck():
    roster, boss = real_five_roster(), short_boss()
    deck_a, deck_b = list(roster), [roster[0], roster[1], roster[4], roster[3], roster[2]]
    with SimPool(roster, boss, workers=None) as pool:
        totals = pool.score_many([deck_a, deck_b])
    assert totals == [evaluate_deck(deck_a, boss)["total_damage"],
                      evaluate_deck(deck_b, boss)["total_damage"]]
    assert totals[0] != totals[1]  # ordering matters, so the two differ


def test_serial_summarize_many_matches_direct_evaluate_deck():
    roster, boss = real_five_roster(), short_boss()
    deck = list(roster)
    with SimPool(roster, boss, workers=None) as pool:
        (summary,) = pool.summarize_many([deck])
    result = evaluate_deck(deck, boss)
    assert summary == {
        "deck": [u.slug for u in deck],
        "total_damage": result["total_damage"],
        "burst_damage": sum(e["damage"] for e in result["damage_log"] if e["source"] == "burst"),
        "normal_attack_damage": sum(
            e["damage"] for e in result["damage_log"] if e["source"] == "normal_attack"),
    }


def test_serial_mode_never_spawns_an_executor():
    roster, boss = real_five_roster(), short_boss()
    with SimPool(roster, boss, workers=None) as pool:
        pool.score_many([list(roster)] * 40)  # over SPAWN_THRESHOLD, still serial
        assert pool._executor is None
