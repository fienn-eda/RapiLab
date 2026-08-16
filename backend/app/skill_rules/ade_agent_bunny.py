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

Not modeled: every Minimum Effective Range bullet - Spy Lens's 4.44%-per-stack
ramp (approximated as permanently maxed, since the ATK bullet it gates is what
matters) and her burst's own +55.56% for 10 sec. The engine holds no
minimum-effective-range stat: since 2026-07-31 the effective-range bonus is
decided by the encounter (`BossProfile.effective_range_band`), which no skill
can move, so encoding either would be inert. Her burst has no enemy nuke.

The effective-range bonus itself is no longer an engine gap: since 2026-07-31
`BossProfile.effective_range_band` pays the measured +0.30 to the weapon classes
the encounter's distance covers. Ade is an SR, i.e. `far`, so she collects it
only against a `far` encounter - the recorded Annihilator run is `mid`, which
pays ARs and MGs and not her. That is the encounter, not a missing wiring.

She reads 1.629x of her recorded raid damage, the roster's worst ratio, and it
was investigated in full on 2026-07-27 - DO NOT re-open it as an Ade bug. Her
per-shot damage is exact (the range test above), and her 169 shots in 180s are
fully accounted for by her real overload (max ammo +68.93%, charge speed +9.84%)
and the cube's reload speed. What she is, is the extreme point of a roster-wide
pattern: the simulator compresses each deck's damage spread, and her 0.102B is
the SMALLEST recorded contribution of all 25 measured units, so the same
over-credit reads as the largest ratio. In absolute terms she is +0.064B, 1.5%
of her deck and only 4th of its 5 units. Two tempting fixes are already
measured and rejected: lowering the global core-hit rate (0.2 puts her at 1.001
and collapses the other 24 - see docs/insights.md) and paying her the
effective-range bonus, which moves her to 1.700 (and is why a `far` band would
be the wrong reading of that `mid` encounter). What is NOT settled is whether
she actually fired for the whole 180 seconds in that run.
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
