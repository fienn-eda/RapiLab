"""SkillRule encoding of Anis: Sparkling Summer (slug "anis-sparkling-summer",
lootandwaifus.com). Electric, Burst 3, Shotgun, Supporter.

Modeled (DPS-relevant):
- Sparkling Boost (Skill 1, on entering Full Burst): to all Electric Code
  allies, flat ATK = 55.31% of the caster's own base ATK and Reload Speed
  +49.28%, both for 10 sec. The caster-scaled ATK buff is her core support
  value. Scope is element:Electric, which includes Anis herself (also Electric).
- Sparkling Wave (Burst, self): Max Ammunition Capacity +73.92% and Reload
  Speed +27.72% for 10 sec, self only - boosts her own shotgun uptime.

Not modeled / deferred:
- Sparkling Missile (Skill 2): "when firing the last bullet" deals 382.42% of
  final ATK to the 2 highest-ATK enemies, plus self Damage-to-Interruption-
  Parts +6.91% for 10 sec. Both hang off a "fire the last bullet" event, which
  is an ammo-depletion / normal-attack-count trigger - none of the four burst
  triggers - so it can't fire. Deferred (this is a chunk of her personal
  damage, though as a supporter that's secondary to Sparkling Boost).
- Sparkling Wave's "Elemental Advantage Attack Damage +42.24% (self, 10 sec)":
  which damage bucket this maps to is ambiguous (other_elemental_bonus vs
  attack_damage_up), and it only boosts Anis's own minor shotgun damage. Left
  deferred rather than guess the wrong bucket.
"""
from app.skill_rules._helpers import buff_rule
from app.squad_engine import SkillRule


def build_anis_sparkling_summer_rules(values: dict) -> list[SkillRule]:
    boost = values["sparkling_boost"]
    caster_atk = values["caster_atk"]
    electric_atk = float(boost["description_value_01"]) / 100 * caster_atk
    electric_atk_duration = float(boost["description_value_02"])
    electric_reload = float(boost["description_value_03"]) / 100
    electric_reload_duration = float(boost["description_value_04"])

    wave = values["sparkling_wave"]
    self_max_ammo = float(wave["description_value_01"]) / 100
    self_max_ammo_duration = float(wave["description_value_02"])
    self_reload = float(wave["description_value_03"]) / 100
    self_reload_duration = float(wave["description_value_04"])

    return [
        buff_rule("full_burst_enter", [
            ("flat_atk", electric_atk, "element:Electric", electric_atk_duration),
            ("reload_speed_percent", electric_reload, "element:Electric", electric_reload_duration),
        ]),
        buff_rule("own_burst_activate", [
            ("max_ammo_percent", self_max_ammo, "self", self_max_ammo_duration),
            ("reload_speed_percent", self_reload, "self", self_reload_duration),
        ]),
    ]
