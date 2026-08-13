"""The Tactical Bear cube's bullet refund, as a magazine-walking counter.

The refund is not a stat: a magazine that refills mid-burst shifts every
later reload, and reload phase against the 10-second Full Burst window is
what decides whether the extra rounds are worth anything. Scoring deck 1
with the refund faked as a flat max-ammo percentage reads 0.9804x at +11%,
0.9736x at +22% and 0.9930x at +43% - non-monotonic, so no percentage
stands in for it.
"""
import pytest

from app.attack_rate import (
    AmmoRefill,
    AmmoRefund,
    generate_segmented_shots,
    generate_shot_times,
    last_bullet_shot_times,
    magazine_shot_count,
)


BASTION = AmmoRefund(every_shots=10, rounds=3)

# Scarlet: Black Shadow's weapon - the roster's one confirmed Tactical Bear
# wearer, and the reason the counter has to outlive a magazine (she holds 9).
RL = dict(weapon="RL", max_ammo=9, reload_time=2.0, charge_time=0.3,
          damage_percent=57.29, charge_damage_percent=164.205,
          charge_motion_delay=0.43)


def test_no_refund_fires_exactly_the_magazine():
    assert magazine_shot_count(9, 0, None) == (9, 9)


def test_a_fresh_nine_round_magazine_never_reaches_the_trigger():
    # Scarlet: Black Shadow holds 9 - the 10th shot of the fight lands in her
    # SECOND magazine, which is why the counter has to survive the reload.
    assert magazine_shot_count(9, 0, BASTION) == (9, 9)


def test_the_counter_carries_across_the_reload_and_buys_one_round():
    # Second magazine: shot 10 refunds 3 onto 8 remaining, capped back to 9.
    assert magazine_shot_count(9, 9, BASTION) == (10, 19)


def test_the_steady_state_is_ten_shots_per_magazine():
    shots_before = 0
    sizes = []
    for _ in range(4):
        size, shots_before = magazine_shot_count(9, shots_before, BASTION)
        sizes.append(size)
    assert sizes == [9, 10, 10, 10]


def test_a_magazine_larger_than_the_trigger_refunds_inside_itself():
    # Her Full Burst magazine is 9 x 1.6 = 14. Shot 10 of the fight lands
    # with 4 left, so the refund is NOT capped away: 4 + 3 = 7 more rounds.
    assert magazine_shot_count(14, 0, BASTION) == (17, 17)


def test_a_refund_that_outpaces_the_trigger_is_rejected():
    # 10 rounds back every 10 shots would never empty the magazine.
    with pytest.raises(ValueError, match="never empties"):
        AmmoRefund(every_shots=10, rounds=10)


def test_the_refund_adds_shots_to_a_charge_weapons_timeline():
    without = generate_shot_times("RL", 9, 2.0, 0.3, 180.0)
    with_refund = generate_shot_times("RL", 9, 2.0, 0.3, 180.0,
                                      ammo_refund=BASTION)
    assert len(with_refund) > len(without)


def test_a_timeline_without_a_refund_is_unchanged():
    assert generate_shot_times("RL", 9, 2.0, 0.3, 180.0) == \
        generate_shot_times("RL", 9, 2.0, 0.3, 180.0, ammo_refund=None)


def test_last_bullet_marks_the_refunded_final_round():
    # With the refund the second magazine runs to 10 rounds, so the round that
    # empties it is the 10th, not the 9th.
    times = generate_shot_times("RL", 9, 2.0, 0.3, 180.0, ammo_refund=BASTION)
    lasts = last_bullet_shot_times("RL", 9, 2.0, 0.3, 180.0,
                                   ammo_refund=BASTION)
    assert times[8] in lasts        # first magazine still ends at round 9
    assert times[18] in lasts       # second ends at round 10 (index 9..18)
    assert times[17] not in lasts


def _shared_magazine_case(**extra):
    """Snow White: Heavy Arms' shape - a mode that re-times her charge and
    draws from her own magazine rather than arriving loaded."""
    base = dict(weapon="SR", max_ammo=6, reload_time=2.0, charge_time=1.2,
                damage_percent=100.0, charge_damage_percent=200.0, **extra)
    segment = [dict(start=5.0, until_shots=3, shares_magazine=True,
                    profile=dict(weapon="SR", charge_time=3.2,
                                 damage_percent=100.0,
                                 charge_damage_percent=200.0))]
    return base, segment


