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
- Journey Ahead (skills[1]) nuke: 675% of final ATK every 5 normal attacks,
  modeled via the per-shot trigger (`per_shot_rules`, mode "every") - see
  `build_journey_ahead_rules`. Likely a bigger DPS lever than Ignition
  Sequence's flat 636%.
- Full Throttle (skills[2], her burst): ATK % of caster's ATK to "all allies
  except self" - the engine has no "squad except self" scope, so approximated
  as squad (per the encoding skill's documented approximation pattern); Brid
  herself also incorrectly picks up her own buff, a small self-only
  overstatement.

Not modeled:
- Ignition Sequence's and Journey Ahead's Wind-Code Damage Taken debuffs (every
  Full Burst / every 10 normal attacks): both gate on the enemy being Wind Code.
  Skill-rule actions have no access to the boss's element (only `raid_simulator`
  does), so a boss-element-conditional debuff can't be gated correctly; applying
  it unconditionally would be wrong against non-Wind bosses. For Journey Ahead
  the per-shot COUNT part is now supported - only the Wind-Code gating isn't.
  Flag to Fienn if this needs supporting (would need threading boss_element into
  SkillRule actions).
"""
from app.effects import Effect
from app.skill_rules._helpers import instant_nuke_pulse_rule
from app.squad_engine import SkillRule

JOURNEY_AHEAD_NUKE_SHOT_COUNT = 5  # skill text: "after 5 normal attacks"


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


def build_journey_ahead_rules(values):
    """Per-shot rules (see raid_simulator's `per_shot_rules`): every 5 normal
    attacks, deal 675% of final ATK. The Wind-Code Damage Taken debuff (every 10
    normal attacks) is deferred - boss-element gate not representable."""
    nuke_percent = float(values["description_value_03"])
    return [
        (JOURNEY_AHEAD_NUKE_SHOT_COUNT, "every", [instant_nuke_pulse_rule("per_shot", nuke_percent)]),
    ]
