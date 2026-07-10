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


def instant_nuke_pulse_rule(trigger, percent):
    """"Deals X% of final ATK as damage" tied to a trigger OTHER than the
    caster's own burst (e.g. Brid: Silent Track's Ignition Sequence, on
    full_burst_enter). raid_simulator.drain_instant_damage computes it using
    the caster's own ATK and live buffs, exactly like a burst nuke."""

    def action(context, caster_slug, time, registry):
        registry.add_pulse(Pulse("instant_damage_percent", percent, "self", caster_slug))

    return SkillRule(trigger=trigger, action=action)


def escalating_buff_rule(trigger, tiers):
    """Cumulative "Once/Twice/Three times, previous effects trigger repeatedly".

    tiers[k] is the list of (stat, value, scope, duration) UNLOCKED at the
    (k+1)-th activation; use an empty list for a tier with no DPS-relevant
    effect (e.g. a Hit Rate step). On the Nth activation every unlocked tier
    (1..N) is re-applied, so each tier's duration-limited buff refreshes and the
    bundle saturates once all tiers are unlocked. Relies on
    SquadContext.activation_count, so it must be fired via fire_trigger.
    """

    def action(context, caster_slug, time, registry):
        n = context.activation_count(caster_slug, trigger)
        for unlock_at, buffs in enumerate(tiers, start=1):
            if n >= unlock_at:
                for stat, value, scope, duration in buffs:
                    registry.add(Effect(stat, value, scope, duration, caster_slug), applied_at=time)

    return SkillRule(trigger=trigger, action=action)
