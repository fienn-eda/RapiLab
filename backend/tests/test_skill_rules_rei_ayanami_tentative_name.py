from app.effects import EffectRegistry
from app.skill_rules.rei_ayanami_tentative_name import (
    attack_state_burst_percent,
    build_annihilation_support_per_shot_rules,
    build_rei_tentative_rules,
)
from app.squad_engine import SquadContext, SquadMember, fire_trigger

CASTER_ATK = 70000.0

# Real skill level 10 values from lootandwaifus.com (values rendered inline;
# slots numbered by left-to-right appearance).
ANNIHILATION_SUPPORT = {
    "description_value_01": "18",      # deferred: Anti A.T. Field clause threshold
    "description_value_02": "590.64",  # deferred: its nuke % (needs Anti A.T. Field target status)
    "description_value_03": "10",      # deferred: Anti A.T. Field stacks +
    "description_value_04": "7",       # Attack State clause threshold (own-status window)
    "description_value_05": "286.37",  # its nuke % of final ATK ("as additional damage")
    "description_value_06": "1",       # deferred: Annihilation State units affected +
    "description_value_07": "9",       # deferred: duration
    "description_value_08": "500",     # deferred: Annihilation State attack range %
    "description_value_09": "9",       # deferred: duration
    "description_value_10": "17.6",    # deferred: Annihilation State ally ATK % of caster
    "description_value_11": "9",       # deferred: duration
}
MAINTENANCE_AND_RESUPPLY = {
    "description_value_01": "100",     # deferred: MG heating up speed %
    "description_value_02": "13",      # deferred: its duration
    "description_value_03": "11.61",   # squad flat ATK = % of caster ATK
    "description_value_04": "10",      # its duration
}
ATTACK_STATE = {
    "description_value_01": "35.9",    # self Attack Damage %
    "description_value_02": "10",      # its duration
    "description_value_03": "63.36",   # self flat ATK = % of caster ATK
    "description_value_04": "10",      # its duration
    "description_value_05": "990.2",   # burst nuke % of final ATK
}

ATTACK_STATE_WINDOW = 10.0  # Attack State lasts 10 sec from her burst


def make_context():
    return SquadContext([
        SquadMember("rei-ayanami-tentative-name", burst_tier=3, element="Wind"),
        SquadMember("ally", burst_tier=1, element="Fire"),
    ])


def build():
    return build_rei_tentative_rules({
        "maintenance_and_resupply": MAINTENANCE_AND_RESUPPLY,
        "attack_state": ATTACK_STATE,
        "caster_atk": CASTER_ATK,
    })


REI = {"slug": "rei-ayanami-tentative-name", "element": "Wind"}
ALLY = {"slug": "ally", "element": "Fire"}


def test_burst_percent_is_9902():
    assert attack_state_burst_percent({"attack_state": ATTACK_STATE}) == 990.2


def test_attack_state_burst_grants_self_attack_damage_and_flat_atk():
    ctx = make_context()
    registry = EffectRegistry()
    fire_trigger("own_burst_activate", {"rei-ayanami-tentative-name": build()}, ctx, registry, time=5.0)

    assert round(registry.total_for("attack_damage_up", REI, now=5.0), 4) == 0.359
    assert round(registry.total_for("flat_atk", REI, now=5.0), 4) == round(0.6336 * CASTER_ATK, 4)
    assert registry.total_for("attack_damage_up", ALLY, now=5.0) == 0.0  # self-only
    assert registry.total_for("attack_damage_up", REI, now=15.1) == 0.0  # 10s


def test_maintenance_grants_squad_flat_atk_on_full_burst_enter():
    ctx = make_context()
    registry = EffectRegistry()
    fire_trigger("full_burst_enter", {"rei-ayanami-tentative-name": build()}, ctx, registry, time=5.0)

    expected = round(0.1161 * CASTER_ATK, 4)
    assert round(registry.total_for("flat_atk", ALLY, now=5.0), 4) == expected
    assert round(registry.total_for("flat_atk", REI, now=5.0), 4) == expected  # squad incl. self
    assert registry.total_for("flat_atk", ALLY, now=15.1) == 0.0  # 10s


def test_annihilation_support_nukes_every_7_in_attack_state_window():
    rules = build_annihilation_support_per_shot_rules({"annihilation_support": ANNIHILATION_SUPPORT})
    assert len(rules) == 1
    threshold, mode, subrules = rules[0]
    assert (threshold, mode) == ((7, ATTACK_STATE_WINDOW), "every_during_own_status_window")

    registry = EffectRegistry()
    subrules[0].action(make_context(), "rei-ayanami-tentative-name", 5.0, registry)
    pulses = registry.drain_pulses("instant_damage_percent")
    assert len(pulses) == 1
    assert pulses[0].value == 286.37
