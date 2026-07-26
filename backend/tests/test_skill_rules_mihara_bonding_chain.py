"""Real max-level figures from lootandwaifus for Mihara: Bonding Chain
(slug "mihara-bonding-chain"), slots numbered left-to-right per skill.
"""
from app.effects import EffectRegistry
from app.raid_simulator import AFTER_WINDOW_EPSILON
from app.skill_rules.mihara_bonding_chain import (
    build_dragging_chain_resource_scaled_nukes,
    build_ensnaring_chain_resources,
    build_mihara_bonding_chain_rules,
    build_mihara_scheduled_nukes,
)
from app.squad_engine import SquadContext, SquadMember, fire_trigger

BODY_CONTACT = {
    "description_value_01": "10",     # Restraint Chains charged at battle start
    "description_value_02": "10",     # its cap
    "description_value_03": "10",     # Restraint Chains charged when Full Burst ends
    "description_value_04": "10",     # its cap
    "description_value_05": "50.06",  # damage % per chain attack
    "description_value_06": "1",      # Restraint Chains spent per attack
    "description_value_07": "25.08",  # Ensnaring Chains sustained damage %
    "description_value_08": "1",      # its tick interval sec
    "description_value_09": "20",     # Ensnaring Chains stack cap
}
TIGHTEN_UP = {
    "description_value_01": "40",     # normal attacks during Full Burst
    "description_value_02": "1",      # Ensnaring Chains stacks gained
    "description_value_03": "20",     # stacks granted when incapacitated (deferred)
    "description_value_04": "1",      # Restraint Chain on a neutralized enemy (deferred)
    "description_value_05": "10",     # its cap
    "description_value_06": "3",      # "entering Burst Stage 3"
    "description_value_07": "59.98",  # Sustained Damage %
    "description_value_08": "10",     # its duration sec
}
BONDING_PAIN = {
    "description_value_01": "50.05",  # Dragging Chain sustained damage %
    "description_value_02": "1",      # its tick interval sec
    "description_value_03": "10",     # its duration sec
}
MIHARA_VALUES = {
    "body_contact": BODY_CONTACT,
    "tighten_up": TIGHTEN_UP,
    "bonding_pain": BONDING_PAIN,
}
MIHARA = {"slug": "mihara-bonding-chain", "element": "Fire"}
ALLY = {"slug": "ally", "element": "Iron"}


def make_context(own_bursts=(), full_burst_starts=()):
    context = SquadContext(
        [
            SquadMember("mihara-bonding-chain", burst_tier=3, element="Fire"),
            SquadMember("ally", burst_tier=1, element="Iron"),
        ],
        base_atk={"mihara-bonding-chain": 60000.0, "ally": 0.0},
    )
    context.full_burst_windows = [(s, s + 10.0) for s in full_burst_starts]
    for burst_time in own_bursts:
        context.record_burst_time("mihara-bonding-chain", burst_time)
    return context


def ensnaring_spec():
    return build_ensnaring_chain_resources(MIHARA_VALUES)[0]


def test_ensnaring_chains_is_fed_by_discharges_and_the_normal_attack_trickle():
    spec = ensnaring_spec()
    assert spec.name == "ensnaring_chains"
    assert spec.cap == 20.0
    assert spec.fill == [
        (("at_battle_start",), 10.0),
        (("on_full_burst_end_after_own_burst",), 10.0),
        (("per_shot_every_during_full_burst", 40.0), 1.0),
    ]


def test_bonding_pain_wipes_ensnaring_chains_ten_seconds_after_her_burst():
    reset = ensnaring_spec().resets[0]
    assert reset == {"trigger": "own_burst_delayed", "delay": 10.0, "value": 0.0}


def test_chain_attacks_fire_one_hit_per_chain_at_each_discharge():
    chain_attacks = build_mihara_scheduled_nukes(MIHARA_VALUES)[0]
    assert chain_attacks["percent"] == 50.06
    # She bursts at t=20, inside the Full Burst window [20, 30); the chains
    # are re-banked and spent whole when that window ends.
    context = make_context(own_bursts=[20.0], full_burst_starts=[20.0, 45.0])

    times = chain_attacks["schedule"](context, 60.0)

    assert times.count(0.0) == 10   # battle start, all 10 chains at once
    assert times.count(30.0 + AFTER_WINDOW_EPSILON) == 10  # just after that Full Burst's end
    assert times.count(20.0) == 0   # not at the burst itself - the bank is empty
    assert times.count(45.0) == 0   # she did not burst in that window
    assert len(times) == 20


def test_ensnaring_dot_ticks_every_second_scaled_per_stack():
    dot = build_mihara_scheduled_nukes(MIHARA_VALUES)[1]
    assert dot["percent"] == 25.08
    assert dot["damage_type"] == "sustained"
    resource, cap, lifetime, scale_fn = dot["resource_gate"]
    assert (resource, cap, lifetime) == ("ensnaring_chains", 20.0, None)
    assert scale_fn(13) == 13
    context = make_context()

    times = dot["schedule"](context, 5.0)

    assert times == [1.0, 2.0, 3.0, 4.0]


def test_dragging_chain_mirrors_the_stack_count_for_ten_ticks():
    spec = build_dragging_chain_resource_scaled_nukes(MIHARA_VALUES)[0]
    assert spec["resource"] == "ensnaring_chains"
    assert spec["base_percent"] == 50.05
    assert spec["tick_count"] == 10
    assert spec["tick_interval"] == 1.0
    assert spec["damage_type"] == "sustained"
    assert spec["scale_fn"](20) == 20


def test_burst_stage_three_entry_grants_self_sustained_damage():
    context = make_context()
    registry = EffectRegistry()
    rules = {"mihara-bonding-chain": build_mihara_bonding_chain_rules(MIHARA_VALUES)}

    # "Entering Burst Stage 3" = a Burst 3 taking the slot, one beat BEFORE its
    # own cast settles - so it reaches that cast's damage.
    context.last_burst_slug = "mihara-bonding-chain"
    fire_trigger("ally_burst_activate", rules, context, registry, 20.0)

    assert registry.total_for("sustained_damage_up", MIHARA, 29.9) == 0.5998
    assert registry.total_for("sustained_damage_up", MIHARA, 30.1) == 0.0
    assert registry.total_for("sustained_damage_up", ALLY, 25.0) == 0.0  # self-scoped


def test_tighten_up_also_fires_when_an_allied_burst_three_takes_the_stage():
    # The stage, not the caster: she still gets it in cycles she does not burst.
    context = make_context()
    registry = EffectRegistry()
    rules = {"mihara-bonding-chain": build_mihara_bonding_chain_rules(MIHARA_VALUES)}

    context.last_burst_slug = "other-b3"
    context.members.append(SquadMember("other-b3", burst_tier=3, element="Water"))
    fire_trigger("ally_burst_activate", rules, context, registry, 20.0)
    assert registry.total_for("sustained_damage_up", MIHARA, 25.0) == 0.5998


def test_tighten_up_does_not_fire_on_a_lower_stage():
    context = make_context()
    registry = EffectRegistry()
    rules = {"mihara-bonding-chain": build_mihara_bonding_chain_rules(MIHARA_VALUES)}

    context.last_burst_slug = "ally"  # Burst 1
    fire_trigger("ally_burst_activate", rules, context, registry, 20.0)
    assert registry.total_for("sustained_damage_up", MIHARA, 25.0) == 0.0
