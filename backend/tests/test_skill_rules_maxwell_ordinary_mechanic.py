from app.effects import EffectRegistry
from app.skill_rules.maxwell_ordinary_mechanic import build_maxwell_ordinary_mechanic_rules
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
    "description_value_03": "7.15",  # deferred: burst gauge fill %
    "description_value_04": "0",
    "description_value_05": "30",    # Overcurrent self ATK % per stage
    "description_value_06": "5",     # Overcurrent stages
    "description_value_07": "7.15",  # deferred: burst gauge fill %
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


def test_full_burst_grants_squad_attack_damage():
    ctx = make_context()
    registry = EffectRegistry()
    fire_trigger("full_burst_enter", {"maxwell-ordinary-mechanic": rules()}, ctx, registry, time=5.0)
    assert round(registry.total_for("attack_damage_up", ALLY, now=5.0), 4) == 0.10
    assert registry.total_for("attack_damage_up", ALLY, now=10.1) == 0.0  # 5 sec window


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
