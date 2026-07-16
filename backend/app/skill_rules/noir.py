"""Noir (slug "noir"), a Burst-3 Wind Shotgun attacker. Base skills.

Modeled (DPS-relevant):
- Lucky Charm (skills[0]): squad ATK up (14.08% of caster's ATK), permanent. The
  ">70% HP" gate is approximated as always-on (true for most of a raid).
- Finale (skills[2], her burst): burst nuke 351.64% of final ATK, plus squad
  Damage-to-Interruption-Parts up (23.23% for 10s + 19.36% for 30s). The "Shotgun
  allies" / "ally from the same squad on the battlefield" scopes are approximated
  as squad. Like pierce, damage_to_parts_up is applied as a general Damage-Up term
  (not gated to actual parts hits) - the engine's existing convention.

Not modeled:
- Rabbit Twins B (skills[1]): Max Ammo +5 rounds (flat, not a %) and an instant
  partial magazine reload - ammo QoL, not representable as a buff and minor for DPS.
- Finale's Hit Rate buffs - Hit Rate is not consumed by this engine.
"""
from app.skill_rules._helpers import buff_rule


SKILL_VALUE_MANIFESTS = {
    "noir": {
        "source": "lootandwaifus",
        "test_module": "test_skill_rules_burst3_eb1",
        "keys": {
            "lucky_charm": ("skills", 0),
            "finale": ("skills", 2),
        },
        "drop_tokens": {
            "lucky_charm": [0],
        },
    },
}


def finale_burst_percent(values):
    return float(values["finale"]["description_value_01"])


def build_noir_rules(values):
    lucky = values["lucky_charm"]
    finale = values["finale"]
    caster_atk = values["caster_atk"]
    squad_atk = float(lucky["description_value_01"]) / 100 * caster_atk
    parts_1 = float(finale["description_value_04"]) / 100
    parts_1_duration = float(finale["description_value_05"])
    parts_2 = float(finale["description_value_08"]) / 100
    parts_2_duration = float(finale["description_value_09"])

    return [
        buff_rule("battle_start", [("flat_atk", squad_atk, "squad", None)]),
        buff_rule("own_burst_activate", [
            ("damage_to_parts_up", parts_1, "squad", parts_1_duration),
            ("damage_to_parts_up", parts_2, "squad", parts_2_duration),
        ]),
    ]
