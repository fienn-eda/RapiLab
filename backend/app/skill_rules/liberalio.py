"""Liberalio (slug "liberalio"), a Burst-3 Wind Sniper Rifle attacker. Base skills.

Every SR shot is a Full Charge, and in a solo raid the shots land on the boss
(the "stage target") and its core, so her Full-Charge-triggered effects are
modeled via per-shot rules (see build_liberalio_per_shot_rules).

Modeled (DPS-relevant):
- Calm Depths (skills[0]): on Full Burst enter, self ATK +160% for 3s; on every
  Full Charge on the core, self Attack Damage +20.83% for 60s (refreshing);
  the first 5 Full Charges each deal 40.5% of final ATK as additional damage.
- Strange Currents (skills[1]): the first Full Charge on the boss grants Raging
  Current - self Attack Damage +231% continuously (permanent; only removed by
  Gentle Current, which requires hitting a non-boss Rapture - see deferred).
- Submerged World (skills[2], her burst): self Attack Damage +50% for 10s, and a
  925%-of-final-ATK burst nuke.

Not modeled / deferred:
- Gentle Current (Strange Currents' non-boss-target branch): fixes charge time
  and removes Raging Current - assumed never triggered, since solo-raid fire stays
  on the boss. Its Charge-Time effect is inert anyway (attack rate not skill-driven).
- Calm Depths' Charge Speed buff on the lowest-ATK Burst-3 ally (Charge Speed is
  inert in this engine) and its immunity effects.

Approximation: the on-core Attack Damage is applied on every Full Charge (core
hits aren't tracked per-shot), consistent with how core damage is handled globally.
"""
from app.skill_rules._helpers import buff_rule, instant_nuke_pulse_rule, refreshing_buff_rule


def submerged_world_burst_percent(values):
    return float(values["submerged_world"]["description_value_03"])


def build_liberalio_rules(values):
    calm = values["calm_depths"]
    submerged = values["submerged_world"]
    fb_atk = float(calm["description_value_01"]) / 100
    fb_atk_duration = float(calm["description_value_02"])
    burst_attack_damage = float(submerged["description_value_01"]) / 100
    burst_attack_damage_duration = float(submerged["description_value_02"])

    return [
        buff_rule("full_burst_enter", [("atk_percent", fb_atk, "self", fb_atk_duration)]),
        buff_rule("own_burst_activate", [("attack_damage_up", burst_attack_damage, "self", burst_attack_damage_duration)]),
    ]


def build_liberalio_per_shot_rules(values):
    calm = values["calm_depths"]
    strange = values["strange_currents"]
    raging_attack_damage = float(strange["description_value_01"]) / 100
    on_core_attack_damage = float(calm["description_value_03"]) / 100
    on_core_duration = float(calm["description_value_04"])
    additional = float(calm["description_value_05"])
    additional_times = int(calm["description_value_06"])

    rules = [
        # Raging Current: first Full Charge on the boss -> permanent Attack Damage.
        (1, "after", [buff_rule("per_shot", [("attack_damage_up", raging_attack_damage, "self", None)])]),
        # On-core Attack Damage: every Full Charge, refreshing its 60s window.
        (1, "every", [refreshing_buff_rule("per_shot", [("attack_damage_up", on_core_attack_damage, "self", on_core_duration)])]),
    ]
    # The first N Full Charges each deal additional damage (one "after n" per hit).
    for n in range(1, additional_times + 1):
        rules.append((n, "after", [instant_nuke_pulse_rule("per_shot", additional)]))
    return rules
