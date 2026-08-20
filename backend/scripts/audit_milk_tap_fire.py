"""밀크의 톡톡이 케이던스를 엔진에게 직접 물어 찍는다.

손계산으로 발수를 재유도하면 버프를 하나씩 조용히 빠뜨린다(앨리스에서 세 번
당했다). 그래서 이 스크립트는 산술을 다시 하지 않고 `generate_segmented_shots`가
실제로 만든 ShotRecord를 세어 보여준다.

쓸 때: 밀크의 장탄/재장전/차속이 바뀌는 변경 뒤, 또는 `optimal_full_charges`를
손댄 뒤. 출력의 「풀차지 간 최대 간격」이 6초를 넘으면 Pierce 근사가 깨진 것이다.

    cd backend && python scripts/audit_milk_tap_fire.py

★★★ 이 스크립트가 「창 길이」에서 거짓을 찍은 적이 있다(2026-08-20). `FIGHT = 30.0`짜리
창으로 「누적배율」(이득 비율)까지 같이 재고 있었는데, 같은 창 길이 스윕을 옛 모델
(톡톡이 배율 0%)로 재면 30초에서 5.56%, 60초에서 8.33%, 180초에서 9.62%로 아직
수렴 전이다 - 정상상태가 아니다. 그래서 이득 비율은 **창을 아예 안 쓴다.** 이 무기는
버프가 전투 내내 상수라 케이던스가 첫 매거진부터 이미 완전히 주기적이고(2·3번째
매거진의 시각차가 100·101번째, 500·501번째와
부동소수점 오차 안에서 같다 - 9개 장탄/재장전 조합 전부 확인됨), 그래서 한 매거진
주기의 대미지 ÷ 그 주기의 길이가 **창을 얼마나 늘려도 다시 잴 필요 없는 정확한
정상상태 DPS**다. 창으로 근사하면 얼마나 위험한지: 600초 창은 10.79%를 주는데(300·600·
900·1200·2400초 여러 배수에서 우연히 같은 값이 나와 「수렴했다」는 착시를 준다), 그
사이 450초는 11.06%로 위쪽에 튀고 4800초는 10.7487%로 아래쪽에 튄다 - **단조로
미끄러지지 않고 극한값 주위에서 진동하며 수렴한다.** 120,000초에서 10.763%,
500,000초에서야 매거진-주기 방식과 소수점 4자리까지 맞아떨어진다(10.7627% 대
10.7628%). **600초도 정상상태가 아니었다** - 창을 어디서 끊든 마지막 미완성 매거진이
편향을 남기고, 두 케이던스의 주기가 서로 약분되지 않아 그 편향이 창 길이에 따라
들쭉날쭉 없어졌다 나타났다 한다.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.attack_rate import FRAME_SECONDS, generate_segmented_shots
from app.skill_rules.registry import (
    get_charge_motion_delay, get_full_charge_window, get_tap_fire_interval)

SLUG = "milk-blooming-bunny"
# 창·멈춤·톡톡이 간격은 **레지스트리에 묻는다.** 한동안 여기 상수로 박혀 있었고
# (`charge_motion_delay = 22 * FRAME_SECONDS`), 2026-08-20에 그녀의 멈춤이 자동값
# 22프레임에서 수동 stand-in 17.643프레임으로 바뀌었을 때 **이 스크립트만 옛 값으로
# 계속 초록을 찍었다.** 검산 도구가 엔진과 다른 숫자를 세면 검산이 아니다.
WINDOW = get_full_charge_window(SLUG)
# 창 위반(Pierce 창 초과) 스캔 전용 - 매거진 몇 개 안에서 이미 드러나는 질문이라
# 짧아도 안전하다. **이득 비율에는 안 쓴다** - 위 docstring 참고.
FIGHT = 30.0
# 정상상태 DPS를 뽑을 매거진 몇 개를 확보하기 위한 프로브 창. 「정상상태」 개념
# 자체가 창 길이가 아니라 매거진 주기이므로, 이 값을 늘려도 결과는 안 바뀐다
# (skip 뒤 첫 완결 주기 하나만 쓴다) - 늘리는 건 그냥 낭비다.
CYCLE_PROBE = 200.0


def milk_weapon(max_ammo=6, reload_time=2.0):
    return {
        "weapon": "SR", "charge_time": 1.0, "charge_damage_percent": 250.0,
        "damage_percent": 100.0, "max_ammo": max_ammo, "reload_time": reload_time,
        "charge_motion_delay": get_charge_motion_delay(SLUG), "tap_fire": True,
        "tap_fire_interval": get_tap_fire_interval(SLUG), "full_charge_window": WINDOW,
    }


def steady_state_dps(weapon, skip=2):
    """정상상태 DPS = 한 매거진 주기의 대미지 ÷ 그 주기의 길이.

    이 무기는 버프가 전투 내내 상수라 케이던스가 첫 매거진부터 이미 주기적이다 -
    `optimal_full_charges`가 매 매거진 같은 `k`를 고르고 그 배치가 그대로 반복된다.
    그래서 창을 늘려 평균을 근사할 필요가 없다: 한 주기의 대미지/시간이 그 자체로
    정확한 정상상태 값이다(부동소수점 오차 말고는 근사가 없다). `skip`은 그냥
    여유 - 0번째 매거진부터 써도 이 무기에서는 같은 값이 나온다(직접 확인함).
    """
    shots = generate_segmented_shots(weapon, (), CYCLE_PROBE)
    starts = [s.time for s in shots if s.is_first_bullet]
    a, b = starts[skip], starts[skip + 1]
    damage = sum(s.damage_percent * (1 + s.extra_charge_bonus)
                 for s in shots if a <= s.time < b)
    return damage / (b - a)


def report(label, weapon):
    shots = generate_segmented_shots(weapon, (), FIGHT)
    # 풀차지는 `is_tap_fire` 플래그로 가른다 - 값(`extra_charge_bonus > 0`)으로
    # 가르면 톡톡이 배율이 0보다 큰 지금(0.03) 모든 톡톡이 샷이 풀차지로
    # 오분류된다.
    fulls = [s.time for s in shots if not s.is_tap_fire]
    taps = [s for s in shots if s.is_tap_fire]
    tap_mult = (1 + taps[0].extra_charge_bonus) if taps else float("nan")
    gaps = [b - a for a, b in zip(fulls, fulls[1:])]
    worst = max(gaps) if gaps else 0.0
    dps = steady_state_dps(weapon)
    print(f"{label:28s} [{FIGHT:.0f}s 창위반검사] 발수 {len(shots):3d}  풀차지 {len(fulls):3d}  "
          f"최대간격 {worst:5.2f}s  톡톡이배율 {tap_mult:.3f}"
          f"{'  ** 창 초과 **' if worst > WINDOW + 1e-9 else ''}"
          f"   [정상상태] DPS {dps:9.4f}")


if __name__ == "__main__":
    print(f"창위반검사 {FIGHT:.0f}초 · Pierce 창 {WINDOW}초 "
          f"· DPS는 매거진 주기로 계산(창 스윕 아님 - 위 docstring)\n")
    for ammo in (6, 10, 14):
        for reload_time in (2.0, 1.0, 0.5):
            report(f"장탄 {ammo:2d} · 재장전 {reload_time}s",
                   milk_weapon(max_ammo=ammo, reload_time=reload_time))
    print("\n대조 - 톡톡이 없이 전부 풀차지:")
    off_weapon = milk_weapon()
    off_weapon["tap_fire"] = False
    report("장탄  6 · 재장전 2.0s", off_weapon)

    on_dps = steady_state_dps(milk_weapon())
    off_dps = steady_state_dps(off_weapon)
    print(f"\n이득(장탄 6 · 재장전 2.0s, 정상상태 DPS 대조 - 매거진 주기, 창 길이 무관): "
          f"{(on_dps / off_dps - 1) * 100:.2f}%")
