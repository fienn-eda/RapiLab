"""Snow White (slug "snow-white"), a Burst-3 Iron AR attacker (Pilgrim, burst
cd 40s, no signature weapon - base skills only). Her burst swaps her AR for a
single-shot 5s-charge cannon; second consumer of `weapon_mode_schedules` (the
gap #10-adjacent transform-window primitive, red-hood precedent), but her
window is a single measured shot rather than a rate_of_fire anchor.

Modeled (DPS-relevant):
- Determination (skills[0]): every 30th normal-attack hit, deals 82.8% of
  final ATK "as additional damage" to the target (`per_shot_rules`' "every"
  mode, full_burst_bonus_eligible=True) and grants self ATK +8.28% for 5 sec.
- Seven Dwarves: V & VI (skills[1]): a periodic AoE nuke on its own 15s
  cooldown, independent of the burst cycle - 144.73% of final ATK
  (`get_periodic_nuke`).
- Seven Dwarves: I (skills[2], her burst): the weapon transform - self weapon
  becomes a 5s-charge, 1-round cannon: 499.5% of final ATK per shot, 1000%
  Full Charge Damage. Modeled as a `weapon_mode_schedules` segment
  (`until_shots: 1`) at each own-burst time - the transform's single charged
  shot rides the same extra_charge_bonus path a normal charge-weapon shot
  uses, so deck Charge Damage/ATK buffs multiply it like any other charge
  shot.

Not modeled / deferred:
- Seven Dwarves: V & VI's "Critical Rate +26.1% for 10 sec" rider: gated on
  "using this skill during Full Burst," but the periodic-nuke path has no
  window-check primitive (it fires on its own fixed cadence, not through the
  triggered-rule/registry pipeline a condition could hook into) - deferring
  rather than applying it unconditionally, which would overstate her outside
  Full Burst.
- Seven Dwarves: I's "Additional Effect: Pierce": the pierce property has no
  engine representation (same as Red Hood's Wild Tooth/Red Wolf Pierce -
  pierce_damage_up is a damage bucket, not the property itself; the property
  is now carried as `has_pierce`).
- Whether the transform's single shot counts toward Determination's own
  30-hit normal-attack counter: the spec's open question - this engine's
  per-shot loop counts EVERY shot on a unit's unified timeline (including
  weapon-mode segment shots), so as encoded it DOES count. Flag for Fienn to
  confirm; if the transform shot should NOT count, Determination's threshold
  bookkeeping would need a dedicated exclusion this engine doesn't have yet.

Numbers sourced from data/lootandwaifus/char_snow-white.json (skill values)
and dotgg (AR weapon: 14.71% damage, 60 rounds, 1.5s reload - unused directly
here since the transform profile is self-contained, but confirms she has no
signature weapon).
"""
from app.skill_rules._helpers import buff_rule, instant_nuke_pulse_rule, round_buff_rule

SEVEN_DWARVES_V_VI_COOLDOWN = 15.0

SKILL_VALUE_MANIFESTS = {
    "snow-white": {
        "source": "lootandwaifus",
        "test_module": "test_skill_rules_snow_white",
        "keys": {
            "determination": ("skills", 0),
            "seven_dwarves_v_vi": ("skills", 1),
            "seven_dwarves_i": ("skills", 2),
        },
    },
}


def build_snow_white_rules(values):
    # Burst is entirely the weapon-mode transform (Seven Dwarves: I) - no
    # buffs, no direct nuke. Its "Additional Effect: Pierce" is the property,
    # and the transform is one charged shot, so it is a one-round grant.
    return [round_buff_rule("own_burst_activate",
                            [("has_pierce", 1.0, "self")], shots=1)]


def build_determination_per_shot_rules(values):
    det = values["determination"]
    n = int(float(det["description_value_01"]))
    return [(n, "every", [
        instant_nuke_pulse_rule("per_shot", float(det["description_value_02"]),
                                full_burst_bonus_eligible=True),
        buff_rule("per_shot", [("atk_percent", float(det["description_value_04"]) / 100,
                                "self", float(det["description_value_05"]))]),
    ])]


def snow_white_periodic_nuke(values):
    return {"cooldown": SEVEN_DWARVES_V_VI_COOLDOWN,
            "percent": float(values["seven_dwarves_v_vi"]["description_value_01"])}


def build_seven_dwarves_weapon_mode_schedule(values):
    burst = values["seven_dwarves_i"]
    profile = {
        "weapon": "SR",
        "damage_percent": float(burst["description_value_02"]),
        "charge_damage_percent": float(burst["description_value_03"]),
        "charge_time": float(burst["description_value_01"]),
    }

    def schedule(context, fight_duration):
        return [{"start": t, "until_shots": 1, "profile": profile}
                for t in context.burst_times.get("snow-white", [])]

    return schedule
