"""Laplace (slug "laplace"), a Burst-3 Iron RL attacker. Base skills. Collected
from lootandwaifus.com. She is fundamentally a weapon-transformation unit, so
only a thin representable subset is modeled; the bulk of her kit is deferred.

Modeled (DPS-relevant):
- Laplace Buster (skills[2], her burst): her "First Damage" (897.6% of final ATK)
  is modeled as the burst nuke (`laplace_buster_burst_percent`).
- Hero Bomber (skills[1]): when the last bullet hits the target, 81.66% of final
  ATK as additional damage (gap #1 `last_bullet` mode) - fired off her own
  shots, so it takes the Full Burst bonus on whichever land inside a window.
  See `build_hero_bomber_per_shot_rules`.
- Laplace Buster's transform: for 5 sec her weapon becomes a Buster firing
  "Normal Damage 14.52%" per shot. Modeled as a `weapon_mode_schedules`
  segment. Its fire rate is the one Fienn measured on the SIGNATURE Buster
  (93 ticks / 10 sec = 9.3/s), which he confirmed (2026-07-21) fires at the
  same rate as this base Buster - so the base 5-sec window is ~46 ticks. Every
  tick is ordinary damage: the signature's "Normal damage is applied as true
  damage" conversion is a signature-only bullet, absent from these skills.
- Hero Vision (skills[0]): a Full-Charge stack counter, up to 5, each stack
  lasting 5 sec. Its own payload - Explosion Radius - is not a damage
  multiplier and stays inert, but the counter GATES Laplace Buster's "11.9% of
  final ATK as true damage when Hero Vision is at max stacks", so it is a
  `ResourceSpec` and the rider reads it per tick
  (`build_buster_scheduled_nukes`). At her fire rate the gate never opens; see
  that builder for the arithmetic and for why a constant "never" would be the
  wrong way to say so.

Not modeled / deferred:
- Hero Bomber's parts-hit 14.78% additional damage - needs a Parts-hit trigger
  the engine lacks.
- Her Signature/Treasure weapon build is a SEPARATE slug (`laplace-signature`),
  not something this module represents.
"""
from app.effects import ResourceSpec
from app.skill_rules._helpers import buff_rule, instant_nuke_pulse_rule

# Fienn (2026-07-21): base Laplace's Buster fires at the same rate as her
# signature's, which he measured in-game at 93 ticks over its 10-sec window.
BUSTER_RATE_OF_FIRE = 93 / 10  # 9.3 ticks/sec, shared by both Buster builds

# Hero Vision, the Full-Charge stack counter both builds carry.
HERO_VISION = "hero_vision"


SKILL_VALUE_MANIFESTS = {
    "laplace": {
        "source": "lootandwaifus",
        "test_module": "test_skill_rules_laplace",
        "keys": {
            "hero_vision": ("skills", 0),
            "hero_bomber": ("skills", 1),
            "laplace_buster": ("skills", 2),
        },
    },
}


def hero_vision_cap(values):
    """"stacks up to 5 time(s)"."""
    return int(float(values["hero_vision"]["description_value_02"]))


def hero_vision_lifetime(values):
    """"...and lasts for 5 sec" - 15 on the signature build. Each stack carries
    its own timer (the project's ResourceSpec convention, Modernia's precedent),
    so the count decays one stack at a time once the fills stop."""
    return float(values["hero_vision"]["description_value_03"])


def build_hero_vision_resources(values, slug_duration_key="laplace_buster"):
    """Hero Vision: +1 per Full Charge attack, capped, each stack expiring on
    its own clock.

    The fill deliberately excludes her own Buster transform window. Her weapon
    during that window is not a charge weapon, so its ticks are not Full Charge
    attacks - but they land in the simulator's `shot_times` exactly like her
    ordinary shots, and counting them would let the gauge feed itself out of the
    very transform whose damage reads it."""
    duration = float(values[slug_duration_key]["description_value_03"])
    return [ResourceSpec(
        name=HERO_VISION,
        fill=("per_shot_every_outside_own_status_window", 1, duration),
        cap=hero_vision_cap(values),
    )]


