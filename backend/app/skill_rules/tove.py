"""Tove (slug "tove"), a Burst-1 AR supporter, signature weapon done
(dollskills). Fienn's Tove has hers completed.

Modeled (DPS-relevant):
- Modification Successful (dollskills[1]): squad Crit Rate up (continuous while
  Temporary Modification is fully stacked).
- Miracle of Makeshifts (dollskills[2], her burst): squad ATK up as a flat
  bonus scaled off Tove's own ATK, mirroring the Temporary Modification stack
  count.

Assumption: Temporary Modification is treated as fully stacked (its max, from
Emergency-Crafted Bullets), reached quickly by Tove's own fire, so the Crit
Rate is always on and Miracle uses the max stack multiplier. Not modeled:
- The Attack Speed buff (+42.24%) AND the ATK variant (+24.21% of caster ATK)
  from Modification Successful / Miracle both target "shotgun allies only". The
  engine now consumes attack_speed_percent (Phase S), but only self/squad/element
  scopes exist - a weapon-type scope (Phase C, gap #3) is needed to apply these
  to shotgun allies without over-crediting non-shotgun allies. Both are DEFERRED
  to Phase C together (per Fienn, 2026-07-16); squad-approx was rejected because
  attack-speed over-application to non-SG allies distorts the deck search.
- The normal-attack-count ramp of Temporary Modification itself.
"""
from app.skill_rules._helpers import buff_rule

MAX_TEMP_MOD_STACKS = 3  # Emergency-Crafted Bullets "stacks up to 3 times"


def build_tove_rules(values):
    modification = values["modification_successful"]
    miracle = values["miracle_of_makeshifts"]
    caster_atk = values["caster_atk"]
    crit_rate = float(modification["description_value_01"]) / 100
    atk_per_stack = caster_atk * float(miracle["description_value_01"]) / 100
    atk_bonus = atk_per_stack * MAX_TEMP_MOD_STACKS
    atk_duration = float(miracle["description_value_02"])

    return [
        buff_rule("battle_start", [("crit_rate", crit_rate, "squad", None)]),
        buff_rule("own_burst_activate", [("flat_atk", atk_bonus, "squad", atk_duration)]),
    ]
