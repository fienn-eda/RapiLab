import pytest

from app.deck_search import BossProfile
from app.burst_cycle import (
    FULL_BURST_DURATION,
    FULL_BURST_OPEN_DELAY,
    simulate_burst_cycle,
)


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
    # It OPENS one ordering step after the tier-3 cast, not at it - the Burst 3
    # fires, then Full Burst starts (see FULL_BURST_OPEN_DELAY).
    deck = make_deck()
    events = simulate_burst_cycle(deck, gauge_charge_time=5.0, fight_duration=20.0, mode="auto")

    start = next(e for e in events if e["type"] == "full_burst_start")
    end = next(e for e in events if e["type"] == "full_burst_end")
    assert start["time"] == 5.0 + FULL_BURST_OPEN_DELAY
    assert end["time"] == pytest.approx(15.0 + FULL_BURST_OPEN_DELAY)


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
    assert starts == [5.0 + FULL_BURST_OPEN_DELAY, 25.0 + FULL_BURST_OPEN_DELAY]


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
        on_full_burst_enter=lambda start, end: calls.append((start, end)),
    )
    assert calls == [(5.0 + FULL_BURST_OPEN_DELAY,
                      5.0 + FULL_BURST_OPEN_DELAY + FULL_BURST_DURATION)]


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
    assert events.count({"type": "full_burst_start",
                         "time": 5.0 + FULL_BURST_OPEN_DELAY}) == 1
    assert any(e["type"] == "full_burst_start"
               and e["time"] == pytest.approx(20.0 + FULL_BURST_OPEN_DELAY)
               for e in events)
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


def test_the_gauge_sets_the_steady_cycle_once_cooldowns_outrun_it():
    """Fienn's range run of Volume/Prika/Mint/Snow White: Heavy Arms/Cinderella
    (2026-07-27): 14 Full Bursts in 180 sec with the 14th at 2:57. Volume's
    cumulative cooldown reduction (up to 8.21 sec/cycle) outruns the gauge, so
    the rotation settles at `FULL_BURST_DURATION + gauge_charge_time + tier gap`.

    That law is what this test exercises. It does NOT pin the constant: this
    composition and the 7.48-sec-CDR one that sets the current value imply
    different gauges (14 Full Bursts here vs 15 there in the same 180 sec), which
    is the per-deck nature of the real gauge showing through - it fills from
    damage dealt. The constant follows the faster measurement, so this deck is
    modelled with one cycle more than it ran.

    Here that law is exercised directly: cooldowns short enough to never bind,
    so every cycle is gauge-bound.
    """
    deck = [
        {"slug": "b1", "burst_tier": 1, "cooldown": 1.0},
        {"slug": "b2", "burst_tier": 2, "cooldown": 1.0},
        {"slug": "b3", "burst_tier": 3, "cooldown": 1.0},
    ]
    gauge = BossProfile.gauge_charge_time
    events = simulate_burst_cycle(deck, gauge_charge_time=gauge,
                                  fight_duration=100.0, mode="manual")
    starts = [e["time"] for e in events if e["type"] == "full_burst_start"]
    gaps = [b - a for a, b in zip(starts, starts[1:])]
    assert gaps, "expected more than one cycle"
    assert all(g == pytest.approx(FULL_BURST_DURATION + gauge + 0.2) for g in gaps)


def test_gauge_charge_time_matches_the_measurement_it_is_derived_from():
    # It is a per-DECK quantity modelled as one constant, so a change needs an
    # argument rather than a preference. This value has one: a CDR deck driven
    # as fast as the gauge allows opens its 15th Full Burst at t~179, which
    # solves to 2.4 (the arithmetic lives in
    # test_default_gauge_reproduces_the_measured_fifteenth_full_burst).
    #
    # Two measured compositions do NOT agree - the Volume run above implies a
    # slower gauge - so this sits at the fast end of what has been measured.
    # That end is the one that invents the fewest constraints for decks whose
    # gauge never binds, which is the same principle as before; what changed is
    # which number that principle picks now that a fast deck has been timed.
    assert BossProfile.gauge_charge_time == 2.4


# --- Seats whose burst the player never spends -------------------------
# A "totem" is seated for its passive kit and never bursts, and a unit can be
# burst once and then held for the rest of the fight (Fienn's recorded raid:
# Helm and Mihara are totems; Prika bursts only the opening cycle, after which
# Mint takes the tier-2 seat). That is a choice made in the run, not a property
# of the unit, so it arrives as `max_bursts` on the deck member.


