"""Miranda (slug "miranda"), a Burst-1 SMG supporter, signature weapon done
(dollskills). Fienn's Miranda has hers completed.

Modeled (DPS-relevant):
- Wake Up! (dollskills[1]): on Full Burst enter, squad Crit Damage up, plus
  self Crit Rate and Attack Damage up.
- Powering Up! (dollskills[2], her burst): ATK and Crit Damage up.

Approximation: Powering Up! and part of Wake Up! target "the N allies with the
highest final ATK", which this engine's scope model (self/squad/element)
can't express. They're applied squad-wide instead - the intended beneficiary
(the deck's main attacker) is buffed correctly, and the extra application to
low-damage supporters barely affects total output. This slightly over-applies
when a deck runs two damage dealers.

Not modeled: Health Up! (dollskills[0]) - Hit Rate (no DPS effect here) and a
self ATK buff gated on a normal-attack counter, which needs the deferred
attack-count trigger; and Wake Up!'s highest-ATK-ally per-round crit rate.
"""
from app.skill_rules._helpers import buff_rule


def build_miranda_rules(values):
    wake = values["wake_up"]
    power = values["powering_up"]
    squad_crit_damage = float(wake["description_value_01"]) / 100
    crit_damage_duration = float(wake["description_value_02"])
    self_crit_rate = float(wake["description_value_03"]) / 100
    self_crit_rate_duration = float(wake["description_value_04"])
    self_attack_damage = float(wake["description_value_05"]) / 100
    self_attack_damage_duration = float(wake["description_value_06"])
    burst_atk = float(power["description_value_02"]) / 100
    burst_atk_duration = float(power["description_value_03"])
    burst_crit_damage = float(power["description_value_04"]) / 100
    burst_crit_damage_duration = float(power["description_value_05"])

    return [
        buff_rule("full_burst_enter", [
            ("other_critical_damage_sources", squad_crit_damage, "squad", crit_damage_duration),
            ("crit_rate", self_crit_rate, "self", self_crit_rate_duration),
            ("attack_damage_up", self_attack_damage, "self", self_attack_damage_duration),
        ]),
        # "highest-ATK allies" approximated as squad (see module docstring)
        buff_rule("own_burst_activate", [
            ("atk_percent", burst_atk, "squad", burst_atk_duration),
            ("other_critical_damage_sources", burst_crit_damage, "squad", burst_crit_damage_duration),
        ]),
    ]
