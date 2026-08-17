"""Laplace: Ultimate Hero (slug "laplace-ultimate-hero"), a Burst-3 Wind RL
attacker from MISSILIS. Value slots from ShiftyPad (blablalink public data),
effect text from lootandwaifus.

Her core damage engine is a charge-count-driven weapon transform loop (Warm Up
stacks -> "Electric Power, Fully Full Charge" weapon -> a full magazine at SMG
cadence -> Over Energy stages). Rather than build a general charge-count trigger
primitive - which would put shot tracking in the simulation hot path and make
every deck evaluation heavier - the loop is modeled on Fienn's in-game
measurements (2026-07-24) with the EXISTING weapon-mode segment machinery, the
same route red-hood took. Modeling it took her end-to-end damage from 46.4M to
125.4M (2.70x) on a 180s solo-raid shell.

The cycle is DERIVED, never hardcoded: the transform ends when the magazine
empties, so its length scales with [Max Ammo Increase]. At the baseline
(120 rounds, 2.5s file reload) the period is 4.0 (Warm Up build) + 0.617
(weapon-change motion) + 5.0 (120 at 24/s) + 2.648 (reload) = 12.265s.

**The cadence is 24 shots/sec, not the SMG class constant 20** (Fienn's range
reading, 2026-08-17): a magazine spans 293 and 292 frames first-shot to
last-shot, ~2.5 frames per shot. See `docs/measurements/laplace-uh-transform-loop.md`.

Modeled (DPS-relevant):
- The weapon transform (skills[0]): each cycle silences her base RL and empties
  one magazine at 9.45%/shot, 24 shots/sec (`build_laplace_transform_schedule`,
  a weapon-mode segment). NO charge damage - Fienn measured that these shots do
  not take the 250% full-charge multiplier. `rate_of_fire` makes the profile a
  measurement anchor, so it takes no cadence buffs.
- Over Energy (skills[1]): one stage per TWO transforms (2 magazines = 240
  transformed normals = 100% Over Energy - Fienn), capped at 4 stages, each
  granting Max HP (+2/+3/+7/+10.5%). The stages are CUMULATIVE - the skill
  says "[Each subsequent effect triggers all effects before it:]", so stage 2
  holds 1+2 and stage 4 holds 1+2+3+4 = +22.5% Max HP (Fienn, 2026-07-24).
  That Max HP feeds Electric Power's ATK above, which is re-applied at each
  stage so the growth is actually reflected.
- Mjolnir's stage bonus (skills[2]): 934.76% of final ATK x the Over Energy
  stage AT THAT BURST. One
  `scheduled_nukes` spec per stage, since a spec carries a single percent.
- Electric Power, Full Full Charge (skills[0]), at battle start: self ATK +
  (4.05% of her LIVE Max HP) continuously - resolved through
  max_hp_scaled_atk_rule, so ally/self Max HP buffs feed it. Snapshot at
  battle start: her own Over Energy stages raise Max HP later in the fight
  and must re-apply this buff to be reflected (see the deferred list).
- Over Energy (skills[1]), on "[Burst Stage 3 entry]" (= after B2 fires,
  before B3 fires - Fienn's in-game reading, 2026-07-24): self Attack Damage
  +52.14% for 10 sec. That phrase describes the STAGE, so it rides
  `ally_burst_activate` + `burst_stage_entered(3)` - a deck seating a second
  Burst 3 splits the slot and the ally's cycles are Stage-3 entries too.
  Not `full_burst_enter`, which is the LATER instant (after the B3 cast) and
  so would miss her own burst damage.
- The transformed weapon's "Additional Effect: Gains Pierce" (skills[0]): the
  `has_pierce` property for exactly each transform window, pre-registered at the
  first Full Burst alongside the Over Energy stages (same reason - the plan needs
  [Max Ammo Increase], which is not in the registry at battle start). It rides
  the transform, not her burst: Mjolnir's text names no Pierce at all.
- Regenerative Energy Armament: Mjolnir (skills[2], her burst):
  - self ATK +63.36% for 10 sec.
  - burst nuke: 2953.84% of final ATK (default attack type).

- Over Energy (skills[1]): one stage per 240 transformed normal attacks - the
  text's "+5% per 12 normal attacks while in the transformed state, up to 100%"
  (slots 09/08/01), counted in SHOTS rather than in whole transform windows.
  At the baseline 120-round magazine those coincide (240 = two windows exactly),
  which is what made a "2 transforms per stage" constant look right; they part
  company as soon as a deck adds [Max Ammo Increase]. A stage then lands
  part-way through a window, and once a single window can hold 240 shots it
  skips a reload gap and arrives 6.5 sec sooner.
- "Removes 100% of ammo" when Electric Power, Fully Full Charge ends: a silent
  segment one reload long, right after the transform window, so the base weapon
  does not resume until that reload has been spent.

Not modeled / deferred:
- Warm Up's Charge Speed +10% per stack (skills[0]): not modeled as a buff
  because it is already IN the constant - the 4.0s build (1.0 + 0.9 + 0.8 +
  0.7 + 0.6) IS that ramp. Encoding it as a live charge-speed buff on top would
  double-count it, and it never holds max anyway (5 stacks are consumed to fire
  the transform).

  **A range reading of ~4.4s and "5% per stack" is not evidence against this**
  (`docs/measurements/charge-speed-scaling.md`). That reading came from an alt
  account whose skill levels were all 1, and the per-stack value is LEVEL
  SCALED: `description_value_02` is 5% at Lv1 and 10% at Lv10. A Lv1 ramp is
  1.00 + 0.95 + 0.90 + 0.85 + 0.80 = 4.50s, which is what was timed. The deck
  builder simulates max levels, so 4.0s is the right constant and stays
  (Fienn, 2026-08-17). The transform PERIOD looked like a second anomaly at the
  time - 16.1s read against 12.5s modeled - and it was not one either: that
  reading spanned stretches where the range boss briefly vanishes, which drops
  the aim and breaks the burst. Read on continuous fire only, the loop is
  11.883s on that account and the model reproduces it (see `_plan_from_percent`).
"""
from app.attack_rate import reload_time_with_speed
from app.effects import Effect, max_ammo_percent_total
from app.skill_rules._helpers import buff_rule, max_hp_scaled_atk_rule
from app.squad_engine import SkillRule, burst_stage_entered

