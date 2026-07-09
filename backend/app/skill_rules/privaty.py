"""SkillRule encoding of Privaty's "EX Magazine" (skills[0]) from
api.dotgg.gg slug "privaty".

Unlike Crown's "X% of caster's ATK", EX Magazine's ATK bonus is a plain
"ATK UP X%" buff on the target's own ATK, so it maps directly to
atk_percent rather than needing a caster-stat snapshot.

Not modeled: "LD Assault" and "AK Missile" (skills[1]/[2], her burst skill)
are pure damage instances ("Deals X% of final ATK as damage") - deferred to
the raid_simulator's damage-accumulation piece, same as the other
Attackers' burst nukes.
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

    return [SkillRule(trigger="full_burst_enter", action=action)]
