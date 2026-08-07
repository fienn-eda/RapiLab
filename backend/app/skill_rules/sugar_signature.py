"""Sugar's Favorite Item (애장품) build, slug "sugar-signature" - a SEPARATE
roster entry from base Sugar (slug "sugar"), per the dual-slot convention
(2026-07-12). The Favorite Item does not merely raise her numbers: it adds a
permanent Attack Damage bullet, an elemental-advantage grant, a self ATK buff on
both Full Burst and her burst, and an elemental buff for Water/Iron shotgun
allies that the base build has no trace of.

Weapon stats come from base Sugar's ShiftyPad file via the manifest's
`weapon_source`, since ShiftyPad exposes no dollskills and dotgg is dead.

Modeled (DPS-relevant):
- Black Typhoon (dollskills[0]): Attack Damage +19.98% while her cover is
  intact. The engine models no cover destruction, so cover is always intact -
  Fienn approved encoding it as a permanent battle-start self buff (2026-07-24).
- Black Typhoon (dollskills[0]): "Converts damage to Elemental Advantage damage
  against Fire Code enemies" at battle start. She is Iron, which holds no
  natural advantage over Fire, so this is element_advantage_grant gated on
  boss_is_element("Fire") - the same shape as Rapi: Red Hood's grant. It is
  deliberately NOT other_elemental_bonus, which only pays out to a unit that
  ALREADY has advantage and would be self-cancelling here.
- Noire Sensor (dollskills[1], on Full Burst entry): self Critical Rate +13.02%
  and ATK +25.01% for 10 sec; Max Ammunition Capacity +83.8% for 15 sec on all
  shotgun allies (10 sec in the base build); Elemental Advantage Attack Damage
  +40.02% for 15 sec on Water and Iron Code shotgun allies.
- Trouble Shooter (dollskills[2], her burst, cd 40): self Attack Speed +66%,
  Hit Rate +33% and ATK +20% for 15 sec; Elemental Advantage Attack Damage
  +60.01% for 15 sec on Water and Iron Code shotgun allies. Her burst deals no
  damage, so the registry's burst percent is None.

Both member subsets are EXACT, not squad approximations - member_subset_buff_rule
resolves the weapon and element filters live against SquadMember.

Not modeled / deferred:
- Black Typhoon's cover-attack buffs (Critical Damage +16.39%, Reload Speed
  +12.12%, 10 sec). This build drops the base's 20% roll, but "when cover is
  attacked" is still a trigger the engine has no concept of. Fienn ruled it
  deferred (2026-07-24) rather than approximated as permanent, so this encoding
  is a FLOOR.
- Black Typhoon's cover-HP restore (1.5% of final Max HP) - survivability, not
  damage.
"""
from app.skill_rules._helpers import buff_rule, member_subset_buff_rule
from app.skill_rules.sugar import shotgun_allies
from app.squad_engine import boss_is_element


SKILL_VALUE_MANIFESTS = {
    "sugar-signature": {
        "source": "lootandwaifus",
        "weapon_source": "shiftypad",
        "data_slug": "sugar",
        "test_module": "test_skill_rules_sugar_signature",
        "keys": {
            "black_typhoon": ("dollskills", 0),
            "noire_sensor": ("dollskills", 1),
            "trouble_shooter": ("dollskills", 2),
        },
    },
}

# "all Water Code and Iron Code allies with shotguns" - Noire Sensor's and
# Trouble Shooter's elemental bullets share one target set.
_ELEMENTAL_BUFF_ELEMENTS = ("Water", "Iron")


def water_or_iron_shotgun_allies(member, context):
    return member.weapon == "SG" and member.element in _ELEMENTAL_BUFF_ELEMENTS


def build_sugar_signature_rules(values):
    typhoon = values["black_typhoon"]
    sensor = values["noire_sensor"]
    trouble = values["trouble_shooter"]
    intact_cover_damage = float(typhoon["description_value_06"]) / 100
    crit_rate = float(sensor["description_value_01"]) / 100
    crit_duration = float(sensor["description_value_02"])
    fb_atk = float(sensor["description_value_03"]) / 100
    fb_atk_duration = float(sensor["description_value_04"])
    max_ammo = float(sensor["description_value_05"]) / 100
    ammo_duration = float(sensor["description_value_06"])
    fb_elemental = float(sensor["description_value_07"]) / 100
    fb_elemental_duration = float(sensor["description_value_08"])
    attack_speed = float(trouble["description_value_01"]) / 100
    speed_duration = float(trouble["description_value_02"])
    hit_rate = float(trouble["description_value_03"]) / 100
    hit_rate_duration = float(trouble["description_value_04"])
    burst_atk = float(trouble["description_value_05"]) / 100
    burst_atk_duration = float(trouble["description_value_06"])
    burst_elemental = float(trouble["description_value_07"]) / 100
    burst_elemental_duration = float(trouble["description_value_08"])
    return [
        buff_rule("battle_start", [
            ("attack_damage_up", intact_cover_damage, "self", None),
        ]),
        buff_rule("battle_start", [
            ("element_advantage_grant", 1.0, "self", None),
        ], condition=boss_is_element("Fire")),
        buff_rule("full_burst_enter", [
            ("crit_rate", crit_rate, "self", crit_duration),
            ("atk_percent", fb_atk, "self", fb_atk_duration),
        ]),
        member_subset_buff_rule("full_burst_enter", shotgun_allies, [
            ("max_ammo_percent", max_ammo, ammo_duration),
        ]),
        member_subset_buff_rule("full_burst_enter", water_or_iron_shotgun_allies, [
            ("other_elemental_bonus", fb_elemental, fb_elemental_duration),
        ]),
        buff_rule("own_burst_activate", [
            ("attack_speed_percent", attack_speed, "self", speed_duration),
            ("hit_rate", hit_rate, "self", hit_rate_duration),
            ("atk_percent", burst_atk, "self", burst_atk_duration),
        ]),
        member_subset_buff_rule("own_burst_activate", water_or_iron_shotgun_allies, [
            ("other_elemental_bonus", burst_elemental, burst_elemental_duration),
        ]),
    ]
