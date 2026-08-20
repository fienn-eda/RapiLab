import pytest

from app.attack_rate import (
    RELOAD_FIXED_SECONDS,
    CHARGE_ROUNDS_PER_MINUTE,
    RATE_OF_FIRE_60FPS,
    ROUNDS_PER_MINUTE,
    AmmoRefill,
    AmmoRefund,
    ShotRecord,
    charge_interval_floor,
    charge_interval_floor_for,
    charge_time_with_speed,
    charge_first_bullet_times,
    charge_last_bullet_times,
    first_bullet_shot_times,
    reload_time_with_speed,
    generate_charge_shot_times,
    generate_magazine_shot_times,
    generate_segmented_shots,
    generate_shot_times,
    last_bullet_shot_times,
    magazine_first_bullet_times,
    magazine_last_bullet_times,
    magazine_shot_count,
    rate_of_fire_for_weapon,
    rounds_per_second,
)


def test_rate_of_fire_matches_fienns_60fps_table():
    assert rate_of_fire_for_weapon("AR") == 12.0
    assert rate_of_fire_for_weapon("MG") == 60.0
    assert rate_of_fire_for_weapon("SMG") == 20.0
    assert rate_of_fire_for_weapon("SG") == 1.5


def test_the_class_table_is_the_frame_grid_applied_to_the_game_data():
    """Each class's rounds-per-minute put through `rounds_per_second` reproduces
    the measured constant, which is what makes the two SMG/MG surprises benign:
    the nominal rates are 24 and 70 per second and the 60fps grid rounds their
    intervals up to 3 and 1 frames."""
    assert rounds_per_second(720) == RATE_OF_FIRE_60FPS["AR"]      # 5 frames
    assert rounds_per_second(90) == RATE_OF_FIRE_60FPS["SG"]       # 40 frames
    assert rounds_per_second(1440) == RATE_OF_FIRE_60FPS["SMG"]    # 2.5 -> 3
    assert rounds_per_second(4200) == RATE_OF_FIRE_60FPS["MG"]     # 0.857 -> 1


def test_a_round_never_takes_less_than_a_frame():
    # The MG's nominal 70/sec is the case: the grid is what caps it at 60.
    assert rounds_per_second(6000) == 60.0


def test_the_per_unit_table_holds_only_units_the_class_rate_is_wrong_for():
    # Jill: Valentine's AR is a 9-round marksman rifle - 150 rounds/min against
    # the class's 720. Fienn read 24 (+-1) frames between her rounds in game
    # (2026-08-15), which is exactly the 2.5/sec this rpm decodes to.
    assert ROUNDS_PER_MINUTE == {"jill-valentine": 150}
    assert rounds_per_second(ROUNDS_PER_MINUTE["jill-valentine"]) == 2.5


def test_magazine_shots_are_evenly_spaced_within_one_magazine():
    # rate_of_fire=10/sec, 5 rounds -> shots at 0, 0.1, 0.2, 0.3, 0.4
    shots = generate_magazine_shot_times(
        rate_of_fire=10.0, max_ammo=5, reload_time=1.0, fight_duration=0.45
    )
    assert [round(t, 4) for t in shots] == [0.0, 0.1, 0.2, 0.3, 0.4]


def test_magazine_reloads_after_emptying_then_resumes():
    # magazine empties at t=0.5 (5 shots * 0.1s), reload takes the file's 1s
    # plus the fixed 0.148 segment -> next magazine starts at t=1.648.
    shots = generate_magazine_shot_times(
        rate_of_fire=10.0, max_ammo=5, reload_time=1.0, fight_duration=3.0
    )
    assert [round(t, 4) for t in shots] == [
        0.0, 0.1, 0.2, 0.3, 0.4,
        1.648, 1.748, 1.848, 1.948, 2.048,
    ]


def test_magazine_shots_stop_at_fight_duration():
    shots = generate_magazine_shot_times(
        rate_of_fire=10.0, max_ammo=5, reload_time=1.0, fight_duration=0.25
    )
    assert [round(t, 4) for t in shots] == [0.0, 0.1, 0.2]


def test_magazine_reload_speed_up_shortens_the_gap_between_magazines():
    # reload_speed_percent=1.0 (100% faster) at the moment the magazine empties
    # takes the whole scaled part away, leaving only the fixed 0.148 segment.
    shots = generate_magazine_shot_times(
        rate_of_fire=10.0, max_ammo=5, reload_time=1.0, fight_duration=3.0,
        reload_speed_percent_at=lambda t: 1.0,
    )
    assert round(shots[5], 4) == 0.648  # 0.5 (empty) + 0.148 (what is left)


def test_magazine_ammo_up_increases_shots_per_magazine():
    # max_ammo_percent=1.0 (double) evaluated at each magazine's start time
    shots = generate_magazine_shot_times(
        rate_of_fire=10.0, max_ammo=5, reload_time=1.0, fight_duration=1.5,
        max_ammo_percent_at=lambda t: 1.0,
    )
    assert len(shots) == 10
    assert [round(t, 4) for t in shots] == [round(i * 0.1, 4) for i in range(10)]


def test_max_ammo_increase_and_decrease_both_apply_to_base_ammo_additively():
    # Per Fienn's in-game check: an overload ammo INCREASE and Privaty's EX
    # Magazine ammo DECREASE are both computed against BASE ammo and summed,
    # NOT the decrease applied to the already-increased total. Base 300, +200%
    # overload, -50.66% Privaty -> 300*(1 + 2.0 - 0.5066) = 748 rounds, not
    # 300*(1+2.0)*(1-0.5066) = 444. Since total_for sums all max_ammo_percent
    # effects, passing their sum here reproduces exactly that additive-on-base
    # behavior.
    summed_percent = 2.0 - 0.5066
    shots = generate_magazine_shot_times(
        rate_of_fire=1000.0, max_ammo=300, reload_time=1000.0, fight_duration=1.0,
        max_ammo_percent_at=lambda t: summed_percent,
    )
    # one magazine only (huge reload keeps us in the first magazine); its size
    # is the whole story here.
    assert len(shots) == 748


def test_charge_shots_fire_max_ammo_rounds_before_reloading():
    # charge_time=1, max_ammo=3, reload_time=2: three charged shots 1s apart
    # (t=1,2,3), THEN a 2.148s reload (file 2.0 plus the fixed segment) before
    # the next magazine's first shot.
    shots = generate_charge_shot_times(
        charge_time=1.0, reload_time=2.0, max_ammo=3, fight_duration=9.0
    )
    assert shots == pytest.approx([1.0, 2.0, 3.0, 6.148, 7.148, 8.148])


def test_charge_shots_single_round_magazine_matches_original_behavior():
    # max_ammo=1 (the old assumed behavior): reload after every shot.
    shots = generate_charge_shot_times(
        charge_time=1.0, reload_time=2.0, max_ammo=1, fight_duration=8.0
    )
    assert shots == pytest.approx([1.0, 4.148, 7.296])


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
    # +100% takes the whole scaled part, leaving the fixed 0.148 -> next shot at
    # 1.0(charge) + 0.148(reload) + 1.0(charge) = 2.148.
    assert shots == pytest.approx([1.0, 2.148, 3.296, 4.444, 5.592, 6.74, 7.888])


def test_generate_shot_times_dispatches_to_magazine_for_non_charge_weapons():
    shots = generate_shot_times(
        weapon="MG", max_ammo=3, reload_time=1.0, charge_time=0.0, fight_duration=1.0,
    )
    # An MG reaches its nominal 60/sec only after warming up, and the warm-up's
    # cost sits at the front - rounds 0-2 of a magazine span 56 frames, not 3.
    assert len(shots) == 3
    assert shots[0] == 0.0
    assert shots[2] == pytest.approx(56 / 60)


def test_generate_shot_times_dispatches_to_charge_for_charge_weapons():
    shots = generate_shot_times(
        weapon="RL", max_ammo=3, reload_time=2.0, charge_time=1.0, fight_duration=9.0,
    )
    assert shots == pytest.approx([1.0, 2.0, 3.0, 6.148, 7.148, 8.148])


def test_rate_of_fire_for_unknown_weapon_raises():
    with pytest.raises(KeyError):
        rate_of_fire_for_weapon("UNKNOWN")