SLUG = "laplace-ultimate-hero"

# The transformed weapon's cadence, measured in the range on continuous-fire
# stretches (Fienn, 2026-08-17): one magazine spans 293 and 292 frames between
# its first and last shot, i.e. ~2.5 frames per shot. NOT the project's SMG
# class constant, which is 20.0 - that one is the nominal 1440rpm (24.00/s)
# rounded UP to a 3-frame grid, and this weapon does not sit on that grid.
# Do not "fix" it back to RATE_OF_FIRE_60FPS["SMG"] for consistency.
TRANSFORM_RATE_OF_FIRE = 24.0
# The weapon change costs animation before the first transformed shot lands:
# reload-complete to first transformed shot measured 305 frames, of which the
# Warm Up build (5 full charges, same reading) is 268. See the module docstring
# for what the remainder does and does not separate.
TRANSFORM_MOTION_SECONDS = 37 / 60
WARM_UP_BUILD_SECONDS = 4.0    # 5 full charges: 1.0 + 0.9 + 0.8 + 0.7 + 0.6
OVER_ENERGY_MAX_STAGE = 4
OVER_ENERGY_BURST_STAGE = 3    # "[Burst Stage 3 entry]" - the stage, not her cast

# How many transform windows the Pierce grant is pre-registered for. A SkillRule
# is not handed `fight_duration`, and effects landing past the fight's end never
# become active, so this is a runaway guard sized far above any fight - 200
# windows is ~2500 sec at the baseline 12.3 sec period - not a quality knob.
PREREGISTERED_TRANSFORMS = 200

_ELECTRIC_POWER_GROUP = "electric_power_atk"
_OVER_ENERGY_GROUP = "over_energy_stage_max_hp"
_PLAN_ATTR = "_laplace_ultimate_hero_plan"


