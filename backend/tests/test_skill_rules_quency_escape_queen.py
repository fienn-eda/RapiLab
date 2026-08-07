"""Real max-level (base-skill) figures from lootandwaifus, slots numbered
left-to-right per skill (stage-number references in the text are not slots).
"""
from app.accuracy import spread_diameter
from app.effects import EffectRegistry
from app.skill_rules.quency_escape_queen import (
    STEADY_STATE_ATK,
    STEADY_STATE_HIT_RATE,
    build_quency_rules,
    the_great_thief_burst_percent,
)
from app.squad_engine import SquadContext, SquadMember

QUENCY_VALUES = {
    "secure_route": {
        "description_value_01": "49.58", "description_value_02": "25.25", "description_value_03": "16.73",
    },
    "the_great_thief": {
        "description_value_01": "57.08", "description_value_02": "10",
        "description_value_03": "25.87", "description_value_04": "10",
        "description_value_05": "1736.31",
    },
}

QUENCY = {"slug": "quency-escape-queen", "element": "Water"}


def make_context():
    return SquadContext([
        SquadMember("quency-escape-queen", burst_tier=3, element="Water"),
        SquadMember("ally", burst_tier=1, element="Iron"),
    ])


def test_steady_state_atk_is_fully_stacked_explore_route():
    assert round(STEADY_STATE_ATK, 4) == round(2.45 * 10 + 4.9 * 10 + 7.36 * 5, 4)


def test_the_great_thief_burst_percent():
    assert the_great_thief_burst_percent(QUENCY_VALUES) == 1736.31


def test_battle_start_grants_permanent_self_buffs():
    ctx = make_context()
    reg = EffectRegistry()
    for rule in build_quency_rules(QUENCY_VALUES):
        if rule.trigger == "battle_start":
            rule.action(ctx, "quency-escape-queen", 0.0, reg)
    assert round(reg.total_for("atk_percent", QUENCY, now=0.0), 4) == round(STEADY_STATE_ATK / 100, 4)
    assert round(reg.total_for("distributed_damage_up", QUENCY, now=0.0), 4) == 0.4958
    assert round(reg.total_for("other_core_damage_sources", QUENCY, now=0.0), 4) == 0.2525
    assert round(reg.total_for("crit_rate", QUENCY, now=0.0), 4) == 0.1673
    # permanent - still active far later in the fight
    assert round(reg.total_for("atk_percent", QUENCY, now=1000.0), 4) == round(STEADY_STATE_ATK / 100, 4)


def test_steady_state_hit_rate_is_fully_stacked_explore_route():
    """The three stages' Hit Rate, on the same caps as their ATK - 61.1%, which
    pulls a submachine gun's 110px spread inside a 50px core. Reading only the
    largest stage (4.08%) undercounts it fifteenfold."""
    assert round(STEADY_STATE_HIT_RATE, 4) == round(1.36 * 10 + 2.71 * 10 + 4.08 * 5, 4)
    assert round(STEADY_STATE_HIT_RATE, 2) == 61.10
    assert spread_diameter("SMG", STEADY_STATE_HIT_RATE / 100) < 50.0


def test_battle_start_grants_the_hit_rate_too():
    ctx = make_context()
    reg = EffectRegistry()
    for rule in build_quency_rules(QUENCY_VALUES):
        if rule.trigger == "battle_start":
            rule.action(ctx, "quency-escape-queen", 0.0, reg)
    expected = round(STEADY_STATE_HIT_RATE / 100, 4)
    assert round(reg.total_for("hit_rate", QUENCY, now=0.0), 4) == expected
    assert round(reg.total_for("hit_rate", QUENCY, now=1000.0), 4) == expected  # permanent
    assert reg.total_for("hit_rate", {"slug": "ally", "element": "Iron"}, now=0.0) == 0.0


def test_own_burst_self_attack_damage_and_reload_speed_for_10_sec():
    ctx = make_context()
    reg = EffectRegistry()
    for rule in build_quency_rules(QUENCY_VALUES):
        if rule.trigger == "own_burst_activate":
            rule.action(ctx, "quency-escape-queen", 5.0, reg)
    assert round(reg.total_for("attack_damage_up", QUENCY, now=5.0), 4) == 0.5708
    assert round(reg.total_for("reload_speed_percent", QUENCY, now=5.0), 4) == 0.2587
    assert reg.total_for("attack_damage_up", QUENCY, now=15.1) == 0.0  # 10s window


# Module-level fixture aliases so the assembly verification harness
# (test_skill_value_assembly.py) can resolve each sub-skill fixture by name.
SECURE_ROUTE = QUENCY_VALUES["secure_route"]
THE_GREAT_THIEF = QUENCY_VALUES["the_great_thief"]


def test_the_great_thief_burst_is_typed_distributed():
    # "Deals 1736.31% of final ATK as Distributed Damage" - without the typing
    # her own Secure Route Stage-1 buff (+49.58% Distributed Damage), and every
    # ally's, would miss the one instance they exist to multiply.
    from app.skill_rules.registry import get_burst_damage_type

    assert get_burst_damage_type("quency-escape-queen") == "distributed"
