"""Volume (slug "volume"), a Burst-1 SMG supporter. Base skills (no signature).

Modeled (DPS-relevant):
- Drop the Beat (skills[1]): on Full Burst enter, squad burst-cooldown
  reduction; on her own burst, squad Crit Damage up.
- Turn up the volume! (skills[2], her burst): squad Crit Rate up.

Simplification: both Drop the Beat effects escalate over the first three
activations ("previous effects trigger repeatedly"); the crit-damage tiers
stack, so the steady-state value is the sum of all three, and the CDR uses
the third-activation value. Freestyle (skills[0]) is a self ATK buff on kill,
which raid bosses don't grant, so it's not modeled.
"""
from app.skill_rules._helpers import buff_rule, cdr_pulse_rule


def build_volume_rules(values):
    beat = values["drop_the_beat"]
    turn_up = values["turn_up"]
    cdr_sec = float(beat["description_value_03"])  # steady-state (3rd) CDR
    crit_damage = (
        float(beat["description_value_04"])
        + float(beat["description_value_06"])
        + float(beat["description_value_08"])
    ) / 100  # three crit-damage tiers stack at steady state
    crit_damage_duration = float(beat["description_value_09"])
    crit_rate = float(turn_up["description_value_01"]) / 100
    crit_rate_duration = float(turn_up["description_value_02"])

    return [
        cdr_pulse_rule("full_burst_enter", cdr_sec),
        buff_rule("own_burst_activate", [
            ("other_critical_damage_sources", crit_damage, "squad", crit_damage_duration),
        ]),
        buff_rule("own_burst_activate", [
            ("crit_rate", crit_rate, "squad", crit_rate_duration),
        ]),
    ]
