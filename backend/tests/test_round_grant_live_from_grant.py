"""A "for N round(s)" buff is live from the MOMENT IT IS GRANTED. The round
count says when it ENDS, not when it starts.

Fienn (in-game, 2026-08-18): the tactic is Miranda's "Critical Rate 85.42% for
1 round" landing on Marciana: Marine Study, whose Flagged Target Designation
nuke fires on the same "entering Full Burst" trigger - and the nuke DOES crit
under it. Two things had to be true and both are: the buff resolves before the
nuke, and a round-count buff applies to skill damage, not only to the bullet
that spends it.

The engine used to anchor the Effect at the recipient's first covered SHOT
instead, which is invisible for normal attacks - by construction there is no
shot of theirs between the grant and that one - and silently dropped everything
else in the gap.
"""
import pytest

from app.effects import RoundGrant
from app.raid_simulator import (
    _capped_round_grant_segments,
    _round_grant_shot_window,
    simulate_raid,
)
from app.skill_rules._helpers import buff_rule, instant_nuke_pulse_rule, round_buff_rule
from tests.test_raid_simulator import (
    _ar_weapon,
    fb_factor,
    make_base_stats,
    make_deck,
)

FIGHT = 100.0


def test_the_window_opens_at_the_grant_not_at_the_next_shot():
    # Granted at 1.5 with the recipient's next shot at 2.0: the 0.5 sec in
    # between is inside the buff.
    assert _round_grant_shot_window([1.0, 2.0, 3.0], 1.5, 1, [], FIGHT) == (1.5, 3.0)


def test_the_buff_is_still_held_between_the_grant_and_the_bullet_that_spends_it():
    # A round buff is spent BY a bullet, so between two bullets it is still
    # held - the whole gap belongs to it, however long the recipient idles.
    # Phantom's "Attack Damage for 1 round(s) on every normal attack" is
    # exactly this: it must be up when her burst fires between two of her shots.
    start, end = _round_grant_shot_window([2.0, 9.0, 9.5], 1.5, 1, [], FIGHT)
    assert (start, end) == (1.5, 9.0)
    assert start <= 5.0 < end   # idling between the grant and the next bullet
    assert start <= 2.0 < end   # and the bullet the buff was granted on


def test_which_shots_the_buff_covers_is_unchanged_by_the_new_anchor():
    # The whole point of the old anchor was that it made no difference to normal
    # attacks: no shot of the recipient's can fall between the grant and their
    # first covered shot. Same three shots covered, either way.
    start, end = _round_grant_shot_window([1.0, 2.0, 3.0, 4.0, 5.0], 1.5, 3, [], FIGHT)
    assert [t for t in [1.0, 2.0, 3.0, 4.0, 5.0] if start <= t < end] == [2.0, 3.0, 4.0]


def test_a_grant_the_recipient_never_fires_after_lasts_to_fight_end():
    # Nothing spends it, so nothing ends it. Previously this produced no Effect
    # at all, which also denied it to any skill damage in the meantime.
    assert _round_grant_shot_window([1.0], 2.0, 1, [], FIGHT) == (2.0, FIGHT)


def test_an_unlimited_window_still_ends_it_and_now_covers_the_gap_before_it():
    assert _round_grant_shot_window([5.0], 2.5, 1, [(2.0, 12.0)], FIGHT) == (2.5, 12.0)
    # ...including when no shot of theirs lands in the window at all: the buff
    # existed for those 9.5 sec even though no bullet carried it.
    assert _round_grant_shot_window([20.0], 2.5, 1, [(2.0, 12.0)], FIGHT) == (2.5, 12.0)


