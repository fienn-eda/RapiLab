"""Ludmilla: Winter Owner (slug "ludmilla-winter-owner"), a Burst-3 Water Machine
Gun attacker. Base skills.

Modeled (DPS-relevant):
- The Queen's Gaze (skills[0]): every 60 normal attacks, a squad Damage-Taken
  debuff (12.56% for 3s, refreshing) plus a 158.43%-of-final-ATK nuke (per-shot).
- Snowstorm (skills[1]): on Full Burst enter, self Crit Rate +14.6% for 10s.
- Guiding Lantern (skills[2], her burst): self ATK +62.54% for 10s and Reload
  Speed +67.2% for 20s (a buffs-only burst - no nuke).

- Snowstorm (skills[1]) also fires a 109.64% nuke every 60 CORE hits. The
  engine has no discrete "core hit" event (core damage is a uniform
  coefficient applied to every hit), so this is counted off her real shot
  timeline and gated on the boss actually having an exploitable core
  (`boss_core_hittable`, the cinderella-crystal-wave precedent). Fienn
  approved the core-hittable gate on 2026-07-20.

  Counting shots is deliberately preferred over a fixed 1-sec timer, which was
  the other candidate: her MG's 60 rounds/sec only holds while a magazine
  lasts, and she spends 3 sec reloading every 300 rounds, so a wall-clock tick
  would fire ~60% more often than she can actually land the hits. Riding the
  shot timeline also means max-ammo and reload-speed buffs move the cadence
  the way they do in game.

  The standing approximation is that while the core IS hittable every shot
  counts as a core hit - an over-estimate whose size is exactly the deck's
  real core-hit rate, and the same convention the rest of the engine uses.

- The Queen's Gaze's second bullet, "when landing 60 normal attack(s), Reloads
  20 round(s) of ammunition": an `AmmoRefund` off her own slots
  (`queens_gaze_ammo_refund`), ungated - the bullet names no boss condition.
  Rounds handed back mid-magazine are not a Max Ammo percentage: what a refund
  is worth depends on how much of the magazine is left when it lands, and an
  earlier reload shifts every later one against the Full Burst window.

  **Wiring it LOWERED her damage, and that is the model working.** In the
  per-slug sweep shell she goes 9,766 -> 9,930 normal attacks (+1.68%) while her
  own damage falls 0.65%, because average damage per shot drops 2.25%: the
  reload time a refund buys back is the time she was NOT firing, and her burst
  hands her Reload Speed +67.2% for 20 sec, so the reloads near her Full Burst
  were already cheap and the ones it actually shortens sit outside the window.
  The shots it adds therefore miss the Full Burst bonus. Same non-monotonicity
  the Tactical Bear cube showed. Do not read the drop as a bug and revert it.

Not modeled / deferred:
- Nothing. Every bullet of all three skills is encoded.
"""
from app.attack_rate import AmmoRefund
from app.skill_rules._helpers import buff_rule, instant_nuke_pulse_rule, refreshing_buff_rule
from app.squad_engine import boss_core_hittable


SKILL_VALUE_MANIFESTS = {
    "ludmilla-winter-owner": {
        "source": "lootandwaifus",
        "test_module": "test_skill_rules_burst3_eb2",
        "keys": {
            "queens_gaze": ("skills", 0),
            "snowstorm": ("skills", 1),
            "guiding_lantern": ("skills", 2),
        },
    },
}


def build_ludmilla_rules(values):
    snowstorm = values["snowstorm"]
    guiding = values["guiding_lantern"]
    fb_crit_rate = float(snowstorm["description_value_03"]) / 100
    fb_crit_rate_duration = float(snowstorm["description_value_04"])
    burst_atk = float(guiding["description_value_01"]) / 100
    burst_atk_duration = float(guiding["description_value_02"])
    burst_reload = float(guiding["description_value_03"]) / 100
    burst_reload_duration = float(guiding["description_value_04"])

    return [
        buff_rule("full_burst_enter", [("crit_rate", fb_crit_rate, "self", fb_crit_rate_duration)]),
        buff_rule("own_burst_activate", [
            ("atk_percent", burst_atk, "self", burst_atk_duration),
            ("reload_speed_percent", burst_reload, "self", burst_reload_duration),
        ]),
    ]


def queens_gaze_ammo_refund(values):
    """"Activates when landing 60 normal attack(s). Affects self. Reloads 20
    round(s) of ammunition."

    Both numbers are the skill's own slots, so a rebalance moves them. Unlike
    EVE's Eagle Eye the bullet carries no boss condition, so the registry
    registers it with no required element.
    """
    queens = values["queens_gaze"]
    return AmmoRefund(
        every_shots=int(float(queens["description_value_05"])),
        rounds=int(float(queens["description_value_06"])),
    )


def build_ludmilla_per_shot_rules(values):
    queens = values["queens_gaze"]
    normal_count = int(queens["description_value_01"])
    damage_taken = float(queens["description_value_02"]) / 100
    damage_taken_duration = float(queens["description_value_03"])
    nuke = float(queens["description_value_04"])

    snowstorm = values["snowstorm"]
    core_count = int(snowstorm["description_value_01"])
    core_nuke = float(snowstorm["description_value_02"])

    return [
        (normal_count, "every", [
            refreshing_buff_rule("per_shot", [("damage_taken_up", damage_taken, "squad", damage_taken_duration)]),
            instant_nuke_pulse_rule("per_shot", nuke),
        ]),
        # Snowstorm counts CORE hits, which the engine has no discrete event for
        # (core damage is a uniform coefficient). Gated on the boss actually
        # having an exploitable core and then counted off her real shot
        # timeline, per Fienn 2026-07-20 - see the module docstring.
        (core_count, "every", [
            instant_nuke_pulse_rule("per_shot", core_nuke,
                                    condition=boss_core_hittable()),
        ]),
    ]
