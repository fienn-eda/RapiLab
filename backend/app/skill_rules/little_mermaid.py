"""Little Mermaid (slug "little-mermaid"), a Burst-1 SMG supporter. Base skills.

Modeled (DPS-relevant):
- Bubble Order (skills[0]): squad burst-cooldown reduction when Full Burst
  ends; squad Attack Damage up when Full Burst begins.
- Siren's Song (skills[2], her burst): squad Attack Damage up + self ATK up.

Not modeled: the ally-ammo-expended counter (gauge fill and the Bubble Wave
burst nuke both trigger off it - no such counter exists), the Bubble
damage-taken debuff (Focusing/target-state), and Siren's Song's instant
partial reload.
"""
from app.skill_rules._helpers import buff_rule, cdr_pulse_rule


def build_little_mermaid_rules(values):
    order = values["bubble_order"]
    siren = values["sirens_song"]
    cdr_sec = float(order["description_value_01"])
    fb_attack_damage = float(order["description_value_02"]) / 100
    fb_attack_damage_duration = float(order["description_value_03"])
    burst_attack_damage = float(siren["description_value_01"]) / 100
    burst_attack_damage_duration = float(siren["description_value_02"])
    self_atk = float(siren["description_value_04"]) / 100
    self_atk_duration = float(siren["description_value_05"])

    return [
        cdr_pulse_rule("full_burst_end", cdr_sec),
        buff_rule("full_burst_enter", [
            ("attack_damage_up", fb_attack_damage, "squad", fb_attack_damage_duration),
        ]),
        buff_rule("own_burst_activate", [
            ("attack_damage_up", burst_attack_damage, "squad", burst_attack_damage_duration),
            ("atk_percent", self_atk, "self", self_atk_duration),
        ]),
    ]
