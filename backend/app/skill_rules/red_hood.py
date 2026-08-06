"""Red Hood (slug "red-hood"), a Burst-3 Iron Sniper Rifle attacker. PARTIAL.

Re-verified 2026-07-18: the old "Pattern B, charge-speed gauge = not damage"
verdict predates Phase S wiring `charge_speed_percent` into the firing
cadence - charge speed IS a DPS stat now. Her burst's "Step 1/2/3" is NOT a
state machine: it's which burst-stage slot she is used in (she can burst at
any stage). This engine pins her at burst_tier 3, so only the Step 3 (Red
Wolf) branch ever fires; the Step 1/2 branches and their once-per-battle
-40s cooldown tricks are unreachable by construction, not deferred.

Modeled (DPS-relevant):
- Glaring Eyes (skills[0]): Charge Speed +3.81% per normal attack, 10-stack
  cap, 5s lifetime. Her SR cadence (1.0s charge, 2.0s reload) never lets the
  counter's refreshed lifetime lapse (Raven counter precedent), so the fight
  settles at 10 stacks within the first ~10 shots -> modeled as a continuous
  battle_start self buff of +38.1% (settling ramp is negligible over 180s,
  Fienn approved 2026-07-18).
- Wild Tooth (skills[1]): "when casting Red Wolf" self ATK +71.42% for 10s
  -> own_burst_activate.
- Red Wolf Step 3 weapon transform (burst): modeled from Fienn's in-game
  measurement (2026-07-18): the transform window fires exactly 33 shots over
  its 10s duration with an infinite magazine (no reloads), and charge time
  never reaches 0 even above +100% charge speed (a minimum shot gap exists).
  Modeled as a weapon-mode segment (see attack_rate.generate_segmented_shots):
  a 10s window, starting at each own-burst, that silences her base SR and
  fires a `rate_of_fire=33/10=3.3` profile instead - a measurement anchor, so
  (per attack_rate's contract) it takes no cadence buffs; the 33-shot count
  IS the +100.8% Charge Speed already baked in. Per-shot damage_percent is
  51.46% (shot_percent); charge_damage_percent is 250% full charge +
  93.36%p Glaring Eyes conversion, folded once at build time. The conversion
  itself - Charge Speed excess over 100% x 240% -> Charge Damage (skill text;
  excess = 38.1 + 100.8 - 100 = 38.9) - stays own-sources-only (steady stacks
  + this window's own +100.8%, not deck charge-speed buffers), per Fienn's
  semantics (2026-07-18). Unlike the old scheduled_nukes model, the segment
  window genuinely silences the base SR (no more double-counted/subtracted
  overlap), and the profile's charge_damage_percent rides through the same
  extra_charge_bonus path a normal charge-weapon shot uses - so a deck's
  Charge Damage / ATK buffs now multiply these shots like any other normal
  attack.

- Wild Tooth's "Gain Pierce continuously": the `has_pierce` property from
  battle start, which is what makes any Pierce Damage buff worth anything to
  her.

Not modeled / deferred:
- Beast Cage's squad DEF and The Last Howl's healing - survival stats, and on
  burst-step branches this engine never reaches anyway (see above).
- Red Wolf's "Expand Pierce range by 100%": the engine models no pierce RANGE
  (only the property and the damage bucket).

Numbers sourced from data/dotgg/char_red-hood.json for the weapon profile
(SR, 69.04% damage, 250% charge damage, 6 rounds, 2.0s reload, 1.0s charge)
and lootandwaifus for skill values.
"""
from app.skill_rules._helpers import buff_rule

SKILL_VALUE_MANIFESTS = {
    "red-hood": {
        "source": "lootandwaifus",
        "test_module": "test_skill_rules_red_hood",
        "keys": {
            "glaring_eyes": ("skills", 0),
            "wild_tooth": ("skills", 1),
            "red_wolf": ("skills", 2),
        },
    },
}

# Fienn's in-game measurement (2026-07-18): 33 shots across the 10s transform
# window, infinite magazine, no reloads.
TRANSFORM_SHOTS = 33


def _steady_charge_speed(glaring):
    return float(glaring["description_value_01"]) / 100 * float(glaring["description_value_02"])


def build_red_hood_rules(values):
    glaring = values["glaring_eyes"]
    wild_tooth = values["wild_tooth"]
    steady = _steady_charge_speed(glaring)
    red_wolf_atk = float(wild_tooth["description_value_05"]) / 100
    red_wolf_atk_duration = float(wild_tooth["description_value_06"])

    return [
        buff_rule("battle_start", [
            ("charge_speed_percent", steady, "self", None),
            # Wild Tooth: "Gain Pierce continuously" - the property, which is
            # what makes any Pierce Damage buff worth anything to her.
            ("has_pierce", 1.0, "self", None),
        ]),
        buff_rule("own_burst_activate", [("atk_percent", red_wolf_atk, "self", red_wolf_atk_duration)]),
    ]


def build_red_wolf_weapon_mode_schedule(values):
    glaring = values["glaring_eyes"]
    red_wolf = values["red_wolf"]
    shot_percent = float(red_wolf["description_value_11"])
    full_charge_percent = float(red_wolf["description_value_12"])   # 250
    duration = float(red_wolf["description_value_13"])              # 10
    window_charge_speed = float(red_wolf["description_value_16"]) / 100
    steady = _steady_charge_speed(glaring)
    threshold = float(glaring["description_value_04"]) / 100
    rate = float(glaring["description_value_05"]) / 100
    converted = (steady + window_charge_speed - threshold) * rate   # 0.9336
    profile = {
        "weapon": "SR",
        "damage_percent": shot_percent,
        # A collectible's charge-damage 배율 scales the transformed weapon's own
        # full-charge multiplier only. Glaring's conversion arrives as a
        # "Charge Damage ▲" BUFF, and Fienn measured (2026-08-03) that the 배율
        # does not reach charge-damage buffs - ratio-of-ratios 2.9292601 against
        # a 2.9292957 prediction, with "buffs scale too" 6.24% away. Same split
        # snow_white_heavy_arms makes between weapon_stats and its skill term.
        "charge_damage_percent": (
            full_charge_percent * values.get("caster_charge_damage_multiplier", 1.0)
            + converted * 100),
        "rate_of_fire": TRANSFORM_SHOTS / duration,
    }

    def schedule(context, fight_duration):
        return [
            {"start": t, "until_shots": TRANSFORM_SHOTS, "profile": profile}
            for t in context.burst_times.get("red-hood", [])
        ]

    return schedule
