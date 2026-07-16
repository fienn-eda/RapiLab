from app.effects import EffectRegistry
from app.skill_rules.brid_silent_track import (
    JOURNEY_AHEAD_DEBUFF_SHOT_COUNT,
    JOURNEY_AHEAD_NUKE_SHOT_COUNT,
    build_brid_rules,
    build_journey_ahead_rules,
)
from app.squad_engine import SquadContext, SquadMember, fire_trigger

JOURNEY_AHEAD = {
    "description_value_01": "12.12",  # Wind Code enemy Damage Taken % (every 10 normals)
    "description_value_02": "10",     # duration
    "description_value_03": "675",    # nuke % of final ATK, every 5 normal attacks
}

# Real skill level 10 values from api.dotgg.gg.
IGNITION_SEQUENCE = {
    "description_value_01": "15.12",  # Wind Code enemy Damage Taken % (on Full Burst enter)
    "description_value_02": "10",     # duration
    "description_value_03": "636",    # instant nuke % of final ATK
}
FULL_THROTTLE = {
    "description_value_01": "66.52",  # squad(approx) ATK % of caster's ATK
    "description_value_02": "10",     # duration
    "description_value_03": "0",      # unused slot
    "description_value_04": "10",     # unused slot
}


def make_context(boss_element=None):
    return SquadContext([
        SquadMember("brid-silent-track", burst_tier=2, element="Fire"),
        SquadMember("ally", burst_tier=3, element="Wind"),
    ], boss_element=boss_element)


def build(caster_atk=10000):
    return build_brid_rules({
        "ignition_sequence": IGNITION_SEQUENCE,
        "full_throttle": FULL_THROTTLE,
        "caster_atk": caster_atk,
    })


ALLY = {"slug": "ally", "element": "Wind"}


def test_ignition_sequence_emits_an_instant_nuke_pulse_on_full_burst_enter():
    ctx = make_context()
    registry = EffectRegistry()
    fire_trigger("full_burst_enter", {"brid-silent-track": build()}, ctx, registry, time=5.0)

    pulses = registry.drain_pulses("instant_damage_percent")
    assert len(pulses) == 1
    assert pulses[0].value == 636.0
    assert pulses[0].source_slug == "brid-silent-track"


def test_full_throttle_grants_squad_atk_on_own_burst():
    ctx = make_context()
    registry = EffectRegistry()
    fire_trigger("own_burst_activate", {"brid-silent-track": build()}, ctx, registry, time=5.0)

    # 66.52% of caster ATK 10000 = 6652, for 10 sec.
    assert registry.total_for("flat_atk", ALLY, now=5.0) == 6652.0
    assert registry.total_for("flat_atk", ALLY, now=15.1) == 0.0


def test_ignition_sequence_wind_debuff_applies_only_against_wind_boss():
    registry = EffectRegistry()
    rules = {"brid-silent-track": build()}
    # Wind Code enemy Damage Taken +15.12% for 10 sec, on Full Burst enter.
    wind_ctx = make_context(boss_element="Wind")
    fire_trigger("full_burst_enter", rules, wind_ctx, registry, time=5.0)
    assert round(registry.total_for("damage_taken_up", ALLY, now=5.0), 4) == 0.1512
    assert registry.total_for("damage_taken_up", ALLY, now=15.1) == 0.0

    # No debuff against a non-Wind boss (boss-element-gated).
    registry2 = EffectRegistry()
    iron_ctx = make_context(boss_element="Iron")
    fire_trigger("full_burst_enter", rules, iron_ctx, registry2, time=5.0)
    assert registry2.total_for("damage_taken_up", ALLY, now=5.0) == 0.0


def test_journey_ahead_wind_debuff_fires_every_10_normal_attacks_against_wind_boss():
    rules = build_journey_ahead_rules(JOURNEY_AHEAD)
    debuff_entry = next(r for r in rules if r[0] == JOURNEY_AHEAD_DEBUFF_SHOT_COUNT)
    threshold, mode, skill_rules = debuff_entry
    assert (threshold, mode) == (10, "every")

    registry = EffectRegistry()
    wind_ctx = make_context(boss_element="Wind")
    for rule in skill_rules:
        if rule.condition(wind_ctx, "brid-silent-track"):
            rule.action(wind_ctx, "brid-silent-track", 3.0, registry)
    # 12.12% Wind Code Damage Taken for 10 sec.
    assert round(registry.total_for("damage_taken_up", ALLY, now=3.0), 4) == 0.1212

    registry2 = EffectRegistry()
    iron_ctx = make_context(boss_element="Iron")
    for rule in skill_rules:
        if rule.condition(iron_ctx, "brid-silent-track"):
            rule.action(iron_ctx, "brid-silent-track", 3.0, registry2)
    assert registry2.total_for("damage_taken_up", ALLY, now=3.0) == 0.0


def test_journey_ahead_nuke_fires_every_5_normal_attacks():
    rules = build_journey_ahead_rules(JOURNEY_AHEAD)
    nuke_entry = next(r for r in rules if r[0] == JOURNEY_AHEAD_NUKE_SHOT_COUNT)
    threshold, mode, skill_rules = nuke_entry
    assert (threshold, mode) == (JOURNEY_AHEAD_NUKE_SHOT_COUNT, "every")
    assert JOURNEY_AHEAD_NUKE_SHOT_COUNT == 5

    ctx = make_context()
    registry = EffectRegistry()
    for rule in skill_rules:
        rule.action(ctx, "brid-silent-track", 3.0, registry)
    pulses = registry.drain_pulses("instant_damage_percent")
    assert len(pulses) == 1
    assert pulses[0].value == 675.0
    assert pulses[0].source_slug == "brid-silent-track"
