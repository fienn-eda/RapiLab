"""Liberalio (slug "liberalio"), a Burst-3 Wind Sniper Rifle attacker. Base skills.

Every SR shot is a Full Charge, and in a solo raid the shots land on the boss
(the "stage target") and its core, so her Full-Charge-triggered effects are
modeled via per-shot rules (see build_liberalio_per_shot_rules).

Modeled (DPS-relevant):
- Calm Depths (skills[0]): on Full Burst enter, self ATK +160% for 3s; on every
  Full Charge on the core, self Attack Damage +20.83% for 60s (refreshing, NOT
  stacking - the text says no "stacks up to", Fienn 2026-07-26); every Full
  Charge deals 40.5% of final ATK as additional damage, five times.
- Calm Depths' Charge Speed on "the 1 Burst 3 ally with the lowest final ATK"
  (see build_calm_depths_charge_rules).
- Strange Currents (skills[1]): the first Full Charge on the boss grants Raging
  Current - self Attack Damage +231% continuously (permanent; only removed by
  Gentle Current, which requires hitting a non-boss Rapture - see deferred).
- Submerged World (skills[2], her burst): self Attack Damage +50% for 10s, and a
  925%-of-final-ATK burst nuke.

Not modeled / deferred:
- Gentle Current (Strange Currents' non-boss-target branch): fixes charge time
  and removes Raging Current - assumed never triggered, since solo-raid fire stays
  on the boss. Its Charge-Time effect is inert anyway (attack rate not skill-driven).
Strange Currents' charge-speed IMMUNITY is modeled (see
`build_strange_currents_immunity_rules`) - it was skipped while charge speed
moved nothing, but now that it does, omitting the immunity would let any deck
charge-speed buffer speed her up when in game it cannot.

Approximation: the on-core Attack Damage is applied on every Full Charge (core
hits aren't tracked per-shot), consistent with how core damage is handled globally.

She reads 0.837x of her recorded raid damage - **the largest absolute miss in
the whole calibration** (-0.630B of 3.860B) - and every input behind that number
was audited on 2026-07-27 and found correct. Re-auditing them is wasted work:
- Her five overload rolls reproduce the damage formula's terms exactly (ATK
  +40.91% -> atk_percent 0.4091; superior code 99.82% + cube 19.09% ->
  other_elemental_bonus 1.1891; charge damage +21.52% on the collectible-scaled
  273.675% -> charge_damage_bonus 1.95195).
- 117 shots = 13 magazines of 9 rounds, which is max ammo +48.39% on her 6, at
  1.417 sec = her 1.5 sec charge with her own +6.09% and the external immunity
  correctly refusing everyone else's.
- Skills are 10/10/10 and the values match the level-10 text; attack_damage_up
  2.5183 is Raging Current 231% + the on-core 20.83% counted ONCE, which is what
  the text supports (no "stacks up to" phrase).
- She bursts 8 of the deck's 15 Full Bursts because deck1 seats two Burst 3s who
  alternate, and 25.24 sec between her bursts is her 40 sec cooldown minus two
  doses of Anis: Star's per-Full-Burst reduction.
- Calm Depths' charge buff correctly lands on Scarlet (lowest FINAL ATK B3, not
  lowest base), reproducing Fienn's 0.7323 -> 0.5424 sec measurement.
The shortfall is therefore not an input error in this file. It sits with the
roster-wide pattern in docs/insights.md: the simulator compresses each deck's
spread, and deck1's three big dealers (Liberalio, Scarlet, Anis: Star) are three
of the four largest misses in the run, all in the same direction.
"""
from app.effects import Effect
from app.skill_rules._helpers import buff_rule, instant_nuke_pulse_rule, refreshing_buff_rule
from app.squad_engine import SkillRule


SKILL_VALUE_MANIFESTS = {
    "liberalio": {
        "source": "lootandwaifus",
        "test_module": "test_skill_rules_burst3_eb1",
        "keys": {
            "calm_depths": ("skills", 0),
            "strange_currents": ("skills", 1),
            "submerged_world": ("skills", 2),
        },
        "drop_tokens": {
            "calm_depths": [6, 7],
        },
    },
}


def submerged_world_burst_percent(values):
    return float(values["submerged_world"]["description_value_03"])


