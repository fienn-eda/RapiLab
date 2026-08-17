"""Laplace: Ultimate Hero의 변신 루프 - 세그먼트 창, Over Energy 단계, Mjolnir 추가딜.

앵커는 Fienn 인게임 실측(2026-07-24 · 케이던스와 모션은 2026-08-17 재측정).
기본 무기는 ShiftyPad 원본(RL, 120발, 2.5%, charge 1.0s, reload 2.5s) - 주기는
빌드 4.0 + 무기변경 모션 0.617 + 창 5.0(120발 ÷ 24발/초) + 재장전 2.648 =
12.265초다. `docs/measurements/laplace-uh-transform-loop.md`.
"""
from app.effects import Effect, EffectRegistry
from app.skill_rules.laplace_ultimate_hero import (
    TRANSFORM_MOTION_SECONDS,
    TRANSFORM_RATE_OF_FIRE,
    WARM_UP_BUILD_SECONDS,
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


def test_transform_window_is_one_magazine_at_the_measured_cadence():
    schedule = build_laplace_transform_schedule(values())
    segs = schedule(make_context(), fight_duration=180.0)

    first = segs[0]
    # 빌드(풀차지 5발) 다음에 무기변경 모션이 있고, 그제서야 첫 발이 나간다.
    assert first["start"] == WARM_UP_BUILD_SECONDS + TRANSFORM_MOTION_SECONDS
    assert first["until_shots"] == 120                 # empties the magazine
    # 24발/초는 실측이다. 무기군 SMG 상수(20.0)로 되돌리지 말 것 - 그 값은
    # 공칭 1440rpm을 3프레임 격자로 올림한 것이고 이 무기는 그 격자에 없다.
    assert first["profile"]["rate_of_fire"] == TRANSFORM_RATE_OF_FIRE == 24.0
    assert first["profile"]["damage_percent"] == 9.45
    # Fienn: SMG 대미지에 차지대미지 미적용
    assert "charge_damage_percent" not in first["profile"]


def test_transform_period_is_build_plus_window_plus_reload():
    schedule = build_laplace_transform_schedule(values())
    segs = schedule(make_context(), fight_duration=180.0)
    # Segments now alternate transform/reload (see the reload segment tests in
    # test_skill_rules_laplace_ultimate_hero.py), so the transform TIMES have
    # to be picked out by until_shots rather than read straight off segs.
    starts = [s["start"] for s in segs if "until_shots" in s]
    # 4.0 + 0.6167 + (120/24) + 2.648 = 12.2647
    assert round(starts[1] - starts[0], 4) == 12.2647
    assert [round(s, 4) for s in starts[:3]] == [4.6167, 16.8813, 29.146]


def test_window_and_period_scale_with_max_ammo_overload():
    """[최대 장탄 수 증가]가 창을 늘리므로 주기를 상수로 박으면 안 된다."""
    schedule = build_laplace_transform_schedule(values())
    segs = schedule(make_context(max_ammo_percent=0.5), fight_duration=180.0)
    transforms = [s for s in segs if "until_shots" in s]
    assert transforms[0]["until_shots"] == 180          # round(120 * 1.5)
    # 4.0 + 0.6167 + (180/24) + 2.648 = 14.7647
    assert round(transforms[1]["start"] - transforms[0]["start"], 4) == 14.7647


def test_segments_never_overlap():
    """Covers both segment shapes in the schedule: a transform window
    (until_shots) and the silent reload right after it (end). The boundary is
    `>=` because a reload segment opens exactly at its transform's end instant
    (an `until_shots` window ends AT its last shot) - back-to-back, not gapped."""
    schedule = build_laplace_transform_schedule(values())
    segs = schedule(make_context(), fight_duration=180.0)
    for earlier, later in zip(segs, segs[1:]):
        if "until_shots" in earlier:
            window_end = earlier["start"] + earlier["until_shots"] / TRANSFORM_RATE_OF_FIRE
        else:
            window_end = earlier["end"]
        assert later["start"] >= window_end


def _fire_stage_rule(ctx, registry, at=5.0):
    rules = build_laplace_ultimate_hero_rules(values(), CASTER_MAX_HP)
    fire_trigger("battle_start", {"laplace-ultimate-hero": rules}, ctx, registry, time=0.0)
    fire_trigger("full_burst_enter", {"laplace-ultimate-hero": rules}, ctx, registry, time=at)


def test_over_energy_stages_are_cumulative_every_two_transforms():
    """스킬 원문 "[Each subsequent effect triggers all effects before it:]" —
    stage 2는 1+2, stage 4는 1+2+3+4를 받는다(Fienn 2026-07-24)."""
    ctx = make_context()
    registry = EffectRegistry()
    _fire_stage_rule(ctx, registry)

    # stage 1 = 2번째 변신 창이 끝나는 순간 = 16.8813 + 5.0 = 21.8813
    assert registry.total_for("flat_max_hp", LAPLACE, now=21.8) == 0.0
    assert round(registry.total_for("flat_max_hp", LAPLACE, now=21.9), 2) == round(CASTER_MAX_HP * 0.02, 2)
    # stage 2 = 4번째 창 끝 = 46.41 → 2 + 3 = 5%
    assert round(registry.total_for("flat_max_hp", LAPLACE, now=46.5), 2) == round(CASTER_MAX_HP * 0.05, 2)
    # stage 3 = 6번째 창 끝 = 70.94 → 2 + 3 + 7 = 12%
    assert round(registry.total_for("flat_max_hp", LAPLACE, now=71.0), 2) == round(CASTER_MAX_HP * 0.12, 2)
    # stage 4 = 8번째 창 끝 = 95.47 → 2 + 3 + 7 + 10.5 = 22.5%
    assert round(registry.total_for("flat_max_hp", LAPLACE, now=95.5), 2) == round(CASTER_MAX_HP * 0.225, 2)


def test_electric_power_atk_is_reapplied_with_the_bigger_max_hp():
    ctx = make_context()
    registry = EffectRegistry()
    _fire_stage_rule(ctx, registry)

    # 초기: 4.05% of 800000 = 32400
    assert round(registry.total_for("flat_atk", LAPLACE, now=0.0), 2) == 32400.0
    # stage 1: (800000 * 1.02) * 4.05% = 33048 - 합산이 아니라 교체(값 자체가 누적합)
    assert round(registry.total_for("flat_atk", LAPLACE, now=22.5), 2) == 33048.0
    # stage 4: (800000 * 1.225) * 4.05% = 39690
    assert round(registry.total_for("flat_atk", LAPLACE, now=97.5), 2) == 39690.0


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