def test_magazine_last_bullet_times_marks_the_final_round_of_each_magazine():
    # Same scenario as test_magazine_reloads_after_emptying_then_resumes:
    # shots at [0, .1, .2, .3, .4, 1.648, ...] - the round that actually empties
    # each 5-round magazine is index 4 within it (t=0.4, t=2.048), not any
    # other shot.
    last_bullets = magazine_last_bullet_times(
        rate_of_fire=10.0, max_ammo=5, reload_time=1.0, fight_duration=3.0,
    )
    assert sorted(last_bullets) == pytest.approx([0.4, 2.048])


def test_magazine_last_bullet_times_tracks_live_max_ammo_percent():
    # Same scenario as test_magazine_ammo_up_increases_shots_per_magazine:
    # max_ammo_percent doubles the magazine (5 -> 10 rounds), evaluated live
    # at the magazine's start - same mechanism generate_magazine_shot_times
    # already uses for magazine SIZE. The last bullet shifts to the 10th
    # round (t=0.9), not the un-buffed 5th (t=0.4).
    last_bullets = magazine_last_bullet_times(
        rate_of_fire=10.0, max_ammo=5, reload_time=1.0, fight_duration=1.5,
        max_ammo_percent_at=lambda t: 1.0,
    )
    assert last_bullets == {0.9}


def test_magazine_last_bullet_times_does_not_mark_a_fight_duration_truncated_shot():
    # Same scenario as test_magazine_shots_stop_at_fight_duration: the fight
    # ends mid-magazine (3 of 5 rounds fired) - the final recorded shot is a
    # cutoff artifact, not a genuine "magazine emptied" event, so it must NOT
    # be marked as a last bullet.
    last_bullets = magazine_last_bullet_times(
        rate_of_fire=10.0, max_ammo=5, reload_time=1.0, fight_duration=0.25,
    )
    assert last_bullets == set()


def test_charge_last_bullet_times_marks_the_final_round_of_each_magazine():
    # Same scenario as test_charge_shots_fire_max_ammo_rounds_before_reloading:
    # shots at [1, 2, 3, 6.148, 7.148, 8.148] - the round that empties each
    # 3-shot magazine is the 3rd (t=3.0, t=8.148).
    last_bullets = charge_last_bullet_times(
        charge_time=1.0, reload_time=2.0, max_ammo=3, fight_duration=9.0,
    )
    assert sorted(last_bullets) == pytest.approx([3.0, 8.148])


def test_last_bullet_shot_times_dispatches_by_weapon_type():
    # Magazine weapon: single magazine (huge reload keeps us in it), so the
    # last shot generated IS the last bullet.
    shots = generate_shot_times(
        weapon="AR", max_ammo=5, reload_time=1000.0, charge_time=0.0, fight_duration=1.0,
    )
    last_bullets = last_bullet_shot_times(
        weapon="AR", max_ammo=5, reload_time=1000.0, charge_time=0.0, fight_duration=1.0,
    )
    assert len(shots) == 5
    assert last_bullets == {shots[-1]}

    # Charge weapon: same scenario as test_charge_shots_fire_max_ammo_rounds_before_reloading.
    charge_last_bullets = last_bullet_shot_times(
        weapon="RL", max_ammo=3, reload_time=2.0, charge_time=1.0, fight_duration=9.0,
    )
    assert sorted(charge_last_bullets) == pytest.approx([3.0, 8.148])


def test_last_bullet_shot_times_is_always_a_subset_of_generate_shot_times():
    shots = generate_shot_times(
        weapon="MG", max_ammo=7, reload_time=0.5, charge_time=0.0, fight_duration=2.0,
    )
    last_bullets = last_bullet_shot_times(
        weapon="MG", max_ammo=7, reload_time=0.5, charge_time=0.0, fight_duration=2.0,
    )
    assert last_bullets and last_bullets <= set(shots)


def test_magazine_first_bullet_times_marks_each_magazine_start_including_t0():
    # Same scenario as test_magazine_last_bullet_times...: magazines start at
    # t=0 and t=1.5. The battle-opening magazine at t=0 IS a first bullet - a
    # "at the start of battle and upon reloading to Max Ammunition" trigger
    # (gap #9, e.g. Jill Valentine's Magnum/Acid Ammo) fires there too.
    first_bullets = magazine_first_bullet_times(
        rate_of_fire=10.0, max_ammo=5, reload_time=1.0, fight_duration=3.0,
    )
    assert sorted(first_bullets) == pytest.approx([0.0, 1.648])


def test_first_bullet_shot_times_ar_marks_each_magazine_start():
    # AR (12/s, 60 ammo, 1s reload): magazine empties at 5.0, reloads by 6.0 -
    # first bullets at each magazine's start: 0.0, 6.0, 12.0.
    first_bullets = first_bullet_shot_times(
        weapon="AR", max_ammo=60, reload_time=1.0, charge_time=0.0, fight_duration=12.5,
    )
    assert sorted(first_bullets) == pytest.approx([0.0, 6.148, 12.296])


def test_charge_first_bullet_times_is_one_effective_charge_after_magazine_start():
    # Same scenario as test_charge_last_bullet_times...: shots [1,2,3, 6,7,8] -
    # the first charged shot of each magazine lands at 1.0 and 6.0.
    first_bullets = charge_first_bullet_times(
        charge_time=1.0, reload_time=2.0, max_ammo=3, fight_duration=9.0,
    )
    assert sorted(first_bullets) == pytest.approx([1.0, 6.148])


def test_charge_first_bullet_beyond_fight_duration_is_excluded():
    # The charged first shot itself lands after the fight ends - never fires.
    first_bullets = charge_first_bullet_times(
        charge_time=1.0, reload_time=2.0, max_ammo=3, fight_duration=0.5,
    )
    assert first_bullets == set()


def test_first_bullet_shot_times_is_always_a_subset_of_generate_shot_times():
    kwargs = dict(weapon="MG", max_ammo=7, reload_time=0.5, charge_time=0.0, fight_duration=2.0)
    shots = generate_shot_times(**kwargs)
    first_bullets = first_bullet_shot_times(**kwargs)
    assert first_bullets and first_bullets <= set(shots)

    charge_kwargs = dict(weapon="RL", max_ammo=3, reload_time=2.0, charge_time=1.0, fight_duration=9.0)
    charge_shots = generate_shot_times(**charge_kwargs)
    charge_first = first_bullet_shot_times(**charge_kwargs)
    assert charge_first and charge_first <= set(charge_shots)


# --- attack speed / charge speed (Phase S) ---

def test_magazine_attack_speed_up_shortens_shot_interval():
    # attack_speed +1.0 (double rate) -> interval 1/(10*2) = 0.05s
    shots = generate_magazine_shot_times(
        rate_of_fire=10.0, max_ammo=5, reload_time=1.0, fight_duration=0.3,
        attack_speed_percent_at=lambda t: 1.0,
    )
    assert [round(t, 4) for t in shots] == [0.0, 0.05, 0.1, 0.15, 0.2]


def test_magazine_attack_speed_is_evaluated_per_magazine():
    # +1.0 for the first magazine (start t=0), 0 afterwards. First magazine's
    # interval is 0.05s (5 rounds: 0..0.2), empties at 0.25, reload 1.148 ->
    # next magazine at 1.398 fires at the base 0.1s interval.
    def attack_speed(t):
        return 1.0 if t < 1.0 else 0.0
    shots = generate_magazine_shot_times(
        rate_of_fire=10.0, max_ammo=5, reload_time=1.0, fight_duration=1.6,
        attack_speed_percent_at=attack_speed,
    )
    assert [round(t, 4) for t in shots] == [0.0, 0.05, 0.1, 0.15, 0.2, 1.398, 1.498, 1.598]


def test_magazine_attack_speed_default_is_inert():
    a = generate_magazine_shot_times(rate_of_fire=10.0, max_ammo=5, reload_time=1.0, fight_duration=3.0)
    b = generate_magazine_shot_times(
        rate_of_fire=10.0, max_ammo=5, reload_time=1.0, fight_duration=3.0,
        attack_speed_percent_at=lambda t: 0.0,
    )
    assert a == b


