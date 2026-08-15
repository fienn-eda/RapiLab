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
  hence the hardcoded constant. Her self HP drain (Prediction) is not modeled -
  survivability. Prediction's unlimited ammunition IS modeled - see below.
- Prediction's unlimited ammunition ("Affects self", Plot Spoiler): raises
  `max_ammo_percent` for the 10-sec window instead of a weapon-mode segment -
  a segment would freeze her cadence to an explicit `rate_of_fire`, silencing
  every live attack-speed buff during the exact window her deck's buffs are
  up. See `unlimited_ammo_percent`.
- Heat Emission (skills[0]): "Activates when Prediction status ends" -
  Prediction is granted for exactly 10 sec by her own burst, and Full Burst
  itself lasts 10 sec, so activation is approximated as firing at
  full_burst_end IF her own burst fired this cycle (`own_burst_fired_this_cycle`).
  Ends when either of two in-game tooltip conditions fires ("[방열 제거 조건]"):
  (1) a reload completes to MAX AMMUNITION, or (2) she bursts again. Prediction
  dumps her ammo and Reload Ratio halves what each load puts back, so it takes
  a doubled reload to satisfy (1) - `heat_emission_seconds` - and that is far
  shorter than (2), her 40-sec burst cooldown. So the squad Pierce Damage buff
  is timed to the doubled reload, not to her next burst: a status flag gates
  re-triggering while it and its buff are both live, and the buff itself
  expires on its own duration (`heat_emission_duration`), so the reburst rule
  (`remove_heat_emission_on_reburst`) only has the status flag left to clear -
  a safety net for condition (2), which in practice never arrives before
  condition (1) already closed the buff out. Also modeled: the forced double
  reload itself (`build_grave_weapon_mode_schedule`), the segment that spends
  it. Her own HP regen and the Burst Gauge fill-speed bonus (gauge_charge_time
  is a fixed sim input, not consumed) are not modeled.

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
from app.attack_rate import rate_of_fire_for_profile, reload_time_with_speed
from app.effects import Effect
from app.skill_rules._helpers import silent_reload_segments
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

# Prediction's unlimited ammo only has to outlast the window. Four times the
# rounds an unbuffed AR spends in it is headroom no deck's attack speed
# reaches, and the magazine is discarded at the window's end anyway.
UNLIMITED_AMMO_HEADROOM = 4.0


def unlimited_ammo_percent(values):
    """Prediction's unlimited ammunition, as a max-ammo ratio big enough that no
    reload lands inside the window.

    NOT a weapon-mode segment: a segment would silence her own weapon and take
    its cadence from an explicit `rate_of_fire`, which by contract ignores live
    buffs - and this window is exactly when her deck's buffs are up. Raising
    max ammo keeps every live buff and costs one approximation instead: capacity
    is sampled at each magazine's START, so the grant reaches the first magazine
    that begins inside Prediction rather than the one already in flight. That
    leaves one extra reload in the window, which understates her.
    """
    weapon = values["caster_weapon_stats"]
    rounds = (PREDICTION_DURATION * rate_of_fire_for_profile(weapon)
              * UNLIMITED_AMMO_HEADROOM)
    return rounds / weapon["max_ammo"] - 1.0