def test_a_totem_seat_never_bursts():
    deck = make_deck()
    deck[2]["max_bursts"] = 0

    events = simulate_burst_cycle(deck, gauge_charge_time=5.0, fight_duration=180.0, mode="auto")

    assert not any(e["type"] == "burst" and e["slug"] == "b3_unit_a" for e in events)


def test_a_totems_tier_mates_still_carry_the_cycle():
    deck = make_deck()
    deck[2]["max_bursts"] = 0

    events = simulate_burst_cycle(deck, gauge_charge_time=5.0, fight_duration=180.0, mode="auto")

    tier3 = [e["slug"] for e in events if e["type"] == "burst" and e["tier"] == 3]
    assert not any(e["type"] == "full_burst_missed" for e in events)
    assert set(tier3) == {"b3_unit_b", "flex_unit"}


def test_max_bursts_of_one_fires_the_opening_cycle_and_then_never_again():
    deck = make_deck()
    deck[2]["max_bursts"] = 1

    events = simulate_burst_cycle(deck, gauge_charge_time=5.0, fight_duration=180.0, mode="auto")

    fires = [e["time"] for e in events if e["type"] == "burst" and e["slug"] == "b3_unit_a"]
    assert fires == [5.0]


def test_a_tier_of_nothing_but_totems_stalls_rather_than_bursting_one_anyway():
    # Firing a held burst would credit the deck a Full Burst it never had - the
    # same reasoning as a delayed unit alone in its tier.
    deck = make_deck()
    for member in deck:
        if member["burst_tier"] == 3:
            member["max_bursts"] = 0

    events = simulate_burst_cycle(deck, gauge_charge_time=5.0, fight_duration=60.0, mode="auto")

    assert not any(e["type"] == "burst" for e in events)


def test_a_totem_does_not_shorten_the_wait_for_a_tier_mate_on_cooldown():
    # b3_unit_a is a totem, so the tier's readiness is b3_unit_b's alone: the
    # second Full Burst waits a full 40 sec instead of being covered.
    deck = make_deck()
    deck[2]["max_bursts"] = 0
    deck[4]["max_bursts"] = 0

    events = simulate_burst_cycle(deck, gauge_charge_time=5.0, fight_duration=180.0, mode="auto")

    fires = [e["time"] for e in events if e["type"] == "burst" and e["tier"] == 3]
    assert all(e == "b3_unit_b" for e in
               [x["slug"] for x in events if x["type"] == "burst" and x["tier"] == 3])
    assert all(b - a >= 40.0 for a, b in zip(fires, fires[1:]))


# A Nikke can also take herself out of the rotation: Mast: Romantic Maid's
# Hangover stuns HER for 10 sec at the end of every third Full Burst when no
# Anchor is there to clear her Drunken stacks. That is not a `burst_delay` -
# it recurs, and it starts from an event mid-fight rather than from the opening.
def test_a_self_stun_holds_a_member_out_of_the_cycles_it_covers():
    """Fienn, 2026-08-04: in deck 4, 2 of Mast's 8 bursts landed inside a stun
    window the scheduler knew nothing about. A stunned member cannot burst - a
    tier-mate covers, and with no tier-mate the cycle waits for her."""
    deck = [
        {"slug": "b1_unit", "burst_tier": 1, "cooldown": 5.0},
        {"slug": "drunk", "burst_tier": 2, "cooldown": 5.0,
         "self_stun": {"seconds": 10.0, "cycles": 2}},
        {"slug": "sober", "burst_tier": 2, "cooldown": 5.0},
        {"slug": "b3_a", "burst_tier": 3, "cooldown": 5.0},
        {"slug": "b3_b", "burst_tier": 3, "cooldown": 5.0},
    ]
    events = simulate_burst_cycle(deck, gauge_charge_time=1.0, fight_duration=60.0,
                                  mode="auto")

    ends = [e["time"] for e in events if e["type"] == "full_burst_end"]
    b2 = [(e["time"], e["slug"]) for e in events if e["type"] == "burst" and e["tier"] == 2]
    # Every second Full Burst leaves her stunned for the 10 sec after it.
    windows = [(end, end + 10.0) for end in ends[1::2]]
    assert windows, "fixture must run long enough to stun her at all"
    assert not [t for t, slug in b2 if slug == "drunk"
                and any(a <= t < b for a, b in windows)]
    # ...and the tier keeps firing, because her tier-mate covers those cycles.
    assert len(b2) == len(ends)


# --- What sets the default gauge charge time ---------------------------


