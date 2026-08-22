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


def _tier1_bursts(events):
    return [e for e in events if e["type"] == "burst" and e["tier"] == 1]


def test_a_cycle_is_gauge_bound_only_when_the_gauge_opens_after_every_cooldown():
    """`gauge_bound`은 그 사이클의 발동 시각을 **게이지가 정했는가**다.

    쿨다운 1초짜리 덱은 창이 닫히자마자 준비되므로 게이지가 늦고, 40초짜리
    덱은 게이지가 아무리 빨라도 쿨다운을 못 이긴다. 두 방향을 같이 재는 이유는
    한쪽만 재면 상수를 돌려주는 구현이 통과하기 때문이다.
    """
    def flags(cooldown):
        deck = [{"slug": f"u{tier}", "burst_tier": tier, "cooldown": cooldown}
                for tier in (1, 2, 3)]
        return [e["gauge_bound"] for e in _tier1_bursts(simulate_burst_cycle(
            deck, gauge_charge_time=5.0, fight_duration=60.0, mode="auto"))]

    assert all(flags(1.0)), "쿨은 다 돌았고 게이지만 남았으면 게이지가 민 것이다"
    # 첫 사이클은 예외 없이 게이지가 정한다 - 돌고 있던 쿨다운이 없다.
    assert flags(40.0)[0] is True
    assert not any(flags(40.0)[1:]), "쿨다운이 더 늦으면 게이지는 아무것도 안 밀었다"


def test_a_cycle_the_gauge_and_the_cooldown_open_together_is_not_gauge_bound():
    """**동점은 밀림이 아니다** - 게이지가 없었어도 그 사이클은 같은 시각에
    터졌으므로 아무것도 밀리지 않았다.

    동점을 손으로 만든다: 사이클 0은 t=GAUGE에 터지고 그 창은
    `OPEN_DELAY + DURATION` 뒤에 닫히므로 사이클 1의 게이지 준비 시각은
    거기서 다시 GAUGE 뒤다. 쿨다운을 그 시각에 **정확히** 맞춘다.

    동점이 실제로 성립했는지는 **시뮬레이션을 읽어** 확인한다 - 아래
    `second["time"] == gauge_ready`가 그 자리다. 손으로 세운
    `gauge + cooldown == gauge_ready`를 단언하는 것은 구성상 참이라 아무것도 안
    잰다: `cooldown`을 그 차이로 정의했기 때문이다.
    """
    gauge = 5.0
    end_of_opening_window = (gauge + FULL_BURST_OPEN_DELAY) + FULL_BURST_DURATION
    gauge_ready = end_of_opening_window + gauge
    cooldown = gauge_ready - gauge

    deck = [{"slug": f"u{tier}", "burst_tier": tier, "cooldown": cooldown}
            for tier in (1, 2, 3)]
    events = simulate_burst_cycle(deck, gauge_charge_time=gauge,
                                  fight_duration=60.0, mode="auto")

    second = _tier1_bursts(events)[1]
    assert second["time"] == gauge_ready, "동점이면 발동 시각은 어느 쪽으로 봐도 같다"
    assert second["gauge_bound"] is False
    # 밀리지 않았으므로 지연도 0이다 - 음수(「쿨다운이 몇 초 이겼는가」)를 실으면
    # 합계에서 진짜 밀림을 상쇄해 없애 버린다.
    assert second["gauge_delay"] == 0.0


def test_gauge_delay_separates_two_decks_that_are_bound_the_same_number_of_cycles():
    """**개수는 크기를 말하지 않는다.** 이 변경의 요점이고, 개수만 보는 픽스처로는
    옛 구현도 통과하므로 한 테스트 안에서 둘을 갈라야 한다.

    쿨다운만 다른 두 덱을 쓴다. 게이지가 사이클을 정하는 한 사이클 길이는
    `게이지 + 창`이라 **쿨다운과 무관**하고, 그래서 두 덱의 사이클 수도 밀린
    사이클 수도 같다. 밀린 **시간**만 `창 + 게이지 - 쿨다운`으로 갈린다:
    쿨다운 1초짜리는 사이클마다 14초씩, 14초짜리는 1초씩 민다.

    실측에서 이것이 덱 1(11사이클·4.3초, 판독 「안 밀림」)과 덱 3(11사이클·
    11.6초, 판독 「밀림」)을 가르는 축이다.
    """
    gauge = 5.0
    per_cycle = FULL_BURST_OPEN_DELAY + FULL_BURST_DURATION + gauge

    def bound_and_delay(cooldown):
        deck = [{"slug": f"u{tier}", "burst_tier": tier, "cooldown": cooldown}
                for tier in (1, 2, 3)]
        after_opening = _tier1_bursts(simulate_burst_cycle(
            deck, gauge_charge_time=gauge, fight_duration=60.0, mode="auto"))[1:]
        return (sum(1 for e in after_opening if e["gauge_bound"]),
                sum(e["gauge_delay"] for e in after_opening),
                len(after_opening))

    short_cd = bound_and_delay(1.0)
    long_cd = bound_and_delay(14.0)

    assert short_cd[2] == long_cd[2] > 0, "사이클 수가 같아야 비교가 성립한다"
    assert short_cd[0] == long_cd[0] == short_cd[2], "밀린 사이클 수도 같다"
    assert short_cd[1] > long_cd[1], "그런데 밀린 시간은 다르다 - 이것이 판별한다"
    assert long_cd[1] == pytest.approx(long_cd[2] * (per_cycle - 14.0))
    assert short_cd[1] == pytest.approx(short_cd[2] * (per_cycle - 1.0))


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


