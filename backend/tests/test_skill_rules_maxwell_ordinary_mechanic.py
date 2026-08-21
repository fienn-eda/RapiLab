import pytest

from app.effects import EffectRegistry
from app.skill_rules.maxwell_ordinary_mechanic import (
    build_maxwell_ordinary_mechanic_rules,
    build_output_switching_gauge_fills,
)
from app.skill_rules.registry import get_gauge_fills
from app.squad_engine import SquadContext, SquadMember, fire_trigger

# Real skill level 10 values from ShiftyPad (data/shiftypad/maxwell-ordinary-mechanic.json).
SEQUENTIAL_LIMIT_RELEASE = {
    "description_value_01": "1",    # Max HP % per stack (deferred: Max HP, full-charge trigger)
    "description_value_02": "30",   # stacks (deferred)
    "description_value_03": "3",    # Burst Stage literal
    "description_value_04": "10",   # Full Burst Attack Damage %
    "description_value_05": "5",    # duration
}
OUTPUT_SWITCHING_SEQUENCE = {
    "description_value_01": "1",     # squad ATK % of caster Max HP
    "description_value_02": "15",    # duration
    # 템플릿이 이름을 대지 않는 슬롯. 전 레벨에서 07과 값이 같아 값으로는 못
    # 가르므로, 게이지 충전으로 읽으면 오늘은 맞고 근거는 틀린다.
    "description_value_03": "7.15",
    "description_value_04": "0",
    "description_value_05": "30",    # Overcurrent self ATK % per stage
    "description_value_06": "5",     # Overcurrent stages
    # 원문 "Fills Burst Gauge by {description_value_07}%" - 이 슬롯이 게이지다.
    "description_value_07": "7.15",  # full-charge squad Burst Gauge fill %
}
MATIS_UBERBUSTER = {
    "description_value_01": "2.5",   # deferred: transform charge time (stage 2)
    "description_value_02": "2",     # stage 3
    "description_value_03": "1.5",   # stage 4
    "description_value_04": "0.4",   # stage 5+
    "description_value_05": "350",   # deferred: transform self damage %
    "description_value_06": "1",     # transform max ammo
    "description_value_07": "25",    # squad Attack Damage %
    "description_value_08": "10",    # duration
    "description_value_09": "3",     # base charge time
}

CASTER_MAX_HP = 500_000.0


def values():
    return {
        "sequential_limit_release": SEQUENTIAL_LIMIT_RELEASE,
        "output_switching_sequence": OUTPUT_SWITCHING_SEQUENCE,
        "matis_uberbuster": MATIS_UBERBUSTER,
    }


def make_context():
    return SquadContext([
        SquadMember("maxwell-ordinary-mechanic", burst_tier=2, element="Wind", weapon="SR"),
        SquadMember("ally", burst_tier=3, element="Fire", weapon="AR"),
    ])


MAXWELL = {"slug": "maxwell-ordinary-mechanic", "element": "Wind"}
ALLY = {"slug": "ally", "element": "Fire"}


def rules():
    return build_maxwell_ordinary_mechanic_rules(values(), CASTER_MAX_HP)


def test_matis_uberbuster_charge_time_follows_the_overcurrent_stage():
    """"Charge Time is fixed. Effect varies according to the stage of
    Overcurrent" - 3 sec at stage 1 or below, then 2.5 / 2 / 1.5, and 0.4 from
    stage 5. Overcurrent gains one stage per own burst and caps at 5, so the
    k-th burst transforms at stage min(k, 5) and every burst from the 5th on
    fires the 0.4-sec version."""
    from app.skill_rules.maxwell_ordinary_mechanic import (
        build_matis_uberbuster_weapon_mode_schedule)

    schedule = build_matis_uberbuster_weapon_mode_schedule(values())
    ctx = make_context()
    ctx.burst_times = {"maxwell-ordinary-mechanic": [10.0, 30.0, 50.0, 70.0, 90.0, 110.0, 130.0]}
    segments = schedule(ctx, 180.0)

    assert [s["start"] for s in segments] == [10.0, 30.0, 50.0, 70.0, 90.0, 110.0, 130.0]
    assert [s["profile"]["charge_time"] for s in segments] == [3.0, 2.5, 2.0, 1.5, 0.4, 0.4, 0.4]
    # One round, so one shot, and the transform's own damage terms.
    assert all(s["until_shots"] == 1 for s in segments)
    assert {s["profile"]["damage_percent"] for s in segments} == {350.0}
    assert {s["profile"]["charge_damage_percent"] for s in segments} == {300.0}
    assert {s["profile"]["weapon"] for s in segments} == {"SR"}


def test_matis_uberbuster_charge_damage_takes_the_collectible_multiplier():
    """No term in this profile comes from weapon_stats, which is where a
    collectible's charge-damage 배율 is normally applied - so it has to be
    applied here to reach the transform at all (base Maxwell's precedent,
    measured 2026-08-03)."""
    from app.skill_rules.maxwell_ordinary_mechanic import (
        build_matis_uberbuster_weapon_mode_schedule)

    schedule = build_matis_uberbuster_weapon_mode_schedule(
        {**values(), "caster_charge_damage_multiplier": 1.0631})
    ctx = make_context()
    ctx.burst_times = {"maxwell-ordinary-mechanic": [10.0]}
    assert schedule(ctx, 180.0)[0]["profile"]["charge_damage_percent"] == pytest.approx(
        300.0 * 1.0631)


