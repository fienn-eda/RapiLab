"""Chisato Nishikigi (slug "chisato-nishikigi"), a Burst-3 Iron Submachine Gun
attacker. Base skills.

Modeled (DPS-relevant):
- Extrasensory (skills[0]): a self charge that starts at 100% and decays 1% every
  2s, gating tiered self buffs by charge level (>70% ATK +53.69%, >55% True Damage
  +48.62%, >25% Hit Rate +22.37%). Her burst recharges it to 100% every cycle, and
  40s of decay is only 20%, so in a bursting rotation the charge stays >70% -
  modeled as all three self buffs being permanently active (steady-state
  approximation). The Hit Rate tier rides the same approximation with room to
  spare: its threshold is the lowest of the three, so any charge level that keeps
  the other two also keeps it.
- AP Rounds (skills[1]): on burst, her normal attacks deal True Damage for 10s;
  every 48 normal attacks, a 472.18%-of-final-ATK nuke, itself True Damage - so it
  ignores enemy DEF and picks up True-Damage-Up buffs (including her own +48.62%).
- Emergency Charge (skills[2], her burst): self ATK +73.16% for 10s (also recharges
  Extrasensory - covered by the steady-state approximation above). Buffs-only burst.

Not modeled / deferred:
- Extrasensory's Invulnerable tier (>=100%) - survivability.
"""
from app.skill_rules._helpers import buff_rule, instant_nuke_pulse_rule


SKILL_VALUE_MANIFESTS = {
    "chisato-nishikigi": {
        "source": "lootandwaifus",
        "dotgg_slug": "chisato",
        "test_module": "test_skill_rules_burst3_eb2",
        "keys": {
            "extrasensory": ("skills", 0),
            "ap_rounds": ("skills", 1),
            "emergency_charge": ("skills", 2),
        },
    },
}


def build_chisato_rules(values):
    extra = values["extrasensory"]
    emergency = values["emergency_charge"]
    ap = values["ap_rounds"]
    steady_atk = float(extra["description_value_06"]) / 100
    steady_true_damage = float(extra["description_value_08"]) / 100
    steady_hit_rate = float(extra["description_value_10"]) / 100
    burst_atk = float(emergency["description_value_02"]) / 100
    burst_atk_duration = float(emergency["description_value_03"])
    true_conversion_duration = float(ap["description_value_01"])

    return [
        buff_rule("battle_start", [
            ("atk_percent", steady_atk, "self", None),
            ("true_damage_up", steady_true_damage, "self", None),
            ("hit_rate", steady_hit_rate, "self", None),
        ]),
        buff_rule("own_burst_activate", [
            ("atk_percent", burst_atk, "self", burst_atk_duration),
            ("normal_attacks_deal_true", 1.0, "self", true_conversion_duration),
        ]),
    ]


def build_chisato_per_shot_rules(values):
    ap = values["ap_rounds"]
    normal_count = int(ap["description_value_02"])
    nuke = float(ap["description_value_03"])
    return [
        (normal_count, "every",
         [instant_nuke_pulse_rule("per_shot", nuke, damage_type="true")]),
    ]
