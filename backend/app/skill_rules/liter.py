"""Liter (slug "liter"), a Burst-1 SMG supporter. Base skills (no signature).

Modeled (DPS-relevant):
- Liter Boost (skills[0]): on Full Burst enter, squad burst-cooldown reduction;
  on her own burst, squad Max Ammo + Crit Damage + ATK up.
- Double Boost (skills[2], her burst): squad ATK up.

Simplification: Liter Boost's on-burst effects escalate over the first three
activations ("previous effects trigger repeatedly"); a 3-minute raid reaches
the third-activation steady state almost immediately, so the max (all three)
values are used throughout. Volt Boost (skills[1]) is cover-HP restoration -
survivability, no DPS - and is not modeled.
"""
from app.skill_rules._helpers import buff_rule, cdr_pulse_rule


def build_liter_rules(values):
    boost = values["liter_boost"]
    double = values["double_boost"]
    cdr_sec = float(boost["description_value_03"])           # steady-state (3rd) CDR
    max_ammo = float(boost["description_value_04"]) / 100
    crit_damage = float(boost["description_value_06"]) / 100
    self_atk = float(boost["description_value_08"]) / 100
    on_burst_duration = float(boost["description_value_09"])
    double_atk = float(double["description_value_01"]) / 100
    double_duration = float(double["description_value_02"])

    return [
        cdr_pulse_rule("full_burst_enter", cdr_sec),
        buff_rule("own_burst_activate", [
            ("max_ammo_percent", max_ammo, "squad", on_burst_duration),
            ("other_critical_damage_sources", crit_damage, "squad", on_burst_duration),
            ("atk_percent", self_atk, "squad", on_burst_duration),
        ]),
        buff_rule("own_burst_activate", [
            ("atk_percent", double_atk, "squad", double_duration),
        ]),
    ]