def test_a_lone_delayed_burst_three_reports_a_miss_instead_of_falling_silent():
    """A `skip_cycles` delay on the ONLY member of its tier is unsatisfiable:
    the cycle it skips is the cycle that would have advanced the counter, so
    the delay never lifts and no Full Burst ever opens.

    That is the same dead end as a missing tier - no amount of waiting fixes
    it - and it must be reported the same way. Reaching `fight_duration` with
    an infinite ready-time used to leave through the ordinary end-of-fight
    branch, so the whole simulation returned an EMPTY event list and a caller
    could not tell a deck that cannot Full Burst from a fight that simply
    ended. `evaluate_deck` scored such a deck at a fraction of its real damage
    with no complaint (Diesel: Winter Sweets in Highlight, measured 2026-08-07).
    """
    deck = [
        {"slug": "b1_unit", "burst_tier": 1, "cooldown": 20.0},
        {"slug": "b2_unit", "burst_tier": 2, "cooldown": 20.0},
        {"slug": "lone_b3", "burst_tier": 3, "cooldown": 40.0,
         "burst_delay": {"skip_cycles": 1}},
    ]

    events = simulate_burst_cycle(deck, gauge_charge_time=5.0, fight_duration=180.0,
                                  mode="auto")

    assert events == [{"type": "full_burst_missed", "time": 5.0}]


def test_a_lone_totem_burst_three_reports_the_same_miss():
    """`max_bursts: 0` takes the seat out of its tier permanently, which is the
    same dead end reached a different way."""
    deck = [
        {"slug": "b1_unit", "burst_tier": 1, "cooldown": 20.0},
        {"slug": "b2_unit", "burst_tier": 2, "cooldown": 20.0},
        {"slug": "totem_b3", "burst_tier": 3, "cooldown": 40.0, "max_bursts": 0},
    ]

    events = simulate_burst_cycle(deck, gauge_charge_time=5.0, fight_duration=180.0,
                                  mode="auto")

    assert events == [{"type": "full_burst_missed", "time": 5.0}]


def test_a_fight_that_simply_runs_out_of_time_is_not_a_miss():
    """The other side of the same branch: a deck that CAN Full Burst but whose
    fight ends first is not a miss, and must stay silent as before."""
    deck = make_deck()

    events = simulate_burst_cycle(deck, gauge_charge_time=5.0, fight_duration=4.0,
                                  mode="auto")

    assert events == []


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


def test_default_gauge_is_the_first_pass_seed_not_the_encounter_value():
    """게이지는 이제 덱에서 계산된다(docs/measurements/burst-gauge-fill.md 및
    `burst_gauge.fill_times`). 이 상수가 정하는 것은 **첫 패스가 어디서
    출발하는가**뿐이고, `simulate_raid`의 고정점이 그 위에서 실제 값을 찾는다.

    값 자체는 CDR 편성의 15번째 풀버스트 t~179에서 역산한 것이라(산술은
    test_default_gauge_reproduces_the_measured_fifteenth_full_burst) 출발점으로
    여전히 합리적이다. 실측된 두 편성이 서로 다른 게이지를 함의한다는 사실 -
    예전에는 이 상수를 어느 쪽으로 놓을지의 딜레마였던 것 - 이 곧 게이지가
    보스가 아니라 덱의 양이라는 증거였다.
    """
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


