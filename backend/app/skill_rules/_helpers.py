"""Small builders shared by the many Burst-1 support skill encodings.

Most supporters just grant a bundle of timed buffs on a trigger, or emit a
burst-cooldown-reduction pulse. These two helpers cover that so each Nikke
module only has to declare its stats/values, not re-implement the action.
"""
from app.effects import Effect, Pulse
from app.squad_engine import SkillRule


def buff_rule(trigger, buffs):
    """buffs: list of (stat, value, scope, duration). duration None = permanent."""

    def action(context, caster_slug, time, registry):
        for stat, value, scope, duration in buffs:
            registry.add(Effect(stat, value, scope, duration, caster_slug), applied_at=time)

    return SkillRule(trigger=trigger, action=action)


def cdr_pulse_rule(trigger, seconds, scope="squad"):
    def action(context, caster_slug, time, registry):
        registry.add_pulse(Pulse("burst_cooldown_reduction_sec", seconds, scope, caster_slug))

    return SkillRule(trigger=trigger, action=action)
