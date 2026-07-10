"""Grave (slug "grave"), a Burst-2 Fire AR supporter. Base skills (no
signature weapon).

Modeled (DPS-relevant):
- Plot Spoiler (skills[2], her burst): self Pierce Damage; squad Attack
  Damage, Pierce Damage, and Critical Rate. All durations are a literal
  "10 sec" in the skill text (not a data slot), hence the hardcoded constant.
  Her self HP drain (Prediction) and the flat "+3 rounds" Max Ammo bullet are
  not modeled - the latter needs the caster's base ammo, which skill_rules
  doesn't have access to (only raid_simulator/roster do).
- Heat Emission (skills[0]): "Activates when Prediction status ends" -
  Prediction is granted for exactly 10 sec by her own burst, and Full Burst
  itself lasts 10 sec, so activation is approximated as firing at
  full_burst_end IF her own burst fired this cycle (`own_burst_fired_this_cycle`).
  Per Fienn, the "removed under certain conditions" text means Heat Emission is
  removed exactly when Grave uses her burst skill AGAIN - so the squad Pierce
  Damage buff is really a TOGGLE: off during each ~10s Prediction window right
  after she bursts, on the rest of the time. Modeled with a status flag +
  `EffectRegistry.truncate_open_ended`: the buff is added open-ended
  (duration=None) when Heat Emission activates, and closed out (duration set to
  the elapsed time) the next time her own burst fires - so replay queries for
  any point in the fight see the correct on/off windows. Her own HP regen and
  the Burst Gauge fill-speed bonus (gauge_charge_time is a fixed sim input, not
  consumed) are not modeled.

Not modeled: Overheat (skills[1]) is a normal-attack-count-based self-buff
chain (Overheat I/II/III) - no normal-attack-count trigger exists in the engine.
"""
from app.effects import Effect
from app.squad_engine import SkillRule, own_burst_fired_this_cycle

PLOT_SPOILER_BUFF_DURATION = 10.0  # the skill text hardcodes "10 sec", not a data slot
HEAT_EMISSION_STATUS = "heat_emission_active"


def build_grave_rules(values):
    heat_emission = values["heat_emission"]
    plot_spoiler = values["plot_spoiler"]

    self_pierce = float(plot_spoiler["description_value_02"]) / 100
    squad_attack_damage = float(plot_spoiler["description_value_03"]) / 100
    squad_pierce = float(plot_spoiler["description_value_04"]) / 100
    squad_crit_rate = float(plot_spoiler["description_value_06"]) / 100
    heat_emission_pierce = float(heat_emission["description_value_05"]) / 100

    def apply_plot_spoiler(context, caster_slug, time, registry):
        registry.add(
            Effect("pierce_damage_up", self_pierce, "self", PLOT_SPOILER_BUFF_DURATION, caster_slug),
            applied_at=time,
        )
        registry.add(
            Effect("attack_damage_up", squad_attack_damage, "squad", PLOT_SPOILER_BUFF_DURATION, caster_slug),
            applied_at=time,
        )
        registry.add(
            Effect("pierce_damage_up", squad_pierce, "squad", PLOT_SPOILER_BUFF_DURATION, caster_slug),
            applied_at=time,
        )
        registry.add(
            Effect("crit_rate", squad_crit_rate, "squad", PLOT_SPOILER_BUFF_DURATION, caster_slug),
            applied_at=time,
        )

    def remove_heat_emission_on_reburst(context, caster_slug, time, registry):
        if context.has_status(caster_slug, HEAT_EMISSION_STATUS):
            registry.truncate_open_ended("pierce_damage_up", caster_slug, time)
            context.clear_status(caster_slug, HEAT_EMISSION_STATUS)

    def apply_heat_emission(context, caster_slug, time, registry):
        if context.has_status(caster_slug, HEAT_EMISSION_STATUS):
            return
        context.set_status(caster_slug, HEAT_EMISSION_STATUS)
        registry.add(
            Effect("pierce_damage_up", heat_emission_pierce, "squad", None, caster_slug), applied_at=time
        )

    return [
        SkillRule(trigger="own_burst_activate", action=apply_plot_spoiler),
        SkillRule(trigger="own_burst_activate", action=remove_heat_emission_on_reburst),
        SkillRule(trigger="full_burst_end", action=apply_heat_emission, condition=own_burst_fired_this_cycle()),
    ]
