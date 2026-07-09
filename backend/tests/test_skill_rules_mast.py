from app.effects import EffectRegistry
from app.skill_rules.mast_romantic_maid import build_mast_rules
from app.squad_engine import SquadContext, SquadMember, fire_trigger

# Real skill level 10 values from api.dotgg.gg.
PIRATES_HEART = {
    "description_value_01": "20",     # Drunken: Hit Rate down (not modeled)
    "description_value_02": "3",      # max stacks
    "description_value_03": "20.05",  # while Drunken: squad Critical Rate %
    "description_value_04": "35.02",  # while Drunken: squad ATK % of caster's ATK
}
PIRATES_SPIRIT = {
    "description_value_01": "15.03",  # Distributed Damage per stack (not modeled)
    "description_value_02": "10",
    "description_value_03": "15.04",  # Reloading Speed % per stack
    "description_value_04": "10",
    "description_value_05": "10",     # Hangover stun sec
}
PIRATES_ROMANCE = {
    "description_value_01": "40.04",  # Critical Damage %
    "description_value_02": "10",
    "description_value_03": "15.04",  # Attack Damage %
    "description_value_04": "10",
    "description_value_05": "20.06",  # ATK % of caster's ATK per stack
    "description_value_06": "10",
}

DEALER = {"slug": "dealer", "element": "Fire"}


def build(caster_atk=10000):
    return build_mast_rules({
        "pirates_heart": PIRATES_HEART,
        "pirates_spirit": PIRATES_SPIRIT,
        "pirates_romance": PIRATES_ROMANCE,
        "caster_atk": caster_atk,
    })


def solo_context():
    return SquadContext([
        SquadMember("mast-romantic-maid", burst_tier=2, element="Water"),
        SquadMember("dealer", burst_tier=3, element="Fire"),
    ])


def anchor_context():
    return SquadContext([
        SquadMember("mast-romantic-maid", burst_tier=2, element="Water"),
        SquadMember("anchor-innocent-maid", burst_tier=2, element="Water"),
        SquadMember("dealer", burst_tier=3, element="Fire"),
    ])


def _fire_enter_cycles(rules, ctx, registry, times):
    for t in times:
        fire_trigger("full_burst_enter", {"mast-romantic-maid": rules}, ctx, registry, time=t)


def test_spirit_reload_cycles_when_mast_is_solo():
    # Solo: Drunken stacks 1->2->3->1 (Hangover stun resets at 3), so the
    # per-stack reload buff tracks that cycle.
    ctx = solo_context()
    registry = EffectRegistry()
    rules = build()
    times = [15.0, 35.0, 55.0, 75.0]  # >10s apart so only the current cycle's buff is live
    expected = [0.1504, 0.3008, 0.4512, 0.1504]
    for t, want in zip(times, expected):
        fire_trigger("full_burst_enter", {"mast-romantic-maid": rules}, ctx, registry, time=t)
        assert round(registry.total_for("reload_speed_percent", DEALER, now=t), 4) == want


def test_spirit_reload_holds_at_three_stacks_with_anchor():
    # With Anchor in the deck, Drunken holds 1->2->3->3 (no stun reset).
    ctx = anchor_context()
    registry = EffectRegistry()
    rules = build()
    times = [15.0, 35.0, 55.0, 75.0]
    expected = [0.1504, 0.3008, 0.4512, 0.4512]
    for t, want in zip(times, expected):
        fire_trigger("full_burst_enter", {"mast-romantic-maid": rules}, ctx, registry, time=t)
        assert round(registry.total_for("reload_speed_percent", DEALER, now=t), 4) == want


def test_drunken_continuous_buff_applied_once_and_kept():
    # The while-Drunken Critical Rate + ATK buff is flat (not stack-scaled) and
    # applied once from cycle 1, then kept for the fight.
    ctx = solo_context()
    registry = EffectRegistry()
    rules = build()

    _fire_enter_cycles(rules, ctx, registry, [15.0])
    assert round(registry.total_for("crit_rate", DEALER, now=15.0), 4) == 0.2005
    assert registry.total_for("flat_atk", DEALER, now=15.0) == 3502.0  # 35.02% of 10000

    # Cycle 2 must NOT re-apply it (no doubling).
    _fire_enter_cycles(rules, ctx, registry, [35.0])
    assert round(registry.total_for("crit_rate", DEALER, now=35.0), 4) == 0.2005
    assert registry.total_for("flat_atk", DEALER, now=35.0) == 3502.0


def test_romance_burst_applies_flat_buffs_and_stack_scaled_atk():
    # On her own burst: flat Critical Damage + Attack Damage, plus ATK scaled by
    # the current Drunken stack count.
    ctx = anchor_context()
    registry = EffectRegistry()
    rules = build()

    fire_trigger("own_burst_activate", {"mast-romantic-maid": rules}, ctx, registry, time=5.0)
    assert round(registry.total_for("other_critical_damage_sources", DEALER, now=5.0), 4) == 0.4004
    assert round(registry.total_for("attack_damage_up", DEALER, now=5.0), 4) == 0.1504
    # cycle 1 stacks = 1 -> 20.06% of 10000 * 1 = 2006
    assert registry.total_for("flat_atk", DEALER, now=5.0) == 2006.0

    # cycle 2 stacks = 2 -> 4012 (previous 10s window has expired by t=25)
    fire_trigger("own_burst_activate", {"mast-romantic-maid": rules}, ctx, registry, time=25.0)
    assert registry.total_for("flat_atk", DEALER, now=25.0) == 4012.0
