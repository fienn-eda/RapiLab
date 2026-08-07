"""Miranda (slug "miranda") and her Favorite Item build (slug
"miranda-signature"), a Burst-1 SMG supporter. Collected from api.dotgg.gg.

The two builds are separate deck candidates (dual-slot); which one a user fights
with comes from their roster's per-unit `favorite_item` flag.

Base modeled (DPS-relevant):
- Wake Up! (skills[1]): on Full Burst enter, squad Crit Damage up. That is the
  WHOLE skill on the base build - the self Crit Rate / Attack Damage steps and
  the top-ATK round grant are text the Favorite Item adds (slots 03-09 simply do
  not exist in the base array).
- Powering Up! (skills[2], her burst): ATK + Crit Damage up on the **1** ally
  with the highest final ATK. The Favorite Item widens this to 2 allies (slot 01
  is the ally count: 1 vs 2) and changes nothing else.
- Health Up! (skills[0]): after every 30 normal attacks, squad Hit Rate +5.44%
  and a further +3.79% on submachine-gun allies, both for 5 sec. Both bullets
  REFRESH rather than stack - neither says "stacks up to", and her own SMG
  clears 30 rounds in about 1.5 sec, well inside the 5 sec they last, so a
  stacking reading would run away. This IS the base build's per-shot rule set;
  before Hit Rate had a consumer the base build had none at all.

Favorite Item modeled (DPS-relevant):
- Health Up! (dollskills[0]): the same two Hit Rate bullets, plus - the part the
  Favorite Item adds - self ATK up on the same every-30-normals counter (via
  per_shot_rules, see build_health_up_rules).
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

Not modeled (both builds): nothing outstanding.
"""
from app.skill_rules._helpers import (
    buff_rule,
    highest_atk_buff_rule,
    member_subset_buff_rule,
    refreshing_buff_rule,
    round_buff_rule,
)

SKILL_VALUE_MANIFESTS = {
    "miranda": {
        "source": "dotgg",
        "test_module": "test_skill_rules_burst1_batch1",
        "keys": {
            "health_up": ("skills", 0),
            "wake_up": ("skills", 1),
            "powering_up": ("skills", 2),
        },
        "fixtures": {
            "health_up": "MIRANDA_BASE_HEALTH_UP",
            "wake_up": "MIRANDA_BASE_WAKE_UP",
            "powering_up": "MIRANDA_BASE_POWERING_UP",
        },
    },
    "miranda-signature": {
        "source": "dotgg",
        "data_slug": "miranda",
        "test_module": "test_skill_rules_burst1_batch1",
        "keys": {
            "health_up": ("dollskills", 0),
            "wake_up": ("dollskills", 1),
            "powering_up": ("dollskills", 2),
        },
        "fixtures": {
            "health_up": "MIRANDA_SIG_HEALTH_UP",
            "wake_up": "MIRANDA_SIG_WAKE_UP",
            "powering_up": "MIRANDA_SIG_POWERING_UP",
        },
    },
}


def build_miranda_base_rules(values):
    """Miranda without her Favorite Item: one squad Crit Damage buff and a
    top-1-ATK burst. Deliberately not written as a special case of
    build_miranda_rules - the base array stops at slot 02 of Wake Up!, so the
    shared function's slot reads would KeyError rather than degrade."""
    wake = values["wake_up"]
    power = values["powering_up"]
    squad_crit_damage = float(wake["description_value_01"]) / 100
    crit_damage_duration = float(wake["description_value_02"])
    burst_allies = int(power["description_value_01"])
    burst_atk = float(power["description_value_02"]) / 100
    burst_atk_duration = float(power["description_value_03"])
    burst_crit_damage = float(power["description_value_04"]) / 100
    burst_crit_damage_duration = float(power["description_value_05"])

    return [
        buff_rule("full_burst_enter", [
            ("other_critical_damage_sources", squad_crit_damage, "squad", crit_damage_duration),
        ]),
        highest_atk_buff_rule("own_burst_activate", burst_allies, [
            ("atk_percent", burst_atk, burst_atk_duration),
            ("other_critical_damage_sources", burst_crit_damage, burst_crit_damage_duration),
        ]),
    ]


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


def submachine_gun_allies(member, context):
    """Health Up!'s second step, "all allies with a Submachine Gun" - Miranda
    herself carries one, so she is included."""
    return member.weapon == "SMG"


def build_health_up_hit_rate_rules(values):
    """Health Up!'s two Hit Rate steps, on both builds: after every N normal
    attacks, squad Hit Rate and a second helping for submachine-gun allies.

    Refreshing, not stacking. Neither bullet carries a "stacks up to" clause,
    which is the only marker that tells the two apart - and the counter fires
    far faster than the buff expires (30 SMG rounds ~ 1.5 sec against a 5 sec
    duration), exactly the shape that inflates a wrongly-stacked buff without
    bound."""
    shot_count = int(values["description_value_01"])
    squad_hit_rate = float(values["description_value_02"]) / 100
    squad_duration = float(values["description_value_03"])
    smg_hit_rate = float(values["description_value_05"]) / 100
    smg_duration = float(values["description_value_06"])
    return [
        (shot_count, "every", [
            refreshing_buff_rule("per_shot", [
                ("hit_rate", squad_hit_rate, "squad", squad_duration),
            ]),
            member_subset_buff_rule("per_shot", submachine_gun_allies, [
                ("hit_rate", smg_hit_rate, smg_duration),
            ], refreshing=True),
        ]),
    ]


def build_health_up_rules(values):
    """Per-shot rules for Health Up! on the FAVORITE ITEM build: the two Hit
    Rate steps both builds share, plus the self ATK step only this build has
    (slots 07-09, absent from the base array). Refreshing for the same reason."""
    shot_count = int(values["description_value_07"])
    self_atk = float(values["description_value_08"]) / 100
    self_atk_duration = float(values["description_value_09"])
    return build_health_up_hit_rate_rules(values) + [
        (shot_count, "every", [
            refreshing_buff_rule("per_shot", [("atk_percent", self_atk, "self", self_atk_duration)]),
        ]),
    ]