def test_charge_speed_shortens_charge_by_its_own_percent():
    # A buff of n% SHORTENS the charge by n% of base (NOT charge/(1+n)):
    # +30% takes a 1.0s charge to 0.70s, not 0.769s.
    shots = generate_charge_shot_times(
        charge_time=1.0, reload_time=1.0, max_ammo=2, fight_duration=1.5,
        charge_speed_percent_at=lambda t: 0.3,
    )
    assert [round(t, 4) for t in shots] == [0.7, 1.4]


def test_charge_speed_at_full_shortening_lands_on_the_weapons_own_rate_of_fire():
    """+100% drives the charge to zero, so what remains is the weapon's own
    shortest gap - and that gap is PER UNIT, read from
    `shot_detail.rate_of_fire`. Cinderella's 180 rounds/min is the reading the
    old global 10/29 was inferred from: 0.33333 sec is exactly 30 shots in the
    10 sec Fienn read as 29-30."""
    floor = charge_interval_floor_for("cinderella")

    assert floor == pytest.approx(1 / 3)
    assert round(10.0 / floor) == 30
    base = {"weapon": "RL", "charge_time": 1.0, "max_ammo": 24,
            "reload_time": 2.0, "damage_percent": 100.0,
            "charge_damage_percent": 200.0, "charge_interval_floor": floor}
    shots = [r.time for r in generate_segmented_shots(
        base, [], 1.2, charge_speed_percent_at=lambda t: 1.0)]
    assert [round(t, 4) for t in shots] == [round(floor * k, 4) for k in (1, 2, 3)]


def test_every_charge_weapon_that_deviates_floors_on_a_whole_frame():
    """The five deviants land on 12, 18, 20 and 30 frames of a 60 fps grid,
    which the old inferred 10/29 (20.69 frames) did not - the same grid every
    other charge timing in this engine snaps to."""
    for rounds_per_minute in CHARGE_ROUNDS_PER_MINUTE.values():
        frames = charge_interval_floor(rounds_per_minute) * 60
        assert frames == pytest.approx(round(frames)), rounds_per_minute


def test_a_floor_can_never_slow_a_weapon_below_its_own_base_charge():
    """Scarlet: Black Shadow charges in 0.30 sec - quicker than the 1.0 sec her
    weapon's nominal 60 rounds/min would imply, which is the reading that keeps
    that default out of the floor table. With no floor of her own, nothing but
    the frame grid bounds her charge; her CADENCE is bounded by her 0.43 sec
    pause instead, one branch up in `shot_interval_with_speed`."""
    assert charge_time_with_speed(0.3, 0.0) == pytest.approx(0.3)
    assert charge_time_with_speed(0.3, 1.0) == pytest.approx(1 / 60)
    # And a floor LARGER than the base charge is clamped to it rather than
    # slowing the weapon down to it.
    assert charge_time_with_speed(0.3, 0.0, interval_floor=1.0) == pytest.approx(0.3)


def test_charge_speed_down_lengthens_the_charge():
    # The same expression covers slowdowns: -20% is 1.2x the base.
    assert charge_time_with_speed(1.0, -0.2) == pytest.approx(1.2)


def test_charge_speed_default_is_inert():
    a = generate_charge_shot_times(charge_time=1.0, reload_time=2.0, max_ammo=3, fight_duration=9.0)
    b = generate_charge_shot_times(
        charge_time=1.0, reload_time=2.0, max_ammo=3, fight_duration=9.0,
        charge_speed_percent_at=lambda t: 0.0,
    )
    assert a == b


def test_magazine_last_bullet_time_shifts_with_attack_speed():
    # 5-round magazine, attack_speed +1.0 -> interval 0.05, last bullet at 0.2
    lb = magazine_last_bullet_times(
        rate_of_fire=10.0, max_ammo=5, reload_time=1.0, fight_duration=0.5,
        attack_speed_percent_at=lambda t: 1.0,
    )
    assert {round(t, 4) for t in lb} == {0.2}


def test_last_bullet_times_stay_a_subset_under_attack_speed():
    # the shifted last-bullet times must still line up with the shifted shots
    shots = generate_shot_times(
        weapon="AR", max_ammo=10, reload_time=1.0, charge_time=0.0, fight_duration=5.0,
        attack_speed_percent_at=lambda t: 0.5,
    )
    lb = last_bullet_shot_times(
        weapon="AR", max_ammo=10, reload_time=1.0, charge_time=0.0, fight_duration=5.0,
        attack_speed_percent_at=lambda t: 0.5,
    )
    assert lb and lb <= {round(t, 10) for t in shots} or lb <= set(shots)


# --- generate_segmented_shots (weapon transforms) ---

AR_BASE = {"weapon": "AR", "damage_percent": 14.71, "max_ammo": 60,
           "reload_time": 1.5, "charge_time": 0.0, "charge_damage_percent": 100.0}
SR_BASE = {"weapon": "SR", "damage_percent": 69.04, "max_ammo": 6,
           "reload_time": 2.0, "charge_time": 1.0, "charge_damage_percent": 250.0}
# Jill: Valentine's shape - an AR whose own cadence is not its class's.
AR_SLOW = {**AR_BASE, "max_ammo": 9, "damage_percent": 71.09, "reload_time": 1.0,
           "rate_of_fire": 2.5}
SR_ODD = {"weapon": "SR", "damage_percent": 63.11, "max_ammo": 6,
          "reload_time": 2.33, "charge_time": 1.19, "charge_damage_percent": 250.0}
CANNON = {"weapon": "SR", "damage_percent": 499.5,
          "charge_damage_percent": 1000.0, "charge_time": 5.0}
# rate 4.0 → interval 0.25 (이진 정확) — 부동소수점 경계 없는 카운트 단언용.
# 실소비자(laplace 9.3)는 until_shots 형태라 경계 문제가 없다.
TICKER = {"weapon": "SR", "damage_percent": 22.2, "rate_of_fire": 4.0}


def test_no_segments_matches_legacy_generator_exactly():
    for base in (AR_BASE, SR_BASE, SR_ODD):
        records = generate_segmented_shots(base, [], 180.0)
        legacy = generate_shot_times(
            base["weapon"], base["max_ammo"], base["reload_time"],
            base["charge_time"], 180.0)
        assert [r.time for r in records] == legacy
        assert {r.time for r in records if r.is_last_bullet} == last_bullet_shot_times(
            base["weapon"], base["max_ammo"], base["reload_time"], base["charge_time"], 180.0)
        assert {r.time for r in records if r.is_first_bullet} == first_bullet_shot_times(
            base["weapon"], base["max_ammo"], base["reload_time"], base["charge_time"], 180.0)
        assert all(r.damage_percent == base["damage_percent"] for r in records)


def test_fixed_window_silences_base_and_fires_profile_rate():
    seg = {"start": 10.0, "end": 20.0, "profile": TICKER}
    records = generate_segmented_shots(SR_BASE, [seg], 60.0)
    inside = [r for r in records if 10.0 <= r.time < 20.0]
    # 창 안은 전부 오버라이드 프로필(고정 rate) — 기본 SR 발사 없음
    assert all(r.damage_percent == 22.2 for r in inside)
    assert inside[0].time == 10.25          # start + 1/rate
    assert len(inside) == 39                # k*0.25 < 10.0 → k <= 39
    assert all(r.extra_charge_bonus == 0.0 for r in inside)


def test_a_base_profile_may_carry_its_own_rate_of_fire():
    """A weapon whose cadence is not its class's brings it on the profile, the
    same channel `max_ammo` and `reload_time` already travel on. Jill:
    Valentine's 9-round AR fires every 0.4 sec, not the class's 1/12."""
    records = generate_segmented_shots(AR_SLOW, [], 10.0)
    assert [r.time for r in records][:4] == pytest.approx([0.0, 0.4, 0.8, 1.2])
    # 9 rounds at 0.4 sec, then the 1.0-sec reload plus the fixed segment.
    assert records[9].time == pytest.approx(9 * 0.4 + RELOAD_FIXED_SECONDS + 1.0)


def test_a_base_profile_without_one_still_takes_the_class_rate():
    records = generate_segmented_shots(AR_BASE, [], 10.0)
    assert [r.time for r in records][:3] == [0.0, pytest.approx(1 / 12),
                                             pytest.approx(2 / 12)]


def test_base_resumes_with_fresh_magazine_at_window_end():
    seg = {"start": 10.0, "end": 20.0, "profile": TICKER}
    records = generate_segmented_shots(SR_BASE, [seg], 60.0)
    after = [r for r in records if r.time >= 20.0]
    # 새 매거진 즉시: 첫 발은 20.0 + 차지 1발 시간, first_bullet 플래그
    assert after[0].time == 20.0 + 1.0
    assert after[0].is_first_bullet


