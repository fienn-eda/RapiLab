"""The Tactical Bear cube's bullet refund, as a magazine-walking counter.

The refund is not a stat: a magazine that refills mid-burst shifts every
later reload, and reload phase against the 10-second Full Burst window is
what decides whether the extra rounds are worth anything. Scoring deck 1
with the refund faked as a flat max-ammo percentage reads 0.9804x at +11%,
0.9736x at +22% and 0.9930x at +43% - non-monotonic, so no percentage
stands in for it.
"""
import pytest

from app.attack_rate import AmmoRefund, magazine_shot_count


BASTION = AmmoRefund(every_shots=10, rounds=3)


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
