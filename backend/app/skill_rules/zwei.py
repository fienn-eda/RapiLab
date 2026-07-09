"""Zwei (slug "zwei"), a Burst-1 SG supporter, signature weapon done
(dollskills). Fienn's Zwei has hers completed.

Modeled (DPS-relevant):
- Pierce Equation (dollskills[0]): on Full Burst enter, squad Pierce Damage up.
- Frame Analysis (dollskills[1]): on Full Burst enter, squad Crit Rate up.
- Overcharge Formula (dollskills[2], her burst): squad Pierce Damage up.

Not modeled: the per-round and normal-attack-stacking pierce/crit variants
(round-count durations and normal-attack-during-full-burst triggers aren't
modeled), Overcharge Formula's self weapon transformation, and cover-HP
recovery. Note pierce is treated as general damage-up (see raid_simulator).
"""
from app.skill_rules._helpers import buff_rule


def build_zwei_rules(values):
    pierce = values["pierce_equation"]
    frame = values["frame_analysis"]
    overcharge = values["overcharge_formula"]
    fb_pierce = float(pierce["description_value_03"]) / 100
    fb_pierce_duration = float(pierce["description_value_04"])
    fb_crit_rate = float(frame["description_value_03"]) / 100
    fb_crit_rate_duration = float(frame["description_value_04"])
    burst_pierce = float(overcharge["description_value_03"]) / 100
    burst_pierce_duration = float(overcharge["description_value_04"])

    return [
        buff_rule("full_burst_enter", [
            ("pierce_damage_up", fb_pierce, "squad", fb_pierce_duration),
            ("crit_rate", fb_crit_rate, "squad", fb_crit_rate_duration),
        ]),
        buff_rule("own_burst_activate", [
            ("pierce_damage_up", burst_pierce, "squad", burst_pierce_duration),
        ]),
    ]
