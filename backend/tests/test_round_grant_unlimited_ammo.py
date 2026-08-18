"""A "for N round(s)" buff counts AMMUNITION SPENT, not shots fired.

[Unlimited Ammunition] makes a shot spend nothing, so a round-count buff on a
unit under it does not tick down - it survives the whole window and is consumed
when the window ends (Fienn, in-game 2026-08-18: Miranda's "Critical Rate
85.42% for 1 round" stays on Nayuta and Grave). The rule is the status's, not
Miranda's: every "for N round(s)" buff behaves this way.
"""
import pytest

from app.raid_simulator import (
    ROUND_GRANT_EPSILON,
    _round_grant_shot_window,
    simulate_raid,
)
from app.skill_rules._helpers import round_buff_rule
from app.skill_rules.registry import get_unlimited_ammo_duration
from tests.test_raid_simulator import (
    _ar_weapon,
    fb_factor,
    make_base_stats,
    make_deck,
)

FIGHT = 100.0


def test_without_a_window_the_next_shot_still_ends_a_one_round_buff():
    # The ordinary rule: live from the grant, ended by the Nth spending bullet,
    # which it still covers.
    shots = [1.0, 2.0, 3.0, 4.0]
    eps = ROUND_GRANT_EPSILON
    assert _round_grant_shot_window(shots, 1.5, 1, [], FIGHT) == (1.5, 2.0 + eps)
    assert _round_grant_shot_window(shots, 1.5, 2, [], FIGHT) == (1.5, 3.0 + eps)


def test_without_a_window_a_buff_that_outlives_the_shots_runs_to_fight_end():
    assert _round_grant_shot_window([1.0], 0.0, 3, [], FIGHT) == (0.0, FIGHT)


def test_a_grant_that_reaches_no_shot_of_theirs_still_exists():
    # Nothing of theirs spends it, so nothing ends it before the fight does.
    # It used to produce no Effect at all, which also denied it to any skill
    # damage of theirs in the meantime.
    assert _round_grant_shot_window([1.0, 2.0], 5.0, 1, [], FIGHT) == (5.0, FIGHT)


def test_shots_inside_an_unlimited_window_do_not_spend_the_buff():
    # Granted at 2.5 inside [2.0, 12.0): none of the four shots in the window
    # spends a round, so the buff lives to the window's end instead of dying on
    # the shot at 4.0.
    shots = [1.0, 3.0, 4.0, 5.0, 6.0, 20.0]
    assert _round_grant_shot_window(shots, 2.5, 1, [(2.0, 12.0)], FIGHT) == (2.5, 12.0)


def test_the_buff_is_consumed_when_the_unlimited_window_ends():
    # No shot at all between the last in-window shot and the window's end - the
    # end itself consumes it, so it does not coast on to the next shot.
    shots = [3.0, 50.0]
    assert _round_grant_shot_window(shots, 2.5, 1, [(2.0, 12.0)], FIGHT) == (2.5, 12.0)


def test_a_count_frozen_by_a_later_window_resumes_nowhere():
    # Granted OUTSIDE the window with 3 rounds to spend: the shot at 1.0 spends
    # one, the window then freezes the count, and its end consumes what is left
    # rather than handing the rest back.
    shots = [1.0, 5.0, 6.0, 7.0, 30.0]
    assert _round_grant_shot_window(shots, 0.5, 3, [(4.0, 12.0)], FIGHT) == (0.5, 12.0)


def test_a_buff_already_spent_before_the_window_is_untouched_by_it():
    shots = [1.0, 2.0, 5.0]
    assert _round_grant_shot_window(shots, 0.5, 1, [(4.0, 12.0)], FIGHT) == (
        0.5, 1.0 + ROUND_GRANT_EPSILON)


def test_a_window_ending_before_their_first_shot_still_covers_the_window():
    # No bullet of theirs carries it, but the buff was live for those 9.5 sec
    # and their skill damage in them is under it. It ends at 12.0 all the same -
    # extending it to the shot at 20.0 would resurrect a spent buff.
    assert _round_grant_shot_window([20.0], 2.5, 1, [(2.0, 12.0)], FIGHT) == (2.5, 12.0)


def test_a_shot_landing_exactly_at_the_window_end_is_outside_it():
    # Windows are half-open, so the shot at 12.0 spends a round - and the window
    # end is ordered first, which is what makes the buff already gone by then.
    assert _round_grant_shot_window([3.0, 12.0], 2.5, 1, [(2.0, 12.0)], FIGHT) == (2.5, 12.0)