def test_until_shots_single_charged_shot_then_resume():
    seg = {"start": 10.0, "until_shots": 1, "profile": CANNON}
    records = generate_segmented_shots(SR_BASE, [seg], 60.0)
    cannon_shots = [r for r in records if r.damage_percent == 499.5]
    assert len(cannon_shots) == 1
    assert cannon_shots[0].time == 15.0            # 10.0 + 차지 5초 (버프 없음)
    assert cannon_shots[0].extra_charge_bonus == 9.0  # 1000%/100 - 1
    # 기본 무기는 그 발사 시각부터 새 매거진으로 재개
    resumed = [r for r in records if r.time > 15.0 and r.damage_percent == 69.04]
    assert resumed[0].time == 15.0 + 1.0


def test_shot_records_carry_in_segment_flag():
    seg = {"start": 10.0, "until_shots": 1, "profile": CANNON}
    records = generate_segmented_shots(SR_BASE, [seg], 60.0)
    assert all(r.in_segment == (r.damage_percent == 499.5) for r in records)


def test_charge_speed_callable_shortens_profile_charge():
    seg = {"start": 10.0, "until_shots": 1, "profile": CANNON}
    records = generate_segmented_shots(
        SR_BASE, [seg], 60.0, charge_speed_percent_at=lambda t: 1.0)
    cannon = [r for r in records if r.damage_percent == 499.5][0]
    # +100% shortens the 5s cannon charge to zero, so it fires one floor-gap in.
    # A transform profile has no rate of fire of its own, so only the frame grid
    # bounds it.
    assert cannon.time == pytest.approx(10.0 + 1 / 60)


def test_fight_duration_clips_segment_shots():
    seg = {"start": 178.0, "until_shots": 33,
           "profile": {"weapon": "SR", "damage_percent": 51.46,
                       "charge_damage_percent": 343.36, "rate_of_fire": 3.3}}
    records = generate_segmented_shots(SR_BASE, [seg], 180.0)
    seg_shots = [r for r in records if r.damage_percent == 51.46]
    assert all(r.time < 180.0 for r in seg_shots)
    assert len(seg_shots) < 33


def test_a_window_reopened_before_it_closed_runs_on_the_new_windows_clock():
    # 같은 변형이 아직 열려 있는 창을 다시 열면 지속시간이 **새 발동 기준으로**
    # 갱신된다(Fienn 판정, 2026-08-06). 그래서 이전 창은 재발동 시각에서 끊기고
    # 새 창이 자기 시각부터 케이던스를 세운다 - 변형 자체는 한 순간도 안 풀린다.
    reopened = [{"start": 10.0, "end": 20.0, "profile": TICKER},
                {"start": 15.1, "end": 25.0, "profile": TICKER}]
    records = generate_segmented_shots(SR_BASE, reopened, 60.0)
    times = [r.time for r in records]
    # 10.0~25.0 사이에 기본 무기가 한 발도 안 나간다 (창이 안 끊긴다)
    assert all(r.damage_percent == 22.2 for r in records if 10.0 <= r.time < 25.0)
    # 첫 창은 15.1에서 끊긴다 - 이어졌다면 15.25에 한 발이 더 있었다
    assert not [t for t in times if 15.1 < t < 15.35]
    # 새 창의 첫 발은 자기 시작 + 1/rate
    assert pytest.approx(15.35) in times
    # 25.0 이후 기본 무기 복귀
    assert any(r.time >= 25.0 and r.damage_percent == 69.04 for r in records)


def test_a_window_still_running_at_the_bell_never_hands_the_weapon_back():
    # `until_shots` 창은 마지막 발이 전투 밖이면 전투가 끝날 때까지 계속 들고 있는
    # 것이다. 창의 끝을 "실제로 쏜 마지막 발"로 접으면 매거진 베이스가 그 뒤로
    # 돌아온다 - 새 매거진의 0번 탄은 재개 시각에 바로 나가므로 눈에 보인다.
    seg = {"start": 178.0, "until_shots": 33, "profile": TICKER}
    records = generate_segmented_shots(AR_BASE, [seg], 180.0)
    assert [r.time for r in records if r.time >= 178.0 and r.damage_percent == 14.71] == []


def test_overlapping_segments_of_different_profiles_rejected():
    # 갱신은 같은 변형일 때의 이야기다. 서로 다른 프로필이 겹치면 어느 무기를
    # 들고 있는지 정해지지 않으므로 여전히 표현할 수 없다.
    segs = [{"start": 10.0, "end": 20.0, "profile": TICKER},
            {"start": 15.0, "end": 25.0, "profile": CANNON}]
    with pytest.raises(ValueError):
        generate_segmented_shots(SR_BASE, segs, 60.0)


def test_unsorted_segments_rejected():
    segs = [{"start": 25.0, "end": 30.0, "profile": TICKER},
            {"start": 10.0, "end": 20.0, "profile": TICKER}]
    with pytest.raises(ValueError):
        generate_segmented_shots(SR_BASE, segs, 60.0)


def test_magazine_base_resumes_at_the_same_instant_as_a_charged_segments_final_shot():
    # Pins the live snow-white combination: an AR (magazine) base with a
    # until_shots=1 charge-profile segment (CANNON, same shape as her Seven
    # Dwarves: I transform). A magazine base's fresh-magazine round 0 fires
    # AT magazine_start (see generate_magazine_shot_times), so the resumed
    # AR's FIRST shot lands at the SAME instant as the segment's one and
    # only (charge) shot - not one interval later, unlike a charge base
    # (see test_until_shots_single_charged_shot_then_resume).
    seg = {"start": 10.0, "until_shots": 1, "profile": CANNON}
    records = generate_segmented_shots(AR_BASE, [seg], 60.0)
    # (a) base AR shots are silenced for the whole segment window
    silenced = [r for r in records
                if 10.0 <= r.time < 15.0 and r.damage_percent == AR_BASE["damage_percent"]]
    assert silenced == []
    # (c) the cannon record carries the segment profile's percent
    cannon_shots = [r for r in records if r.damage_percent == CANNON["damage_percent"]]
    assert len(cannon_shots) == 1
    assert cannon_shots[0].time == 15.0  # 10.0 + charge_time 5.0 (no buffs)
    # (b) the resumed AR magazine's first shot lands at that SAME instant,
    # flagged is_first_bullet
    resumed_first = [r for r in records
                      if r.time == 15.0 and r.damage_percent == AR_BASE["damage_percent"]]
    assert len(resumed_first) == 1
    assert resumed_first[0].is_first_bullet


# Fienn's six readings, 60fps, 2026-07-29 - the measurements the affine model
# was fitted to, promoted to a regression anchor. Max residual is 1.12 frames
# (Privaty unbuffed), so the bound is 1.2 frames. Raw and what they do and do
# not settle: docs/measurements/reload-affine.md.
RELOAD_READINGS = [
    # (file reload, reload speed, measured seconds)
    (1.0, 0.0000, 1.1667),   # Privaty, AR, unbuffed
    (1.0, 0.2969, 0.8333),   # + Resilience cube
    (1.0, 0.8085, 0.3500),   # + cube and Privaty's own buff
    (2.5, 0.0000, 2.6500),   # Rapi: Red Hood, MG, unbuffed
    (2.5, 0.2969, 1.9000),
    (2.5, 0.8085, 0.6400),
]


def test_the_model_reproduces_every_measured_reload():
    for file_value, speed, measured in RELOAD_READINGS:
        assert reload_time_with_speed(file_value, speed) == pytest.approx(
            measured, abs=1.2 / 60), f"file {file_value} at {speed:.4%}"


def test_an_unbuffed_reload_is_the_file_value_plus_the_fixed_segment():
    """The model's core reinterpretation: the data file's reloadTime is the part
    a buff scales, not the reload itself. Privaty's 1.0-sec file value measures
    1.1667 in game with nothing on her."""
    assert reload_time_with_speed(1.0, 0.0) == pytest.approx(1.148)
    assert reload_time_with_speed(2.5, 0.0) == pytest.approx(2.648)


