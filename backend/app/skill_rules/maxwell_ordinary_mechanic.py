"""Maxwell: Ordinary Mechanic (slug "maxwell-ordinary-mechanic"), a Burst-2 Wind
SR supporter from MISSILIS. Collected from ShiftyPad (blablalink public data).

Her team value is a stack of Attack Damage buffs plus an ATK buff scaled off her
own Max HP - all fully modeled. Her burst is a self weapon-transform (a single-
shot cannon) with no "X% as Burst Skill damage" nuke, so the registry burst
percent is None (buffs-only support).

Modeled (DPS-relevant):
- Sequential Limit Release (skills[0]), on entering Full Burst (Burst Stage 3):
  all allies Attack Damage +10% for 5 sec (squad).
- Sequential Limit Release (skills[0]) Max HP: +1% of her Max HP per Full
  Charge, capped at 30 stacks (squad). The full-charge-count trigger does not
  exist, but her SR fires a full charge every shot, so the cap is reached early
  and held - modeled as the settled +30% granted at battle start (same settling
  approximation as red-hood's Glaring Eyes). No longer inert: it feeds the
  squad ATK below through the live-Max-HP path.
- Output Switching Sequence (skills[1]), on her own burst:
  - all allies ATK + (1% of her LIVE Max HP - base plus the Max HP stacks
    above) for 15 sec, via max_hp_scaled_atk_rule.
  - Overcurrent: self ATK +30% continuously, cumulative up to 5 stages (+150%),
    one stage per burst - modeled as a per-cycle escalating self buff.
- Matis Uberbuster (skills[2], her burst): all allies Attack Damage +25% for
  10 sec (squad).

Not modeled / deferred (handle later, needs engine work):
- Output Switching Sequence's "Fills Burst Gauge by 7.15% per Full Charge": burst
  gauge fill speed is not consumed by the engine (fixed sim input), and the
  trigger is a full-charge count. Deferred.
- Matis Uberbuster's weapon transform (Matis UberBuster single-shot cannon, whose
  fixed charge time shortens with Overcurrent stage, 350% self damage): a stage-
  dependent weapon transform. Her own SR/cannon damage is minor for a supporter,
  so this is deferred rather than approximated; the team buffs above are her real
  contribution.
"""
from app.skill_rules._helpers import buff_rule, escalating_buff_rule, max_hp_scaled_atk_rule

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

    squad_atk_pct = float(s2["description_value_01"]) / 100  # 그녀 Max HP의 1%
    squad_atk_dur = float(s2["description_value_02"])         # 15 sec

    max_hp_per_stack = float(s1["description_value_01"]) / 100  # 스택당 Max HP 1%
    max_hp_stack_cap = int(float(s1["description_value_02"]))   # 30 스택
    settled_max_hp = caster_max_hp * max_hp_per_stack * max_hp_stack_cap
    overcurrent_atk = float(s2["description_value_05"]) / 100                  # 30% per stage
    overcurrent_stages = int(float(s2["description_value_06"]))                # up to 5 stages

    burst_attack_damage = float(burst["description_value_07"]) / 100  # 25%
    burst_attack_damage_dur = float(burst["description_value_08"])     # 10 sec

    return [
        buff_rule("full_burst_enter", [
            ("attack_damage_up", fb_attack_damage, "squad", fb_attack_damage_dur),
        ]),
        # 풀차지마다 Max HP +1%(그녀 Max HP 기준), 캡 30 - SR은 매 발사가
        # 풀차지라 캡에 초반 도달해 유지되므로 정착값을 battle_start에 부여한다.
        buff_rule("battle_start", [("flat_max_hp", settled_max_hp, "squad", None)]),
        # squad ATK = 그녀의 LIVE Max HP의 1% (위 스택을 포함해 읽는다)
        max_hp_scaled_atk_rule("own_burst_activate", squad_atk_pct, "squad", squad_atk_dur, caster_max_hp),
        buff_rule("own_burst_activate", [
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
