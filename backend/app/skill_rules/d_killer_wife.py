"""D: Killer Wife (slug "d-killer-wife"), a Burst-1 SR supporter. Base skills
(no signature).

Modeled (DPS-relevant):
- Calm Sniping (skills[0]): on Full Burst enter, squad Pierce Damage up (the
  skill limits it to Sniper Rifle allies; approximated as squad - the scope
  model has no weapon-conditional targeting, and pierce is a general damage-up).
- Assault Formation (skills[1]): squad Attack Damage on every 5 Full Charge
  attacks (via per_shot_rules; an SR's every shot is a full charge); and its
  every-8-full-charge squad Cooldown reduction, modeled as a per-CYCLE CDR pulse
  (on full_burst_end) rather than counting shots. Rationale (Fienn): 8 full
  charges is met essentially every cycle (a full charge ~1 sec), so applying the
  reduction once per cycle is a faithful approximation - and it uses the existing
  per-cycle CDR machinery, sidestepping the per-shot -> rotation ordering problem.

Not modeled:
- Calm Sniping's "gain Pierce for 1 shot after 3 full charges" - a per-shot
  pierce enable, not a damage-up buff.
- Kill the Target (skills[2], her burst): deferred per Fienn. It is a 269.28%
  nuke plus a Wipe-Out debuff whose follow-up buffs depend on which area of the
  target allies hit (positional/target-state, unrepresentable). Her burst
  currently contributes no modeled damage.
"""
from app.skill_rules._helpers import buff_rule, cdr_pulse_rule, refreshing_buff_rule

ASSAULT_FORMATION_ATTACK_DAMAGE_SHOT_COUNT = 5  # skill text: "for 5 time(s)"


def build_d_killer_wife_rules(values):
    calm = values["calm_sniping"]
    assault = values["assault_formation"]
    fb_pierce = float(calm["description_value_02"]) / 100
    fb_pierce_duration = float(calm["description_value_03"])
    cdr_sec = float(assault["description_value_02"])  # every-8-full-charge CDR ~= per cycle
    return [
        buff_rule("full_burst_enter", [
            ("pierce_damage_up", fb_pierce, "squad", fb_pierce_duration),
        ]),
        cdr_pulse_rule("full_burst_end", cdr_sec),
    ]


def build_assault_formation_rules(values):
    """Per-shot rules (see raid_simulator's `per_shot_rules`): squad Attack
    Damage on every 5th Full Charge attack (an SR's every shot is a full charge).
    Refreshing buff (the game refreshes, not stacks)."""
    attack_damage = float(values["description_value_04"]) / 100
    attack_damage_duration = float(values["description_value_05"])
    return [(ASSAULT_FORMATION_ATTACK_DAMAGE_SHOT_COUNT, "every", [refreshing_buff_rule("per_shot", [
        ("attack_damage_up", attack_damage, "squad", attack_damage_duration),
    ])])]
