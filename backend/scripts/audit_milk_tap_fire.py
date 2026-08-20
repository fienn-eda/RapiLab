"""밀크의 톡톡이 케이던스를 엔진에게 직접 물어 찍는다.

손계산으로 발수를 재유도하면 버프를 하나씩 조용히 빠뜨린다(앨리스에서 세 번
당했다). 그래서 이 스크립트는 산술을 다시 하지 않고 `generate_segmented_shots`가
실제로 만든 ShotRecord를 세어 보여준다.

쓸 때: 밀크의 장탄/재장전/차속이 바뀌는 변경 뒤, 또는 `optimal_full_charges`를
손댄 뒤. 출력의 「풀차지 간 최대 간격」이 6초를 넘으면 Pierce 근사가 깨진 것이다.

    cd backend && python scripts/audit_milk_tap_fire.py
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.attack_rate import FRAME_SECONDS, generate_segmented_shots

WINDOW = 6.0
FIGHT = 30.0


def milk_weapon(max_ammo=6, reload_time=2.0):
    return {
        "weapon": "SR", "charge_time": 1.0, "charge_damage_percent": 250.0,
        "damage_percent": 100.0, "max_ammo": max_ammo, "reload_time": reload_time,
        "charge_motion_delay": 22 * FRAME_SECONDS, "tap_fire": True,
        "tap_fire_interval": 15 * FRAME_SECONDS, "full_charge_window": WINDOW,
    }


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
    damage = sum(s.damage_percent * (1 + s.extra_charge_bonus) for s in shots)
    print(f"{label:28s} 발수 {len(shots):3d}  풀차지 {len(fulls):3d}  "
          f"최대간격 {worst:5.2f}s  누적배율 {damage:8.1f}  톡톡이배율 {tap_mult:.3f}"
          f"{'  ** 창 초과 **' if worst > WINDOW + 1e-9 else ''}")


if __name__ == "__main__":
    print(f"전투 {FIGHT}초 · Pierce 창 {WINDOW}초\n")
    for ammo in (6, 10, 14):
        for reload_time in (2.0, 1.0, 0.5):
            report(f"장탄 {ammo:2d} · 재장전 {reload_time}s",
                   milk_weapon(max_ammo=ammo, reload_time=reload_time))
    print("\n대조 - 톡톡이 없이 전부 풀차지:")
    weapon = milk_weapon()
    weapon["tap_fire"] = False
    report("장탄  6 · 재장전 2.0s", weapon)
