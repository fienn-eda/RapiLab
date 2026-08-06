"""Real max-level (base-skill) figures from lootandwaifus, slots numbered
left-to-right per skill (stage-number references in the text are not slots).
"""
from app.effects import EffectRegistry, ResourceSpec
from app.raid_simulator import simulate_raid
from app.skill_rules.soda_twinkling_bunny import (
    build_beginners_rewards_full_burst_delta,
    build_beginners_rewards_per_shot_rules,
    build_golden_chip_resources,
    build_lucky_golden_chip_per_shot_rules,
    build_onward_soda_resource_gated_buffs,
    onward_soda_burst_percent,
)
from app.squad_engine import SquadContext, SquadMember

SODA = {"slug": "soda-twinkling-bunny", "element": "Iron"}
TOP_ALLY = {"slug": "ally", "element": "Iron"}

SODA_VALUES = {
    "lucky_golden_chip": {
        "description_value_01": "50", "description_value_02": "3",
        "description_value_03": "1.32", "description_value_04": "50",
        "description_value_05": "3", "description_value_06": "10.51", "description_value_07": "2",
    },
    "onward_soda": {
        "description_value_01": "17", "description_value_02": "628.7",
        "description_value_03": "20", "description_value_04": "38.91", "description_value_05": "15",
        "description_value_06": "30", "description_value_07": "65.25", "description_value_08": "15",
    },
    "beginners_rewards": {
        "description_value_01": "3", "description_value_02": "1",
        "description_value_03": "10", "description_value_04": "2",
        "description_value_05": "2", "description_value_06": "20",
        "description_value_07": "3", "description_value_08": "1",
        "description_value_09": "1", "description_value_10": "52.04",
        "description_value_11": "2", "description_value_12": "85.02",
    },
}


def test_onward_soda_burst_percent():
    assert onward_soda_burst_percent(SODA_VALUES) == 628.7


def test_beginners_rewards_full_burst_tiers_are_cumulative():
    """"Each subsequent effect triggers all effects before it" - 20스택 이상은
    Time Extension I(+2초)과 II(+3초)를 함께 받아 +5초다 (Fienn 실측: 풀 버스트
    15초 = 10 + 2 + 3)."""
    spec = build_beginners_rewards_full_burst_delta(SODA_VALUES)
    assert spec["resource"] == "chip"
    assert spec["cap"] == 50
    assert spec["tiers"] == [(10.0, 2.0), (20.0, 5.0)]


def test_beginners_rewards_reads_thresholds_and_seconds_from_slots():
    """상수로 박지 않는다 - 스킬 레벨이 바뀌면 값도 따라가야 한다."""
    lower = {
        **SODA_VALUES,
        "beginners_rewards": {**SODA_VALUES["beginners_rewards"],
                              "description_value_03": "8", "description_value_04": "1",
                              "description_value_06": "16", "description_value_07": "2"},
    }
    spec = build_beginners_rewards_full_burst_delta(lower)
    assert spec["tiers"] == [(8.0, 1.0), (16.0, 3.0)]


def test_beginners_rewards_nuke_scales_with_the_cycles_extension_stage():
    """넉도 누적이다 (Fienn 확정): II단계 한 발은 52.04 + 85.02 = 137.06%.
    확장이 없는 창(0단계)에서는 아예 안 나간다."""
    rules = build_beginners_rewards_per_shot_rules(SODA_VALUES)
    assert len(rules) == 1
    threshold, mode, skill_rules = rules[0]
    assert (threshold, mode) == (1, "every_during_full_burst")

    ctx = SquadContext([SquadMember("soda-twinkling-bunny", burst_tier=3, element="Iron")])
    reg = EffectRegistry()

    ctx.full_burst_extension_stages = [
        (0.0, 10.0, {}), (20.0, 32.0, {"soda-twinkling-bunny": 1}),
        (40.0, 55.0, {"soda-twinkling-bunny": 2}),
    ]

    skill_rules[0].action(ctx, "soda-twinkling-bunny", 5.0, reg)
    assert reg.drain_pulses("instant_damage_percent") == []      # 0단계: 넉 없음

    skill_rules[0].action(ctx, "soda-twinkling-bunny", 25.0, reg)
    pulses = reg.drain_pulses("instant_damage_percent")
    assert len(pulses) == 1
    assert round(pulses[0].value, 4) == 52.04                    # I단계

    skill_rules[0].action(ctx, "soda-twinkling-bunny", 45.0, reg)
    pulses = reg.drain_pulses("instant_damage_percent")
    assert len(pulses) == 1
    assert round(pulses[0].value, 4) == 137.06                   # II단계 = 52.04 + 85.02
    assert pulses[0].source_slug == "soda-twinkling-bunny"


