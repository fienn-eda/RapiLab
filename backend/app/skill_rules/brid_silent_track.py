"""Brid: Silent Track (slug "brid-silent-track"), a Burst-2 Fire SG supporter.
Base skills (no signature weapon).

Her burst (Full Throttle) has no enemy nuke - her real damage comes from
Ignition Sequence, a passive that fires on entering Full Burst regardless of
who bursts, not from her own burst activating. That needed a new engine
capability (`instant_nuke_pulse_rule` / `raid_simulator.drain_instant_damage`)
since the existing burst-nuke path only computes damage when the caster's OWN
burst tier fires - see raid_simulator's module docstring.

Modeled (DPS-relevant):
- Ignition Sequence (skills[0]): on Full Burst enter, an unconditioned instant
  nuke - 636% of final ATK, using `instant_nuke_pulse_rule`.
- Full Throttle (skills[2], her burst): ATK % of caster's ATK to "all allies
  except self" - the engine has no "squad except self" scope, so approximated
  as squad (per the encoding skill's documented approximation pattern); Brid
  herself also incorrectly picks up her own buff, a small self-only
  overstatement.

Not modeled:
- Ignition Sequence's other bullet - a Damage Taken debuff on Wind Code
  enemies specifically. Skill-rule actions have no access to the boss's
  element (only `raid_simulator` does), so a boss-element-conditional debuff
  can't be gated correctly; applying it unconditionally would be wrong against
  non-Wind bosses. Flag to Fienn if this needs supporting (would need threading
  boss_element into SkillRule actions).
- Journey Ahead (skills[1]) entirely - both its bullets trigger "after N normal
  attacks" (no normal-attack-count trigger exists), including a SIZEABLE nuke
  (675% of final ATK every 5 normal attacks) - this is likely a bigger DPS
  lever than Ignition Sequence's flat 636%, so a deck evaluation with Brid
  meaningfully undercounts her until attack-count triggers are supported.
"""
from app.effects import Effect
from app.skill_rules._helpers import instant_nuke_pulse_rule
from app.squad_engine import SkillRule


def build_brid_rules(values):
    ignition = values["ignition_sequence"]
    full_throttle = values["full_throttle"]

    nuke_percent = float(ignition["description_value_03"])
    ally_atk = float(full_throttle["description_value_01"]) / 100 * values["caster_atk"]
    ally_atk_duration = float(full_throttle["description_value_02"])

    def apply_full_throttle(context, caster_slug, time, registry):
        registry.add(Effect("flat_atk", ally_atk, "squad", ally_atk_duration, caster_slug), applied_at=time)

    return [
        instant_nuke_pulse_rule("full_burst_enter", nuke_percent),
        SkillRule(trigger="own_burst_activate", action=apply_full_throttle),
    ]
