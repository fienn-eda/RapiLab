"""Miranda (slug "miranda"), a Burst-1 SMG supporter, signature weapon done
(dollskills). Fienn's Miranda has hers completed.

Modeled (DPS-relevant):
- Health Up! (dollskills[0]): after every 30 normal attacks, self ATK up (via
  per_shot_rules - see build_health_up_rules).
- Wake Up! (dollskills[1]): on Full Burst enter, squad Crit Damage up, self Crit
  Rate + Attack Damage up, and Crit Rate up on the single highest-final-ATK ally
  for 1 round.
- Powering Up! (dollskills[2], her burst): ATK + Crit Damage up on the 2 allies
  with the highest final ATK (except caster).

The highest-final-ATK targets are resolved live at application time
(SquadContext.top_atk_slugs), so Powering Up (her burst, tier 1) is reflected in
the ranking when Wake Up (Full Burst enter, tier 3) fires later that cycle. "for
1 round" is a bullet-count duration: the buff covers exactly the target's next
shot (see round_buff_rule / raid_simulator's round-grant handling).

Not modeled: Health Up!'s two Hit Rate steps - Hit Rate is not consumed by this
engine's damage model, so encoding it would be inert.
"""
from app.skill_rules._helpers import (
    buff_rule,
    highest_atk_buff_rule,
    refreshing_buff_rule,
    round_buff_rule,
)


def build_miranda_rules(values):
    wake = values["wake_up"]
    power = values["powering_up"]
    squad_crit_damage = float(wake["description_value_01"]) / 100
    crit_damage_duration = float(wake["description_value_02"])
    self_crit_rate = float(wake["description_value_03"]) / 100
    self_crit_rate_duration = float(wake["description_value_04"])
    self_attack_damage = float(wake["description_value_05"]) / 100
    self_attack_damage_duration = float(wake["description_value_06"])
    top_crit_rate_allies = int(wake["description_value_07"])
    top_crit_rate = float(wake["description_value_08"]) / 100
    top_crit_rate_rounds = int(wake["description_value_09"])
    burst_allies = int(power["description_value_01"])
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
        # Crit Rate on the highest-final-ATK ally, for 1 round (its next shot).
        round_buff_rule(
            "full_burst_enter",
            [("crit_rate", top_crit_rate, ("top_atk", top_crit_rate_allies))],
            shots=top_crit_rate_rounds,
        ),
        # Powering Up: ATK + Crit Damage on the top-N highest-final-ATK allies.
        highest_atk_buff_rule("own_burst_activate", burst_allies, [
            ("atk_percent", burst_atk, burst_atk_duration),
            ("other_critical_damage_sources", burst_crit_damage, burst_crit_damage_duration),
        ]),
    ]


def build_health_up_rules(values):
    """Per-shot rules for Health Up!: after every N normal attacks, self ATK up.
    Refreshing (re-applied each Nth shot without stacking). The skill's two Hit
    Rate steps are omitted (inert - see module docstring)."""
    shot_count = int(values["description_value_07"])
    self_atk = float(values["description_value_08"]) / 100
    self_atk_duration = float(values["description_value_09"])
    return [
        (shot_count, "every", [
            refreshing_buff_rule("per_shot", [("atk_percent", self_atk, "self", self_atk_duration)]),
        ]),
    ]
