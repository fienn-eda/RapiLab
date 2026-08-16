"""Asuka Shikinami Langley: Wille (slug "asuka-shikinami-langley-wille"), a
Burst-3 Wind Machine Gun attacker. Base skills. PARTIAL - see below.

First consumer of the delayed dynamic_hit_count_nuke (`fire_delay` +
`own_burst_delayed` resets - a burst effect that lands after a fixed delay,
not at cast time), which is also the clearest illustration of why the Full
Burst bonus is decided by TIME: the same burst produces damage at the cast
(no bonus, the window has not opened) and damage 9 sec later (inside it).

Modeled (DPS-relevant): an "anti_at_field" resource (Anti A.T. Field, a stack
debuff on the boss), capped at 30.
- Anti A.T. Field (skills[0]) fills it +1 every 10 shots, but ONLY while
  Annihilation State is active (`per_shot_every_during_own_status_window`,
  9s - the window is anchored to HER OWN burst, not the squad's Full Burst
  window, since Annihilation State starts at her burst and is shorter than
  Full Burst). Each stack: Damage Taken +0.83% for 30 sec (squad-scoped, since
  it's a debuff on the boss that every attacker benefits from). Separately,
  the SAME skill deals 471.86% of final ATK as additional damage every 50
  shots, unconditionally (not gated on Annihilation State) - "as additional
  damage" makes this eligible for the Full Burst Bonus, checked against
  whichever Full Burst window (if any) the shot's own time happens to fall
  in, since this trigger runs independently of her burst.
- Annihilation State (her burst): grants self ATK +46.8% of her own ATK and
  Attack Damage +36%, and cuts her own Normal Attack Damage Multiplier by
  40%, all three for 9 sec. That cut is the state's price and it is not a
  small one: her burst opens the Full Burst window, so the 9 sec cover her
  most valuable shots - 62% of her normal-attack damage in the recorded deck.
  It also reloads her own magazine 21% on cast (`annihilation_state_refill`)
  - a one-shot percentage grant at her own burst, not a repeating shot
  counter, so it goes through `get_ammo_refill_grant` rather than
  `attack_rate.AmmoRefund`. Separately, "Annihilation" fires 9 sec
  LATER (when Annihilation State ends, not at cast time) - deals 6.62% of
  final ATK as additional damage, once per Anti A.T. Field stack accumulated
  right before that moment (`dynamic_hit_count_nukes` + `fire_delay`), and
  clears Anti A.T. Field to 0 there too (`own_burst_delayed` reset, matching
  the skill text "Anti A.T. Field status is removed after effect is
  triggered" - the SAME reset also cuts short any Damage Taken stacks that
  hadn't yet hit their own 30s timer, which is correct: the whole status is
  removed, not just the hit-count tracking). "As additional damage" + the 9s
  delay landing inside the 10s Full Burst window (which starts the same
  instant as her burst) makes this eligible for the Full Burst Bonus too.
- Emergency Repair (skills[1]): on entering Full Burst WHILE Annihilation
  State is active, self Attack Damage +30.97% for 10 sec. Modeled as
  `own_burst_fired_this_cycle()` gating a `full_burst_enter` rule - in this
  engine's strict burst1->burst2->burst3->full-burst ordering, her own burst
  (tier 3) always fires immediately before full_burst_enter in the same
  cycle, so "her burst fired this cycle" is exactly "Annihilation State just
  started, still active" at the instant full_burst_enter fires.
- Emergency Repair's Effect 1 + Effect 2 + Effect 4, all **when Annihilation
  fires** - that bullet reads "Activates when using Annihilation", and
  Annihilation is "After Annihilation State ends", so they land a full state
  duration (9 sec) after the burst that started it, NOT at the cast (Fienn,
  2026-08-16). The delay is read from Annihilation State's own slot, the same
  value `fire_delay` uses, so the two can never disagree.
  Effect 1 is MG heating up speed down 100% for 3 sec
  (`mg_heating_speed_percent`, negative - a down arrow subtracts) alongside
  Effect 2 removing 100% of her ammo with Effect 4's Forced Reload fixed at a
  60% speed increase. The ammo dump is a `build_asuka_weapon_mode_schedule`
  segment (see `silent_reload_segments`, `offset=`) covering that reload; the
  segment ends by starting a fresh magazine, whose warm-up is scaled by
  whatever `mg_heating_speed_percent` total is live the instant it opens -
  `registry.total_for` sums Effect 1's own -100% against every other producer
  targeting her (e.g. Rei Ayanami: Tentative Name's Maintenance and Resupply,
  +100% to a bursted MG ally for 13 sec, which still spans this later window).
  Effect 1's 3 sec covers the segment's own ~2.08 sec entirely, so an ally
  buff of that size reaching her for the whole segment cancels the debuff and
  leaves that magazine's warm-up unmodified.
  **Where this sits is load-bearing for her Anti A.T. Field stacks.** They are
  built by her shots inside the SAME 9 sec, so a magazine dumped at the cast
  ate the window that feeds them: she reached 25 stacks of her 30 cap. Landing
  it at the far end instead, she fires 505 shots in that window rather than 250
  and pins the cap in every cycle.

- Anti A.T. Field's OWN 15.62%-of-ATK direct-damage component ("every 10
  shots while in Annihilation State, deals 15.62% as damage" - a SEPARATE
  bullet from the 471.86% unconditional nuke): modeled via the window-gated
  per-shot trigger (`per_shot_rules` mode "every_during_own_status_window",
  gap #7, built 2026-07-15) - the same 9s own-burst-anchored window the stack
  fill uses. It fires on her own shots, so like every other per-shot instance
  it takes the Full Burst bonus on whichever of them land inside a window - no
  reading of its wording involved. A small nuke, secondary to her headline
  mechanics.

Not modeled / deferred:
- Emergency Repair's HP recovery effect (Effect 3): not consumed by the engine
  (see "Stats the engine does NOT consume" in engine-capabilities.md).
"""
from app.attack_rate import reload_time_with_speed
from app.effects import Effect, ResourceSpec
from app.skill_rules._helpers import (buff_rule, instant_nuke_pulse_rule,
                                      linear_resource_buff, silent_reload_segments)
