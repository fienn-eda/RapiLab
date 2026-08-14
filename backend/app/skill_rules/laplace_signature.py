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
  Hero Vision is at max stacks", and the segment applies that typing to the
  whole window because a segment's `damage_type` is fixed when the segment is
  built, which is before any resource exists to gate it (see the deferral
  below for the measured cost).
  PLUS a per-tick +11.9%-of-final-ATK true-damage rider ("Deals 11.9% of
  final ATK as true damage" when Hero Vision is at max stacks) landing
  alongside each Normal Damage tick: modeled as a `scheduled_nukes` spec
  (`build_buster_scheduled_nukes`) on the identical 93-tick cadence, anchored
  to the same `context.burst_times["laplace-signature"]` burst times as the
  weapon-mode segment, and GATED on the live Hero Vision count - a
  `scheduled_nukes` resource gate resolves in phase 2, after the resource
  pass, so each tick reads the counter at its own instant. The two paths share
  the same NOMINAL cadence but reach it by different float computations -
  the segment's interval is 1.0/(BUSTER_SHOTS/duration) (rate_of_fire, then
  its reciprocal), the rider's is duration/BUSTER_SHOTS directly - so they
  can differ by sub-ULP (~4e-15s) float rounding, at most 1 ULP on the last
  tick. No consumer (damage log timestamps, full-burst-window checks) can
  observe a drift that small, so in practice the two paths land on the same
  instant; this is not a claim that the two computations are bit-identical.
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
- Hero Vision's Explosion Radius payload: not a damage multiplier, inert.
  (The COUNTER itself is modeled - see `build_hero_vision_signature_resources`
  - and the 11.9% rider now reads it. What stays unmodeled is the gate on the
  weapon-mode segment's true-damage TYPING, below.)
- The max-Hero-Vision gate on the Buster segment's true-damage typing. The
  counter says the gate is open for 82.5% of her transform ticks, but a
  `weapon_mode_schedules` profile fixes its `damage_type` when the segment is
  built - and segments are built while the shot timeline is being generated,
  BEFORE any resource exists to read. Splitting each window into a typed
  prefix and an ordinary suffix needs a schedule that can see its own owner's
  shots, which is a different piece of engine than this one.
  Measured cost of leaving it: the typing is worth +3.54% of her total on a
  DEF-carrying boss, so the ~17.5% of ticks that should lose it overstate her
  by roughly 0.6%. The 11.9% rider, worth +7.34%, is the larger half and IS
  gated (a −1.23% correction). See `docs/engine-gaps.md`.
- Hero Bomber's parts-hit 14.78% additional damage: needs a Parts-hit
  trigger the engine lacks (same as base Laplace).
- Laplace Buster's "Gains Pierce" (Additional Effect 1) IS modeled, as the
  `has_pierce` property for the transform's duration: Pierce Damage Up only
  credits a unit that holds Pierce (Fienn, 2026-07-26).
(Base Laplace's own Buster transform is NOT deferred - `laplace.py` models it
as a 5-sec segment riding the tick rate measured here, which Fienn confirmed
(2026-07-21) is the same for both Busters. What the base build lacks is
Additional Effect 2, the true-damage conversion, which is a signature-only
bullet. Both builds share Hero Vision and the 11.9% rider it gates; the
difference that matters there is the stack lifetime - 5 sec on the base
against 15 here - which is why her gate opens and the base's never does.)
"""
from app.skill_rules._helpers import buff_rule, instant_nuke_pulse_rule
from app.skill_rules.laplace import (
    build_hero_vision_resources,
    hero_vision_max_stack_gate,
)

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
    # weapon-mode segment, and the scheduled-nuke rider. The one self effect is
    # Laplace Buster's "Additional Effect 1: Gains Pierce", held for the
    # transform's own stated duration.
    duration = float(values["laplace_buster"]["description_value_03"])
    return [buff_rule("own_burst_activate", [("has_pierce", 1.0, "self", duration)])]


def build_hero_bomber_signature_per_shot_rules(values):
    """Hero Bomber's signature trigger: every Full Charge hit (not base
    Laplace's `last_bullet`), 132.45% of final ATK "as additional damage".
    See module docstring for why `every_outside_full_burst` matches the
    in-game trigger exactly during the transform window - this relies on
    `_resource_fill_times`'s outside-Full-Burst filter being closed on the
    right (a shot at exactly the FB window's end counts as inside, not
    outside), so the 93rd Buster tick landing at burst+10.0 == FB end is
    never misread as an outside-FB Full Charge shot."""
    hero_bomber = values["hero_bomber"]
    nuke_percent = float(hero_bomber["description_value_01"])
    return [(1, "every_outside_full_burst", [
        instant_nuke_pulse_rule("per_shot", nuke_percent),
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


def build_hero_vision_signature_resources(values):
    """Hero Vision on this build: the same counter as the base's, but each
    stack lasts 15 sec instead of 5, so the cap needs only 0.33 Full Charge
    attacks/sec - a threshold she clears comfortably (0.66/sec measured)."""
    return build_hero_vision_resources(values)


def build_buster_scheduled_nukes(values):
    """The per-tick +11.9% true-damage rider riding alongside each Normal
    Damage tick - same 93-tick cadence, same burst-time anchor as the
    weapon-mode segment (see module docstring), so the two paths never drift
    out of sync.

    Gated on Hero Vision at max stacks, per the bullet's own wording. Fills
    stop for the whole transform - Buster ticks are not Full Charge attacks -
    so the count decays while the rider is firing, and the gate is NOT open for
    the whole window: 506 of 613 ticks (82.5%) in the tier-3 measurement shell.

    How much of a window survives depends on how long she has been shooting
    when the burst lands, so it moves with the seat order: a burst she takes
    early enough that she has not yet landed five Full Charge attacks opens
    with the gate already shut. That dependence is the reason to read the
    counter instead of assuming it."""
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

    return [{
        "schedule": schedule,
        "percent": rider_percent,
        "damage_type": "true",
        "resource_gate": hero_vision_max_stack_gate(values),
    }]