def _plan_from_percent(weapon, max_ammo_percent):
    """(shots, window_sec, period_sec) for one transform cycle.

    Nothing here is a constant: the magazine the transform has to empty scales
    with [Max Ammo Increase] exactly like a normal magazine does (same
    `round(max_ammo * (1 + pct))` rule attack_rate uses), and the window is
    just that magazine at the transformed cadence.

    Period = Warm Up build + weapon-change motion + window + reload, and the
    reload term is the SAME expression the silent segment spends
    (`reload_time_with_speed`), so the loop closes: the base weapon gets back
    exactly build + motion between one reload ending and the next window
    opening. Using the raw file value here instead left the two 0.148s apart.

    At the baseline (120 rounds, 2.5s file reload) this is
    4.0 + 0.617 + 5.0 + 2.648 = 12.265s. Fienn's range reading of the same loop
    - first transformed shot to first transformed shot - is 713 frames =
    11.883s on an account whose skill levels are 1 (a 4.47s build, not 4.0) and
    whose Resilience cube shortens the reload to 1.917s; those two account
    differences are the whole gap."""
    shots = max(1, round(int(weapon["max_ammo"]) * (1 + max_ammo_percent)))
    window = shots / TRANSFORM_RATE_OF_FIRE
    reload_seconds = reload_time_with_speed(float(weapon["reload_time"]), 0.0)
    period = WARM_UP_BUILD_SECONDS + TRANSFORM_MOTION_SECONDS + window + reload_seconds
    return shots, window, period


def _transform_times(period, fight_duration):
    """When each transform's FIRST SHOT lands - the build and the weapon-change
    motion both come before it."""
    times, t = [], WARM_UP_BUILD_SECONDS + TRANSFORM_MOTION_SECONDS
    while t < fight_duration:
        times.append(t)
        t += period
    return times


def over_energy_normals_per_stage(values):
    """Transformed normal attacks one Over Energy stage costs.

    "+5% per 12 normal attacks while in the transformed state, up to 100%" -
    so 100/5 = 20 activations of 12 shots each = 240. Read from the slots
    because all three numbers are skill values a rebalance can move.
    """
    s2 = values["over_energy"]
    cap = float(s2["description_value_01"])
    per_normal_count = float(s2["description_value_08"])
    per_trigger = float(s2["description_value_09"])
    return int(round(cap / per_trigger * per_normal_count))


