"""Marciana: Marine Study (slug "marciana-marine-study"), a Burst-3 Iron AR
attacker. Base skills. Collected from lootandwaifus.com.

Encoded under two solo-raid assumptions confirmed by Fienn (2026-07-16):
- Rapture count is always 1 (the boss), so her rapture-count-gated bullets
  simplify: the "3 or fewer Raptures" condition is always met (Whistle keeps
  filling to its cap) and the "6 or more Raptures" Penguin Emergency Dispatch
  nuke never fires (skipped).
- "Flagged Target" = the enemy with the highest Max HP = the boss, and
  "High-Risk Target" is just an effect name; the real gate on the High-Risk
  bullets is "Electric Code enemies" (boss_is_element - gap #5).

Modeled (DPS-relevant):
- Whistle (Penguin Emergency Dispatch): self ATK +32.73% per stack, up to 5
  stacks. Under raptures=1 it starts at 4 stacks and fills to the cap within
  ~5 sec, so it's modeled as a steady-state permanent self atk_percent of
  5 x 32.73% from battle start (the brief ramp is ignored).
- "Elemental Advantage Attack Damage" (Penguin Emergency Dispatch, continuous
  +20.41%; Penguin Spiral burst, +30.97% for 10 sec): this is Element Bonus
  Damage that only counts with elemental advantage (Iron > Electric), so it goes
  in the formula's Element Bonus Damage group (other_elemental_bonus), NOT the
  Attack Damage / Damage-Up group - modeled as other_elemental_bonus gated on an
  Electric boss.
- Penguin Spiral (burst) self Attack Damage +27.45% for 10 sec: unconditional
  attack_damage_up (a general Damage-Up buff, not element-gated).
- Penguin Spiral (burst) High-Risk Target DEF -10.56% for 20 sec against Electric
  Code enemies: squad-scope enemy_def_percent debuff, gated on an Electric boss.
- Flagged Target Designation (Emergency Whistle): on entering Full Burst after
  her own burst, 3789.25% of final ATK as additional damage to the boss - her
  headline nuke. Modeled as an instant nuke on full_burst_enter gated by
  own_burst_fired_this_cycle(); "as additional damage" + Burst 3 (fires at Full
  Burst start) makes it Full Burst Bonus eligible.
- High-Risk 20-normal nuke (Emergency Whistle): 152.68% of final ATK as
  additional damage every 20 normal attacks while the boss is in High-Risk
  Target state. Since High-Risk Target is just the name of the burst's mark on
  an Electric enemy (which her burst keeps re-applying), the state is treated as
  maintained whenever the boss is Electric - so the nuke fires every 20 normal
  attacks (an AR fires ~12/sec, so ~every 1.7 sec) throughout the fight, gated
  only on an Electric boss (plain per_shot "every", NOT a 20-sec window).
  "As additional damage" -> Full Burst Bonus eligible when the shot falls in a
  Full Burst window.

Not modeled / deferred:
- Flagged Target Designation's "Flagged Target: ATK +10.56% for 10 sec" bullet:
  the skill text attaches an ATK buff to the enemy-targeting bullet, so its
  beneficiary (self vs squad) is ambiguous - deferred rather than guessed
  (Fienn, 2026-07-16). Small (+10.56%).
- Flagged Target Designation's second copy of the 3789.25% nuke, triggered "when
  an enemy is neutralized": in a solo raid the boss is only neutralized when the
  fight ends, so this never fires meaningfully.
- Penguin Emergency Dispatch's 214.36% nuke (needs 6+ Raptures) - never fires
  under raptures=1.
- Reload / heating / HP / hit-rate clauses: not damage, not consumed by the
  engine.
"""
from app.skill_rules._helpers import buff_rule, instant_nuke_pulse_rule
from app.squad_engine import boss_is_element, own_burst_fired_this_cycle


SKILL_VALUE_MANIFESTS = {
    "marciana-marine-study": {
        "source": "lootandwaifus",
        "test_module": "test_skill_rules_marciana_marine_study",
        "keys": {
            "emergency_whistle": ("skills", 0),
            "penguin_emergency_dispatch": ("skills", 1),
            "penguin_spiral": ("skills", 2),
        },
        "drop_tokens": {
            "emergency_whistle": [0, 1, 3, 5, 6, 7, 8, 9, 10, 11, 12],
            "penguin_emergency_dispatch": [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14],
            "penguin_spiral": [1, 3],
        },
    },
}


WHISTLE_CAP = 5  # skill text: Whistle "stacks up to 5 times"
BURST_BUFF_DURATION = 10.0  # Penguin Spiral's self buffs last 10 sec
DEF_DEBUFF_DURATION = 20.0  # High-Risk Target DEF debuff lasts 20 sec
HIGH_RISK_NUKE_SHOT_COUNT = 20  # "after landing 20 normal attacks"
ELECTRIC = "Electric"  # her Elemental-Advantage / High-Risk bullets need an Electric boss


def build_marciana_rules(values):
    whistle = values["penguin_emergency_dispatch"]
    spiral = values["penguin_spiral"]
    designation = values["emergency_whistle"]

    whistle_atk = float(whistle["description_value_01"]) / 100 * WHISTLE_CAP
    elem_adv_continuous = float(whistle["description_value_02"]) / 100
    burst_elem_adv = float(spiral["description_value_01"]) / 100
    burst_attack_damage = float(spiral["description_value_02"]) / 100
    def_debuff = float(spiral["description_value_03"]) / 100
    flagged_nuke = float(designation["description_value_01"])

    return [
        buff_rule("battle_start", [("atk_percent", whistle_atk, "self", None)]),
        buff_rule(
            "battle_start",
            [("other_elemental_bonus", elem_adv_continuous, "self", None)],
            condition=boss_is_element(ELECTRIC),
        ),
        buff_rule(
            "own_burst_activate",
            [("attack_damage_up", burst_attack_damage, "self", BURST_BUFF_DURATION)],
        ),
        buff_rule(
            "own_burst_activate",
            [("other_elemental_bonus", burst_elem_adv, "self", BURST_BUFF_DURATION)],
            condition=boss_is_element(ELECTRIC),
        ),
        buff_rule(
            "own_burst_activate",
            [("enemy_def_percent", -def_debuff, "squad", DEF_DEBUFF_DURATION)],
            condition=boss_is_element(ELECTRIC),
        ),
        instant_nuke_pulse_rule(
            "full_burst_enter",
            flagged_nuke,
            condition=own_burst_fired_this_cycle(),
        ),
    ]


def build_marciana_per_shot_rules(values):
    """Per-shot rules (see raid_simulator's `per_shot_rules`): 152.68% of final
    ATK as additional damage every 20 normal attacks while the boss is in
    High-Risk Target state. High-Risk Target is just the burst's mark on an
    Electric enemy, kept re-applied, so it's treated as maintained whenever the
    boss is Electric - a plain "every 20" per-shot trigger gated on an Electric
    boss (an AR fires ~12/sec, so this lands ~every 1.7 sec)."""
    high_risk_nuke = float(values["emergency_whistle"]["description_value_03"])
    return [
        (
            HIGH_RISK_NUKE_SHOT_COUNT,
            "every",
            [instant_nuke_pulse_rule(
                "per_shot", high_risk_nuke,
                condition=boss_is_element(ELECTRIC),
            )],
        ),
    ]