def test_lucky_golden_chip_cofired_buff_targets_self_and_top_atk_ally():
    rules = build_lucky_golden_chip_per_shot_rules(SODA_VALUES)
    assert len(rules) == 1
    threshold, mode, skill_rules = rules[0]
    assert (threshold, mode) == (3, "every_during_full_burst")

    ctx = SquadContext(
        [
            SquadMember("soda-twinkling-bunny", burst_tier=3, element="Iron"),
            SquadMember("ally", burst_tier=1, element="Iron"),
        ],
        base_atk={"soda-twinkling-bunny": 10000.0, "ally": 50000.0},
    )
    reg = EffectRegistry()
    skill_rules[0].action(ctx, "soda-twinkling-bunny", 5.0, reg)
    # self and the highest-ATK ally each get Attack Damage +10.51% for 2 sec
    assert round(reg.total_for("attack_damage_up", SODA, now=5.0), 4) == 0.1051
    assert round(reg.total_for("attack_damage_up", TOP_ALLY, now=5.0), 4) == 0.1051

    # a second fire inside the 2s window refreshes, not stacks
    skill_rules[0].action(ctx, "soda-twinkling-bunny", 6.0, reg)
    assert round(reg.total_for("attack_damage_up", SODA, now=6.0), 4) == 0.1051
    # expires 2 sec after the latest fire
    assert reg.total_for("attack_damage_up", SODA, now=8.1) == 0.0


def test_golden_chip_resource_starts_at_cap_and_burst_spends_seventeen():
    specs = build_golden_chip_resources(SODA_VALUES)
    assert len(specs) == 1
    spec = specs[0]
    assert isinstance(spec, ResourceSpec)
    assert spec.name == "chip"
    assert spec.fill == ("per_shot_every_during_full_burst", 3)
    assert spec.cap == 50
    assert len(spec.resets) == 2
    assert spec.resets[0] == {"trigger": "battle_start", "value": 50}
    assert spec.resets[1]["trigger"] == "own_burst"

    # "Golden Chip stacks v 17" SPENDS 17 of whatever had built up - it does
    # not set the count to 17.
    spend = spec.resets[1]["value_fn"]
    assert spend(50) == 33
    assert spend(30) == 13
    # Floored at 1: Fienn bursted at 16 stacks in game and was left with 1.
    assert spend(16) == 1
    assert spend(17) == 1
    assert spend(1) == 1


def test_golden_chip_crit_damage_scales_linearly_per_stack():
    spec = build_golden_chip_resources(SODA_VALUES)[0]
    assert len(spec.buffs) == 1
    buff = spec.buffs[0]
    assert buff.stat == "other_critical_damage_sources"
    assert buff.scope == "self"
    assert round(buff.value_fn(50), 4) == round(0.0132 * 50, 4)
    assert round(buff.value_fn(17), 4) == round(0.0132 * 17, 4)


def test_onward_soda_atk_buff_gated_on_pre_reset_stacks_at_least_30():
    specs = build_onward_soda_resource_gated_buffs(SODA_VALUES)
    assert len(specs) == 1
    spec = specs[0]
    assert spec["resource"] == "chip"
    assert spec["cap"] == 50
    assert spec["use_pre_reset"] is True
    assert spec["gate_fn"](30) is True
    assert spec["gate_fn"](29) is False
    assert spec["stat"] == "atk_percent"
    assert round(spec["value"], 4) == 0.6525
    assert spec["scope"] == "self"
    assert spec["duration"] == 15.0


