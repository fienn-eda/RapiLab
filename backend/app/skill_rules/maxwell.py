"""Maxwell (slug "maxwell"), a Burst-3 Iron SR attacker (Matis, burst cd 40s,
no signature weapon - base skills only).

Modeled (DPS-relevant):
- Straight Shot (skills[0], on entering Full Burst): Charge Speed +4.48% and
  ATK +43.1% for 10 sec to the 2 allies with the highest final ATK. Fienn's
  ruling (2026-07-19): unlike the shared `highest_atk_buff_rule` /
  `SquadContext.top_atk_slugs` helper - which always EXCLUDES the caster and
  only falls back to including her when there aren't enough OTHER allies -
  Maxwell's "2 allies with the highest final ATK" includes Maxwell HERSELF in
  the ranking pool from the start. A local `_top_final_atk_slugs` ranks every
  squad member (caster included) by the same final-ATK formula
  `top_atk_slugs` uses, and the top 2 are buffed via a `slugs:` scope Effect.
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
- Pierce Shot's "Additional Effect: Pierce": the pierce property has no
  engine representation (same as Red Hood's Wild Tooth/Red Wolf Pierce,
  Snow White's Seven Dwarves: I - pierce_damage_up is a damage bucket, not
  the property itself).

Numbers sourced from data/lootandwaifus/char_maxwell.json (skill values);
dotgg's char_maxwell.json weapon block (SR, 69.04% damage, 250% charge
damage, 6 rounds, 2.0s reload, 1.0s charge) confirms she has no signature
weapon, unused directly here since the transform profile is self-contained.
"""
from app.effects import Effect
from app.skill_rules._helpers import round_buff_rule
from app.squad_engine import SkillRule

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


def _top_final_atk_slugs(context, registry, n, time):
    """The `n` squad members with the highest final ATK at `time`, WITHOUT
    excluding the caster (Fienn's ruling, 2026-07-19 - see module docstring).
    Final ATK computed the same way as SquadContext.top_atk_slugs: base ATK
    grown by live atk_percent buffs plus flat_atk. Ties break by deck order
    (stable sort)."""
    by_slug = {m.slug: m for m in context.members}

    def final_atk(slug):
        target = {"slug": slug, "element": by_slug[slug].element}
        base = context.base_atk.get(slug, 0.0)
        return base * (1 + registry.total_for("atk_percent", target, time)) + registry.total_for(
            "flat_atk", target, time
        )

    ranked = sorted(by_slug, key=final_atk, reverse=True)
    return ranked[:n]


def _straight_shot_rule(n, buffs):
    """buffs: list of (stat, value, duration), applied to the `n` allies
    (caster included) with the highest final ATK - see _top_final_atk_slugs."""

    def action(context, caster_slug, time, registry):
        scope = "slugs:" + ",".join(_top_final_atk_slugs(context, registry, n, time))
        for stat, value, duration in buffs:
            registry.add(Effect(stat, value, scope, duration, caster_slug), applied_at=time)

    return SkillRule(trigger="full_burst_enter", action=action)


def build_maxwell_rules(values):
    straight = values["straight_shot"]
    n = int(float(straight["description_value_01"]))
    charge_speed = float(straight["description_value_02"]) / 100
    charge_speed_duration = float(straight["description_value_03"])
    atk = float(straight["description_value_04"]) / 100
    atk_duration = float(straight["description_value_05"])

    return [
        _straight_shot_rule(n, [
            ("charge_speed_percent", charge_speed, charge_speed_duration),
            ("atk_percent", atk, atk_duration),
        ]),
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
