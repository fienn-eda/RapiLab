"""톡톡이 — 차지를 채우지 않고 바로 놓아 배율을 버리고 발수를 버는 조작.

Fienn 사격장 실측(2026-08-19, 앨리스 1인 편성, docs/measurements/alice-tap-fire.md)이
두 가지를 확정했다:

1. **부분 차지 대미지는 HUD가 표시하는 게이지 퍼센트 그 자체다.** 게이지는 차지 전에
   이미 100%로 시작해 풀차지에서 383%까지 오르고, 대미지는 그 값에 정확히 비례한다
   (8개 판독, 편차 −0.40%~+0.15%, 표시값 정수 반올림으로 전부 설명됨).
2. **톡톡이는 게이지를 전혀 안 채운다** — 게이지가 오르는 첫 프레임과 발사 프레임이
   같다. 그래서 톡톡이 샷은 정확히 **100%**, 즉 차지 보너스가 0이다.

그래서 이건 「바닥값」이 아니라 **한 샷을 어디서 놓느냐**의 문제이고, 중간 지점은 볼
필요가 없다(`tap_fire_wins`의 독스트링 참고). 남는 것은 매거진마다 두 끝 중 어느
쪽이 나은지 고르는 일뿐이다.
"""
import pytest

from app.attack_rate import (FRAME_SECONDS, full_charge_positions,
                             generate_segmented_shots, optimal_full_charges,
                             shot_interval_with_speed, tap_fire_wins)
from app.skill_rules.registry import (TAP_FIRE_CANDIDATES,
                                      get_charge_motion_delay,
                                      get_full_charge_window,
                                      get_tap_fire_interval,
                                      is_tap_fire_candidate)

# 앨리스의 무기 (data/shiftypad/alice.json) + Fienn 계정의 소장품 차지대미지
ALICE_CHARGE_TIME = 1.5
ALICE_MAX_AMMO = 6
ALICE_RELOAD_TIME = 2.0
ALICE_FULL_CHARGE_PERCENT = 383.0      # 실측(소장품 포함). 데이터 기본값은 350.
ALICE_MOTION_DELAY = 15 * FRAME_SECONDS
# 버스트 Wonderland 차속 80.15% + 그날 판독이 시사하는 오버로드 약 7.5~9%
ALICE_BURST_CHARGE_SPEED = 0.8015 + 0.0896
ALICE_RESTING_CHARGE_SPEED = 0.0896
# 크라운 44.35 + 프리바티 51.16 + 회복력 큐브 29.69 = 125.20%, 재장전이 사라지는 지점
NO_RELOAD_SPEED = 1.2520


def test_alices_motion_delay_is_the_measured_fifteen_frames():
    """실측 14.75프레임(n=12, sd 0.62, 범위 13~15)이 프레임 격자에서 15에 앉는다.

    같은 영상의 톡톡이 발사 간격 15.38프레임과 같은 값인 것이 교차검증이다 —
    톡톡이는 차지가 0이므로 그 간격이 곧 딜레이다.
    """
    assert get_charge_motion_delay("alice") == pytest.approx(15 * FRAME_SECONDS)


def test_every_tap_fire_candidate_has_a_motion_delay():
    """톡톡이 간격은 그 유닛의 멈춤 그 자체다. 멈춤이 0이면 톡톡이가 무한 연사가
    되므로, 딜레이가 없는 유닛은 후보가 될 수 없다."""
    for slug in TAP_FIRE_CANDIDATES:
        assert get_charge_motion_delay(slug) > 0.0, slug
        assert is_tap_fire_candidate(slug)


def _wins(charge_speed, reload_speed):
    # 딜레이를 실어 재야 `차지 + 딜레이` 분기를 타고, 거기서 딜레이를 빼면 그 시점의
    # 유효 차지시간이 나온다 - 엔진이 매거진 시작에 하는 계산과 같다.
    interval = shot_interval_with_speed(
        ALICE_CHARGE_TIME, charge_speed, motion_delay=ALICE_MOTION_DELAY)
    charge = interval - ALICE_MOTION_DELAY
    reload_seconds = max(0.0, ALICE_RELOAD_TIME * (1 - reload_speed)) + 0.148
    return tap_fire_wins(charge, ALICE_MOTION_DELAY, ALICE_FULL_CHARGE_PERCENT,
                         ALICE_MAX_AMMO, reload_seconds)


