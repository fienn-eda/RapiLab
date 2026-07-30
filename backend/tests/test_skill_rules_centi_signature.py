"""Centi's Favorite Item build - the same burst as base Centi, plus two buffs
hung off Skill 2's cycle, whose length her Full Charge cooldown cut decides."""
from app.effects import EffectRegistry
from app.skill_rules.centi import (
    FIELD_DISCUSSION_COOLDOWN,
    build_centi_rules,
    build_field_discussion_periodic_rules,
    field_discussion_effective_cooldown,
    start_construction_burst_percent,
)
from app.skill_rules.registry import get_periodic_rules
from app.squad_engine import SquadContext, SquadMember, fire_trigger

MAINTAIN_FORTIFICATION = {
    "description_value_01": "2", "description_value_02": "9.16",
    "description_value_03": "2", "description_value_04": "5.69",
    "description_value_05": "10", "description_value_06": "10",
    "description_value_07": "7", "description_value_08": "5",
    "description_value_09": "7", "description_value_10": "100",
    "description_value_11": "7",
}
FIELD_DISCUSSION = {
    "description_value_01": "7", "description_value_02": "5",
    "description_value_03": "4.6", "description_value_04": "10",
    "description_value_05": "8",
}
START_CONSTRUCTION = {
    "description_value_01": "5", "description_value_02": "145.46",
    "description_value_03": "14.54", "description_value_04": "10",
    "description_value_05": "30.2",
}
CASTER_ATK = 100_000.0
# Base Centi's assembled weapon profile, which the Favorite Item leaves alone.
CENTI_WEAPON = {
    "weapon": "RL", "damage_percent": 61.3, "max_ammo": 6,
    "reload_time": 0.5, "charge_time": 1.0, "charge_damage_percent": 250.0,
}
CENTI_SIG = {
    "maintain_fortification": MAINTAIN_FORTIFICATION,
    "field_discussion": FIELD_DISCUSSION,
    "start_construction": START_CONSTRUCTION,
    "caster_atk": CASTER_ATK,
    "caster_weapon_stats": CENTI_WEAPON,
}

SELF = {"slug": "centi-signature", "element": "Iron"}
IRON_ALLY = {"slug": "iron-ally", "element": "Iron"}
FIRE_ALLY = {"slug": "fire-ally", "element": "Fire"}


def _context():
    return SquadContext([
        SquadMember("centi-signature", burst_tier=2, element="Iron", weapon="RL"),
        SquadMember("iron-ally", burst_tier=3, element="Iron", weapon="AR"),
        SquadMember("fire-ally", burst_tier=1, element="Fire", weapon="SMG"),
    ])


def _fire(trigger, rules, time=0.0):
    reg = EffectRegistry()
    fire_trigger(trigger, {"centi-signature": rules}, _context(), reg, time)
    return reg


def _fire_skill_2(time=0.0):
    return _fire("periodic", build_field_discussion_periodic_rules(CENTI_SIG), time)


def test_field_discussion_gives_the_squad_caster_scaled_atk():
    reg = _fire_skill_2()
    for member in (SELF, IRON_ALLY, FIRE_ALLY):
        assert round(reg.total_for("flat_atk", member, 0.0), 4) == 4600.0
    assert round(reg.total_for("flat_atk", SELF, 7.9), 4) == 4600.0
    assert reg.total_for("flat_atk", SELF, 8.1) == 0.0


def test_only_iron_code_allies_get_the_elemental_bonus():
    reg = _fire_skill_2()
    assert round(reg.total_for("other_elemental_bonus", SELF, 0.0), 4) == 0.0569
    assert round(reg.total_for("other_elemental_bonus", IRON_ALLY, 0.0), 4) == 0.0569
    assert reg.total_for("other_elemental_bonus", FIRE_ALLY, 0.0) == 0.0
    # It outlasts the ATK buff by two seconds.
    assert round(reg.total_for("other_elemental_bonus", SELF, 9.9), 4) == 0.0569
    assert reg.total_for("other_elemental_bonus", SELF, 10.1) == 0.0


def test_repeat_activations_stack_rather_than_refresh():
    """Both buffs read "Stacks up to 10 times", so two activations inside one
    buff window are worth two stacks - never one refreshed stack."""
    reg = EffectRegistry()
    rules = {"centi-signature": build_field_discussion_periodic_rules(CENTI_SIG)}
    ctx = _context()
    for tick in (5.0, 10.0):
        fire_trigger("periodic", rules, ctx, reg, tick)
    assert round(reg.total_for("flat_atk", SELF, 10.0), 4) == 9200.0
    assert round(reg.total_for("flat_atk", SELF, 13.1), 4) == 4600.0


def test_field_discussion_rules_are_labeled_periodic():
    assert all(r.trigger == "periodic"
               for r in build_field_discussion_periodic_rules(CENTI_SIG))


def test_full_charge_cooldown_cut_shortens_the_skill_2_cycle():
    cooldown = field_discussion_effective_cooldown(CENTI_SIG)
    # Her charged shots come 1.45 sec apart - a 1.0 sec charge plus the measured
    # 22-frame pause, with the 0.5 sec reload spread over the 6 rounds it buys.
    # Each shot knocks 9 x 9.16% = 0.8244 sec off, so the elapsed time plus what
    # those shots removed must add back up to the nominal cooldown.
    shots = cooldown / 1.45
    assert round(cooldown + shots * 0.8244, 6) == FIELD_DISCUSSION_COOLDOWN
    assert round(cooldown, 4) == 5.7378


def test_the_registry_hands_the_shortened_cooldown_to_the_engine():
    """The buffs only land if the registry threads them through as periodic
    rules - a builder nobody calls is silently inert."""
    groups = get_periodic_rules("centi-signature", CENTI_SIG)
    assert groups is not None and len(groups) == 1
    cooldown, rules = groups[0]
    assert round(cooldown, 4) == 5.7378
    assert [r.trigger for r in rules] == ["periodic"]


def test_the_favorite_item_leaves_the_burst_alone():
    assert start_construction_burst_percent(CENTI_SIG) == 145.46
    reg = _fire("own_burst_activate", build_centi_rules(CENTI_SIG))
    assert round(reg.total_for("enemy_def_percent", FIRE_ALLY, 0.0), 4) == -0.1454
    assert reg.total_for("enemy_def_percent", FIRE_ALLY, 10.1) == 0.0
