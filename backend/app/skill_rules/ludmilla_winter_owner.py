"""Ludmilla: Winter Owner (slug "ludmilla-winter-owner"), a Burst-3 Water Machine
Gun attacker. Base skills.

Modeled (DPS-relevant):
- The Queen's Gaze (skills[0]): every 60 normal attacks, a squad Damage-Taken
  debuff (12.56% for 3s, refreshing) plus a 158.43%-of-final-ATK nuke (per-shot).
- Snowstorm (skills[1]): on Full Burst enter, self Crit Rate +14.6% for 10s.
- Guiding Lantern (skills[2], her burst): self ATK +62.54% for 10s and Reload
  Speed +67.2% for 20s (a buffs-only burst - no nuke).

Not modeled / deferred:
- Snowstorm's "60 Core hits -> 109.64% nuke": it counts CORE hits, not shots.
  Approximating it as every-60-shots would fire the nuke as often as the normal
  counter and overstate it (core hits accrue slower than shots), so it's deferred
  rather than approximated. (The on-core Attack Damage buff case is milder; a
  repeated nuke is not.)
- The Queen's Gaze self reload of 20 rounds - ammo QoL, not a % buff.
"""
from app.skill_rules._helpers import buff_rule, instant_nuke_pulse_rule, refreshing_buff_rule


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


def build_ludmilla_per_shot_rules(values):
    queens = values["queens_gaze"]
    normal_count = int(queens["description_value_01"])
    damage_taken = float(queens["description_value_02"]) / 100
    damage_taken_duration = float(queens["description_value_03"])
    nuke = float(queens["description_value_04"])

    return [
        (normal_count, "every", [
            refreshing_buff_rule("per_shot", [("damage_taken_up", damage_taken, "squad", damage_taken_duration)]),
            instant_nuke_pulse_rule("per_shot", nuke),
        ]),
    ]
