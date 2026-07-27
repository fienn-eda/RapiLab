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

Verified against Fienn's in-game range test (2026-07-27, solo, ATK 305,667,
skills 10/7/10, target DEF 100). Seven readings across crit on/off, in/out of
effective range, and Spy Lens below/at max all match this model to within 1e-4
of one another - every buff, value and gate above is right, including the
`has_pierce` gate discarding her Pierce Damage while Spy Lens is below max.
They sit a uniform 1.06x below the model, and the cause is her COLLECTIBLE
(소장품, SR weapon group Lv5, "차지대미지 6.31% 배율"), which scales the
weapon's own 250% full charge to 265.775%. Nothing in the engine models
collectible skill effects - see docs/engine-gaps.md #17.

Not modeled: Spy Lens / Minimum Effective Range STACKING (the 4.44%-per-stack
ramp to max - approximated as permanently maxed) and the effective-range damage
bonus itself, which the measurement puts at exactly +0.30 in the major modifier
but `raid_simulator` never sets (gap #16). Her burst has no enemy nuke.
"""
from app.skill_rules._helpers import buff_rule

SKILL_VALUE_MANIFESTS = {
    "ade-agent-bunny": {
        "source": "dotgg",
        "test_module": "test_skill_rules_ade",
        "keys": {
            "agents_gaze": ("skills", 0),
            "agents_movement": ("skills", 1),
            "cutting_edge_equipment": ("skills", 2),
        },
    },
}


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
            # Same Spy-Lens-at-max bullet grants "Gains Pierce. This effect is
            # continuous", modeled permanent alongside its ATK. She is the only
            # unit her own squad-wide Pierce Damage buff can actually credit
            # unless an ally brings Pierce too.
            ("has_pierce", 1.0, "self", None),
        ]),
        buff_rule("own_burst_activate", [
            ("attack_damage_up", burst_attack_damage, "squad", burst_attack_damage_duration),
            ("pierce_damage_up", burst_pierce, "squad", burst_pierce_duration),
        ]),
    ]
