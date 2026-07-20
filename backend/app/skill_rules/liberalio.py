"""Liberalio (slug "liberalio"), a Burst-3 Wind Sniper Rifle attacker. Base skills.

Every SR shot is a Full Charge, and in a solo raid the shots land on the boss
(the "stage target") and its core, so her Full-Charge-triggered effects are
modeled via per-shot rules (see build_liberalio_per_shot_rules).

Modeled (DPS-relevant):
- Calm Depths (skills[0]): on Full Burst enter, self ATK +160% for 3s; on every
  Full Charge on the core, self Attack Damage +20.83% for 60s (refreshing);
  the first 5 Full Charges each deal 40.5% of final ATK as additional damage.
- Strange Currents (skills[1]): the first Full Charge on the boss grants Raging
  Current - self Attack Damage +231% continuously (permanent; only removed by
  Gentle Current, which requires hitting a non-boss Rapture - see deferred).
- Submerged World (skills[2], her burst): self Attack Damage +50% for 10s, and a
  925%-of-final-ATK burst nuke.

Not modeled / deferred:
- Gentle Current (Strange Currents' non-boss-target branch): fixes charge time
  and removes Raging Current - assumed never triggered, since solo-raid fire stays
  on the boss. Its Charge-Time effect is inert anyway (attack rate not skill-driven).
- Calm Depths' Charge Speed buff on "the 1 Burst 3 ally with the lowest final
  ATK". Charge Speed is no longer the blocker (Phase S made it a damage stat -
  the note here used to say it was inert); what is missing is a LOWEST-ATK
  ranking, the mirror of `SquadContext.top_atk_slugs`. Low value even once
  built: it deliberately targets the weakest Burst-3 ally, i.e. not the carry.
  Its value is also stated as "12.74% of the skill user's Charge Speed", which
  is ambiguous enough to need Fienn before encoding.

Strange Currents' charge-speed IMMUNITY is modeled (see
`build_strange_currents_immunity_rules`) - it was skipped while charge speed
moved nothing, but now that it does, omitting the immunity would let any deck
charge-speed buffer speed her up when in game it cannot.

Approximation: the on-core Attack Damage is applied on every Full Charge (core
hits aren't tracked per-shot), consistent with how core damage is handled globally.
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
    # The first N Full Charges each deal additional damage (one "after n" per hit).
    for n in range(1, additional_times + 1):
        rules.append((n, "after", [instant_nuke_pulse_rule("per_shot", additional)]))
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
