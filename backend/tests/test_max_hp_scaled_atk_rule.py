from app.effects import Effect, EffectRegistry
from app.skill_rules._helpers import max_hp_scaled_atk_rule
from app.squad_engine import SquadContext, SquadMember, fire_trigger

CASTER = {"slug": "caster", "element": "Wind"}
ALLY = {"slug": "ally", "element": "Fire"}


def make_context():
    return SquadContext([
        SquadMember("caster", burst_tier=3, element="Wind", weapon="RL"),
        SquadMember("ally", burst_tier=1, element="Fire", weapon="AR"),
    ])


def test_uses_base_max_hp_when_no_max_hp_buffs_are_active():
    ctx = make_context()
    registry = EffectRegistry()
    rule = max_hp_scaled_atk_rule("battle_start", 0.0405, "self", None, base_max_hp=800_000.0)
    fire_trigger("battle_start", {"caster": [rule]}, ctx, registry, time=0.0)
    # 800000 * 4.05% = 32400
    assert round(registry.total_for("flat_atk", CASTER, now=0.0), 2) == 32400.0


def test_live_max_hp_buffs_raise_the_converted_atk():
    ctx = make_context()
    registry = EffectRegistry()
    # 먼저 캐스터에게 Max HP +200000을 건다.
    registry.add(Effect("flat_max_hp", 200_000.0, "self", None, "caster"), applied_at=0.0)
    rule = max_hp_scaled_atk_rule("battle_start", 0.0405, "self", None, base_max_hp=800_000.0)
    fire_trigger("battle_start", {"caster": [rule]}, ctx, registry, time=0.0)
    # (800000 + 200000) * 4.05% = 40500
    assert round(registry.total_for("flat_atk", CASTER, now=0.0), 2) == 40500.0


def test_squad_scope_pays_allies_using_the_casters_max_hp():
    ctx = make_context()
    registry = EffectRegistry()
    registry.add(Effect("flat_max_hp", 200_000.0, "self", None, "caster"), applied_at=0.0)
    rule = max_hp_scaled_atk_rule("own_burst_activate", 0.01, "squad", 15.0, base_max_hp=800_000.0)
    fire_trigger("own_burst_activate", {"caster": [rule]}, ctx, registry, time=5.0)
    # 아군도 캐스터의 라이브 Max HP 기준 1% = 10000을 받는다
    assert round(registry.total_for("flat_atk", ALLY, now=5.0), 2) == 10000.0
    assert registry.total_for("flat_atk", ALLY, now=20.1) == 0.0  # 15초 창


def test_a_max_hp_buff_landing_after_application_does_not_retroactively_grow_it():
    """알려진 한계를 명시적으로 고정한다 - 스냅샷 의미론."""
    ctx = make_context()
    registry = EffectRegistry()
    rule = max_hp_scaled_atk_rule("battle_start", 0.0405, "self", None, base_max_hp=800_000.0)
    fire_trigger("battle_start", {"caster": [rule]}, ctx, registry, time=0.0)
    registry.add(Effect("flat_max_hp", 200_000.0, "self", None, "caster"), applied_at=1.0)
    assert round(registry.total_for("flat_atk", CASTER, now=5.0), 2) == 32400.0


def test_an_allys_squad_max_hp_buff_raises_a_consumers_converted_atk():
    """Rouge가 오래 심어두기만 했던 squad flat_max_hp가 드디어 딜을 움직인다."""
    ctx = make_context()
    registry = EffectRegistry()
    registry.add(Effect("flat_max_hp", 100_000.0, "squad", None, "ally"), applied_at=0.0)
    rule = max_hp_scaled_atk_rule("battle_start", 0.01, "self", None, base_max_hp=800_000.0)
    fire_trigger("battle_start", {"caster": [rule]}, ctx, registry, time=0.0)
    # (800000 + 100000) * 1% = 9000
    assert round(registry.total_for("flat_atk", CASTER, now=0.0), 2) == 9000.0
