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
  Modeled as `scheduled_nukes`: 33 evenly spaced hits per own-burst window.
  Per-hit percent is measurement-anchored NET damage:
    gross = 51.46% x (250% full charge + 93.36%p converted charge damage)
    minus the double-counted normal shots the engine's weapon pass still
    emits inside the window (static steady-state estimate: 10s of SR fire at
    +38.1% charge speed = ~9.46 shots x 69.04% x 2.5), spread over the 33
    hits. The 93.36%p is Glaring Eyes' conversion: Charge Speed excess over
    100% x 240% -> Charge Damage (skill text; excess = 38.1 + 100.8 - 100 =
    38.9, own sources only - deck charge-speed buffers are NOT folded into
    the conversion, and the transform window's +100.8% Charge Speed is baked
    into the measured 33-shot cadence rather than applied as an engine buff).

Not modeled / deferred:
- Squad charge-damage/ATK buffs multiplying the transform shots' folded
  charge multiplier: the scheduled-nuke path has no charge-bonus bucket, so
  the 250%+93.36%p is a constant - a deck's Charge Damage buffers boost her
  engine-emitted normal shots but not the folded transform constant.
- Wild Tooth's "Gain Pierce continuously": the pierce property itself has no
  engine representation (pierce_damage_up is a damage bucket, not the
  property); Beast Cage squad DEF and Last Howl healing are survival stats
  on unreachable branches anyway.
- Red Wolf's "Expand Pierce range by 100%": no pierce/range model.

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

# Her own SR weapon profile (data/dotgg/char_red-hood.json), used for the
# static overlap subtraction - the engine's weapon pass keeps firing these
# shots inside the transform window and they must not be double-counted.
_SR_DAMAGE_PERCENT = 69.04
_SR_CHARGE_MULTIPLIER = 2.5
_SR_MAX_AMMO = 6
_SR_RELOAD_TIME = 2.0
_SR_CHARGE_TIME = 1.0


def _steady_charge_speed(glaring):
    return float(glaring["description_value_01"]) / 100 * float(glaring["description_value_02"])


def build_red_hood_rules(values):
    glaring = values["glaring_eyes"]
    wild_tooth = values["wild_tooth"]
    steady = _steady_charge_speed(glaring)
    red_wolf_atk = float(wild_tooth["description_value_05"]) / 100
    red_wolf_atk_duration = float(wild_tooth["description_value_06"])

    return [
        buff_rule("battle_start", [("charge_speed_percent", steady, "self", None)]),
        buff_rule("own_burst_activate", [("atk_percent", red_wolf_atk, "self", red_wolf_atk_duration)]),
    ]


def build_red_wolf_scheduled_nukes(values):
    glaring = values["glaring_eyes"]
    red_wolf = values["red_wolf"]

    shot_percent = float(red_wolf["description_value_11"])
    full_charge = float(red_wolf["description_value_12"]) / 100
    duration = float(red_wolf["description_value_13"])
    window_charge_speed = float(red_wolf["description_value_16"]) / 100

    # Glaring Eyes' conversion: Charge Speed excess over the threshold x rate
    # -> Charge Damage. Own sources only (steady stacks + the transform buff).
    steady = _steady_charge_speed(glaring)
    threshold = float(glaring["description_value_04"]) / 100
    rate = float(glaring["description_value_05"]) / 100
    converted_charge_damage = (steady + window_charge_speed - threshold) * rate

    gross_per_hit = shot_percent * (full_charge + converted_charge_damage)

    # Static overlap: normal SR shots the weapon pass emits inside the window
    # at her steady +38.1% charge speed (see module docstring).
    effective_charge = _SR_CHARGE_TIME / (1 + steady)
    magazine_cycle = _SR_MAX_AMMO * effective_charge + _SR_RELOAD_TIME
    overlap_shots = duration * _SR_MAX_AMMO / magazine_cycle
    overlap_damage = overlap_shots * _SR_DAMAGE_PERCENT * _SR_CHARGE_MULTIPLIER

    net_per_hit = (TRANSFORM_SHOTS * gross_per_hit - overlap_damage) / TRANSFORM_SHOTS
    interval = duration / TRANSFORM_SHOTS

    def schedule(context, fight_duration):
        times = []
        for burst_time in context.burst_times.get("red-hood", []):
            for k in range(1, TRANSFORM_SHOTS + 1):
                hit_time = burst_time + k * interval
                if hit_time < fight_duration:
                    times.append(hit_time)
        return times

    return [{"schedule": schedule, "percent": net_per_hit}]
