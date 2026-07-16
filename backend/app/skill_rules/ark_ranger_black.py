"""Ark Ranger Black (slug "ark-ranger-black"), a Burst-3 Wind AR attacker.
Base skills. Her damage is almost entirely sustained-typed DoTs gated on
Transformation, which is driven by a self-depleting battery.

Modeled as a floor/ceiling bracket selected by BossProfile.part_destructible
(see docs/superpowers/specs/2026-07-16-ark-ranger-black-transformation-design.md):
- floor (no part-destruction): transformation window [burst, burst+D], where
  D = post_transform_battery / (decay% / decay_interval) = 50 / (1/0.2) = 10 s.
- ceiling (part-destruction gimmick): permanent transformation.

Modeled (DPS-relevant):
- Transform! (skills[0]): while transformed, ATK +156.19%. Floor: applied at
  own_burst_activate for D sec. Ceiling: permanent from battle_start.
- Transform! per-30-normals: Sustained Damage +59.6% for 5 sec (per_shot, see
  build_ark_ranger_per_shot_rules) - both branches.
- Ark Black Collider (skills[1]): 45.87% sustained DoT while transformed. Floor:
  burst-anchored D-tick DoT; ceiling: whole-fight periodic 1s DoT (see
  build_ark_ranger_dots / build_ark_ranger_ceiling_collider).
- Ultimate! (skills[2], burst): Meteor 266.69% sustained DoT x10 (both
  branches); self Sustained Damage +135.83% for 10 sec (both branches).

Not modeled / deferred:
- Part-destruction battery fill (no enemy-part concept) - the reason for the
  floor/ceiling flag.
- Skill 2 Full-Burst "Wind Code allies with assault rifles: Sustained Damage
  +77.5%" - needs gap #3 (weapon+element scope); deferred to avoid overestimation.
- Damage to Parts +20% (skill 1) - situational part damage, not raid DPS.
"""
from app.skill_rules._helpers import buff_rule
from app.squad_engine import boss_part_destructible, not_condition


def transformation_window_seconds(values):
    """Public: seconds a floor-branch transformation lasts, derived from the
    skill values (post-transform battery drained at decay%/interval)."""
    transform = values["transform"]
    ultimate = values["ultimate"]
    post_transform = float(ultimate["description_value_01"])
    decay_pct = float(transform["description_value_04"])
    decay_interval = float(transform["description_value_05"])
    return post_transform / (decay_pct / decay_interval)


def build_ark_ranger_black_rules(values):
    transform = values["transform"]
    ultimate = values["ultimate"]
    atk = float(transform["description_value_06"]) / 100
    window = transformation_window_seconds(values)
    self_sustained = float(ultimate["description_value_04"]) / 100
    self_sustained_duration = float(ultimate["description_value_05"])

    floor = not_condition(boss_part_destructible())
    ceiling = boss_part_destructible()

    return [
        # ATK +156.19% while transformed - floor: window buff on burst.
        buff_rule("own_burst_activate", [("atk_percent", atk, "self", window)], condition=floor),
        # ceiling: permanent from battle start.
        buff_rule("battle_start", [("atk_percent", atk, "self", None)], condition=ceiling),
        # Burst self Sustained Damage +135.83% for 10s - both branches.
        buff_rule("own_burst_activate", [("sustained_damage_up", self_sustained, "self", self_sustained_duration)]),
    ]
