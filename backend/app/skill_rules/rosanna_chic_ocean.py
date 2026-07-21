"""SkillRule encoding of Rosanna: Chic Ocean (slug "rosanna-chic-ocean",
lootandwaifus.com). Wind, Burst 2, Assault Rifle, Supporter.

Modeled (DPS-relevant):
- Ferita (Skill 1, at start of battle): squad Damage to Parts +24.26% for 15 sec.
- Spina di Rosa (Skill 2, cd 30 sec), both clauses:
  - squad Damage to Parts +24.26% for 15 sec, on `periodic_rules`.
  - 70.4% of final ATK as sustained damage every 1 sec for 15 sec, on
    `scheduled_nukes`. The 15s-on / 15s-off duty cycle its own cooldown implies
    is what a plain `periodic_nukes` entry could not express (it assumes a
    continuous fixed interval and would have doubled the damage); a schedule
    callback emitting 15 ticks per cast states the real timeline instead.
    5 casts x 15 ticks = 5280% of final ATK over a 180 sec fight.
  Both fire at t=30/60/90/120/150: Spina carries no battle-start force-fire (cf.
  Sakura's Bloom, which does), so it first fires at its own cooldown per the
  universal rule in docs/decisions.md ("Periodic skill trigger").
- Onda Grande (Burst): squad Sustained Damage +20.32% and squad enemy Damage
  Taken +32.23%, both for 10 sec. The Damage Taken debuff is her clearest,
  biggest support value; the Sustained Damage buff now has one of her own DoTs
  to boost as well as any allied sustained dealer.

Not modeled / deferred:
- Ferita's second clause: "when an ally or self destroys an enemy's part, ATK
  +3% of caster's ATK, stacks up to 5, 30 sec" - needs a part-destroy trigger
  (engine-gaps.md gap #2 Pattern B) plus stack tracking. Deferred; it would only
  ADD damage, so this encoding is a floor.
- "Affects the enemy nearest to the crosshair" is the solo raid's only boss, so
  the DoT's targeting needs no modeling.
"""
from app.skill_rules._helpers import buff_rule
from app.squad_engine import SkillRule

# Spina di Rosa's own cooldown. It has no battle-start force-fire, so this is
# also when it first casts.
SPINA_COOLDOWN = 30.0


SKILL_VALUE_MANIFESTS = {
    "rosanna-chic-ocean": {
        "source": "lootandwaifus",
        "test_module": "test_skill_rules_rosanna_chic_ocean",
        "keys": {
            "ferita": ("skills", 0),
            "spina_di_rosa": ("skills", 1),
            "onda_grande": ("skills", 2),
        },
    },
}


def build_rosanna_rules(values: dict) -> list[SkillRule]:
    ferita = values["ferita"]
    parts = float(ferita["description_value_01"]) / 100
    parts_duration = float(ferita["description_value_02"])

    onda = values["onda_grande"]
    sustained = float(onda["description_value_01"]) / 100
    sustained_duration = float(onda["description_value_02"])
    damage_taken = float(onda["description_value_03"]) / 100
    damage_taken_duration = float(onda["description_value_04"])

    return [
        buff_rule("battle_start", [("damage_to_parts_up", parts, "squad", parts_duration)]),
        buff_rule("own_burst_activate", [
            ("sustained_damage_up", sustained, "squad", sustained_duration),
            ("damage_taken_up", damage_taken, "squad", damage_taken_duration),
        ]),
    ]


def _spina_cast_times(fight_duration):
    """t=30, 60, ... - Spina's own cooldown, with no cast at t=0."""
    times, t = [], SPINA_COOLDOWN
    while t < fight_duration:
        times.append(t)
        t += SPINA_COOLDOWN
    return times


def build_spina_periodic_rules(values: dict):
    """Spina di Rosa's squad buff half. Same (stat, scope, value) as Ferita's
    battle-start buff, but the two windows never overlap - Ferita covers
    [0, 15) and the first Spina cast lands at t=30 - so they neither stack nor
    need to refresh each other."""
    spina = values["spina_di_rosa"]
    parts = float(spina["description_value_01"]) / 100
    duration = float(spina["description_value_02"])
    return [(SPINA_COOLDOWN, [
        buff_rule("periodic", [("damage_to_parts_up", parts, "squad", duration)]),
    ])]


def build_spina_scheduled_nukes(values: dict):
    """Spina di Rosa's DoT half: `duration / interval` ticks per cast, on a
    timeline fixed by the cooldown alone, so the schedule reads nothing off the
    context (the Sakura Petals shape)."""
    spina = values["spina_di_rosa"]
    percent = float(spina["description_value_03"])
    interval = float(spina["description_value_04"])
    duration = float(spina["description_value_05"])
    tick_count = int(duration / interval)

    def schedule(context, fight_duration):
        return [
            tick
            for cast in _spina_cast_times(fight_duration)
            for n in range(1, tick_count + 1)
            if (tick := cast + interval * n) < fight_duration
        ]

    return [{"schedule": schedule, "percent": percent, "damage_type": "sustained"}]
