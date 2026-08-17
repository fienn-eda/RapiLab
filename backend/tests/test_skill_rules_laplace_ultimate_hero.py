import pytest

from app.attack_rate import reload_time_with_speed
from app.effects import EffectRegistry
from app.skill_rules.laplace_ultimate_hero import (
    build_laplace_transform_schedule,
    build_laplace_ultimate_hero_rules,
    laplace_ultimate_hero_burst_percent,
)
from app.squad_engine import SquadContext, SquadMember, fire_trigger

# Real skill level 10 values from ShiftyPad (data/shiftypad/laplace-ultimate-hero.json).
ELECTRIC_POWER_FULL_FULL_CHARGE = {
    "description_value_01": "4.05",  # self ATK % of caster Max HP (battle start)
    "description_value_02": "10",    # deferred: Warm Up charge speed % per stack
    "description_value_03": "5",     # deferred: Warm Up stacks
    "description_value_04": "0",
    "description_value_05": "9.45",  # deferred: transform weapon damage %
    "description_value_06": "120",   # deferred: transform max ammo
    "description_value_07": "100",   # deferred: ammo removal %
}
OVER_ENERGY = {
    "description_value_01": "100",   # Over Energy cap % (deferred)
    "description_value_02": "2",     # deferred: stage 1 Max HP %
    "description_value_03": "3",     # deferred: stage 2 Max HP %
    "description_value_04": "7",     # deferred: stage 3 Max HP %
    "description_value_05": "10.5",  # deferred: stage 4 Max HP %
    "description_value_06": "52.14",  # Full Burst self Attack Damage %
    "description_value_07": "10",    # duration
    "description_value_08": "12",    # deferred: normal-attack count
    "description_value_09": "5",     # deferred: Over Energy per trigger %
}
REGENERATIVE_ENERGY_ARMAMENT_MJOLNIR = {
    "description_value_01": "63.36",    # self ATK %
    "description_value_02": "10",       # duration
    "description_value_03": "2953.84",  # burst nuke % of final ATK
    "description_value_04": "934.76",   # deferred: additional damage per Over Energy stage
}

CASTER_MAX_HP = 800_000.0

# Her real base weapon (ShiftyPad), injected by the roster as caster_weapon_stats.
# Fienn confirmed the 2.5% shot coefficient is correct - her DPS lives in the
# transformed state, not the base RL.
CASTER_WEAPON_STATS = {
    "weapon": "RL", "damage_percent": 2.5, "charge_damage_percent": 250.0,
    "charge_time": 1.0, "max_ammo": 120, "reload_time": 2.5,
}


def values():
    return {
        "electric_power_full_full_charge": ELECTRIC_POWER_FULL_FULL_CHARGE,
        "over_energy": OVER_ENERGY,
        "regenerative_energy_armament_mjolnir": REGENERATIVE_ENERGY_ARMAMENT_MJOLNIR,
        "caster_weapon_stats": dict(CASTER_WEAPON_STATS),
    }


def make_context():
    return SquadContext([
        SquadMember("laplace-ultimate-hero", burst_tier=3, element="Wind", weapon="RL"),
        SquadMember("ally", burst_tier=1, element="Fire", weapon="AR"),
    ])


def _schedule_context():
    """make_context()'s bare SquadContext has no max_ammo_percent_at -
    raid_simulator injects that live; build_laplace_transform_schedule's
    schedule() needs it, so the stub reads it as flat (no overload)."""
    ctx = make_context()
    ctx.max_ammo_percent_at = lambda _t: 0.0
    return ctx


LAPLACE = {"slug": "laplace-ultimate-hero", "element": "Wind"}
ALLY = {"slug": "ally", "element": "Fire"}


def rules():
    return build_laplace_ultimate_hero_rules(values(), CASTER_MAX_HP)


def test_burst_percent():
    assert laplace_ultimate_hero_burst_percent(values()) == 2953.84


def test_battle_start_self_atk_from_max_hp_is_permanent():
    ctx = make_context()
    registry = EffectRegistry()
    fire_trigger("battle_start", {"laplace-ultimate-hero": rules()}, ctx, registry, time=0.0)
    # self flat_atk = 4.05% of 800000 = 32400, permanent, self-only
    assert round(registry.total_for("flat_atk", LAPLACE, now=0.0), 2) == 32400.0
    assert round(registry.total_for("flat_atk", LAPLACE, now=170.0), 2) == 32400.0
    assert registry.total_for("flat_atk", ALLY, now=0.0) == 0.0


def test_burst_stage3_entry_self_attack_damage_fires_on_her_own_burst():
    ctx = make_context()
    registry = EffectRegistry()
    ctx.last_burst_slug = "laplace-ultimate-hero"
    fire_trigger("ally_burst_activate", {"laplace-ultimate-hero": rules()}, ctx, registry, time=5.0)
    assert round(registry.total_for("attack_damage_up", LAPLACE, now=5.0), 4) == 0.5214
    assert registry.total_for("attack_damage_up", LAPLACE, now=15.1) == 0.0  # 10 sec window
    assert registry.total_for("attack_damage_up", ALLY, now=5.0) == 0.0  # self-only


