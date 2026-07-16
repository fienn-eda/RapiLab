"""Tove (slug "tove"), a Burst-1 AR supporter, signature weapon done
(dollskills). Fienn's Tove has hers completed.

Modeled (DPS-relevant):
- Modification Successful (dollskills[1]): squad Crit Rate up (continuous while
  Temporary Modification is fully stacked); shotgun allies additionally get
  Attack Speed +42.24% continuously (member-subset scope, gap #3 - live-read
  per magazine, so SG allies genuinely fire more shots).
- Miracle of Makeshifts (dollskills[2], her burst): squad ATK up as a flat
  bonus scaled off Tove's own ATK, mirroring the Temporary Modification stack
  count; shotgun allies get a second, bigger ATK bullet (+24.21% of caster ATK
  per stack) with the same "mirrors the stack count" wording, so it uses the
  same max-stack multiplier.

Assumption: Temporary Modification is treated as fully stacked (its max, from
Emergency-Crafted Bullets), reached quickly by Tove's own fire, so the Crit
Rate / SG Attack Speed are always on and both Miracle bullets use the max
stack multiplier. Not modeled:
- The normal-attack-count ramp of Temporary Modification itself.
"""
from app.skill_rules._helpers import buff_rule, member_subset_buff_rule

MAX_TEMP_MOD_STACKS = 3  # Emergency-Crafted Bullets "stacks up to 3 times"


def build_tove_rules(values):
    modification = values["modification_successful"]
    miracle = values["miracle_of_makeshifts"]
    caster_atk = values["caster_atk"]
    crit_rate = float(modification["description_value_01"]) / 100
    atk_per_stack = caster_atk * float(miracle["description_value_01"]) / 100
    atk_bonus = atk_per_stack * MAX_TEMP_MOD_STACKS
    atk_duration = float(miracle["description_value_02"])
    sg_attack_speed = float(modification["description_value_02"]) / 100
    sg_atk = caster_atk * float(miracle["description_value_03"]) / 100 * MAX_TEMP_MOD_STACKS
    sg_atk_duration = float(miracle["description_value_04"])

    sg_only = lambda m, context: m.weapon == "SG"

    return [
        buff_rule("battle_start", [("crit_rate", crit_rate, "squad", None)]),
        buff_rule("own_burst_activate", [("flat_atk", atk_bonus, "squad", atk_duration)]),
        # Modification Successful: continuous under the module's existing
        # full-stack steady-state assumption, like the squad crit rate.
        member_subset_buff_rule("battle_start", sg_only,
                                [("attack_speed_percent", sg_attack_speed, None)]),
        member_subset_buff_rule("own_burst_activate", sg_only,
                                [("flat_atk", sg_atk, sg_atk_duration)]),
    ]
