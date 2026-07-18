from app.effects import EffectRegistry
from app.skill_rules.scarlet_black_shadow import (
    BREAKTHROUGH_BASE_REQUIREMENTS,
    build_breakthrough_per_shot_rules,
    build_scarlet_black_shadow_rules,
)
from app.squad_engine import SquadContext, SquadMember, fire_trigger

# Real skill level 10 values from lootandwaifus.com (Scarlet: Black Shadow).
FLEETLY_FADING_BREAKTHROUGH = {
    "description_value_01": "1",       # targets the 1 lowest-final-DEF enemy (= the solo raid boss)
    "description_value_02": "283.03",  # stage 1 (3rd full charge) % of final ATK as damage
    "description_value_03": "565",     # stage 2 (6th) % as Distributed Damage
    "description_value_04": "848.03",  # stage 3 (9th) % as Distributed Damage
}
FLEETLY_FADING_ASURA = {
    "description_value_01": "60",   # self Max Ammunition Capacity %
    "description_value_02": "10",   # its duration
    "description_value_03": "100",  # magazine % reloaded on FB entry (deferred)
}
FLEETLY_FADING_STRIKE = {
    "description_value_01": "1",       # overridden stage-1 requirement
    "description_value_02": "2",       # overridden stage-2 requirement
    "description_value_03": "3",       # overridden stage-3 requirement
    "description_value_04": "10",      # override window duration
    "description_value_05": "115.12",  # self ATK %
    "description_value_06": "10",      # its duration
    "description_value_07": "169.63",  # self Charge Damage %
    "description_value_08": "10",      # its duration
}

VALUES = {
    "fleetly_fading_breakthrough": FLEETLY_FADING_BREAKTHROUGH,
    "fleetly_fading_asura": FLEETLY_FADING_ASURA,
    "fleetly_fading_strike": FLEETLY_FADING_STRIKE,
}

SCARLET = {"slug": "scarlet-black-shadow", "element": "Wind"}
ALLY = {"slug": "ally", "element": "Fire"}


def make_context():
    return SquadContext([
        SquadMember("scarlet-black-shadow", burst_tier=3, element="Wind"),
        SquadMember("ally", burst_tier=1, element="Fire"),
    ])


def test_burst_grants_self_atk_and_charge_damage():
    ctx = make_context()
    registry = EffectRegistry()
    rules = {"scarlet-black-shadow": build_scarlet_black_shadow_rules(VALUES)}
    fire_trigger("own_burst_activate", rules, ctx, registry, time=5.0)

    assert round(registry.total_for("atk_percent", SCARLET, now=5.0), 4) == 1.1512
    assert round(registry.total_for("charge_damage_bonus", SCARLET, now=5.0), 4) == 1.6963
    assert registry.total_for("atk_percent", ALLY, now=5.0) == 0.0  # self-only
    assert registry.total_for("atk_percent", SCARLET, now=15.1) == 0.0  # 10s duration


def test_full_burst_entry_grants_self_max_ammo():
    ctx = make_context()
    registry = EffectRegistry()
    rules = {"scarlet-black-shadow": build_scarlet_black_shadow_rules(VALUES)}
    fire_trigger("full_burst_enter", rules, ctx, registry, time=5.0)

    assert round(registry.total_for("max_ammo_percent", SCARLET, now=5.0), 4) == 0.6
    assert registry.total_for("max_ammo_percent", ALLY, now=5.0) == 0.0  # self-only
    assert registry.total_for("max_ammo_percent", SCARLET, now=15.1) == 0.0  # 10s duration


def test_breakthrough_sequence_spec_swaps_requirements_in_her_burst_window():
    entries = build_breakthrough_per_shot_rules(VALUES)
    assert len(entries) == 1
    spec, mode, stage_rules = entries[0]
    assert mode == "sequence"
    assert spec["requirements"] == list(BREAKTHROUGH_BASE_REQUIREMENTS) == [3, 6, 9]
    assert spec["own_burst_window"] == (10.0, [1, 2, 3])
    assert len(stage_rules) == 3


def test_breakthrough_stage_nukes_have_real_percents_and_distributed_typing():
    _, _, stage_rules = build_breakthrough_per_shot_rules(VALUES)[0]
    ctx = make_context()
    registry = EffectRegistry()

    expected = [(283.03, "attack"), (565.0, "distributed"), (848.03, "distributed")]
    for rules, (percent, damage_type) in zip(stage_rules, expected):
        for rule in rules:
            rule.action(ctx, "scarlet-black-shadow", 5.0, registry)
        pulses = registry.drain_pulses("instant_damage_percent")
        assert len(pulses) == 1
        assert pulses[0].value == percent
        assert pulses[0].damage_type == damage_type
        # "as damage" / "as Distributed Damage", never "as additional damage"
        assert pulses[0].full_burst_bonus_eligible is False
