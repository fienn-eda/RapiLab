"""Centi's Favorite Item build - the same burst as base Centi, plus two buffs
hung off Skill 2's cycle, whose length her Full Charge cooldown cut decides."""
import pytest

from app.effects import EffectRegistry
from app.skill_rules.centi import (
    FIELD_DISCUSSION_COOLDOWN,
    build_centi_rules,
    build_field_discussion_resources,
    field_discussion_effective_cooldown,
    start_construction_burst_percent,
)
from app.skill_rules.registry import get_periodic_rules, get_resource_specs
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


def test_skill_2_drives_one_ten_stack_counter_on_its_own_cycle():
    (spec,) = build_field_discussion_resources(CENTI_SIG)
    assert spec.name == "field_discussion"
    assert spec.fill == ("periodic", field_discussion_effective_cooldown(CENTI_SIG))
    assert spec.cap == 10


def test_the_squad_atk_scales_with_the_caster_and_the_count():
    (spec,) = build_field_discussion_resources(CENTI_SIG)
    atk = next(b for b in spec.buffs if b.stat == "flat_atk")
    assert atk.scope == "squad"
    assert round(atk.value_fn(1), 4) == 4600.0
    assert round(atk.value_fn(10), 4) == 46000.0


def test_only_iron_code_allies_get_the_elemental_bonus():
    (spec,) = build_field_discussion_resources(CENTI_SIG)
    elemental = next(b for b in spec.buffs if b.stat == "other_elemental_bonus")
    assert elemental.scope == "element:Iron"
    assert round(elemental.value_fn(1), 4) == 0.0569
    assert round(elemental.value_fn(10), 4) == 0.569


def test_both_stacks_reach_the_cap_because_her_cycle_outruns_them():
    """"Stacks up to 10 times and lasts for 8 sec" (and 10 for the elemental
    bullet) is ONE timer per stack-set that every new stack restarts (the Raven
    ruling; Fienn confirmed the caps bind in game, 2026-08-17). Her cycle is
    what makes the distinction decidable, and it decides it: the gap between
    fills is the cooldown itself, and that never reaches the SHORTER of the two
    durations, so neither counter can lapse and a permanent accumulation is the
    faithful model. Per-stack expiry would hold her at 2 of the 10 stacks."""
    (spec,) = build_field_discussion_resources(CENTI_SIG)
    assert all(buff.lifetime is None for buff in spec.buffs)

    gap = field_discussion_effective_cooldown(CENTI_SIG)
    shortest_duration = float(FIELD_DISCUSSION["description_value_05"])
    assert gap < shortest_duration, f"a {gap:.2f}s cycle would drop the counter"


def test_a_split_stack_cap_is_refused_rather_than_guessed():
    """One counter serves both bullets only while their caps agree; if the data
    ever disagrees they are two different stacks and need a resource each."""
    split = dict(CENTI_SIG, maintain_fortification=dict(
        MAINTAIN_FORTIFICATION, description_value_05="5"))
    with pytest.raises(ValueError, match="share a stack cap"):
        build_field_discussion_resources(split)


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
    """The buffs only land if the registry threads them through - a builder
    nobody calls is silently inert. They moved from periodic rules to a
    resource when the stacks were found to reach their cap, so BOTH sides are
    asserted: the old path must be empty or the buffs would land twice."""
    assert get_periodic_rules("centi-signature", CENTI_SIG) is None
    specs = get_resource_specs("centi-signature", CENTI_SIG)
    assert specs is not None and len(specs) == 1
    assert specs[0].fill == ("periodic", pytest.approx(5.7378, abs=1e-4))
    assert {buff.stat for buff in specs[0].buffs} == {"flat_atk", "other_elemental_bonus"}


def test_the_favorite_item_leaves_the_burst_alone():
    assert start_construction_burst_percent(CENTI_SIG) == 145.46
    reg = _fire("own_burst_activate", build_centi_rules(CENTI_SIG))
    assert round(reg.total_for("enemy_def_percent", FIRE_ALLY, 0.0), 4) == -0.1454
    assert reg.total_for("enemy_def_percent", FIRE_ALLY, 10.1) == 0.0


def test_her_cooldown_cut_follows_the_clip_reload():
    # Her Skill 2 cooldown is derived from her shot interval, so the reload
    # model propagates into how often the squad ATK buff lands. Modelling one
    # reload made her cycle 5.74 sec; three loads make it 5.96.
    def values(reload_time):
        return {
            "maintain_fortification": {"description_value_02": "9.16"},
            "caster_weapon_stats": {
                "charge_time": 1.0, "max_ammo": 6, "reload_time": reload_time,
            },
        }

    assert round(field_discussion_effective_cooldown(values(1.5)), 4) == 5.9605
    assert round(field_discussion_effective_cooldown(values(0.5)), 4) == 5.7378
