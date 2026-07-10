from app.effects import EffectRegistry
from app.skill_rules.helm_aquamarine import (
    aegis_cannon_overload_burst_percent,
    aegis_cannon_suppression_fire_percent,
    build_helm_aquamarine_rules,
)
from app.squad_engine import SquadContext, SquadMember, fire_trigger

# Real skill level 10 values from lootandwaifus.com (Helm: Aquamarine).
ADMIRE_ACCOMPANIMENT = {
    "description_value_01": "131.34",  # deferred: 30-normal-attack nuke %
    "description_value_02": "1.82",    # Once: CDR sec
    "description_value_03": "2.2",     # Twice: CDR sec
    "description_value_04": "2.6",     # Three times: CDR sec
}
AEGIS_CANNON_OVERLOAD = {
    "description_value_01": "164.83",  # burst nuke % of final ATK
}
AEGIS_CANNON_SUPPRESSION_FIRE = {
    "description_value_01": "105.58",  # periodic nuke % of final ATK
    "description_value_02": "5.64",    # deferred: Electric-conditional Damage Taken %
    "description_value_03": "5",       # deferred: stack cap
    "description_value_04": "5",       # deferred: duration
}


def make_context():
    return SquadContext([
        SquadMember("helm-aquamarine", burst_tier=2, element="Iron"),
        SquadMember("ally", burst_tier=3, element="Fire"),
    ])


def build():
    return build_helm_aquamarine_rules({"admire_accompaniment": ADMIRE_ACCOMPANIMENT})


def test_burst_percent_is_16483():
    assert aegis_cannon_overload_burst_percent({"aegis_cannon_overload": AEGIS_CANNON_OVERLOAD}) == 164.83


def test_periodic_nuke_percent_is_10558():
    values = {"aegis_cannon_suppression_fire": AEGIS_CANNON_SUPPRESSION_FIRE}
    assert aegis_cannon_suppression_fire_percent(values) == 105.58


def test_cdr_escalates_and_sums_across_full_burst_enter_cycles():
    ctx = make_context()
    registry = EffectRegistry()
    rules = {"helm-aquamarine": build()}

    fire_trigger("full_burst_enter", rules, ctx, registry, time=5.0)
    pulses1 = registry.drain_pulses("burst_cooldown_reduction_sec")
    assert len(pulses1) == 1
    assert round(pulses1[0].value, 4) == 1.82
    assert pulses1[0].scope == "squad"

    fire_trigger("full_burst_enter", rules, ctx, registry, time=30.0)
    pulses2 = registry.drain_pulses("burst_cooldown_reduction_sec")
    assert round(pulses2[0].value, 4) == 4.02  # 1.82 + 2.2

    fire_trigger("full_burst_enter", rules, ctx, registry, time=55.0)
    pulses3 = registry.drain_pulses("burst_cooldown_reduction_sec")
    assert round(pulses3[0].value, 4) == 6.62  # 1.82 + 2.2 + 2.6


def test_cdr_stays_capped_at_three_tiers_on_later_cycles():
    ctx = make_context()
    registry = EffectRegistry()
    rules = {"helm-aquamarine": build()}
    pulses = None
    for t in (5.0, 30.0, 55.0, 80.0):
        fire_trigger("full_burst_enter", rules, ctx, registry, time=t)
        pulses = registry.drain_pulses("burst_cooldown_reduction_sec")
    # 4th cycle (t=80) should still be capped at the sum of all 3 tiers
    assert round(pulses[0].value, 4) == 6.62
