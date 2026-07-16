from app.effects import EffectRegistry
from app.skill_rules.helm_aquamarine import (
    ADMIRE_ACCOMPANIMENT_NUKE_SHOT_COUNT,
    aegis_cannon_overload_burst_percent,
    aegis_cannon_suppression_fire_percent,
    build_admire_accompaniment_per_shot_rules,
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
    "description_value_01": "164.83",  # burst nuke % AND Electric-only additional bullet %
}
AEGIS_CANNON_SUPPRESSION_FIRE = {
    "description_value_01": "105.58",  # periodic nuke % of final ATK
    "description_value_02": "5.64",    # Electric-conditional Damage Taken % per stack
    "description_value_03": "5",       # stack cap
    "description_value_04": "5",       # duration
}


def make_context(boss_element=None):
    return SquadContext([
        SquadMember("helm-aquamarine", burst_tier=2, element="Iron"),
        SquadMember("ally", burst_tier=3, element="Fire"),
    ], boss_element=boss_element)


def build():
    return build_helm_aquamarine_rules({
        "admire_accompaniment": ADMIRE_ACCOMPANIMENT,
        "aegis_cannon_suppression_fire": AEGIS_CANNON_SUPPRESSION_FIRE,
        "aegis_cannon_overload": AEGIS_CANNON_OVERLOAD,
    })


SQUAD_TARGET = {"slug": "ally", "element": "Fire"}


def test_suppression_fire_electric_damage_taken_debuff_only_against_electric_boss():
    # "when attacking an Electric Code target: Damage Taken +5.64%, up to 5 stacks,
    # 5 sec" - her AR reaches 5 stacks in <0.5 sec and holds them, so it's modeled
    # as a steady-state 28.2% squad debuff, gated on an Electric boss.
    registry = EffectRegistry()
    ctx = make_context(boss_element="Electric")
    fire_trigger("battle_start", {"helm-aquamarine": build()}, ctx, registry, time=0.0)
    assert round(registry.total_for("damage_taken_up", SQUAD_TARGET, now=90.0), 4) == 0.282

    registry2 = EffectRegistry()
    iron_ctx = make_context(boss_element="Iron")
    fire_trigger("battle_start", {"helm-aquamarine": build()}, iron_ctx, registry2, time=0.0)
    assert registry2.total_for("damage_taken_up", SQUAD_TARGET, now=90.0) == 0.0


def test_overload_electric_additional_bullet_only_against_electric_boss():
    # "when attacking an Electric Code target: Deals 164.83% as additional damage" -
    # an extra burst bullet, gated on an Electric boss. Helm is Burst 2, so it fires
    # just before the Full Burst window opens - modeled without the Full Burst bonus
    # (Fienn, 2026-07-16).
    registry = EffectRegistry()
    ctx = make_context(boss_element="Electric")
    fire_trigger("own_burst_activate", {"helm-aquamarine": build()}, ctx, registry, time=5.0)
    pulses = registry.drain_pulses("instant_damage_percent")
    assert len(pulses) == 1
    assert pulses[0].value == 164.83
    assert pulses[0].full_burst_bonus_eligible is False
    assert pulses[0].source_slug == "helm-aquamarine"

    registry2 = EffectRegistry()
    iron_ctx = make_context(boss_element="Iron")
    fire_trigger("own_burst_activate", {"helm-aquamarine": build()}, iron_ctx, registry2, time=5.0)
    assert registry2.drain_pulses("instant_damage_percent") == []


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


def test_admire_accompaniment_nuke_fires_every_30_normal_attacks():
    rules = build_admire_accompaniment_per_shot_rules(ADMIRE_ACCOMPANIMENT)
    assert len(rules) == 1
    threshold, mode, skill_rules = rules[0]
    assert (threshold, mode) == (ADMIRE_ACCOMPANIMENT_NUKE_SHOT_COUNT, "every")
    assert ADMIRE_ACCOMPANIMENT_NUKE_SHOT_COUNT == 30

    ctx = make_context()
    registry = EffectRegistry()
    for rule in skill_rules:
        rule.action(ctx, "helm-aquamarine", 3.0, registry)
    pulses = registry.drain_pulses("instant_damage_percent")
    assert len(pulses) == 1
    assert pulses[0].value == 131.34
    assert pulses[0].source_slug == "helm-aquamarine"
