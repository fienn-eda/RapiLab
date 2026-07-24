"""Laplace: Ultimate Hero (slug "laplace-ultimate-hero"), a Burst-3 Wind RL
attacker from MISSILIS. Collected from ShiftyPad (blablalink public data).

Her core damage engine is a charge-count-driven weapon transform loop (Warm Up
stacks -> "Electric Power, Fully Full Charge" weapon -> a full magazine at SMG
cadence -> Over Energy stages). Rather than build a general charge-count trigger
primitive - which would put shot tracking in the simulation hot path and make
every deck evaluation heavier - the loop is modeled on Fienn's in-game
measurements (2026-07-24) with the EXISTING weapon-mode segment machinery, the
same route red-hood took. Modeling it took her end-to-end damage from 46.4M to
125.4M (2.70x) on a 180s solo-raid shell.

The cycle is DERIVED, never hardcoded: the transform ends when the magazine
empties, so its length scales with [Max Ammo Increase]. At the measured
baseline (120 rounds, 2.5s reload) the period is 4.0 (Warm Up build) + 6.0
(120/20 at SMG cadence) + 2.5 (reload) = 12.5s, matching Fienn's measured
"about every 12.5 seconds".

Modeled (DPS-relevant):
- The weapon transform (skills[0]): each cycle silences her base RL and empties
  one magazine at 9.45%/shot, 20 shots/sec (`build_laplace_transform_schedule`,
  a weapon-mode segment). NO charge damage - Fienn measured that these shots do
  not take the 250% full-charge multiplier. `rate_of_fire` makes the profile a
  measurement anchor, so it takes no cadence buffs.
- Over Energy (skills[1]): one stage per TWO transforms (2 magazines = 240
  transformed normals = 100% Over Energy - Fienn), capped at 4 stages, each
  granting Max HP (+2/+3/+7/+10.5%). The stage Max HP feeds Electric Power's
  ATK below, which is re-applied at each stage.
- Mjolnir's stage bonus (skills[2]): 934.76% of final ATK x the Over Energy
  stage AT THAT BURST, as additional damage (full-burst-bonus eligible). One
  `scheduled_nukes` spec per stage, since a spec carries a single percent.
- Electric Power, Full Full Charge (skills[0]), at battle start: self ATK +
  (4.05% of her LIVE Max HP) continuously - resolved through
  max_hp_scaled_atk_rule, so ally/self Max HP buffs feed it. Snapshot at
  battle start: her own Over Energy stages raise Max HP later in the fight
  and must re-apply this buff to be reflected (see the deferred list).
- Over Energy (skills[1]), on her OWN Burst-3 activation ("[Burst Stage 3
  entry]" = after B2 fires, before B3 fires - Fienn's in-game reading,
  2026-07-24): self Attack Damage +52.14% for 10 sec. Encoded on
  own_burst_activate, not full_burst_enter: the two are numerically
  identical for a B3 unit's own nuke (same timestamp, inclusive buff
  window - see tests/test_burst_cycle_buff_timing.py), but
  full_burst_enter would also pay out on cycles where a DIFFERENT B3 unit
  bursts instead of her.
- Regenerative Energy Armament: Mjolnir (skills[2], her burst):
  - self ATK +63.36% for 10 sec.
  - burst nuke: 2953.84% of final ATK (default attack type).

Not modeled / deferred:
- Warm Up's Charge Speed +10% per stack (skills[0]): not modeled as a buff
  because it is already IN the measurement - the 4.0s build time Fienn timed
  (1.0 + 0.9 + 0.8 + 0.7 + 0.6) is the ramp itself. Encoding it as a live
  charge-speed buff on top would double-count it, and it never holds max
  anyway (5 stacks are consumed to fire the transform).
- Pierce on the transformed weapon: the pierce PROPERTY has no engine
  representation (`pierce_damage_up` is a damage bucket, not the property) -
  same limitation red-hood carries.
- The reload gap after a transform: `generate_segmented_shots` resumes the base
  weapon at the segment's end with a fresh magazine and no reload, so she fires
  ~2 extra base shots during the 2.5s reload the real cycle spends. At 2.5% a
  shot this is a rounding error against the transform, and the reload IS
  counted in the cycle period, which is what actually matters.
- ASSUMPTION (worth confirming): the Over Energy stage Max HP values
  2/3/7/10.5% are read as the value AT each stage, REPLACING the previous one
  (escalating tier), not as a cumulative sum. If the original text is
  cumulative, only the value handed to the refreshing effect changes.
"""
from app.effects import Effect
from app.skill_rules._helpers import buff_rule, max_hp_scaled_atk_rule
from app.squad_engine import SkillRule

SLUG = "laplace-ultimate-hero"

