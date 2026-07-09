"""SkillRule encoding of Helm's "Frontline Command" (skills[0]) and "Fire
Away" (skills[1]) from api.dotgg.gg slug "helm".

Fienn's Helm has her signature weapon completed, so callers must build these
rules from the "dollskills" array's values, not "skills" - the cherished-
weapon version changes more than numbers (e.g. Frontline Command gains an
entirely new full-charge-hit effect) even where a stat's own value carries
over unchanged (e.g. the crit rate on Frontline Command is the same in both).

"Aegis Cannon" (skills[2]/dollskills[2], her burst skill) is mostly a pure
damage instance - use aegis_cannon_burst_percent() for the "X% of final ATK"
figure raid_simulator needs; the damage-proportional heal-over-time isn't
modeled since it doesn't affect DPS output.

"Frontline Command" fires on `on_last_bullet_hit`, a trigger nothing emits
yet - it depends on the deferred attack-rate/ammo model. Same for the
full-charge-hit effects on both skills (heal/gauge-fill/bonus damage).
"""
from app.effects import Effect
from app.squad_engine import SkillRule


def build_frontline_command_rules(values: dict) -> list[SkillRule]:
    crit_rate_up = float(values["description_value_01"]) / 100
    duration = float(values["description_value_02"])

    def action(context, caster_slug, time, registry):
        registry.add(
            Effect("crit_rate", crit_rate_up, "squad", duration, caster_slug),
            applied_at=time,
        )

    return [SkillRule(trigger="on_last_bullet_hit", action=action)]


def build_fire_away_rules(values: dict) -> list[SkillRule]:
    damage_to_parts_up = float(values["description_value_01"]) / 100
    attack_damage_up = float(values["description_value_02"]) / 100
    attack_damage_duration = float(values["description_value_03"])

    def grant_damage_to_parts(context, caster_slug, time, registry):
        if context.has_status(caster_slug, "Fire Away Granted"):
            return
        context.set_status(caster_slug, "Fire Away Granted")
        registry.add(
            Effect("damage_to_parts_up", damage_to_parts_up, "squad", None, caster_slug),
            applied_at=time,
        )

    def grant_attack_damage_up(context, caster_slug, time, registry):
        registry.add(
            Effect("attack_damage_up", attack_damage_up, "squad", attack_damage_duration, caster_slug),
            applied_at=time,
        )

    return [
        SkillRule(trigger="battle_start", action=grant_damage_to_parts),
        SkillRule(trigger="full_burst_enter", action=grant_attack_damage_up),
    ]


def aegis_cannon_burst_percent(values: dict) -> float:
    return float(values["description_value_01"])