def test_burst_stage3_entry_also_fires_when_another_burst3_takes_the_slot():
    """[버스트 3단계 진입 시]는 단계에 대한 서술이지 시전자에 대한 서술이 아니다.
    두 번째 B3를 앉히면 둘이 슬롯을 나눠 갖고, 상대가 쏜 사이클도 3단계 진입이다."""
    ctx = SquadContext([
        SquadMember("laplace-ultimate-hero", burst_tier=3, element="Wind", weapon="RL"),
        SquadMember("other-burst-three", burst_tier=3, element="Fire", weapon="AR"),
    ])
    registry = EffectRegistry()
    ctx.last_burst_slug = "other-burst-three"
    fire_trigger("ally_burst_activate", {"laplace-ultimate-hero": rules()}, ctx, registry, time=5.0)
    assert round(registry.total_for("attack_damage_up", LAPLACE, now=5.0), 4) == 0.5214


def test_burst_stage3_entry_does_not_fire_when_a_lower_tier_bursts():
    ctx = make_context()
    registry = EffectRegistry()
    ctx.last_burst_slug = "ally"  # Burst 1
    fire_trigger("ally_burst_activate", {"laplace-ultimate-hero": rules()}, ctx, registry, time=5.0)
    assert registry.total_for("attack_damage_up", LAPLACE, now=5.0) == 0.0


def test_full_burst_enter_alone_does_not_grant_attack_damage():
    """그녀가 버스트하지 않은 사이클엔 지급되지 않아야 한다."""
    ctx = make_context()
    registry = EffectRegistry()
    fire_trigger("full_burst_enter", {"laplace-ultimate-hero": rules()}, ctx, registry, time=5.0)
    assert registry.total_for("attack_damage_up", LAPLACE, now=5.0) == 0.0


def test_pierce_rides_the_transform_window_not_her_burst():
    """"Additional Effect: Gains Pierce" is on skills[0]'s transformed weapon
    (Electric Power, Fully Full Charge). Mjolnir's text names no Pierce at all,
    so hanging it off her burst was both the wrong source and the wrong window.

    At the baseline the transform runs 4.617-9.617, 16.881-21.881, ... (a 5.0
    sec magazine at 24 shots/sec, on a 12.265 sec period - the first shot comes
    after the Warm Up build AND the weapon-change motion)."""
    ctx = make_context()
    registry = EffectRegistry()
    rs = {"laplace-ultimate-hero": rules()}
    fire_trigger("own_burst_activate", rs, ctx, registry, time=5.0)
    assert registry.total_for("has_pierce", LAPLACE, now=5.0) == 0.0

    fire_trigger("full_burst_enter", rs, ctx, registry, time=5.0)
    for inside in (4.7, 9.5, 17.0, 21.8):
        assert registry.total_for("has_pierce", LAPLACE, now=inside) == 1.0, inside
    for outside in (0.0, 4.5, 9.8, 16.8, 22.0):
        assert registry.total_for("has_pierce", LAPLACE, now=outside) == 0.0, outside
    assert registry.total_for("has_pierce", ALLY, now=4.7) == 0.0  # self-only


def test_pierce_windows_stretch_with_max_ammo_like_the_transform_does():
    """The window is the magazine at the transformed cadence, so [Max Ammo
    Increase] makes it longer - the same derivation the schedule itself uses."""
    from app.effects import Effect

    ctx = make_context()
    registry = EffectRegistry()
    registry.add(Effect("max_ammo_percent", 0.5, "self", None, "laplace-ultimate-hero"),
                 applied_at=0.0)
    fire_trigger("full_burst_enter", {"laplace-ultimate-hero": rules()}, ctx, registry, time=5.0)
    # 120 -> 180 rounds = a 7.5 sec window, so 4.617-12.117 instead of -9.617.
    assert registry.total_for("has_pierce", LAPLACE, now=12.0) == 1.0
    assert registry.total_for("has_pierce", LAPLACE, now=12.2) == 0.0


