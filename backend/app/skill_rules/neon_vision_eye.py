"""Neon: Vision Eye (slug "neon-vision-eye"), a Burst-3 Electric RL attacker.
Base skills (no signature/Treasure). Collected from lootandwaifus.com.

Her kit runs on a Firepower Gauge that starts at 100 and, once consumed by her
burst, refills to 100 (+2 per normal, +1 per recharge tick, +45 when Firepower
Charge ends) far inside the 40s burst cooldown - so EVERY burst reaches gauge
100 and triggers Super Firepower. The gauge is therefore modeled as a
steady-state "Super Firepower every cycle" assumption rather than a live
resource: the Super-Firepower-gated bonuses are always applied per cycle, and
the +262.79% explosion bonus is gated to her 10s Super Firepower window.

Modeled (DPS-relevant), under that steady-state assumption:
- Maximum Firepower (skills[1], on entering Full Burst): self ATK +80.04%, plus
  the Super Firepower additional +35.05% (= 115.09%), for 10 sec.
- Super Firepower burst (skills[2], on her burst): self Attack Damage +45.03%
  (the gauge-100 branch) plus the general +110.21% (= 155.24%), for 10 sec. Her
  burst has NO nuke - all her damage is Firepower Explosion below.
- Firepower Explosion (skills[0], on every Full Charge attack vs the stage
  target, i.e. the boss): 437.98% of final ATK as additional damage every full
  charge (RL: every shot is a full charge), plus the Super Firepower additional
  +262.79% on full charges landed within her 10s Super Firepower window (gap #7's
  `every_during_own_status_window`). "As additional damage", so both are
  Full-Burst-Bonus eligible. See `build_firepower_explosion_per_shot_rules`.

Not modeled / deferred:
- The Firepower Gauge itself (approximated as steady-state Super Firepower every
  cycle, above - a live resource would matter only if some cycle failed to
  refill to 100, which the refill rates make unlikely).
- Firepower Explosion is nominally a Rocket-Launcher explosion but is recorded as
  a plain "attack"-type instant nuke (the pulse path has no damage_type); this is
  inert in her own kit but would under-credit a deck pairing her with
  projectile-explosion buffers - a deferred refinement.
- Explosion Radius +200% (not a damage multiplier), Burst Gauge filling speed
  (not DPS), and all of Healthy Body's survivability (invulnerability, debuff
  immunity, incoming-healing) are skipped.
"""
from app.skill_rules._helpers import buff_rule, instant_nuke_pulse_rule

SUPER_FIREPOWER_WINDOW = 10.0  # Super Firepower status lasts 10 sec from her burst


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
            ("atk_percent", super_firepower_atk, "self", super_atk_duration),  # Super Firepower additional
        ]),
        buff_rule("own_burst_activate", [
            ("attack_damage_up", super_attack_damage, "self", super_ad_duration),  # gauge-100 branch
            ("attack_damage_up", general_attack_damage, "self", general_ad_duration),
        ]),
    ]


def build_firepower_explosion_per_shot_rules(values):
    """gap #1 + gap #7: the base 437.98% Firepower Explosion on every full charge,
    plus the +262.79% Super Firepower additional on full charges inside her 10s
    Super Firepower window."""
    healthy_body = values["healthy_body"]
    base_percent = float(healthy_body["description_value_07"])
    super_bonus_percent = float(healthy_body["description_value_08"])
    return [
        (1, "every", [instant_nuke_pulse_rule("per_shot", base_percent, full_burst_bonus_eligible=True)]),
        (
            (1, SUPER_FIREPOWER_WINDOW),
            "every_during_own_status_window",
            [instant_nuke_pulse_rule("per_shot", super_bonus_percent, full_burst_bonus_eligible=True)],
        ),
    ]
