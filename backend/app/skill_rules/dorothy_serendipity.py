"""Dorothy: Serendipity (slug "dorothy-serendipity"), a Burst-3 Water SG
attacker. Base skills. Collected from lootandwaifus.com. Her main lever is a
self Attack Speed buff (Phase S), which raises her shotgun's fire rate and thus
her normal-attack damage volume.

Modeled (DPS-relevant):
- Radiant Wings (skills[1]): self Pierce Damage +55.08% continuously (from battle
  start, permanent). During Full Burst, self ATK +75.24% and self Hit Rate
  +40.68% - modeled as full_burst_enter buffs lasting until the open Full Burst
  window closes (falls back to `FULL_BURST_DURATION` for a context without a
  burst cycle). +40.68% narrows her shotgun's 250px spread to 157.5px, so on a
  50px core her Full Burst share goes 4.0% -> 10.1%.
- False Salvation (skills[2], her burst): self Attack Speed +65% and self ATK
  +88.12%, both for 15 sec. Attack Speed feeds the Phase S shot-cadence model, so
  her shotgun fires ~65% more often for those 15 sec. Her burst has no nuke.

Not modeled / deferred:
- Number of pellets +5 (False Salvation) and the pellet-count triggers of Flash
  (skills[0], "when hitting with 80/160 pellets": Pierce, fixed pellet count,
  Attack Damage +72%, Pierce range, **and Hit Rate +98.18% for 3 round(s)**) -
  the engine has no per-pellet shotgun model. Her shot fires 10 pellets
  (`shot_detail.shot_count`), so 80 pellets LOOKS like 8 shots, but two things
  the engine cannot see sit between those numbers: how many of the 10 actually
  hit the target is a play condition (the same term gap #21 calls p_조준), and
  the buff itself fixes the pellet count at 1 for its own 3 rounds, which
  changes the rate of the next accumulation. Approximating it onto a shot
  counter would be inventing both. Fienn ruled it deferred (2026-08-07).
  Note this is the one bullet that would take her past the 110% singularity -
  40.68 + 98.18 = 138.86% collapses an SG's spread to a point and puts every
  round on the core. The design doc's §6 reading of her as this model's biggest
  winner therefore describes a build the engine does NOT yet reach.
"""
from app.effects import Effect
from app.skill_rules._helpers import buff_rule, full_burst_window_length
from app.squad_engine import SkillRule


SKILL_VALUE_MANIFESTS = {
    "dorothy-serendipity": {
        "source": "lootandwaifus",
        "test_module": "test_skill_rules_dorothy_serendipity",
        "keys": {
            "radiant_wings": ("skills", 1),
            "false_salvation": ("skills", 2),
        },
    },
}


def build_dorothy_serendipity_rules(values):
    radiant_wings = values["radiant_wings"]
    false_salvation = values["false_salvation"]

    self_pierce = float(radiant_wings["description_value_01"]) / 100
    fb_atk = float(radiant_wings["description_value_02"]) / 100
    fb_hit_rate = float(radiant_wings["description_value_03"]) / 100
    attack_speed = float(false_salvation["description_value_01"]) / 100
    attack_speed_duration = float(false_salvation["description_value_02"])
    burst_atk = float(false_salvation["description_value_03"]) / 100
    burst_atk_duration = float(false_salvation["description_value_04"])

    def apply_full_burst_buffs(context, caster_slug, time, registry):
        window = full_burst_window_length(context, time)
        registry.add(
            Effect("atk_percent", fb_atk, "self", window, caster_slug),
            applied_at=time,
        )
        registry.add(
            Effect("hit_rate", fb_hit_rate, "self", window, caster_slug),
            applied_at=time,
        )

    return [
        buff_rule("battle_start", [
            ("pierce_damage_up", self_pierce, "self", None),
            # Flash grants Pierce for 3 round(s) after 80 pellets, which her
            # shotgun re-earns continuously; held permanent alongside the
            # Pierce Damage the same kit gives her.
            ("has_pierce", 1.0, "self", None),
        ]),
        SkillRule(trigger="full_burst_enter", action=apply_full_burst_buffs),
        buff_rule("own_burst_activate", [
            ("atk_percent", burst_atk, "self", burst_atk_duration),
            ("attack_speed_percent", attack_speed, "self", attack_speed_duration),
        ]),
    ]