def _simulate(fight_duration):
    """Soda plus two damage-less totems, so every entry in the log is hers.
    Her SG fires 1.5/s with ammo enough never to reload, so Golden Chip fills
    once per 2 sec of Full Burst."""
    deck = [
        {"slug": "buffer", "burst_tier": 1, "element": "Iron", "cooldown": 20.0},
        {"slug": "midtier", "burst_tier": 2, "element": "Iron", "cooldown": 20.0},
        {"slug": "soda-twinkling-bunny", "burst_tier": 3, "element": "Iron", "cooldown": 40.0},
    ]
    base_stats = {
        "buffer": {"atk": 0, "def": 0, "max_hp": 0},
        "midtier": {"atk": 0, "def": 0, "max_hp": 0},
        "soda-twinkling-bunny": {"atk": 10000, "def": 0, "max_hp": 0},
    }
    sg = {"weapon": "SG", "damage_percent": 10.0, "max_ammo": 1000,
          "reload_time": 1.0, "charge_time": 0.0, "charge_damage_percent": 0.0}
    return simulate_raid(
        deck,
        {"buffer": [], "midtier": [], "soda-twinkling-bunny": []},
        burst_damage_percents={"soda-twinkling-bunny": onward_soda_burst_percent(SODA_VALUES)},
        base_stats=base_stats,
        enemy_def=0, gauge_charge_time=5.0, fight_duration=fight_duration, mode="auto",
        base_crit_rate=0.0,
        weapon_stats={"soda-twinkling-bunny": sg},
        resource_specs={"soda-twinkling-bunny": build_golden_chip_resources(SODA_VALUES)},
        resource_gated_buffs={
            "soda-twinkling-bunny": build_onward_soda_resource_gated_buffs(SODA_VALUES)
        },
    )


def test_soda_end_to_end_burst_spends_chip_and_gates_the_atk_buff():
    # Full chain: Golden Chip starts at cap (50) from battle start, so the
    # FIRST burst's pre-spend count is already >=30 -> the ATK buff fires;
    # the spend then takes the crit-damage stack down to 33 for the next cycle.
    result = _simulate(fight_duration=6.0)
    burst_hits = [e for e in result["damage_log"] if e["source"] == "burst"]
    assert len(burst_hits) == 1
    # the gated ATK buff is granted at the SAME instant as the burst nuke it
    # was earned by, so it boosts this burst hit too (both read at t=5.0).
    assert round(burst_hits[0]["damage"], 4) == round(10000 * 1.6525 * 6.287, 4)
    # SG fires 1.5/s (interval 2/3s); burst fires at t=5.0 -> shot index 8
    # (t=16/3=5.333) is the first shot after the burst, within the 15s ATK
    # window -> reflects ATK+65.25%.
    normals = sorted(
        [e for e in result["damage_log"] if e["source"] == "normal_attack"],
        key=lambda e: e["time"],
    )
    post_burst_shot = next(e for e in normals if e["time"] > 5.0)
    # x1.5: the burst opened Full Burst, so this shot also collects the +0.5
    # the major modifier gains inside the window (measured 2026-07-28).
    assert round(post_burst_shot["damage"], 4) == round(10000 * 1.6525 * 0.10 * 1.5, 4)


def test_soda_second_burst_still_clears_the_atk_gate_because_the_spend_leaves_stacks():
    # What the spend-vs-set reading decides. Spending: 50 - 17 = 33, plus the
    # 5 fills of the first Full Burst = 38 at the second burst, so the >=30 ATK
    # gate opens again. SETTING the count to 17 would leave 17 + 5 = 22 and the
    # gate would stay shut for every cycle after the first.
    result = _simulate(fight_duration=50.0)
    burst_hits = sorted(
        [e for e in result["damage_log"] if e["source"] == "burst"], key=lambda e: e["time"]
    )
    assert [round(e["time"], 3) for e in burst_hits] == [5.0, 45.0]
    for hit in burst_hits:
        assert round(hit["damage"], 4) == round(10000 * 1.6525 * 6.287, 4)


# Module-level fixture aliases so the assembly verification harness
# (test_skill_value_assembly.py) can resolve each sub-skill fixture by name.
LUCKY_GOLDEN_CHIP = SODA_VALUES["lucky_golden_chip"]
BEGINNERS_REWARDS = SODA_VALUES["beginners_rewards"]
ONWARD_SODA = SODA_VALUES["onward_soda"]
