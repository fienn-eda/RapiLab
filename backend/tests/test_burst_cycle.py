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


def test_second_cycle_waits_for_the_slowest_tiers_cooldown_instead_of_missing():
    # tier1/tier2 only have ONE eligible Nikke each with a 20s cooldown, used
    # at t=5. Full Burst ends at t=15, so a fixed 5s gauge-charge gap would
    # want to fire the next cycle at t=20 - too early, since tier1/2 aren't
    # off cooldown until t=25. Per Fienn: gauge always finishes charging
    # before cooldowns do, so the scheduler should just wait until t=25
    # (the true bottleneck) rather than declaring the cycle missed - a
    # weaker deck cycles slower, it doesn't break.
    deck = make_deck()
    events = simulate_burst_cycle(deck, gauge_charge_time=5.0, fight_duration=35.0, mode="auto")

    assert not any(e["type"] == "full_burst_missed" for e in events)
    starts = [e["time"] for e in events if e["type"] == "full_burst_start"]
    assert starts == [5.0, 25.0]


def test_missing_a_burst_tier_entirely_is_reported_as_missed():
    # A deck with no Burst 1 member at all can never enter Full Burst no
    # matter how long it waits - this is the one case still a real "miss".
    deck = [
        {"slug": "b2_unit", "burst_tier": 2, "cooldown": 20.0},
        {"slug": "b3_unit", "burst_tier": 3, "cooldown": 40.0},
    ]
    events = simulate_burst_cycle(deck, gauge_charge_time=5.0, fight_duration=35.0, mode="auto")

    assert events == [{"type": "full_burst_missed", "time": 5.0}]


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
    # Without any reduction, the second cycle waits until tier1/2's 20s
    # cooldown clears at t=25 (see the test above). A 15s reduction applied
    # at t=15 pulls that up to t=10, which is earlier than the 5s gauge-charge
    # floor (t=20) - so the gauge floor becomes the new bottleneck and the
    # second cycle starts at t=20 instead. The hook returns a per-slug map.
    deck = make_deck()
    events = simulate_burst_cycle(
        deck, gauge_charge_time=5.0, fight_duration=35.0, mode="auto",
        on_full_burst_end=lambda time: {member["slug"]: 15.0 for member in deck},
    )
    assert events.count({"type": "full_burst_start", "time": 5.0}) == 1
    assert any(e["type"] == "full_burst_start" and e["time"] == 20.0 for e in events)
    assert not any(e["type"] == "full_burst_missed" for e in events)


def test_hooks_are_optional_and_default_to_no_op():
    deck = make_deck()
    # should not raise even though no hooks are supplied
    events = simulate_burst_cycle(deck, gauge_charge_time=5.0, fight_duration=20.0, mode="auto")
    assert len(events) > 0


def test_fractional_cooldown_reductions_never_strand_a_tier():
    # Regression: fractional CDR pulses (e.g. Little Mermaid's 7.48s) push
    # last_used_at to values where fire_time - last_used_at rounds to just
    # under the cooldown (51.44 - 31.44 = 19.999...996 < 20.0), so the very
    # member whose ready time DEFINED fire_time failed the eligibility check
    # and the scheduler crashed. Eligibility must use the same arithmetic as
    # tier_ready_time (last_used_at + cooldown <= fire_time).
    deck = [
        {"slug": "lm", "burst_tier": 1, "cooldown": 20.0},
        {"slug": "arcana", "burst_tier": 2, "cooldown": 40.0},
        {"slug": "grave", "burst_tier": 2, "cooldown": 20.0},
        {"slug": "drake", "burst_tier": 3, "cooldown": 40.0},
        {"slug": "modernia", "burst_tier": 3, "cooldown": 40.0},
    ]
    reductions = iter([13.48, 7.48, 13.48, 7.48, 13.48, 7.48, 13.48])

    def cdr(time):
        reduction = next(reductions, 0.0)
        return {member["slug"]: reduction for member in deck}

    events = simulate_burst_cycle(
        deck, gauge_charge_time=2.0, fight_duration=180.0, mode="manual",
        on_full_burst_end=cdr,
    )
    assert not any(e["type"] == "full_burst_missed" for e in events)
    assert sum(e["type"] == "full_burst_start" for e in events) >= 5


# --- Per-unit first-burst delay ----------------------------------------
# Some units are deliberately held back rather than fired the instant their
# cooldown allows: Diesel: Winter Sweets must skip the opening cycle so the
# Full Burst she does not burst into locks her into Highlight, and Elegg:
# Boom and Shock is held until her Ghosts reach the 13 cap. Both are
# expressed as a `burst_delay` on the deck member.


