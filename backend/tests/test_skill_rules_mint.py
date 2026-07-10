from app.effects import EffectRegistry
from app.skill_rules.mint import build_here_i_go_rules, build_mint_rules
from app.squad_engine import SquadContext, SquadMember, fire_trigger

# Real skill level 10 values, cross-verified between api.dotgg.gg and
# lootandwaifus.com (exact match).
LETS_SING_TOGETHER = {
    "description_value_01": "30.02",  # squad Attack Damage %
    "description_value_02": "10",     # duration
    "description_value_03": "40",     # squad Max Ammo %
    "description_value_04": "10",     # duration
    "description_value_05": "45.05",  # squad Critical Damage %
    "description_value_06": "10",     # duration
}
FANTASTIC_PERFORMANCE = {
    "description_value_01": "19.94",  # squad Critical Rate %
    "description_value_02": "10",     # duration
    "description_value_03": "50",     # squad Projectile Explosion Damage % (inert)
    "description_value_04": "10",     # duration
    "description_value_05": "32.72",  # squad Pierce Damage %
    "description_value_06": "10",     # duration
}


def make_context():
    return SquadContext([
        SquadMember("mint", burst_tier=2, element="Iron"),
        SquadMember("ally", burst_tier=3, element="Fire"),
    ])


def build():
    return build_mint_rules({
        "lets_sing_together": LETS_SING_TOGETHER,
        "fantastic_performance": FANTASTIC_PERFORMANCE,
    })


ALLY = {"slug": "ally", "element": "Fire"}


def test_burst_grants_squad_attack_damage_max_ammo_and_crit_damage():
    ctx = make_context()
    registry = EffectRegistry()
    fire_trigger("own_burst_activate", {"mint": build()}, ctx, registry, time=5.0)

    assert round(registry.total_for("attack_damage_up", ALLY, now=5.0), 4) == 0.3002
    assert round(registry.total_for("max_ammo_percent", ALLY, now=5.0), 4) == 0.40
    assert round(registry.total_for("other_critical_damage_sources", ALLY, now=5.0), 4) == 0.4505
    assert registry.total_for("attack_damage_up", ALLY, now=15.1) == 0.0


def test_fantastic_performance_only_applies_while_singing():
    # 1st burst use -> Dancing (odd activation count); Fantastic Performance
    # should NOT apply this cycle.
    ctx = make_context()
    registry = EffectRegistry()
    rules = {"mint": build()}
    fire_trigger("own_burst_activate", rules, ctx, registry, time=5.0)
    fire_trigger("full_burst_enter", rules, ctx, registry, time=5.0)
    assert registry.total_for("crit_rate", ALLY, now=5.0) == 0.0

    # 2nd burst use -> Singing (even count); Fantastic Performance applies.
    fire_trigger("own_burst_activate", rules, ctx, registry, time=30.0)
    fire_trigger("full_burst_enter", rules, ctx, registry, time=30.0)
    assert round(registry.total_for("crit_rate", ALLY, now=30.0), 4) == 0.1994
    assert round(registry.total_for("projectile_explosion_damage_up", ALLY, now=30.0), 4) == 0.50
    assert round(registry.total_for("pierce_damage_up", ALLY, now=30.0), 4) == 0.3272


def test_fantastic_performance_alternates_off_again_on_the_third_use():
    ctx = make_context()
    registry = EffectRegistry()
    rules = {"mint": build()}
    for t in (5.0, 30.0, 55.0):
        fire_trigger("own_burst_activate", rules, ctx, registry, time=t)
        fire_trigger("full_burst_enter", rules, ctx, registry, time=t)
    # 3rd use -> Dancing again (odd count 3); no fresh buff at t=55, and the
    # one added at t=30 (10s duration) has already expired.
    assert registry.total_for("crit_rate", ALLY, now=55.0) == 0.0


def test_fantastic_performance_applies_when_singing_status_is_pinned():
    # Prika's Encore pins Mint's Singing status; then Fantastic Performance's
    # Singing branch applies on the FIRST burst (parity would say Dancing).
    ctx = make_context()
    ctx.set_status("mint", "singing")
    registry = EffectRegistry()
    rules = {"mint": build()}
    fire_trigger("own_burst_activate", rules, ctx, registry, time=5.0)
    fire_trigger("full_burst_enter", rules, ctx, registry, time=5.0)
    assert round(registry.total_for("crit_rate", ALLY, now=5.0), 4) == 0.1994


HERE_I_GO = {
    "description_value_01": "45.02",  # squad ATK % of Mint's ATK (Singing)
    "description_value_02": "3",      # duration
}


def test_here_i_go_applies_squad_atk_only_while_singing_status():
    rules = build_here_i_go_rules({**HERE_I_GO, "caster_atk": 300000})
    assert len(rules) == 1
    threshold, mode, skill_rules = rules[0]
    assert (threshold, mode) == (1, "every")  # every full charge (RL)

    ctx = make_context()
    registry = EffectRegistry()
    rule = skill_rules[0]

    # Not Singing -> condition false, no buff.
    assert rule.condition(ctx, "mint") is False

    # Singing status pinned (by Prika's Encore) -> squad ATK of Mint's ATK, 3s.
    ctx.set_status("mint", "singing")
    assert rule.condition(ctx, "mint") is True
    rule.action(ctx, "mint", 8.0, registry)
    assert round(registry.total_for("flat_atk", ALLY, now=8.0), 2) == round(300000 * 0.4502, 2)
    assert registry.total_for("flat_atk", ALLY, now=11.1) == 0.0  # 3s duration
