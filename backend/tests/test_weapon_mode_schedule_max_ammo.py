"""weapon-mode 스케줄 함수가 라이브 최대 장탄을 읽을 수 있어야 한다.

Laplace: Ultimate Hero의 변신 창 길이는 탄창을 다 비우는 데 걸리는 시간이라
[최대 장탄 수 증가] 오버로드에 비례한다 - 상수로 박으면 육성 상태가 다른
유저에게 틀린 주기를 준다(Fienn, 2026-07-24).
"""
from app.effects import Effect
from app.raid_simulator import simulate_raid
from app.squad_engine import SkillRule

WEAPON = {
    "weapon": "SMG", "damage_percent": 10.0, "charge_damage_percent": 100.0,
    "charge_time": 0.0, "max_ammo": 120, "reload_time": 1.0,
}


def make_deck():
    return [
        {"slug": "buffer", "burst_tier": 1, "element": "Iron", "cooldown": 20.0},
        {"slug": "midtier", "burst_tier": 2, "element": "Iron", "cooldown": 20.0},
        {"slug": "attacker", "burst_tier": 3, "element": "Iron", "cooldown": 40.0},
    ]


def run(schedule, rules_by_slug=None):
    deck = make_deck()
    base_stats = {m["slug"]: {"atk": 1000, "def": 0, "max_hp": 0} for m in deck}
    return simulate_raid(
        deck,
        rules_by_slug or {m["slug"]: [] for m in deck},
        burst_damage_percents={},
        base_stats=base_stats,
        enemy_def=0,
        gauge_charge_time=5.0,
        fight_duration=20.0,
        weapon_stats={"attacker": dict(WEAPON)},
        weapon_mode_schedules={"attacker": schedule},
        base_crit_rate=0.0,
    )


def test_schedule_fn_can_read_live_max_ammo_percent():
    seen = {}

    def schedule(context, fight_duration):
        seen["pct"] = context.max_ammo_percent_at(0.0)
        return []

    run(schedule)
    assert seen["pct"] == 0.0


def test_live_max_ammo_percent_reflects_a_max_ammo_buff():
    seen = {}

    def schedule(context, fight_duration):
        seen["pct"] = context.max_ammo_percent_at(0.0)
        return []

    def grant_max_ammo(context, caster_slug, time, registry):
        registry.add(Effect("max_ammo_percent", 0.5, "self", None, "attacker"), applied_at=time)

    rules = {m["slug"]: [] for m in make_deck()}
    rules["attacker"] = [SkillRule(trigger="battle_start", action=grant_max_ammo)]
    run(schedule, rules)
    assert seen["pct"] == 0.5
