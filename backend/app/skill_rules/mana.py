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
  and ATK +63.36% (of her own final ATK, i.e. `atk_percent`), both for 10 sec -
  gated on the Metal sigma STATUS, which the same bullet then spends
  ("Removes Metal sigma").

  Sigma is a status that CARRIES ACROSS CYCLES, not a per-cycle check, and the
  distinction is load-bearing in a deck with two Burst 3s. Fienn's in-game
  reading (2026-08-17):

      battle start -> sigma ON
      cycle 1, Mana bursts  -> FB entry: sigma present, buffs fire, sigma OFF
                            -> FB end:   she cast this window, sigma ON again
      cycle 2, the OTHER B3 -> FB entry: sigma present, buffs fire, sigma OFF
                            -> FB end:   she did not cast, sigma stays OFF
      cycle 3, Mana bursts  -> FB entry: no sigma, NO buffs

  So the fourth bullet ("Activates if the skill user has cast Burst Skill
  before Full Burst ends") is settled at Full Burst END, and the payoff lands
  on the cycle AFTER the one she bursts in. Modeled with an explicit status:
  `battle_start` sets it, `full_burst_enter` spends it, `full_burst_end`
  restores it when `own_burst_fired_this_cycle()` (still populated there -
  the simulator clears `burst_used_this_cycle` after the trigger runs).

  This used to read `own_burst_fired_this_cycle()` on `full_burst_enter`,
  which put the buffs on exactly the wrong cycles: her own burst damage
  collected an ATK buff the game pays the next window instead. The docstring
  justified it as "no deck this engine can simulate has two attackers in a
  tier" - which is false; `burst_cycle`'s `chosen = eligible[0]` alternates
  same-tier members. Alone in her tier she casts every cycle, so sigma is
  restored every cycle and the two readings agree - which is why it went
  unnoticed.
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

Metal sigma's Burst Gauge filling speed (self, +70.4% at lv10) rides the same
grant/spend/restore lifecycle as the status flag: up while Metal sigma is up,
closed at Full Burst entry by `EffectRegistry.truncate_open_ended` (the window
until the NEXT Full Burst entry is not known when it is granted, so a fixed
duration cannot express it - see `build_metal_sigma_rules`).

Not modeled / deferred:
- Metal gamma's heal-after-10-normal-attacks (2.04% of caster's Max HP to all
  allies) and its ally-resurrect (revives the highest-ATK incapacitated ally
  at 96% HP): both HP/survivability mechanics tied to ally-KO tracking, which
  this engine doesn't model at all.
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
from app.squad_engine import SkillRule, has_status, own_burst_fired_this_cycle

# "Metal σ", the status her Skill 2 spends at Full Burst entry and re-earns at
# Full Burst end. Tracked as a flag - `spend_sigma`'s condition gates on it -
# alongside its own payload, a `burst_gauge_fill_speed_percent` Effect that
# rides the same grant/spend timeline (see `build_metal_sigma_rules`).
METAL_SIGMA_STATUS = "metal_sigma"


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
    """Metal sigma's three moments: granted at battle start, SPENT at Full Burst
    entry for the two self buffs, and restored at Full Burst end if she cast her
    own burst inside that window. See the module docstring for the in-game
    sequence this reproduces."""
    sigma = values["metal_sigma"]
    gauge_fill_speed = float(sigma["description_value_01"]) / 100
    attack_damage = float(sigma["description_value_02"]) / 100
    duration = float(sigma["description_value_03"])
    atk = float(sigma["description_value_04"]) / 100

    def grant_sigma(context, caster_slug, time, registry):
        context.set_status(caster_slug, METAL_SIGMA_STATUS)
        # The status's own payload: self Burst Gauge filling speed, open-ended
        # until `spend_sigma` closes it - the window until the next Full Burst
        # entry isn't known here, so a fixed duration can't express it.
        registry.add(
            Effect("burst_gauge_fill_speed_percent", gauge_fill_speed, "self", None, caster_slug),
            applied_at=time,
        )

    def spend_sigma(context, caster_slug, time, registry):
        registry.add(Effect("attack_damage_up", attack_damage, "self", duration, caster_slug), applied_at=time)
        registry.add(Effect("atk_percent", atk, "self", duration, caster_slug), applied_at=time)
        registry.truncate_open_ended("burst_gauge_fill_speed_percent", caster_slug, time)
        context.clear_status(caster_slug, METAL_SIGMA_STATUS)  # "Removes Metal σ."

    return [
        SkillRule(trigger="battle_start", action=grant_sigma),
        SkillRule(trigger="full_burst_enter", action=spend_sigma,
                  condition=has_status(METAL_SIGMA_STATUS)),
        # "Activates if the skill user has cast Burst Skill before Full Burst
        # ends" - settled at the window's end, so it can only pay the NEXT one.
        SkillRule(trigger="full_burst_end", action=grant_sigma,
                  condition=own_burst_fired_this_cycle()),
    ]


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