def test_tap_fire_wins_outside_her_burst_when_the_reload_is_gone():
    """Fienn 사격장 확인(크라운+프리바티+재장전 큐브 15렙): 자기 버스트가 아닐 때
    톡톡이가 자동사격보다 딜이 높다. 재장전이 톡톡이의 유일한 비용인데 그 조합이
    재장전을 아예 없애기 때문이다."""
    assert _wins(ALICE_RESTING_CHARGE_SPEED, NO_RELOAD_SPEED)


def test_full_charge_wins_outside_her_burst_when_the_reload_is_normal():
    """같은 구간이라도 재장전 버프가 없으면 부호가 뒤집힌다 - 탄창 6발을 4.8배 빨리
    비우는 값을 못 낸다."""
    assert not _wins(ALICE_RESTING_CHARGE_SPEED, 0.0)


def test_full_charge_wins_inside_her_burst_window():
    """창 안에서는 차속이 차지를 10프레임까지 밀어 풀차지가 거의 공짜다. 그걸 버리고
    100%로 쏘는 것은 어느 재장전에서도 손해다."""
    assert not _wins(ALICE_BURST_CHARGE_SPEED, 0.0)
    assert not _wins(ALICE_BURST_CHARGE_SPEED, NO_RELOAD_SPEED)


def test_the_full_charge_interval_reproduces_the_measured_reading():
    """차속 없이 수동 풀차지를 이어 쏜 실측 발간격은 101.73프레임(n=11)이었다.

    모델은 `차지 + 딜레이` = 90 + 15 = 105프레임을 준다. 차이 3.2%는 차지 시작
    프레임 판독이 늦게 잡히는 쪽으로 치우친 것과 같은 방향이다(같은 영상의 차지
    실측이 87.92프레임으로 파일값 90보다 작다).
    """
    interval = shot_interval_with_speed(
        ALICE_CHARGE_TIME, 0.0, motion_delay=ALICE_MOTION_DELAY)
    assert interval / FRAME_SECONDS == pytest.approx(105.0)
    assert abs(interval / FRAME_SECONDS / 101.73 - 1) < 0.035


def test_the_two_modes_are_close_enough_that_the_collectible_flips_the_verdict():
    """엔진 기본값(회복력 큐브 15렙 = 재장전속도 +29.69%)에서 두 모드가 5% 안에 있고,
    소장품 차지대미지가 그 안에서 부호를 뒤집는다.

    **그래도 점수는 안 흔들린다** - 엔진이 큰 쪽을 고르므로 출력은 두 값의 max이고,
    뒤집히는 것은 화면에 표시되는 모드뿐이다. 이 테스트는 그 민감도가 실재한다는
    사실을 못박아, 나중에 「앨리스가 왜 덱마다 다르게 나오냐」가 버그로 오해되지
    않게 한다.
    """
    cube_reload = max(0.0, ALICE_RELOAD_TIME * (1 - 0.2969)) + 0.148
    charge = shot_interval_with_speed(
        ALICE_CHARGE_TIME, ALICE_RESTING_CHARGE_SPEED,
        motion_delay=ALICE_MOTION_DELAY) - ALICE_MOTION_DELAY
    # 데이터 파일 그대로(소장품 없음)
    assert tap_fire_wins(charge, ALICE_MOTION_DELAY, 350.0, ALICE_MAX_AMMO, cube_reload)
    # Fienn 계정처럼 소장품이 붙으면 풀차지가 이긴다
    assert not tap_fire_wins(charge, ALICE_MOTION_DELAY, ALICE_FULL_CHARGE_PERCENT,
                             ALICE_MAX_AMMO, cube_reload)


def _alice_base(**over):
    base = {
        "weapon": "SR",
        "damage_percent": 69.04,
        "charge_damage_percent": ALICE_FULL_CHARGE_PERCENT,
        "charge_time": ALICE_CHARGE_TIME,
        "max_ammo": ALICE_MAX_AMMO,
        "reload_time": ALICE_RELOAD_TIME,
        "charge_motion_delay": ALICE_MOTION_DELAY,
        "tap_fire": True,
    }
    base.update(over)
    return base


