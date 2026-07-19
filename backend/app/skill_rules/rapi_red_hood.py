"""SkillRule encoding of Rapi: Red Hood's "Battlefield Assessment" (skills[0])
and "Attachable Projectiles" (skills[1], battle-start effects only) from
lootandwaifus.com slug "rapi-red-hood".

Whether she becomes a Burst-1 stand-in ("Combat Assist") depends on whether
another Burst 1 ally is already in the deck - re-using the same
no_other_burst_tier_allies condition Anis: Star's rules use, since combination
search needs this evaluated per-deck, not hardcoded to one roster.

Modeled from Attachable Projectiles (both permanent battle-start self effects):
- Projectile Explosion Damage ▲ 100.6% continuously - boosts her
  projectile_explosion-typed burst nuke (Power of Inheritance is a Projectile
  Explosion keyword skill, see registry's _BURST_DAMAGE_TYPES).
- "Applies Elemental Advantage damage to Electric Code enemies continuously" -
  she is Fire (advantaged vs Wind only), so this is a self
  other_elemental_bonus of ELEMENT_ADVANTAGE_BONUS gated on
  boss_is_element("Electric"): the element bucket becomes 1.0 + 0.1, exactly
  the multiplier natural advantage would give (damage_formula adds
  other_elemental_bonus onto element_multiplier).

Not modeled / deferred:
- Attachable Projectiles' 120-normal-attack launcher (projectiles attach, then
  explode on Full Burst entry - a projectile state machine no engine trigger
  expresses; confirmed not unlockable by gap #7/#9, 2026-07-15).
- Projectile Attachment Damage ▲ 150.72% - inert until the attachment damage
  instances above are modeled (nothing attachment-typed exists to boost).
- The Stage 1 branch damage of "Power of Inheritance" (skills[2]) - the Stage 3
  branch's nuke IS modeled via power_of_inheritance_stage3_burst_percent.
"""
from app.effects import Effect, Pulse
from app.elements import ELEMENT_ADVANTAGE_BONUS
from app.skill_rules._helpers import buff_rule
from app.squad_engine import (
    SkillRule,
    boss_is_element,
    has_status,
    no_other_burst_tier_allies,
    not_condition,
)

SKILL_VALUE_MANIFESTS = {
    "rapi-red-hood": {
        "source": "lootandwaifus",
        "test_module": "test_skill_rules_rapi_red_hood",
        "keys": {
            "battlefield_assessment": ("skills", 0),
            "attachable_projectiles": ("skills", 1),
            "power_of_inheritance": ("skills", 2),
        },
        "fixtures": {
            "battlefield_assessment": "VALUES",
        },
    },
}


def build_battlefield_assessment_rules(values: dict) -> list[SkillRule]:
    own_burst_tier = int(values["description_value_01"])
    cooldown_reduction_sec = float(values["description_value_04"])
    self_atk_up = float(values["description_value_07"]) / 100
    self_atk_duration = float(values["description_value_08"])
    damage_to_parts_up = float(values["description_value_09"]) / 100
    damage_to_parts_duration = float(values["description_value_10"])
    squad_attack_damage_up = float(values["description_value_05"]) / 100
    squad_attack_damage_duration = float(values["description_value_06"])

    no_burst1_ally = no_other_burst_tier_allies(own_burst_tier)

    def assess_formation(context, caster_slug, time, registry):
        if no_burst1_ally(context, caster_slug):
            context.set_status(caster_slug, "Combat Assist")
        else:
            context.clear_status(caster_slug, "Combat Assist")

    def combat_assist_branch(context, caster_slug, time, registry):
        registry.add_pulse(
            Pulse(
                stat="burst_cooldown_reduction_sec",
                value=cooldown_reduction_sec,
                scope="squad",
                source_slug=caster_slug,
            )
        )
        registry.add(
            Effect(
                "attack_damage_up",
                squad_attack_damage_up,
                "squad",
                squad_attack_damage_duration,
                caster_slug,
            ),
            applied_at=time,
        )

    def self_buff_branch(context, caster_slug, time, registry):
        registry.add(
            Effect("atk_percent", self_atk_up, "self", self_atk_duration, caster_slug),
            applied_at=time,
        )
        registry.add(
            Effect(
                "damage_to_parts_up", damage_to_parts_up, "self", damage_to_parts_duration, caster_slug
            ),
            applied_at=time,
        )

    in_combat_assist = has_status("Combat Assist")
    not_in_combat_assist = not_condition(in_combat_assist)

    return [
        SkillRule(trigger="battle_start", action=assess_formation),
        SkillRule(trigger="full_burst_end", action=assess_formation),
        SkillRule(trigger="full_burst_enter", condition=in_combat_assist, action=combat_assist_branch),
        SkillRule(trigger="full_burst_enter", condition=not_in_combat_assist, action=self_buff_branch),
    ]


def build_attachable_projectiles_rules(values: dict) -> list[SkillRule]:
    projectile_explosion_up = float(values["description_value_02"]) / 100
    return [
        buff_rule("battle_start", [
            ("projectile_explosion_damage_up", projectile_explosion_up, "self", None),
        ]),
        buff_rule("battle_start", [
            ("other_elemental_bonus", ELEMENT_ADVANTAGE_BONUS, "self", None),
        ], condition=boss_is_element("Electric")),
    ]


def power_of_inheritance_stage3_burst_percent(values: dict) -> float:
    """The Stage 3 branch's "Deals X% of final ATK as additional damage" -
    only correct when NOT in Combat Assist (i.e. a Burst 1 ally is present),
    which is the case in Fienn's actual deck. Stage 1's own damage isn't
    modeled since that branch doesn't apply here."""
    return float(values["description_value_08"])
