"""Modernia (slug "modernia"), a Burst-3 Fire Machine Gun attacker. Base skills.
First consumer of the named-resource / capped-stack-counter primitive (a TIMED
capped stack - see effects.ResourceSpec and raid_simulator's resolution pass).

Modeled (DPS-relevant):
- High-Speed Evolution (skills[0]): every normal-attack hit deals 3.05% of final
  ATK as additional damage (per-shot instant nuke). Every 200 hits, gains a stack
  of Critical Damage +14.25% AND Max Ammunition Capacity +5.04%, each stacking up
  to 5 and lasting 10 sec - modeled as one "evolution" resource (filled every 200
  shots, cap 5) driving two 10-sec linear buffs.
- Giant Leap (skills[1]) self ATK +29.38% for 10 sec: fires on every 200th
  normal hit counted from battle start - in-game it is NOT gated on the
  15-sec increasing-Hit-Rate window the skill text describes (Fienn
  2026-07-18), so it's a plain every-200 per-shot rule, refreshing (MG's
  60 shots/s puts consecutive marks well inside the 10s duration).

Not modeled / deferred:
- The Max Ammunition Capacity stack is emitted, but Max Ammo only feeds shot
  generation (magazine size / reload cadence), which is computed for this unit
  BEFORE the resource resolution pass runs - so it can't retroactively grow her
  own already-scheduled magazines. It's an inert-for-own-shots buff, kept for
  faithfulness (a future live-max-ammo consumer would read it).
- Giant Leap's all-ally Hit Rate buff: inert (not a damage stat).
- New World (skills[2], her burst): Full Burst Duration +5s, unlimited ammo, and
  Destroy Mode (auto-aim + a 2.24%-of-ATK Destroy-Mode damage over 15s) - a
  weapon/targeting mode, not a single burst nuke, so burst_percent is None.
- Its 2.24% Destroy-Mode damage and unlimited-ammo/FB-duration effects.
"""
from app.effects import ResourceSpec
from app.skill_rules._helpers import (
    instant_nuke_pulse_rule,
    linear_resource_buff,
    refreshing_buff_rule,
)

SKILL_VALUE_MANIFESTS = {
    "modernia": {
        "source": "lootandwaifus",
        "test_module": "test_skill_rules_resource_eb",
        "keys": {
            "high_speed_evolution": ("skills", 0),
            "giant_leap": ("skills", 1),
        },
    },
}


def build_modernia_resources(values):
    evo = values["high_speed_evolution"]
    hit_threshold = int(evo["description_value_02"])
    crit_per_stack = float(evo["description_value_03"]) / 100
    stack_cap = int(evo["description_value_04"])
    stack_duration = float(evo["description_value_05"])
    ammo_per_stack = float(evo["description_value_06"]) / 100
    return [
        ResourceSpec(
            name="evolution",
            fill=("per_shot_every", hit_threshold),
            cap=stack_cap,
            buffs=[
                linear_resource_buff(
                    "other_critical_damage_sources", crit_per_stack, "self", lifetime=stack_duration
                ),
                linear_resource_buff("max_ammo_percent", ammo_per_stack, "self", lifetime=stack_duration),
            ],
        )
    ]


def build_modernia_per_shot_rules(values):
    evo = values["high_speed_evolution"]
    additional = float(evo["description_value_01"])
    leap = values["giant_leap"]
    leap_threshold = int(leap["description_value_03"])
    leap_atk = float(leap["description_value_04"]) / 100
    leap_duration = float(leap["description_value_05"])
    return [
        (1, "every", [instant_nuke_pulse_rule("per_shot", additional)]),
        (leap_threshold, "every", [
            refreshing_buff_rule("per_shot", [
                ("atk_percent", leap_atk, "self", leap_duration),
            ]),
        ]),
    ]
