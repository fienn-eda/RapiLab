"""Laplace: Ultimate Hero의 변신 루프 - 세그먼트 창, Over Energy 단계, Mjolnir 추가딜.

앵커는 전부 Fienn 인게임 실측(2026-07-24). 기본 무기는 ShiftyPad 원본
(RL, 120발, 2.5%, charge 1.0s, reload 2.5s) - 주기 4.0 + 6.0 + 2.5 = 12.5초가
실측 "약 12.5초마다 변신"과 일치한다.
"""
from app.effects import Effect, EffectRegistry
from app.skill_rules.laplace_ultimate_hero import (
    SMG_RATE_OF_FIRE,
    build_laplace_stage_nukes,
    build_laplace_transform_schedule,
    build_laplace_ultimate_hero_rules,
)
from app.squad_engine import SquadContext, SquadMember, fire_trigger
from tests.test_skill_rules_laplace_ultimate_hero import CASTER_MAX_HP, values as base_values

WEAPON = {
    "weapon": "RL", "damage_percent": 2.5, "charge_damage_percent": 250.0,
    "charge_time": 1.0, "max_ammo": 120, "reload_time": 2.5,
}

LAPLACE = {"slug": "laplace-ultimate-hero", "element": "Wind"}


def values(max_ammo=120):
    v = base_values()
    v["caster_weapon_stats"] = {**WEAPON, "max_ammo": max_ammo}
    return v


def make_context(max_ammo_percent=0.0):
    ctx = SquadContext([
        SquadMember("laplace-ultimate-hero", burst_tier=3, element="Wind", weapon="RL"),
        SquadMember("ally", burst_tier=1, element="Fire", weapon="AR"),
    ])
    ctx.max_ammo_percent_at = lambda t, pct=max_ammo_percent: pct
    return ctx


def test_transform_window_is_one_magazine_at_smg_cadence():
    schedule = build_laplace_transform_schedule(values())
    segs = schedule(make_context(), fight_duration=180.0)

    first = segs[0]
    assert first["start"] == 4.0                       # Warm Up 5 full charges
    assert first["until_shots"] == 120                 # empties the magazine
    assert first["profile"]["rate_of_fire"] == SMG_RATE_OF_FIRE
    assert first["profile"]["damage_percent"] == 9.45
    # Fienn: SMG 대미지에 차지대미지 미적용
    assert "charge_damage_percent" not in first["profile"]


def test_transform_period_is_build_plus_window_plus_reload():
    schedule = build_laplace_transform_schedule(values())
    segs = schedule(make_context(), fight_duration=180.0)
    starts = [s["start"] for s in segs]
    # 4.0 + (120/20) + 2.5 = 12.5
    assert starts[1] - starts[0] == 12.5
    assert starts[:3] == [4.0, 16.5, 29.0]


def test_window_and_period_scale_with_max_ammo_overload():
    """[최대 장탄 수 증가]가 창을 늘리므로 주기를 상수로 박으면 안 된다."""
    schedule = build_laplace_transform_schedule(values())
    segs = schedule(make_context(max_ammo_percent=0.5), fight_duration=180.0)
    assert segs[0]["until_shots"] == 180          # round(120 * 1.5)
    # 4.0 + (180/20) + 2.5 = 15.5
    assert segs[1]["start"] - segs[0]["start"] == 15.5


def test_segments_never_overlap():
    schedule = build_laplace_transform_schedule(values())
    segs = schedule(make_context(), fight_duration=180.0)
    for earlier, later in zip(segs, segs[1:]):
        window_end = earlier["start"] + earlier["until_shots"] / SMG_RATE_OF_FIRE
        assert later["start"] > window_end


def _fire_stage_rule(ctx, registry, at=5.0):
    rules = build_laplace_ultimate_hero_rules(values(), CASTER_MAX_HP)
    fire_trigger("battle_start", {"laplace-ultimate-hero": rules}, ctx, registry, time=0.0)
    fire_trigger("full_burst_enter", {"laplace-ultimate-hero": rules}, ctx, registry, time=at)


def test_over_energy_stage_grants_max_hp_every_two_transforms():
    ctx = make_context()
    registry = EffectRegistry()
    _fire_stage_rule(ctx, registry)

    # stage 1 = 2번째 변신 창이 끝나는 순간 = 16.5 + 6.0 = 22.5
    assert registry.total_for("flat_max_hp", LAPLACE, now=22.4) == 0.0
    assert round(registry.total_for("flat_max_hp", LAPLACE, now=22.5), 2) == round(CASTER_MAX_HP * 0.02, 2)
    # stage 2 = 4번째 창 끝 = 41.5 + 6.0 = 47.5, 값이 교체된다(누적 아님)
    assert round(registry.total_for("flat_max_hp", LAPLACE, now=47.5), 2) == round(CASTER_MAX_HP * 0.03, 2)
    # stage 4 = 8번째 창 끝 = 91.5 + 6.0 = 97.5
    assert round(registry.total_for("flat_max_hp", LAPLACE, now=97.5), 2) == round(CASTER_MAX_HP * 0.105, 2)


def test_electric_power_atk_is_reapplied_with_the_bigger_max_hp():
    ctx = make_context()
    registry = EffectRegistry()
    _fire_stage_rule(ctx, registry)

    # 초기: 4.05% of 800000 = 32400
    assert round(registry.total_for("flat_atk", LAPLACE, now=0.0), 2) == 32400.0
    # stage 1부터: (800000 * 1.02) * 4.05% = 33048 - 합산이 아니라 교체
    assert round(registry.total_for("flat_atk", LAPLACE, now=22.5), 2) == 33048.0
    # stage 4: (800000 * 1.105) * 4.05% = 35802
    assert round(registry.total_for("flat_atk", LAPLACE, now=97.5), 2) == 35802.0


def test_mjolnir_stage_nukes_use_the_stage_at_each_burst():
    ctx = make_context()
    ctx.record_burst_time("laplace-ultimate-hero", 10.0)   # stage 0
    ctx.record_burst_time("laplace-ultimate-hero", 30.0)   # stage 1 (>= 22.5)
    ctx.record_burst_time("laplace-ultimate-hero", 50.0)   # stage 2 (>= 47.5)
    # 세그먼트 패스가 남긴 plan을 흉내낸다
    build_laplace_transform_schedule(values())(ctx, 180.0)

    specs = build_laplace_stage_nukes(values())
    by_stage = {round(s["percent"] / 934.76): s for s in specs}

    assert by_stage[1]["schedule"](ctx, 180.0) == [30.0]
    assert by_stage[2]["schedule"](ctx, 180.0) == [50.0]
    # stage 0 버스트는 어떤 스펙에도 안 잡힌다 (추가딜 0)
    assert all(10.0 not in s["schedule"](ctx, 180.0) for s in specs)
    assert all(s["full_burst_bonus_eligible"] for s in specs)