# Fienn's in-game measurement (2026-07-24).
SMG_RATE_OF_FIRE = 20.0        # the transformed weapon fires at SMG cadence
WARM_UP_BUILD_SECONDS = 4.0    # 5 full charges: 1.0 + 0.9 + 0.8 + 0.7 + 0.6
OVER_ENERGY_TRANSFORMS_PER_STAGE = 2   # 240 transformed normals = 2 full magazines
OVER_ENERGY_MAX_STAGE = 4

_ELECTRIC_POWER_GROUP = "electric_power_atk"
_OVER_ENERGY_GROUP = "over_energy_stage_max_hp"
_PLAN_ATTR = "_laplace_ultimate_hero_plan"


def _plan_from_percent(weapon, max_ammo_percent):
    """(shots, window_sec, period_sec) for one transform cycle.

    Nothing here is a constant: the magazine the transform has to empty scales
    with [Max Ammo Increase] exactly like a normal magazine does (same
    `round(max_ammo * (1 + pct))` rule attack_rate uses), and the window is
    just that magazine at SMG cadence. Period = Warm Up build + window +
    reload. At the measured baseline (120 rounds, 2.5s reload) this is
    4.0 + 6.0 + 2.5 = 12.5s, matching Fienn's "about every 12.5 seconds"."""
    shots = max(1, round(int(weapon["max_ammo"]) * (1 + max_ammo_percent)))
    window = shots / SMG_RATE_OF_FIRE
    return shots, window, WARM_UP_BUILD_SECONDS + window + float(weapon["reload_time"])


def _transform_times(period, fight_duration):
    times, t = [], WARM_UP_BUILD_SECONDS
    while t < fight_duration:
        times.append(t)
        t += period
    return times


def _stage_times(period, window, fight_duration):
    """[(stage, time)] - stage s lands when the 2s-th transform window ends."""
    times = _transform_times(period, fight_duration)
    out = []
    for stage in range(1, OVER_ENERGY_MAX_STAGE + 1):
        index = stage * OVER_ENERGY_TRANSFORMS_PER_STAGE - 1
        if index >= len(times):
            break
        out.append((stage, times[index] + window))
    return out


def _stage_at(stage_times, time):
    stage = 0
    for value, at in stage_times:
        if at <= time:
            stage = value
    return stage


def _caster_target(context, caster_slug):
    by_slug = {m.slug: m for m in context.members}
    return {"slug": caster_slug, "element": by_slug[caster_slug].element}


SKILL_VALUE_MANIFESTS = {
    "laplace-ultimate-hero": {
        "source": "shiftypad",
        "test_module": "test_skill_rules_laplace_ultimate_hero",
        "keys": {
            "electric_power_full_full_charge": ("skills", 0),
            "over_energy": ("skills", 1),
            "regenerative_energy_armament_mjolnir": ("skills", 2),
        },
    },
}


def laplace_ultimate_hero_burst_percent(values):
    return float(values["regenerative_energy_armament_mjolnir"]["description_value_03"])


def build_laplace_ultimate_hero_rules(values, caster_max_hp):
    s1 = values["electric_power_full_full_charge"]
    s2 = values["over_energy"]
    burst = values["regenerative_energy_armament_mjolnir"]

    battle_start_atk_pct = float(s1["description_value_01"]) / 100  # Max HP의 4.05%

    fb_attack_damage = float(s2["description_value_06"]) / 100  # 52.14%
    fb_attack_damage_dur = float(s2["description_value_07"])     # 10 sec

    burst_atk = float(burst["description_value_01"]) / 100  # 63.36%
    burst_atk_dur = float(burst["description_value_02"])     # 10 sec

    return [
        # refreshing + refresh_group: the Over Energy stage rule below re-applies
        # this same bullet with a bigger Max HP, and the re-application must
        # REPLACE it rather than stack on top of it.
        max_hp_scaled_atk_rule(
            "battle_start", battle_start_atk_pct, "self", None, caster_max_hp,
            refreshing=True, refresh_group=_ELECTRIC_POWER_GROUP,
        ),
        _over_energy_stage_rule(values, caster_max_hp),
        # 스킬텍스트의 [버스트 3단계 진입 시] = 그녀 자신이 B3를 쏘는 순간
        # (Fienn 실측 2026-07-24). own_burst_activate는 넉이 기록되기 전에 발동해
        # 이 버프가 그녀의 버스트딜에 곱해지고, 그녀가 버스트하지 않은 사이클엔
        # 지급되지 않는다 (full_burst_enter는 후자를 못 막는다).
        buff_rule("own_burst_activate", [("attack_damage_up", fb_attack_damage, "self", fb_attack_damage_dur)]),
        buff_rule("own_burst_activate", [("atk_percent", burst_atk, "self", burst_atk_dur)]),
    ]