def test_a_nuke_on_the_same_trigger_as_the_grant_is_covered_by_it():
    # The Marciana shape: a Full-Burst-enter nuke on the recipient, and a
    # "for 1 round" buff granted by an ally on the same trigger. The nuke is
    # recorded at the instant of the grant, before the recipient's next bullet.
    grant = round_buff_rule("full_burst_enter", [("damage_taken_up", 0.5, "squad")], shots=1)
    nuke = instant_nuke_pulse_rule("full_burst_enter", 1000.0)
    result = simulate_raid(
        make_deck(),
        {"buffer": [grant], "midtier": [], "attacker": [nuke]},
        burst_damage_percents={},
        base_stats=make_base_stats(attacker_atk=10000),
        enemy_def=0,
        gauge_charge_time=5.0,
        fight_duration=8.0,
        mode="auto",
        base_crit_rate=0.0,
        weapon_stats={"attacker": _ar_weapon(max_ammo=1000)},
    )
    nukes = [e for e in result["damage_log"] if e["source"] == "instant_nuke"]
    assert len(nukes) == 1
    # 10000 ATK x 1000% = 100,000 before modifiers; the buff is +50% damage
    # taken, and the nuke lands inside the Full Burst window it opens on.
    assert nukes[0]["damage"] == pytest.approx(
        100_000.0 * 1.5 * fb_factor(result, nukes[0]["time"])
    )


def test_a_nuke_before_the_grant_is_not_covered_by_it():
    # The control: the same nuke fired at battle start, long before any grant,
    # must not pick the buff up. Guards against the window leaking backwards.
    grant = round_buff_rule("full_burst_enter", [("damage_taken_up", 0.5, "squad")], shots=1)
    nuke = instant_nuke_pulse_rule("battle_start", 1000.0)
    result = simulate_raid(
        make_deck(),
        {"buffer": [grant], "midtier": [], "attacker": [nuke]},
        burst_damage_percents={},
        base_stats=make_base_stats(attacker_atk=10000),
        enemy_def=0,
        gauge_charge_time=5.0,
        fight_duration=8.0,
        mode="auto",
        base_crit_rate=0.0,
        weapon_stats={"attacker": _ar_weapon(max_ammo=1000)},
    )
    nukes = [e for e in result["damage_log"] if e["source"] == "instant_nuke"]
    assert len(nukes) == 1
    assert nukes[0]["damage"] == pytest.approx(100_000.0)


def _entry(order, granted_at, value, start, end):
    grant = RoundGrant("pierce_damage_up", value, "squad", "granter", 1, granted_at,
                       cap=2, cap_group="g")
    return (order, grant, start, end)


def test_a_stack_cap_counts_what_is_held_AT_ONCE_not_what_overlaps_anywhere():
    # Three grants live together at t=3: the cap of 2 keeps the two newest, so
    # the oldest pays nothing there. Before the third lands, two are held and
    # both pay.
    entries = [
        _entry(0, 1.0, 0.25, 1.0, 10.0),
        _entry(1, 2.0, 0.25, 2.0, 10.0),
        _entry(2, 3.0, 0.25, 3.0, 10.0),
    ]
    assert _capped_round_grant_segments(entries, 2) == [
        (1.0, 2.0, 0.25),   # one held
        (2.0, 10.0, 0.50),  # two, then three - capped at two either way
    ]


def test_an_older_grant_squeezed_out_by_the_cap_comes_back_when_a_newer_expires():
    # The chain the per-grant rule got wrong: the oldest grant outlives the two
    # that pushed it out, so it is held again once they are gone. Dropping it
    # wholesale for being overlapped would lose that tail.
    entries = [
        _entry(0, 1.0, 0.25, 1.0, 9.0),
        _entry(1, 2.0, 0.25, 2.0, 4.0),
        _entry(2, 3.0, 0.25, 3.0, 5.0),
    ]
    assert _capped_round_grant_segments(entries, 2) == [
        (1.0, 2.0, 0.25),
        (2.0, 5.0, 0.50),
        (5.0, 9.0, 0.25),   # the oldest, alone again and still paying
    ]


def test_grants_sharing_an_instant_break_the_tie_by_grant_order():
    # Same granted_at, so "newest" has to fall back to the order they were
    # recorded in - otherwise which one the cap keeps is arbitrary.
    entries = [
        _entry(0, 1.0, 0.10, 1.0, 4.0),
        _entry(1, 1.0, 0.20, 1.0, 8.0),
    ]
    # 0.20 throughout, never 0.10: the later-recorded grant is the newer one.
    # The two segments carry the same total, so they merge into one Effect.
    assert _capped_round_grant_segments(entries, 1) == [(1.0, 8.0, 0.20)]
