from app.effects import EffectRegistry
from app.raid_simulator import simulate_raid
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


def make_context(boss_element=None):
    return SquadContext([
        SquadMember("rei-ayanami", burst_tier=3, element="Fire"),
        SquadMember("fire-ally", burst_tier=1, element="Fire"),
        SquadMember("wind-ally", burst_tier=2, element="Wind"),
    ], boss_element=boss_element)


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


def test_preemptive_subdual_elemental_advantage_is_not_boss_gated():
    rules = build_preemptive_subdual_per_shot_rules({"preemptive_subdual": PREEMPTIVE_SUBDUAL})
    _, _, subrules = rules[0]
    # nuke + the self Elemental Advantage buff now share the every-100 trigger
    assert len(subrules) == 2
    elem_buff = subrules[1]

    # The skill text names no element ("Elemental Advantage Attack Damage
    # +30.23%"), so the rule carries no boss gate of its own: damage_formula's
    # advantage gate alone decides when it pays out (Fire > Wind).
    for boss in ("Iron", "Water", "Wind", None):
        assert elem_buff.condition(make_context(boss_element=boss), "rei-ayanami") is True

    registry = EffectRegistry()
    elem_buff.action(make_context(boss_element="Wind"), "rei-ayanami", 5.0, registry)
    # self-scoped Elemental Advantage Attack Damage +30.23% (other_elemental_bonus) for 3 sec
    assert round(registry.total_for("other_elemental_bonus", REI, now=5.0), 4) == 0.3023
    assert registry.total_for("other_elemental_bonus", REI, now=8.1) == 0.0  # 3s duration
    assert registry.total_for("other_elemental_bonus", FIRE_ALLY, now=5.0) == 0.0  # self only


def test_preemptive_subdual_elemental_advantage_refreshes_not_stacks():
    rules = build_preemptive_subdual_per_shot_rules({"preemptive_subdual": PREEMPTIVE_SUBDUAL})
    _, _, subrules = rules[0]
    elem_buff = subrules[1]
    registry = EffectRegistry()
    # Two procs within the 3s window refresh, not stack (100-round condition met repeatedly).
    elem_buff.action(make_context(boss_element="Wind"), "rei-ayanami", 5.0, registry)
    elem_buff.action(make_context(boss_element="Wind"), "rei-ayanami", 7.0, registry)
    assert round(registry.total_for("other_elemental_bonus", REI, now=7.0), 4) == 0.3023


def _rei_solo_deck_damage(boss_element, subrules):
    """simulate_raid with Rei as the only damage source, so total_damage is a
    direct readout of her Elemental Advantage buff reaching the damage path."""
    deck = [
        {"slug": "tier1", "burst_tier": 1, "element": "Iron", "cooldown": 20.0},
        {"slug": "tier2", "burst_tier": 2, "element": "Iron", "cooldown": 20.0},
        {"slug": "rei-ayanami", "burst_tier": 3, "element": "Fire", "cooldown": 40.0},
    ]
    threshold, mode, _ = build_preemptive_subdual_per_shot_rules(
        {"preemptive_subdual": PREEMPTIVE_SUBDUAL})[0]
    return simulate_raid(
        deck,
        rules_by_slug={"tier1": [], "tier2": [], "rei-ayanami": []},
        burst_damage_percents={},
        base_stats={
            "tier1": {"atk": 0.0, "def": 0.0, "max_hp": 0.0},
            "tier2": {"atk": 0.0, "def": 0.0, "max_hp": 0.0},
            "rei-ayanami": {"atk": 100000.0, "def": 0.0, "max_hp": 0.0},
        },
        enemy_def=0.0,
        gauge_charge_time=5.0,
        fight_duration=60.0,
        mode="auto",
        base_crit_rate=0.0,
        boss_element=boss_element,
        weapon_stats={"rei-ayanami": {
            "weapon": "MG", "damage_percent": 5.57, "max_ammo": 300,
            "reload_time": 2.5, "charge_time": 0.0, "charge_damage_percent": 100.0,
        }},
        per_shot_rules={"rei-ayanami": [(threshold, mode, subrules)]},
    )["total_damage"]


def test_preemptive_subdual_elemental_advantage_pays_out_against_a_wind_boss():
    """Damage-path regression: Rei is Fire, so she holds advantage over WIND.
    Her (unqualified) "Elemental Advantage Attack Damage +30.23%" must raise her
    damage there - it was previously gated on an Iron boss, which the formula's
    advantage gate then made unreachable under every boss."""
    _, _, subrules = build_preemptive_subdual_per_shot_rules(
        {"preemptive_subdual": PREEMPTIVE_SUBDUAL})[0]
    nuke_only, with_elem_buff = subrules[:1], subrules

    assert (_rei_solo_deck_damage("Wind", with_elem_buff)
            > _rei_solo_deck_damage("Wind", nuke_only))


def test_preemptive_subdual_elemental_advantage_is_inert_without_advantage():
    """The same buff is Superior Code Damage: with no advantage over the boss
    (Fire is neutral vs Water) it must contribute nothing."""
    _, _, subrules = build_preemptive_subdual_per_shot_rules(
        {"preemptive_subdual": PREEMPTIVE_SUBDUAL})[0]
    nuke_only, with_elem_buff = subrules[:1], subrules

    assert (_rei_solo_deck_damage("Water", with_elem_buff)
            == _rei_solo_deck_damage("Water", nuke_only))
