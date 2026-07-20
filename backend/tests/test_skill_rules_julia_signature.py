"""Julia's signature-weapon (dollskills) build, slug "julia-signature" - a
separate roster entry from base Julia (slug "julia"), per Fienn's decision to
model base/signature as distinct slugs (2026-07-12). Real max-level dollskill
figures from lootandwaifus, slots numbered left-to-right per skill.
"""
from app.effects import EffectRegistry
from app.skill_rules.julia_signature import (
    CLIMAX_HIT_COUNT,
    build_climax_signature_resource_scaled_nuke,
    build_crescendo_signature_resources,
    build_decrescendo_battle_start_rules,
    build_decrescendo_periodic_rules,
    build_marcato_per_shot_rules,
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


def test_crescendo_fills_on_expected_crits_and_caps_at_five():
    (spec,) = build_crescendo_signature_resources(JULIA_SIGNATURE_VALUES)

    assert spec.name == "crescendo"
    # The whole point of the 2026-07-20 reopening: a crit-count fill, not the
    # last-bullet fill base Julia uses.
    assert spec.fill == ("per_critical_hit_every", 6.0)
    assert spec.cap == 5


def test_each_crescendo_stack_is_crit_damage_for_fifteen_seconds():
    (spec,) = build_crescendo_signature_resources(JULIA_SIGNATURE_VALUES)
    (buff,) = spec.buffs

    assert buff.stat == "other_critical_damage_sources"
    assert buff.scope == "self"
    assert buff.lifetime == 15.0
    assert round(buff.value_fn(1), 4) == 0.2479
    assert round(buff.value_fn(5), 4) == round(0.2479 * 5, 4)


def test_marcato_fires_every_eight_expected_crits_as_additional_damage():
    (threshold, mode, rules), = build_marcato_per_shot_rules(JULIA_SIGNATURE_VALUES)

    assert (threshold, mode) == (8.0, "every_n_critical_hits")
    ctx = make_context()
    reg = EffectRegistry()
    for rule in rules:
        rule.action(ctx, "julia-signature", 30.0, reg)
    (pulse,) = reg.drain_pulses("instant_damage_percent")
    assert pulse.value == 88.0
    # "as additional damage" -> opts into the Full Burst Bonus
    assert pulse.full_burst_bonus_eligible


def test_climax_rider_only_pays_out_at_max_crescendo_stacks():
    (spec,) = build_climax_signature_resource_scaled_nuke(JULIA_SIGNATURE_VALUES)

    assert spec["resource"] == "crescendo"
    assert spec["base_percent"] == 544.5
    assert spec["scale_fn"](5) == 1.0
    assert spec["scale_fn"](4) == 0.0


# Module-level fixture aliases so the assembly verification harness
# (test_skill_value_assembly.py) can resolve each sub-skill fixture by name.
DECRESCENDO = JULIA_SIGNATURE_VALUES["decrescendo"]
CRESCENDO = JULIA_SIGNATURE_VALUES["crescendo"]
CLIMAX = JULIA_SIGNATURE_VALUES["climax"]
