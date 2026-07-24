"""Sugar (slug "sugar"), a Burst-3 Iron shotgun Attacker who enlarges shotgun
allies' magazines on Full Burst and speeds up her own fire with her burst.

Modeled (DPS-relevant):
- Noire Sensor (skills[1], on Full Burst entry): self Critical Rate +13.02% for
  10 sec, and Max Ammunition Capacity +83.8% for 10 sec on every shotgun ally.
  The shotgun subset is EXACT, not a squad approximation - member_subset_buff_rule
  resolves the weapon filter live against SquadMember.weapon.
- Trouble Shooter (skills[2], her burst, cd 40): self Attack Speed +66% for
  15 sec. Attack Speed moves damage since Phase S - attack_rate scales the firing
  cadence from it, so a fixed-length fight fits more shots. Her burst deals no
  damage, so the registry's burst percent is None.

Not modeled / deferred:
- Black Typhoon (skills[0]) entirely: Critical Damage +16.39% and Reload Speed
  +12.12% for 10 sec both hang off "when cover is attacked", a trigger the engine
  has no concept of, behind a 20% roll on top of it. Fienn ruled it deferred
  (2026-07-24) rather than approximated as permanent, because cover-hit frequency
  swings with the boss, its attack pattern and her position. This makes the
  encoding a FLOOR for her.
- Hit Rate +33% from her burst: Hit Rate is not a damage concept in the engine
  and no consumer can exist without a much bigger model.
"""
from app.skill_rules._helpers import buff_rule, member_subset_buff_rule


SKILL_VALUE_MANIFESTS = {
    "sugar": {
        "source": "shiftypad",
        "test_module": "test_skill_rules_sugar",
        "keys": {
            "noire_sensor": ("skills", 1),
            "trouble_shooter": ("skills", 2),
        },
    },
}


def shotgun_allies(member, context):
    """Noire Sensor's "all allies with shotguns" - the caster included."""
    return member.weapon == "SG"


def build_sugar_rules(values):
    sensor = values["noire_sensor"]
    trouble = values["trouble_shooter"]
    crit_rate = float(sensor["description_value_01"]) / 100
    crit_duration = float(sensor["description_value_02"])
    max_ammo = float(sensor["description_value_03"]) / 100
    ammo_duration = float(sensor["description_value_04"])
    attack_speed = float(trouble["description_value_01"]) / 100
    speed_duration = float(trouble["description_value_02"])
    return [
        buff_rule("full_burst_enter", [
            ("crit_rate", crit_rate, "self", crit_duration),
        ]),
        member_subset_buff_rule("full_burst_enter", shotgun_allies, [
            ("max_ammo_percent", max_ammo, ammo_duration),
        ]),
        buff_rule("own_burst_activate", [
            ("attack_speed_percent", attack_speed, "self", speed_duration),
        ]),
    ]
