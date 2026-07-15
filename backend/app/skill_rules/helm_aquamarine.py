"""Helm: Aquamarine (slug "helm-aquamarine"), a Burst-2 Iron AR attacker.
Collected from lootandwaifus.com.

Modeled (DPS-relevant):
- Admire Accompaniment (skills[0]): escalating squad burst-cooldown reduction
  on Full Burst enter - "Once/Twice/Three times, each subsequent effect
  triggers all effects before it" means the tiers SUM (matches the project's
  established escalating-tiers-of-the-same-stat convention). Modeled via
  `context.activation_count(caster_slug, "full_burst_enter")` (this trigger
  isn't gated on her own burst - "when entering Full Burst" is a squad-wide
  event - so the count tracks the raid's cycle number from her perspective).
- Aegis Cannon Overload (skills[2], her burst, cd=20): burst nuke, 164.83% of
  final ATK (`aegis_cannon_overload_burst_percent`).
- Aegis Cannon Suppression Fire (skills[1]): a SEPARATE active skill with its
  own 4-second cooldown, independent of the burst cycle ("Cooldown: 4s" badge,
  not the Burst tab) - fires repeatedly throughout the whole fight regardless
  of burst timing. Fienn approved a new engine capability for this
  (`raid_simulator`'s `periodic_nukes` param / `registry.get_periodic_nuke`)
  rather than a thin/silent approximation, since at 105.58% of final ATK
  per tick (~45 ticks over a 180s fight) this is likely her primary DPS
  source as an Attacker. Exposed via `aegis_cannon_suppression_fire_percent`
  + `AEGIS_CANNON_SUPPRESSION_FIRE_COOLDOWN`.
- Admire Accompaniment (skills[0]) nuke: 131.34% of final ATK every 30 normal
  attacks, via the per-shot trigger (`per_shot_rules`, mode "every" - "after
  landing 30 normal attacks" repeats, matching Brid: Journey Ahead's phrasing).
  See `build_admire_accompaniment_per_shot_rules`. A meaningful DPS lever for an
  AR attacker (~72 hits over a 180s fight).

Not modeled:
- Aegis Cannon Suppression Fire's Electric-Code-conditional stacking Damage
  Taken debuff (5.64% x up to 5 stacks, 5 sec) - needs boss-element access in
  skill rules, which doesn't exist (same gap as Brid: Silent Track's
  Wind-conditional debuff).
- Aegis Cannon Overload's Electric-Code-conditional additional damage bullet
  (164.83%) - same boss-element gap.
"""
from app.effects import Pulse
from app.skill_rules._helpers import instant_nuke_pulse_rule
from app.squad_engine import SkillRule

AEGIS_CANNON_SUPPRESSION_FIRE_COOLDOWN = 4.0  # the skill text hardcodes "Cooldown: 4s"
ADMIRE_ACCOMPANIMENT_NUKE_SHOT_COUNT = 30  # skill text: "after landing 30 normal attacks"


def aegis_cannon_overload_burst_percent(values):
    return float(values["aegis_cannon_overload"]["description_value_01"])


def aegis_cannon_suppression_fire_percent(values):
    return float(values["aegis_cannon_suppression_fire"]["description_value_01"])


def build_helm_aquamarine_rules(values):
    accompaniment = values["admire_accompaniment"]

    cdr_tiers = [
        float(accompaniment["description_value_02"]),  # Once
        float(accompaniment["description_value_03"]),  # Twice
        float(accompaniment["description_value_04"]),  # Three times
    ]

    def apply_cdr(context, caster_slug, time, registry):
        n = context.activation_count(caster_slug, "full_burst_enter")
        total = sum(cdr_tiers[: min(n, len(cdr_tiers))])
        registry.add_pulse(Pulse("burst_cooldown_reduction_sec", total, "squad", caster_slug))

    return [SkillRule(trigger="full_burst_enter", action=apply_cdr)]


def build_admire_accompaniment_per_shot_rules(values):
    """Per-shot rules (see raid_simulator's `per_shot_rules`): every 30 normal
    attacks, deal 131.34% of final ATK as additional damage."""
    nuke_percent = float(values["description_value_01"])
    return [
        (ADMIRE_ACCOMPANIMENT_NUKE_SHOT_COUNT, "every", [instant_nuke_pulse_rule("per_shot", nuke_percent)]),
    ]