def test_reload_speed_reduction_lengthens_the_reload():
    """Milk: Blooming Bunny's forced reload - "reload speed fixed at a 50%
    reduction" - scales her 2-sec file value by 1.5. She reads 3.0 sec in game
    (Fienn, 2026-07-20), which is the file value alone; the fixed segment is
    taken as global anyway (Fienn, 2026-07-31), so the model says 3.148 and that
    reading is treated as too coarse to resolve 9 frames."""
    assert reload_time_with_speed(2.0, -0.5) == pytest.approx(3.148)


def test_enough_reload_speed_removes_the_reload_entirely():
    """The observation that killed the reciprocal form: Crown + Privaty + the
    Resilience cube reach 125.20% and the reload disappears. `time / (1 + s)`
    cannot reach zero at any speed; this form reaches it at 1 + 0.148/file."""
    assert reload_time_with_speed(1.0, 1.148) == pytest.approx(0.0)
    assert reload_time_with_speed(1.0, 1.2520) == 0.0
    assert reload_time_with_speed(2.5, 1.2520) == 0.0


def test_the_reload_never_goes_negative():
    for speed in (1.5, 2.0, 10.0):
        assert reload_time_with_speed(1.0, speed) == 0.0


# --- charge speed: frame quantisation + caster-based flat reductions ---

def test_charge_speed_reduction_is_quantised_to_whole_frames():
    # The game reduces charge time by whole frames: community testing describes
    # "180 frames x 10.28% = 18.5 frames". Neon: Vision Eye's 9.47% overload on
    # a 1.0s charge measured 0.9178s, which the floored 5-frame step reproduces
    # to 0.07 frames where the continuous value is 0.75 frames off.
    assert charge_time_with_speed(1.0, 0.0947) == pytest.approx(1.0 - 5 / 60)
    # 10% of 60 frames is exactly 6, so no rounding happens there.
    assert charge_time_with_speed(1.0, 0.10) == pytest.approx(1.0 - 6 / 60)


def test_the_charge_left_by_a_flat_cut_keeps_its_fraction():
    """Only the PERCENT cut lands on frames. A flat cut can leave a fraction of
    a frame and that fraction survives - the charge is not snapped back onto the
    grid afterwards.

    Scarlet: Black Shadow is the case that matters and she needs
    `shot_interval_with_speed`, because her 0.30 charge sits under every floor
    in the table and only the timed-delay branch skips it."""
    from app.attack_rate import shot_interval_with_speed

    # 0.30 - 0.1911 = 0.1089 sec of charge left - 6.53 frames, carried as such.
    assert shot_interval_with_speed(
        0.30, 0.0, 0.1274 * 1.5, motion_delay=0.43) == pytest.approx(0.1089 + 0.43)
    assert charge_time_with_speed(1.0, 0.0, flat_reduction_sec=0.05) == pytest.approx(0.95)
    # A percent cut still lands on whole frames, and a frame-aligned input comes
    # back untouched: `1.0 - 1/60` must not lose a frame to float error.
    assert charge_time_with_speed(1.0, 0.02) == pytest.approx(59 / 60)
    assert charge_time_with_speed(1.0, 0.0) == pytest.approx(1.0)


def test_charge_speed_percent_applies_to_the_units_own_charge_time():
    # The percent scales the charge time it applies to, so the same buff buys
    # less absolute time on a shorter charge.
    assert charge_time_with_speed(1.5, 0.10) == pytest.approx(1.5 - 9 / 60)
    assert charge_time_with_speed(0.5, 0.10) == pytest.approx(0.5 - 3 / 60)


def test_flat_reduction_subtracts_absolute_seconds_on_top():
    # "Caster-based" buffs (Liberalio, Mana) hand over SECONDS, computed from
    # the caster's charge time, so they do not scale with the recipient's - and
    # the subtraction is plain, leaving whatever fraction of a frame it leaves.
    assert charge_time_with_speed(1.0, 0.0, flat_reduction_sec=0.1911) == pytest.approx(0.8089)
    assert charge_time_with_speed(1.5, 0.0, flat_reduction_sec=0.1911) == pytest.approx(1.3089)


def test_flat_reduction_and_percent_compose():
    # Percent first (on the unit's own charge), then the absolute seconds.
    assert charge_time_with_speed(1.0, 0.10, flat_reduction_sec=0.2) == pytest.approx(
        1.0 - 6 / 60 - 0.2)


def test_charge_floor_still_bounds_the_combination():
    # A huge flat reduction cannot drive the interval below the unit's floor -
    # and with no rate of fire known, below one frame.
    assert charge_time_with_speed(1.0, 0.0, flat_reduction_sec=5.0) == pytest.approx(1 / 60)
    assert charge_time_with_speed(
        1.0, 0.0, flat_reduction_sec=5.0,
        interval_floor=charge_interval_floor_for("neon-vision-eye")) == pytest.approx(0.2)


# --- per-unit charge motion delay --------------------------------------------
# Fienn timed about 0.4 sec between a charged shot firing and the next charge
# starting (2026-07-28). It is a property of the UNIT, not the weapon: Liberalio
# is a Sniper Rifle with no gap at all, and handing it to every charge weapon
# drops Scarlet: Black Shadow from 0.981x of her recorded damage to 0.559x.

def test_a_measured_pause_replaces_the_floor_instead_of_stacking_on_it():
    """The two bounds are alternatives, not layers. A weapon with no pause is
    bounded by its own rate of fire once charge speed drives the charge to
    zero; a weapon WITH a pause is bounded by that pause, and applying both
    would count the same wait twice.
    """
    from app.attack_rate import shot_interval_with_speed

    # No pause: the weapon's own floor bounds her.
    assert shot_interval_with_speed(
        1.0, 1.0, interval_floor=charge_interval_floor_for("neon-vision-eye")) == 0.2
    assert shot_interval_with_speed(1.0, 0.0) == 1.0
    # Measured: the pause is the bound. Stacking the floor on top of it had Mint
    # firing every 0.735 sec at full charge speed instead of every 0.39.
    assert shot_interval_with_speed(1.0, 1.0, motion_delay=0.39) == pytest.approx(0.39)
    # And a charge already quicker than the floor keeps benefiting from a buff:
    # Scarlet charges in 0.30 sec, which the floor used to pin in place.
    assert shot_interval_with_speed(0.30, 0.5, motion_delay=0.43) == pytest.approx(0.58)
    assert shot_interval_with_speed(0.30, 0.0, motion_delay=0.43) == pytest.approx(0.73)


def test_charge_motion_delay_is_a_per_unit_list_not_a_weapon_class_constant():
    from app.skill_rules.registry import get_charge_motion_delay
    from app.attack_rate import CHARGE_MOTION_DELAY_SECONDS
    # Units whose own timing happened to land on the shared default.
    for slug in ("helm", "helm-signature", "velvet"):
        assert get_charge_motion_delay(slug) == CHARGE_MOTION_DELAY_SECONDS
    # Bready is the same weapon class as those three and lands somewhere else,
    # which is the point: 22 frames, not the 24 the default would hand her.
    assert get_charge_motion_delay("bready-lingering") == pytest.approx(22 / 60)
    assert get_charge_motion_delay("bready-lingering") != CHARGE_MOTION_DELAY_SECONDS
    # Liberalio is the counter-example that makes this per-unit: also SR, and
    # Fienn confirms she fires her charged shots back to back with no gap.
    assert get_charge_motion_delay("liberalio") == 0.0
    assert get_charge_motion_delay("neon-vision-eye") == 0.0


