"""Cinderella (slug "cinderella"), a Burst-3 Fire Rocket Launcher attacker.
Base skills. PARTIAL - decoy creation (survival) is deferred; Beautiful's own
Max HP growth is inert (no live max_hp stat consumer), only its stack COUNT
feeds the burst's mirrored additional hit.

Modeled (DPS-relevant):
- Flawless Glass (skills[0]): on entering Burst Stage 3 (her own burst), self
  ATK += 2.71% of her final Max HP for 10 sec. Every shot she fires deals an
  extra 136.6%-of-final-ATK hit - RL is a charge weapon, so EVERY normal attack
  IS a full-charge attack (see `attack_rate`), modeled as a per-shot instant
  nuke firing on every shot.
- Dirt-Resistant Mirror (skills[1]): Beautiful, a named resource that ticks
  every 3 sec (her decoy is up continuously from battle start), capped at 12
  stacks - feeds Glass Slippers' mirrored additional hit below.
- Glass Slippers, Full Contact. (skills[2], her burst): deals 1365.92% of final
  ATK as damage, attacking sequentially 10 times - 10 separate hits
  (`burst_hit_counts`, each independently defense-subtracted). While in
  Beautiful status, an additional hit whose magnitude "mirrors the stack count
  of Beautiful" (28.9% * count, via `resource_scaled_nukes`).

Not modeled / deferred:
- Decoy creation (both the battle-start and burst-tier-3-entry copies) - pure
  survivability (an HP-sponge clone), no damage-output consumer.
- Beautiful's own "Max HP +1.6% per stack": the engine has no live max_hp stat
  consumer (base_stats' max_hp is a fixed input, never read back from the
  registry), so this specific bullet is inert - only the STACK COUNT itself
  (read via resource_scaled_nukes) matters for damage.
(Flawless Glass's Charge Speed +100% used to be listed here as "not a damage
stat". That was written before Phase S wired `charge_speed_percent`; it is now
modeled - see `flawless_glass_charge_speed`. It is one of her biggest levers,
since every shot she fires also carries the 136.6% additional hit.)
"""
from app.effects import ResourceSpec
from app.skill_rules._helpers import buff_rule, instant_nuke_pulse_rule


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
    fg = values["flawless_glass"]
    atk_from_max_hp = caster_max_hp * float(fg["description_value_01"]) / 100
    duration = float(fg["description_value_02"])
    return [buff_rule("own_burst_activate", [("flat_atk", atk_from_max_hp, "self", duration)])]


def build_flawless_glass_per_shot_rules(values):
    fg = values["flawless_glass"]
    additional = float(fg["description_value_04"])
    return [(1, "every", [instant_nuke_pulse_rule("per_shot", additional)])]


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
    dm = values["dirt_resistant_mirror"]
    interval = float(dm["description_value_03"])
    cap = int(float(dm["description_value_05"]))
    return [ResourceSpec(name="beautiful", fill=("periodic", interval), cap=cap, buffs=[])]


def build_glass_slippers_resource_scaled_nuke(values):
    gs = values["glass_slippers"]
    additional = float(gs["description_value_03"])
    cap = int(float(values["dirt_resistant_mirror"]["description_value_05"]))
    return [{
        "resource": "beautiful", "cap": cap, "base_percent": additional,
        "scale_fn": lambda count: count, "tick_count": 1, "tick_interval": 0.0,
    }]