def heat_emission_seconds(values):
    """How long Heat Emission lives: the lengthened reload it takes to get back
    to max ammo from empty.

    In-game tooltip "[방열 제거 조건]": Heat Emission is removed (1) when a
    reload completes to MAX AMMUNITION, or (2) when she bursts again. Condition
    1 fires first by a wide margin - her burst cooldown is 40 sec - so the
    status, and everything hanging off it, lives exactly as long as this.

    Reload Ratio down 50% halves what each load puts back, so it takes twice as
    many loads to reach max, which is what Fienn read in game as "she loads half
    a magazine twice - the reload just takes twice as long". This is a MULTIPLIER
    on her reload, not an absolute load count: her AR already loads in halves
    (`CLIP_RELOAD_SPLITS["grave"] = 2`, folded into `reload_time` before a
    builder sees it), and the skill halves that ratio again on top.

    Approximation: the reload's fixed animation segment (RELOAD_FIXED_SECONDS)
    is paid once per lengthened reload, not once per load. Unmeasured either
    way, and it is 0.148 sec against a multi-second window.
    """
    ratio_reduction = float(values["heat_emission"]["description_value_02"]) / 100
    reload_multiplier = 1 / (1 - ratio_reduction)
    normal = reload_time_with_speed(values["caster_weapon_stats"]["reload_time"], 0.0)
    return reload_multiplier * normal


def build_grave_weapon_mode_schedule(values):
    """The ammo dump when Prediction ends, as a segment that fires nothing.

    "Removes 100% of bullets" lands at the end of her own burst's Prediction
    window, and the reload that follows runs for `heat_emission_seconds` - twice
    a normal one, because Reload Ratio only puts half the magazine back per
    load. `rate_of_fire` (not `charge_time`) so no ally's Charge Speed buff can
    shrink the window into leaking a shot.

    Limitation: this segment anchors on `burst_time + PREDICTION_DURATION`, a
    fixed 10-sec offset, while `apply_heat_emission` (build_grave_rules) fires
    the Heat Emission Pierce Damage buff on the live `full_burst_end` trigger,
    whose timing follows the deck's actual Full Burst length. Both represent
    the same in-game moment (Prediction ending), but Full Burst length is not
    fixed in this engine - Isabel shortens it by 5 sec, Modernia extends it by
    5 sec - so a deck carrying either separates the ammo dump from the Heat
    Emission buff by up to 5 sec.
    """
    return silent_reload_segments(
        "grave",
        heat_emission_seconds(values),
        values["caster_weapon_stats"]["weapon"],
        offset=PREDICTION_DURATION,
    )


def build_grave_rules(values):
    heat_emission = values["heat_emission"]
    plot_spoiler = values["plot_spoiler"]

    self_pierce = float(plot_spoiler["description_value_02"]) / 100
    self_crit_rate = float(plot_spoiler["description_value_06"]) / 100
    squad_attack_damage = float(plot_spoiler["description_value_03"]) / 100
    squad_pierce = float(plot_spoiler["description_value_04"]) / 100
    squad_ammo_rounds = float(plot_spoiler["description_value_05"])
    heat_emission_pierce = float(heat_emission["description_value_05"]) / 100
    unlimited_ammo = unlimited_ammo_percent(values)
    heat_emission_duration = heat_emission_seconds(values)

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
        # Prediction's unlimited ammunition, for the window her own burst opens.
        registry.add(
            Effect("max_ammo_percent", unlimited_ammo, "self", PREDICTION_DURATION, caster_slug),
            applied_at=time,
        )

    def remove_heat_emission_on_reburst(context, caster_slug, time, registry):
        # Removal condition 2. The buff itself is already timed out by then
        # (condition 1 fires within two reloads), so only the status flag is
        # cleared here.
        if context.has_status(caster_slug, HEAT_EMISSION_STATUS):
            context.clear_status(caster_slug, HEAT_EMISSION_STATUS)

    def apply_heat_emission(context, caster_slug, time, registry):
        if context.has_status(caster_slug, HEAT_EMISSION_STATUS):
            return
        context.set_status(caster_slug, HEAT_EMISSION_STATUS)
        # The status ends when a reload reaches max ammo (in-game tooltip
        # condition 1), which the double reload below does. Her burst - the
        # other removal condition - is 40 sec away and never gets there first,
        # so `remove_heat_emission_on_reburst` stays only as a safety net.
        registry.add(
            Effect("pierce_damage_up", heat_emission_pierce, "squad",
                   heat_emission_duration, caster_slug),
            applied_at=time,
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
