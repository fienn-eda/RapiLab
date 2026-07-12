"""Julia (slug "julia"), a Burst-3 Water Assault Rifle attacker. Base skills.
PARTIAL - her burst nuke and Skill 1 self-buff are modeled; the Crescendo
crit-damage-stack chain (and the burst's additional hit gated on it) is
deferred entirely (see below).

Modeled (DPS-relevant):
- Decrescendo (skills[0], own cooldown 20s): self Crit Rate +26.04% for 10 sec.
  A Skill 1 on its own cooldown fires at t=cooldown, 2*cooldown, ... - modeled
  via `periodic_rules` (see `raid_simulator`), like Takina Inoue's Battlefield
  Control.
- Climax (skills[2], her burst): deals 544.5% of final ATK as damage to the 5
  enemy unit(s) with the highest final DEF - in a solo-boss raid there's only
  one target, so this is a single 544.5% hit.

Not modeled / deferred:
- Crescendo (skills[1]): "Activates when the last bullet hits the target" -
  the fill trigger is a magazine-boundary ("last bullet") event, which
  `attack_rate`'s shot generation doesn't mark (no per-shot "is this the last
  round before reload" flag exists yet - a distinct gap from the per-shot
  counters/resource fills already built). Deferred rather than approximated.
- Climax's additional 544.5% hit ("Activates when Crescendo is at max
  stacks") is gated on the deferred Crescendo resource, so it's deferred with
  it - her burst here is the base 544.5% hit only.
"""
from app.skill_rules._helpers import buff_rule

DECRESCENDO_COOLDOWN = 20.0  # skill text: Skill 1 cooldown 20s


def climax_burst_percent(values):
    return float(values["climax"]["description_value_02"])


def build_decrescendo_rules(values):
    crit_rate = float(values["description_value_01"]) / 100
    duration = float(values["description_value_02"])
    return [buff_rule("periodic", [("crit_rate", crit_rate, "self", duration)])]
