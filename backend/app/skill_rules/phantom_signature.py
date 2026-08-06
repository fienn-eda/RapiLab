"""Phantom's Favorite Item (애장품) build, slug "phantom-signature" - a SEPARATE
roster entry from base Phantom (slug "phantom"), per the dual-slot convention
(2026-07-12).

**What the Favorite Item actually does here**: it adds a second Thief's Dagger
source, "after landing 30 normal attacks on the stage target". That one bullet
unlocks her whole Skill 2. In the base build the dagger's only source is a normal
attack on a target NOT in the Calling Card state - and that same attack applies
Calling Card for 5 sec, exactly the dagger's own duration - so a stack expires
the instant the next could be earned and the dagger is pinned at 1 forever
(Fienn confirmed, 2026-07-24). With the shot-counted source (30 AR shots = 2.5
sec of fire) two dagger stacks coexist from it, plus one from the Calling Card
source, so max stacks land about every 5 sec of fire - Fienn's figure, encoded
as a 60-shot counter (12 shots/sec x 5 sec).

Weapon stats come from base Phantom's ShiftyPad file via the manifest's
`weapon_source`, since ShiftyPad exposes no dollskills and dotgg is dead.

Modeled (DPS-relevant):
- Thief's Calling Card (dollskills[0]): permanent squad `enemy_def_percent`
  -32.19%, and self Attack Damage +75.17% as a per-shot round grant - both
  exactly as in the base build.
- Thief's Vision (dollskills[1]): self ATK +85.12% for 5 sec and Distributed
  Damage +31.92% for 10 sec every 10 normal attacks, also as in the base. The
  bullet names no stack count, so at 12 AR shots/sec each re-application
  refreshes the live grant instead of adding to it.
- Thief's Vision (dollskills[1]) at max dagger stacks, every 60 shots:
  * 84.33% of final ATK as ADDITIONAL damage. "Additional damage" is
    Full-Burst-Bonus eligible (the project's standing rule), and unlike a burst
    nuke it is computed at its own time, so it genuinely can land inside a Full
    Burst window - it is emitted as an instant-damage pulse with the flag set.
  * 250% of final ATK as Distributed Damage to all enemies.
  * self Distributed Damage +12.86%, up to 3 stacks. The text removes the stacks
    on Burst Skill use, so they rebuild each burst cycle rather than sitting at
    max - encoded as a 10 sec grant, which at a 5 sec proc cadence holds the
    2-3 stacks the cycle actually sustains instead of assuming the cap.
- Secret Trick (dollskills[2], her burst, cd 40): 1457.28% as Distributed
  Damage; Damage Taken +18% for 30 sec when the boss is Fire Code; self Max
  Ammunition Capacity +50% for 10 sec.

Not modeled / deferred:
- Thief's Dagger's Hit Rate +25.75% - Hit Rate is not a damage concept.
- The dagger stack count itself is not tracked as a resource: the 60-shot
  counter stands in for "max stacks reached", per Fienn's cadence. If the
  engine ever grows a real multi-source stack model this should be revisited.
"""
from app.skill_rules._helpers import (
    buff_rule,
    instant_nuke_pulse_rule,
    refreshing_buff_rule,
    round_buff_rule,
)
from app.squad_engine import boss_is_element


SKILL_VALUE_MANIFESTS = {
    "phantom-signature": {
        "source": "lootandwaifus",
        "weapon_source": "shiftypad",
        "data_slug": "phantom",
        "test_module": "test_skill_rules_phantom_signature",
        "keys": {
            "calling_card": ("dollskills", 0),
            "thiefs_vision": ("dollskills", 1),
            "secret_trick": ("dollskills", 2),
        },
    },
}

# Shots between Thief's Vision procs: 12 AR shots/sec x the ~5 sec of fire it
# takes the dagger to reach max stacks with the Favorite Item's extra source
# (Fienn, 2026-07-24).
VISION_PROC_SHOTS = 60
# The stacking Distributed Damage bullet has no stated duration - it is removed
# on Burst Skill use. Held for two proc cycles so the deck sees the 2-3 stacks a
# burst cycle really sustains rather than the text's 3-stack cap.
VISION_STACK_DURATION = 10.0


def secret_trick_signature_burst_percent(values):
    return float(values["secret_trick"]["description_value_01"])


def build_phantom_signature_rules(values):
    card = values["calling_card"]
    trick = values["secret_trick"]
    def_debuff = float(card["description_value_01"]) / 100
    damage_taken = float(trick["description_value_02"]) / 100
    damage_taken_duration = float(trick["description_value_03"])
    max_ammo = float(trick["description_value_04"]) / 100
    max_ammo_duration = float(trick["description_value_05"])
    return [
        buff_rule("battle_start", [
            ("enemy_def_percent", -def_debuff, "squad", None),
        ]),
        buff_rule("own_burst_activate", [
            ("max_ammo_percent", max_ammo, "self", max_ammo_duration),
        ]),
        buff_rule("own_burst_activate", [
            ("damage_taken_up", damage_taken, "squad", damage_taken_duration),
        ], condition=boss_is_element("Fire")),
    ]


def build_phantom_signature_per_shot_rules(values):
    card = values["calling_card"]
    vision = values["thiefs_vision"]
    attack_damage = float(card["description_value_10"]) / 100
    rounds = int(float(card["description_value_11"]))
    vision_shots = int(float(vision["description_value_05"]))
    vision_atk = float(vision["description_value_06"]) / 100
    vision_atk_duration = float(vision["description_value_07"])
    distributed = float(vision["description_value_08"]) / 100
    distributed_duration = float(vision["description_value_09"])
    additional = float(vision["description_value_01"])
    stack_distributed = float(vision["description_value_02"]) / 100
    max_stack_nuke = float(vision["description_value_04"])
    return [
        (1, "every", [
            round_buff_rule("per_shot", [("attack_damage_up", attack_damage, "self")],
                            shots=rounds),
        ]),
        (vision_shots, "every", [
            refreshing_buff_rule("per_shot", [
                ("atk_percent", vision_atk, "self", vision_atk_duration),
                ("distributed_damage_up", distributed, "self", distributed_duration),
            ]),
        ]),
        (VISION_PROC_SHOTS, "every", [
            instant_nuke_pulse_rule("per_shot", additional),
            instant_nuke_pulse_rule("per_shot", max_stack_nuke, damage_type="distributed"),
            buff_rule("per_shot", [
                ("distributed_damage_up", stack_distributed, "self", VISION_STACK_DURATION),
            ]),
        ]),
    ]
