"""SkillRule encoding of Anis: Star's "Starfall" skill (skills[0] in the
api.dotgg.gg character payload for slug "anis-star").

Not modeled: the "Everyone's Star: Re-enters Burst and changes to Stage
{value_01}" branch effect and the full-charge-hit bonus damage instance -
both need pieces of the simulator (multi-stage burst re-entry, normal-attack
damage accumulation) that don't exist yet.
"""
from app.effects import Effect, Pulse
from app.squad_engine import SkillRule, no_other_burst_tier_allies, not_condition


def build_starfall_rules(values: dict) -> list[SkillRule]:
    own_burst_tier = int(values["description_value_01"])
    my_own_star_atk = float(values["description_value_02"]) / 100
    cooldown_reduction_sec = float(values["description_value_03"])
    gauge_fill_speed = float(values["description_value_05"]) / 100

    def grant_gauge_fill_speed(context, caster_slug, time, registry):
        if context.has_status(caster_slug, "Starfall Gauge Buff Granted"):
            return
        context.set_status(caster_slug, "Starfall Gauge Buff Granted")
        registry.add(
            Effect(
                stat="burst_gauge_fill_speed_percent",
                value=gauge_fill_speed,
                scope="squad",
                duration=None,
                source_slug=caster_slug,
            ),
            applied_at=time,
        )

    def alone_branch(context, caster_slug, time, registry):
        context.clear_status(caster_slug, "Everyone's Star")
        if not context.has_status(caster_slug, "My Own Star"):
            context.set_status(caster_slug, "My Own Star")
            registry.add(
                Effect(
                    stat="atk_percent",
                    value=my_own_star_atk,
                    scope="self",
                    duration=None,
                    source_slug=caster_slug,
                ),
                applied_at=time,
            )
        registry.add_pulse(
            Pulse(
                stat="burst_cooldown_reduction_sec",
                value=cooldown_reduction_sec,
                scope="squad",
                source_slug=caster_slug,
            )
        )

    def with_ally_branch(context, caster_slug, time, registry):
        context.clear_status(caster_slug, "My Own Star")
        context.set_status(caster_slug, "Everyone's Star")

    alone = no_other_burst_tier_allies(own_burst_tier)
    with_ally = not_condition(alone)

    return [
        SkillRule(trigger="battle_start", action=grant_gauge_fill_speed),
        SkillRule(trigger="battle_start", condition=alone, action=alone_branch),
        SkillRule(trigger="battle_start", condition=with_ally, action=with_ally_branch),
        SkillRule(trigger="full_burst_end", condition=alone, action=alone_branch),
        SkillRule(trigger="full_burst_end", condition=with_ally, action=with_ally_branch),
    ]