def test_an_untimed_charge_weapon_carries_the_measured_stand_in_not_zero():
    """Zero is not the neutral choice for a unit nobody has timed - it models
    her as the fastest version of herself, which is what put Mint at 1.502x of
    her record. Until someone puts a clock on her she carries the frame-resolved
    pause Bready and Centi share, one SR and one RL."""
    from app.skill_rules.registry import (ASSUMED_CHARGE_MOTION_DELAY_SECONDS,
                                          INFERRED_NO_CHARGE_MOTION_DELAY,
                                          NO_CHARGE_MOTION_DELAY,
                                          TAP_FIRE_MANUAL_MOTION_DELAY,
                                          TIMED_CHARGE_MOTION_DELAY,
                                          get_charge_motion_delay)

    assert ASSUMED_CHARGE_MOTION_DELAY_SECONDS == pytest.approx(22 / 60)
    # Ein used to be in this list and no longer belongs: she was timed on
    # 2026-08-20 and her auto reading landed on the same 22 frames, so she stops
    # being an example of "nobody looked" without any number moving.
    for slug in ("maiden-ice-rose", "red-hood", "takina-inoue"):
        assert get_charge_motion_delay(slug) == pytest.approx(22 / 60), slug
    # Cinderella is not one of them either, but for the opposite reason: the
    # 10/29 she used to carry was never a pause, it was her weapon's 180
    # rounds/min showing through once her charge hit zero.
    assert get_charge_motion_delay("cinderella") == 0.0
    assert charge_interval_floor_for("cinderella") == pytest.approx(1 / 3)
    # A measured answer always wins over the stand-in, in both directions.
    for slug in NO_CHARGE_MOTION_DELAY | INFERRED_NO_CHARGE_MOTION_DELAY:
        assert get_charge_motion_delay(slug) == 0.0, slug
    # One exception, and it is NOT about precedence between guess and
    # measurement: a tap-fire candidate is played BY HAND, so her manual pause
    # overrides an AUTO measurement of the same unit
    # (registry.TAP_FIRE_MANUAL_MOTION_DELAY). The timed reading is not wrong -
    # it is a reading of the other input, and Ein measured the two 8.4 frames
    # apart. Milk: Blooming Bunny is the only unit in that position today.
    for slug, delay in TIMED_CHARGE_MOTION_DELAY.items():
        if slug in TAP_FIRE_MANUAL_MOTION_DELAY:
            assert get_charge_motion_delay(slug) == TAP_FIRE_MANUAL_MOTION_DELAY[slug], slug
            continue
        assert get_charge_motion_delay(slug) == pytest.approx(delay), slug


def test_no_charge_weapon_is_left_silently_at_zero():
    """The audit's UNVERIFIED bucket is what "nobody looked" looks like, and an
    empty one is the invariant this pins: every encoded charge weapon is either
    timed, confirmed to have none, or carrying the stand-in."""
    import json
    from pathlib import Path

    from app.skill_rules.registry import (INFERRED_NO_CHARGE_MOTION_DELAY,
                                          NO_CHARGE_MOTION_DELAY,
                                          TIMED_CHARGE_MOTION_DELAY,
                                          _BUILDERS, get_charge_motion_delay)

    root = Path(__file__).resolve().parent.parent.parent
    silent = []
    for slug in sorted(_BUILDERS):
        weapon = None
        parts = slug.split("-")
        for cut in range(len(parts), 0, -1):
            base = "-".join(parts[:cut])
            for source in ("lootandwaifus", "dotgg"):
                path = root / "data" / source / f"char_{base}.json"
                if weapon is None and path.exists():
                    weapon = json.loads(path.read_text(encoding="utf-8")).get("weapon")
        if weapon not in ("SR", "RL"):
            continue
        known = (slug in TIMED_CHARGE_MOTION_DELAY
                 or slug in NO_CHARGE_MOTION_DELAY
                 or slug in INFERRED_NO_CHARGE_MOTION_DELAY)
        if not known and not get_charge_motion_delay(slug):
            silent.append(slug)
    assert silent == []


def test_a_zero_pause_charge_weapon_always_has_a_rate_of_fire():
    """The floor branch of `shot_interval_with_speed` is only reachable by a
    unit whose pause is zero, and for her the bound has to come from somewhere.
    Every one of them carries her weapon's own rate of fire - which follows
    from a mechanism rather than a coincidence: `shot_detail.input_type` splits
    the 31 collected charge weapons into `UP` (fires on release, so there is a
    fire-to-charge pause, and rpm is a 60 placeholder nobody reads) and
    `DOWN_Charge` (charges and fires while held, so no pause, and the loop's
    own speed is the floor). `scripts/audit_rate_of_fire.py` checks that split
    against the collected data; this pins the engine-side half of it, so a new
    zero-pause unit missing from the table cannot be modelled as able to fire
    arbitrarily fast under charge speed."""
    from app.skill_rules.registry import (INFERRED_NO_CHARGE_MOTION_DELAY,
                                          NO_CHARGE_MOTION_DELAY,
                                          get_charge_motion_delay)

    for slug in NO_CHARGE_MOTION_DELAY | INFERRED_NO_CHARGE_MOTION_DELAY:
        assert charge_interval_floor_for(slug) is not None, slug
    # The reverse too: a pause and a rate-of-fire floor are ALTERNATIVES, so a
    # unit in the table who also carried a pause would have one of the two
    # silently unread.
    for slug in CHARGE_ROUNDS_PER_MINUTE:
        assert get_charge_motion_delay(slug) == 0.0, slug


def test_a_timed_unit_carries_its_own_delay_rather_than_the_shared_default():
    """Fienn timed Mint and Prika the same way he timed Snow White, reading the
    gap between a charged bullet leaving and the next charge gauge starting off
    the Full Burst clock (2026-07-28, 60 FPS so ~0.01 sec of noise):
        Mint   0.39 / 0.40 / 0.39
        Prika  0.36 / 0.34 / 0.33
    Their shot-to-shot gaps confirm the model rather than just the number - 1.40
    sec for Mint and 1.36/1.35 for Prika, against a 1.0 sec charge time, so the
    interval really is charge + delay. The values differ per unit, which is why
    this is a mapping and not one constant over a list."""
    from app.skill_rules.registry import get_charge_motion_delay

    assert get_charge_motion_delay("mint") == 0.39
    assert get_charge_motion_delay("prika") == 0.34
    assert get_charge_motion_delay("ade-agent-bunny") == 0.35
    assert get_charge_motion_delay("anchor-innocent-maid") == 0.4


def test_the_borrowed_default_was_timed_and_held():
    """Helm and Velvet carried Snow White's 0.4 on Fienn's naked-eye "there is a
    pause" until he timed both (2026-07-29), reading charge completion against
    next-charge start:
        Helm    0.39 / 0.40 / 0.39 / 0.40 / 0.40
        Velvet  0.40 / 0.40 / 0.40 / 0.39 / 0.40
    The borrowed value was right, so no damage moves - what changes is that
    these stop being assumptions. Their shot gaps check the model again
    (1.380 / 1.393 against charges of 0.987 / 0.997, so interval - delay lands
    back on the charge every time)."""
    from app.skill_rules.registry import TIMED_CHARGE_MOTION_DELAY, get_charge_motion_delay

    for slug in ("helm", "helm-signature", "velvet"):
        assert slug in TIMED_CHARGE_MOTION_DELAY, f"{slug} is still an assumption"
        assert get_charge_motion_delay(slug) == 0.4


def test_bready_pause_is_a_whole_number_of_frames():
    """Bready's pause is the one read off raw video frame numbers rather than the
    Full Burst clock, whose 0.01-sec display skips 0.04 in places and cannot
    separate 22 frames from 24. 49 readings put it at 22 frames.

    The reading is checked three ways rather than trusted alone: her charge reads
    57 frames, her shot gap 78.9696 +- 0.0319 frames, and charge + pause lands
    within 0.042 of a frame of that gap. Pinned as a frame count because that is
    the grid the measurement resolved, and a decimal would hide it -
    docs/measurements/bready-charge.md."""
    from app.skill_rules.registry import get_charge_motion_delay

    for slug in ("bready-lingering", "bready-recommended"):
        assert get_charge_motion_delay(slug) == pytest.approx(22 / 60)
    # Charge + pause returns the measured shot gap. This is what makes the pause
    # a reading rather than a parameter fitted to one number.
    charge = charge_time_with_speed(1.00, 0.0609)
    assert charge + get_charge_motion_delay("bready-lingering") == pytest.approx(
        78.9696 / 60, abs=0.042 / 60)


