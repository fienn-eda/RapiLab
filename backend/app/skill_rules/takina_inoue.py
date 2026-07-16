"""SkillRule encoding of Takina Inoue (slug "takina-inoue", lootandwaifus.com).
Iron, Burst 2, Sniper Rifle, Supporter.

Modeled (DPS-relevant):
- Combat Support (Skill 1): self ATK +80.04% for 5 sec on battle start AND on
  Full Burst end; self True Damage +35.05% for 15 sec on entering Full Burst.
- Battlefield Control (Skill 2, cooldown 15 sec): squad enemy Damage Taken
  +10.09% for 5 sec and squad ally True Damage +140.49% for 10 sec. This is her
  headline support. It is a periodic skill on its own 15-sec cooldown, so it
  first fires at t=15 and repeats - fired via the engine's `periodic_rules`
  (see raid_simulator), NOT one of the four event triggers. The rules are
  labeled trigger="periodic" (a label; they're never dispatched by fire_trigger).
- Suppression Initiated (Burst): converts her normal attacks to True Damage for
  10 sec (a self `normal_attacks_deal_true` effect the normal-attack pass reads
  - see damage typing), so during her burst her SR shots benefit from the True
  Damage buffs above. Plus an on-hit enemy Damage Taken +6.04% debuff.

Her True Damage buffs (self 35% + squad 140%) only move damage when the deck
produces a True-Damage instance: she herself contributes it during her 10-sec
burst window (via the conversion), and any other true-damage dealer benefits.

Not modeled / deferred:
- Battlefield Control's 2-sec stun (no consumer).
- Suppression Initiated's weapon transformation ("Changes the weapon in use.
  Damage: 200.64% of final ATK. Duration: 10 sec") - weapon transformation isn't
  modeled, and the text is ambiguous whether 200.64% is a one-time nuke or the
  transformed weapon's per-shot damage, so it's deferred rather than guessed
  (she's a supporter, so her personal damage is secondary). burst_percent=None.
- The burst's on-hit Damage Taken +6.04% is "Affects targets hit for 5 sec";
  modeled as a squad enemy debuff for the 10-sec burst window (against a boss,
  "targets hit" is the boss, and she fires throughout the transform) - an
  approximation, documented here.
"""
from app.skill_rules._helpers import buff_rule
from app.squad_engine import SkillRule


SKILL_VALUE_MANIFESTS = {
    "takina-inoue": {
        "source": "lootandwaifus",
        "dotgg_slug": "takina",
        "test_module": "test_skill_rules_takina_inoue",
        "keys": {
            "combat_support": ("skills", 0),
            "battlefield_control": ("skills", 1),
            "suppression_initiated": ("skills", 2),
        },
        "drop_tokens": {
            "battlefield_control": [2],
            "suppression_initiated": [2],
        },
    },
}


BATTLEFIELD_CONTROL_COOLDOWN = 15.0  # skill text: Skill 2 cooldown 15s


def build_combat_support_rules(values: dict) -> list[SkillRule]:
    self_atk = float(values["description_value_01"]) / 100
    self_atk_duration = float(values["description_value_02"])
    self_true = float(values["description_value_03"]) / 100
    self_true_duration = float(values["description_value_04"])

    atk_buff = [("atk_percent", self_atk, "self", self_atk_duration)]
    return [
        buff_rule("battle_start", atk_buff),
        buff_rule("full_burst_end", atk_buff),
        buff_rule("full_burst_enter", [("true_damage_up", self_true, "self", self_true_duration)]),
    ]


def build_battlefield_control_rules(values: dict) -> list[SkillRule]:
    """Periodic rules (own 15-sec cooldown) - fired via raid_simulator's
    periodic_rules, not by an event trigger. trigger="periodic" is a label."""
    damage_taken = float(values["description_value_01"]) / 100
    damage_taken_duration = float(values["description_value_02"])
    ally_true = float(values["description_value_03"]) / 100
    ally_true_duration = float(values["description_value_04"])

    return [
        buff_rule("periodic", [
            ("damage_taken_up", damage_taken, "squad", damage_taken_duration),
            ("true_damage_up", ally_true, "squad", ally_true_duration),
        ]),
    ]


def build_suppression_initiated_rules(values: dict) -> list[SkillRule]:
    window = float(values["description_value_02"])  # transform / true-conversion window (10s)
    on_hit_damage_taken = float(values["description_value_03"]) / 100

    return [
        buff_rule("own_burst_activate", [
            ("normal_attacks_deal_true", 1.0, "self", window),
            ("damage_taken_up", on_hit_damage_taken, "squad", window),
        ]),
    ]
