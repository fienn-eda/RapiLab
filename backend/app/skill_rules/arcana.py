"""Arcana (slug "arcana"), a Burst-2 Electric RL supporter. Base skills (no
signature weapon).

"Wheel of Fortune" is a status her own burst (Shackles of Destiny) grants to
all Electric Code allies, including herself (she is Electric). Her other two
skills gate a bullet on "if self is in Wheel of Fortune status" - since only
her own burst grants it, this is equivalent to "did Arcana's own burst fire
this cycle", modeled with `own_burst_fired_this_cycle()` (reads
SquadContext.burst_used_this_cycle, which is not yet cleared when
full_burst_end rules run).

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

Not modeled: both skills[0] and skills[1]'s first bullets ("The Magician" /
"Strength") target "Burst 3 Electric Code allies who previously cast their
Burst Skill" - a per-member subset (tier + element + already-burst-this-cycle)
the engine can't target (Effect scope is only self/squad/element:X, not a
dynamic per-member list). These are sizeable buffs (180%/90% of caster's ATK)
for a narrow, deck-specific audience - flag to Fienn if a deck leans into
all-Electric Burst-3 stacking, since it would materially undercount such a deck.
"""
from app.effects import Effect, Pulse
from app.squad_engine import SkillRule, own_burst_fired_this_cycle


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

    return [
        SkillRule(trigger="own_burst_activate", action=apply_shackles_buffs),
        SkillRule(trigger="full_burst_end", action=apply_awakened_squad_atk),
        SkillRule(trigger="full_burst_end", action=apply_cycle_death, condition=own_burst_fired_this_cycle()),
        SkillRule(trigger="full_burst_end", action=apply_cycle_attack_damage),
    ]
