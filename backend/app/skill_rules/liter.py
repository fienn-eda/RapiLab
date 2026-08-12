"""Liter (slug "liter"), a Burst-1 SMG supporter. Base skills (no signature).

Modeled (DPS-relevant):
- Liter Boost (skills[0]), two bullets that both ESCALATE: "Effect changes
  according to the number of activation times. Previous effects trigger
  repeatedly." The Nth activation applies every tier unlocked so far, so the
  tiers ADD and the sum is the STEADY state rather than the opening value.
  - On Full Burst enter: squad burst-cooldown reduction, 2.34 -> 5.04 -> 8.21
    sec. Same wording and the same tier values as Volume's Drop the Beat, whose
    cumulative shape Fienn's in-game range measurement settled (2026-07-27);
    Liter's own cadence has not been timed separately, so she rides that
    reading. These three slots carry the same numbers at every skill level -
    the cooldown half does not scale with investment, unlike the buffs below.
  - On her own burst: Max Ammo (once), + Critical Damage (twice), + ATK (three
    times), each for its own duration slot.
- Double Boost (skills[2], her burst): squad ATK up. A separate bullet, so it
  lands on every use regardless of where Liter Boost's ramp stands.

Not modeled:
- Volt Boost (skills[1]): cover-HP restoration - survivability, no DPS.
"""
from app.skill_rules._helpers import (buff_rule, escalating_buff_rule,
                                      escalating_cdr_rule)

SKILL_VALUE_MANIFESTS = {
    "liter": {
        "source": "dotgg",
        "test_module": "test_skill_rules_burst1_batch1",
        "keys": {
            "liter_boost": ("skills", 0),
            "double_boost": ("skills", 2),
        },
    },
}


def build_liter_rules(values):
    boost = values["liter_boost"]
    double = values["double_boost"]
    cdr_tiers = [float(boost[f"description_value_0{slot}"]) for slot in (1, 2, 3)]
    on_burst_tiers = [
        [("max_ammo_percent", float(boost["description_value_04"]) / 100, "squad",
          float(boost["description_value_05"]))],
        [("other_critical_damage_sources", float(boost["description_value_06"]) / 100, "squad",
          float(boost["description_value_07"]))],
        [("atk_percent", float(boost["description_value_08"]) / 100, "squad",
          float(boost["description_value_09"]))],
    ]
    double_atk = float(double["description_value_01"]) / 100
    double_duration = float(double["description_value_02"])

    return [
        escalating_cdr_rule("full_burst_enter", cdr_tiers),
        # Each tier's 5-sec window is far shorter than her burst cooldown, so
        # re-applications never overlap and plain adds are correct.
        escalating_buff_rule("own_burst_activate", on_burst_tiers),
        buff_rule("own_burst_activate", [
            ("atk_percent", double_atk, "squad", double_duration),
        ]),
    ]
