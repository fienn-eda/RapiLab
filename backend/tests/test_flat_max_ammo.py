"""[최대 장탄 수 ▲ N발] - 퍼센트가 아니라 라운드 수로 오는 장탄 버프.

오버로드와 대부분의 스킬은 장탄을 퍼센트로 주지만, 토브의 임시개조(+2발,
3중첩)·그레이브(+3발)·느와르(+5발)는 무기와 무관한 고정 발수를 준다. 같은
+6발이 SG 9발에게는 +67%이고 MG 300발에게는 +2%라, 스쿼드 스코프 퍼센트
하나로는 근사조차 되지 않는다 - 그래서 별도 스탯이다.
"""
from app.effects import Effect, EffectRegistry, max_ammo_percent_total
from app.raid_simulator import simulate_raid
from app.skill_rules._helpers import buff_rule

SG_INTERVAL = 1 / 1.5  # attack_rate.RATE_OF_FIRE_60FPS["SG"]
SG_ALLY = {"slug": "sg-ally", "element": "Fire"}


def _run(buffs, fight_duration=60.0):
    return simulate_raid(
        deck=[
            {"slug": "buffer", "burst_tier": 1, "element": "Water", "cooldown": 20.0, "weapon": "AR"},
            {"slug": "sg-ally", "burst_tier": 3, "element": "Fire", "cooldown": 40.0, "weapon": "SG"},
        ],
        rules_by_slug={
            "buffer": [buff_rule("battle_start", buffs)] if buffs else [],
            "sg-ally": [],
        },
        burst_damage_percents={},
        base_stats={"buffer": {"atk": 300000}, "sg-ally": {"atk": 200000}},
        enemy_def=0,
        gauge_charge_time=5.0,
        fight_duration=fight_duration,
        base_crit_rate=0.0,
        weapon_stats={"sg-ally": {"weapon": "SG", "damage_percent": 200.0, "max_ammo": 9,
                                  "reload_time": 1.5, "charge_time": 0.0,
                                  "charge_damage_percent": 100.0}},
    )


def _shot_times(result):
    return [e["time"] for e in result["damage_log"] if e["source"] == "normal_attack"]


def _first_magazine_size(times):
    """재장전이 끊기 전까지 등간격으로 이어진 발수 = 그 탄창의 크기."""
    size = 1
    while size < len(times) and abs(times[size] - times[size - 1] - SG_INTERVAL) < 1e-6:
        size += 1
    return size


def test_without_the_buff_the_magazine_is_the_weapon_s_own():
    assert _first_magazine_size(_shot_times(_run([]))) == 9


def test_flat_rounds_enlarge_the_magazine():
    # 토브의 임시개조 3중첩 = +6발. SG 9발 -> 15발.
    times = _shot_times(_run([("max_ammo_rounds", 6.0, "squad", None)]))
    assert _first_magazine_size(times) == 15


def test_flat_rounds_land_on_top_of_the_percent():
    # 오버로드 +30%와 겹칠 때: round(9 x 1.30) + 6 = 12 + 6 = 18발. 퍼센트는
    # 기본 장탄에만 걸리고 플랫 발수는 그 위에 얹힌다 (Fienn, 2026-08-02).
    times = _shot_times(_run([
        ("max_ammo_percent", 0.30, "squad", None),
        ("max_ammo_rounds", 6.0, "squad", None),
    ]))
    assert _first_magazine_size(times) == 18


def test_flat_rounds_raise_the_shot_count():
    # 탄창이 커지면 같은 시간에 재장전을 덜 하므로 실제로 더 쏜다.
    without = len(_shot_times(_run([])))
    with_buff = len(_shot_times(_run([("max_ammo_rounds", 6.0, "squad", None)])))
    assert without and with_buff > without


def test_flat_rounds_fold_into_the_percent_the_magazine_reads():
    # 탄창 크기를 계산하는 쪽은 지금까지처럼 배율 하나만 알면 되도록,
    # 플랫 발수는 받는 유닛의 기본 장탄에 대한 비율로 환산되어 합류한다.
    reg = EffectRegistry()
    reg.add(Effect("max_ammo_percent", 0.30, "squad", None, "buffer"), applied_at=0.0)
    reg.add(Effect("max_ammo_rounds", 6.0, "squad", None, "buffer"), applied_at=0.0)
    assert max_ammo_percent_total(reg, SG_ALLY, 0.0, 9) == 0.30 + 6 / 9


def test_a_unit_with_no_ammo_buff_reads_its_plain_percent():
    reg = EffectRegistry()
    reg.add(Effect("max_ammo_percent", 0.30, "squad", None, "buffer"), applied_at=0.0)
    assert max_ammo_percent_total(reg, SG_ALLY, 0.0, 9) == 0.30
