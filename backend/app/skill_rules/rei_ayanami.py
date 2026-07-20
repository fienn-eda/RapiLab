"""Rei Ayanami (slug "rei-ayanami"), a Burst-3 Fire MG attacker. Base skills
(no signature/Treasure weapon - see deferred note). Collected from
lootandwaifus.com.

Modeled (DPS-relevant):
- Attack Support (skills[1]): on entering Burst stage 3 (full_burst_enter), all
  Fire Code allies (element:Fire scope) gain flat ATK = 25.03% of the caster's
  ATK for 10 sec.
- Annihilation: High Explosives (skills[2], her burst): all Fire Code allies
  gain Attack Damage +48.02% for 10 sec, plus the burst nuke, 990.2% of final
  ATK (`annihilation_burst_percent`).
- Preemptive Subdual (skills[0]): every 100 normal attacks, a 112.37%-of-final-
  ATK nuke on the nearest enemy (gap #1 per_shot `every` mode). "As damage", so
  NOT Full-Burst-Bonus eligible. On the same every-100 trigger, a self Elemental
  Advantage Attack Damage +30.23% for 3 sec: modeled as a REFRESHING
  other_elemental_bonus buff with NO boss gate - the skill text names no
  element, and damage_formula only pays out that group to a unit that already
  holds advantage, so the formula alone decides when it lands (Rei is Fire, so
  vs a Wind boss). See `build_preemptive_subdual_per_shot_rules`.

Not modeled / deferred:
- Attack Support's "Damage dealt to Shield +700.5%" and Annihilation's Shield
  creation (13.44% of Max HP) - shield damage / survivability, not raid DPS.
- Signature/Treasure weapon (dollskills) is available and may change numbers or
  add effects; the base skills are encoded here (a signature variant would be a
  separate dual-slug entry, like drake/drake-signature).
"""
from app.skill_rules._helpers import buff_rule, instant_nuke_pulse_rule, refreshing_buff_rule

SKILL_VALUE_MANIFESTS = {
    "rei-ayanami": {
        "source": "lootandwaifus",
        "test_module": "test_skill_rules_rei_ayanami",
        "keys": {
            "preemptive_subdual": ("skills", 0),
            "attack_support": ("skills", 1),
            "annihilation": ("skills", 2),
        },
        # "Activates when entering Burst stage 3" - the encoder skipped the
        # trigger-phrase "3" when numbering Attack Support's slots.
        "drop_tokens": {"attack_support": [1]},
    },
}

PREEMPTIVE_SUBDUAL_NUKE_SHOT_COUNT = 100  # "after landing 100 normal attacks"


def annihilation_burst_percent(values):
    return float(values["annihilation"]["description_value_05"])


def build_rei_ayanami_rules(values):
    attack_support = values["attack_support"]
    annihilation = values["annihilation"]
    caster_atk = values["caster_atk"]

    fire_atk = float(attack_support["description_value_02"]) / 100 * caster_atk
    fire_atk_duration = float(attack_support["description_value_03"])
    fire_attack_damage = float(annihilation["description_value_03"]) / 100
    fire_attack_damage_duration = float(annihilation["description_value_04"])

    return [
        buff_rule("full_burst_enter", [("flat_atk", fire_atk, "element:Fire", fire_atk_duration)]),
        buff_rule(
            "own_burst_activate",
            [("attack_damage_up", fire_attack_damage, "element:Fire", fire_attack_damage_duration)],
        ),
    ]


def build_preemptive_subdual_per_shot_rules(values):
    """Every 100 normal attacks (gap #1 per_shot `every` mode): a 112.37%-of-
    final-ATK nuke on the nearest enemy, plus a self Elemental Advantage Attack
    Damage buff (+30.23% for 3 sec). Both clauses count to 100 on the same
    normal-attack cadence, so they share one trigger entry. The buff REFRESHES
    (each re-proc within the 3s window renews it rather than stacking) and lands
    in the Element Bonus group, ungated: the skill text names no element, and
    damage_formula already restricts that group to a unit holding elemental
    advantage - Rei is Fire, so it pays out against a Wind boss."""
    preemptive = values["preemptive_subdual"]
    threshold = int(float(preemptive["description_value_04"]))
    nuke_percent = float(preemptive["description_value_05"])
    elem_adv = float(preemptive["description_value_02"]) / 100
    elem_adv_duration = float(preemptive["description_value_03"])
    return [(threshold, "every", [
        instant_nuke_pulse_rule("per_shot", nuke_percent),
        refreshing_buff_rule(
            "per_shot",
            [("other_elemental_bonus", elem_adv, "self", elem_adv_duration)],
        ),
    ])]