def test_default_gauge_reproduces_the_measured_fifteenth_full_burst():
    """실측(Fienn, 2026-08-05): CDR 7.48초 유닛이 든 덱을 게이지 충전까지
    최대한 빠르게 컨트롤하면 **15번째 풀버스트가 t≈179**에 열린다.

    게이지가 병목일 때 사이클 간격은 CDR과 무관하게
    `FULL_BURST_DURATION + gauge + 티어갭`이 되므로, 그 한 시각이 기본
    게이지를 유일하게 결정한다 - 그래서 이 테스트가 곧
    `BossProfile.gauge_charge_time`의 근거다. 값을 바꾸면 여기서 걸리고,
    걸리면 실측을 다시 봐야 한다.

    쿨다운을 1초로 둔 것은 게이지 말고는 아무것도 병목이 되지 않게 하기
    위해서다. 실제 덱에서 CDR이 클수록 이 조건에 가까워진다.
    """
    deck = [{"slug": f"u{tier}", "burst_tier": tier, "cooldown": 1.0}
            for tier in (1, 2, 3)]

    events = simulate_burst_cycle(
        deck, gauge_charge_time=BossProfile().gauge_charge_time,
        fight_duration=180.0, mode="manual")

    starts = [e["time"] for e in events if e["type"] == "full_burst_start"]
    assert len(starts) == 15
    assert starts[-1] == pytest.approx(179.0, abs=0.1)


def _deck_with_two_b3(delta_a=None, delta_b=None):
    """b3_unit_a와 b3_unit_b가 사이클마다 번갈아 티어 3을 맡는 덱."""
    a = {"slug": "b3_unit_a", "burst_tier": 3, "cooldown": 40.0}
    b = {"slug": "b3_unit_b", "burst_tier": 3, "cooldown": 40.0}
    if delta_a is not None:
        a["full_burst_duration_delta"] = delta_a
    if delta_b is not None:
        b["full_burst_duration_delta"] = delta_b
    return [
        {"slug": "b1_unit", "burst_tier": 1, "cooldown": 20.0},
        {"slug": "b2_unit", "burst_tier": 2, "cooldown": 20.0},
        a,
        b,
    ]


def _windows(events):
    return list(zip(
        (e["time"] for e in events if e["type"] == "full_burst_start"),
        (e["time"] for e in events if e["type"] == "full_burst_end"),
    ))


def test_full_burst_window_shortens_for_a_tier3_that_cuts_it():
    deck = _deck_with_two_b3(delta_a=-5.0)
    events = simulate_burst_cycle(deck, gauge_charge_time=5.0, fight_duration=20.0, mode="auto")

    start, end = _windows(events)[0]
    assert end - start == pytest.approx(5.0)


def test_full_burst_window_lengthens_for_a_tier3_that_extends_it():
    deck = _deck_with_two_b3(delta_a=5.0)
    events = simulate_burst_cycle(deck, gauge_charge_time=5.0, fight_duration=25.0, mode="auto")

    start, end = _windows(events)[0]
    assert end - start == pytest.approx(15.0)


def test_each_cycle_takes_the_length_of_whichever_burst3_opened_it():
    # 티어 3이 둘이고 쿨다운이 40초라 사이클마다 번갈아 연다. 창 길이는 사이클의
    # 속성이 아니라 그 사이클을 연 유닛의 속성이다.
    deck = _deck_with_two_b3(delta_a=-5.0)
    events = simulate_burst_cycle(deck, gauge_charge_time=5.0, fight_duration=60.0, mode="auto")

    lengths = [round(end - start, 6) for start, end in _windows(events)[:2]]
    assert lengths == [5.0, 10.0]


def test_a_delta_below_the_base_duration_gives_a_zero_length_window_not_a_negative_one():
    # 음수 길이의 창은 아래의 모든 `start <= t < end` 검사를 조용히 뒤집는다.
    deck = _deck_with_two_b3(delta_a=-25.0)
    events = simulate_burst_cycle(deck, gauge_charge_time=5.0, fight_duration=20.0, mode="auto")

    start, end = _windows(events)[0]
    assert end - start == pytest.approx(0.0)


def test_a_member_without_a_delta_keeps_the_base_duration():
    deck = _deck_with_two_b3()
    events = simulate_burst_cycle(deck, gauge_charge_time=5.0, fight_duration=20.0, mode="auto")

    start, end = _windows(events)[0]
    assert end - start == pytest.approx(FULL_BURST_DURATION)
