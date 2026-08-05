"""Arcana (slug "arcana"), a Burst-2 Electric RL supporter. Base skills (no
signature weapon).

"Wheel of Fortune" is a status her own burst (Shackles of Destiny) grants to
all Electric Code allies, including herself (she is Electric). Her other two
skills gate a bullet on "if self is in Wheel of Fortune status" - since only
her own burst grants it, the encoding reads that as "did Arcana's own burst
fire this cycle" and uses `own_burst_fired_this_cycle()` (reads
SquadContext.burst_used_this_cycle, which is not yet cleared when
full_burst_end rules run).

KNOWN DEFECT (2026-08-05): that equivalence drops the status's CLOCK, and these
three bullets fire on full_burst_end, ten seconds after the grant. Wheel of
Fortune lasts 10 sec and starts when Arcana casts at Burst Stage 2 - strictly
BEFORE the Burst 3 cast that opens Full Burst - so with the standard 10 sec
window it has always lapsed by the time Full Burst ends. The registry agrees:
in a scored deck the Wheel expires at t=12.500 while full_burst_end fires at
t=12.600. Read honestly the gate is ALWAYS false, and the only thing that
turns it true is a shortened Full Burst - which today means Isabel alone
("Full Burst Time -5 sec", not modelled either, see isabel.py). So Arcana's
three conditional bullets currently fire in every deck she bursts in, worth
+25-29% of deck total on a real roster, when they should fire only alongside
Isabel. Fixing this needs a per-cycle Full Burst duration in burst_cycle.py
plus a time-aware gate; the two changes are useless apart and are an
engine-extension decision, not a skill-rule edit. Contrast grave.py, which
gates the same 10-sec-status/10-sec-window coincidence on the status ENDING
(where full_burst_end is the right instant) rather than on it still running.

Modeled (DPS-relevant):
- Shackles of Destiny (skills[2], her burst): Electric-Code squad Attack
  Damage (Wheel of Fortune, `element:Electric` scope); burst nuke 300% of
  final ATK (`arcana_burst_percent`); enemy Damage Taken debuff (Judgement,
  squad scope since it's on the boss).
- Awakened Destiny (skills[0]): on Full Burst end, squad ATK % of caster's ATK
  - this bullet is unconditioned (no Wheel of Fortune requirement).
- Cycle of Destiny (skills[1]): on Full Burst end, an unconditioned squad
  Attack Damage buff, plus - only if Arcana's own burst fired this cycle -
  squad burst-cooldown reduction + squad ATK % of caster's ATK (Death).
- "The Magician" (skills[0]) / "Strength" (skills[1]) first bullets: on Full
  Burst end, all Burst 3 Electric Code allies who previously cast their Burst
  Skill - if Arcana is in Wheel of Fortune status - get Attack damage +180%
  (Magician) and ATK +180% of caster's ATK (Strength), 15 sec each
  (member_subset_buff_rule, gap #3; burst_used_this_cycle is still populated
  when full_burst_end rules run).

Not modeled: The Magician's "Cooldown of Skill 2 -75%" - ally Skill 1/2
cooldowns aren't simulated (only periodic_rules units have one, and none is
Electric Burst-3 today).
"""
from app.effects import Effect, Pulse
from app.skill_rules._helpers import member_subset_buff_rule
from app.squad_engine import SkillRule, own_burst_fired_this_cycle

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

    return [
        SkillRule(trigger="own_burst_activate", action=apply_shackles_buffs),
        SkillRule(trigger="full_burst_end", action=apply_awakened_squad_atk),
        SkillRule(trigger="full_burst_end", action=apply_cycle_death, condition=own_burst_fired_this_cycle()),
        SkillRule(trigger="full_burst_end", action=apply_cycle_attack_damage),
        # The Magician / Strength: bursted Electric Burst-3 subset (gap #3).
        member_subset_buff_rule(
            "full_burst_end", bursted_electric_b3,
            [("attack_damage_up", magician_attack_damage, magician_duration)],
            condition=own_burst_fired_this_cycle(),
        ),
        member_subset_buff_rule(
            "full_burst_end", bursted_electric_b3,
            [("flat_atk", strength_atk, strength_duration)],
            condition=own_burst_fired_this_cycle(),
        ),
    ]
