"""Grave (slug "grave"), a Burst-2 Fire AR supporter. Base skills (no
signature weapon).

Modeled (DPS-relevant):
- Plot Spoiler (skills[2], her burst). The text is split into two blocks and
  the scopes follow that split exactly:
  - "Affects self": Pierce (the property), Pierce Damage, Critical Rate. The
    Critical Rate is hers alone, and it is the largest number in the bullet -
    read as a squad buff it pays every ally a crit rate they never get.
  - "Affects all allies": Attack Damage, Pierce Damage, and Max Ammunition
    Capacity +3 ROUNDS (a flat round count, `max_ammo_rounds` -
    raid_simulator converts it against each recipient's own base magazine,
    which is why skill_rules can state it without knowing any weapon).
  All durations are a literal "10 sec" in the skill text (not a data slot),
  hence the hardcoded constant. Her self HP drain and the unlimited ammunition
  (both Prediction) are not modeled.
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

- Overheat (skills[1]), a normal-attack-count escalation on self. Per Fienn
  (verified in-game), the three tiers split into two permanence regimes:
  - Overheat I (self ATK +15.48%): unlocks after 15 normal attacks landed from
    battle start (a plain per-shot counter, NOT Prediction-gated) and is
    PERMANENT once unlocked. The skill text's "removed upon reloading to max
    ammunition" does not recur in practice, so it's modeled as a permanent
    self buff granted once (`unlock_overheat_i`, gap #1's `after` mode). It's
    also Overheat II's prerequisite, satisfied long before the first Prediction.
  - Overheat II (self ATK +20.66%) and III (self Attack Damage +30.8%): unlock
    at the 30th / 60th normal attack landed WHILE in Prediction (her burst's own
    10s status window, gap #7's `every_during_own_status_window` mode) and are
    ACTIVE ONLY WHILE IN PREDICTION. Each is granted refreshing, bounded to the
    end of the current Prediction window, so it fades when Prediction ends and
    re-earns itself the next cycle (Prediction gives unlimited ammo, so at an
    AR's ~12/s she reliably re-reaches 30 (~2.5s) and 60 (~5s) each window).
    II is gated on Overheat I; III on having reached Overheat II. See
    `build_overheat_per_shot_rules`. Self-scoped on a supporter, minor DPS weight.
"""
from app.effects import Effect
from app.squad_engine import SkillRule, own_burst_fired_this_cycle

SKILL_VALUE_MANIFESTS = {
    "grave": {
        "source": "dotgg",
        "test_module": "test_skill_rules_grave",
        "keys": {
            "heat_emission": ("skills", 0),
            "overheat": ("skills", 1),
            "plot_spoiler": ("skills", 2),
        },
    },
}

PLOT_SPOILER_BUFF_DURATION = 10.0  # the skill text hardcodes "10 sec", not a data slot
PREDICTION_DURATION = 10.0  # Plot Spoiler grants Prediction (her status window) for 10 sec
HEAT_EMISSION_STATUS = "heat_emission_active"


def build_grave_rules(values):
    heat_emission = values["heat_emission"]
    plot_spoiler = values["plot_spoiler"]

    self_pierce = float(plot_spoiler["description_value_02"]) / 100
    self_crit_rate = float(plot_spoiler["description_value_06"]) / 100
    squad_attack_damage = float(plot_spoiler["description_value_03"]) / 100
    squad_pierce = float(plot_spoiler["description_value_04"]) / 100
    squad_ammo_rounds = float(plot_spoiler["description_value_05"])
    heat_emission_pierce = float(heat_emission["description_value_05"]) / 100

    def apply_plot_spoiler(context, caster_slug, time, registry):
        registry.add(
            Effect("pierce_damage_up", self_pierce, "self", PLOT_SPOILER_BUFF_DURATION, caster_slug),
            applied_at=time,
        )
        # "Gain Pierce for 10 sec" - the property, without which the Pierce
        # Damage above would credit nothing.
        registry.add(
            Effect("has_pierce", 1.0, "self", PLOT_SPOILER_BUFF_DURATION, caster_slug),
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
            Effect("crit_rate", self_crit_rate, "self", PLOT_SPOILER_BUFF_DURATION, caster_slug),
            applied_at=time,
        )
        registry.add(
            Effect("max_ammo_rounds", squad_ammo_rounds, "squad", PLOT_SPOILER_BUFF_DURATION, caster_slug),
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


def _current_prediction_end(context, caster_slug, time):
    """End of the Prediction window `time` falls in - the latest of Grave's own
    burst times at or before `time`, plus PREDICTION_DURATION. The Overheat II/III
    rules only fire on in-window shots, so such a burst always exists."""
    bursts = [t for t in context.burst_times.get(caster_slug, ()) if t <= time]
    return (max(bursts) + PREDICTION_DURATION) if bursts else time


def build_overheat_per_shot_rules(values):
    """gap #1/#7: Overheat I unlocks at the `oh1_threshold`-th normal attack from
    battle start (permanent self ATK, `after` mode). Overheat II unlocks at the
    `oh2_threshold`-th normal attack landed during Prediction (self ATK), Overheat
    III at the `oh3_threshold`-th (self Attack Damage). II/III are active only
    while in Prediction: granted refreshing and bounded to the current Prediction
    window's end, so they fade when Prediction ends and re-earn each cycle. II is
    gated on Overheat I; III on Overheat II having been reached. See the module
    docstring for the permanence regimes (per Fienn, verified in-game)."""
    overheat = values["overheat"]
    oh1_threshold = int(float(overheat["description_value_01"]))
    oh1_atk = float(overheat["description_value_02"]) / 100
    oh2_threshold = int(float(overheat["description_value_03"]))
    oh2_atk = float(overheat["description_value_04"]) / 100
    oh3_threshold = int(float(overheat["description_value_05"]))
    oh3_attack_damage = float(overheat["description_value_06"]) / 100

    def unlock_overheat_i(context, caster_slug, time, registry):
        if context.has_status(caster_slug, "overheat_i"):
            return
        context.set_status(caster_slug, "overheat_i")
        registry.add(Effect("atk_percent", oh1_atk, "self", None, caster_slug), applied_at=time)

    def apply_overheat_ii(context, caster_slug, time, registry):
        if not context.has_status(caster_slug, "overheat_i"):
            return  # prerequisite: Overheat I must already be unlocked
        context.set_status(caster_slug, "overheat_ii_reached")
        duration = _current_prediction_end(context, caster_slug, time) - time
        registry.add_refreshing(
            Effect("atk_percent", oh2_atk, "self", duration, caster_slug, refresh_group="overheat_ii"),
            applied_at=time,
        )

    def apply_overheat_iii(context, caster_slug, time, registry):
        if not context.has_status(caster_slug, "overheat_ii_reached"):
            return  # prerequisite: Overheat II must have been reached
        duration = _current_prediction_end(context, caster_slug, time) - time
        registry.add_refreshing(
            Effect("attack_damage_up", oh3_attack_damage, "self", duration, caster_slug,
                   refresh_group="overheat_iii"),
            applied_at=time,
        )

    return [
        (oh1_threshold, "after", [SkillRule(trigger="per_shot", action=unlock_overheat_i)]),
        ((oh2_threshold, PREDICTION_DURATION), "every_during_own_status_window",
         [SkillRule(trigger="per_shot", action=apply_overheat_ii)]),
        ((oh3_threshold, PREDICTION_DURATION), "every_during_own_status_window",
         [SkillRule(trigger="per_shot", action=apply_overheat_iii)]),
    ]