def test_the_timeline_switches_modes_at_her_burst_window():
    """엔진이 매거진마다 고른다 - 창 밖은 톡톡이(배율 0 보너스), 창 안은 풀차지.

    재장전이 사라진 덱이라 창 밖에서 톡톡이가 이긴다. 이 전환이 런의 선택 하나로는
    표현되지 않는 부분이고(단일 모드 최선 대비 +27.6%), 판정이 닫힌 형태라 탐색은
    필요 없다.
    """
    def charge_speed_at(time):
        return ALICE_BURST_CHARGE_SPEED if time < 10.0 else ALICE_RESTING_CHARGE_SPEED

    records = generate_segmented_shots(
        _alice_base(), [], 40.0,
        reload_speed_percent_at=lambda _t: NO_RELOAD_SPEED,
        charge_speed_percent_at=charge_speed_at)
    inside = [r for r in records if r.time < 10.0]
    outside = [r for r in records if r.time >= 12.0]
    assert inside and outside
    # 창 안: 풀차지 배율이 실려 있다
    assert all(r.extra_charge_bonus == pytest.approx(ALICE_FULL_CHARGE_PERCENT / 100 - 1)
               for r in inside)
    # 창 밖: 톡톡이라 차지 보너스가 없다
    assert all(r.extra_charge_bonus == 0.0 for r in outside)


def test_a_unit_that_is_not_a_candidate_never_taps():
    """옵트인이 아닌 차지 무기는 오늘 그대로 - 전부 풀차지다."""
    records = generate_segmented_shots(
        _alice_base(tap_fire=False), [], 40.0,
        reload_speed_percent_at=lambda _t: NO_RELOAD_SPEED,
        charge_speed_percent_at=lambda _t: ALICE_RESTING_CHARGE_SPEED)
    assert records
    assert all(r.extra_charge_bonus == pytest.approx(ALICE_FULL_CHARGE_PERCENT / 100 - 1)
               for r in records)


def test_milks_tap_interval_is_not_her_motion_delay():
    """밀크의 두 실측은 다른 값이다 — 톡톡이 14.810f(n=21) 대 멈춤 21.889f(n=9),
    약 16시그마. 앨리스에서 둘이 같게 나온 것은 우연이었고, 그녀에게 멈춤을
    톡톡이 간격으로 주면 발수를 47% 과소평가한다.
    docs/measurements/milk-blooming-bunny-tap-fire.md
    """
    assert get_tap_fire_interval("milk-blooming-bunny") == pytest.approx(15 * FRAME_SECONDS)
    assert get_charge_motion_delay("milk-blooming-bunny") == pytest.approx(22 * FRAME_SECONDS)


def test_alices_two_values_agree_so_she_does_not_move():
    """앨리스는 멈춤 14.75f · 톡톡이 15.38f로 둘 다 15프레임에 앉는다. 값이 같으므로
    분리해도 그녀의 타임라인은 한 발도 안 움직인다 — 그것이 이 변경의 회귀 기준이다."""
    assert get_tap_fire_interval("alice") == get_charge_motion_delay("alice")


def test_milk_declares_the_window_that_forces_a_full_charge():
    """「Gain Pierce for 6 sec」 — 스킬 원문에서 읽은 값이지 조작에서 나온 값이 아니다."""
    assert get_full_charge_window("milk-blooming-bunny") == pytest.approx(6.0)


def test_alice_has_no_full_charge_window():
    """앨리스의 Pierce는 HP 조건이라 풀차지가 갱신하지 않는다. 창이 없으면 매거진을
    통째로 톡톡이로 쏘는 것이 허용된다."""
    assert get_full_charge_window("alice") is None


MILK_CAPACITY = 6
MILK_CHARGE_TIME = 1.0
MILK_FULL_CHARGE_PERCENT = 250.0
MILK_RELOAD_TIME = 2.0
MILK_MOTION_DELAY = 22 * FRAME_SECONDS
MILK_TAP_INTERVAL = 15 * FRAME_SECONDS
MILK_WINDOW = 6.0


def _milk_k(capacity=MILK_CAPACITY, reload_seconds=MILK_RELOAD_TIME):
    return optimal_full_charges(
        capacity, reload_seconds, MILK_CHARGE_TIME, MILK_MOTION_DELAY,
        MILK_TAP_INTERVAL, MILK_FULL_CHARGE_PERCENT, MILK_WINDOW)


def test_milk_at_stock_ammo_fires_one_full_charge_a_magazine():
    """Fienn 조작 그대로 — 매거진 첫 탄만 풀차지, 나머지 다섯 발은 톡톡이."""
    assert _milk_k() == 1


