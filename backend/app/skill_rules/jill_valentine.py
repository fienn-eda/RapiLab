"""Jill Valentine (slug "jill-valentine"), a Burst-3 Electric Assault Rifle
attacker. Base skills.

Modeled (DPS-relevant):
- Acid Ammo (skills[1]): on Full Burst enter, self ATK +40.03% for 10s.
- Magnum Ammo (skills[0]) + Supercop (skills[2], her burst): on burst, self True
  Damage +34.99%, Attack Damage +75%, Reload Speed +99.96%, and normal attacks
  deal True Damage - all for 10s. During her burst she sprays AR normal attacks as
  True Damage, boosted by those buffs; a buffs-only burst (no separate nuke).
- Magnum Ammo's 1st bullet: at battle start and on each reload to Max
  Ammunition, her next 9 rounds get Normal Attack Damage Multiplier +30% - a
  Final ATK modifier on her normal attacks only (damage-formula reference),
  modeled with the "first_bullet" per-shot marker + a 9-shot round grant of
  the normal_attack_damage_multiplier stat (gap #9). See
  build_magnum_per_shot_rules.
- Acid Ammo's 1st bullet: at battle start and on each reload to max, the first
  round applies a 192%/1s sustained DoT for 30 sec. Overlapping applications
  REFRESH (NIKKE convention - Fienn ruling 2026-07-16): her ~6s reload cadence
  against the 30s duration makes the refresh steady state a continuous
  1-tick/sec sustained DoT for the whole fight, modeled as a whole-fight
  periodic sustained nuke. See build_acid_ammo_periodic_nuke.

Not modeled / deferred:
- Supercop's Hit Rate buff (inert) and its forced-reload/ammo-removal bookkeeping.
"""
from app.skill_rules._helpers import buff_rule, round_buff_rule


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


def build_magnum_per_shot_rules(values):
    """Magnum Ammo: at battle start and on each reload to Max Ammunition, her
    next 9 rounds deal +30% normal-attack damage (first_bullet marker, gap #9;
    round-count buff; normal_attack_damage_multiplier = Final ATK modifier on
    normal attacks only)."""
    magnum = values["magnum_ammo"]
    multiplier = float(magnum["description_value_01"]) / 100
    rounds = int(float(magnum["description_value_02"]))
    return [(None, "first_bullet", [
        round_buff_rule("per_shot", [("normal_attack_damage_multiplier", multiplier, "self")], shots=rounds)
    ])]


def build_acid_ammo_periodic_nuke(values):
    """Acid Ammo: refreshed on every reload-to-max (~6s cadence) with a 30s
    duration, so the refresh steady state is a continuous 1 tick/sec sustained
    DoT from battle start (her trigger includes battle start). Modeled as a
    whole-fight periodic sustained nuke - the Fienn-confirmed refresh reading
    (2026-07-16) recorded in the module docstring."""
    acid = values["acid_ammo"]
    return {
        "cooldown": float(acid["description_value_02"]),
        "percent": float(acid["description_value_01"]),
        "damage_type": "sustained",
    }
