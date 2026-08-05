"""Arcana (slug "arcana"), a Burst-2 Electric RL supporter. Base skills (no
signature weapon).

"Wheel of Fortune" is a status her own burst (Shackles of Destiny) grants to
all Electric Code allies, including herself (she is Electric). Her other two
skills gate three bullets on "if self is in Wheel of Fortune status" at Full
Burst END - and the status runs 10 sec from her Burst Stage 2 cast, which is
strictly before the Burst 3 cast that opens the window. So with a standard 10
sec Full Burst it has always lapsed by the time those bullets check, and the
only thing that opens the gate is a shortened window: today that means Isabel
alone ("Full Burst Time -5 sec"). Modeled with `own_burst_status_active`, which
reads the grant off her own burst time and compares it against the trigger's
time - `own_burst_fired_this_cycle()` carries no clock and cannot tell the two
cases apart.

Modeled (DPS-relevant):
- Shackles of Destiny (skills[2], her burst): Electric-Code squad Attack
  Damage (Wheel of Fortune, `element:Electric` scope); burst nuke 300% of
  final ATK (`arcana_burst_percent`); enemy Damage Taken debuff (Judgement,
  squad scope since it's on the boss).
- Awakened Destiny (skills[0]): on Full Burst end, squad ATK % of caster's ATK
  - this bullet is unconditioned (no Wheel of Fortune requirement).
- Cycle of Destiny (skills[1]): on Full Burst end, an unconditioned squad
  Attack Damage buff, plus - only while Arcana is still in Wheel of Fortune
  status - squad burst-cooldown reduction + squad ATK % of caster's ATK
  (Death).
- "The Magician" (skills[0]) / "Strength" (skills[1]) first bullets: on Full
  Burst end, all Burst 3 Electric Code allies who previously cast their Burst
  Skill - if Arcana is still in Wheel of Fortune status - get Attack damage
  +180% and Skill 2 cooldown -75% (Magician, 15 sec each) and ATK +180% of
  caster's ATK (Strength, 15 sec). The Skill 2 cut has exactly one consumer:
  Isabel's Pointed Feather (Skill 2, cooldown 15 sec). The other Electric
  Burst-3 units with cooldown-driven damage carry no skill cooldown at all -
  Jill Valentine's Acid Ammo and Ada Wong's Flash Grenade tick on an interval
  inside their own window, and Ein's Feather Shot is a summon cadence.
  (member_subset_buff_rule, gap #3; burst_used_this_cycle is still populated
  when full_burst_end rules run).

Not modeled: nothing. All six bullets are encoded.
"""
from app.effects import Effect, Pulse
from app.skill_rules._helpers import member_subset_buff_rule
from app.squad_engine import SkillRule, own_burst_status_active

SKILL_VALUE_MANIFESTS = {
    "arcana": {
        "source": "dotgg",
        "test_module": "test_skill_rules_arcana",
        "keys": {
            "awakened_destiny": ("skills", 0),
            "cycle_of_destiny": ("skills", 1),
            "shackles_of_destiny": ("skills", 2),
        },
    },
}


def arcana_burst_percent(values):
    return float(values["shackles_of_destiny"]["description_value_03"])


def build_arcana_rules(values):
    awakened = values["awakened_destiny"]
    cycle = values["cycle_of_destiny"]
    shackles = values["shackles_of_destiny"]
    caster_atk = values["caster_atk"]

    wheel_attack_damage = float(shackles["description_value_01"]) / 100
    wheel_duration = float(shackles["description_value_02"])
    judgement_damage_taken = float(shackles["description_value_04"]) / 100
    judgement_duration = float(shackles["description_value_05"])

    awakened_atk = float(awakened["description_value_06"]) / 100 * caster_atk
    awakened_atk_duration = float(awakened["description_value_07"])

    magician_skill2_cdr = float(awakened["description_value_02"]) / 100
    magician_skill2_cdr_duration = float(awakened["description_value_03"])
    magician_attack_damage = float(awakened["description_value_04"]) / 100
    magician_duration = float(awakened["description_value_05"])
    strength_atk = float(cycle["description_value_02"]) / 100 * caster_atk
    strength_duration = float(cycle["description_value_03"])

    cycle_cdr_sec = float(cycle["description_value_04"])
    cycle_death_atk = float(cycle["description_value_05"]) / 100 * caster_atk
    cycle_death_duration = float(cycle["description_value_06"])
    cycle_attack_damage = float(cycle["description_value_07"]) / 100
    cycle_attack_damage_duration = float(cycle["description_value_08"])

    def apply_shackles_buffs(context, caster_slug, time, registry):
        registry.add(
            Effect("attack_damage_up", wheel_attack_damage, "element:Electric", wheel_duration, caster_slug),
            applied_at=time,
        )
        registry.add(
            Effect("damage_taken_up", judgement_damage_taken, "squad", judgement_duration, caster_slug),
            applied_at=time,
        )

    def apply_awakened_squad_atk(context, caster_slug, time, registry):
        registry.add(
            Effect("flat_atk", awakened_atk, "squad", awakened_atk_duration, caster_slug),
            applied_at=time,
        )

    def apply_cycle_death(context, caster_slug, time, registry):
        registry.add_pulse(Pulse("burst_cooldown_reduction_sec", cycle_cdr_sec, "squad", caster_slug))
        registry.add(
            Effect("flat_atk", cycle_death_atk, "squad", cycle_death_duration, caster_slug),
            applied_at=time,
        )

    def apply_cycle_attack_damage(context, caster_slug, time, registry):
        registry.add(
            Effect("attack_damage_up", cycle_attack_damage, "squad", cycle_attack_damage_duration, caster_slug),
            applied_at=time,
        )

    def bursted_electric_b3(member, context):
        return (
            member.burst_tier == 3
            and member.element == "Electric"
            and member.slug in context.burst_used_this_cycle
        )

    wheel_active = own_burst_status_active(wheel_duration)

    return [
        SkillRule(trigger="own_burst_activate", action=apply_shackles_buffs),
        SkillRule(trigger="full_burst_end", action=apply_awakened_squad_atk),
        SkillRule(trigger="full_burst_end", action=apply_cycle_death,
                  time_condition=wheel_active),
        SkillRule(trigger="full_burst_end", action=apply_cycle_attack_damage),
        # The Magician / Strength: bursted Electric Burst-3 subset (gap #3).
        member_subset_buff_rule(
            "full_burst_end", bursted_electric_b3,
            [("attack_damage_up", magician_attack_damage, magician_duration),
             ("skill_cooldown_reduction_percent", magician_skill2_cdr,
              magician_skill2_cdr_duration)],
            time_condition=wheel_active,
        ),
        member_subset_buff_rule(
            "full_burst_end", bursted_electric_b3,
            [("flat_atk", strength_atk, strength_duration)],
            time_condition=wheel_active,
        ),
    ]