def test_over_energy_stages_are_counted_in_shots_not_in_whole_transforms():
    """"+5% per 12 normal attacks in the transformed state, up to 100%" = 240
    transformed normals per stage. At the baseline 120-round magazine that is
    exactly two windows, which is what the old constant said; with more max ammo
    a stage arrives sooner and lands MID-window, which the constant could not."""
    from app.skill_rules.laplace_ultimate_hero import (
        _plan_from_percent, _stage_times, over_energy_normals_per_stage)

    values = {"over_energy": OVER_ENERGY}
    assert over_energy_normals_per_stage(values) == 240

    weapon = dict(CASTER_WEAPON_STATS)
    shots, window, period = _plan_from_percent(weapon, 0.0)
    assert (shots, window) == (120, 5.0)
    assert period == pytest.approx(12.2647, abs=1e-4)
    baseline = _stage_times(period, window, shots, 240, 200.0)
    # Stage 1 at the end of the 2nd window (4.617 + 12.265 + 5.0), stage 2 two more.
    assert [t for _, t in baseline][:2] == pytest.approx([21.8813, 46.4107], abs=1e-4)

    # +50% max ammo: 180 shots a window, so stage 1 needs 1 window + 60 shots
    # and lands 2.5 sec INTO the second one rather than at its end. The clock
    # does not move (4.617 + 14.765 + 2.5 = 21.881): 240 shots take 10 sec of
    # firing either way and both layouts cross exactly one reload gap.
    shots, window, period = _plan_from_percent(weapon, 0.5)
    assert (shots, window) == (180, 7.5)
    assert period == pytest.approx(14.7647, abs=1e-4)
    mid = _stage_times(period, window, shots, 240, 200.0)
    assert mid[0][1] == pytest.approx(4.6167 + period + 60 / 24.0, abs=1e-4)
    assert mid[0][1] == pytest.approx(21.8813, abs=1e-4)

    # +100%: 240 shots fit in ONE window, so the stage skips a reload gap
    # entirely and arrives 7.3 sec sooner. That is the case the old "2
    # transforms per stage" constant could never express.
    shots, window, period = _plan_from_percent(weapon, 1.0)
    assert (shots, window) == (240, 10.0)
    fast = _stage_times(period, window, shots, 240, 200.0)
    assert fast[0][1] == pytest.approx(14.6167, abs=1e-4)
    assert fast[0][1] < baseline[0][1]


def test_burst_self_atk():
    ctx = make_context()
    registry = EffectRegistry()
    fire_trigger("own_burst_activate", {"laplace-ultimate-hero": rules()}, ctx, registry, time=5.0)
    assert round(registry.total_for("atk_percent", LAPLACE, now=5.0), 4) == 0.6336
    assert registry.total_for("atk_percent", LAPLACE, now=15.1) == 0.0  # 10 sec window
    assert registry.total_for("atk_percent", ALLY, now=5.0) == 0.0  # self-only


def test_battle_start_atk_uses_live_max_hp_when_a_max_hp_buff_is_active():
    from app.effects import Effect

    ctx = make_context()
    registry = EffectRegistry()
    registry.add(Effect("flat_max_hp", 200_000.0, "self", None, "laplace-ultimate-hero"), applied_at=0.0)
    fire_trigger("battle_start", {"laplace-ultimate-hero": rules()}, ctx, registry, time=0.0)
    # (800000 + 200000) * 4.05% = 40500 (정적이면 32400에 머문다)
    assert round(registry.total_for("flat_atk", LAPLACE, now=0.0), 2) == 40500.0


def test_every_transform_is_followed_by_a_silent_reload_segment():
    """"Removes 100% of ammo" when Electric Power, Fully Full Charge ends: the
    base weapon does not resume with a fresh magazine for free - it owes one
    reload, silent like the transform windows around it.

    At the baseline (period 12.5) the 180s fight cuts the 15th transform's own
    window short (it would run 179.0-185.0), so it earns no reload of its own
    - same as any segment truncated by fight_duration. Every transform whose
    window actually finishes inside the fight gets exactly one."""
    schedule = build_laplace_transform_schedule(values())
    fight_duration = 180.0
    segments = schedule(_schedule_context(), fight_duration)

    transforms = [s for s in segments if s["profile"]["damage_percent"] > 0]
    reloads = [s for s in segments if s["profile"]["damage_percent"] == 0.0]
    completed = [
        t for t in transforms
        if t["start"] + t["until_shots"] / t["profile"]["rate_of_fire"] < fight_duration
    ]
    assert len(reloads) == len(completed)
    assert len(reloads) == len(transforms) - 1  # the trailing window is the one exception


def test_the_reload_segment_starts_where_the_transform_ends():
    schedule = build_laplace_transform_schedule(values())
    segments = schedule(_schedule_context(), 180.0)

    transform, reload_segment = segments[0], segments[1]
    # An `until_shots` window ends AT its last shot's time, not one interval later.
    interval = 1.0 / transform["profile"]["rate_of_fire"]
    transform_end = transform["start"] + transform["until_shots"] * interval
    assert reload_segment["start"] == pytest.approx(transform_end)
    # The window's LENGTH is her own weapon's affine reload
    # (reload_time_with_speed), not the raw file value the cycle period
    # uses - 2.648 sec against CASTER_WEAPON_STATS' 2.5, from the fixed
    # 0.148 sec segment every reload carries on top of the scaled part.
    expected_reload_seconds = reload_time_with_speed(CASTER_WEAPON_STATS["reload_time"], 0.0)
    assert (reload_segment["end"] - reload_segment["start"]
            == pytest.approx(expected_reload_seconds))


def test_the_two_segments_do_not_overlap():
    schedule = build_laplace_transform_schedule(values())
    segments = sorted(schedule(_schedule_context(), 180.0), key=lambda s: s["start"])

    for earlier, later in zip(segments, segments[1:]):
        end = earlier.get("end")
        if end is None:
            interval = 1.0 / earlier["profile"]["rate_of_fire"]
            end = earlier["start"] + earlier["until_shots"] * interval
        assert end <= later["start"] + 1e-9
