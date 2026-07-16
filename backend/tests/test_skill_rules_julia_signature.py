"""Julia's signature-weapon (dollskills) build, slug "julia-signature" - a
separate roster entry from base Julia (slug "julia"), per Fienn's decision to
model base/signature as distinct slugs (2026-07-12). Real max-level dollskill
figures from lootandwaifus, slots numbered left-to-right per skill.
"""
from app.effects import EffectRegistry
from app.skill_rules.julia_signature import (
    CLIMAX_HIT_COUNT,
    build_decrescendo_battle_start_rules,
    build_decrescendo_periodic_rules,
    climax_burst_percent,
)
from app.squad_engine import SquadContext, SquadMember

JULIA_SIGNATURE_VALUES = {
    "decrescendo": {
        "description_value_01": "26.04", "description_value_02": "10",
        "description_value_03": "20", "description_value_04": "10",
        "description_value_05": "36.16", "description_value_06": "10",
    },
    "crescendo": {
        "description_value_01": "6", "description_value_02": "24.79", "description_value_03": "5",
        "description_value_04": "15", "description_value_05": "8", "description_value_06": "88",
        "description_value_07": "100", "description_value_08": "1",
    },
    "climax": {"description_value_01": "544.5", "description_value_02": "5", "description_value_03": "544.5"},
}

JULIA = {"slug": "julia-signature", "element": "Water"}


def make_context():
    return SquadContext([
        SquadMember("julia-signature", burst_tier=3, element="Water"),
        SquadMember("ally", burst_tier=1, element="Iron"),
    ])


def test_climax_hit_count_is_five():
    assert CLIMAX_HIT_COUNT == 5


def test_climax_burst_percent_is_per_hit_base():
    assert climax_burst_percent(JULIA_SIGNATURE_VALUES) == 544.5


def test_decrescendo_periodic_buffs_self_crit_rate_and_atk():
    ctx = make_context()
    reg = EffectRegistry()
    for rule in build_decrescendo_periodic_rules(JULIA_SIGNATURE_VALUES["decrescendo"]):
        rule.action(ctx, "julia-signature", 20.0, reg)
    assert round(reg.total_for("crit_rate", JULIA, now=20.0), 4) == 0.2604
    assert round(reg.total_for("atk_percent", JULIA, now=20.0), 4) == 0.20
    assert reg.total_for("crit_rate", JULIA, now=30.1) == 0.0  # 10s window
    assert reg.total_for("atk_percent", JULIA, now=30.1) == 0.0


def test_decrescendo_periodic_rules_are_labeled_periodic():
    rules = build_decrescendo_periodic_rules(JULIA_SIGNATURE_VALUES["decrescendo"])
    assert all(r.trigger == "periodic" for r in rules)


def test_decrescendo_battle_start_rules_apply_same_buffs_at_t0():
    # Crescendo's "Activates at the start of battle... Forcefully uses Skill 1"
    # bullet - an extra Decrescendo cast at t=0, alongside (not replacing) the
    # normal periodic cd-20 schedule.
    ctx = make_context()
    reg = EffectRegistry()
    rules = build_decrescendo_battle_start_rules(JULIA_SIGNATURE_VALUES["decrescendo"])
    assert all(r.trigger == "battle_start" for r in rules)
    for rule in rules:
        rule.action(ctx, "julia-signature", 0.0, reg)
    assert round(reg.total_for("crit_rate", JULIA, now=0.0), 4) == 0.2604
    assert round(reg.total_for("atk_percent", JULIA, now=0.0), 4) == 0.20


# Module-level fixture aliases so the assembly verification harness
# (test_skill_value_assembly.py) can resolve each sub-skill fixture by name.
DECRESCENDO = JULIA_SIGNATURE_VALUES["decrescendo"]
CLIMAX = JULIA_SIGNATURE_VALUES["climax"]