from app.squad_engine import SkillRule, own_burst_fired_this_cycle

SKILL_VALUE_MANIFESTS = {
    "asuka-shikinami-langley-wille": {
        "source": "lootandwaifus",
        # dotgg shortens her to "asuka-wille" - bridge for the weapon-stats lookup.
        "dotgg_slug": "asuka-wille",
        "test_module": "test_skill_rules_asuka_shikinami_langley_wille",
        "keys": {
            "anti_at_field": ("skills", 0),
            "emergency_repair": ("skills", 1),
            "annihilation_state": ("skills", 2),
        },
        "drop_tokens": {
            # "Effect 1/2/3/4" enumeration labels plus the "every 1 sec" tick
            # interval the fixture skipped.
            "emergency_repair": [2, 5, 7, 9, 11],
            # The "Effect 1/2/3/4" labels plus Effect 3/4's repeated "9 sec"
            # durations - the fixture keeps a single duration slot (02).
            "annihilation_state": [0, 3, 5, 7, 8, 10],
        },
    },
}


def build_anti_at_field_resources(values):
    field = values["anti_at_field"]
    duration = float(values["annihilation_state"]["description_value_02"])  # Annihilation State's 9s

    per_stack = float(field["description_value_06"]) / 100
    stack_lifetime = float(field["description_value_07"])
    cap = int(float(field["description_value_08"]))
    fill_every = int(float(field["description_value_04"]))

    return [
        ResourceSpec(
            name="anti_at_field",
            fill=("per_shot_every_during_own_status_window", fill_every, duration),
            cap=cap,
            buffs=[linear_resource_buff("damage_taken_up", per_stack, "squad", lifetime=stack_lifetime)],
            resets=[{"trigger": "own_burst_delayed", "delay": duration, "value": 0}],
        )
    ]


def build_anti_at_field_per_shot_rules(values):
    field = values["anti_at_field"]
    uncond_threshold = int(float(field["description_value_01"]))
    uncond_nuke = float(field["description_value_02"])
    windowed_nuke = float(field["description_value_05"])
    fill_every = int(float(field["description_value_04"]))
    window_duration = float(values["annihilation_state"]["description_value_02"])
    return [
        (uncond_threshold, "every", [instant_nuke_pulse_rule("per_shot", uncond_nuke)]),
        # gap #7: every `fill_every` shots WHILE in Annihilation State (a
        # `window_duration`-sec window anchored to her own burst).
        (
            (fill_every, window_duration),
            "every_during_own_status_window",
            [instant_nuke_pulse_rule("per_shot", windowed_nuke)],
        ),
    ]