def test_charge_speed_lands_on_frames_not_on_a_hundredth_of_a_second():
    """Bready's 6.09% charge-speed overload buys 3 whole frames of her 1.00-sec
    charge and the remaining 1.09%p is wasted, because a frame costs 1/60 =
    1.6667% and the fourth frame needs 6.667%.

    This is the anchor for the frame grid itself. Community guides report charge
    speed rounding to 0.01 sec instead, which would take the full 0.0609 off and
    leave 0.94 - a charge of 56.4 frames. Fienn's 51 charge readings put her at
    57 frames: 83% of the readings that came out 56 or 57 were 57 where the
    0.01-sec rule predicts 40% (5.6 sigma), and her shot gap sits 1.0 sigma from
    a whole 79 frames where that rule needs 78.4 or 79.4 (13.5 sigma). See
    docs/measurements/bready-charge.md for both arguments and what they rest
    on."""
    assert charge_time_with_speed(1.00, 0.0609) == pytest.approx(0.95)
    assert charge_time_with_speed(1.00, 0.0609) != pytest.approx(0.94)
    # The step is a frame wide: everything from the third frame up to the fourth
    # threshold buys the same 3 frames, so paying more changes no number.
    for percent in (0.05, 0.0521, 0.0609, 0.0666):
        assert charge_time_with_speed(1.00, percent) == pytest.approx(0.95)
    assert charge_time_with_speed(1.00, 0.0667) == pytest.approx(1.00 - 4 / 60)


def test_no_delay_confirmed_is_recorded_separately_from_never_checked():
    """The engine treats an unchecked charge weapon as having no pause, so a
    unit nobody has looked at is indistinguishable from one Fienn has checked -
    and the first is a silent over-estimate. Naming the confirmed-none units
    keeps `scripts/audit_charge_motion_delay.py` able to tell them apart."""
    from app.skill_rules.registry import (
        NO_CHARGE_MOTION_DELAY, TIMED_CHARGE_MOTION_DELAY, get_charge_motion_delay)

    for slug in ("liberalio", "neon-vision-eye", "laplace-ultimate-hero", "anis-star"):
        assert slug in NO_CHARGE_MOTION_DELAY
        assert get_charge_motion_delay(slug) == 0.0
    # Timed and confirmed-none are disjoint: a unit cannot be both.
    assert not (TIMED_CHARGE_MOTION_DELAY.keys() & NO_CHARGE_MOTION_DELAY)


def test_charge_motion_delay_lengthens_the_shot_interval_and_nothing_else():
    base = {"weapon": "SR", "damage_percent": 69.04, "max_ammo": 6,
            "reload_time": 2.0, "charge_time": 1.2, "charge_damage_percent": 250.0}
    without = generate_segmented_shots(base, [], 30.0)
    with_delay = generate_segmented_shots({**base, "charge_motion_delay": 0.4}, [], 30.0)
    # First shot lands one charge in, so the delay shows up immediately...
    assert round(without[0].time, 4) == 1.2
    assert round(with_delay[0].time, 4) == 1.6
    # ...and every gap inside a magazine grows by exactly the delay.
    assert round(without[1].time - without[0].time, 4) == 1.2
    assert round(with_delay[1].time - with_delay[0].time, 4) == 1.6
    # Fewer shots fit, which is the whole point.
    assert len(with_delay) < len(without)


# --- The cadence floor is the weapon's own rate of fire --------------------
# A charge weapon with no fire-to-charge pause is bounded instead by
# `shot_detail.rate_of_fire`, which is per unit (attack_rate's
# CHARGE_ROUNDS_PER_MINUTE). A unit whose pause HAS been timed already carries
# that bound explicitly, so flooring her charge on top double-counts it, and
# for a charge shorter than the floor it cancels charge-speed buffs outright.

def test_a_timed_units_charge_is_not_floored_because_her_delay_already_bounds_her():
    """Scarlet: Black Shadow's real cycle is a 0.30 sec charge plus a 0.43 sec
    motion delay (Fienn, 2026-07-28). Liberalio cuts a flat 0.19 sec off the
    CHARGE. Flooring the 0.30 charge at all would swallow the whole cut."""
    from app.attack_rate import shot_interval_with_speed

    unbuffed = shot_interval_with_speed(0.30, 0.0, 0.0, motion_delay=0.43)
    with_liberalio = shot_interval_with_speed(0.30, 0.0, 0.19, motion_delay=0.43)

    assert unbuffed == pytest.approx(0.73, abs=0.001)
    assert with_liberalio == pytest.approx(0.54, abs=0.001)


def test_a_unit_with_no_pause_is_bounded_by_her_own_rate_of_fire():
    """Cinderella holds a permanent +100% charge speed from her own kit, so her
    charge is zero all fight and her weapon's 180 rounds/min IS her cadence.
    Her old 10/29 was that same number read one shot short."""
    from app.attack_rate import shot_interval_with_speed

    floor = charge_interval_floor_for("cinderella")
    assert shot_interval_with_speed(1.0, 1.0, interval_floor=floor) == pytest.approx(1 / 3)
    assert shot_interval_with_speed(1.0, 0.0, interval_floor=floor) == pytest.approx(1.0)


def test_a_timed_delay_bounds_the_cadence_where_the_floor_used_to():
    # Mint at +100% charge speed: her charge really does reach zero, and what is
    # left is her own 0.39, not another unit's floor stacked on top of it.
    from app.attack_rate import shot_interval_with_speed

    assert shot_interval_with_speed(1.0, 1.0, motion_delay=0.39) == pytest.approx(0.39)


def test_the_sword_swingers_decompose_into_charge_plus_delay():
    """Scarlet: Black Shadow and Raven both measured far slower than their data
    said, and both were modelled by overwriting charge_time with the whole
    measured interval. Timing the fire-to-charge gap the same way as Mint's
    (Fienn, 2026-07-28) splits that interval and vindicates the data files:

        Scarlet  delay 0.43, interval 0.7325  ->  charge 0.3025  (file says 0.30)
        Raven    delay 1.014, interval 2.0275 ->  charge 1.0135  (file says 1.0)

    The split is not cosmetic. Charge-speed buffs apply to the charge and not to
    the delay, and Scarlet is played with Liberalio precisely for that buff.
    """
    from app.skill_rules.registry import get_charge_motion_delay
    assert get_charge_motion_delay("scarlet-black-shadow") == 0.43
    assert get_charge_motion_delay("raven") == 1.014


def test_scarlet_keeps_her_measured_cadence_after_the_split():
    """Her measured cadence, anchored on the comparison that needs no assumption
    about the motion delay.

    Fienn read the damage numbers off the Full Burst clock frame by frame. The
    delay is only known to the nearest 0.01 sec (0.44/0.42/0.44/0.42/0.43), so
    an ABSOLUTE interval can only be pinned to about a third of a frame. But
    subtracting the Liberalio-accompanied interval from the solo interval within
    one account CANCELS the delay and leaves her grant alone, and that survives
    a much tighter bound. Main account, four solo and two accompanied windows
    (2026-07-30): 0.73371 and 0.54352 sec, so a grant of 0.19019.

    The grant assertion is what makes this test load-bearing: snapping the
    surviving charge back onto the frame grid would make the effective grant
    0.20000, which misses by 0.59 frames.

    A second account reads 0.20229 for the same quantity and nothing known
    separates the two - see docs/measurements/scarlet-black-shadow-charge.md.
    """
    from app.attack_rate import shot_interval_with_speed
    from app.skill_rules.registry import get_charge_motion_delay

    delay = get_charge_motion_delay("scarlet-black-shadow")
    liberalio_cut = 0.1274 * 1.5
    frame = 1 / 60

    solo = shot_interval_with_speed(0.30, 0.0, 0.0, delay)
    accompanied = shot_interval_with_speed(0.30, 0.0, liberalio_cut, delay)

    assert solo - accompanied == pytest.approx(0.19019, abs=0.1 * frame)
    # Absolute intervals inherit the delay's own precision, so they get a
    # looser bound than the difference above.
    assert solo == pytest.approx(0.73371, abs=0.35 * frame)
    assert accompanied == pytest.approx(0.54352, abs=0.35 * frame)


def _centi_weapon(reload_time):
    """Centi's real weapon profile: RL, 6 rounds, 1.0 sec charge, and the 22
    frame pause Fienn timed between a shot and the next charge."""
    return {
        "weapon": "RL", "charge_time": 1.0, "max_ammo": 6,
        "reload_time": reload_time, "damage_percent": 100.0,
        "charge_damage_percent": 250.0, "charge_motion_delay": 22 / 60,
    }


def _shot_times(reload_time, duration=60.0):
    return [r.time for r in generate_segmented_shots(
        _centi_weapon(reload_time), [], duration)]


