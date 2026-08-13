"""Maxwell (slug "maxwell"), a Burst-3 Iron SR attacker (Matis, burst cd 40s,
no signature weapon - base skills only).

Modeled (DPS-relevant):
- Straight Shot (skills[0], on entering Full Burst): Charge Speed +4.48% and
  ATK +43.1% for 10 sec to the 2 allies with the highest final ATK. Fienn's
  ruling (2026-07-19): Maxwell's "2 allies with the highest final ATK" includes
  Maxwell HERSELF in the ranking pool from the start, because the bullet has no
  "except caster" clause. That generalized on 2026-08-08 - the absence of the
  clause is the marker, and its presence (Miranda, Mana, Soda) is what asks for
  exclusion - so `top_atk_slugs` grew an `include_caster` flag and this module's
  hand-rolled `_top_final_atk_slugs` was deleted in favour of
  `highest_atk_buff_rule(..., include_caster=True)`. Keeping a second copy of
  the final-ATK formula was a standing risk of the two drifting apart.
  Charge Speed is a real DPS stat (see red-hood.py's Phase-S re-verification -
  it feeds the firing cadence now), so it's encoded like ATK.
- Pierce Shot (her burst, skills[2]): the weapon transform - self weapon
  becomes a 2s-charge, 1-round cannon: 813.42% of final ATK per shot, 300%
  Full Charge Damage. Modeled as a `weapon_mode_schedules` segment
  (`until_shots: 1`), same shape as Snow White's Seven Dwarves: I / Red
  Hood's Red Wolf transform. No direct burst nuke - the transform's own shot
  IS the burst's damage.

Not modeled / deferred:
- Spark Shot (skills[1]): "Activates when there are above 5 enemy units,
  excluding Nikkes" - this engine's raid sims are always a single boss, so
  the condition is always false and the skill never fires. Left entirely out
  of build_maxwell_rules (not wired to any trigger) rather than approximated
  onto a trigger that would misrepresent it - there's no "enemy count"
  primitive to gate it on anyway.
(Pierce Shot's "Additional Effect: Pierce" is NOT deferred: the engine holds
the pierce property itself as `has_pierce`, distinct from the `pierce_damage_up`
bucket, and build_maxwell_rules grants it for the transform's duration.)

Numbers sourced from data/lootandwaifus/char_maxwell.json (skill values);
dotgg's char_maxwell.json weapon block (SR, 69.04% damage, 250% charge
damage, 6 rounds, 2.0s reload, 1.0s charge) confirms she has no signature
weapon, unused directly here since the transform profile is self-contained.
"""
from app.skill_rules._helpers import highest_atk_buff_rule, round_buff_rule

SKILL_VALUE_MANIFESTS = {
    "maxwell": {
        "source": "lootandwaifus",
        "test_module": "test_skill_rules_maxwell",
        "keys": {
            "straight_shot": ("skills", 0),
            "pierce_shot": ("skills", 2),
        },
    },
}


def build_maxwell_rules(values):
    straight = values["straight_shot"]
    n = int(float(straight["description_value_01"]))
    charge_speed = float(straight["description_value_02"]) / 100
    charge_speed_duration = float(straight["description_value_03"])
    atk = float(straight["description_value_04"]) / 100
    atk_duration = float(straight["description_value_05"])

    return [
        highest_atk_buff_rule("full_burst_enter", n, [
            ("charge_speed_percent", charge_speed, charge_speed_duration),
            ("atk_percent", atk, atk_duration),
        ], include_caster=True),
        # Pierce shot's "Additional Effect: Pierce" - the transform is one
        # charged shot, so the property covers exactly that round.
        round_buff_rule("own_burst_activate", [("has_pierce", 1.0, "self")], shots=1),
    ]


def build_pierce_shot_weapon_mode_schedule(values):
    pierce = values["pierce_shot"]
    # The transformed weapon's full-charge multiplier is wholly a skill value:
    # no term here comes from weapon_stats, which is where a collectible's
    # charge-damage 배율 is applied. So the 배율 has to be applied here to reach
    # this profile at all - Fienn measured 2026-08-03 that it does reach it
    # (docs/measurements/collectible-charge-damage-in-transform.md).
    profile = {
        "weapon": "SR",
        "damage_percent": float(pierce["description_value_02"]),
        "charge_damage_percent": (
            float(pierce["description_value_03"])
            * values.get("caster_charge_damage_multiplier", 1.0)),
        "charge_time": float(pierce["description_value_01"]),
    }

    def schedule(context, fight_duration):
        return [{"start": t, "until_shots": 1, "profile": profile}
                for t in context.burst_times.get("maxwell", [])]

    return schedule
