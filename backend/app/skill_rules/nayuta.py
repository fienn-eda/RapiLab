"""Nayuta (slug "nayuta"), a Burst-2 Wind SMG supporter. Base skills (no
signature weapon).

Impermanence passively stacks "Memory Absorption" once every 3 sec (self,
fixed timeline - not deck/RNG-dependent), up to 30 stacks, unlocking three
self-only ATK/Attack-Damage/core-damage tiers at specific stack thresholds.
Since the interval and thresholds are fixed, each tier's activation time is a
known constant - computed once and added as an Effect with a fixed `applied_at`
from `battle_start` (t=0), NOT approximated as instantly active: Stage 3
doesn't unlock until 90s into a 180s fight (half the raid), and steady-
stating that away would materially overstate her early-fight value (per
Fienn's cycle-accuracy preference).

Per Fienn, "exceeds N stacks" here means "reaches N stacks" (>= N), not a
strict > N - confirmed against his in-game knowledge, since the literal
"exceeds 30" (Stage 3) would otherwise be impossible (30 is also the max cap,
`description_value_02` == `description_value_03` == 30).

Timeline (the Nth stack lands at t=N*3, since the first stack lands at t=3s):
Stage 1 (reaches 2 stacks) at t=6s, Stage 2 (reaches 10 stacks) at t=30s,
Stage 3 (reaches the 30-stack cap) at t=90s.

Modeled (DPS-relevant):
- Impermanence (skills[1]): self ATK / Attack Damage / core-damage (the last
  gated on `core_hittable` like every other core-damage source) at the fixed
  times above, permanent thereafter.
- Hypocrisy (skills[0]): "when Memory Absorption takes effect" (every 3 sec)
  grants SQUAD core-damage + squad ATK (caster-scaled) for 5 sec each time.
  Since the 3-sec re-trigger interval is shorter than the 5-sec duration,
  applications fully overlap from the first trigger onward - modeled as a
  single permanent effect starting at t=3s, equivalent in outcome to the
  actual overlapping 5s pulses.
- Asceticism (skills[2], her burst): squad Attack Damage (35.45%, 15s); burst
  nuke, 645.33% of final ATK (`asceticism_burst_percent`).

- Memory Incineration (Asceticism's self weapon transform): for 10s per burst
  her normal attack becomes a 1.8-sec charge shot at 275.18% of final ATK, 250%
  of that on Full Charge - a `weapon_mode_schedules` segment. See
  `build_memory_incineration_weapon_mode_schedule` for why a segment is right
  here (unlimited ammo, so the no-reload limitation cannot bite) and why the
  cadence is a `rate_of_fire` rather than a `charge_time`.
- Hypocrisy's Full-Charge-during-Memory-Incineration nuke: 150% + 380.46%
  against the stage target, which in a raid is the only enemy, so both always
  apply. Five charges land per window, driven off the same fixed 1.8-sec cadence
  as the segment itself.

Not modeled:
- Unchanging Heart (self Indomitability), Impermanence's Hit Rate, and the two
  HP-recovery bullets - survivability, not DPS-relevant.
"""
from app.effects import Effect
from app.squad_engine import SkillRule

SKILL_VALUE_MANIFESTS = {
    "nayuta": {
        "source": "lootandwaifus",
        "test_module": "test_skill_rules_nayuta",
        "keys": {
            "hypocrisy": ("skills", 0),
            "impermanence": ("skills", 1),
            "asceticism": ("skills", 2),
        },
    },
}


def asceticism_burst_percent(values):
    return float(values["asceticism"]["description_value_03"])


