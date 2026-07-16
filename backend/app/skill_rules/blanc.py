"""Blanc (slug "blanc"), a Burst-2 Wind AR defender. Base skills (no signature).

Modeled (DPS-relevant):
- Showtime (skills[2], her burst): enemy Damage Taken ▲ - modeled as a
  squad-scoped `damage_taken_up` so every attacker's hits gain it (the debuff is
  on the boss).
- Rabbit Twins W (skills[1]): her own Burst-Skill cooldown reduction on Full
  Burst end. In game this only activates with a same-squad ally (Rouge or Noir)
  present, and it is SELF-scoped, so it's gated on deck_contains and emitted as
  a self CDR pulse (which reduces only Blanc's cooldown - letting her long 60s
  burst keep pace - not the whole squad's rotation).

Not modeled: Lucky Guard shield (after 120 normal attacks), the per-second
heals, and the lowest-HP-ally Max HP / Indomitability grant - all survivability.
Her burst has no enemy nuke.
"""
from app.effects import Effect, Pulse
from app.squad_engine import SkillRule

SKILL_VALUE_MANIFESTS = {
    "blanc": {
        "source": "dotgg",
        "test_module": "test_skill_rules_blanc",
        "keys": {
            "rabbit_twins_w": ("skills", 1),
            "showtime": ("skills", 2),
        },
    },
}

TWIN_SLUGS = {"rouge", "noir"}


def build_blanc_rules(values):
    showtime = values["showtime"]
    rabbit_twins = values["rabbit_twins_w"]

    damage_taken = float(showtime["description_value_07"]) / 100
    damage_taken_duration = float(showtime["description_value_08"])
    self_cdr_seconds = float(rabbit_twins["description_value_03"])

    def apply_damage_taken(context, caster_slug, time, registry):
        registry.add(
            Effect("damage_taken_up", damage_taken, "squad", damage_taken_duration, caster_slug),
            applied_at=time,
        )

    def emit_self_cdr(context, caster_slug, time, registry):
        registry.add_pulse(Pulse("burst_cooldown_reduction_sec", self_cdr_seconds, "self", caster_slug))

    def has_squad_twin(context, caster_slug):
        return any(member.slug in TWIN_SLUGS for member in context.members)

    return [
        SkillRule(trigger="own_burst_activate", action=apply_damage_taken),
        SkillRule(trigger="full_burst_end", action=emit_self_cdr, condition=has_squad_twin),
    ]