def build_annihilation_state_rules(values, caster_atk):
    annihilation = values["annihilation_state"]
    duration = float(annihilation["description_value_02"])
    # Effect 1 is the price of the state: her normal attacks are cut while the
    # other two effects raise everything else. Negative, because it is the
    # DOWN direction of the same Final ATK modifier.
    normal_attack_multiplier = -float(annihilation["description_value_01"]) / 100
    atk_from_caster_atk = caster_atk * float(annihilation["description_value_04"]) / 100
    attack_damage = float(annihilation["description_value_05"]) / 100

    def action(context, caster_slug, time, registry):
        registry.add(Effect("normal_attack_damage_multiplier", normal_attack_multiplier,
                            "self", duration, caster_slug), applied_at=time)
        registry.add(Effect("flat_atk", atk_from_caster_atk, "self", duration, caster_slug), applied_at=time)
        registry.add(Effect("attack_damage_up", attack_damage, "self", duration, caster_slug), applied_at=time)

    return [SkillRule(trigger="own_burst_activate", action=action)]


def annihilation_state_refill(values):
    """Annihilation State's "Effect 2: Reloads 21% magazine(s)" - a one-shot
    percentage refill at her own burst, not a repeating shot counter."""
    state = values["annihilation_state"]
    return {"percent": float(state["description_value_03"]),
            "scope": "self", "event": "own_burst"}


def build_emergency_repair_rules(values):
    repair = values["emergency_repair"]
    attack_damage = float(repair["description_value_01"]) / 100
    duration = float(repair["description_value_02"])
    heating_speed_down = float(repair["description_value_03"]) / 100
    heating_speed_duration = float(repair["description_value_04"])
    # Bullet 2 fires "when using Annihilation", and Annihilation is "After
    # Annihilation State ends" - so its effects land a whole state duration
    # after the burst that started it. Read from Annihilation State's own slot,
    # the same value `fire_delay` uses, so the two can never disagree.
    annihilation_delay = float(values["annihilation_state"]["description_value_02"])

    def action(context, caster_slug, time, registry):
        registry.add(Effect("attack_damage_up", attack_damage, "self", duration, caster_slug), applied_at=time)

    def heating_action(context, caster_slug, time, registry):
        # Effect 1: "MG heating up speed down 100% for 3 sec" (slots _03/_04).
        # Negative, because a down arrow subtracts. Applied at a FUTURE instant:
        # the registry stores (effect, applied_at) and answers by time, so a
        # window that opens later needs no delayed-trigger machinery.
        registry.add(
            Effect("mg_heating_speed_percent", -heating_speed_down, "self",
                   heating_speed_duration, caster_slug),
            applied_at=time + annihilation_delay,
        )

    return [
        SkillRule(trigger="full_burst_enter", action=action, condition=own_burst_fired_this_cycle()),
        SkillRule(trigger="own_burst_activate", action=heating_action),
    ]


def build_asuka_weapon_mode_schedule(values):
    """Emergency Repair's "Removes 100% of ammo" (slot _05), as a segment that
    fires nothing. Its length is her own reload under the same bullet's "Reload
    speed is fixed at a 60% increase" (slot _08) - "fixed" overrides whatever
    else is live, so it is derived from that value alone.

    The segment ends by starting a fresh magazine, which re-arms her warm-up -
    that new ramp is scaled by whatever `mg_heating_speed_percent` total is
    live the instant it opens, Effect 1's own -100% summed against any other
    producer targeting her. An MG ally buffer reaching her for the segment's
    whole span (e.g. Rei Ayanami: Tentative Name's Maintenance and Resupply)
    cancels Effect 1 out and leaves the new magazine's warm-up unmodified.
    """
    repair = values["emergency_repair"]
    fixed_reload_speed = float(repair["description_value_08"]) / 100
    weapon_stats = values["caster_weapon_stats"]
    return silent_reload_segments(
        "asuka-shikinami-langley-wille",
        reload_time_with_speed(weapon_stats["reload_time"], fixed_reload_speed),
        weapon_stats["weapon"],
        # Same "when using Annihilation" trigger as Effect 1 above: the dump
        # lands after Annihilation State ends, not at the burst that opened it.
        offset=float(values["annihilation_state"]["description_value_02"]),
    )


def build_annihilation_dynamic_hit_count_nukes(values):
    annihilation = values["annihilation_state"]
    duration = float(annihilation["description_value_02"])
    nuke = float(annihilation["description_value_06"])
    return [{
        "resource": "anti_at_field", "base_percent": nuke, "fire_delay": duration,
    }]
