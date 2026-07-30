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
