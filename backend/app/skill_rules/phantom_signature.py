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
  -32.19% and self Attack Damage +75.17% as a per-shot round grant, both
  exactly as in the base build. Its Hit Rate +25.75% per dagger stack is NOT a
  flat grant here - it rides the live count (below), which is the one place
  this build's Calling Card differs from the base's in effect.
- Thief's Vision (dollskills[1]): self ATK +85.12% for 5 sec and Distributed
  Damage +31.92% for 10 sec every 10 normal attacks, also as in the base. The
  bullet names no stack count, so at 12 AR shots/sec each re-application
  refreshes the live grant instead of adding to it.
- Thief's Vision (dollskills[1]) at max dagger stacks, every 60 shots:
  * 84.33% of final ATK as additional damage. It rides her own shots, so it is
    computed at each proc's own time and collects the Full Burst bonus on
    whichever land inside a window - the TIMING decides it, not the wording (the
    "as additional damage" text rule was deleted 2026-07-28). Emitted as an
    instant-damage pulse, which takes no eligibility flag for that reason.
  * 250% of final ATK as Distributed Damage to all enemies.
  * self Distributed Damage +12.86%, up to 3 stacks. The text removes the stacks
    on Burst Skill use, so they rebuild each burst cycle rather than sitting at
    max - encoded as a 10 sec grant, which at a 5 sec proc cadence holds the
    2-3 stacks the cycle actually sustains instead of assuming the cap.
- Secret Trick (dollskills[2], her burst, cd 40): 1457.28% as Distributed
  Damage; Damage Taken +18% for 30 sec when the boss is Fire Code; self Max
  Ammunition Capacity +50% for 10 sec.
- Thief's Dagger as a live counter (`build_dagger_resource_specs`), driving her
  Hit Rate as the step function the stack count really traces. The count runs
  0 -> 1 -> 2 -> spend, never resting at 3: the cap is reached and consumed in
  the same instant, so a three-stack Hit Rate is never held for any duration.
  Its time-average over her shots is **1.48 stacks**.

  The PROC side is deliberately left on `VISION_PROC_SHOTS`: the walk's spend
  times are every 60th shot exactly (see above), so moving the nukes onto the
  resource would buy nothing and risk the one thing that is proven. The cadence
  test pins the two against each other.

Not modeled / deferred:
- Nothing in the dagger. (What her Hit Rate is worth depends entirely on the
  encounter: hit rate reaches damage only when the boss is BOTH `core_hittable`
  and carries a `core_diameter_px`, and no boss the product builds decks against
  declares either - `data/raid-rotations.json` has 0 of 6, and both
  `BossProfile` fields default off. Measured on this deck: 0.00% against the
  default boss, **+1.68%** against one with the record boss's core hittable at
  48.89 px. Above two stacks her 75px spread is already inside that core, which
  is why the third stack would have been worth nothing even if it were held.)
"""
from app.effects import ResourceSpec
from app.skill_rules._helpers import (
    buff_rule,
    instant_nuke_pulse_rule,
    linear_resource_buff,
    refreshing_buff_rule,
    round_buff_rule,
)
from app.squad_engine import boss_is_element

THIEFS_DAGGER = "thiefs_dagger"


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


def dagger_timeline(shot_times, values):
    """Walk Thief's Dagger over `shot_times`, returning (fill times, spend times).

    One walk feeds both sides of the resource, so the fills and the spends can
    never disagree about when the dagger emptied. Written straight from the
    Favorite Item text:

    - source 1 fires on a normal attack against a target NOT carrying Calling
      Card, and the same attack applies Calling Card. Both last 5 sec, and that
      shared clock is why the source nets nothing past the stack it grants right
      after each spend (see the module docstring).
    - source 2 fires every 30 normal attacks, on a counter of its own.
    - reaching the 3-stack cap fires Thief's Vision, which removes the stacks
      and (first bullet) removes Calling Card, re-arming source 1.
    """
    card = values["calling_card"]
    cap = int(float(card["description_value_04"]))
    stack_seconds = float(card["description_value_05"])
    calling_card_seconds = float(card["description_value_02"])
    source_two_shots = int(float(card["description_value_06"]))

    expiries = []
    calling_card_until = float("-inf")
    since_source_two = 0
    fills, spends = [], []
    for time in shot_times:
        expiries = [e for e in expiries if e > time]
        if time >= calling_card_until:
            if len(expiries) < cap:
                expiries.append(time + stack_seconds)
                fills.append(time)
            calling_card_until = time + calling_card_seconds
        since_source_two += 1
        if since_source_two >= source_two_shots:
            since_source_two = 0
            if len(expiries) < cap:
                expiries.append(time + stack_seconds)
                fills.append(time)
        if len(expiries) >= cap:
            spends.append(time)
            expiries = []
            calling_card_until = time
    return fills, spends


def build_dagger_resource_specs(values):
    """Thief's Dagger as a live counter, so her Hit Rate is the step function the
    stack count really traces instead of the base build's one-stack floor.

    The walk is the module's because the dagger's two sources INTERACT - spending
    it strips Calling Card, which is the condition re-arming the other source -
    so no set of independent per-source schedules can express it. Everything
    after the walk is the engine's: `resource_count` already replaces its
    baseline at each spend and expires each fill on its own clock, which is
    exactly the sawtooth.
    """
    card = values["calling_card"]
    cap = int(float(card["description_value_04"]))
    stack_seconds = float(card["description_value_05"])
    per_stack_hit_rate = float(card["description_value_03"]) / 100
    return [ResourceSpec(
        name=THIEFS_DAGGER,
        fill=("computed", lambda shot_times: dagger_timeline(shot_times, values)[0]),
        cap=cap,
        buffs=[linear_resource_buff("hit_rate", per_stack_hit_rate, "self")],
        # "Stacks up to 3 times and lasts for 5 sec" - one clock the stack
        # shares. The walk below reaches the cap and spends it in the same
        # instant either way (source 1 is gated on the absence of a status that
        # lasts exactly as long as the stack, so it can never add to a live
        # one); the shared clock only changes how the leftovers decay.
        lifetime=stack_seconds,
        lifetime_refreshes=True,
        resets=[{
            "trigger": "computed",
            "value": 0,
            "times": lambda shot_times: dagger_timeline(shot_times, values)[1],
        }],
    )]


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
            # Hit Rate is NOT granted here - the dagger drives it as a live
            # count (`build_dagger_resource_specs`).
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
                            shots=rounds, from_own_shot=True),
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
