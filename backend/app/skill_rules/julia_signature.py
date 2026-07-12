"""Julia's signature-weapon (dollskills) build, slug "julia-signature" - a
SEPARATE roster entry from base Julia (slug "julia"), per Fienn's decision to
model characters with an optional signature weapon as two distinct slugs
(2026-07-12), matching how Privaty/Helm: Aquamarine are already encoded.
PARTIAL - the Crescendo/Marcato crit-hit-count chain is deferred entirely (see
below), same as base Julia's Crescendo.

Modeled (DPS-relevant):
- Decrescendo (skills[0], own cooldown 20s): self Crit Rate +26.04% and self
  ATK +20% for 10 sec. Fires periodically (t=20,40,...) like base Julia's
  Decrescendo, PLUS an extra cast at battle start - Crescendo's "Activates at
  the start of battle... Forcefully uses Skill 1" bullet (alongside, not
  instead of, the periodic schedule - a forced use still starts her own
  cooldown, so the periodic ticks are unaffected).
- Climax (skills[2], her burst): deals 544.5% of final ATK as damage, attacking
  sequentially 5 times - 5 separate hits (`burst_hit_counts`), each
  independently defense-subtracted.

Not modeled / deferred:
- Decrescendo's Normal Attack Critical Rate +36.16%/10s: the engine has one
  crit_rate stat shared by every damage instance (burst/normal/per-shot) - no
  bucket for a NORMAL-ATTACK-ONLY crit rate distinct from the general one.
  Folding it into the general crit_rate would inflate her burst nuke's crit
  too, an overcount; deferred rather than faked.
- Crescendo/Marcato (skills[1]): both fill triggers are "after N CRITICAL hits
  with normal attacks" - the engine models crit as expected value (a
  probability baked into every hit's damage), not a per-hit RNG roll, so there
  is no "was this specific shot a crit" event to count. Fundamentally
  incompatible with the crit model, not just an unbuilt trigger - deferred.
  Climax's additional 544.5% hit (gated on Crescendo at max stacks) is
  deferred with it.
"""
from app.skill_rules._helpers import buff_rule

DECRESCENDO_COOLDOWN = 20.0  # skill text: Skill 1 cooldown 20s
CLIMAX_HIT_COUNT = 5  # skill text: "Attacks sequentially 5 times" (fixed, not a data slot)


def climax_burst_percent(values):
    return float(values["climax"]["description_value_01"])


def _decrescendo_buffs(values):
    crit_rate = float(values["description_value_01"]) / 100
    crit_rate_duration = float(values["description_value_02"])
    atk = float(values["description_value_03"]) / 100
    atk_duration = float(values["description_value_04"])
    return [
        ("crit_rate", crit_rate, "self", crit_rate_duration),
        ("atk_percent", atk, "self", atk_duration),
    ]


def build_decrescendo_periodic_rules(values):
    return [buff_rule("periodic", _decrescendo_buffs(values))]


def build_decrescendo_battle_start_rules(values):
    return [buff_rule("battle_start", _decrescendo_buffs(values))]
