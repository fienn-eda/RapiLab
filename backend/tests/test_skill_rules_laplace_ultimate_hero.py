from app.effects import EffectRegistry
from app.skill_rules.laplace_ultimate_hero import (
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