def test_matis_uberbuster_grants_pierce_for_its_one_round():
    """"Additional Effect: Gains Pierce." The transform is a single charged
    shot, so the property covers exactly that round - base Maxwell's shape."""
    grants = [r for r in rules() if getattr(r, "trigger", None) == "own_burst_activate"]
    reg = EffectRegistry()
    ctx = make_context()
    for rule in grants:
        rule.action(ctx, "maxwell-ordinary-mechanic", 10.0, reg)
    pierce = [g for g in reg.round_grants() if g.stat == "has_pierce"]
    assert len(pierce) == 1
    assert pierce[0].shots == 1
    assert pierce[0].scope == "self"


def test_burst_stage_three_entry_grants_squad_attack_damage():
    """"Activates when entering Burst Stage 3" describes the STAGE, so it rides
    ally_burst_activate + burst_stage_entered(3) - which fires BEFORE the Burst
    3's own nuke is recorded, unlike full_burst_enter."""
    ctx = make_context()
    registry = EffectRegistry()
    rs = {"maxwell-ordinary-mechanic": rules()}
    ctx.last_burst_slug = "ally"          # the deck's Burst 3 takes the stage
    fire_trigger("ally_burst_activate", rs, ctx, registry, time=5.0)
    assert round(registry.total_for("attack_damage_up", ALLY, now=5.0), 4) == 0.10
    assert registry.total_for("attack_damage_up", ALLY, now=10.1) == 0.0  # 5 sec window


def test_stage_three_buff_does_not_fire_on_a_lower_tier_ally_bursting():
    ctx = make_context()
    registry = EffectRegistry()
    rs = {"maxwell-ordinary-mechanic": rules()}
    ctx.last_burst_slug = "maxwell-ordinary-mechanic"   # her own tier-2 cast
    fire_trigger("ally_burst_activate", rs, ctx, registry, time=5.0)
    assert registry.total_for("attack_damage_up", ALLY, now=5.0) == 0.0


def test_stage_three_buff_is_not_on_full_burst_enter():
    """full_burst_enter lands AFTER the Burst 3 cast, so wiring it there would
    silently drop the +10% from that unit's own burst damage."""
    ctx = make_context()
    registry = EffectRegistry()
    fire_trigger("full_burst_enter", {"maxwell-ordinary-mechanic": rules()}, ctx, registry, time=5.0)
    assert registry.total_for("attack_damage_up", ALLY, now=5.0) == 0.0


def test_burst_grants_squad_atk_from_max_hp_and_attack_damage():
    ctx = make_context()
    registry = EffectRegistry()
    fire_trigger("own_burst_activate", {"maxwell-ordinary-mechanic": rules()}, ctx, registry, time=5.0)
    # squad flat_atk = 1% of 500000 = 5000, reaches allies
    assert round(registry.total_for("flat_atk", ALLY, now=5.0), 2) == 5000.0
    assert registry.total_for("flat_atk", ALLY, now=20.1) == 0.0  # 15 sec window
    # squad Attack Damage 25% for 10 sec
    assert round(registry.total_for("attack_damage_up", ALLY, now=5.0), 4) == 0.25
    assert registry.total_for("attack_damage_up", ALLY, now=15.1) == 0.0


def test_overcurrent_self_atk_ramps_per_burst_and_caps_at_five_stages():
    ctx = make_context()
    registry = EffectRegistry()
    rs = {"maxwell-ordinary-mechanic": rules()}
    times = [5.0, 25.0, 45.0, 65.0, 85.0, 105.0]
    ramp = []
    for t in times:
        fire_trigger("own_burst_activate", rs, ctx, registry, time=t)
        ramp.append(round(registry.total_for("atk_percent", MAXWELL, now=t), 4))
    # +30% per burst, cumulative, capped at 5 stages (+150%); self-only
    assert ramp == [0.30, 0.60, 0.90, 1.20, 1.50, 1.50]
    assert registry.total_for("atk_percent", ALLY, now=105.0) == 0.0  # self-only


def test_sequential_limit_release_grants_settled_max_hp_at_battle_start():
    ctx = make_context()
    registry = EffectRegistry()
    fire_trigger("battle_start", {"maxwell-ordinary-mechanic": rules()}, ctx, registry, time=0.0)
    # 그녀 Max HP의 1% x 30스택 = 30%, squad 스코프
    expected = CASTER_MAX_HP * 0.30
    assert round(registry.total_for("flat_max_hp", MAXWELL, now=0.0), 2) == round(expected, 2)
    assert round(registry.total_for("flat_max_hp", ALLY, now=0.0), 2) == round(expected, 2)


def test_squad_atk_uses_her_live_max_hp_including_her_own_max_hp_stacks():
    ctx = make_context()
    registry = EffectRegistry()
    fire_trigger("battle_start", {"maxwell-ordinary-mechanic": rules()}, ctx, registry, time=0.0)
    fire_trigger("own_burst_activate", {"maxwell-ordinary-mechanic": rules()}, ctx, registry, time=5.0)
    # squad ATK = 라이브 Max HP(=1.30 x base)의 1% = 6500 (정적이면 5000)
    expected = CASTER_MAX_HP * 1.30 * 0.01
    assert round(registry.total_for("flat_atk", ALLY, now=5.0), 2) == round(expected, 2)


def test_output_switching_fills_the_gauge_on_her_own_full_charge():
    """원문: "Activates when performing a Full Charge attack. Affects all
    allies. Fills Burst Gauge by {description_value_07}%".

    슬롯 03이 전 레벨에서 07과 값이 같아 어느 쪽을 읽어도 오늘은 통과한다 -
    원문이 이름을 대는 슬롯이 07이므로 07을 읽는다.
    """
    expected = [{"every_own_full_charge": "maxwell-ordinary-mechanic",
                 "fraction": pytest.approx(0.0715)}]
    assert build_output_switching_gauge_fills(values()) == expected
    assert get_gauge_fills("maxwell-ordinary-mechanic", values()) == expected