def test_centis_clip_reload_costs_three_loads_not_one():
    """Her three 0.5-sec loads, not one - the clip fix this pins.

    Fienn timed her at 1.617 sec a shot: six shots at charge + pause is 8.2 sec
    and three loads close the cycle at 9.7. Modelling ONE reload gives 8.7 / 6 =
    1.45, about 11% fast, which is the error this test exists to catch.

    The engine now reads 9.848 rather than 9.7, because the affine reload model
    adds a fixed 0.148-sec segment to every reload and Fienn ruled that segment
    global (2026-07-31) even though her loads measure the file value exactly.
    So this pins the load COUNT - the thing the clip fix decides - and records
    that the cadence sits 0.148 sec above her reading by that ruling. If the
    fixed segment is ever measured per weapon class, her 9.7 comes back.
    """
    clip = _shot_times(1.5)
    single = _shot_times(0.5)
    assert round(clip[6] - clip[0], 4) == 9.848
    assert round(single[6] - single[0], 4) == 8.848   # one load: still 11% fast
    assert round((clip[6] - clip[0]) / 6, 4) == 1.6413


def test_the_clip_reload_only_moves_shots_after_the_magazine_empties():
    # The loads run back-to-back once the magazine is out, so her first six
    # shots are untouched and the seventh is a full second later - the two extra
    # loads, and only those. The fixed reload segment lands once either way, so
    # it cancels out of that one-second difference.
    clip, single = _shot_times(1.5), _shot_times(0.5)
    assert clip[:6] == single[:6]
    assert round(clip[6], 4) == 11.2147
    assert round(single[6], 4) == 10.2147
    assert round(clip[11], 4) == 18.048
    assert len(clip) == 36
    assert len(single) == 41


@pytest.mark.parametrize("speed", [0.2969, 0.8085, -0.5])
def test_the_scaled_part_multiplies_cleanly_through_a_reload_speed_buff(speed):
    """Why the load count may be multiplied at roster assembly rather than
    inside attack_rate: the buff scales the file value linearly, so scaling
    before or after it is the same number. (0.2969 is the cube, 0.8085 cube +
    Privaty, -0.5 the negative direction.)"""
    scaled = lambda t: reload_time_with_speed(t, speed) - RELOAD_FIXED_SECONDS
    assert scaled(0.5 * 3) == pytest.approx(scaled(0.5) * 3, abs=1e-12)


@pytest.mark.parametrize("speed", [0.0, 0.2969, -0.5])
def test_a_clip_weapon_pays_the_fixed_segment_once_per_magazine(speed):
    """The fixed segment is NOT linear, and that is the point. Folding Centi's
    three loads into one 1.5-sec file value charges the segment once for the
    magazine; charging it per load would add it three times. Once is the
    convention Fienn confirmed for the charge motion delay on the same reload
    (2026-07-31)."""
    folded = reload_time_with_speed(0.5 * 3, speed)
    per_load = 3 * reload_time_with_speed(0.5, speed)
    assert per_load - folded == pytest.approx(2 * RELOAD_FIXED_SECONDS)


# --- a refund declared windowed but resolved to no windows must fail closed --
# `needs_own_burst_window=True` (Arcana: Fortune Mate's rotation reload) means
# the registry could not fill `windows` itself and is trusting the simulator
# to do it once the burst schedule exists. If that owner's burst never lands
# before the fight ends, the simulator hands back `windows=()` - and the
# refund must go permanently silent, not fall back to firing on every shot of
# the fight the way a bare, undeclared refund would.

def test_a_refund_declared_windowed_but_resolved_to_none_is_permanently_inert():
    # rounds=1 (not Arcana's real 6) so the comparison object below - what
    # misclassifying `windowless` as plain would make it behave like - can
    # actually be walked: a 6-for-6 ratio trips `_refund_sequence`'s
    # unrelated "never empties" guard on its own (1.0 >= 1) regardless of
    # windowing, which would crash this comparison rather than demonstrate
    # the fail-open it stands in for.
    unrestricted = AmmoRefund(every_shots=6, rounds=1, first_shot=2)
    windowless = AmmoRefund(every_shots=6, rounds=1, first_shot=2,
                            needs_own_burst_window=True)  # windows never resolved

    unbuffered = generate_magazine_shot_times(12.0, 18, 1.5, 20.0)
    with_unrestricted = generate_magazine_shot_times(
        12.0, 18, 1.5, 20.0, ammo_refund=unrestricted)
    with_windowless = generate_magazine_shot_times(
        12.0, 18, 1.5, 20.0, ammo_refund=windowless)

    # Misclassifying `windowless` as plain (fail-open) would make it behave
    # exactly like `unrestricted` - refilling all fight on the bare phase and
    # firing more shots than the unbuffered baseline. Classified correctly,
    # it fires nowhere (empty `windows` never contains any time) and the
    # timeline is untouched.
    assert with_windowless == unbuffered
    assert len(with_unrestricted) > len(unbuffered)


def test_a_shared_magazine_walk_drops_a_windowed_refund_instead_of_running_it_unrestricted():
    # Mirrors test_a_refund_declared_windowed_but_resolved_to_none_is_permanently_inert
    # for `_shared_magazine_shots` (Snow White: Heavy Arms' shares_magazine walk):
    # it keeps no per-window counter of its own, so a refund gated to windows -
    # even one whose windows never resolved - must be dropped before the walk
    # rather than firing on every shot ungated.
    base = {"weapon": "SR", "max_ammo": 6, "reload_time": 2.0, "charge_time": 1.2,
            "damage_percent": 100.0, "charge_damage_percent": 200.0}
    segment = [{"start": 5.0, "until_shots": 3, "shares_magazine": True,
               "profile": {"weapon": "SR", "charge_time": 3.2,
                           "damage_percent": 100.0, "charge_damage_percent": 200.0}}]
    unrestricted = AmmoRefund(every_shots=6, rounds=1, first_shot=2)
    windowless = AmmoRefund(every_shots=6, rounds=1, first_shot=2,
                            needs_own_burst_window=True)  # windows never resolved

    unbuffered = generate_segmented_shots(base, segment, 60.0)
    with_unrestricted = generate_segmented_shots(
        {**base, "ammo_refund": unrestricted}, segment, 60.0)
    with_windowless = generate_segmented_shots(
        {**base, "ammo_refund": windowless}, segment, 60.0)

    # Misclassifying `windowless` as plain would make it behave exactly like
    # `unrestricted` - refunding all fight ungated. This walk has no
    # per-window counter to honor a window even when one resolves, so it must
    # drop the refund entirely rather than run it unrestricted.
    assert with_windowless == unbuffered
    # `unrestricted` (not gated) must still work on this walk - over a fixed
    # 60-sec fight its extra rounds can tie the unbuffered SHOT COUNT (a
    # magazine that empties one round later reloads one round later too), so
    # the timeline itself - not its length - is what proves the refund fired.
    assert with_unrestricted != unbuffered


def test_a_refund_or_refill_needs_exactly_one_of_rounds_or_percent():
    # Neither set (a misspelled dict key resolving both to their defaults)
    # must not resolve to a silently-inert 0; both set (a stray leftover key)
    # must not silently prefer `rounds` over `percent`.
    with pytest.raises(ValueError, match="exactly one"):
        AmmoRefund(every_shots=10).rounds_for(60)
    with pytest.raises(ValueError, match="exactly one"):
        AmmoRefund(every_shots=10, rounds=3, percent=5.0).rounds_for(60)
    with pytest.raises(ValueError, match="exactly one"):
        AmmoRefill(time=1.0).rounds_for(60)
    with pytest.raises(ValueError, match="exactly one"):
        AmmoRefill(time=1.0, rounds=3, percent=5.0).rounds_for(60)


def test_timed_refills_without_a_clock_raise_a_named_error():
    # `time_of_round` defaults to None on the 3-positional-argument call
    # `charge_window.py` uses; passing refills without also passing a clock
    # must name what's missing rather than crash inside `_apply_due_refills`
    # comparing a float to None.
    with pytest.raises(ValueError, match="time_of_round"):
        magazine_shot_count(9, 0, None, refills=(AmmoRefill(time=1.0, rounds=1),))


def test_a_windowed_refund_without_a_clock_raises_a_named_error():
    windowed = AmmoRefund(every_shots=6, rounds=1, first_shot=2,
                          windows=((0.0, 5.0),))
    with pytest.raises(ValueError, match="time_of_round"):
        magazine_shot_count(9, 0, windowed)


