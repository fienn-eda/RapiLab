"""Julia (slug "julia"), a Burst-3 Water Assault Rifle attacker. Base skills.

Second consumer (after Mana) of `resource_scaled_nukes`, and first consumer
of the `("on_last_bullet",)` resource fill kind - both Crescendo and its
gated Climax additional hit were deferred pending gap #1's "last bullet"
marker (built 2026-07-12), motivating that engine capability originally.

Modeled (DPS-relevant):
- Decrescendo (skills[0], own cooldown 20s): self Crit Rate +26.04% for 10 sec.
  A Skill 1 on its own cooldown fires at t=cooldown, 2*cooldown, ... - modeled
  via `periodic_rules` (see `raid_simulator`), like Takina Inoue's Battlefield
  Control.
- Crescendo (skills[1]): "Activates when the last bullet hits the target" -
  self Critical Damage +24.79%, stacks up to 5 times, each stack lasting 15
  sec (`ResourceSpec` with `fill=("on_last_bullet",)`, cap 5).
- Climax (skills[2], her burst): deals 544.5% of final ATK as damage to the 5
  enemy unit(s) with the highest final DEF (in a solo-boss raid, a single
  hit) - plus, "when Crescendo is at max stacks," an ADDITIONAL 544.5% hit
  (`resource_scaled_nukes`, gated on Crescendo's count at burst time via
  `scale_fn`). Only the additional hit's text says "as additional damage"
  (the base hit says plain "as damage"), so only the additional hit opts
  into `full_burst_bonus_eligible`.
"""
from app.skill_rules._helpers import buff_rule, linear_resource_buff
from app.effects import ResourceSpec


SKILL_VALUE_MANIFESTS = {
    "julia": {
        "source": "lootandwaifus",
        "test_module": "test_skill_rules_julia",
        "keys": {
            "decrescendo": ("skills", 0),
            "crescendo": ("skills", 1),
            "climax": ("skills", 2),
        },
    },
}


DECRESCENDO_COOLDOWN = 20.0  # skill text: Skill 1 cooldown 20s


def climax_burst_percent(values):
    return float(values["climax"]["description_value_02"])


def build_decrescendo_rules(values):
    crit_rate = float(values["description_value_01"]) / 100
    duration = float(values["description_value_02"])
    return [buff_rule("periodic", [("crit_rate", crit_rate, "self", duration)])]


def build_crescendo_resources(values):
    cres = values["crescendo"]
    per_stack = float(cres["description_value_01"]) / 100
    cap = int(float(cres["description_value_02"]))
    lifetime = float(cres["description_value_03"])
    return [
        ResourceSpec(
            name="crescendo",
            fill=("on_last_bullet",),
            cap=cap,
            buffs=[linear_resource_buff("other_critical_damage_sources", per_stack, "self", lifetime=lifetime)],
        )
    ]


def build_climax_resource_scaled_nuke(values):
    cap = int(float(values["crescendo"]["description_value_02"]))
    additional_percent = float(values["climax"]["description_value_03"])
    return [{
        "resource": "crescendo", "cap": cap, "base_percent": additional_percent,
        "scale_fn": lambda count, cap=cap: 1.0 if count >= cap else 0.0,
        "tick_count": 1, "tick_interval": 0.0,
        "full_burst_bonus_eligible": True,
    }]
