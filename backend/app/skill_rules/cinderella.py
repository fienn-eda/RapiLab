"""Cinderella (slug "cinderella"), a Burst-3 Electric Rocket Launcher defender.
Base skills. PARTIAL - decoy creation (survival) is deferred.

Modeled (DPS-relevant):
- Flawless Glass (skills[0]): on entering Burst Stage 3 - the STAGE, so also in
  the cycles an allied Burst 3 takes the slot - self ATK += 2.71% of her final
  Max HP for 10 sec. Every shot she fires deals an extra 136.6%-of-final-ATK
  hit - RL is a charge weapon, so EVERY normal attack IS a full-charge attack
  (see `attack_rate`), modeled as a per-shot instant nuke firing on every shot
  and eligible for the Full Burst bonus ("as additional damage").
- Dirt-Resistant Mirror (skills[1]): Beautiful, which is TWO things. Its stack
  COUNT is a named resource ticking every 3 sec (her decoy is up continuously
  from battle start), capped at 12, feeding Glass Slippers' mirrored additional
  hit below. Its Max HP +1.6% per stack is a separate battle-start ramp, which
  Flawless Glass's ATK above then reads live off.
- Glass Slippers, Full Contact. (skills[2], her burst): deals 1365.92% of final
  ATK as damage, attacking sequentially 10 times - 10 separate hits
  (`burst_hit_counts`, each independently defense-subtracted). While in
  Beautiful status, an additional hit whose magnitude "mirrors the stack count
  of Beautiful" (28.9% * count, via `resource_scaled_nukes`).

Not modeled / deferred:
- Decoy creation (both the battle-start and burst-tier-3-entry copies) - pure
  survivability (an HP-sponge clone), no damage-output consumer.
(Flawless Glass's Charge Speed +100% used to be listed here as "not a damage
stat". That was written before Phase S wired `charge_speed_percent`; it is now
modeled - see `flawless_glass_charge_speed`. It is one of her biggest levers,
since every shot she fires also carries the 136.6% additional hit.)
"""
from app.effects import Effect, ResourceSpec
from app.skill_rules._helpers import buff_rule, instant_nuke_pulse_rule, max_hp_scaled_atk_rule
from app.squad_engine import SkillRule, burst_stage_entered

BURST_STAGE = 3  # skill text: "entering Burst Stage 3" (a fixed reference, not a data slot)


SKILL_VALUE_MANIFESTS = {
    "cinderella": {
        "source": "lootandwaifus",
        "test_module": "test_skill_rules_cinderella",
        "keys": {
            "flawless_glass": ("skills", 0),
            "dirt_resistant_mirror": ("skills", 1),
            "glass_slippers": ("skills", 2),
        },
        "drop_tokens": {
            "flawless_glass": [0],
            "dirt_resistant_mirror": [1],
        },
    },
}


GLASS_SLIPPERS_HIT_COUNT = 10  # skill text: "Attacks sequentially for 10 time(s)" (fixed, not a data slot)


def glass_slippers_burst_percent(values):
    return float(values["glass_slippers"]["description_value_01"])


def build_flawless_glass_rules(values, caster_max_hp):
    """"Activates when entering Burst Stage 3" is about the STAGE, not about
    her - so it fires in every cycle a Burst 3 takes the slot, including the
    ones an ALLIED Burst 3 takes. `own_burst_activate` would silently drop
    those cycles (see squad_engine.burst_stage_entered)."""
    fg = values["flawless_glass"]
    atk_pct_of_max_hp = float(fg["description_value_01"]) / 100
    duration = float(fg["description_value_02"])
    return [max_hp_scaled_atk_rule(
        "ally_burst_activate", atk_pct_of_max_hp, "self", duration, caster_max_hp,
        condition=burst_stage_entered(BURST_STAGE),
    )]


def build_flawless_glass_per_shot_rules(values):
    """Full-burst-bonus eligible: the bullet's own text says "as additional
    damage", and each shot computes at its own time, so the simulator checks
    the shot against the Full Burst window rather than approximating."""
    fg = values["flawless_glass"]
    additional = float(fg["description_value_04"])
    return [(1, "every", [instant_nuke_pulse_rule("per_shot", additional,
                                                  full_burst_bonus_eligible=True)])]


def flawless_glass_charge_speed(values):
    """Flawless Glass's Charge Speed, straight from the skill slot.

    Nothing is calibrated here any more. `attack_rate.charge_time_with_speed`
    now models the game's real behaviour (a buff of n% SHORTENS the charge by
    n%, so her +100% reaches zero) and carries the measured floor on the gap
    between charged shots, so the raw skill value produces the right cadence
    on its own. Before that fix this function had to hand the engine a
    back-solved number instead.
    """
    return float(values["flawless_glass"]["description_value_03"]) / 100


def build_flawless_glass_charge_speed_rules(values):
    """Permanent, because she re-arms it on the first Full Charge of every
    magazine. The engine samples charge speed once per magazine, so treating
    it as always-on credits her magazine's first shot - which really pays the
    unbuffed charge - as fast too. That is one shot in 24, and the honest
    alternative (a per-shot charge model) would change every unit's timeline."""
    speed = flawless_glass_charge_speed(values)
    return [buff_rule("battle_start", [("charge_speed_percent", speed, "self", None)])]


def build_beautiful_resources(values):
    """The stack COUNT only - Glass Slippers' mirrored hit reads it. Beautiful's
    own Max HP per stack cannot ride this spec's `buffs` (see
    `build_beautiful_max_hp_rules`)."""
    dm = values["dirt_resistant_mirror"]
    interval = float(dm["description_value_03"])
    cap = int(float(dm["description_value_05"]))
    return [ResourceSpec(name="beautiful", fill=("periodic", interval), cap=cap, buffs=[])]


def build_beautiful_max_hp_rules(values, caster_max_hp):
    """Beautiful's "Max HP +1.6% continuously, stacks up to 12 times", which
    Flawless Glass's ATK then reads off her LIVE Max HP.

    Laid down at battle start as the whole ramp - one permanent effect per
    stack, each with the `applied_at` its stack really arrives at. The decoy is
    up from battle start and never drops, so the schedule is fully determined
    and pre-adding it is exact (the same reason periodic_rules may pre-add).

    Why not the `beautiful` ResourceSpec's own `buffs`: the simulator resolves
    resource buffs AFTER the shot loop, while max_hp_scaled_atk_rule reads
    flat_max_hp DURING it, at the instant her burst fires. A ResourceBuff here
    measures as exactly zero (verified 2026-07-27) - the resource can express
    the count for a nuke, but not a stat another rule has to see live.
    """
    dm = values["dirt_resistant_mirror"]
    interval = float(dm["description_value_03"])
    per_stack = float(dm["description_value_04"]) / 100 * caster_max_hp
    cap = int(float(dm["description_value_05"]))

    def action(context, caster_slug, time, registry):
        for stack in range(1, cap + 1):
            registry.add(Effect("flat_max_hp", per_stack, "self", None, caster_slug),
                         applied_at=time + interval * stack)

    return [SkillRule(trigger="battle_start", action=action)]


def build_glass_slippers_resource_scaled_nuke(values):
    gs = values["glass_slippers"]
    additional = float(gs["description_value_03"])
    cap = int(float(values["dirt_resistant_mirror"]["description_value_05"]))
    return [{
        "resource": "beautiful", "cap": cap, "base_percent": additional,
        "scale_fn": lambda count: count, "tick_count": 1, "tick_interval": 0.0,
    }]
