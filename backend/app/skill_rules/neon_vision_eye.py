"""Neon: Vision Eye (slug "neon-vision-eye"), a Burst-3 Electric RL attacker.
Base skills (no signature/Treasure). Collected from lootandwaifus.com.

Her kit runs on a Firepower Gauge, and the gauge is what decides which of her
bursts is the big one. She opens the fight at 100 (skills[1] battle-start), so
her FIRST burst takes the gauge-100 branch and Super Firepower spends all 100.
Refilling runs +2 per normal attack while in Firepower Charge and +45 when that
status ends, which does not reach 100 again within one burst - it takes two.
So Super Firepower lands on her 1st, 4th, 7th ... burst (Fienn, in-game
2026-07-28), and that period is `SUPER_FIREPOWER_BURST_PERIOD`.

This module used to assume the gauge refilled inside the burst cooldown and
granted Super Firepower EVERY cycle, which paid the gauge-100 bonuses three
times over. The refill rates were read as generous without checking what they
add up to between two bursts; ask what a resource actually reaches, not whether
it is "far inside" a cooldown.

Modeled (DPS-relevant):
- Maximum Firepower (skills[1], on entering Full Burst): self ATK +80.04% for
  10 sec on EVERY Full Burst, including cycles another Burst 3 opened - the
  skill's trigger is the window, not her burst. Its Super Firepower additional
  +35.05% rides her own qualifying burst instead (see the builder).
- Super Firepower burst (skills[2], on her burst): the general +110.21% self
  Attack Damage on every burst, plus the gauge-100 branch's +45.03% on the
  qualifying ones (= 155.24% there), for 10 sec. Her burst has NO nuke - all
  her damage is Firepower Explosion below.
- Firepower Explosion (skills[0], on every Full Charge attack vs the stage
  target, i.e. the boss): 437.98% of final ATK as additional damage every full
  charge (RL: every shot is a full charge), plus the Super Firepower additional
  +262.79% on full charges landed within her 10s Super Firepower window - which
  now opens only on the qualifying bursts (gap #7's
  `every_during_own_status_window`, with the burst period). Both are
  Projectile-Explosion damage (a Rocket Launcher's explosion), so a deck's
  Projectile-Explosion-Damage-Up buffs (e.g. Rapi: Red Hood's) credit them. See
  `build_firepower_explosion_per_shot_rules`.

Not modeled / deferred:
- The Firepower Gauge as a live resource. The 3-burst period is Fienn's in-game
  observation, held as a constant rather than derived from the fill rates: the
  +2-per-normal term makes the real refill depend on how fast she shoots, so a
  deck that buffs her attack or charge speed could in principle reach 100 a
  burst sooner. Deriving it needs the recharge tick's rate, which the skill text
  gives as a bare "+1" with no interval.
- Explosion Radius +200% (not a damage multiplier), Burst Gauge filling speed
  (not DPS), and all of Healthy Body's survivability (invulnerability, debuff
  immunity, incoming-healing) are skipped.
"""
from app.skill_rules._helpers import buff_rule, instant_nuke_pulse_rule
from app.squad_engine import SkillRule

SKILL_VALUE_MANIFESTS = {
    "neon-vision-eye": {
        "source": "lootandwaifus",
        "test_module": "test_skill_rules_neon_vision_eye",
        "keys": {
            "healthy_body": ("skills", 0),
            "firepower_charge": ("skills", 1),
            "super_firepower": ("skills", 2),
        },
        "drop_tokens": {
            # The two gauge-branch thresholds ("charge is lower than 100" /
            # "charge is at 100") - branch conditions, not value slots.
            "super_firepower": [0, 3],
        },
    },
}

SUPER_FIREPOWER_WINDOW = 10.0  # Super Firepower status lasts 10 sec from her burst

# Super Firepower lands on her 1st, 4th, 7th ... burst (Fienn, in-game
# 2026-07-28). She opens the fight at gauge 100, so burst 1 qualifies and spends
# it all; the +2-per-normal / +45-on-Firepower-Charge-end refill needs two more
# bursts to get back to 100.
SUPER_FIREPOWER_BURST_PERIOD = 3


def _is_super_firepower_burst(context, caster_slug):
    """Her gauge is at 100 on this burst. `activation_count` is 1-based inside
    the action, so her 1st/4th/7th burst reads 1/4/7."""
    count = context.activation_count(caster_slug, "own_burst_activate")
    return count % SUPER_FIREPOWER_BURST_PERIOD == 1


def build_neon_vision_eye_rules(values):
    firepower_charge = values["firepower_charge"]
    super_firepower = values["super_firepower"]

    max_firepower_atk = float(firepower_charge["description_value_06"]) / 100
    max_firepower_duration = float(firepower_charge["description_value_07"])
    super_firepower_atk = float(firepower_charge["description_value_08"]) / 100
    super_atk_duration = float(firepower_charge["description_value_09"])
    super_attack_damage = float(super_firepower["description_value_03"]) / 100
    super_ad_duration = float(super_firepower["description_value_04"])
    general_attack_damage = float(super_firepower["description_value_08"]) / 100
    general_ad_duration = float(super_firepower["description_value_09"])

    return [
        buff_rule("full_burst_enter", [
            ("atk_percent", max_firepower_atk, "self", max_firepower_duration),
        ]),
        buff_rule("own_burst_activate", [
            ("attack_damage_up", general_attack_damage, "self", general_ad_duration),
        ]),
        # The gauge-100 branch: both "additional effect of Super Firepower
        # status" bullets ride her own qualifying burst. Maximum Firepower's
        # additional reads the status at Full Burst enter, but she is Burst 3 -
        # her burst and the Full Burst it opens are one instant - and her
        # bursts are further apart than the 10 sec status, so the only Full
        # Burst inside her window is the one she opened herself.
        buff_rule("own_burst_activate", [
            ("attack_damage_up", super_attack_damage, "self", super_ad_duration),
            ("atk_percent", super_firepower_atk, "self", super_atk_duration),
        ], condition=_is_super_firepower_burst),
    ]


def build_firepower_explosion_per_shot_rules(values):
    """gap #1 + gap #7: the base 437.98% Firepower Explosion on every full charge,
    plus the +262.79% Super Firepower additional on full charges inside her 10s
    Super Firepower window."""
    healthy_body = values["healthy_body"]
    base_percent = float(healthy_body["description_value_07"])
    super_bonus_percent = float(healthy_body["description_value_08"])
    return [
        (1, "every", [instant_nuke_pulse_rule(
            "per_shot", base_percent,
            damage_type="projectile_explosion")]),
        (
            (1, SUPER_FIREPOWER_WINDOW, SUPER_FIREPOWER_BURST_PERIOD),
            "every_during_own_status_window",
            [instant_nuke_pulse_rule(
                "per_shot", super_bonus_percent,
                damage_type="projectile_explosion")],
        ),
    ]
