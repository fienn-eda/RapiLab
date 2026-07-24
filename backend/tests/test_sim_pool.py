import app.sim_pool as sim_pool
from app.deck_search import BossProfile, evaluate_deck
from app.sim_pool import SimPool, resolve_workers
from tests.test_deck_search import real_five_roster


def short_boss():
    return BossProfile(element=None, core_hittable=False, fight_duration=20.0)


def _inline_forbidden(deck, boss):
    raise AssertionError("batch ran inline when a warm executor was available")


def test_resolve_workers_serial_values():
    assert resolve_workers(None) == 1
    assert resolve_workers(0) == 1
    assert resolve_workers(1) == 1
    assert resolve_workers(4) == 4
    assert resolve_workers("auto") >= 1


def test_auto_leaves_the_machine_half_free(monkeypatch):
    """This runs on the player's own device, so "auto" may not take the machine
    over. Half the cores is enough to converge: measured on 78 units, 8 workers
    reach exactly the same allocation damage as 15 (docs/decisions.md)."""
    for cores, expected in ((16, 8), (8, 4), (4, 2), (2, 1), (1, 1)):
        monkeypatch.setattr(sim_pool.os, "cpu_count", lambda c=cores: c)
        assert resolve_workers("auto") == expected


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


def test_pooled_results_match_serial_bit_for_bit():
    roster, boss = real_five_roster(), short_boss()
    decks = [list(roster), [roster[0], roster[1], roster[4], roster[3], roster[2]]]
    with SimPool(roster, boss, workers=None) as serial:
        expected_scores = serial.score_many(decks)
        expected_summaries = serial.summarize_many(decks)
    with SimPool(roster, boss, workers=2, spawn_threshold=1) as pooled:
        assert pooled.score_many(decks) == expected_scores
        assert pooled._executor is not None  # the pool really spawned
        assert pooled.summarize_many(decks) == expected_summaries


def test_small_batches_stay_inline_even_with_workers():
    roster, boss = real_five_roster(), short_boss()
    with SimPool(roster, boss, workers=2) as pool:  # default threshold 32
        pool.score_many([list(roster)])
        assert pool._executor is None


def test_a_warm_executor_serves_batches_too_small_to_have_started_it(monkeypatch):
    """The threshold's real cost is STARTING the executor - spawning processes
    and pickling the roster into each. Once one is running, a task is a
    five-slug tuple, so holding small batches back would leave the workers idle
    for no saving. The swap hill-climb depends on this: its deck-to-deck
    candidates come in batches of ~22, well under the threshold, and running
    those inline left them serial."""
    roster, boss = real_five_roster(), short_boss()
    decks = [list(roster), [roster[0], roster[1], roster[4], roster[3], roster[2]]]
    with SimPool(roster, boss, workers=None) as serial:
        expected = serial.score_many(decks)
    with SimPool(roster, boss, workers=2) as pool:
        pool.score_many([list(roster)] * 40)      # over the threshold: starts it
        assert pool._executor is not None
        # Only the inline path reaches this module's own binding; the workers
        # imported their own, so breaking it here proves where the batch ran.
        monkeypatch.setattr(sim_pool, "evaluate_deck", _inline_forbidden)
        assert pool.score_many(decks) == expected  # under it, but still pooled