def _stage_times(period, window, shots, normals_per_stage, fight_duration):
    """[(stage, time)] - when each Over Energy stage is reached.

    Counted in SHOTS, not in whole transform windows. The magazine scales with
    [Max Ammo Increase] and the stage cost does not, so a bigger magazine buys
    a stage sooner AND part-way through a window - at the baseline 120 rounds
    the two happen to coincide (240 = exactly two windows), which is what made
    a "2 transforms per stage" constant look right.
    """
    times = _transform_times(period, fight_duration)
    out = []
    for stage in range(1, OVER_ENERGY_MAX_STAGE + 1):
        needed = stage * normals_per_stage
        full_windows, remainder = divmod(needed, shots)
        # A remainder of 0 means the stage lands on the last shot of window
        # `full_windows`, not at the start of the next one.
        index = full_windows - 1 if remainder == 0 else full_windows
        if index >= len(times):
            break
        into_window = window if remainder == 0 else remainder / TRANSFORM_RATE_OF_FIRE
        out.append((stage, times[index] + into_window))
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
        # 스킬텍스트의 [버스트 3단계 진입 시]는 **단계**에 대한 서술이라 그 슬롯을
        # 누가 가져가든 일어난다 — 두 번째 B3를 앉히면 상대가 쏜 사이클도 3단계
        # 진입이다. 트리거가 넉 기록보다 먼저 발동하므로 그녀가 직접 쏜 사이클엔
        # 여전히 자기 버스트딜에 곱해진다. full_burst_enter는 캐스트 이후라 다르다.
        buff_rule("ally_burst_activate",
                  [("attack_damage_up", fb_attack_damage, "self", fb_attack_damage_dur)],
                  condition=burst_stage_entered(OVER_ENERGY_BURST_STAGE)),
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

    Each stage REPLACES the previous one in the registry (refreshing, one
    group), but the VALUE it carries is cumulative: the skill says "[Each
    subsequent effect triggers all effects before it]", so stage 2 is worth 1+2
    and stage 4 is worth 1+2+3+4 = +22.5% Max HP (Fienn, 2026-07-24). Refreshing
    is what stops the sum being double-counted when the next stage lands.
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
        shots, window, period = _plan_from_percent(
            weapon,
            max_ammo_percent_total(registry, target, time, int(weapon["max_ammo"])),
        )
        # Enough horizon to reach the last stage; effects landing past the
        # fight's end simply never become active.
        normals_per_stage = over_energy_normals_per_stage(values)
        horizon = WARM_UP_BUILD_SECONDS + period * (
            OVER_ENERGY_MAX_STAGE * normals_per_stage / shots + 1
        )
        # "Additional Effect: Gains Pierce" belongs to the TRANSFORMED weapon
        # (skills[0]), so it is up for exactly each transform window - not for
        # a duration off her burst, which Mjolnir's text never mentions. Pierce
        # Damage Up only credits a holder, so the window has to be the real one.
        for at in _transform_times(period, period * PREREGISTERED_TRANSFORMS):
            registry.add(
                Effect("has_pierce", 1.0, "self", window, caster_slug),
                applied_at=at,
            )
        for stage, at in _stage_times(period, window, shots, normals_per_stage, horizon):
            # 누적: 스킬 원문의 "[Each subsequent effect triggers all effects
            # before it:]" - stage 2는 1+2, stage 4는 1+2+3+4를 받는다
            # (Fienn 2026-07-24). refreshing이라 앞 단계 효과를 대체하되,
            # 값 자체가 그 단계까지의 합이다.
            registry.add_refreshing(
                Effect("flat_max_hp", caster_max_hp * sum(stage_max_hp_pcts[:stage]),
                       "self", None, caster_slug, _OVER_ENERGY_GROUP),
                applied_at=at,
            )
            live_max_hp = context.live_max_hp(caster_max_hp, target, at, registry)
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
            "rate_of_fire": TRANSFORM_RATE_OF_FIRE,
        }
        reload_seconds = reload_time_with_speed(weapon["reload_time"], 0.0)
        interval = 1.0 / TRANSFORM_RATE_OF_FIRE
        segments = []
        for t in _transform_times(period, fight_duration):
            segments.append({"start": t, "until_shots": shots, "profile": profile})
            # "Removes 100% of ammo" when Fully Full Charge ends: the base
            # weapon does not resume until one reload has been spent. An
            # `until_shots` window ends AT its last shot, so that instant is
            # where the silent window opens.
            transform_end = t + shots * interval
            if transform_end >= fight_duration:
                continue
            segments.append({
                "start": transform_end,
                "end": min(transform_end + reload_seconds, fight_duration),
                "profile": {
                    "weapon": weapon["weapon"],
                    "damage_percent": 0.0,
                    "rate_of_fire": 1.0 / (reload_seconds * 2),
                },
            })
        return segments

    return schedule


def build_laplace_stage_nukes(values):
    """Mjolnir's "934.76% of final ATK x Over Energy stage as additional damage".

    `scheduled_nukes` carries one percent per spec, so one spec per stage: each
    schedule returns only the bursts where the stage is exactly that value.
    Stages and transform times are both deterministic, so every burst gets the
    stage it actually had at that instant (Fienn's call, 2026-07-24) rather
    than a settled approximation.
    """
    per_stage = float(values["regenerative_energy_armament_mjolnir"]["description_value_04"])
    weapon = values["caster_weapon_stats"]
    normals_per_stage = over_energy_normals_per_stage(values)

    def make_schedule(stage):
        def schedule(context, fight_duration):
            plan = getattr(context, _PLAN_ATTR, None)
            if plan is None:  # no weapon-mode pass ran (unit not in this sim)
                plan = _plan_from_percent(weapon, 0.0)
            shots, window, period = plan
            stage_times = _stage_times(period, window, shots, normals_per_stage, fight_duration)
            return [
                t for t in context.burst_times.get(SLUG, [])
                if _stage_at(stage_times, t) == stage
            ]
        return schedule

    return [
        {
            "percent": per_stage * stage,
            "schedule": make_schedule(stage),
        }
        for stage in range(1, OVER_ENERGY_MAX_STAGE + 1)
    ]
