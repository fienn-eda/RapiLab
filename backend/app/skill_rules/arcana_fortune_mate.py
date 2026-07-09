"""Arcana: Fortune Mate (slug "arcana-fortune-mate"), a Burst-2 Fire SG
attacker. Base skills (no signature weapon).

Modeled (DPS-relevant):
- Radiant Youth (skills[2], her burst): grants herself "Making Memories" -
  Critical Rate + Attack Damage, continuous until Full Burst ends (Keepsake
  Album removes it there) - approximated as lasting the Full Burst window
  (`FULL_BURST_DURATION`). Plus the burst nuke, 554.4% of final ATK
  (`radiant_youth_burst_percent`).
- Memories and Moments (skills[1]): on using her Burst Skill, an Attack Damage
  buff to "all shotgun-wielding allies (except self)" - the engine has no
  weapon-type scope, so approximated as squad (per the encoding skill's
  documented approximation pattern for unrepresentable targeting). This means
  Fortune Mate herself also picks up the buff she wasn't meant to receive - a
  small self-only overstatement.

Not modeled - a self-stacking normal-attack-count chain the engine can't
represent (no normal-attack-count trigger):
- Keepsake Album (skills[0]): its squad ATK buff scales by "stack count of
  Precious Moments", an untracked counter - can't even compute a base value.
- Memories and Moments' own escalating tiers (Two/Four/Six normal attacks:
  reload, pellet count, Precious Moments stacks) and Keepsake Album's
  "Snapshots of Youth" (triggered by Happy Memories) - both attack-count chains.
"""
from app.burst_cycle import FULL_BURST_DURATION
from app.effects import Effect
from app.squad_engine import SkillRule


def radiant_youth_burst_percent(values):
    return float(values["radiant_youth"]["description_value_04"])


def build_fortune_mate_rules(values):
    radiant_youth = values["radiant_youth"]
    memories = values["memories_and_moments"]

    crit_rate = float(radiant_youth["description_value_01"]) / 100
    attack_damage = float(radiant_youth["description_value_03"]) / 100
    ally_attack_damage = float(memories["description_value_06"]) / 100
    ally_attack_damage_duration = float(memories["description_value_07"])

    def apply_radiant_youth(context, caster_slug, time, registry):
        registry.add(
            Effect("crit_rate", crit_rate, "self", FULL_BURST_DURATION, caster_slug), applied_at=time
        )
        registry.add(
            Effect("attack_damage_up", attack_damage, "self", FULL_BURST_DURATION, caster_slug),
            applied_at=time,
        )

    def apply_squad_attack_damage(context, caster_slug, time, registry):
        registry.add(
            Effect("attack_damage_up", ally_attack_damage, "squad", ally_attack_damage_duration, caster_slug),
            applied_at=time,
        )

    return [
        SkillRule(trigger="own_burst_activate", action=apply_radiant_youth),
        SkillRule(trigger="own_burst_activate", action=apply_squad_attack_damage),
    ]