def test_a_shared_magazine_segment_spends_refunded_rounds_too():
    # Its shots draw from her own magazine, so they count toward the trigger
    # like any other.
    plain_base, segment = _shared_magazine_case()
    bastion_base, _ = _shared_magazine_case(ammo_refund=BASTION)
    plain = generate_segmented_shots(plain_base, segment, 60.0)
    bastion = generate_segmented_shots(bastion_base, segment, 60.0)
    assert len(bastion) > len(plain)


def test_a_refund_does_not_re_open_the_magazine():
    # Refunding onto a partly-spent magazine must not mark another shot as the
    # magazine's first - only a reload starts a magazine.
    base, segment = _shared_magazine_case(ammo_refund=BASTION)
    records = generate_segmented_shots(base, segment, 60.0)
    firsts = [r for r in records if r.is_first_bullet]
    lasts = [r for r in records if r.is_last_bullet]
    # Every magazine opens once and closes once (the fight may cut the last
    # one short, so firsts can lead lasts by at most one).
    assert 0 <= len(firsts) - len(lasts) <= 1


def test_the_weapon_stats_dict_carries_the_refund_into_segmented_shots():
    plain = generate_segmented_shots(RL, [], 180.0)
    bastion = generate_segmented_shots({**RL, "ammo_refund": BASTION}, [], 180.0)
    assert len(bastion) > len(plain)
    assert [r.time for r in plain] == [r.time for r in
                                       generate_segmented_shots(RL, [], 180.0)]


# EVE's Eagle Eye-Type Exospine hands back the same 3 rounds every 10 shots off
# her own skill, so a wearer of the cube can carry two independent refunds.
EAGLE_EYE = AmmoRefund(every_shots=10, rounds=3)


def test_two_refunds_each_keep_their_own_trigger():
    # A 14-round magazine, both refunds on the same 10-shot cadence. Shot 10
    # leaves 4 and each hands back 3, so 10 remain; shot 20 leaves 0 and the
    # pair rebuilds it to 6; those run out on shot 26 with no trigger left.
    assert magazine_shot_count(14, 0, (BASTION, EAGLE_EYE)) == (26, 26)
    # One source alone stops at 17 (see the single-refund case above).
    assert magazine_shot_count(14, 0, BASTION) == (17, 17)


def test_one_refund_in_a_sequence_matches_passing_it_alone():
    assert magazine_shot_count(9, 9, (BASTION,)) == magazine_shot_count(9, 9, BASTION)


def test_an_empty_sequence_is_the_no_refund_case():
    assert magazine_shot_count(9, 0, ()) == magazine_shot_count(9, 0, None)


def test_refunds_that_together_outpace_the_magazine_are_rejected():
    # 9 rounds back every 10 shots is legal alone; three of them is not, and a
    # magazine that never empties would spin forever.
    nine = AmmoRefund(every_shots=10, rounds=9)
    with pytest.raises(ValueError, match="never empties"):
        magazine_shot_count(9, 0, (nine, nine))


def test_the_boss_gate_is_resolved_where_the_encounter_is_known():
    """The roster assembles a deck and cannot know the boss, so it carries the
    skill refund with its required element and the simulator applies it."""
    from app.raid_simulator import resolve_ammo_refunds

    gated = {**RL, "skill_ammo_refund": (EAGLE_EYE, "Electric")}
    assert resolve_ammo_refunds(gated, "Electric") == (EAGLE_EYE,)
    assert resolve_ammo_refunds(gated, "Fire") == ()
    assert resolve_ammo_refunds(gated, None) == ()

    # An ungated skill refund needs no encounter.
    ungated = {**RL, "skill_ammo_refund": (EAGLE_EYE, None)}
    assert resolve_ammo_refunds(ungated, "Fire") == (EAGLE_EYE,)

    # The cube's rides alongside, and both apply when both are present.
    assert resolve_ammo_refunds({**RL, "ammo_refund": BASTION}, "Fire") == (BASTION,)
    both = {**RL, "ammo_refund": BASTION, "skill_ammo_refund": (EAGLE_EYE, "Electric")}
    assert resolve_ammo_refunds(both, "Electric") == (BASTION, EAGLE_EYE)
    assert resolve_ammo_refunds(both, "Iron") == (BASTION,)
    assert resolve_ammo_refunds(RL, "Electric") == ()


# Tove's Favorite Item build: "Activates after 10 normal attack(s). Affects
# self. Reload 5.31% of the magazine." She is an AR with 60 rounds, so the
# percentage is worth 3 whole rounds - the unit the engine hands back.
TOVE = AmmoRefund(every_shots=10, percent=5.31)


def test_a_percentage_refund_resolves_against_the_magazine_it_lands_in():
    assert TOVE.rounds_for(60) == 3


