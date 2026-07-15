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
  NOT Full-Burst-Bonus eligible. See `build_preemptive_subdual_per_shot_rules`.

Not modeled / deferred:
- Preemptive Subdual's self "Elemental Advantage Attack Damage +30.23% for 3
  sec" (every 100 normals) - Elemental Advantage buffs only apply when the boss
  is element-disadvantaged to her Fire, which needs boss_element (engine gap
  #5). The unconditional nuke on the same trigger is modeled; this conditional
  buff is deferred.
- Attack Support's "Damage dealt to Shield +700.5%" and Annihilation's Shield
  creation (13.44% of Max HP) - shield damage / survivability, not raid DPS.
- Signature/Treasure weapon (dollskills) is available and may change numbers or
  add effects; the base skills are encoded here (a signature variant would be a
  separate dual-slug entry, like drake/drake-signature).
"""
from app.skill_rules._helpers import buff_rule, instant_nuke_pulse_rule

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
    """gap #1: every 100 normal attacks, a 112.37%-of-final-ATK nuke. The
    Elemental Advantage self buff on the same trigger is deferred (gap #5)."""
    preemptive = values["preemptive_subdual"]
    threshold = int(float(preemptive["description_value_04"]))
    nuke_percent = float(preemptive["description_value_05"])
    return [(threshold, "every", [instant_nuke_pulse_rule("per_shot", nuke_percent)])]
