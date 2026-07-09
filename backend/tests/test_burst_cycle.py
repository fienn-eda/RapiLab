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