def test_a_percentage_too_small_for_one_round_hands_back_nothing():
    # 5.31% of 9 is 0.478 - below half a round, so it rounds away.
    assert TOVE.rounds_for(9) == 0


def test_a_refund_declared_in_rounds_ignores_capacity():
    assert BASTION.rounds_for(9) == 3
    assert BASTION.rounds_for(600) == 3


def test_a_percentage_refund_fires_on_the_same_counter_as_a_round_refund():
    # 3 rounds back every 10 shots off a 60-round magazine: shots 10..60 each
    # add 3 when the counter lands, and the magazine walks past its capacity.
    by_percent = magazine_shot_count(60, 0, TOVE)
    by_rounds = magazine_shot_count(60, 0, AmmoRefund(every_shots=10, rounds=3))
    assert by_percent == by_rounds


def test_a_percentage_refund_that_outpaces_the_trigger_is_rejected():
    # 20% of a 60-round magazine is 12 rounds every 10 shots - it never empties.
    greedy = AmmoRefund(every_shots=10, percent=20.0)
    with pytest.raises(ValueError, match="never empties"):
        magazine_shot_count(60, 0, greedy)


def test_a_percentage_rounds_to_the_nearest_round_not_down():
    # 5.31% of 30 is 1.593 - a floor would hand back 1, the game hands back 2.
    assert AmmoRefund(every_shots=10, percent=5.31).rounds_for(30) == 2


def _uniform_clock(magazine_start, interval):
    """Round i of a magazine that starts at `magazine_start` and fires every
    `interval` seconds - the shape both magazine and charge generators reduce
    to when spinup is absent."""
    return lambda i: magazine_start + i * interval


def test_a_refill_inside_the_magazine_adds_rounds_capped_at_capacity():
    # A 10-round magazine firing 1/sec from t=0: rounds land at 0..9. A refill
    # of 40% (4 rounds) at t=5 finds 4 spent, so all 4 come back.
    size, counter = magazine_shot_count(
        10, 0, None,
        time_of_round=_uniform_clock(0.0, 1.0),
        refills=(AmmoRefill(time=5.0, percent=40.0),))
    assert (size, counter) == (14, 14)


def test_a_refill_is_capped_by_what_the_magazine_has_spent():
    # Same magazine, refill at t=1: only 1 round is gone, so only 1 comes back.
    size, _ = magazine_shot_count(
        10, 0, None,
        time_of_round=_uniform_clock(0.0, 1.0),
        refills=(AmmoRefill(time=1.0, percent=40.0),))
    assert size == 11


def test_a_stale_refill_finds_no_room_in_a_full_magazine():
    # A refill at t=20 is checked at this magazine's very first round (opens
    # at t=30, so it is immediately "due") - which is still at full capacity,
    # since nothing has been spent yet. The ordinary cap that limits every
    # refill is what makes a stale one worth nothing: min(10, 10 + 4) == 10.
    # No time-based drop rule is needed for this.
    size, _ = magazine_shot_count(
        10, 0, None,
        time_of_round=_uniform_clock(30.0, 1.0),   # this magazine opens at 30
        refills=(AmmoRefill(time=20.0, percent=40.0),))
    assert size == 10


def test_no_refills_never_touches_the_clock():
    # The clock raises if called - with no refills the walk must not ask for a
    # single round's time, which is what keeps every existing timeline exact.
    def exploding_clock(_i):
        raise AssertionError("time_of_round must not be called without refills")

    assert magazine_shot_count(9, 0, BASTION,
                               time_of_round=exploding_clock) == (9, 9)


def test_refills_and_the_shot_counter_refund_stack():
    # BASTION alone caps out at 17 on a 14-round magazine (one trigger, see
    # the larger-than-trigger case above). The refill adds 4 more at t=5, and
    # those extra rounds carry the counter past 20 too, so BASTION fires a
    # SECOND time: 14 + 4 (refill) + 3 + 3 (two BASTION triggers) = 24.
    size, _ = magazine_shot_count(
        14, 0, BASTION,
        time_of_round=_uniform_clock(0.0, 1.0),
        refills=(AmmoRefill(time=5.0, rounds=4),))
    assert size == 24


def test_the_walk_stops_at_the_end_of_the_fight():
    # A refill every round would keep a magazine alive forever - which is what
    # Arcana's rotation really does inside her window. The walk is bounded by
    # the moment the fight (or the segment) ends, not by the magazine draining.
    forever = tuple(AmmoRefill(time=float(t), rounds=1) for t in range(60))
    size, _ = magazine_shot_count(
        10, 0, None,
        time_of_round=_uniform_clock(0.0, 1.0),
        refills=forever, stop_time=25.0)
    assert size == 25
