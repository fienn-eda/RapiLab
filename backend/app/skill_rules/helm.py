"""SkillRule encoding of Helm's "Frontline Command" (skills[0]) and "Fire
Away" (skills[1]) from api.dotgg.gg slug "helm".

Not modeled: "Aegis Cannon" (skills[2], her burst skill) - it's a pure damage
instance ("Deals X% of final ATK as Burst Skill damage" to the highest-ATK
enemy) plus a damage-proportional heal-over-time, neither of which this
buff/status-oriented engine handles yet; damage instances need the
raid_simulator's damage-accumulation piece, and the heal is irrelevant to
DPS output.

"Frontline Command" fires on `on_last_bullet_hit`, a trigger nothing emits
yet - it depends on the deferred attack-rate/ammo model.
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
