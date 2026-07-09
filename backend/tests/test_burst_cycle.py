from app.burst_cycle import simulate_burst_cycle


def make_deck():
    # 1x burst1, 1x burst2, 2x burst3 - the standard composition Fienn described.
    return [
        {"slug": "b1_unit", "burst_tier": 1, "cooldown": 20.0},
        {"slug": "b2_unit", "burst_tier": 2, "cooldown": 20.0},
        {"slug": "b3_unit_a", "burst_tier": 3, "cooldown": 40.0},
        {"slug": "b3_unit_b", "burst_tier": 3, "cooldown": 40.0},
        {"slug": "flex_unit", "burst_tier": 3, "cooldown": 40.0},
    ]


def test_first_cycle_fires_all_three_tiers_in_order():
    deck = make_deck()
    events = simulate_burst_cycle(deck, gauge_charge_time=5.0, fight_duration=20.0, mode="auto")

    bursts = [e for e in events if e["type"] == "burst"]
    assert [e["tier"] for e in bursts] == [1, 2, 3]
    assert all(e["time"] == 5.0 for e in bursts)


def test_full_burst_window_lasts_ten_seconds_after_tier3():
    deck = make_deck()
    events = simulate_burst_cycle(deck, gauge_charge_time=5.0, fight_duration=20.0, mode="auto")

    start = next(e for e in events if e["type"] == "full_burst_start")
    end = next(e for e in events if e["type"] == "full_burst_end")
    assert start["time"] == 5.0
    assert end["time"] == 15.0


def test_manual_mode_adds_gap_between_tiers():
    deck = make_deck()
    events = simulate_burst_cycle(deck, gauge_charge_time=5.0, fight_duration=20.0, mode="manual")

    bursts = [e for e in events if e["type"] == "burst"]
    assert [round(e["time"], 2) for e in bursts] == [5.0, 5.1, 5.2]


def test_leftmost_eligible_nikke_of_a_tier_is_chosen():
    deck = make_deck()
    events = simulate_burst_cycle(deck, gauge_charge_time=5.0, fight_duration=20.0, mode="auto")

    tier3_event = next(e for e in events if e["type"] == "burst" and e["tier"] == 3)
    assert tier3_event["slug"] == "b3_unit_a"


def test_second_cycle_alternates_to_other_tier3_unit_once_first_is_on_cooldown():
    # tier1/tier2 cooldowns shortened so this test isolates tier3 alternation
    # specifically, independent of the tier1/2 bottleneck covered below.
    deck = make_deck()
    deck[0]["cooldown"] = 5.0
    deck[1]["cooldown"] = 5.0
    # long enough for two cycles: 5s charge + 10s full burst = 15s per cycle
    events = simulate_burst_cycle(deck, gauge_charge_time=5.0, fight_duration=35.0, mode="auto")

    tier3_events = [e for e in events if e["type"] == "burst" and e["tier"] == 3]
    assert [e["slug"] for e in tier3_events] == ["b3_unit_a", "b3_unit_b"]


def test_cycle_fails_without_cooldown_reduction_when_only_one_nikke_per_low_tier():
    # tier1/tier2 only have ONE eligible Nikke each with a 20s cooldown.
    # cycle length is 15s (5s charge + 10s full burst), but the tier1/2 Nikke's
    # cooldown (20s) hasn't elapsed by the time the second cycle wants to fire -
    # this is exactly why Fienn said a burst-cooldown-reduction Nikke is required.
    deck = make_deck()
    events = simulate_burst_cycle(deck, gauge_charge_time=5.0, fight_duration=35.0, mode="auto")

    assert any(e["type"] == "full_burst_missed" for e in events)
    # only one full cycle completes before the miss
    assert len([e for e in events if e["type"] == "full_burst_start"]) == 1


def test_fight_duration_shorter_than_first_charge_produces_no_bursts():
    deck = make_deck()
    events = simulate_burst_cycle(deck, gauge_charge_time=5.0, fight_duration=3.0, mode="auto")
    assert events == []


def test_on_battle_start_hook_fires_once_at_time_zero():
    deck = make_deck()
    calls = []
    simulate_burst_cycle(
        deck, gauge_charge_time=5.0, fight_duration=20.0, mode="auto",
        on_battle_start=lambda time: calls.append(time),
    )
    assert calls == [0.0]


def test_on_tier_fire_hook_fires_for_each_burst_with_slug_and_time():
    deck = make_deck()
    calls = []
    simulate_burst_cycle(
        deck, gauge_charge_time=5.0, fight_duration=20.0, mode="auto",
        on_tier_fire=lambda tier, slug, time: calls.append((tier, slug, time)),
    )
    assert calls == [
        (1, "b1_unit", 5.0),
        (2, "b2_unit", 5.0),
        (3, "b3_unit_a", 5.0),
    ]


def test_on_full_burst_enter_hook_fires_at_tier3_time():
    deck = make_deck()
    calls = []
    simulate_burst_cycle(
        deck, gauge_charge_time=5.0, fight_duration=20.0, mode="auto",
        on_full_burst_enter=lambda time: calls.append(time),
    )
    assert calls == [5.0]


def test_on_full_burst_end_hook_return_value_reduces_all_cooldowns():
    # tier1/tier2 have only one eligible Nikke each with a 20s cooldown, so
    # without cooldown reduction the second cycle would miss (see the
    # dedicated failure test above). A 15s reduction from the hook should be
    # enough to let the second cycle's tier1/tier2 fire on time.
    deck = make_deck()
    events = simulate_burst_cycle(
        deck, gauge_charge_time=5.0, fight_duration=35.0, mode="auto",
        on_full_burst_end=lambda time: 15.0,
    )
    assert events.count({"type": "full_burst_start", "time": 5.0}) == 1
    assert any(e["type"] == "full_burst_start" and e["time"] == 20.0 for e in events)
    assert not any(e["type"] == "full_burst_missed" for e in events)


def test_hooks_are_optional_and_default_to_no_op():
    deck = make_deck()
    # should not raise even though no hooks are supplied
    events = simulate_burst_cycle(deck, gauge_charge_time=5.0, fight_duration=20.0, mode="auto")
    assert len(events) > 0