def test_end_to_end_a_round_grant_covers_the_recipients_whole_unlimited_window():
    # The attacker's own burst at t=5.0 opens a 4.3-sec [Unlimited Ammunition]
    # window (4.3 rather than a round number so no shot lands exactly on its
    # end, which is a separate case tested above). A squad "for 1 round" buff
    # granted at Full Burst enter therefore covers every shot from 61/12 to the
    # last one before 9.3, and the next shot is unbuffed.
    #
    # The magazine is deliberately far larger than the fight so no reload
    # interrupts: this input is a STATUS axis and does not touch shot
    # generation, which each unlimited-ammo unit already models its own way.
    rule = round_buff_rule("full_burst_enter", [("damage_taken_up", 0.5, "squad")], shots=1)
    result = simulate_raid(
        make_deck(),
        {"buffer": [rule], "midtier": [], "attacker": []},
        burst_damage_percents={},
        base_stats=make_base_stats(attacker_atk=10000),
        enemy_def=0,
        gauge_charge_time=5.0,
        fight_duration=11.0,
        mode="auto",
        base_crit_rate=0.0,
        weapon_stats={"attacker": _ar_weapon(max_ammo=1000)},
        unlimited_ammo_durations={"attacker": 4.3},
    )
    normal = {round(e["time"], 6): e["damage"]
              for e in result["damage_log"] if e["source"] == "normal_attack"}
    buffed = sorted(t for t, damage in normal.items()
                    if damage > 1000.0 * fb_factor(result, t) + 1e-6)
    assert buffed[0] == pytest.approx(61 / 12)
    assert buffed[-1] == pytest.approx(111 / 12)   # 9.25, the last shot before 9.3
    assert len(buffed) == 111 - 61 + 1
    assert normal[round(112 / 12, 6)] == pytest.approx(1000.0 * fb_factor(result, 112 / 12))


def test_the_same_deck_without_the_window_spends_the_buff_on_one_shot():
    # The control for the test above: drop the status and the buff is back to a
    # single covered shot.
    rule = round_buff_rule("full_burst_enter", [("damage_taken_up", 0.5, "squad")], shots=1)
    result = simulate_raid(
        make_deck(),
        {"buffer": [rule], "midtier": [], "attacker": []},
        burst_damage_percents={},
        base_stats=make_base_stats(attacker_atk=10000),
        enemy_def=0,
        gauge_charge_time=5.0,
        fight_duration=11.0,
        mode="auto",
        base_crit_rate=0.0,
        weapon_stats={"attacker": _ar_weapon(max_ammo=1000)},
    )
    normal = {round(e["time"], 6): e["damage"]
              for e in result["damage_log"] if e["source"] == "normal_attack"}
    buffed = [t for t, damage in normal.items()
              if damage > 1000.0 * fb_factor(result, t) + 1e-6]
    assert buffed == [pytest.approx(61 / 12)]


# The census Fienn confirmed on 2026-08-18. A unit is on it because her skill
# text says "Unlimited ammunition", never because her transform happens not to
# reload - Red Hood's Red Wolf swaps in a 99-round magazine that outlasts its
# own window, and a round-count buff on her IS spent normally.
UNLIMITED_AMMO_SECONDS = {
    "grave": 10.0,
    "nayuta": 10.0,
    "moran": 10.0,
    "moran-signature": 10.0,
    "modernia": 15.0,
}
NOT_UNLIMITED_AMMO = ["red-hood", "rapi-red-hood", "snow-white", "maxwell", "miranda", "zwei"]


@pytest.mark.parametrize("slug,seconds", sorted(UNLIMITED_AMMO_SECONDS.items()))
def test_each_unlimited_ammo_unit_declares_its_window_from_its_own_data(slug, seconds):
    from app.models import UserNikkeState
    from app.user_roster import load_roster

    specs, excluded = load_roster([UserNikkeState.model_validate({
        "character_slug": slug, "level": 200, "core_level": 0,
        "hp": 1_000_000.0, "atk": 60_000.0, "def_": 3_000.0,
        "skill_levels": {"skill1": 10, "skill2": 10, "burst": 10},
    })])
    assert not excluded
    spec = next(s for s in specs if s.slug == slug)
    assert get_unlimited_ammo_duration(slug, spec.skill_values) == pytest.approx(seconds)


@pytest.mark.parametrize("slug", NOT_UNLIMITED_AMMO)
def test_a_transform_that_merely_outlasts_its_magazine_is_not_the_status(slug):
    assert get_unlimited_ammo_duration(slug, {}) is None
