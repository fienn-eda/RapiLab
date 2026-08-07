"""Soda: Twinkling Bunny (slug "soda-twinkling-bunny"), a Burst-3 Iron
Shotgun attacker. Base skills. PARTIAL - see below.

First consumer of resource_gated_buffs (a burst-fired buff gated on a
resource's count at the burst's own time - see raid_simulator's
`resource_gated_buffs` param).

Modeled (DPS-relevant): a "chip" resource (Golden Chip), capped at 50.
- Lucky Golden Chip (skills[0]) starts it at 50 (the cap) from battle start,
  and fills it +1 every 3 normal attacks DURING FULL BURST
  (`per_shot_every_during_full_burst`) - it IS her Critical Damage stack:
  +1.32% Critical Damage per stack, continuous.
- Onward, Soda! (skills[2], her burst): deals 628.7% of final ATK as damage,
  then SPENDS 17 Golden Chip ("stacks v 17 after the effect is applied" - a
  `resets` entry with a `value_fn`, trigger "own_burst"), floored at 1.
  Additionally, gated on the count right BEFORE that spend
  (`resource_gated_buffs`, `use_pre_reset`): at 20+ stacks self Hit Rate
  +38.91% for 15 sec, and at 30+ stacks self ATK +65.25% for
  15 sec. Whether the chip drains or settles is a property of the DECK, not
  of her: what matters is how many Full Burst windows she gets per spend.
  Bursting every cycle drains her (one window's refill against 17). Taking the
  seat every other cycle - the rotation Fienn plays, with two other Burst 3s -
  gives her two windows per spend, and with her own extension making those
  windows 15 sec the refill covers the spend: the chip cycles
  50 -> 33 -> 42 -> 50 and the ATK gate opens every time
  (docs/measurements/soda-golden-chip-in-play.md).

- Lucky Golden Chip's co-fired buff ("after 3 normal attacks during Full
  Burst, affects self and the 1 ally with the highest final ATK: Attack
  Damage +10.51% for 2 sec"): modeled via the FB-window-gated per-shot trigger
  (`per_shot_rules` mode "every_during_full_burst", gap #7, built 2026-07-15) -
  counting only in-Full-Burst shots, so it stays confined to that cycle's Full
  Burst window (10 sec, or longer when her own extension below is up).
  A REFRESHING buff (SG's 1.5/s cadence makes "every 3
  shots" every 2 sec, exactly the buff's own duration, so repeated fires
  refresh rather than stack). See `build_lucky_golden_chip_per_shot_rules`.

- Beginner's Rewards (skills[1]), both bullets. On entering Burst Stage 3 the
  chip decides a Full Burst Duration extension - +2 sec at 10+ stacks, a
  further +3 at 20+, cumulative, so 20+ is +5 (Fienn measured 15 sec windows
  in play). It affects ALL allies and does not need her to be the Burst 3 that
  opened the cycle. The extension is registered as a conditional per-cycle
  delta (`build_beginners_rewards_full_burst_delta`, resolved to a fixed point
  by simulate_raid) rather than the per-slug constant Isabel and Modernia use,
  because its value changes cycle to cycle with the chip.
  Gated on that same state, every in-Full-Burst normal attack fires a nuke -
  52.04% of final ATK in Time Extension I, 137.06% in II (also cumulative).
  See docs/superpowers/specs/2026-08-06-soda-full-burst-extension-design.md.

Not modeled / deferred:
- Nothing outstanding. (Her Hit Rate tier used to sit here as inert; it is
  modeled above since 2026-08-07. A shotgun's 250px spread is wide enough that
  +38.91% still only lifts her from 4.0% to 9.6% of a 50px core.)
"""
from app.effects import Effect, Pulse, ResourceSpec
from app.skill_rules._helpers import linear_resource_buff
from app.squad_engine import SkillRule


# Her burst never spends the chip below this, whatever it held (Fienn's in-game
# reading: bursting at 16 stacks leaves 1). Not in the skill text, so it is a
# measurement rather than a transcription.
CHIP_FLOOR = 1


SKILL_VALUE_MANIFESTS = {
    "soda-twinkling-bunny": {
        "source": "lootandwaifus",
        "test_module": "test_skill_rules_soda_twinkling_bunny",
        "keys": {
            "lucky_golden_chip": ("skills", 0),
            "beginners_rewards": ("skills", 1),
            "onward_soda": ("skills", 2),
        },
        "drop_tokens": {
            "lucky_golden_chip": [5],
            "onward_soda": [1, 3, 7],
        },
    },
}


def onward_soda_burst_percent(values):
    return float(values["onward_soda"]["description_value_02"])


def build_lucky_golden_chip_per_shot_rules(values):
    """gap #7: Lucky Golden Chip's co-fired buff - every N normal attacks DURING
    FULL BURST, refresh Attack Damage on self and the 1 ally with the highest
    final ATK (`top_atk_slugs`, which excludes the caster)."""
    chip = values["lucky_golden_chip"]
    every = int(float(chip["description_value_05"]))
    attack_damage = float(chip["description_value_06"]) / 100
    duration = float(chip["description_value_07"])

    def apply(context, caster_slug, time, registry):
        registry.add_refreshing(
            Effect("attack_damage_up", attack_damage, "self", duration, caster_slug,
                   refresh_group="lucky_golden_chip"),
            applied_at=time,
        )
        top = [s for s in context.top_atk_slugs(1, caster_slug, registry, time) if s != caster_slug]
        if top:
            registry.add_refreshing(
                Effect("attack_damage_up", attack_damage, "slugs:" + ",".join(top), duration, caster_slug,
                       refresh_group="lucky_golden_chip"),
                applied_at=time,
            )

    return [(every, "every_during_full_burst", [SkillRule(trigger="per_shot", action=apply)])]


