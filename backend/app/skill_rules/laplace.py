"""Laplace (slug "laplace"), a Burst-3 Iron RL attacker. Base skills. Collected
from lootandwaifus.com. She is fundamentally a weapon-transformation unit, so
only a thin representable subset is modeled; the bulk of her kit is deferred.

Modeled (DPS-relevant):
- Hero Bomber (skills[1]): when the last bullet hits the target, 81.66% of final
  ATK as additional damage (gap #1 `last_bullet` mode). "As additional damage",
  so Full-Burst-Bonus eligible. See `build_hero_bomber_per_shot_rules`.
- Laplace Buster (skills[2], her burst): her "First Damage" (897.6% of final ATK)
  is modeled as the burst nuke (`laplace_buster_burst_percent`).

Not modeled / deferred (most of her kit):
- Laplace Buster's weapon transformation: for 5 sec her weapon changes to a
  Buster mode dealing "Normal Damage 14.52%" per shot with Pierce. Weapon-mode
  switching is a deferred state machine (same gap as Snow White / Maxwell), and
  the simulator keeps modeling her normal Rocket Launcher during those 5 sec.
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
from app.skill_rules._helpers import instant_nuke_pulse_rule


def laplace_buster_burst_percent(values):
    return float(values["laplace_buster"]["description_value_01"])


def build_hero_bomber_per_shot_rules(values):
    """gap #1 `last_bullet`: 81.66% of final ATK as additional damage when the
    last bullet of a magazine hits the target."""
    hero_bomber = values["hero_bomber"]
    nuke_percent = float(hero_bomber["description_value_01"])
    return [(None, "last_bullet", [instant_nuke_pulse_rule("per_shot", nuke_percent, full_burst_bonus_eligible=True)])]