def _over_energy_stage_rule(values, caster_max_hp):
    """Over Energy stages, pre-registered at their future times.

    Fired on the FIRST Full Burst rather than at battle start because the
    overload effects (including [Max Ammo Increase], which decides the
    transform period) are appended LAST among a unit's battle_start rules -
    reading them at battle_start would always see zero. By the first Full
    Burst they are in the registry, and the earliest stage lands much later
    (~22.5s at the measured baseline), so pre-adding future-dated effects here
    is replay-safe (the same pre-add pattern `periodic_rules` uses).

    Each stage REPLACES the previous one (refreshing, one group) - the skill
    lists 2/3/7/10.5% as the value AT each stage, read as an escalating tier
    rather than a cumulative sum. If the original text turns out to be
    cumulative, only the value passed here changes.
    """
    s1 = values["electric_power_full_full_charge"]
    s2 = values["over_energy"]
    weapon = values["caster_weapon_stats"]
    atk_pct = float(s1["description_value_01"]) / 100
    stage_max_hp_pcts = [float(s2[f"description_value_0{i}"]) / 100 for i in (2, 3, 4, 5)]

    def action(context, caster_slug, time, registry):
        if context.activation_count(caster_slug, "full_burst_enter") != 1:
            return
        target = _caster_target(context, caster_slug)
        _, window, period = _plan_from_percent(
            weapon, registry.total_for("max_ammo_percent", target, time)
        )
        # Enough horizon to reach the last stage; effects landing past the
        # fight's end simply never become active.
        horizon = WARM_UP_BUILD_SECONDS + period * (
            OVER_ENERGY_MAX_STAGE * OVER_ENERGY_TRANSFORMS_PER_STAGE
        )
        for stage, at in _stage_times(period, window, horizon):
            registry.add_refreshing(
                Effect("flat_max_hp", caster_max_hp * stage_max_hp_pcts[stage - 1],
                       "self", None, caster_slug, _OVER_ENERGY_GROUP),
                applied_at=at,
            )
            live_max_hp = caster_max_hp + registry.total_for("flat_max_hp", target, at)
            registry.add_refreshing(
                Effect("flat_atk", live_max_hp * atk_pct, "self", None,
                       caster_slug, _ELECTRIC_POWER_GROUP),
                applied_at=at,
            )

    return SkillRule(trigger="full_burst_enter", action=action)


def build_laplace_transform_schedule(values):
    """The transform window as a weapon-mode segment: the base RL goes silent
    and the transformed weapon empties its magazine at SMG cadence.

    No charge damage - Fienn measured that the transformed shots do NOT take
    the 250% full-charge multiplier, so the profile carries only
    `damage_percent`. `rate_of_fire` makes this a measurement anchor, so (per
    attack_rate's contract) it deliberately takes no cadence buffs.

    Also stashes the cycle plan on the context for the Mjolnir stage nukes,
    which resolve later in the same simulation and must use the SAME plan.
    """
    shot_percent = float(values["electric_power_full_full_charge"]["description_value_05"])
    weapon = values["caster_weapon_stats"]

    def schedule(context, fight_duration):
        shots, window, period = _plan_from_percent(weapon, context.max_ammo_percent_at(0.0))
        setattr(context, _PLAN_ATTR, (shots, window, period))
        profile = {
            "weapon": "SMG",
            "damage_percent": shot_percent,
            "rate_of_fire": SMG_RATE_OF_FIRE,
        }
        return [
            {"start": t, "until_shots": shots, "profile": profile}
            for t in _transform_times(period, fight_duration)
        ]

    return schedule


def build_laplace_stage_nukes(values):
    """Mjolnir's "934.76% of final ATK x Over Energy stage as additional damage".

    `scheduled_nukes` carries one percent per spec, so one spec per stage: each
    schedule returns only the bursts where the stage is exactly that value.
    Stages and transform times are both deterministic, so every burst gets the
    stage it actually had at that instant (Fienn's call, 2026-07-24) rather
    than a settled approximation. "as additional damage" -> full-burst-bonus
    eligible (Velvet precedent).
    """
    per_stage = float(values["regenerative_energy_armament_mjolnir"]["description_value_04"])
    weapon = values["caster_weapon_stats"]

    def make_schedule(stage):
        def schedule(context, fight_duration):
            plan = getattr(context, _PLAN_ATTR, None)
            if plan is None:  # no weapon-mode pass ran (unit not in this sim)
                plan = _plan_from_percent(weapon, 0.0)
            _, window, period = plan
            stage_times = _stage_times(period, window, fight_duration)
            return [
                t for t in context.burst_times.get(SLUG, [])
                if _stage_at(stage_times, t) == stage
            ]
        return schedule

    return [
        {
            "percent": per_stage * stage,
            "schedule": make_schedule(stage),
            "full_burst_bonus_eligible": True,
        }
        for stage in range(1, OVER_ENERGY_MAX_STAGE + 1)
    ]
