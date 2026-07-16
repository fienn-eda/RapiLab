"""SkillRule encoding of Anis: Sparkling Summer (slug "anis-sparkling-summer",
lootandwaifus.com). Electric, Burst 3, Shotgun, Supporter.

Modeled (DPS-relevant):
- Sparkling Boost (Skill 1, on entering Full Burst): to all Electric Code
  allies, flat ATK = 55.31% of the caster's own base ATK and Reload Speed
  +49.28%, both for 10 sec. The caster-scaled ATK buff is her core support
  value. Scope is element:Electric, which includes Anis herself (also Electric).
- Sparkling Wave (Burst, self): Max Ammunition Capacity +73.92% and Reload
  Speed +27.72% for 10 sec, self only - boosts her own shotgun uptime. Also
  Elemental Advantage Attack Damage +42.24% for 10 sec: since Anis is Electric,
  this only counts against a Water boss (Electric > Water), so it's gated on
  boss_is_element("Water") and lands in the Element Bonus group
  (other_elemental_bonus), matching how the formula treats elemental advantage.

- Sparkling Missile (Skill 2): "when firing the last bullet" deals 382.42% of
  final ATK to the 2 highest-ATK enemies, plus self Damage-to-Interruption-
  Parts +6.91% for 10 sec. Modeled via the per-shot trigger's "last_bullet"
  mode (`per_shot_rules`, gap #1's residual variant) - see
  `build_sparkling_missile_per_shot_rules`. The "2 highest-ATK enemies" is a
  single boss in solo raid, so the nuke lands once per last bullet. The parts
  buff is a REFRESHING self buff (SG's small magazine empties faster than the
  10s window, so repeated last bullets refresh rather than stack). A chunk of
  her personal damage, though as a supporter that's secondary to Sparkling Boost.

Not modeled / deferred:
- (none - all DPS-relevant effects modeled.)
"""
from app.skill_rules._helpers import buff_rule, instant_nuke_pulse_rule, refreshing_buff_rule
from app.squad_engine import SkillRule, boss_is_element

WATER = "Water"  # Anis is Electric; her Elemental Advantage only counts vs Water


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
    self_elem_adv = float(wave["description_value_05"]) / 100
    self_elem_adv_duration = float(wave["description_value_06"])

    return [
        buff_rule("full_burst_enter", [
            ("flat_atk", electric_atk, "element:Electric", electric_atk_duration),
            ("reload_speed_percent", electric_reload, "element:Electric", electric_reload_duration),
        ]),
        buff_rule("own_burst_activate", [
            ("max_ammo_percent", self_max_ammo, "self", self_max_ammo_duration),
            ("reload_speed_percent", self_reload, "self", self_reload_duration),
        ]),
        buff_rule(
            "own_burst_activate",
            [("other_elemental_bonus", self_elem_adv, "self", self_elem_adv_duration)],
            condition=boss_is_element(WATER),
        ),
    ]


def build_sparkling_missile_per_shot_rules(values: dict) -> list:
    """Per-shot rules (see raid_simulator's `per_shot_rules`): on firing the
    last bullet of a magazine, deal 382.42% of final ATK and refresh a self
    Damage-to-Interruption-Parts buff for 10 sec."""
    nuke_percent = float(values["description_value_01"])
    parts_up = float(values["description_value_02"]) / 100
    parts_duration = float(values["description_value_03"])
    return [(None, "last_bullet", [
        instant_nuke_pulse_rule("per_shot", nuke_percent),
        refreshing_buff_rule("per_shot", [("damage_to_parts_up", parts_up, "self", parts_duration)]),
    ])]
