"""Little Mermaid (slug "little-mermaid"), a Burst-1 SMG supporter. Base skills.

Modeled (DPS-relevant):
- Bubble Order (skills[0]): squad burst-cooldown reduction when Full Burst
  ends; squad Attack Damage up when Full Burst begins.
- Bubble Wave (skills[1]): the "Bubble" enemy Damage Taken +5.05% debuff.
  It activates "when the enemy appears" (= battle start in a raid, always-on)
  and is continuous, so modeled as a permanent squad-scoped enemy debuff.
- Siren's Song (skills[2], her burst): squad Attack Damage up + self ATK up.

Not modeled:
- Bubble Barrage (Bubble Wave): 85% x10 hits each time ALLIES' total ammo
  expended reaches 500 - a squad-wide ammo counter, not the caster's own shots,
  so `per_shot_rules` (per-caster) doesn't cover it. Still a gap.
- Bubble Wave's Full-Burst-only periodic nuke (63.36% x4 every 1 sec DURING
  Full Burst) - the periodic-during-Full-Burst gap (same shape as Ada Wong),
  distinct from `periodic_nukes` which fires the whole fight.
- Explosive Bubble (after 50 of her own normal attacks): it removes Bubble and
  re-applies the same 5.05% Damage Taken (plus a 3s stun), so it adds no extra
  damage over the permanent Bubble already modeled - only the stun, which isn't
  modeled. Deliberately not double-counted.
- Bubble Order's "ally ammo reaches 400 -> Burst Gauge +37%" (gauge fill isn't a
  consumed stat) and Siren's Song's instant partial reload.
"""
from app.skill_rules._helpers import buff_rule, cdr_pulse_rule

SKILL_VALUE_MANIFESTS = {
    "little-mermaid": {
        "source": "dotgg",
        "test_module": "test_skill_rules_burst1_batch3",
        "keys": {
            "bubble_order": ("skills", 0),
            "bubble_wave": ("skills", 1),
            "sirens_song": ("skills", 2),
        },
    },
}


def build_little_mermaid_rules(values):
    order = values["bubble_order"]
    wave = values["bubble_wave"]
    siren = values["sirens_song"]
    cdr_sec = float(order["description_value_01"])
    fb_attack_damage = float(order["description_value_02"]) / 100
    fb_attack_damage_duration = float(order["description_value_03"])
    bubble_damage_taken = float(wave["description_value_01"]) / 100
    burst_attack_damage = float(siren["description_value_01"]) / 100
    burst_attack_damage_duration = float(siren["description_value_02"])
    self_atk = float(siren["description_value_04"]) / 100
    self_atk_duration = float(siren["description_value_05"])

    return [
        buff_rule("battle_start", [("damage_taken_up", bubble_damage_taken, "squad", None)]),
        cdr_pulse_rule("full_burst_end", cdr_sec),
        buff_rule("full_burst_enter", [
            ("attack_damage_up", fb_attack_damage, "squad", fb_attack_damage_duration),
        ]),
        buff_rule("own_burst_activate", [
            ("attack_damage_up", burst_attack_damage, "squad", burst_attack_damage_duration),
            ("atk_percent", self_atk, "self", self_atk_duration),
        ]),
    ]
