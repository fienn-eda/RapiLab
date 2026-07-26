"""Quency: Escape Queen (slug "quency-escape-queen"), a Burst-3 Water
Submachine Gun attacker. Base skills.

Modeled (DPS-relevant):
- Explore Route (skills[1]) + Secure Route (skills[0]): a 3-stage stack chain
  (every 2 normal attacks fills the current stage; each stage's fill only
  starts once the previous stage is AT its cap) that ends in self ATK +2.45%
  per stage-1 stack (cap 10) + 4.9% per stage-2 stack (cap 10) + 7.36% per
  stage-3 stack (cap 5) = 110.3% total ATK, plus, once each respective stage
  is AT max, permanent self Distributed Damage +49.58% (stage 1) / Core Damage
  +25.25% (stage 2) / Crit Rate +16.73% (stage 3). SMG fires 20/s and the fill
  cadence (every 2 shots = 0.1s) is far faster than each stage's own decay
  window (0.5-2s), so once a stage first caps it stays capped continuously for
  the rest of the fight - modeled as a STEADY-STATE approximation (all of it
  permanent from battle_start; the ~2.5s real ramp to fully stack is
  negligible against a raid's length). Hit Rate per stage is inert, not
  modeled.
- The Great Thief (skills[2], her burst): self Attack Damage +57.08% and
  Reload Speed +25.87% for 10 sec, plus a 1736.31%-of-final-ATK burst nuke
  dealing Distributed Damage - typed "distributed" in the registry's
  _BURST_DAMAGE_TYPES, which is what lets `distributed_damage_up` reach it
  (her own Secure Route Stage-1 buff feeds it, as do Mast's and Anchor's).
"""
from app.skill_rules._helpers import buff_rule


SKILL_VALUE_MANIFESTS = {
    "quency-escape-queen": {
        "source": "lootandwaifus",
        "test_module": "test_skill_rules_quency_escape_queen",
        "keys": {
            "secure_route": ("skills", 0),
            "the_great_thief": ("skills", 2),
        },
        "drop_tokens": {
            "secure_route": [0, 2, 4],
        },
    },
}


STEADY_STATE_ATK = 2.45 * 10 + 4.9 * 10 + 7.36 * 5  # Explore Route stages 1-3, fully stacked


def the_great_thief_burst_percent(values):
    return float(values["the_great_thief"]["description_value_05"])


def build_quency_rules(values):
    secure = values["secure_route"]
    thief = values["the_great_thief"]

    distributed_damage = float(secure["description_value_01"]) / 100
    core_damage = float(secure["description_value_02"]) / 100
    crit_rate = float(secure["description_value_03"]) / 100

    self_attack_damage = float(thief["description_value_01"]) / 100
    self_attack_damage_duration = float(thief["description_value_02"])
    reload_speed = float(thief["description_value_03"]) / 100
    reload_speed_duration = float(thief["description_value_04"])

    return [
        buff_rule("battle_start", [
            ("atk_percent", STEADY_STATE_ATK / 100, "self", None),
            ("distributed_damage_up", distributed_damage, "self", None),
            ("other_core_damage_sources", core_damage, "self", None),
            ("crit_rate", crit_rate, "self", None),
        ]),
        buff_rule("own_burst_activate", [
            ("attack_damage_up", self_attack_damage, "self", self_attack_damage_duration),
            ("reload_speed_percent", reload_speed, "self", reload_speed_duration),
        ]),
    ]
