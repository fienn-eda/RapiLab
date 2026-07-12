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
- Flawless Glass's Charge Speed +100% - not a damage stat.
"""
from app.effects import ResourceSpec
from app.skill_rules._helpers import buff_rule, instant_nuke_pulse_rule

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
