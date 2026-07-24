"""Phantom (slug "phantom"), a Burst-3 Water AR Attacker built around Distributed
Damage. Her burst is typed `distributed`, so her own Distributed Damage buffs
multiply it (see the registry's _BURST_DAMAGE_TYPES).

Modeled (DPS-relevant):
- Thief's Calling Card (skills[0]): the Calling Card debuff, enemy DEF -32.19%,
  as a permanent squad-scope `enemy_def_percent`. The text re-applies it on any
  normal attack against a target NOT already carrying it, and at the engine's AR
  rate (12 shots/sec) the very next shot after the 5 sec window lapses restores
  it - the gap is under a tenth of a second, so permanent is the faithful shape.
- Thief's Calling Card (skills[0]): self Attack Damage +75.17% "for 1 round(s)"
  on every normal attack against a Calling Card target. Since Calling Card is
  effectively always up, this is a per-shot round buff on every shot.
- Thief's Vision (skills[1]): self ATK +85.12% for 5 sec and Distributed Damage
  +31.92% for 10 sec every 10 normal attacks. 10 AR shots take 0.83 sec, so both
  are re-applied far faster than they expire.
- Secret Trick: Rampages of Thieves (skills[2], her burst, cd 40): 1457.28% of
  final ATK as Distributed Damage.

Not modeled / deferred:
- **Thief's Dagger and everything gated on its max stacks** - i.e. Thief's
  Vision's 84.33% additional damage and its stacking Distributed Damage +12.86%.
  Fienn confirmed (2026-07-24) that in the BASE build the dagger cannot reach max
  stacks at all: the only stack source is "a normal attack on a Rapture NOT in
  the Calling Card state", but that same attack applies Calling Card for 5 sec -
  exactly the dagger's own duration - so the stack expires in the same instant
  the next one could be earned, pinning her at one stack forever. Her Favorite
  Item build adds a shot-counted dagger source that breaks the deadlock, and
  encodes these bullets.
- Thief's Dagger's Hit Rate +25.75% - Hit Rate is not a damage concept in the
  engine even where the stacks do accrue.
"""
from app.skill_rules._helpers import buff_rule, round_buff_rule


SKILL_VALUE_MANIFESTS = {
    "phantom": {
        "source": "shiftypad",
        "test_module": "test_skill_rules_phantom",
        "keys": {
            "calling_card": ("skills", 0),
            "thiefs_vision": ("skills", 1),
            "secret_trick": ("skills", 2),
        },
    },
}


def secret_trick_burst_percent(values):
    return float(values["secret_trick"]["description_value_01"])


def build_phantom_rules(values):
    card = values["calling_card"]
    def_debuff = float(card["description_value_01"]) / 100
    return [
        buff_rule("battle_start", [
            ("enemy_def_percent", -def_debuff, "squad", None),
        ]),
    ]


def build_phantom_per_shot_rules(values):
    card = values["calling_card"]
    vision = values["thiefs_vision"]
    attack_damage = float(card["description_value_06"]) / 100
    rounds = int(float(card["description_value_07"]))
    vision_shots = int(float(vision["description_value_03"]))
    vision_atk = float(vision["description_value_04"]) / 100
    vision_atk_duration = float(vision["description_value_05"])
    distributed = float(vision["description_value_06"]) / 100
    distributed_duration = float(vision["description_value_07"])
    return [
        (1, "every", [
            round_buff_rule("per_shot", [("attack_damage_up", attack_damage, "self")],
                            shots=rounds),
        ]),
        (vision_shots, "every", [
            buff_rule("per_shot", [
                ("atk_percent", vision_atk, "self", vision_atk_duration),
                ("distributed_damage_up", distributed, "self", distributed_duration),
            ]),
        ]),
    ]
