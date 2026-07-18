"""Laplace's signature-weapon (dollskills) build, slug "laplace-signature" - a
SEPARATE roster entry from base Laplace (slug "laplace"), per Fienn's decision
to model characters with an optional signature weapon as two distinct slugs
(2026-07-12), matching Julia/Julia: Signature and Drake/Drake: Signature. Base
Laplace deferred her entire weapon-transform kit (no in-game tick-count
measurement existed yet); this signature build is now possible because Fienn
measured the transform window in-game (2026-07-19): 1 First Damage hit + 93
Normal Damage ticks over the 10-sec window.

Modeled (DPS-relevant):
- Laplace Buster (dollskills[2], her burst): First Damage 1455.72% of final
  ATK is the direct burst nuke (`laplace_buster_signature_burst_percent`).
  The Normal Damage phase - 22.2% of final ATK per shot, 10 sec - is modeled
  as a `weapon_mode_schedules` segment (`until_shots: BUSTER_SHOTS=93`, rate
  of fire = BUSTER_SHOTS / duration = 9.3/s, Fienn's in-game measured tick
  count - same shape as Red Hood's Red Wolf / Snow White's Seven Dwarves: I /
  Maxwell's Pierce Shot transform segments). Ticks are typed TRUE damage:
  Additional Effect 2 reads "Normal damage is applied as true damage when
  Hero Vision is at max stacks" - the max-stacks GATE itself stays unmodeled
  (Hero Vision's stack counter is deferred, same as base Laplace), but Fienn
  ruled (2026-07-19) the transform should assume Hero Vision sits at max
  stacks for its whole life, so every tick is unconditionally true damage -
  the same steady-state assumption already approved for Red Hood's Glaring
  Eyes (settles fast, stays settled).
  PLUS a per-tick +11.9%-of-final-ATK true-damage rider ("Deals 11.9% of
  final ATK as true damage" when Hero Vision is at max stacks - same steady-
  max assumption) landing alongside each Normal Damage tick: modeled as a
  `scheduled_nukes` spec (`build_buster_scheduled_nukes`) on the identical
  93-tick cadence, anchored to the same `context.burst_times["laplace-
  signature"]` burst times as the weapon-mode segment, so the two paths never
  drift out of sync.
- Hero Bomber (dollskills[1]): unlike base Laplace's `last_bullet` trigger,
  the signature version fires on every Full Charge hit ("Activates when
  hitting a target with Full Charge"): a 132.45% "as additional damage" nuke,
  modeled as a per-shot rule `(1, "every_outside_full_burst", [...])`.
  "Outside full burst" is in-game accurate here, not just an engine
  approximation: her B3 burst opens the transform window AND the squad's
  Full Burst window at the same instant, and during the transform her weapon
  IS the Buster (fixed-rate ticks, not a charge weapon) - there are no Full
  Charge shots inside that window to trigger Hero Bomber. Outside of it, her
  base RL fires Full Charge shots as normal and Hero Bomber fires on every
  one.

Not modeled / deferred (same as base Laplace, plus signature-specific):
- Hero Vision (dollskills[0]): unchanged from base - Explosion Radius is not
  a damage multiplier (inert stat) and its decaying stack counter is
  Pattern B (time-decay gauge), which the engine doesn't model. Its "max
  stacks" gate is approximated as always-true for the transform window's
  true-damage typing (see above) per Fienn's 2026-07-19 ruling; the gate
  itself stays unmodeled.
- Hero Bomber's parts-hit 14.78% additional damage: needs a Parts-hit
  trigger the engine lacks (same as base Laplace).
- Laplace Buster's "Gains Pierce" (Additional Effect 1): the pierce property
  has no engine representation (same as every other transform's Pierce
  rider - Red Hood, Snow White, Maxwell).
- Base Laplace's own weapon-transform kit stays deferred on the "laplace"
  slug (untouched by this module) - it never got an in-game tick-count
  measurement, unlike this signature build.
"""
from app.skill_rules._helpers import instant_nuke_pulse_rule

SKILL_VALUE_MANIFESTS = {
    "laplace-signature": {
        "source": "lootandwaifus",
        "data_slug": "laplace",
        "test_module": "test_skill_rules_laplace_signature",
        "keys": {
            "hero_vision": ("dollskills", 0),
            "hero_bomber": ("dollskills", 1),
            "laplace_buster": ("dollskills", 2),
        },
        # "Additional Effect 1:"/"Additional Effect 2:" labels parse as stray
        # numeric tokens (1, 2); not real values.
        "drop_tokens": {"laplace_buster": (3, 4)},
    },
}

# Fienn's in-game measurement (2026-07-19): 93 Normal Damage ticks across the
# 10-sec transform window (plus the separate First Damage hit at burst time).
BUSTER_SHOTS = 93


def laplace_buster_signature_burst_percent(values):
    return float(values["laplace_buster"]["description_value_01"])


def build_laplace_signature_rules(values):
    # No ally buffs - all of her signature's DPS lives in the burst nuke, the
    # weapon-mode segment, and the scheduled-nuke rider.
    return []


def build_hero_bomber_signature_per_shot_rules(values):
    """Hero Bomber's signature trigger: every Full Charge hit (not base
    Laplace's `last_bullet`), 132.45% of final ATK "as additional damage".
    See module docstring for why `every_outside_full_burst` matches the
    in-game trigger exactly during the transform window."""
    hero_bomber = values["hero_bomber"]
    nuke_percent = float(hero_bomber["description_value_01"])
    return [(1, "every_outside_full_burst", [
        instant_nuke_pulse_rule("per_shot", nuke_percent, full_burst_bonus_eligible=True),
    ])]


def build_buster_weapon_mode_schedule(values):
    """Laplace Buster's Normal Damage phase: 93 measured ticks over the
    10-sec transform window, typed true damage (steady max-Hero-Vision
    assumption - see module docstring)."""
    buster = values["laplace_buster"]
    damage_percent = float(buster["description_value_02"])
    duration = float(buster["description_value_03"])
    profile = {
        "weapon": "RL",
        "damage_percent": damage_percent,
        "rate_of_fire": BUSTER_SHOTS / duration,
        "damage_type": "true",
    }

    def schedule(context, fight_duration):
        return [
            {"start": t, "until_shots": BUSTER_SHOTS, "profile": profile}
            for t in context.burst_times.get("laplace-signature", [])
        ]

    return schedule


def build_buster_scheduled_nukes(values):
    """The per-tick +11.9% true-damage rider riding alongside each Normal
    Damage tick - same 93-tick cadence, same burst-time anchor as the
    weapon-mode segment (see module docstring), so the two paths never drift
    out of sync."""
    buster = values["laplace_buster"]
    rider_percent = float(buster["description_value_04"])
    duration = float(buster["description_value_03"])
    interval = duration / BUSTER_SHOTS

    def schedule(context, fight_duration):
        times = [
            t + k * interval
            for t in context.burst_times.get("laplace-signature", [])
            for k in range(1, BUSTER_SHOTS + 1)
        ]
        return [t for t in times if t < fight_duration]

    return [{"schedule": schedule, "percent": rider_percent, "damage_type": "true"}]