def build_nayuta_rules(values):
    hypocrisy = values["hypocrisy"]
    impermanence = values["impermanence"]
    asceticism = values["asceticism"]
    caster_atk = values["caster_atk"]

    hyp_core_damage = float(hypocrisy["description_value_03"]) / 100
    hyp_atk = float(hypocrisy["description_value_05"]) / 100 * caster_atk

    imp_interval = float(impermanence["description_value_01"])  # 3 sec
    stage1_threshold = float(impermanence["description_value_05"])  # reaches 2 stacks
    stage1_atk = float(impermanence["description_value_06"]) / 100
    stage2_threshold = float(impermanence["description_value_08"])  # reaches 10 stacks
    stage2_attack_damage = float(impermanence["description_value_09"]) / 100
    stage3_threshold = float(impermanence["description_value_11"])  # reaches cap 30
    stage3_core_damage = float(impermanence["description_value_12"]) / 100

    # the Nth stack lands at t=N*imp_interval - all three stages use the same
    # "reaches N stacks" formula (see module docstring).
    stage1_time = stage1_threshold * imp_interval
    stage2_time = stage2_threshold * imp_interval
    stage3_time = stage3_threshold * imp_interval

    burst_attack_damage = float(asceticism["description_value_01"]) / 100
    burst_attack_damage_duration = float(asceticism["description_value_02"])

    def apply_fixed_time_effects(context, caster_slug, time, registry):
        registry.add(
            Effect("other_core_damage_sources", hyp_core_damage, "squad", None, caster_slug),
            applied_at=imp_interval,
        )
        registry.add(
            Effect("flat_atk", hyp_atk, "squad", None, caster_slug), applied_at=imp_interval
        )
        registry.add(
            Effect("atk_percent", stage1_atk, "self", None, caster_slug), applied_at=stage1_time
        )
        registry.add(
            Effect("attack_damage_up", stage2_attack_damage, "self", None, caster_slug),
            applied_at=stage2_time,
        )
        registry.add(
            Effect("other_core_damage_sources", stage3_core_damage, "self", None, caster_slug),
            applied_at=stage3_time,
        )

    def apply_asceticism(context, caster_slug, time, registry):
        registry.add(
            Effect("attack_damage_up", burst_attack_damage, "squad", burst_attack_damage_duration, caster_slug),
            applied_at=time,
        )

    return [
        SkillRule(trigger="battle_start", action=apply_fixed_time_effects),
        SkillRule(trigger="own_burst_activate", action=apply_asceticism),
    ]


def _memory_incineration_window(asceticism):
    """(charge interval, duration) of the transform window. The charge time is
    "Fixed at 1.8 sec", so it is returned as a cadence, not a charge_time - see
    build_memory_incineration_weapon_mode_schedule."""
    return (float(asceticism["description_value_04"]),
            float(asceticism["description_value_07"]))


def build_memory_incineration_weapon_mode_schedule(values):
    """Asceticism's self weapon transform: for 10 sec her normal attack becomes a
    1.8-sec charge shot at 275.18% of final ATK, 250% of that on Full Charge.

    Modeled as a `weapon_mode_schedules` segment rather than Anis: Star's
    equivalent-charge-speed-buff trick, because the one thing that forced that
    detour does not apply here: segments never reload, and Memory Incineration
    grants "Unlimited ammunition" for exactly the same 10 sec, so there is no
    magazine to interrupt the window.

    The cadence is given as `rate_of_fire`, not `charge_time`: a charge_time
    profile honours live Charge Speed buffs, but the skill fixes the charge at
    1.8 sec, and an explicit rate_of_fire is precisely the profile kind that
    takes no cadence buffs. "SR" is the engine's charge archetype - the weapon
    string only changes damage typing for RL.
    """
    asceticism = values["asceticism"]
    interval, duration = _memory_incineration_window(asceticism)
    profile = {
        "weapon": "SR",
        "damage_percent": float(asceticism["description_value_05"]),
        "charge_damage_percent": float(asceticism["description_value_06"]),
        "rate_of_fire": 1 / interval,
    }

    def schedule(context, fight_duration):
        return [
            {"start": t, "end": t + duration, "profile": profile}
            for t in context.burst_times.get("nayuta", [])
        ]

    return schedule


def build_memory_incineration_scheduled_nukes(values):
    """Hypocrisy's compound trigger: "when attacking with Full Charge while in
    Memory Incineration status", 150% of final ATK, plus 380.46% additional
    against the stage target - which in a raid is the only enemy, so both
    always apply and are summed into one per-charge hit.

    The charge times are derived from the same fixed 1.8-sec cadence the weapon
    segment uses, so the two stay in lockstep by construction.
    """
    hypocrisy = values["hypocrisy"]
    interval, duration = _memory_incineration_window(values["asceticism"])
    percent = (float(hypocrisy["description_value_09"])
               + float(hypocrisy["description_value_10"]))

    def schedule(context, fight_duration):
        ticks = []
        for burst in context.burst_times.get("nayuta", []):
            k = 1
            while (tick := burst + k * interval) < min(burst + duration, fight_duration):
                ticks.append(tick)
                k += 1
        return ticks

    return [{"schedule": schedule, "percent": percent}]