def test_a_bigger_magazine_forces_a_second_full_charge():
    """장탄이 커지면 한 매거진이 Pierce 6초를 넘기므로 풀차지가 하나 더 든다 —
    Fienn이 「풀차지 → 톡톡이 → 풀차지 → 톡톡이」라고 적은 그 패턴이고,
    하드코딩이 아니라 창 제약에서 떨어져 나온다."""
    assert _milk_k(capacity=14) == 2


def _milk_worst_gap(capacity, full_charges, reload_seconds):
    """풀차지 `full_charges`발을 균등 배치했을 때 연속한 두 풀차지 사이의 최악 간격.

    `optimal_full_charges`가 후보를 거르는 데 쓰는 식과 같은 것을, 테스트가
    독립적으로 다시 쓴 것이다 - 구현이 자기 식으로 자기를 검증하지 않게.
    """
    block = -(-capacity // full_charges)
    return (MILK_CHARGE_TIME + MILK_MOTION_DELAY
            + (block - 1) * MILK_TAP_INTERVAL + reload_seconds)


def test_the_chosen_cadence_keeps_the_window_whenever_any_cadence_can():
    """**불변식** - 창을 지킬 수 있는 k가 하나라도 있으면 고른 k가 그것을 지킨다.

    전부 풀차지(k=C)가 「언제나 안전」한 것은 **아니다**: 그때 최악 간격은
    `차지+멈춤+재장전`까지 줄지만, 재장전 하나가 창보다 길면 그 값도 창을 넘는다
    (예: 장탄 6 · 재장전 8초 -> 9.37초 > 6초). 그때는 모델이 아니라 게임이 창을
    잃는 것이므로, 주장은 「항상 지킨다」가 아니라 「지킬 수 있으면 지킨다」여야 한다.
    """
    for capacity in range(1, 21):
        for reload_seconds in (0.0, 0.5, 1.0, 2.0, 4.0, 8.0):
            k = _milk_k(capacity=capacity, reload_seconds=reload_seconds)
            assert 1 <= k <= capacity
            feasible = [j for j in range(1, capacity + 1)
                        if _milk_worst_gap(capacity, j, reload_seconds) <= MILK_WINDOW]
            if feasible:
                assert _milk_worst_gap(capacity, k, reload_seconds) <= MILK_WINDOW, (
                    capacity, reload_seconds, k)
            else:
                # 어떤 케이던스로도 못 지킨다 - 최악 간격이 가장 작은 k=C로 물러난다.
                assert k == capacity, (capacity, reload_seconds, k)


def test_milks_real_numbers_never_reach_the_window_she_cannot_keep():
    """밀크의 Pierce를 영구로 두는 근사가 **실제로** 기대는 사실.

    그녀의 차지+멈춤+재장전이 창보다 짧으므로, 창을 못 지키는 분기에 닿지 않는다.
    그녀의 강제 재장전(「50% 감소 고정」 = 2초 base에 대해 3초)까지 넣어도 그렇다.
    이 부등식이 깨지는 날 그녀의 영구 Pierce는 근사가 아니라 오류가 된다.
    """
    for reload_seconds in (2.0, 3.0):
        worst_gap_at_full_charge = (
            MILK_CHARGE_TIME + MILK_MOTION_DELAY + reload_seconds)
        assert worst_gap_at_full_charge < MILK_WINDOW, reload_seconds


def test_without_a_window_the_answer_matches_the_old_two_way_test():
    """앨리스에게는 창이 없으므로 답이 두 끝뿐이고, 그 판정은 기존 `tap_fire_wins`와
    **동치**여야 한다 — 효율이 k에 대해 단조라 f(0) > f(C) ⟺ 톡톡이 승."""
    for capacity in (1, 3, 6, 10):
        for reload_seconds in (0.0, 0.5, 1.0, 2.0, 5.0):
            for charge_seconds in (0.0, 0.25, 1.5, 3.0):
                k = optimal_full_charges(
                    capacity, reload_seconds, charge_seconds, ALICE_MOTION_DELAY,
                    ALICE_MOTION_DELAY, ALICE_FULL_CHARGE_PERCENT, None)
                taps_win = tap_fire_wins(
                    charge_seconds, ALICE_MOTION_DELAY, ALICE_FULL_CHARGE_PERCENT,
                    capacity, reload_seconds)
                assert k == (0 if taps_win else capacity), (
                    capacity, reload_seconds, charge_seconds, k, taps_win)


def test_a_unit_with_no_pause_cannot_tap():
    """톡톡이 간격이 0이면 무한 연사가 된다 — 전부 풀차지로 물러난다."""
    assert optimal_full_charges(6, 2.0, 1.0, 0.0, 0.0, 250.0, None) == 6


def test_full_charges_are_spread_evenly_and_the_first_round_is_one():
    """첫 탄은 항상 풀차지다 — 강제 재장전 직후의 거동이자 Fienn 조작 4번."""
    assert full_charge_positions(6, 1) == frozenset({0})
    assert full_charge_positions(6, 2) == frozenset({0, 3})
    assert full_charge_positions(14, 2) == frozenset({0, 7})
    assert full_charge_positions(6, 6) == frozenset(range(6))
    assert full_charge_positions(6, 0) == frozenset()


def test_the_widest_block_never_exceeds_the_ceiling():
    """제약식이 쓰는 `ceil(C/k)`가 실제 배치의 최대 블록과 맞는지 — 두 곳이
    어긋나면 창을 지킨다고 믿으면서 안 지키게 된다."""
    for capacity in range(1, 21):
        for k in range(1, capacity + 1):
            positions = sorted(full_charge_positions(capacity, k))
            blocks = [b - a for a, b in zip(positions, positions[1:])]
            blocks.append(capacity - positions[-1])
            assert max(blocks) <= -(-capacity // k), (capacity, k)


def _milk_weapon(**overrides):
    weapon = {
        "weapon": "SR",
        "charge_time": MILK_CHARGE_TIME,
        "charge_damage_percent": MILK_FULL_CHARGE_PERCENT,
        "damage_percent": 100.0,
        "max_ammo": MILK_CAPACITY,
        "reload_time": MILK_RELOAD_TIME,
        "charge_motion_delay": MILK_MOTION_DELAY,
        "tap_fire": True,
        "tap_fire_interval": MILK_TAP_INTERVAL,
        "full_charge_window": MILK_WINDOW,
    }
    weapon.update(overrides)
    return weapon


def test_milks_magazine_mixes_one_full_charge_with_five_taps():
    """매거진 여섯 발 가운데 첫 탄만 차지 보너스를 갖는다."""
    shots = generate_segmented_shots(_milk_weapon(), (), 6.0)
    magazine = shots[:MILK_CAPACITY]
    assert [s.extra_charge_bonus > 0 for s in magazine] == [True, False, False, False, False, False]


def test_the_taps_are_spaced_by_the_tap_interval_not_the_pause():
    """톡톡이끼리의 간격은 15프레임이지 그녀의 멈춤 22프레임이 아니다 — 이 구분이
    없으면 발수를 47% 과소평가한다."""
    shots = generate_segmented_shots(_milk_weapon(), (), 6.0)
    gaps = [b.time - a.time for a, b in zip(shots, shots[1:])][:4]
    for gap in gaps:
        assert gap == pytest.approx(MILK_TAP_INTERVAL)


def test_the_full_charge_shot_costs_charge_plus_pause():
    """첫 탄은 차지 1초와 멈춤 22프레임을 함께 치른다."""
    shots = generate_segmented_shots(_milk_weapon(), (), 6.0)
    assert shots[0].time == pytest.approx(MILK_CHARGE_TIME + MILK_MOTION_DELAY)


def test_a_unit_without_a_tap_interval_falls_back_to_its_pause():
    """실측이 없으면 지금까지의 동작 그대로 멈춤을 톡톡이 간격으로 쓴다.

    **재장전을 0으로 두어 톡톡이가 이기는 지점에서 재야** 폴백값이 간격에 드러난다.
    그녀의 기본 재장전 2초에서는 22프레임 톡톡이가 풀차지에 진다(매거진당 1.4286 대
    1.4706). 그러면 매거진이 통째로 풀차지가 되고 발 간격은 폴백값이 아니라
    차지+멈춤이 되어, 폴백이 통째로 깨져도 이 테스트가 초록일 수 있다.

    같은 계산이 이 인코딩의 근거이기도 하다 — 22프레임과 15프레임이 **부호를
    뒤집는다**. 그래서 밀크의 톡톡이 간격을 따로 잰 것이다.
    """
    weapon = _milk_weapon(full_charge_window=None, reload_time=0.0)
    weapon.pop("tap_fire_interval")
    shots = generate_segmented_shots(weapon, (), 6.0)
    gaps = [b.time - a.time for a, b in zip(shots, shots[1:])][:3]
    for gap in gaps:
        assert gap == pytest.approx(MILK_MOTION_DELAY)
