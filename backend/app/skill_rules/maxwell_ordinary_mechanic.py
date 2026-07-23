"""Maxwell: Ordinary Mechanic (slug "maxwell-ordinary-mechanic"), a Burst-2 Wind
SR supporter from MISSILIS. Collected from ShiftyPad (blablalink public data).

Her team value is a stack of Attack Damage buffs plus an ATK buff scaled off her
own Max HP - all fully modeled. Her burst is a self weapon-transform (a single-
shot cannon) with no "X% as Burst Skill damage" nuke, so the registry burst
percent is None (buffs-only support).

Modeled (DPS-relevant):
- Sequential Limit Release (skills[0]), on entering Full Burst (Burst Stage 3):
  all allies Attack Damage +10% for 5 sec (squad).
- Output Switching Sequence (skills[1]), on her own burst:
  - all allies ATK + (1% of her final Max HP) for 15 sec (squad flat_atk,
    caster-Max-HP-scaled).
  - Overcurrent: self ATK +30% continuously, cumulative up to 5 stages (+150%),
    one stage per burst - modeled as a per-cycle escalating self buff.
- Matis Uberbuster (skills[2], her burst): all allies Attack Damage +25% for
  10 sec (squad).

Not modeled / deferred (handle later, needs engine work):
- Sequential Limit Release's Max HP +1% (of her Max HP) per Full Charge, up to 30
  stacks (squad): Max HP is inert for damage today, AND its trigger is a full-
  charge count (no such trigger exists). Skipped.
- Output Switching Sequence's "Fills Burst Gauge by 7.15% per Full Charge": burst
  gauge fill speed is not consumed by the engine (fixed sim input), and the
  trigger is a full-charge count. Deferred.
- Matis Uberbuster's weapon transform (Matis UberBuster single-shot cannon, whose
  fixed charge time shortens with Overcurrent stage, 350% self damage): a stage-
  dependent weapon transform. Her own SR/cannon damage is minor for a supporter,
  so this is deferred rather than approximated; the team buffs above are her real
  contribution.
"""
from app.skill_rules._helpers import buff_rule, escalating_buff_rule

SKILL_VALUE_MANIFESTS = {
    "maxwell-ordinary-mechanic": {
        "source": "shiftypad",
        "test_module": "test_skill_rules_maxwell_ordinary_mechanic",
        "keys": {
            "sequential_limit_release": ("skills", 0),
            "output_switching_sequence": ("skills", 1),
            "matis_uberbuster": ("skills", 2),
        },
    },
}


def build_maxwell_ordinary_mechanic_rules(values, caster_max_hp):
    s1 = values["sequential_limit_release"]
    s2 = values["output_switching_sequence"]
    burst = values["matis_uberbuster"]

    fb_attack_damage = float(s1["description_value_04"]) / 100  # 10%
    fb_attack_damage_dur = float(s1["description_value_05"])     # 5 sec

    squad_atk_flat = caster_max_hp * float(s2["description_value_01"]) / 100  # 1% of Max HP
    squad_atk_dur = float(s2["description_value_02"])                          # 15 sec
    overcurrent_atk = float(s2["description_value_05"]) / 100                  # 30% per stage
    overcurrent_stages = int(float(s2["description_value_06"]))                # up to 5 stages

    burst_attack_damage = float(burst["description_value_07"]) / 100  # 25%
    burst_attack_damage_dur = float(burst["description_value_08"])     # 10 sec

    return [
        buff_rule("full_burst_enter", [
            ("attack_damage_up", fb_attack_damage, "squad", fb_attack_damage_dur),
        ]),
        buff_rule("own_burst_activate", [
            ("flat_atk", squad_atk_flat, "squad", squad_atk_dur),
            ("attack_damage_up", burst_attack_damage, "squad", burst_attack_damage_dur),
        ]),
        # Overcurrent: +30% self ATK per burst, cumulative to 5 stages (+150%),
        # held continuously - each tier refreshes so re-applications don't sum.
        escalating_buff_rule(
            "own_burst_activate",
            [[("atk_percent", overcurrent_atk, "self", None)]] * overcurrent_stages,
            refreshing=True,
        ),
    ]
