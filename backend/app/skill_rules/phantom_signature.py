"""Phantom's Favorite Item (애장품) build, slug "phantom-signature" - a SEPARATE
roster entry from base Phantom (slug "phantom"), per the dual-slot convention
(2026-07-12).

**What the Favorite Item actually does here**: it adds a second Thief's Dagger
source, "after landing 30 normal attacks on the stage target". That one bullet
unlocks her whole Skill 2. In the base build the dagger's only source is a normal
attack on a target NOT in the Calling Card state - and that same attack applies
Calling Card for 5 sec, exactly the dagger's own duration - so a stack expires
the instant the next could be earned and the dagger is pinned at 1 forever
(Fienn confirmed, 2026-07-24).

**The 60-shot proc cadence is exact, not an approximation** (derived 2026-08-14;
`tests/test_phantom_dagger_cadence.py` re-derives it from the data). The base
build's cancellation does not go away here - it applies to source 1 in THIS
build too. Source 1 grants a stack and applies Calling Card for the same 5 sec,
so the moment Calling Card lapses and it may fire again is the moment its own
previous stack expires: past the one stack it contributes right after each proc,
its net contribution is zero. That leaves the Favorite Item's 30-shot metronome
as the only thing that accumulates, and the 3-stack cap therefore lands on its
second tick - **30 x (3 - 1) = 60 shots**, at every fire rate.

Walking it against her real shot timeline gives a proc gap of exactly 60 shots
(min = median = max) from 6.1 to 40 shots/sec. Below **6.0 shots/sec** - where
30 shots takes longer than the 5 sec stack lifetime - source 2's own stacks
expire before the next lands and the dagger can NEVER reach max, so the constant
would be wrong there; her AR fires 12/sec at base and the game has no
attack-speed debuff for your own units, so that cliff is out of reach.

Weapon stats come from base Phantom's ShiftyPad file via the manifest's
`weapon_source`, since ShiftyPad exposes no dollskills and dotgg is dead.

Modeled (DPS-relevant):
- Thief's Calling Card (dollskills[0]): permanent squad `enemy_def_percent`
  -32.19%, self Attack Damage +75.17% as a per-shot round grant, and ONE
  dagger stack's Hit Rate +25.75% held permanently - all three exactly as in
  the base build. The extra stacks this build genuinely earns are NOT added:
  see the deferral below.
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
- The dagger stack count is not tracked as a live resource - the 60-shot
  counter stands in for "max stacks reached". **For the PROC TIMES that is not
  an approximation** (see the derivation above), so tracking the count would
  reproduce the cadence this module already fires. What it would change is the
  Hit Rate below.
- Her Hit Rate is encoded at ONE stack, the base build's floor, while the true
  count is a sawtooth 1 -> 2 -> 3 -> 0 whose time-average is **1.48 stacks**
  (walked against her real shot timeline, 2026-08-14). So this build's core-hit
  share is an UNDERSTATEMENT.

  It currently costs nothing: hit rate reaches damage only through
  `BossProfile.core_diameter_px`, which is opt-in and set on no boss the product
  builds decks against (0 of 6 in `data/raid-rotations.json`, default None).
  Measured: forcing her dagger to 2 or 3 stacks moves her sweep total by 0.00%.

  **And the fix is not to pin 1.48.** Hit rate reaches damage through an AREA
  RATIO, so the mean of the count and the mean of the resulting core-hit
  probability are different numbers; substituting a time-averaged stack count
  into a non-linear path would be wrong in a direction nobody has measured. The
  honest fix is the step function - the dagger as a real resource driving a
  count-scaled `ResourceBuff` - and it is worth building on the day a raid boss
  carries a measured core diameter, not before.
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

# Shots between Thief's Vision procs. Fienn read this in-game as "about 5 sec of
# fire" (2026-07-24); walking the skill text shows it is EXACT rather than a
# cadence fitted to one deck - 30 shots x (3 stacks - 1). See the module
# docstring for the derivation and `tests/test_phantom_dagger_cadence.py`, which
# re-derives it from the data so a value change cannot leave it stale.
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
    dagger_hit_rate = float(card["description_value_03"]) / 100
    damage_taken = float(trick["description_value_02"]) / 100
    damage_taken_duration = float(trick["description_value_03"])
    max_ammo = float(trick["description_value_04"]) / 100
    max_ammo_duration = float(trick["description_value_05"])
    return [
        buff_rule("battle_start", [
            ("enemy_def_percent", -def_debuff, "squad", None),
            # The base build's single held stack, its floor - see the docstring.
            ("hit_rate", dagger_hit_rate, "self", None),
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
