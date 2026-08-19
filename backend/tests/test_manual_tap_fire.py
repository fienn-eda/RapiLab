"""수동 톡톡이(차지 시작 직후 발사)를 상시 유지한다고 가정하는 유닛의 발 간격.

오토 사격의 발사↔차지 멈춤과는 다른 값이다. 멈춤은 게임이 정하고 이건 플레이어의
손이 정하므로, 실측 표(`TIMED_CHARGE_MOTION_DELAY`)에도 무기 데이터에서 유도되는
표(`CHARGE_ROUNDS_PER_MINUTE`)에도 들어가지 않는다 - 후자에 넣으면
`scripts/audit_rate_of_fire.py`가 「`UP`인데 표에 올라 있다」로 실패한다.

이 값이 FLOOR로 실려 가는 것이 핵심이다. 차지가 이보다 길면 차지가 케이던스를
정하므로, 톡톡이는 그녀 차속이 살아 있는 구간에서만 저절로 성립한다.
"""
import pytest

from app.attack_rate import FRAME_SECONDS, shot_interval_with_speed
from app.charge_window import WindowInputs, shot_times
from app.skill_rules.registry import (MANUAL_TAP_FIRE_INTERVAL,
                                      get_charge_motion_delay,
                                      get_manual_tap_fire_interval)

# 앨리스의 무기 (data/shiftypad/alice.json)
ALICE_CHARGE_TIME = 1.5
ALICE_MAX_AMMO = 6
ALICE_RELOAD_TIME = 2.0
# 버스트 Wonderland 차속 80.15% + Fienn 계정 오버로드 8.96%
ALICE_BURST_CHARGE_SPEED = 0.8015 + 0.0896
# 버스트 밖에는 오버로드뿐이다
ALICE_RESTING_CHARGE_SPEED = 0.0896
# 크라운 44.35 + 프리바티 51.16 + 회복력 큐브 29.69 = 125.20%, 재장전이 사라지는 지점
NO_RELOAD_SPEED = 1.2520


def test_alice_taps_at_seventeen_frames():
    """17프레임 = 0.28333초 = 풀버스트 10초에 35발.

    Fienn 실측(2026-08-19): 인게임 오토가 FB 10초 구간에 23발, 수동 톡톡이가 40발
    이상. 그 사이에서 35발을 채택했다. 프레임 격자 위의 값이어야 하는 이유는
    `CHARGE_ROUNDS_PER_MINUTE`의 다섯 값이 전부 정수 프레임인 것과 같다 - 210발/분
    (0.28571초)로 적으면 35번째 샷이 정확히 t=10.0에 서서 창 밖으로 떨어진다.
    """
    assert get_manual_tap_fire_interval("alice") == pytest.approx(17 * FRAME_SECONDS)
    assert get_manual_tap_fire_interval("alice") == pytest.approx(0.283333, abs=1e-6)


def test_a_tap_fire_unit_carries_no_motion_delay():
    """멈춤과 톡톡이 간격은 `shot_interval_with_speed`에서 배타적인 두 분기다.

    멈춤이 실려 가면 floor 분기에 아예 도달하지 못하므로 톡톡이 간격이 조용히
    무시된다. 그래서 이건 취향이 아니라 불변식이다.
    """
    for slug in MANUAL_TAP_FIRE_INTERVAL:
        assert get_charge_motion_delay(slug) == 0.0, slug


def _alice_window(charge_speed, reload_speed=NO_RELOAD_SPEED):
    return WindowInputs(
        charge_time=ALICE_CHARGE_TIME,
        motion_delay=0.0,
        max_ammo=ALICE_MAX_AMMO,
        reload_time=ALICE_RELOAD_TIME,
        charge_speed_percent=charge_speed,
        charge_time_reduction_sec=0.0,
        reload_speed_percent=reload_speed,
        interval_floor=get_manual_tap_fire_interval("alice"),
    )


def test_her_burst_window_lands_the_measured_thirty_five_shots():
    """재장전이 사라진 조건에서 10초에 35발 - Fienn이 잰 그 조건이다."""
    shots = shot_times(_alice_window(ALICE_BURST_CHARGE_SPEED), start_charged=False)
    assert len(shots) == 35


def test_outside_her_burst_the_charge_sets_the_cadence():
    """창 밖에서는 차지 1.367초가 톡톡이 간격보다 길어 floor가 안 걸린다.

    그녀의 차속은 전부 버스트 창 10초 안에만 있다(버스트 Wonderland +80.15%,
    스킬1의 캐스터 기준 감소도 풀버스트 진입에 묶여 있다). 창 밖에는 오버로드뿐이라
    차지가 82프레임으로 돌아오고, 톡톡이로 벌 발수가 없다.
    """
    interval = shot_interval_with_speed(
        ALICE_CHARGE_TIME, ALICE_RESTING_CHARGE_SPEED,
        interval_floor=get_manual_tap_fire_interval("alice"))
    assert interval == pytest.approx(1.36667, abs=1e-5)
    shots = shot_times(_alice_window(ALICE_RESTING_CHARGE_SPEED), start_charged=False)
    assert len(shots) == 7


def test_the_deck_result_names_who_the_player_has_to_tap():
    """화면은 슬러그를 보고 판단하지 않는다 - 누가 톡톡이 전제인지는 엔진이 정해서
    실어 보낸다(`hold_burst_slugs`와 같은 계약). 그래서 표에 유닛이 추가되는 날
    화면에도 그날 나온다.
    """
    from types import SimpleNamespace

    from app.deck_search import tap_fire_slugs

    deck = [SimpleNamespace(slug=s) for s in ("alice", "ein", "crown")]
    assert tap_fire_slugs(deck) == ["alice"]
    assert tap_fire_slugs([SimpleNamespace(slug="crown")]) == []


def test_the_tap_interval_is_a_floor_not_a_cadence():
    """차속이 컷을 넘어 차지가 1프레임까지 떨어져도 발 간격은 17프레임에 선다.

    커뮤니티가 앨리스에게 권하는 「차속 98.889%」(풀차지 1.5초 = 90프레임에서
    89/90)가 그 지점이다. 손이 더 빨라지지는 않으므로 floor가 답이 된다.
    """
    interval = shot_interval_with_speed(
        ALICE_CHARGE_TIME, 0.98889,
        interval_floor=get_manual_tap_fire_interval("alice"))
    assert interval == pytest.approx(17 * FRAME_SECONDS)
