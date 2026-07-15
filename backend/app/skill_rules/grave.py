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

- Overheat (skills[1]) II and III: normal-attack-count self-buffs that unlock
  DURING Prediction (her burst's own 10s status window, gap #7's
  `every_during_own_status_window` mode). Overheat II unlocks at the 30th normal
  attack landed in Prediction (self ATK +20.66%), Overheat III at the 60th (self
  Attack Damage +30.8%, gated on Overheat II already being active). During
  Prediction she has unlimited ammo (Plot Spoiler), so at an AR's 12/s she
  reaches 30 (~2.5s) and 60 (~5s) inside the first 10s window - both are
  "continuously", modeled as PERMANENT self-buffs granted once (a status flag
  guards against re-granting on later windows). See `build_overheat_per_shot_rules`.
  ASSUMPTION (flagged to Fienn): "continuously" = permanent once unlocked (the
  "while in Prediction and Overheat X status" clause is read as the unlock GATE,
  satisfied inside the first Prediction), NOT active-only-while-in-Prediction.
  Self-scoped on a supporter, so its deck-DPS weight is minor either way.

Not modeled: Overheat I (self ATK +15.48%, "removed upon reloading to max
ammunition") is a reload-gated toggle - needs a reload-boundary trigger the
engine lacks (`engine-gaps.md` #9). Its only structural role is being Overheat
II's prerequisite, which is satisfied during Prediction (15 normals land before
the 30th, and Prediction's unlimited ammo means no reload removes it there), so
Overheat II/III model correctly without it. Self-scoped, low DPS weight.
"""
from app.effects import Effect
from app.squad_engine import SkillRule, own_burst_fired_this_cycle

PLOT_SPOILER_BUFF_DURATION = 10.0  # the skill text hardcodes "10 sec", not a data slot
PREDICTION_DURATION = 10.0  # Plot Spoiler grants Prediction (her status window) for 10 sec
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


def build_overheat_per_shot_rules(values):
    """gap #7: Overheat II unlocks at the `oh2_threshold`-th normal attack landed
    during Prediction (self ATK), Overheat III at the `oh3_threshold`-th (self
    Attack Damage, gated on Overheat II). Both are permanent once unlocked - a
    status flag grants each exactly once, on the first Prediction window that
    reaches the count. See this module's docstring for the "continuously"
    assumption and why Overheat I isn't needed here."""
    overheat = values["overheat"]
    oh2_threshold = int(float(overheat["description_value_03"]))
    oh2_atk = float(overheat["description_value_04"]) / 100
    oh3_threshold = int(float(overheat["description_value_05"]))
    oh3_attack_damage = float(overheat["description_value_06"]) / 100

    def unlock_overheat_ii(context, caster_slug, time, registry):
        if context.has_status(caster_slug, "overheat_ii"):
            return
        context.set_status(caster_slug, "overheat_ii")
        registry.add(Effect("atk_percent", oh2_atk, "self", None, caster_slug), applied_at=time)

    def unlock_overheat_iii(context, caster_slug, time, registry):
        if context.has_status(caster_slug, "overheat_iii"):
            return
        if not context.has_status(caster_slug, "overheat_ii"):
            return  # prerequisite: Overheat II must already be active
        context.set_status(caster_slug, "overheat_iii")
        registry.add(Effect("attack_damage_up", oh3_attack_damage, "self", None, caster_slug), applied_at=time)

    return [
        ((oh2_threshold, PREDICTION_DURATION), "every_during_own_status_window",
         [SkillRule(trigger="per_shot", action=unlock_overheat_ii)]),
        ((oh3_threshold, PREDICTION_DURATION), "every_during_own_status_window",
         [SkillRule(trigger="per_shot", action=unlock_overheat_iii)]),
    ]
