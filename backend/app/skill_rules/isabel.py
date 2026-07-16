"""Isabel (slug "isabel"), a Burst-3 Electric Shotgun attacker. Base skills.

Modeled (DPS-relevant):
- Marked Target (skills[0]): on each burst a cumulative self-buff tier unlocks
  (1st: Crit Rate, 2nd: Crit Damage, 3rd: ATK), each 45s. Refreshing, since 45s
  exceeds her 40s burst cd (so re-applications would otherwise stack).
- Pointed Feather (skills[1], cd 15s): a self-cooldown nuke, 170.58% of final
  ATK, auto-firing every 15s (periodic_nuke). "5 enemies with the highest final
  DEF" is just the boss in a solo raid.
- Sonic Chaser (skills[2], her burst): burst nuke 149.85%; plus staged bonuses by
  Marked Target stage (= burst number): MT1 (>=1 burst) squad Damage Taken +39.96%
  for 5s; MT2 (>=2) +299.7% additional damage; MT3 (>=3) +349.65% additional
  damage. The additional damages are instant nukes gated on activation_count, so
  they escalate cycle-accurately rather than assuming a steady state.

Assumption: the N-th burst grants Marked Target N (Skill 1) AND applies the
stage-N burst bonus that same cycle (activation_count == N inside the burst rule).

Not modeled: Sonic Chaser's squad Full Burst Duration +5s - a rotation-timing
effect, not a damage buff.
"""
from app.effects import Pulse
from app.skill_rules._helpers import buff_rule, escalating_buff_rule
from app.squad_engine import SkillRule


SKILL_VALUE_MANIFESTS = {
    "isabel": {
        "source": "lootandwaifus",
        "test_module": "test_skill_rules_burst3_eb1",
        "keys": {
            "marked_target": ("skills", 0),
            "pointed_feather": ("skills", 1),
            "sonic_chaser": ("skills", 2),
        },
        "drop_tokens": {
            "marked_target": [0, 3, 6],
            "sonic_chaser": [1, 4, 6],
        },
    },
}


POINTED_FEATHER_COOLDOWN = 15.0


def sonic_chaser_burst_percent(values):
    return float(values["sonic_chaser"]["description_value_01"])


def pointed_feather_percent(values):
    return float(values["pointed_feather"]["description_value_02"])


def build_isabel_rules(values):
    marked = values["marked_target"]
    sonic = values["sonic_chaser"]
    mt1_crit_rate = float(marked["description_value_01"]) / 100
    mt1_duration = float(marked["description_value_02"])
    mt2_crit_damage = float(marked["description_value_03"]) / 100
    mt2_duration = float(marked["description_value_04"])
    mt3_atk = float(marked["description_value_05"]) / 100
    mt3_duration = float(marked["description_value_06"])
    damage_taken = float(sonic["description_value_02"]) / 100
    damage_taken_duration = float(sonic["description_value_03"])
    mt2_additional = float(sonic["description_value_04"])
    mt3_additional = float(sonic["description_value_05"])

    def apply_staged_additional(context, caster_slug, time, registry):
        n = context.activation_count(caster_slug, "own_burst_activate")
        if n >= 2:
            registry.add_pulse(Pulse("instant_damage_percent", mt2_additional, "self", caster_slug))
        if n >= 3:
            registry.add_pulse(Pulse("instant_damage_percent", mt3_additional, "self", caster_slug))

    return [
        escalating_buff_rule("own_burst_activate", [
            [("crit_rate", mt1_crit_rate, "self", mt1_duration)],
            [("other_critical_damage_sources", mt2_crit_damage, "self", mt2_duration)],
            [("atk_percent", mt3_atk, "self", mt3_duration)],
        ], refreshing=True),
        buff_rule("own_burst_activate", [("damage_taken_up", damage_taken, "squad", damage_taken_duration)]),
        SkillRule(trigger="own_burst_activate", action=apply_staged_additional),
    ]
