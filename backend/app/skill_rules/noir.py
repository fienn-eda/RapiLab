"""Noir (slug "noir"), a Burst-3 Wind Shotgun attacker. Base skills.

Modeled (DPS-relevant):
- Lucky Charm (skills[0]): squad ATK up (14.08% of caster's ATK), permanent. The
  ">70% HP" gate is approximated as always-on (true for most of a raid).
- Rabbit Twins B (skills[1]): on Full Burst entry, squad Max Ammunition Capacity
  +5 ROUNDS for 10 sec (a flat round count, `max_ammo_rounds` - raid_simulator
  converts it against each recipient's own base magazine).
- Finale (skills[2], her burst): burst nuke 351.64% of final ATK, plus squad
  Damage-to-Interruption-Parts up (23.23% for 10s + 19.36% for 30s). The "Shotgun
  allies" / "ally from the same squad on the battlefield" scopes are approximated
  as squad. "Interruption Parts" (저지 부위) is the zone an interruption gimmick
  makes you hit - NOT a destructible part - so it goes to its own stat and,
  like Damage to Parts, never reaches body damage.

Not modeled:
- Rabbit Twins B's instant partial reload ("Reload 39.88% magazine(s)"): the
  engine reloads a magazine as one uninterruptible block, so a fractional
  mid-magazine top-up has nowhere to land.
- Finale's Hit Rate buffs - Hit Rate is not consumed by this engine.
"""
from app.skill_rules._helpers import buff_rule


SKILL_VALUE_MANIFESTS = {
    "noir": {
        "source": "lootandwaifus",
        "test_module": "test_skill_rules_burst3_eb1",
        "keys": {
            "lucky_charm": ("skills", 0),
            "rabbit_twins_b": ("skills", 1),
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
    rabbit_twins = values["rabbit_twins_b"]
    finale = values["finale"]
    caster_atk = values["caster_atk"]
    squad_atk = float(lucky["description_value_01"]) / 100 * caster_atk
    ammo_rounds = float(rabbit_twins["description_value_01"])
    ammo_duration = float(rabbit_twins["description_value_02"])
    parts_1 = float(finale["description_value_04"]) / 100
    parts_1_duration = float(finale["description_value_05"])
    parts_2 = float(finale["description_value_08"]) / 100
    parts_2_duration = float(finale["description_value_09"])

    return [
        buff_rule("battle_start", [("flat_atk", squad_atk, "squad", None)]),
        buff_rule("full_burst_enter", [
            ("max_ammo_rounds", ammo_rounds, "squad", ammo_duration),
        ]),
        buff_rule("own_burst_activate", [
            ("damage_to_interruption_parts_up", parts_1, "squad", parts_1_duration),
            ("damage_to_interruption_parts_up", parts_2, "squad", parts_2_duration),
        ]),
    ]
