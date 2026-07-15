"""Dorothy: Serendipity (slug "dorothy-serendipity"), a Burst-3 Water SG
attacker. Base skills. Collected from lootandwaifus.com. Her main lever is a
self Attack Speed buff (Phase S), which raises her shotgun's fire rate and thus
her normal-attack damage volume.

Modeled (DPS-relevant):
- Radiant Wings (skills[1]): self Pierce Damage +55.08% continuously (from battle
  start, permanent). During Full Burst, self ATK +75.24% - modeled as a
  full_burst_enter buff lasting the Full Burst window (`FULL_BURST_DURATION`).
- False Salvation (skills[2], her burst): self Attack Speed +65% and self ATK
  +88.12%, both for 15 sec. Attack Speed feeds the Phase S shot-cadence model, so
  her shotgun fires ~65% more often for those 15 sec. Her burst has no nuke.

Not modeled / deferred:
- Number of pellets +5 (False Salvation) and the pellet-count triggers of Flash
  (skills[0], "when hitting with 80/160 pellets": Pierce, fixed pellet count,
  Attack Damage, Pierce range) - the engine has no per-pellet shotgun model.
- Hit Rate buffs (Radiant Wings +40.68%, Flash +98.18%) - Hit Rate is not
  consumed by the engine.
"""
from app.burst_cycle import FULL_BURST_DURATION
from app.skill_rules._helpers import buff_rule


def build_dorothy_serendipity_rules(values):
    radiant_wings = values["radiant_wings"]
    false_salvation = values["false_salvation"]

    self_pierce = float(radiant_wings["description_value_01"]) / 100
    fb_atk = float(radiant_wings["description_value_02"]) / 100
    attack_speed = float(false_salvation["description_value_01"]) / 100
    attack_speed_duration = float(false_salvation["description_value_02"])
    burst_atk = float(false_salvation["description_value_03"]) / 100
    burst_atk_duration = float(false_salvation["description_value_04"])

    return [
        buff_rule("battle_start", [("pierce_damage_up", self_pierce, "self", None)]),
        buff_rule("full_burst_enter", [("atk_percent", fb_atk, "self", FULL_BURST_DURATION)]),
        buff_rule("own_burst_activate", [
            ("atk_percent", burst_atk, "self", burst_atk_duration),
            ("attack_speed_percent", attack_speed, "self", attack_speed_duration),
        ]),
    ]
