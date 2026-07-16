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
- Ignition Sequence's Wind-Code Damage Taken debuff: on Full Burst enter, +15.12%
  Damage Taken for 10 sec against a Wind Code boss (squad-scope enemy debuff,
  gated on `boss_is_element("Wind")` - a solo raid has one boss, so "all Wind Code
  enemies" is just the boss when it's Wind).
- Journey Ahead (skills[1]) nuke: 675% of final ATK every 5 normal attacks,
  modeled via the per-shot trigger (`per_shot_rules`, mode "every") - see
  `build_journey_ahead_rules`. Likely a bigger DPS lever than Ignition
  Sequence's flat 636%.
- Journey Ahead's Wind-Code Damage Taken debuff: every 10 normal attacks,
  +12.12% Damage Taken for 10 sec against a Wind Code boss (refreshing per-shot
  buff, gated on `boss_is_element("Wind")`).
- Full Throttle (skills[2], her burst): ATK % of caster's ATK to "all allies
  except self" - the engine has no "squad except self" scope, so approximated
  as squad (per the encoding skill's documented approximation pattern); Brid
  herself also incorrectly picks up her own buff, a small self-only
  overstatement.

Not modeled: none - both Wind-Code debuffs are now representable via the
boss_element gate (gap #5).
"""
from app.effects import Effect
from app.skill_rules._helpers import buff_rule, instant_nuke_pulse_rule, refreshing_buff_rule
from app.squad_engine import SkillRule, boss_is_element

SKILL_VALUE_MANIFESTS = {
    "brid-silent-track": {
        "source": "dotgg",
        "test_module": "test_skill_rules_brid",
        "keys": {
            "ignition_sequence": ("skills", 0),
            "journey_ahead": ("skills", 1),
            "full_throttle": ("skills", 2),
        },
        # Journey Ahead was transcribed with the "after 10/5 normal attack(s)"
        # thresholds and "1 enemy unit(s)" counts skipped (native slots
        # 01/02/05/06); the builder reads the compacted 01..03 numbering.
        "drop_tokens": {"journey_ahead": [0, 1, 4, 5]},
    },
}

JOURNEY_AHEAD_NUKE_SHOT_COUNT = 5  # skill text: "after 5 normal attacks"
JOURNEY_AHEAD_DEBUFF_SHOT_COUNT = 10  # skill text: "after 10 normal attacks"
WIND = "Wind"  # both Damage Taken debuffs gate on a Wind Code boss


def build_brid_rules(values):
    ignition = values["ignition_sequence"]
    full_throttle = values["full_throttle"]

    nuke_percent = float(ignition["description_value_03"])
    wind_debuff = float(ignition["description_value_01"]) / 100
    wind_debuff_duration = float(ignition["description_value_02"])
    ally_atk = float(full_throttle["description_value_01"]) / 100 * values["caster_atk"]
    ally_atk_duration = float(full_throttle["description_value_02"])

    def apply_full_throttle(context, caster_slug, time, registry):
        registry.add(Effect("flat_atk", ally_atk, "squad", ally_atk_duration, caster_slug), applied_at=time)

    return [
        instant_nuke_pulse_rule("full_burst_enter", nuke_percent),
        buff_rule(
            "full_burst_enter",
            [("damage_taken_up", wind_debuff, "squad", wind_debuff_duration)],
            condition=boss_is_element(WIND),
        ),
        SkillRule(trigger="own_burst_activate", action=apply_full_throttle),
    ]


def build_journey_ahead_rules(values):
    """Per-shot rules (see raid_simulator's `per_shot_rules`): every 5 normal
    attacks, deal 675% of final ATK; every 10 normal attacks, apply a +12.12%
    Wind-Code Damage Taken debuff (gated on a Wind Code boss, refreshing since it
    re-applies faster than its 10-sec window)."""
    nuke_percent = float(values["description_value_03"])
    wind_debuff = float(values["description_value_01"]) / 100
    wind_debuff_duration = float(values["description_value_02"])
    return [
        (JOURNEY_AHEAD_NUKE_SHOT_COUNT, "every", [instant_nuke_pulse_rule("per_shot", nuke_percent)]),
        (
            JOURNEY_AHEAD_DEBUFF_SHOT_COUNT,
            "every",
            [refreshing_buff_rule(
                "per_shot",
                [("damage_taken_up", wind_debuff, "squad", wind_debuff_duration)],
                condition=boss_is_element(WIND),
            )],
        ),
    ]
