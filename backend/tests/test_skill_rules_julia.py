"""Real max-level (base-skill) figures from lootandwaifus, slots numbered
left-to-right per skill."""
from app.effects import EffectRegistry
from app.skill_rules.julia import (
    DECRESCENDO_COOLDOWN,
    build_decrescendo_rules,
    climax_burst_percent,
)
from app.squad_engine import SquadContext, SquadMember

JULIA_VALUES = {
    "decrescendo": {"description_value_01": "26.04", "description_value_02": "10"},
    "crescendo": {"description_value_01": "24.79", "description_value_02": "5", "description_value_03": "15"},
    "climax": {"description_value_01": "5", "description_value_02": "544.5", "description_value_03": "544.5"},
}

JULIA = {"slug": "julia", "element": "Water"}


def make_context():
    return SquadContext([
        SquadMember("julia", burst_tier=3, element="Water"),
        SquadMember("ally", burst_tier=1, element="Iron"),
    ])


def test_decrescendo_cooldown_is_20s():
    assert DECRESCENDO_COOLDOWN == 20.0


def test_decrescendo_self_crit_rate_for_10_sec():
    ctx = make_context()
    reg = EffectRegistry()
    for rule in build_decrescendo_rules(JULIA_VALUES["decrescendo"]):
        rule.action(ctx, "julia", 20.0, reg)
    assert round(reg.total_for("crit_rate", JULIA, now=20.0), 4) == 0.2604
    assert reg.total_for("crit_rate", JULIA, now=30.1) == 0.0  # 10s window


def test_decrescendo_rules_are_labeled_periodic():
    assert all(r.trigger == "periodic" for r in build_decrescendo_rules(JULIA_VALUES["decrescendo"]))


def test_climax_burst_percent_is_base_hit_only():
    assert climax_burst_percent(JULIA_VALUES) == 544.5
