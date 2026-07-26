"""Volume (slug "volume"), a Burst-1 SMG supporter. Base skills (no signature).

Modeled (DPS-relevant):
- Drop the Beat (skills[1]): on Full Burst enter, squad burst-cooldown
  reduction; on her own burst, squad Crit Damage up.
- Turn up the volume! (skills[2], her burst): squad Crit Rate up.

Both halves of Drop the Beat ESCALATE: "Effects vary according to the number of
[uses / times entered]. Each subsequent effect triggers all effects before it."
The Nth activation applies every tier unlocked so far - tier 1 alone on the
first, tiers 1+2 on the second, all three from the third on. The sum is the
STEADY state, not the opening value; the old encoding handed the squad its
end-state Crit Damage from the very first cycle (and, inconsistently, used only
the third tier's CDR rather than the running sum).

Fienn's in-game range measurement (2026-07-27) settled it: on the opening burst
her squad Crit Damage contribution was tier 1 alone - 7.74% at skill 7, matching
`description_value_04` exactly, against the 28.45% the old encoding applied.
See docs/decisions.md.

Freestyle (skills[0]) is a self ATK buff on kill, which raid bosses don't grant,
so it's not modeled.
"""
from app.effects import Pulse
from app.skill_rules._helpers import buff_rule, escalating_buff_rule
from app.squad_engine import SkillRule

SKILL_VALUE_MANIFESTS = {
    "volume": {
        "source": "dotgg",
        "test_module": "test_skill_rules_burst1_batch1",
        "keys": {
            "drop_the_beat": ("skills", 1),
            "turn_up": ("skills", 2),
        },
    },
}


def _escalating_cdr_rule(trigger, tier_seconds):
    """The cooldown-reduction half of an escalating bullet.

    `escalating_buff_rule` covers the registry-effect case; a burst-cooldown
    reduction is a Pulse instead, so it needs its own accumulator. On the Nth
    activation every tier unlocked so far fires and they ADD - 2.34, then 5.04,
    then 8.21 sec (Fienn, 2026-07-27). The range measurement could only prove
    the tiers escalate, since cumulative and superseding agree on activation 1;
    Fienn settled which.
    """

    def action(context, caster_slug, time, registry):
        n = context.activation_count(caster_slug, trigger)
        seconds = sum(
            value for unlock_at, value in enumerate(tier_seconds, start=1) if n >= unlock_at
        )
        if seconds:
            registry.add_pulse(Pulse("burst_cooldown_reduction_sec", seconds, "squad", caster_slug))

    return SkillRule(trigger=trigger, action=action)


def build_volume_rules(values):
    beat = values["drop_the_beat"]
    turn_up = values["turn_up"]
    cdr_tiers = [float(beat[f"description_value_0{slot}"]) for slot in (1, 2, 3)]
    crit_damage_tiers = [
        (float(beat["description_value_04"]) / 100, float(beat["description_value_05"])),
        (float(beat["description_value_06"]) / 100, float(beat["description_value_07"])),
        (float(beat["description_value_08"]) / 100, float(beat["description_value_09"])),
    ]
    crit_rate = float(turn_up["description_value_01"]) / 100
    crit_rate_duration = float(turn_up["description_value_02"])

    return [
        _escalating_cdr_rule("full_burst_enter", cdr_tiers),
        # Each tier's 5-sec window is far shorter than her burst cooldown, so
        # re-applications never overlap and plain adds are correct.
        escalating_buff_rule("own_burst_activate", [
            [("other_critical_damage_sources", value, "squad", duration)]
            for value, duration in crit_damage_tiers
        ]),
        buff_rule("own_burst_activate", [
            ("crit_rate", crit_rate, "squad", crit_rate_duration),
        ]),
    ]
