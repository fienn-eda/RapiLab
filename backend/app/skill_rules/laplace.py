"""Laplace (slug "laplace"), a Burst-3 Iron RL attacker. Base skills. Collected
from lootandwaifus.com. She is fundamentally a weapon-transformation unit, so
only a thin representable subset is modeled; the bulk of her kit is deferred.

Modeled (DPS-relevant):
- Laplace Buster's First Damage (897.6% of final ATK) is the burst nuke, above.
- Hero Bomber (skills[1]): when the last bullet hits the target, 81.66% of final
  ATK as additional damage (gap #1 `last_bullet` mode). "As additional damage",
  so Full-Burst-Bonus eligible. See `build_hero_bomber_per_shot_rules`.
- Laplace Buster (skills[2], her burst): her "First Damage" (897.6% of final ATK)
  is modeled as the burst nuke (`laplace_buster_burst_percent`).

Not modeled / deferred (most of her kit):
Modeled (weapon transform, 2026-07-21):
- Laplace Buster's transform: for 5 sec her weapon becomes a Buster firing
  "Normal Damage 14.52%" per shot. Modeled as a `weapon_mode_schedules`
  segment. Its fire rate is the one Fienn measured on the SIGNATURE Buster
  (93 ticks / 10 sec = 9.3/s), which he confirmed (2026-07-21) fires at the
  same rate as this base Buster - so the base 5-sec window is ~46 ticks. Unlike
  the signature, base Laplace does NOT get the max-Hero-Vision true-damage
  conversion (her Hero Vision counter is deferred below, so it can't be gated) -
  every tick is ordinary damage.
- Hero Vision (skills[0]): a full-charge-count stack (Explosion Radius, up to 5,
  decaying over 5 sec). Explosion Radius is not a damage multiplier, and the
  decaying stack counter is Pattern B (time-decay gauge), which the engine
  doesn't model - so the burst's "11.9% true damage when Hero Vision is at max
  stacks" is also deferred (it can't be gated without the counter).
- Hero Bomber's parts-hit 14.78% additional damage - needs a Parts-hit trigger
  the engine lacks.
- Signature/Treasure weapon (dollskills): an even larger weapon-transform build
  (First Damage 1455.72%, 10 sec, conditional true-damage conversion). Deferred
  for the same weapon-transform / Pattern B reasons, so there is no dual-slug
  `laplace-signature` (an unrepresentable signature can't be a deck candidate).
"""
from app.skill_rules._helpers import buff_rule, instant_nuke_pulse_rule

# Fienn (2026-07-21): base Laplace's Buster fires at the same rate as her
# signature's, which he measured in-game at 93 ticks over its 10-sec window.
BUSTER_RATE_OF_FIRE = 93 / 10  # 9.3 ticks/sec, shared by both Buster builds


SKILL_VALUE_MANIFESTS = {
    "laplace": {
        "source": "lootandwaifus",
        "test_module": "test_skill_rules_laplace",
        "keys": {
            "hero_bomber": ("skills", 1),
            "laplace_buster": ("skills", 2),
        },
    },
}


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
    return [(None, "last_bullet", [instant_nuke_pulse_rule("per_shot", nuke_percent, full_burst_bonus_eligible=True)])]


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
