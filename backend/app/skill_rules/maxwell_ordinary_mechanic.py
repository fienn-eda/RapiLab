"""Maxwell: Ordinary Mechanic (slug "maxwell-ordinary-mechanic"), a Burst-2 Wind
SR supporter from MISSILIS. Value slots from ShiftyPad (blablalink public data),
effect text from lootandwaifus.

Her team value is a stack of Attack Damage buffs plus an ATK buff scaled off her
own Max HP. Her burst is a self weapon-transform - a single-shot cannon whose
charge time shortens as Overcurrent stages up - rather than a nuke, so the
registry burst percent is None and the transform carries that damage instead.

Modeled (DPS-relevant):
- Sequential Limit Release (skills[0]), on entering Burst Stage 3: all allies
  Attack Damage +10% for 5 sec (squad) - `ally_burst_activate` +
  `burst_stage_entered(3)`, so it lands before that unit's own burst damage.
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
  10 sec (squad), plus the weapon transform itself - one charged shot from the
  Matis UberBuster per own burst (350% of final ATK, 300% Full Charge Damage,
  1 round, Gains Pierce), modeled as a `weapon_mode_schedules` segment.
  Its charge time is fixed BY the Overcurrent stage rather than being a
  constant, so unlike every other single-shot transform here each segment
  carries its own profile: 3 sec at her first burst, then 2.5 / 2 / 1.5, and
  0.4 from the fifth burst on (Overcurrent gains a stage per own burst, cap 5).
  This silences her base SR for the whole charge, so it is a damage TRADE - but
  a lopsided one, worth +13.71% of her sweep-shell total, because 350% at a
  300% full-charge multiplier dwarfs the handful of ~2.5% base shots those
  seconds would have bought.

Not modeled / deferred:
- Output Switching Sequence's "Fills Burst Gauge by 7.15% per Full Charge": burst
  gauge fill speed is not consumed by the engine (fixed sim input).
- Her registry burst percent stays None: the transform IS her burst damage, so
  there is no "X% as Burst Skill damage" nuke to register alongside it.
"""
from app.skill_rules._helpers import (
    buff_rule,
    escalating_buff_rule,
    max_hp_scaled_atk_rule,
    round_buff_rule,
)
from app.squad_engine import burst_stage_entered

SLUG = "maxwell-ordinary-mechanic"

# The transformed weapon's Full Charge Damage, a flat 300% at every skill level
# and so a constant rather than a slot (the Cinderella / EVE hit-count
# precedent). Every other Matis UberBuster number IS a slot.
MATIS_FULL_CHARGE_DAMAGE = 300.0

# Sequential Limit Release's second bullet names the stage, and the skill's own
# slot 03 carries the literal 3.
BURST_STAGE = 3

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
        # "Activates when entering Burst Stage 3" - the STAGE, so it happens in
        # every cycle whoever takes that slot, and it fires before the Burst 3's
        # own nuke is recorded. full_burst_enter is the LATER instant and would
        # drop the +10% from that damage.
        buff_rule("ally_burst_activate",
                  [("attack_damage_up", fb_attack_damage, "squad", fb_attack_damage_dur)],
                  condition=burst_stage_entered(BURST_STAGE)),
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
        # Matis UberBuster's "Additional Effect: Gains Pierce" - the transform is
        # a single charged shot, so the property covers exactly that round (base
        # Maxwell's Pierce Shot shape).
        round_buff_rule("own_burst_activate", [("has_pierce", 1.0, "self")], shots=1),
    ]


def _overcurrent_charge_times(values):
    """Fixed charge time per Overcurrent stage, as {stage: seconds}.

    The skill lists "Stage 1 or below: 3 sec" then 2.5 / 2 / 1.5, and "Stage 5
    or above: 0.4". Slot 09 carries the stage-1 value (it is also the skill's
    headline "Charge Time: 3sec") and 01..04 the rest, so the ladder is read
    rather than transcribed.
    """
    burst = values["matis_uberbuster"]
    later = [float(burst[f"description_value_0{i}"]) for i in (1, 2, 3, 4)]
    return [float(burst["description_value_09"])] + later


def build_matis_uberbuster_weapon_mode_schedule(values):
    """Her burst's weapon transform: one charged shot from the Matis UberBuster.

    The charge time is not a constant - it is fixed BY the Overcurrent stage,
    which Output Switching Sequence advances one step per own burst up to 5. So
    the k-th burst transforms at stage min(k, 5) and each segment carries its
    own profile, unlike every other single-shot transform in this engine. The
    ladder is steep at the end: 3 sec at her first burst against 0.4 from the
    fifth on.

    This is a damage TRADE, not an addition - the segment silences her base SR
    for the whole charge, so an early 3-sec transform buys one 350% shot at the
    cost of three seconds of her own normal attacks. It comes out ahead anyway
    (see the module docstring's measurement).

    The full-charge multiplier is wholly a skill value: no term in this profile
    comes from weapon_stats, which is where a collectible's charge-damage 배율
    is applied, so the 배율 has to be applied here to reach the transform at all
    (base Maxwell, measured by Fienn 2026-08-03).
    """
    burst = values["matis_uberbuster"]
    damage_percent = float(burst["description_value_05"])
    charge_damage = MATIS_FULL_CHARGE_DAMAGE * values.get(
        "caster_charge_damage_multiplier", 1.0)
    charge_times = _overcurrent_charge_times(values)

    def schedule(context, fight_duration):
        segments = []
        for index, start in enumerate(context.burst_times.get(SLUG, [])):
            stage = min(index + 1, len(charge_times))
            segments.append({
                "start": start,
                "until_shots": 1,
                "profile": {
                    "weapon": "SR",
                    "damage_percent": damage_percent,
                    "charge_damage_percent": charge_damage,
                    "charge_time": charge_times[stage - 1],
                },
            })
        return segments

    return schedule
