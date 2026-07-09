"""SkillRule encoding of Crown's "One for All" (skills[0]) and "Last Kingdom"
(skills[2], her burst skill) from api.dotgg.gg slug "crown".

"X% of caster's ATK/DEF" bonuses use Crown's base ATK/DEF from her character
info tab - per Fienn, that excludes overload/other skill effects and only
reflects gear+breakthrough+cube - so callers pass those as plain numbers
resolved once, not derived from the live EffectRegistry.

Not modeled: "Royal Attire" (skills[1]) - gated on a normal-attack counter,
which needs an attack-rate model that doesn't exist yet.
"""
from app.effects import Effect
from app.squad_engine import SkillRule


def build_one_for_all_rules(values: dict, caster_atk: float, caster_def: float) -> list[SkillRule]:
    atk_bonus = caster_atk * float(values["description_value_01"]) / 100
    atk_duration = float(values["description_value_02"])
    reload_burst_users = float(values["description_value_03"]) / 100
    reload_duration_burst_users = float(values["description_value_04"])
    def_bonus = caster_def * float(values["description_value_05"]) / 100
    def_duration = float(values["description_value_06"])
    reload_non_burst_users = float(values["description_value_07"]) / 100
    reload_duration_non_burst_users = float(values["description_value_08"])

    def action(context, caster_slug, time, registry):
        for member in context.members:
            if member.slug in context.burst_used_this_cycle:
                registry.add(
                    Effect("flat_atk", atk_bonus, "self", atk_duration, member.slug),
                    applied_at=time,
                )
                registry.add(
                    Effect(
                        "reload_speed_percent",
                        reload_burst_users,
                        "self",
                        reload_duration_burst_users,
                        member.slug,
                    ),
                    applied_at=time,
                )
            else:
                registry.add(
                    Effect("flat_def", def_bonus, "self", def_duration, member.slug),
                    applied_at=time,
                )
                registry.add(
                    Effect(
                        "reload_speed_percent",
                        reload_non_burst_users,
                        "self",
                        reload_duration_non_burst_users,
                        member.slug,
                    ),
                    applied_at=time,
                )

    return [SkillRule(trigger="full_burst_enter", action=action)]


def build_last_kingdom_rules(values: dict, caster_max_hp: float) -> list[SkillRule]:
    attack_damage_up = float(values["description_value_01"]) / 100
    attack_damage_duration = float(values["description_value_02"])
    shield_amount = caster_max_hp * float(values["description_value_03"]) / 100
    shield_duration = float(values["description_value_04"])

    def action(context, caster_slug, time, registry):
        registry.add(
            Effect("attack_damage_up", attack_damage_up, "squad", attack_damage_duration, caster_slug),
            applied_at=time,
        )
        # shield_amount has no consumer yet - it's survivability, not damage output.
        registry.add(
            Effect("shield_amount", shield_amount, "squad", shield_duration, caster_slug),
            applied_at=time,
        )

    return [SkillRule(trigger="own_burst_activate", action=action)]
