"""SkillRule encoding of Privaty's "EX Magazine" (skills[0]) and "AK Missile"
(skills[2], her burst skill) from api.dotgg.gg slug "privaty".

Fienn's Privaty has her signature weapon completed, so callers must build
these rules from the "dollskills" array's values, not "skills" - the
cherished-weapon version adds a whole 4th effect to EX Magazine (Attack
Damage up) that the base skill lacks entirely, and roughly triples AK
Missile's burst damage percent.

Unlike Crown's "X% of caster's ATK", EX Magazine's ATK bonus is a plain
"ATK UP X%" buff on the target's own ATK, so it maps directly to
atk_percent rather than needing a caster-stat snapshot.

Not modeled: "LD Assault" (skills[1]) is a pure per-shot damage instance
gated on "last bullet hits" - deferred to the raid_simulator's damage-
accumulation piece alongside the deferred attack-rate model. AK Missile's
own "Deals X% of final ATK as Burst Skill damage" and its Designated-Target
follow-up effects use ak_missile_burst_percent() instead of a SkillRule,
same pattern as Helm's Aegis Cannon.
"""
from app.effects import Effect
from app.squad_engine import SkillRule


def build_ex_magazine_rules(values: dict) -> list[SkillRule]:
    atk_up = float(values["description_value_01"]) / 100
    atk_duration = float(values["description_value_02"])
    reload_speed_up = float(values["description_value_03"]) / 100
    reload_duration = float(values["description_value_04"])
    max_ammo_reduction = float(values["description_value_05"]) / 100
    ammo_duration = float(values["description_value_06"])
    attack_damage_up = float(values["description_value_07"]) / 100
    attack_damage_duration = float(values["description_value_08"])

    def action(context, caster_slug, time, registry):
        registry.add(Effect("atk_percent", atk_up, "squad", atk_duration, caster_slug), applied_at=time)
        registry.add(
            Effect("reload_speed_percent", reload_speed_up, "squad", reload_duration, caster_slug),
            applied_at=time,
        )
        registry.add(
            Effect("max_ammo_percent", -max_ammo_reduction, "squad", ammo_duration, caster_slug),
            applied_at=time,
        )
        registry.add(
            Effect(
                "attack_damage_up", attack_damage_up, "squad", attack_damage_duration, caster_slug
            ),
            applied_at=time,
        )

    return [SkillRule(trigger="full_burst_enter", action=action)]


def build_ak_missile_rules(values: dict) -> list[SkillRule]:
    other_elemental_bonus = float(values["description_value_05"]) / 100
    duration = float(values["description_value_06"])

    def action(context, caster_slug, time, registry):
        registry.add(
            Effect("other_elemental_bonus", other_elemental_bonus, "self", duration, caster_slug),
            applied_at=time,
        )

    return [SkillRule(trigger="own_burst_activate", action=action)]


def ak_missile_burst_percent(values: dict) -> float:
    return float(values["description_value_01"])
