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
- The Firepower Gauge as a live resource - and measured to be inert
  (2026-08-14), so this is a closed question, not a gap. The constant is not a
  stand-in for
  something unknown: simulating the gauge straight from the skill text
  reproduces Fienn's 1st/4th/7th observation exactly, and the answer is
  structurally locked, so a live gauge would return the same three.

  The arithmetic. She opens at 100 (battle start), a qualifying burst spends
  all 100, and a non-qualifying one puts back +2 per normal attack for the
  10-sec Firepower Charge window plus +45 when that window ends. At her
  measured 0.99-1.06 shots/sec that is 66-68 a cycle, so two cycles are needed
  to clear 100 and Super Firepower lands every third burst. Checked across six
  decks - every one gives 1, 4, 7.

  Why a faster deck cannot move it. Reaching 100 inside ONE cycle needs
  1 + 2N + 45 >= 100, i.e. N >= 27 normal attacks in the 10-sec window: 2.7
  shots/sec, two and a half times what a Rocket Launcher does. The period only
  stretches past three below 2 shots per window. The whole realistic band sits
  in the interior.

  This also settles the one ambiguity in the text. "Firepower Charge: Charges
  the Firepower Gauge for 10 sec ... Increases the Firepower Gauge's charge by
  1" reads either as a one-shot +1 or as +1 per tick across the 10 sec, and the
  bullet names no interval. Both readings were simulated; both give 1, 4, 7 -
  an ambiguity that cannot change any number is not a blocker.
- Explosion Radius +200% (not a damage multiplier) and all of Healthy Body's
  survivability (invulnerability, debuff immunity, incoming-healing) are
  skipped.
- Firepower Charge's self Burst Gauge filling speed ("when Full Burst ends
  while Firepower Gauge is active", +5% per point of Firepower Gauge charge,
  up to +500%) is deferred, unlike the other three carriers of this stat
  (`anis_star.py`, `grave.py`, `mana.py`). It scales off the Firepower Gauge's
  actual AMOUNT, and this module deliberately does not carry that as a live
  quantity - the arithmetic above found the gauge inert for DAMAGE
  (2026-08-14) and replaced it with a fixed 1st/4th/7th burst period. That
  finding still stands; this is a different question. **This is a deferral of
  SIZE, not of knowledge** - the trajectory itself (battle-start 100, +2 per
  normal attack, +45 on Firepower Charge end, -100 on a qualifying burst) is
  already measurement-verified (the same arithmetic reproduces Fienn's
  in-game 1st/4th/7th reading across six decks, above). What's missing is a
  `ResourceSpec` to carry that trajectory as a live value readable at each
  Full Burst end, not missing information about what the value would be. See
  `docs/engine-gaps.md`'s "네온: 비전 아이의 게이지 충전 속도" row and
  `.superpowers/sdd/2026-08-21-burst-gauge-as-deck-property/gauge-effect-census.md`.
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
