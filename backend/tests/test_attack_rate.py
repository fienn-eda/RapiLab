import pytest

from app.attack_rate import (
    CHARGE_INTERVAL_FLOOR_SECONDS,
    RATE_OF_FIRE_60FPS,
    ShotRecord,
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


def test_magazine_last_bullet_times_marks_the_final_round_of_each_magazine():
    # Same scenario as test_magazine_reloads_after_emptying_then_resumes:
    # shots at [0, .1, .2, .3, .4, 1.5, 1.6, 1.7, 1.8, 1.9] - the round that
    # actually empties each 5-round magazine is index 4 within it (t=0.4,
    # t=1.9), not any other shot.
    last_bullets = magazine_last_bullet_times(
        rate_of_fire=10.0, max_ammo=5, reload_time=1.0, fight_duration=3.0,
    )
    assert last_bullets == {0.4, 1.9}


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
    # shots at [1, 2, 3, 6, 7, 8] - the round that empties each 3-shot
    # magazine is the 3rd (t=3.0, t=8.0).
    last_bullets = charge_last_bullet_times(
        charge_time=1.0, reload_time=2.0, max_ammo=3, fight_duration=9.0,
    )
    assert last_bullets == {3.0, 8.0}


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
    assert charge_last_bullets == {3.0, 8.0}


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
    assert first_bullets == {0.0, 1.5}


def test_first_bullet_shot_times_ar_marks_each_magazine_start():
    # AR (12/s, 60 ammo, 1s reload): magazine empties at 5.0, reloads by 6.0 -
    # first bullets at each magazine's start: 0.0, 6.0, 12.0.
    first_bullets = first_bullet_shot_times(
        weapon="AR", max_ammo=60, reload_time=1.0, charge_time=0.0, fight_duration=12.5,
    )
    assert first_bullets == {0.0, 6.0, 12.0}


def test_charge_first_bullet_times_is_one_effective_charge_after_magazine_start():
    # Same scenario as test_charge_last_bullet_times...: shots [1,2,3, 6,7,8] -
    # the first charged shot of each magazine lands at 1.0 and 6.0.
    first_bullets = charge_first_bullet_times(
        charge_time=1.0, reload_time=2.0, max_ammo=3, fight_duration=9.0,
    )
    assert first_bullets == {1.0, 6.0}


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
    # interval is 0.05s (5 rounds: 0..0.2), empties at 0.25, reload 1.0 -> next
    # magazine at 1.25 fires at the base 0.1s interval.
    def attack_speed(t):
        return 1.0 if t < 1.0 else 0.0
    shots = generate_magazine_shot_times(
        rate_of_fire=10.0, max_ammo=5, reload_time=1.0, fight_duration=1.6,
        attack_speed_percent_at=attack_speed,
    )
    assert [round(t, 4) for t in shots] == [0.0, 0.05, 0.1, 0.15, 0.2, 1.25, 1.35, 1.45, 1.55]


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


def test_charge_speed_at_full_shortening_lands_on_the_measured_floor():
    # +100% drives the charge to zero, so the game's minimum gap between
    # charged shots is what remains - anchored to Cinderella's 29 shots/10s.
    shots = generate_charge_shot_times(
        charge_time=1.0, reload_time=1.0, max_ammo=3, fight_duration=1.2,
        charge_speed_percent_at=lambda t: 1.0,
    )
    assert [round(t, 4) for t in shots] == [
        round(CHARGE_INTERVAL_FLOOR_SECONDS * k, 4) for k in (1, 2, 3)]


def test_charge_speed_floor_never_slows_a_weapon_below_its_own_base():
    # Scarlet: Black Shadow's base charge (0.3s) is already quicker than the
    # floor measured on an RL; a blanket minimum would have slowed her down.
    assert charge_time_with_speed(0.3, 0.0) == pytest.approx(0.3)
    assert charge_time_with_speed(0.3, 1.0) == pytest.approx(0.3)


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
    assert cannon.time == pytest.approx(10.0 + CHARGE_INTERVAL_FLOOR_SECONDS)


def test_fight_duration_clips_segment_shots():
    seg = {"start": 178.0, "until_shots": 33,
           "profile": {"weapon": "SR", "damage_percent": 51.46,
                       "charge_damage_percent": 343.36, "rate_of_fire": 3.3}}
    records = generate_segmented_shots(SR_BASE, [seg], 180.0)
    seg_shots = [r for r in records if r.damage_percent == 51.46]
    assert all(r.time < 180.0 for r in seg_shots)
    assert len(seg_shots) < 33


def test_overlapping_segments_rejected():
    segs = [{"start": 10.0, "end": 20.0, "profile": TICKER},
            {"start": 15.0, "end": 25.0, "profile": TICKER}]
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


def test_reload_speed_buff_shortens_the_reload_reciprocally():
    assert reload_time_with_speed(2.0, 0.5) == pytest.approx(2.0 / 1.5)
    assert reload_time_with_speed(2.0, 1.0) == pytest.approx(1.0)


def test_reload_speed_reduction_lengthens_the_reload_symmetrically():
    # Milk: Blooming Bunny's forced reload - "reload speed fixed at a 50%
    # reduction" measures 3s against her 2s base in game (Fienn, 2026-07-20),
    # i.e. 1.5x. Dividing by (1 + speed) would give 4s, doubling it instead.
    assert reload_time_with_speed(2.0, -0.5) == pytest.approx(3.0)


def test_reload_speed_directions_are_reciprocal_mirrors():
    # +p and -p scale the reload by 1/(1+p) and (1+p) - symmetric in log space,
    # which is what makes the two branches one formula rather than two rules.
    for p in (0.25, 0.5, 0.8):
        assert reload_time_with_speed(2.0, p) * reload_time_with_speed(2.0, -p) == pytest.approx(4.0)


def test_reload_speed_zero_is_the_identity_on_both_branches():
    assert reload_time_with_speed(2.0, 0.0) == pytest.approx(2.0)


# --- charge speed: frame quantisation + caster-based flat reductions ---

def test_charge_speed_reduction_is_quantised_to_whole_frames():
    # The game reduces charge time by whole frames: community testing describes
    # "180 frames x 10.28% = 18.5 frames". Neon: Vision Eye's 9.47% overload on
    # a 1.0s charge measured 0.9178s, which the floored 5-frame step reproduces
    # to 0.07 frames where the continuous value is 0.75 frames off.
    assert charge_time_with_speed(1.0, 0.0947) == pytest.approx(1.0 - 5 / 60)
    # 10% of 60 frames is exactly 6, so no rounding happens there.
    assert charge_time_with_speed(1.0, 0.10) == pytest.approx(1.0 - 6 / 60)


def test_charge_speed_percent_applies_to_the_units_own_charge_time():
    # The percent scales the charge time it applies to, so the same buff buys
    # less absolute time on a shorter charge.
    assert charge_time_with_speed(1.5, 0.10) == pytest.approx(1.5 - 9 / 60)
    assert charge_time_with_speed(0.5, 0.10) == pytest.approx(0.5 - 3 / 60)


def test_flat_reduction_subtracts_absolute_seconds_on_top():
    # "Caster-based" buffs (Liberalio, Mana) hand over SECONDS, computed from
    # the caster's charge time, so they do not scale with the recipient's.
    assert charge_time_with_speed(1.0, 0.0, flat_reduction_sec=0.1911) == pytest.approx(1.0 - 0.1911)
    assert charge_time_with_speed(1.5, 0.0, flat_reduction_sec=0.1911) == pytest.approx(1.5 - 0.1911)


def test_liberalio_buff_reproduces_scarlets_measured_interval():
    # Fienn measured Scarlet at 0.7323s alone and 0.5424s with Liberalio.
    # Liberalio is an SR with a 1.5s charge, so her "12.74% caster-based"
    # hands over 0.1274 * 1.5 = 0.1911s.
    got = charge_time_with_speed(0.7323, 0.0, flat_reduction_sec=0.1274 * 1.5)
    assert got == pytest.approx(0.5424, abs=1 / 60)


def test_flat_reduction_and_percent_compose():
    # Percent first (on the unit's own charge), then the absolute seconds.
    assert charge_time_with_speed(1.0, 0.10, flat_reduction_sec=0.2) == pytest.approx(
        1.0 - 6 / 60 - 0.2)


def test_charge_floor_still_bounds_the_combination():
    # A huge flat reduction cannot drive the interval below the unit's floor.
    assert charge_time_with_speed(1.0, 0.0, flat_reduction_sec=5.0) == pytest.approx(
        CHARGE_INTERVAL_FLOOR_SECONDS)
