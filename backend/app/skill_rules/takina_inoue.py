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
- Suppression Initiated (Burst): transforms her weapon into a rapid-fire mode
  (200.64% of final ATK per shot, 10 sec) whose shots ARE her normal attacks,
  which the same bullet converts to True Damage for the same 10 sec - modeled as
  a `weapon_mode_schedules` segment with its shots pinned to True Damage (see
  `build_suppression_initiated_weapon_mode_schedule`). Plus an on-hit enemy
  Damage Taken +6.04% debuff. burst_percent=None (the transform is her burst
  damage, not a single nuke).

Her True Damage buffs (self 35% + squad 140%) only move damage when the deck
produces a True-Damage instance: she herself contributes it during her 10-sec
burst window (the transform shots are True), and any other true-damage dealer
benefits.

Not modeled / deferred:
- Battlefield Control's 2-sec stun (no consumer).
- The burst's on-hit Damage Taken +6.04% is "Affects targets hit for 5 sec";
  modeled as a squad enemy debuff for the 10-sec burst window (against a boss,
  "targets hit" is the boss, and she fires throughout the transform) - an
  approximation, documented here.
"""
from app.skill_rules._helpers import buff_rule
from app.squad_engine import SkillRule


# Fienn measured 25 hits across Suppression Initiated's 10-sec transform window
# (2026-07-22). The count is the anchor (via `until_shots`); the cadence follows
# from it and the window duration.
SUPPRESSION_SHOT_COUNT = 25


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

    # The burst's "normal attacks deal True Damage" is carried by the transform
    # segment's shots (pinned True), which ARE her burst-window normal attacks -
    # see build_suppression_initiated_weapon_mode_schedule. Only the on-hit
    # squad debuff is an ordinary registered effect.
    return [
        buff_rule("own_burst_activate", [
            ("damage_taken_up", on_hit_damage_taken, "squad", window),
        ]),
    ]


def build_suppression_initiated_weapon_mode_schedule(values: dict):
    """Suppression Initiated's weapon transform: for 10 sec her Sniper Rifle
    becomes a rapid-fire weapon dealing 200.64% of final ATK per shot. Fienn
    measured 25 hits across the 10-sec Full Burst window (2026-07-22), so the
    segment is anchored to that COUNT via `until_shots` - an `end`-bounded
    window at the same 2.5-shot/sec cadence would place the 25th shot exactly at
    t+10 and drop it (the base weapon resumes there), leaving 24.

    The shots are pinned to `damage_type="true"`: the same burst bullet converts
    her normal attacks to True Damage for the same 10 sec, and these transform
    shots ARE her normal attacks during the window - so her own +35% and squad
    +140% True Damage buffs land on them. Pinning states this directly rather
    than leaning on a `normal_attacks_deal_true` effect, whose right-exclusive
    window would drop that same final boundary shot. "SR" is only the segment's
    charge archetype; with an explicit `rate_of_fire` the cadence takes no buffs
    (the measured 25 already includes every in-game modifier)."""
    suppression = values["suppression_initiated"]
    damage_percent = float(suppression["description_value_01"])  # 200.64
    window = float(suppression["description_value_02"])          # 10 sec
    profile = {
        "weapon": "SR",
        "damage_percent": damage_percent,
        "rate_of_fire": SUPPRESSION_SHOT_COUNT / window,
        "damage_type": "true",
    }

    def schedule(context, fight_duration):
        return [
            {"start": t, "until_shots": SUPPRESSION_SHOT_COUNT, "profile": profile}
            for t in context.burst_times.get("takina-inoue", [])
        ]

    return schedule