def build_beginners_rewards_full_burst_delta(values):
    """Beginner's Rewards의 첫 불릿: Burst Stage 3 진입 시, 골든칩 스택에 따라
    풀 버스트 지속시간이 늘어난다(10+ 이면 +2초, 20+ 이면 거기에 +3초 더).

    누적이다 - "Each subsequent effect triggers all effects before it"이고,
    Fienn의 실측이 그것을 확인한다(풀 버스트 15초 = 10 + 2 + 3,
    docs/measurements/soda-golden-chip-in-play.md). 누적을 여기서 값에 반영해
    소비 지점이 다시 더하지 않게 한다.

    "Affects all allies"이므로 그녀가 그 사이클의 Burst 3일 필요가 없다 -
    덱에 있고 칩이 임계 위면 누가 창을 열든 걸린다."""
    rewards = values["beginners_rewards"]
    stage1_threshold = float(rewards["description_value_03"])
    stage1_seconds = float(rewards["description_value_04"])
    stage2_threshold = float(rewards["description_value_06"])
    stage2_seconds = float(rewards["description_value_07"])

    return {
        "resource": "chip",
        "cap": int(float(values["lucky_golden_chip"]["description_value_04"])),
        "tiers": [
            (stage1_threshold, stage1_seconds),
            (stage2_threshold, stage1_seconds + stage2_seconds),
        ],
    }


def build_beginners_rewards_per_shot_rules(values):
    """Beginner's Rewards의 둘째 불릿: 풀 버스트 중 평타마다, 그 사이클의 Time
    Extension 단계에 따라 최종 ATK의 52.04%(I) / 137.06%(II)를 넉으로 꽂는다.

    누적이다 - 첫 불릿과 같은 "Each subsequent effect triggers all effects
    before it" 아래에 있고, Fienn이 확인했다(2026-08-06).

    단계는 첫 불릿이 정하므로 이 넉은 확장이 모델되기 전에는 도달할 수 없었다.
    threshold 1 = 창 안 모든 샷. 창 밖 샷은 애초에 이 모드가 세지 않는다."""
    rewards = values["beginners_rewards"]
    stage1_percent = float(rewards["description_value_10"])
    stage2_percent = stage1_percent + float(rewards["description_value_12"])
    by_stage = {1: stage1_percent, 2: stage2_percent}

    def apply(context, caster_slug, time, registry):
        percent = by_stage.get(context.full_burst_extension_stage(time, caster_slug))
        if percent is None:
            return
        registry.add_pulse(
            Pulse("instant_damage_percent", percent, "self", caster_slug)
        )

    return [(1, "every_during_full_burst", [SkillRule(trigger="per_shot", action=apply)])]


def build_golden_chip_resources(values):
    chip = values["lucky_golden_chip"]
    soda = values["onward_soda"]

    initial_stacks = int(float(chip["description_value_01"]))
    crit_damage_per_stack = float(chip["description_value_03"]) / 100
    cap = int(float(chip["description_value_04"]))
    burst_spend = int(float(soda["description_value_01"]))

    return [
        ResourceSpec(
            name="chip",
            fill=("per_shot_every_during_full_burst", 3),
            cap=cap,
            buffs=[linear_resource_buff("other_critical_damage_sources", crit_damage_per_stack, "self")],
            resets=[
                {"trigger": "battle_start", "value": initial_stacks},
                {"trigger": "own_burst", "value_fn": _make_chip_spend(burst_spend)},
            ],
        )
    ]


def _make_chip_spend(amount):
    """"Golden Chip stacks v 17 after the effect is applied" - the burst SPENDS
    17 of whatever had built up, floored at 1 (Fienn bursted at 16 stacks in
    game and was left with 1)."""
    return lambda pre_value: max(CHIP_FLOOR, pre_value - amount)


def build_onward_soda_resource_gated_buffs(values):
    """Onward, Soda!'s two chip-gated stages. Both read the count BEFORE the
    burst's own 17-chip spend, and both are cumulative ("Each subsequent effect
    triggers all effects before it"), which falls out of two independent gates:
    a burst at 30+ opens both, one at 20-29 opens only the Hit Rate."""
    soda = values["onward_soda"]
    cap = int(float(values["lucky_golden_chip"]["description_value_04"]))
    hit_rate_gate = float(soda["description_value_03"])
    hit_rate_value = float(soda["description_value_04"]) / 100
    hit_rate_duration = float(soda["description_value_05"])
    atk_gate = float(soda["description_value_06"])
    atk_value = float(soda["description_value_07"]) / 100
    atk_duration = float(soda["description_value_08"])

    return [{
        "resource": "chip", "cap": cap, "use_pre_reset": True,
        "gate_fn": lambda count, gate=hit_rate_gate: count >= gate,
        "stat": "hit_rate", "value": hit_rate_value, "scope": "self",
        "duration": hit_rate_duration,
    }, {
        "resource": "chip", "cap": cap, "use_pre_reset": True,
        "gate_fn": lambda count, gate=atk_gate: count >= gate,
        "stat": "atk_percent", "value": atk_value, "scope": "self", "duration": atk_duration,
    }]
