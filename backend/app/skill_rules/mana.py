"""Mana (slug "mana"), a Burst-3 Wind Assault Rifle attacker. Base skills.
PARTIAL - see below.

First consumer of resource_scaled_nukes' optional "resource" field (a plain
repeating DoT with no resource scaling, unlike every prior consumer).

Modeled (DPS-relevant):
- Metal gamma (skills[0]): permanent self ATK +58.08% from battle start.
  The game removes this status when any ally is out of action and restores
  it via other conditions - not modeled (no ally-KO tracking in this
  engine), so it's approximated as always-on for the whole fight, matching
  this project's existing steady-state precedent for statuses no simulated
  fight here ever actually breaks.
- Metal sigma (skills[1]): on entering Full Burst, self Attack Damage +21.12%
  and ATK +63.36% (of her own final ATK, i.e. `atk_percent`), both for 10
  sec. The real trigger is "while in Metal sigma status" (started at battle
  start, consumed by this same effect, restored when she casts her own burst
  before Full Burst ends) - but in this engine's strict burst1->burst2->
  burst3->full-burst ordering, her own (tier-3) burst always fires
  immediately before full_burst_enter in the SAME cycle, so "her burst fired
  this cycle" (`own_burst_fired_this_cycle()`) is exactly equivalent to
  "Metal sigma is active" at the instant full_burst_enter checks it - no
  separate status bookkeeping needed for any deck this engine can simulate
  (one attacker per burst tier).
- Fatal Error! (her burst): self Sustained Damage +52.8% for 10 sec, plus a
  flat (non-resource-scaled) Sustained-typed DoT - 396% of final ATK per
  second, 10 ticks one second apart (`resource_scaled_nukes` with no
  "resource" key, reusing the tick_count/tick_interval machinery built for
  Guillotine's Hero-Level DoT without a fake resource). **Every tick also
  gets the Full Burst Bonus** (`full_burst_bonus_eligible=True`) - confirmed
  in-game (Fienn, 2026-07-12), even though her skill text says "as sustained
  damage" rather than "as additional damage" - the phrase never decided this
  (that rule was deleted 2026-07-28); a repeating
  DoT tick is, by construction, not "at cast time" past its first tick, and
  her 10 ticks span exactly the same 10s the Full Burst window that opens at
  her burst covers).

Not modeled / deferred:
- Metal gamma's heal-after-10-normal-attacks (2.04% of caster's Max HP to all
  allies) and its ally-resurrect (revives the highest-ATK incapacitated ally
  at 96% HP): both HP/survivability mechanics tied to ally-KO tracking, which
  this engine doesn't model at all.
- Metal sigma's Burst Gauge filling speed buff (70.4%): gauge charge time is
  a fixed simulation input, not a stat the engine consumes.
(Metal sigma's Charge Time -0.18 sec on "1 ally with the longest basic Charge
Time" was deferred for three successive reasons, all now retired. "Charge speed
isn't a damage stat" expired with Phase S; "narrow subsets aren't expressible"
expired with gap #3; and the real one - that a FLAT 0.18 SECONDS cannot be
written as a percent of the recipient's own charge - was resolved when
Liberalio's caster-based buff turned out to be the same shape and earned the
`charge_time_reduction_sec` stat. The note here predicted "if a second unit
ever needs a flat charge-time delta, do that instead of special-casing" - which
is exactly what happened. See `build_metal_sigma_charge_rules`.)
"""
from app.effects import Effect
from app.skill_rules._helpers import buff_rule
from app.squad_engine import SkillRule, own_burst_fired_this_cycle


SKILL_VALUE_MANIFESTS = {
    "mana": {
        "source": "lootandwaifus",
        "test_module": "test_skill_rules_mana",
        "keys": {
            "metal_gamma": ("skills", 0),
            "metal_sigma": ("skills", 1),
            "fatal_error": ("skills", 2),
        },
        "drop_tokens": {
            "metal_gamma": [1, 3],
            "metal_sigma": [4, 5],
            "fatal_error": [2, 4],
        },
    },
}


def build_metal_gamma_rules(values):
    atk = float(values["metal_gamma"]["description_value_01"]) / 100
    return [buff_rule("battle_start", [("atk_percent", atk, "self", None)])]


def build_metal_sigma_rules(values):
    sigma = values["metal_sigma"]
    attack_damage = float(sigma["description_value_02"]) / 100
    duration = float(sigma["description_value_03"])
    atk = float(sigma["description_value_04"]) / 100

    def action(context, caster_slug, time, registry):
        registry.add(Effect("attack_damage_up", attack_damage, "self", duration, caster_slug), applied_at=time)
        registry.add(Effect("atk_percent", atk, "self", duration, caster_slug), applied_at=time)

    return [SkillRule(trigger="full_burst_enter", action=action, condition=own_burst_fired_this_cycle())]


def build_fatal_error_self_buff_rules(values):
    burst = values["fatal_error"]
    sustained_up = float(burst["description_value_01"]) / 100
    duration = float(burst["description_value_02"])
    return [buff_rule("own_burst_activate", [("sustained_damage_up", sustained_up, "self", duration)])]


def build_fatal_error_dot(values):
    burst = values["fatal_error"]
    percent = float(burst["description_value_03"])
    tick_count = int(float(burst["description_value_04"]))
    return [{
        "base_percent": percent, "tick_count": tick_count, "tick_interval": 1.0,
        "damage_type": "sustained", "resolves_after_cast": True,
    }]


def build_metal_sigma_charge_rules(values: dict) -> list[SkillRule]:
    """Metal sigma's "Charge Time -0.18 sec" on the ally with the longest basic
    Charge Time.

    Absolute SECONDS, not a percent - which is exactly why this sat deferred:
    the engine's `charge_speed_percent` scales the recipient's own charge, and
    no single percent can represent a fixed 0.18 sec across allies with
    different charges. The `charge_time_reduction_sec` stat added for
    Liberalio's caster-based buff is the same shape, so this rides it.
    """
    sigma = values["metal_sigma"]
    seconds = float(sigma["description_value_05"])
    duration = float(sigma["description_value_06"])

    def action(context, caster_slug, time, registry):
        targets = context.longest_charge_time_slugs(1)
        if not targets:
            return
        registry.add(
            Effect("charge_time_reduction_sec", seconds,
                   f"slugs:{','.join(targets)}", duration, caster_slug),
            applied_at=time,
        )

    return [SkillRule(trigger="full_burst_enter", action=action)]