def test_full_burst_duration_overrides_lengthen_named_cycles():
    """사이클별 오버라이드는 그 사이클의 창 길이에만 더해진다 - 소다의
    Beginner's Rewards처럼 값이 사이클마다 다른 확장을 위한 자리."""
    deck = [
        {"slug": "b1", "burst_tier": 1, "cooldown": 20.0},
        {"slug": "b2", "burst_tier": 2, "cooldown": 20.0},
        {"slug": "b3", "burst_tier": 3, "cooldown": 20.0},
    ]
    events = simulate_burst_cycle(
        deck, gauge_charge_time=5.0, fight_duration=100.0,
        full_burst_duration_overrides={0: 5.0, 2: 2.0},
    )
    windows = list(zip(
        [e["time"] for e in events if e["type"] == "full_burst_start"],
        [e["time"] for e in events if e["type"] == "full_burst_end"],
    ))
    lengths = [round(end - start, 6) for start, end in windows]
    assert lengths[0] == 15.0    # 10 + 5
    assert lengths[1] == 10.0    # 오버라이드 없음
    assert lengths[2] == 12.0    # 10 + 2


def test_full_burst_duration_overrides_add_to_the_tier3_units_own_delta():
    """오버라이드는 기존 유닛별 델타(이사벨 -5, 모더니아 +5)를 대체하지 않고
    더한다 - 둘은 다른 조건이라 겹쳐 걸린다."""
    deck = [
        {"slug": "b1", "burst_tier": 1, "cooldown": 20.0},
        {"slug": "b2", "burst_tier": 2, "cooldown": 20.0},
        {"slug": "shortener", "burst_tier": 3, "cooldown": 20.0,
         "full_burst_duration_delta": -5.0},
    ]
    events = simulate_burst_cycle(
        deck, gauge_charge_time=5.0, fight_duration=60.0,
        full_burst_duration_overrides={0: 5.0},
    )
    start = next(e["time"] for e in events if e["type"] == "full_burst_start")
    end = next(e["time"] for e in events if e["type"] == "full_burst_end")
    assert round(end - start, 6) == 10.0    # 10 - 5 + 5


def test_no_overrides_is_todays_behaviour():
    """None이면 오늘과 같다 - 조건부 델타가 없는 덱의 불변식."""
    deck = [
        {"slug": "b1", "burst_tier": 1, "cooldown": 20.0},
        {"slug": "b2", "burst_tier": 2, "cooldown": 20.0},
        {"slug": "b3", "burst_tier": 3, "cooldown": 20.0},
    ]
    with_none = simulate_burst_cycle(deck, 5.0, 100.0, full_burst_duration_overrides=None)
    without = simulate_burst_cycle(deck, 5.0, 100.0)
    assert with_none == without


def test_gauge_charge_overrides_change_named_cycles_only():
    """사이클별 게이지는 그 사이클의 하한에만 걸린다 - 게이지가 덱 속성이고
    재장전 위치에 따라 사이클마다 다르기 때문이다(docs/measurements/burst-gauge-fill.md).

    쿨다운을 1초로 두어 게이지가 항상 병목이게 만든다. 그러면 사이클 간격이
    곧 `FULL_BURST_DURATION + 그 사이클의 게이지 + 티어갭`이다.
    """
    deck = [
        {"slug": "b1", "burst_tier": 1, "cooldown": 1.0},
        {"slug": "b2", "burst_tier": 2, "cooldown": 1.0},
        {"slug": "b3", "burst_tier": 3, "cooldown": 1.0},
    ]
    events = simulate_burst_cycle(
        deck, gauge_charge_time=2.4, fight_duration=100.0, mode="manual",
        gauge_charge_overrides={1: 5.0},
    )
    starts = [e["time"] for e in events if e["type"] == "full_burst_start"]
    gaps = [round(b - a, 6) for a, b in zip(starts, starts[1:])]
    # 사이클 1의 게이지가 5.0이므로 사이클 0의 풀버스트 종료 -> 사이클 1 버스트의 간격만 길다.
    assert gaps[0] == pytest.approx(FULL_BURST_DURATION + 5.0 + 0.2)
    assert gaps[1] == pytest.approx(FULL_BURST_DURATION + 2.4 + 0.2)
    assert gaps[2] == pytest.approx(FULL_BURST_DURATION + 2.4 + 0.2)


def test_empty_gauge_overrides_are_todays_behaviour():
    deck = [
        {"slug": "b1", "burst_tier": 1, "cooldown": 1.0},
        {"slug": "b2", "burst_tier": 2, "cooldown": 1.0},
        {"slug": "b3", "burst_tier": 3, "cooldown": 1.0},
    ]
    without = simulate_burst_cycle(deck, gauge_charge_time=2.4, fight_duration=100.0,
                                   mode="manual")
    with_empty = simulate_burst_cycle(deck, gauge_charge_time=2.4, fight_duration=100.0,
                                      mode="manual", gauge_charge_overrides={})
    assert without == with_empty
