"""D: Killer Wife (slug "d-killer-wife"), a Burst-1 SR supporter. Base skills
(no signature).

Modeled (DPS-relevant):
- Calm Sniping (skills[0]): on Full Burst enter, Pierce Damage up on "all allies
  with a Sniper Rifle" - the exact live weapon filter, not a squad
  approximation. It matters because Pierce Damage is gated on the recipient
  holding Pierce, and non-SR units do hold it (Grave, Dorothy: Serendipity,
  Zwei), so a squad scope really did pay allies the skill excludes.
- Calm Sniping's "attacking with Full Charge for 3 time(s): Gain Pierce for 1
  shot" - the `has_pierce` property as a one-round grant, which is what her own
  Pierce Damage buff then credits on her.
- Assault Formation (skills[1]): squad Attack Damage on every 5 Full Charge
  attacks (via per_shot_rules; an SR's every shot is a full charge); and its
  every-8-full-charge squad Cooldown reduction, modeled as a per-CYCLE CDR pulse
  (on full_burst_end) rather than counting shots. Rationale (Fienn): 8 full
  charges is met essentially every cycle (a full charge ~1 sec), so applying the
  reduction once per cycle is a faithful approximation - and it uses the existing
  per-cycle CDR machinery, sidestepping the per-shot -> rotation ordering problem.

Not modeled:
- Kill the Target (skills[2], her burst): deferred per Fienn. It is a 269.28%
  nuke plus a Wipe-Out debuff whose follow-up buffs depend on which area of the
  target allies hit (positional/target-state, unrepresentable). Her burst
  currently contributes no modeled damage.
"""
from app.skill_rules._helpers import (
    cdr_pulse_rule,
    member_subset_buff_rule,
    refreshing_buff_rule,
    round_buff_rule,
)


SKILL_VALUE_MANIFESTS = {
    "d-killer-wife": {
        "source": "lootandwaifus",
        "test_module": "test_skill_rules_burst1_batch2",
        "keys": {
            "calm_sniping": ("skills", 0),
            "assault_formation": ("skills", 1),
        },
        "drop_tokens": {
            "calm_sniping": [1],
        },
    },
}


ASSAULT_FORMATION_ATTACK_DAMAGE_SHOT_COUNT = 5  # skill text: "for 5 time(s)"
CALM_SNIPING_PIERCE_SHOT_COUNT = 3  # skill text: "for 3 time(s)"


def build_d_killer_wife_rules(values):
    calm = values["calm_sniping"]
    assault = values["assault_formation"]
    fb_pierce = float(calm["description_value_02"]) / 100
    fb_pierce_duration = float(calm["description_value_03"])
    cdr_sec = float(assault["description_value_02"])  # every-8-full-charge CDR ~= per cycle
    return [
        member_subset_buff_rule(
            "full_burst_enter",
            lambda m, context: m.weapon == "SR",
            [("pierce_damage_up", fb_pierce, fb_pierce_duration)],
        ),
        cdr_pulse_rule("full_burst_end", cdr_sec),
    ]


def build_assault_formation_rules(values):
    """Per-shot rules (see raid_simulator's `per_shot_rules`): squad Attack
    Damage on every 5th Full Charge attack (an SR's every shot is a full charge).
    Refreshing buff (the game refreshes, not stacks)."""
    attack_damage = float(values["description_value_04"]) / 100
    attack_damage_duration = float(values["description_value_05"])
    return [
        (ASSAULT_FORMATION_ATTACK_DAMAGE_SHOT_COUNT, "every", [refreshing_buff_rule("per_shot", [
            ("attack_damage_up", attack_damage, "squad", attack_damage_duration),
        ])]),
        # Calm Sniping: "attacking with Full Charge for 3 time(s) -> Gain Pierce
        # for 1 shot". An SR's every shot is a full charge, so it lands on every
        # third and covers exactly the next bullet - the round-grant path, not a
        # seconds-based window. She therefore holds Pierce for one shot in three,
        # which is what her own squad Pierce Damage buff credits on her.
        (CALM_SNIPING_PIERCE_SHOT_COUNT, "every", [
            round_buff_rule("per_shot", [("has_pierce", 1.0, "self")], shots=1),
        ]),
    ]



