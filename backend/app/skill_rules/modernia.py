"""Modernia (slug "modernia"), a Burst-3 Fire Machine Gun attacker. Base skills.
First consumer of the named-resource / capped-stack-counter primitive (a TIMED
capped stack - see effects.ResourceSpec and raid_simulator's resolution pass).

Modeled (DPS-relevant):
- High-Speed Evolution (skills[0]): every normal-attack hit deals 3.05% of final
  ATK as additional damage (per-shot instant nuke). Every 200 hits, gains a stack
  of Critical Damage +14.25% AND Max Ammunition Capacity -5.04% (the ammo line is
  a `▼`, so each stack SHRINKS her magazine), each stacking up to 5 and lasting
  10 sec - modeled as one "evolution" resource (filled every 200 shots, cap 5)
  driving two linear buffs. The 10 sec is ONE clock every new stack restarts
  (`lifetime_refreshes`, the Raven ruling): her 200-hit mark comes round every
  ~4 sec, so the chain never breaks and she holds the cap. Read as five
  independent timers she settled at 3 - worth **+2.95% to her, +1.33% to the
  deck** on a DEF-8000 boss (`scripts/audit_stack_lifetime_refresh.py`).
- Giant Leap (skills[1]) squad Hit Rate +8.56% for 15 sec on Full Burst entry.
  It buys HER nothing - an MG's spread converges to 10px, already inside any
  plausible core - but it is "Affects all allies", so it is the deck's SG/SMG/AR
  seats that collect it.
- Giant Leap (skills[1]) self ATK +29.38% for 10 sec: fires on every 200th
  normal hit counted from battle start - in-game it is NOT gated on the
  15-sec increasing-Hit-Rate window the skill text describes (Fienn
  2026-07-18), so it's a plain every-200 per-shot rule, refreshing (MG's
  60 shots/s puts consecutive marks well inside the 10s duration).
- New World's squad Full Burst Duration +5 sec: registered as
  `FULL_BURST_DURATION_DELTA["modernia"]` (registry.py), read by burst_cycle
  from whichever member opened that cycle's tier 3 - so it applies ONLY on a
  cycle she is the one who actually bursts, never on a cycle a tier-3 ally
  opens instead. That's a separate question from whether her burst nuke or
  weapon transform is modeled (it isn't - see below): the delta fires off her
  being the tier-3 opener, not off the transform. Her best shape ((1,1,3), see
  below) is built around her never bursting, so in practice this only
  lengthens the rare cycle a thinner deck forces her to fire.

Not modeled / deferred:
- The Max Ammunition Capacity stack is emitted, but Max Ammo only feeds shot
  generation (magazine size / reload cadence), which is computed for this unit
  BEFORE the resource resolution pass runs - so it can't retroactively resize her
  own already-scheduled magazines. It's an inert-for-own-shots buff, kept for
  faithfulness (a future live-max-ammo consumer would read it). She is the only
  unit whose resource feeds a stat the shot loop consumes, so this ordering costs
  exactly one bullet today.
- New World (skills[2], her burst): unlimited ammo and Destroy Mode (auto-aim +
  a 2.24%-of-ATK Destroy-Mode damage over 15s) - a weapon/targeting mode, not a
  single burst nuke, so burst_percent is None. (Full Burst Duration +5s is
  modeled above, independent of the transform.)
- Its Destroy Mode weapon transform is deliberately NOT modeled as a
  `weapon_mode_schedules` segment, though the primitive exists. Per Fienn
  (2026-07-21), against a raid boss Modernia's burst is a DPS LOSS - Destroy
  Mode's 2.24% normal shot is far below her base MG's 7.71%, and its multi-
  target auto-aim buys nothing when "the stage target is treated as a single
  enemy". So she is played as a burst-ABSTAINING normal-attack dealer, seated
  rightmost in a (1,1,3) deck where her two Burst-3 allies carry the rotation.
  Modelling the segment would force her burst and understate her by ~12% (a
  fixed-shell sweep confirmed this). Her current base-MG normal fire is the
  faithful picture of a unit that never enters Destroy Mode - the segment and
  the unlimited ammo only fire on a burst she does not use. The abstention
  itself is represented in the deck search, not here: she is
  pinned to the LAST Burst-3 seat (deck_search._BUFFER_SEAT_SLUGS), so a Burst-3
  ally is the leftmost-eligible burster every cycle and Modernia never enters
  Destroy Mode in her best shape ((1,1,3), where two allies cover the ~40s
  cooldown; a thinner shape can force an occasional fallback burst, which the
  search scores lower and avoids when a (1,1,3) exists).
"""
from app.effects import ResourceSpec
from app.skill_rules._helpers import (
    buff_rule,
    instant_nuke_pulse_rule,
    linear_resource_buff,
    refreshing_buff_rule,
)

SKILL_VALUE_MANIFESTS = {
    "modernia": {
        "source": "lootandwaifus",
        "test_module": "test_skill_rules_resource_eb",
        "keys": {
            "high_speed_evolution": ("skills", 0),
            "giant_leap": ("skills", 1),
        },
    },
}


def build_modernia_rules(values):
    """Giant Leap's first bullet: squad Hit Rate on Full Burst entry. Her own
    MG gains nothing from it (10px spread), so this exists entirely for the
    allies sharing her deck."""
    leap = values["giant_leap"]
    squad_hit_rate = float(leap["description_value_01"]) / 100
    duration = float(leap["description_value_02"])
    return [
        buff_rule("full_burst_enter", [
            ("hit_rate", squad_hit_rate, "squad", duration),
        ]),
    ]


def build_modernia_resources(values):
    evo = values["high_speed_evolution"]
    hit_threshold = int(evo["description_value_02"])
    crit_per_stack = float(evo["description_value_03"]) / 100
    stack_cap = int(evo["description_value_04"])
    stack_duration = float(evo["description_value_05"])
    # "Max Ammunition Capacity ▼ 5.04%" - the arrow subtracts, so each stack
    # shrinks her magazine.
    ammo_cut_per_stack = float(evo["description_value_06"]) / 100
    return [
        ResourceSpec(
            name="evolution",
            fill=("per_shot_every", hit_threshold),
            cap=stack_cap,
            buffs=[
                linear_resource_buff(
                    "other_critical_damage_sources", crit_per_stack, "self"),
                linear_resource_buff("max_ammo_percent", -ammo_cut_per_stack, "self"),
            ],
            # Both bullets are the same stack, so they share its clock - which
            # is the reason a lifetime belongs to the resource and not to each
            # buff hung off it.
            lifetime=stack_duration,
            lifetime_refreshes=True,
        )
    ]


def build_modernia_per_shot_rules(values):
    evo = values["high_speed_evolution"]
    additional = float(evo["description_value_01"])
    leap = values["giant_leap"]
    leap_threshold = int(leap["description_value_03"])
    leap_atk = float(leap["description_value_04"]) / 100
    leap_duration = float(leap["description_value_05"])
    return [
        (1, "every", [instant_nuke_pulse_rule("per_shot", additional)]),
        (leap_threshold, "every", [
            refreshing_buff_rule("per_shot", [
                ("atk_percent", leap_atk, "self", leap_duration),
            ]),
        ]),
    ]
