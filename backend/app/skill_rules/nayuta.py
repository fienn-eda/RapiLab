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

Not modeled:
- Memory Incineration (Asceticism's self weapon transformation, changing her
  normal-attack weapon for 10s) - no weapon-transformation support.
- Hypocrisy's Full-Charge-during-Memory-Incineration nuke (150% of final ATK,
  +380.46% additional if the enemy is the stage target) - depends on the
  deferred weapon transformation plus a compound "while in status X, on
  full-charge-shot" trigger that doesn't exist.
- Unchanging Heart (self Indomitability), Impermanence's Hit Rate, and the two
  HP-recovery bullets - survivability, not DPS-relevant.
"""
from app.effects import Effect
from app.squad_engine import SkillRule


def asceticism_burst_percent(values):
    return float(values["asceticism"]["description_value_05"])


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
    stage2_threshold = float(impermanence["description_value_07"])  # reaches 10 stacks
    stage2_attack_damage = float(impermanence["description_value_08"]) / 100
    stage3_threshold = float(impermanence["description_value_03"])  # reaches cap 30
    stage3_core_damage = float(impermanence["description_value_04"]) / 100

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