def build_liberalio_rules(values):
    calm = values["calm_depths"]
    submerged = values["submerged_world"]
    fb_atk = float(calm["description_value_01"]) / 100
    fb_atk_duration = float(calm["description_value_02"])
    burst_attack_damage = float(submerged["description_value_01"]) / 100
    burst_attack_damage_duration = float(submerged["description_value_02"])

    return [
        buff_rule("full_burst_enter", [("atk_percent", fb_atk, "self", fb_atk_duration)]),
        buff_rule("own_burst_activate", [("attack_damage_up", burst_attack_damage, "self", burst_attack_damage_duration)]),
    ]


def build_liberalio_per_shot_rules(values):
    calm = values["calm_depths"]
    strange = values["strange_currents"]
    raging_attack_damage = float(strange["description_value_01"]) / 100
    on_core_attack_damage = float(calm["description_value_03"]) / 100
    on_core_duration = float(calm["description_value_04"])
    additional = float(calm["description_value_05"])
    additional_times = int(calm["description_value_06"])

    rules = [
        # Raging Current: first Full Charge on the boss -> permanent Attack Damage.
        (1, "after", [buff_rule("per_shot", [("attack_damage_up", raging_attack_damage, "self", None)])]),
        # On-core Attack Damage: every Full Charge, refreshing its 60s window.
        (1, "every", [refreshing_buff_rule("per_shot", [("attack_damage_up", on_core_attack_damage, "self", on_core_duration)])]),
    ]
    # "Activates N times" with no per-battle qualifier: N hits on EVERY Full
    # Charge. Every other collected unit whose effect is battery-limited says
    # so in words - Neon: Vision Eye "Activates 5 time(s) per battle", Nayuta
    # "1 time(s) during battle", Rosanna "1 time(s) per battle" - and this
    # bullet carries none of them.
    for _ in range(additional_times):
        rules.append((1, "every", [instant_nuke_pulse_rule("per_shot", additional)]))
    return rules


def build_strange_currents_immunity_rules(values: dict) -> list[SkillRule]:
    """Strange Currents' "Gains immunity to Increase/Decrease Charge Speed
    effects. This effect is continuous and cannot be removed."

    Inert before Phase S, when charge speed moved nothing. Now that
    `charge_speed_percent` drives her firing cadence, leaving it out means a
    deck with any charge-speed buffer silently speeds her up when in game it
    does not - an over-estimate. Registered as an EXTERNAL immunity so her own
    overload rolls and cube (registered with her own slug as source) still
    apply; only other units' buffs are refused."""

    def action(context, caster_slug, time, registry):
        # Both stats, because the skill grants immunity to the CONCEPT: the
        # percent form and the caster-based seconds form are the same effect
        # wearing different engine clothes.
        registry.set_external_stat_immunity(caster_slug, "charge_speed_percent")
        registry.set_external_stat_immunity(caster_slug, "charge_time_reduction_sec")

    return [SkillRule(trigger="battle_start", action=action)]


# Her own charge time is the basis for the buff below, so it is read from her
# weapon stats rather than hardcoded.
CALM_DEPTHS_TARGET_BURST_TIER = 3


def build_calm_depths_charge_rules(values: dict, caster_weapon_stats: dict) -> list[SkillRule]:
    """Calm Depths' "Charge Speed +X% of the skill user's Charge Speed" on the
    lowest-final-ATK Burst 3 ally.

    "Of the skill user's" (시전자 기준) is the whole mechanic: the percentage is
    taken against LIBERALIO's charge time, not the recipient's, and the ally
    receives the resulting ABSOLUTE seconds. She is a Sniper Rifle charging in
    1.5 sec, so 12.74% is 0.1911 sec for whoever gets it - the figure Korean
    community guides quote ("약 0.19초 줄어든다"), and the one that reproduces
    Fienn's Scarlet measurement (0.7323 -> 0.5424 sec) to 0.07 frames.

    Encoding it as `charge_speed_percent` would have been wrong in a way that
    hides: the equivalent percent is 26.1% on Scarlet's 0.73 sec charge but
    19.1% on a 1.0 sec one, so a single percent cannot be right for both.
    """
    calm = values["calm_depths"]
    percent = float(calm["description_value_07"]) / 100
    duration = float(calm["description_value_08"])
    seconds = percent * float(caster_weapon_stats["charge_time"])

    def action(context, caster_slug, time, registry):
        targets = context.lowest_atk_slugs(
            1, registry, time, burst_tier=CALM_DEPTHS_TARGET_BURST_TIER
        )
        if not targets:
            return
        registry.add(
            Effect("charge_time_reduction_sec", seconds, f"slugs:{','.join(targets)}",
                   duration, caster_slug),
            applied_at=time,
        )

    return [SkillRule(trigger="full_burst_enter", action=action)]
