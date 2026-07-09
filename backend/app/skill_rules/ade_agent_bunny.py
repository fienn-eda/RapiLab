"""Ade: Agent Bunny (slug "ade-agent-bunny"), a Burst-2 Iron SR supporter.
Base skills (no signature weapon).

Steady-state approximation: her all-ally buffs trigger on landing Full Charge
attacks within effective range, and her self ATK needs Spy Lens fully stacked.
An SR fires Full Charges continuously and (per Fienn) the raid boss is always in
range, so these are modeled as always-on from battle start.

Modeled (DPS-relevant):
- Agent's Gaze (skills[0]): squad ATK % of caster's ATK (always-on approx).
- Agent's Movement (skills[1]): squad Pierce Damage (always-on approx); plus a
  self ATK buff once Spy Lens is fully stacked (always-on approx).
- Cutting-Edge Agent Equipment (skills[2], her burst): squad Attack Damage +
  Pierce Damage on her own burst.

Not modeled: Spy Lens / Minimum Effective Range stacking and the effective-range
damage bonus (an SR positioning mechanic; effective_range_bonus isn't consumed),
and her own "gain Pierce" flag. Her burst has no enemy nuke.
"""
from app.skill_rules._helpers import buff_rule


def build_ade_rules(values):
    gaze = values["agents_gaze"]
    movement = values["agents_movement"]
    equipment = values["cutting_edge_equipment"]
    caster_atk = values["caster_atk"]

    gaze_atk = float(gaze["description_value_01"]) / 100 * caster_atk
    movement_pierce = float(movement["description_value_01"]) / 100
    movement_self_atk = float(movement["description_value_03"]) / 100
    burst_attack_damage = float(equipment["description_value_03"]) / 100
    burst_attack_damage_duration = float(equipment["description_value_04"])
    burst_pierce = float(equipment["description_value_05"]) / 100
    burst_pierce_duration = float(equipment["description_value_06"])

    return [
        buff_rule("battle_start", [
            ("flat_atk", gaze_atk, "squad", None),
            ("pierce_damage_up", movement_pierce, "squad", None),
            ("atk_percent", movement_self_atk, "self", None),
        ]),
        buff_rule("own_burst_activate", [
            ("attack_damage_up", burst_attack_damage, "squad", burst_attack_damage_duration),
            ("pierce_damage_up", burst_pierce, "squad", burst_pierce_duration),
        ]),
    ]
