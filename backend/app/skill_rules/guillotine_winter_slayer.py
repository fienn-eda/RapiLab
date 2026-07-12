"""Guillotine: Winter Slayer (slug "guillotine-winter-slayer"), a Burst-3 Water
Assault Rifle attacker. Base skills. PARTIAL - her resource buffs are modeled;
her Hero-Level-scaled burst DoT is deferred (see below).

First consumer of the named-resource primitive's PERMANENT-accumulate +
count-scaled + derived-level modes (see effects.ResourceSpec).

Modeled (DPS-relevant): one "exp" resource, capped at 100.
- Hero's Gift (skills[1]) fills it: +1 EXP every 3 Core hits (core-hittable boss)
  or every 6 normals otherwise - a core-conditional fill. Each EXP stack grants
  self ATK +1.81% (permanent, linear). While Hero Level >= 2, self Elemental
  Advantage Attack Damage +7.46%.
- Hero's Fate (skills[0]) derives Hero Level = 1 + EXP//10 (capped 11) and grants
  all Water Code allies, scaled by Hero Level: Elemental Advantage Attack Damage
  +1.16% * level and ATK +0.91% of the caster's ATK * level (both continuous).
- Extermination (skills[2], her burst): all Water Code allies Attack Damage
  +10.14% and Elemental Advantage Attack Damage +18.75% for 10 sec.

Not modeled / deferred:
- Extermination's headline burst damage - "20.87% of final ATK * Hero Level per
  sec for 10 sec on the highest-Max-HP enemy" - is a DoT that scales with Hero
  Level AT BURST TIME. A count-scaled nuke needs the resource count queried
  during damage computation, which the fill schedule only populates in the
  resolution pass (after the burst fires); deferred until the count-scaled-nuke
  path exists. So burst_percent is None (her burst here applies only the two
  Water-ally buffs).
- Hero Level Up rewards (reload / HP recovery) - not damage.
- "Elemental Advantage Attack Damage" maps to other_elemental_bonus, which the
  engine adds on top of the elemental multiplier unconditionally - correct only
  when the wielder has elemental advantage (the intended Water-vs-weak-boss raid
  setup); a neutral/disadvantaged boss would overcount it (existing convention,
  see anis_sparkling_summer).
"""
from app.effects import ResourceBuff, ResourceSpec
from app.skill_rules._helpers import buff_rule, leveled_resource_buff, linear_resource_buff


def _hero_level(exp):
    """Hero Level: 1 at 0 EXP, +1 every 10 EXP, capped at 11."""
    return min(11, 1 + int(exp) // 10)


def build_guillotine_resources(values):
    fate = values["heros_fate"]
    gift = values["heros_gift"]
    caster_atk = values["caster_atk"]

    normal_hits = int(gift["description_value_01"])       # +1 EXP per 6 non-core normals
    exp_atk = float(gift["description_value_02"]) / 100    # ATK per EXP stack
    exp_cap = int(gift["description_value_03"])            # EXP cap (100)
    core_hits = int(gift["description_value_04"])          # +1 EXP per 3 core hits
    level2_min = int(gift["description_value_07"])         # Hero Level >= 2
    level2_elem = float(gift["description_value_08"]) / 100  # self elem adv at level >= 2

    water_elem_per_level = float(fate["description_value_05"]) / 100  # Water allies, per level
    water_atk_per_level = float(fate["description_value_06"]) / 100   # % of caster ATK, per level

    return [
        ResourceSpec(
            name="exp",
            fill=("per_shot_every_core", core_hits, normal_hits),
            cap=exp_cap,
            buffs=[
                linear_resource_buff("atk_percent", exp_atk, "self"),
                ResourceBuff(
                    stat="other_elemental_bonus", scope="self",
                    value_fn=lambda c: level2_elem if _hero_level(c) >= level2_min else 0.0,
                ),
                leveled_resource_buff(
                    "other_elemental_bonus", water_elem_per_level, _hero_level, "element:Water"
                ),
                leveled_resource_buff(
                    "flat_atk", water_atk_per_level * caster_atk, _hero_level, "element:Water"
                ),
            ],
        )
    ]


def build_guillotine_rules(values):
    exterm = values["extermination"]
    attack_damage = float(exterm["description_value_01"]) / 100
    attack_duration = float(exterm["description_value_02"])
    elem_advantage = float(exterm["description_value_03"]) / 100
    elem_duration = float(exterm["description_value_04"])
    return [
        buff_rule("own_burst_activate", [
            ("attack_damage_up", attack_damage, "element:Water", attack_duration),
            ("other_elemental_bonus", elem_advantage, "element:Water", elem_duration),
        ])
    ]