def test_skip_cycles_holds_a_unit_out_of_the_opening_cycle():
    deck = make_deck()
    deck[2]["burst_delay"] = {"skip_cycles": 1}

    events = simulate_burst_cycle(deck, gauge_charge_time=5.0, fight_duration=60.0, mode="auto")

    tier3 = [e["slug"] for e in events if e["type"] == "burst" and e["tier"] == 3]
    assert tier3[0] != "b3_unit_a"
    assert "b3_unit_a" in tier3


def test_not_before_holds_a_unit_until_its_time():
    deck = make_deck()
    deck[2]["burst_delay"] = {"not_before": 78.0}

    events = simulate_burst_cycle(deck, gauge_charge_time=5.0, fight_duration=180.0, mode="auto")

    fires = [e["time"] for e in events if e["type"] == "burst" and e["slug"] == "b3_unit_a"]
    assert fires
    assert min(fires) >= 78.0


def test_an_undelayed_tier_mate_still_covers_the_skipped_cycle():
    # The delay must not cost the deck a Full Burst - another member of the
    # tier fires in its place, so every cycle still completes.
    deck = make_deck()
    deck[2]["burst_delay"] = {"skip_cycles": 1}

    events = simulate_burst_cycle(deck, gauge_charge_time=5.0, fight_duration=60.0, mode="auto")

    assert not any(e["type"] == "full_burst_missed" for e in events)
    assert sum(e["type"] == "full_burst_start" for e in events) >= 3


def test_delay_applies_only_to_the_first_burst():
    # Once the unit has burst, it re-fires on its plain cooldown.
    deck = make_deck()
    deck[2]["burst_delay"] = {"skip_cycles": 1}

    events = simulate_burst_cycle(deck, gauge_charge_time=5.0, fight_duration=180.0, mode="auto")

    fires = [e["time"] for e in events if e["type"] == "burst" and e["slug"] == "b3_unit_a"]
    assert len(fires) >= 2
    assert all(b - a >= 40.0 for a, b in zip(fires, fires[1:]))


def test_a_delayed_unit_alone_in_its_tier_stalls_rather_than_bursting_early():
    # ALLOWED_SHAPES never builds a deck with a single Burst-3, so this only
    # reaches a hand-built deck. Stalling is the honest outcome: firing the
    # unit anyway would credit it a state it never entered.
    deck = [
        {"slug": "b1_unit", "burst_tier": 1, "cooldown": 20.0},
        {"slug": "b2_unit", "burst_tier": 2, "cooldown": 20.0},
        {"slug": "lone_b3", "burst_tier": 3, "cooldown": 40.0, "burst_delay": {"skip_cycles": 1}},
    ]

    events = simulate_burst_cycle(deck, gauge_charge_time=5.0, fight_duration=60.0, mode="auto")

    assert not any(e["type"] == "burst" for e in events)


def test_min_interval_stretches_a_units_effective_cooldown():
    # A unit held until a resource refills re-fires on the REFILL time, not
    # its cooldown, when the refill is the slower of the two (Elegg: her
    # burst spends 9 ghosts that come back at 6s each = 54s, against a 40s
    # cooldown).
    deck = make_deck()
    deck[2]["burst_delay"] = {"not_before": 78.0, "min_interval": 54.0}

    events = simulate_burst_cycle(deck, gauge_charge_time=2.0, fight_duration=180.0, mode="auto")

    fires = [e["time"] for e in events if e["type"] == "burst" and e["slug"] == "b3_unit_a"]
    assert fires[0] >= 78.0
    assert all(b - a >= 54.0 for a, b in zip(fires, fires[1:]))
    assert len(fires) == 2


def test_min_interval_below_the_cooldown_never_shortens_it():
    deck = make_deck()
    deck[2]["burst_delay"] = {"min_interval": 5.0}

    events = simulate_burst_cycle(deck, gauge_charge_time=5.0, fight_duration=180.0, mode="auto")

    fires = [e["time"] for e in events if e["type"] == "burst" and e["slug"] == "b3_unit_a"]
    assert all(b - a >= 40.0 for a, b in zip(fires, fires[1:]))


def test_min_interval_is_measured_from_the_real_fire_time_not_a_cdr_shifted_one():
    # Cooldown-reduction pulses rewind last_used_at, which is right for a
    # cooldown but wrong for a min_interval: Elegg's ghosts refill on wall
    # clock, and no ally's CDR makes them come back faster.
    deck = make_deck()
    deck[2]["burst_delay"] = {"min_interval": 54.0}

    events = simulate_burst_cycle(
        deck, gauge_charge_time=2.0, fight_duration=180.0, mode="auto",
        on_full_burst_end=lambda time: {member["slug"]: 10.0 for member in deck},
    )

    fires = [e["time"] for e in events if e["type"] == "burst" and e["slug"] == "b3_unit_a"]
    assert all(b - a >= 54.0 for a, b in zip(fires, fires[1:]))
