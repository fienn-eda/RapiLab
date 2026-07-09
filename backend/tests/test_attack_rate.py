import pytest

from app.attack_rate import (
    RATE_OF_FIRE_60FPS,
    generate_charge_shot_times,
    generate_magazine_shot_times,
    generate_shot_times,
    rate_of_fire_for_weapon,
)


def test_rate_of_fire_matches_fienns_60fps_table():
    assert rate_of_fire_for_weapon("AR") == 12.0
    assert rate_of_fire_for_weapon("MG") == 60.0
    assert rate_of_fire_for_weapon("SMG") == 20.0
    assert rate_of_fire_for_weapon("SG") == 1.5


def test_magazine_shots_are_evenly_spaced_within_one_magazine():
    # rate_of_fire=10/sec, 5 rounds -> shots at 0, 0.1, 0.2, 0.3, 0.4
    shots = generate_magazine_shot_times(
        rate_of_fire=10.0, max_ammo=5, reload_time=1.0, fight_duration=0.45
    )
    assert [round(t, 4) for t in shots] == [0.0, 0.1, 0.2, 0.3, 0.4]


def test_magazine_reloads_after_emptying_then_resumes():
    # magazine empties at t=0.5 (5 shots * 0.1s), reload takes 1s -> next
    # magazine starts at t=1.5.
    shots = generate_magazine_shot_times(
        rate_of_fire=10.0, max_ammo=5, reload_time=1.0, fight_duration=3.0
    )
    assert [round(t, 4) for t in shots] == [
        0.0, 0.1, 0.2, 0.3, 0.4,
        1.5, 1.6, 1.7, 1.8, 1.9,
    ]


def test_magazine_shots_stop_at_fight_duration():
    shots = generate_magazine_shot_times(
        rate_of_fire=10.0, max_ammo=5, reload_time=1.0, fight_duration=0.25
    )
    assert [round(t, 4) for t in shots] == [0.0, 0.1, 0.2]


def test_magazine_reload_speed_up_shortens_the_gap_between_magazines():
    # reload_speed_percent=1.0 (100% faster) at the moment the magazine
    # empties -> actual reload time = 1.0 / (1+1.0) = 0.5s instead of 1.0s.
    shots = generate_magazine_shot_times(
        rate_of_fire=10.0, max_ammo=5, reload_time=1.0, fight_duration=3.0,
        reload_speed_percent_at=lambda t: 1.0,
    )
    assert round(shots[5], 4) == 1.0  # 0.5 (empty) + 0.5 (reduced reload)


def test_magazine_ammo_up_increases_shots_per_magazine():
    # max_ammo_percent=1.0 (double) evaluated at each magazine's start time
    shots = generate_magazine_shot_times(
        rate_of_fire=10.0, max_ammo=5, reload_time=1.0, fight_duration=1.5,
        max_ammo_percent_at=lambda t: 1.0,
    )
    assert len(shots) == 10
    assert [round(t, 4) for t in shots] == [round(i * 0.1, 4) for i in range(10)]


def test_charge_shots_fire_max_ammo_rounds_before_reloading():
    # charge_time=1, max_ammo=3, reload_time=2: three charged shots 1s apart
    # (t=1,2,3), THEN a 2s reload before the next magazine's first shot.
    shots = generate_charge_shot_times(
        charge_time=1.0, reload_time=2.0, max_ammo=3, fight_duration=9.0
    )
    assert shots == [1.0, 2.0, 3.0, 6.0, 7.0, 8.0]


def test_charge_shots_single_round_magazine_matches_original_behavior():
    # max_ammo=1 (the old assumed behavior): reload after every shot.
    shots = generate_charge_shot_times(
        charge_time=1.0, reload_time=2.0, max_ammo=1, fight_duration=8.0
    )
    assert shots == [1.0, 4.0, 7.0]


def test_charge_shots_stop_at_fight_duration():
    shots = generate_charge_shot_times(
        charge_time=1.0, reload_time=2.0, max_ammo=1, fight_duration=4.0
    )
    assert shots == [1.0]


def test_charge_reload_speed_up_shortens_the_gap_between_magazines():
    shots = generate_charge_shot_times(
        charge_time=1.0, reload_time=2.0, max_ammo=1, fight_duration=8.0,
        reload_speed_percent_at=lambda t: 1.0,
    )
    # reload = 2.0/(1+1.0) = 1.0s -> next shot at 1.0(charge) + 1.0(reload) + 1.0(charge) = 3.0
    assert shots == [1.0, 3.0, 5.0, 7.0]


def test_generate_shot_times_dispatches_to_magazine_for_non_charge_weapons():
    shots = generate_shot_times(
        weapon="MG", max_ammo=3, reload_time=1.0, charge_time=0.0, fight_duration=0.25,
    )
    # MG rate of fire is 60/sec -> shots ~1/60s apart
    assert len(shots) == 3
    assert shots[0] == 0.0


def test_generate_shot_times_dispatches_to_charge_for_charge_weapons():
    shots = generate_shot_times(
        weapon="RL", max_ammo=3, reload_time=2.0, charge_time=1.0, fight_duration=9.0,
    )
    assert shots == [1.0, 2.0, 3.0, 6.0, 7.0, 8.0]


def test_rate_of_fire_for_unknown_weapon_raises():
    with pytest.raises(KeyError):
        rate_of_fire_for_weapon("UNKNOWN")
