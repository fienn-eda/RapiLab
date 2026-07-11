"""Zwei (slug "zwei"), a Burst-1 SG supporter, signature weapon done
(dollskills). Fienn's Zwei has hers completed.

Modeled (DPS-relevant):
- Pierce Equation (dollskills[0]): on Full Burst enter, squad Pierce Damage up
  for 1 round (a bullet-count grant - each ally's next shot) plus a separate
  squad Pierce Damage up for 10 sec.
- Frame Analysis (dollskills[1]): on Full Burst enter, squad Crit Rate up.
- Overcharge Formula (dollskills[2], her burst): squad Pierce Damage up.

Not modeled / deferred:
- Frame Analysis's Cover HP recovery (survival, no DPS effect).
- Pierce Equation's normal-attack-during-Full-Burst stacking Pierce (up to 3),
  and Frame Analysis's "normal attack while in Pierce Attacks 101" stacking Crit
  Rate: both need per-shot triggers gated to a Full-Burst window / a self status,
  which isn't modeled yet.
- Overcharge Formula's self weapon transformation (Pierce Attacks 101).
Note pierce is treated as general damage-up (see raid_simulator).
"""
from app.skill_rules._helpers import buff_rule, round_buff_rule


def build_zwei_rules(values):
    pierce = values["pierce_equation"]
    frame = values["frame_analysis"]
    overcharge = values["overcharge_formula"]
    round_pierce = float(pierce["description_value_01"]) / 100
    round_pierce_rounds = int(pierce["description_value_02"])
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
        # Pierce for 1 round: each ally's next shot (bullet-count grant).
        round_buff_rule("full_burst_enter",
                        [("pierce_damage_up", round_pierce, "squad")],
                        shots=round_pierce_rounds),
        buff_rule("own_burst_activate", [
            ("pierce_damage_up", burst_pierce, "squad", burst_pierce_duration),
        ]),
    ]
