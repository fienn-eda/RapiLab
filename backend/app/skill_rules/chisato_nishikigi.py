"""Chisato Nishikigi (slug "chisato-nishikigi"), a Burst-3 Iron Submachine Gun
attacker. Base skills.

Modeled (DPS-relevant):
- Extrasensory (skills[0]): a self charge that starts at 100% and decays 1% every
  2s, gating tiered self buffs by charge level (>70% ATK +53.69%, >55% True Damage
  +48.62%). Her burst recharges it to 100% every cycle, and 40s of decay is only
  20%, so in a bursting rotation the charge stays >70% - modeled as those two self
  buffs being permanently active (steady-state approximation; the >25% Hit Rate
  tier is inert).
- AP Rounds (skills[1]): on burst, her normal attacks deal True Damage for 10s;
  every 48 normal attacks, a 472.18%-of-final-ATK nuke.
- Emergency Charge (skills[2], her burst): self ATK +73.16% for 10s (also recharges
  Extrasensory - covered by the steady-state approximation above). Buffs-only burst.

Not modeled / deferred:
- The 48-normal nuke is True Damage in-game, but per-shot nukes are currently
  attack-typed only, so it's modeled as attack damage - an undercount (it misses
  the True-Damage buff and DEF-ignore), never an overcount.
- Extrasensory's Invulnerable/Hit Rate tiers - survivability / inert.
"""
from app.skill_rules._helpers import buff_rule, instant_nuke_pulse_rule


def build_chisato_rules(values):
    extra = values["extrasensory"]
    emergency = values["emergency_charge"]
    ap = values["ap_rounds"]
    steady_atk = float(extra["description_value_06"]) / 100
    steady_true_damage = float(extra["description_value_08"]) / 100
    burst_atk = float(emergency["description_value_02"]) / 100
    burst_atk_duration = float(emergency["description_value_03"])
    true_conversion_duration = float(ap["description_value_01"])

    return [
        buff_rule("battle_start", [
            ("atk_percent", steady_atk, "self", None),
            ("true_damage_up", steady_true_damage, "self", None),
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
        (normal_count, "every", [instant_nuke_pulse_rule("per_shot", nuke)]),
    ]