def hero_vision_max_stack_gate(values):
    """The `resource_gate` 4-tuple for "when Hero Vision is at max stacks": a
    binary gate, not a scale. `resource_count` already clamps to the cap, so
    "at max" is "equal to the cap"."""
    cap = hero_vision_cap(values)
    return (HERO_VISION, cap, hero_vision_lifetime(values),
            lambda count: 1.0 if count >= cap else 0.0)


def build_laplace_rules(values):
    """Laplace Buster's "Additional Effect: Gains Pierce" - held for the
    transform's own stated duration, the same window the weapon-mode segment
    uses."""
    duration = float(values["laplace_buster"]["description_value_03"])
    return [buff_rule("own_burst_activate", [("has_pierce", 1.0, "self", duration)])]


def laplace_buster_burst_percent(values):
    return float(values["laplace_buster"]["description_value_01"])


def build_hero_bomber_per_shot_rules(values):
    """gap #1 `last_bullet`: 81.66% of final ATK as additional damage when the
    last bullet of a magazine hits the target."""
    hero_bomber = values["hero_bomber"]
    nuke_percent = float(hero_bomber["description_value_01"])
    return [(None, "last_bullet", [instant_nuke_pulse_rule("per_shot", nuke_percent)])]


def build_buster_weapon_mode_schedule(values):
    """Laplace Buster's Normal Damage phase: a 5-sec self weapon transform
    firing at BUSTER_RATE_OF_FIRE, so ~46 ticks of 14.52% of final ATK. The
    window is bounded by `end` (its stated duration) rather than a measured
    `until_shots`, since only the signature's exact tick count was measured;
    the base count follows from the shared rate and its own 5-sec duration."""
    buster = values["laplace_buster"]
    duration = float(buster["description_value_03"])
    profile = {
        "weapon": "RL",
        "damage_percent": float(buster["description_value_02"]),
        "rate_of_fire": BUSTER_RATE_OF_FIRE,
    }

    def schedule(context, fight_duration):
        return [{"start": t, "end": t + duration, "profile": profile}
                for t in context.burst_times.get("laplace", [])]

    return schedule


def build_buster_scheduled_nukes(values):
    """Laplace Buster's "Activates when Hero Vision is at max stacks ... deals
    11.9% of final ATK as true damage" - a per-tick rider alongside each Normal
    Damage tick, on the same cadence and burst anchor as the weapon-mode
    segment above. The per-tick reading is the signature build's (2026-07-19);
    the bullet is identical in both, so the reading is too.

    The gate is real, not assumed: `resource_gate` is resolved in the
    simulator's phase 2, after the resource pass, so each tick reads Hero
    Vision at its OWN time. On this build the gate never opens at all - 0 of
    322 ticks in the tier-3 measurement shell - because a base stack lasts only
    5 sec, so the 5-stack cap needs 1.00 Full Charge attacks/sec sustained and
    she fires 0.68/sec. Forcing it open would be worth +4.72% of her total, so
    the zero is load-bearing rather than incidental.

    It is still worth wiring rather than leaving the bullet deferred: a deck
    that pushes her charge rate past 1.00/sec turns the gate on, and that is
    the one thing a hardcoded "never" could not do."""
    buster = values["laplace_buster"]
    duration = float(buster["description_value_03"])
    rider_percent = float(buster["description_value_04"])
    interval = 1.0 / BUSTER_RATE_OF_FIRE
    ticks = int(duration * BUSTER_RATE_OF_FIRE)

    def schedule(context, fight_duration):
        times = [
            t + k * interval
            for t in context.burst_times.get("laplace", [])
            for k in range(1, ticks + 1)
        ]
        return [t for t in times if t < fight_duration]

    return [{
        "schedule": schedule,
        "percent": rider_percent,
        "damage_type": "true",
        "resource_gate": hero_vision_max_stack_gate(values),
    }]
