"""SkillRule encoding of Rosanna: Chic Ocean (slug "rosanna-chic-ocean",
lootandwaifus.com). Wind, Burst 2, Assault Rifle, Supporter.

Modeled (DPS-relevant):
- Ferita (Skill 1, at start of battle): squad Damage to Parts +24.26% for 15 sec.
- Onda Grande (Burst): squad Sustained Damage +20.32% and squad enemy Damage
  Taken +32.23%, both for 10 sec. The Damage Taken debuff is her clearest,
  biggest support value; the Sustained Damage buff is faithful but only moves
  damage when the deck also has a sustained-damage dealer (see damage typing) -
  her own sustained source (Spina di Rosa) is deferred below.

Not modeled / deferred:
- Ferita's second clause: "when an ally or self destroys an enemy's part, ATK
  +3% of caster's ATK, stacks up to 5, 30 sec" - needs a part-destroy trigger
  (doesn't exist) plus stack tracking. Deferred.
- Spina di Rosa (Skill 2) entirely: it is a separate active skill on a 30-sec
  cooldown that (a) refreshes the squad Damage to Parts +24.26% for 15 sec and
  (b) deals 70.4% of final ATK as sustained damage every 1 sec for 15 sec to the
  nearest enemy. Neither piece is schedulable: there's no trigger to fire the
  buff, and periodic_nukes assumes a continuous fixed interval, not this skill's
  15s-on / 15s-off duty cycle (15 ticks per 30-sec cycle) - modeling it as a
  plain periodic nuke would roughly double its damage. Because Spina is her only
  sustained-damage instance, her own Sustained Damage buff has nothing to boost
  in a Rosanna-only deck until this is modeled.
"""
from app.skill_rules._helpers import buff_rule
from app.squad_engine import SkillRule


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
