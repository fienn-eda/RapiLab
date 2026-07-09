"""Moran (slug "moran"), a Burst-1 AR Defender, signature weapon done
(dollskills). Fienn's Moran has hers completed.

Modeled (DPS-relevant):
- Leave It To Me! (dollskills[1]): on Full Burst enter while in Fervor, squad
  burst-cooldown reduction.
- Fair and Square! (dollskills[2], her burst): squad ATK up as a flat bonus
  scaled off Moran's own ATK.

Assumption: Fervor is triggered by "Raptures appear" and is treated as always
active in a raid. Not modeled: the weapon-transformation self damage mode,
DEF / damage-taken / Max-HP survivability buffs, taunts, and the
HP-threshold Perseverance effect.
"""
from app.skill_rules._helpers import buff_rule, cdr_pulse_rule


def build_moran_rules(values):
    leave = values["leave_it_to_me"]
    fair = values["fair_and_square"]
    caster_atk = values["caster_atk"]
    cdr_sec = float(leave["description_value_10"])
    atk_bonus = caster_atk * float(fair["description_value_09"]) / 100
    atk_duration = float(fair["description_value_10"])

    return [
        cdr_pulse_rule("full_burst_enter", cdr_sec),
        buff_rule("own_burst_activate", [("flat_atk", atk_bonus, "squad", atk_duration)]),
    ]
