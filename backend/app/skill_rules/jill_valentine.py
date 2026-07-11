"""Jill Valentine (slug "jill-valentine"), a Burst-3 Electric Assault Rifle
attacker. Base skills. PARTIAL encoding - her burst window is captured; two
ammo-state mechanics are deferred (see below).

Modeled (DPS-relevant):
- Acid Ammo (skills[1]): on Full Burst enter, self ATK +40.03% for 10s.
- Magnum Ammo (skills[0]) + Supercop (skills[2], her burst): on burst, self True
  Damage +34.99%, Attack Damage +75%, Reload Speed +99.96%, and normal attacks
  deal True Damage - all for 10s. During her burst she sprays AR normal attacks as
  True Damage, boosted by those buffs; a buffs-only burst (no separate nuke).

Not modeled / deferred:
- Magnum Ammo's "Normal Attack Damage Multiplier +30% for 9 rounds": a
  normal-attack-only multiplier over the next 9 bullets. It's neither a general
  attack-damage buff (would wrongly boost non-normal instances) nor cleanly a
  round-buff (there's no normal-attack-only damage stat), so it's deferred.
- Acid Ammo's "first round after a full reload deals 192% sustained damage every
  1s for 30s": a reload-triggered sustained DoT - no reload-boundary trigger.
- Supercop's Hit Rate buff (inert) and its forced-reload/ammo-removal bookkeeping.
"""
from app.skill_rules._helpers import buff_rule


def build_jill_rules(values):
    magnum = values["magnum_ammo"]
    acid = values["acid_ammo"]
    supercop = values["supercop"]
    fb_atk = float(acid["description_value_04"]) / 100
    fb_atk_duration = float(acid["description_value_05"])
    true_damage = float(magnum["description_value_03"]) / 100
    true_damage_duration = float(magnum["description_value_04"])
    reload_speed = float(supercop["description_value_01"]) / 100
    reload_speed_duration = float(supercop["description_value_02"])
    attack_damage = float(supercop["description_value_06"]) / 100
    attack_damage_duration = float(supercop["description_value_07"])
    true_conversion_duration = float(supercop["description_value_08"])

    return [
        buff_rule("full_burst_enter", [("atk_percent", fb_atk, "self", fb_atk_duration)]),
        buff_rule("own_burst_activate", [
            ("true_damage_up", true_damage, "self", true_damage_duration),
            ("attack_damage_up", attack_damage, "self", attack_damage_duration),
            ("reload_speed_percent", reload_speed, "self", reload_speed_duration),
            ("normal_attacks_deal_true", 1.0, "self", true_conversion_duration),
        ]),
    ]
