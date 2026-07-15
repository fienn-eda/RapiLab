from app.effects import EffectRegistry
from app.skill_rules.rei_ayanami import (
    annihilation_burst_percent,
    build_preemptive_subdual_per_shot_rules,
    build_rei_ayanami_rules,
)
from app.squad_engine import SquadContext, SquadMember, fire_trigger

CASTER_ATK = 75000.0

# Real skill level 10 values from lootandwaifus.com (values rendered inline;
# slots numbered by left-to-right appearance).
PREEMPTIVE_SUBDUAL = {
    "description_value_01": "100",     # normal-attack threshold (buff clause)
    "description_value_02": "30.23",   # deferred: Elemental Advantage Attack Damage %
    "description_value_03": "3",       # deferred: its duration
    "description_value_04": "100",     # normal-attack threshold (nuke clause)
    "description_value_05": "112.37",  # nuke % of final ATK
}
ATTACK_SUPPORT = {
    "description_value_01": "700.5",   # deferred: Damage dealt to Shield %
    "description_value_02": "25.03",   # Fire allies flat ATK = % of caster ATK
    "description_value_03": "10",      # its duration
}
ANNIHILATION = {
    "description_value_01": "13.44",   # deferred: Shield % of Max HP
    "description_value_02": "10",      # deferred: Shield duration
    "description_value_03": "48.02",   # Fire allies Attack Damage %
    "description_value_04": "10",      # its duration
    "description_value_05": "990.2",   # burst nuke % of final ATK
}


def make_context():
    return SquadContext([
        SquadMember("rei-ayanami", burst_tier=3, element="Fire"),
        SquadMember("fire-ally", burst_tier=1, element="Fire"),
        SquadMember("wind-ally", burst_tier=2, element="Wind"),
    ])


def build():
    return build_rei_ayanami_rules({
        "attack_support": ATTACK_SUPPORT,
        "annihilation": ANNIHILATION,
        "caster_atk": CASTER_ATK,
    })


REI = {"slug": "rei-ayanami", "element": "Fire"}
FIRE_ALLY = {"slug": "fire-ally", "element": "Fire"}
WIND_ALLY = {"slug": "wind-ally", "element": "Wind"}


def test_burst_percent_is_9902():
    assert annihilation_burst_percent({"annihilation": ANNIHILATION}) == 990.2


def test_attack_support_grants_fire_allies_flat_atk_on_full_burst_enter():
    ctx = make_context()
    registry = EffectRegistry()
    fire_trigger("full_burst_enter", {"rei-ayanami": build()}, ctx, registry, time=5.0)

    expected = round(0.2503 * CASTER_ATK, 4)
    assert round(registry.total_for("flat_atk", REI, now=5.0), 4) == expected
    assert round(registry.total_for("flat_atk", FIRE_ALLY, now=5.0), 4) == expected
    assert registry.total_for("flat_atk", WIND_ALLY, now=5.0) == 0.0  # Fire Code only
    assert registry.total_for("flat_atk", FIRE_ALLY, now=15.1) == 0.0  # 10s duration


def test_annihilation_grants_fire_allies_attack_damage_on_burst():
    ctx = make_context()
    registry = EffectRegistry()
    fire_trigger("own_burst_activate", {"rei-ayanami": build()}, ctx, registry, time=5.0)

    assert round(registry.total_for("attack_damage_up", FIRE_ALLY, now=5.0), 4) == 0.4802
    assert registry.total_for("attack_damage_up", WIND_ALLY, now=5.0) == 0.0  # Fire Code only
    assert registry.total_for("attack_damage_up", FIRE_ALLY, now=15.1) == 0.0


def test_preemptive_subdual_nukes_every_100_normal_attacks():
    rules = build_preemptive_subdual_per_shot_rules({"preemptive_subdual": PREEMPTIVE_SUBDUAL})
    assert len(rules) == 1
    threshold, mode, subrules = rules[0]
    assert (threshold, mode) == (100, "every")

    registry = EffectRegistry()
    subrules[0].action(make_context(), "rei-ayanami", 5.0, registry)
    pulses = registry.drain_pulses("instant_damage_percent")
    assert len(pulses) == 1
    assert pulses[0].value == 112.37
    assert pulses[0].full_burst_bonus_eligible is False  # "as damage", not "as additional damage"
