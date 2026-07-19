from types import SimpleNamespace

import pytest

from app.effects import EffectRegistry
from app.elements import ELEMENT_ADVANTAGE_BONUS
from app.raid_simulator import simulate_raid
from app.skill_rules.rapi_red_hood import (
    build_attachable_projectiles_rules,
    build_attachable_projectiles_scheduled_nukes,
    build_battlefield_assessment_rules,
    build_power_of_inheritance_rules,
    power_of_inheritance_stage3_burst_percent,
)
from app.squad_engine import SquadContext, SquadMember, fire_trigger

# Real skill level 10 values from lootandwaifus.com for rapi-red-hood's
# skills[0] "Battlefield Assessment". 02/03 are branch labels the tokenizer
# picks up (self tier, branch numbers) that the builder doesn't read.
VALUES = {
    "description_value_01": "1",
    "description_value_02": "1",
    "description_value_03": "1",
    "description_value_04": "7.48",
    "description_value_05": "8.02",
    "description_value_06": "10",
    "description_value_07": "95.04",
    "description_value_08": "10",
    "description_value_09": "48",
    "description_value_10": "10",
}


def context_with_burst1_ally():
    return SquadContext(
        [
            SquadMember("rapi-red-hood", burst_tier=3, element="Fire"),
            SquadMember("anis-star", burst_tier=1, element="Electric"),
        ]
    )


def context_without_burst1_ally():
    return SquadContext(
        [
            SquadMember("rapi-red-hood", burst_tier=3, element="Fire"),
            SquadMember("someone-else", burst_tier=2, element="Iron"),
        ]
    )


def test_cancels_combat_assist_when_a_burst1_ally_is_present():
    ctx = context_with_burst1_ally()
    registry = EffectRegistry()
    rules = {"rapi-red-hood": build_battlefield_assessment_rules(VALUES)}

    fire_trigger("battle_start", rules, ctx, registry, time=0.0)

    assert ctx.has_status("rapi-red-hood", "Combat Assist") is False


def test_enters_combat_assist_when_no_burst1_ally_present():
    ctx = context_without_burst1_ally()
    registry = EffectRegistry()
    rules = {"rapi-red-hood": build_battlefield_assessment_rules(VALUES)}

    fire_trigger("battle_start", rules, ctx, registry, time=0.0)

    assert ctx.has_status("rapi-red-hood", "Combat Assist") is True


def test_self_buff_branch_fires_on_full_burst_enter_when_not_in_combat_assist():
    ctx = context_with_burst1_ally()
    registry = EffectRegistry()
    rules = {"rapi-red-hood": build_battlefield_assessment_rules(VALUES)}

    fire_trigger("battle_start", rules, ctx, registry, time=0.0)
    fire_trigger("full_burst_enter", rules, ctx, registry, time=5.0)

    rapi = {"slug": "rapi-red-hood", "element": "Fire"}
    assert round(registry.total_for("atk_percent", rapi, now=5.0), 4) == 0.9504
    assert round(registry.total_for("damage_to_parts_up", rapi, now=5.0), 4) == 0.48
    # this branch should NOT emit a squad-wide burst cooldown reduction
    assert registry.drain_pulses("burst_cooldown_reduction_sec") == []


def test_combat_assist_branch_fires_on_full_burst_enter_when_no_burst1_ally():
    ctx = context_without_burst1_ally()
    registry = EffectRegistry()
    rules = {"rapi-red-hood": build_battlefield_assessment_rules(VALUES)}

    fire_trigger("battle_start", rules, ctx, registry, time=0.0)
    fire_trigger("full_burst_enter", rules, ctx, registry, time=5.0)

    ally = {"slug": "someone-else", "element": "Iron"}
    assert round(registry.total_for("attack_damage_up", ally, now=5.0), 4) == 0.0802
    pulses = registry.drain_pulses("burst_cooldown_reduction_sec")
    assert len(pulses) == 1
    assert pulses[0].value == 7.48

    # and the self-buff branch should NOT have fired
    rapi = {"slug": "rapi-red-hood", "element": "Fire"}
    assert registry.total_for("atk_percent", rapi, now=5.0) == 0.0


# Real skill level 10 values for skills[1] "Attachable Projectiles". v01/v02
# are the permanent battle-start Damage-Up buffs; v03-v06 feed the 120-normal
# projectile launcher (build_attachable_projectiles_scheduled_nukes).
ATTACHABLE_PROJECTILES = {
    "description_value_01": "150.72",
    "description_value_02": "100.6",
    "description_value_03": "120",
    "description_value_04": "88.11",
    "description_value_05": "88.11",
    "description_value_06": "1",
}


def test_attachable_projectiles_grants_permanent_self_projectile_explosion_damage():
    ctx = context_with_burst1_ally()
    registry = EffectRegistry()
    rules = {"rapi-red-hood": build_attachable_projectiles_rules(ATTACHABLE_PROJECTILES)}

    fire_trigger("battle_start", rules, ctx, registry, time=0.0)

    rapi = {"slug": "rapi-red-hood", "element": "Fire"}
    # permanent: still active late into a 180s fight
    assert round(registry.total_for("projectile_explosion_damage_up", rapi, now=170.0), 4) == 1.006
    # self scope: allies get nothing
    ally = {"slug": "anis-star", "element": "Electric"}
    assert registry.total_for("projectile_explosion_damage_up", ally, now=170.0) == 0.0


def test_attachable_projectiles_elemental_advantage_only_vs_electric_boss():
    rapi = {"slug": "rapi-red-hood", "element": "Fire"}
    members = [SquadMember("rapi-red-hood", burst_tier=3, element="Fire")]
    rules = {"rapi-red-hood": build_attachable_projectiles_rules(ATTACHABLE_PROJECTILES)}

    electric_ctx = SquadContext(list(members), boss_element="Electric")
    registry = EffectRegistry()
    fire_trigger("battle_start", rules, electric_ctx, registry, time=0.0)
    assert registry.total_for("other_elemental_bonus", rapi, now=100.0) == ELEMENT_ADVANTAGE_BONUS

    # non-Electric boss: no advantage grant, but the projectile-explosion buff
    # is unconditional and still lands
    wind_ctx = SquadContext(list(members), boss_element="Wind")
    registry = EffectRegistry()
    fire_trigger("battle_start", rules, wind_ctx, registry, time=0.0)
    assert registry.total_for("other_elemental_bonus", rapi, now=100.0) == 0.0
    assert round(registry.total_for("projectile_explosion_damage_up", rapi, now=100.0), 4) == 1.006


# rapi-red-hood has no signature weapon (no dollskills entry), so these are
# the base skill's level-10 values for "Power of Inheritance". v01-v06 are the
# Stage 1 branch (not modeled); v07 labels "Stage 3"; v08 is the Stage 3 nuke;
# v09/v10 are its (deferred) Explosion Radius buff+duration; v11/v12 are the
# Projectile Attachment Damage Up rider+duration; v13 labels "Skill 2"; v14/v15
# are the launcher requirement cut+duration. Module-level so the assembly
# verification harness (test_skill_value_assembly.py) can resolve it by name.
POWER_OF_INHERITANCE = {
    "description_value_01": "1",
    "description_value_02": "20",
    "description_value_03": "100.62",
    "description_value_04": "10",
    "description_value_05": "18.01",
    "description_value_06": "10",
    "description_value_07": "3",
    "description_value_08": "2808",
    "description_value_09": "100.62",
    "description_value_10": "10",
    "description_value_11": "421.2",
    "description_value_12": "10",
    "description_value_13": "2",
    "description_value_14": "60",
    "description_value_15": "10",
}

RAPI_VALUES = {
    "attachable_projectiles": ATTACHABLE_PROJECTILES,
    "power_of_inheritance": POWER_OF_INHERITANCE,
}


def test_power_of_inheritance_stage3_burst_percent_reads_the_damage_slot():
    assert power_of_inheritance_stage3_burst_percent(POWER_OF_INHERITANCE) == 2808.0


def test_projectile_launcher_attaches_every_120_shots_and_explodes_on_fb_entry():
    specs = build_attachable_projectiles_scheduled_nukes(RAPI_VALUES)
    attach, explosion = specs
    assert attach["percent"] == 88.11 and attach["damage_type"] == "projectile_attachment"
    assert explosion["percent"] == 88.11 and explosion["damage_type"] == "projectile_explosion"

    context = SimpleNamespace(
        shot_times={"rapi-red-hood": [float(i) / 10 for i in range(1, 251)]},  # 0.1s 간격 250샷 (t=0.1~25.0)
        burst_times={"rapi-red-hood": []},
        full_burst_windows=[(30.0, 40.0)],
    )
    # 120번째(t=12.0)·240번째(t=24.0)에서 부착 - 둘 다 FB(30.0) 진입 시 일괄 폭발
    times = attach["schedule"](context, 180.0)
    assert times == [12.0, 24.0]
    assert explosion["schedule"](context, 180.0) == [30.0, 30.0]


def test_projectile_requirement_drops_to_60_inside_own_burst_window():
    specs = build_attachable_projectiles_scheduled_nukes(RAPI_VALUES)
    attach = specs[0]
    shots = [float(i) / 10 for i in range(1, 1201)]          # 0.1s 간격 120초
    context = SimpleNamespace(
        shot_times={"rapi-red-hood": shots},
        burst_times={"rapi-red-hood": [0.05]},               # 시작 직후 버스트 → 10초 창
        full_burst_windows=[],
    )
    times = attach["schedule"](context, 180.0)
    assert times[0] == 6.0     # 창(0.05~10.05) 안: 60번째 샷에서 발사
    assert times[1] == 18.0    # 리셋 후 60카운트 도달 시각 12.0은 창 밖 → 120 요구 복원, 120카운트 = t=18.0


def test_stage3_cut_disabled_uses_flat_120_requirement():
    specs = build_attachable_projectiles_scheduled_nukes(
        RAPI_VALUES, slug="rapi-red-hood-b1", stage3_requirement_cut=False)
    attach = specs[0]
    context = SimpleNamespace(
        shot_times={"rapi-red-hood-b1": [float(i) / 10 for i in range(1, 1201)]},
        burst_times={"rapi-red-hood-b1": [0.05]},
        full_burst_windows=[],
    )
    assert attach["schedule"](context, 180.0)[0] == 12.0     # 창 무시, 120 고정


def test_power_of_inheritance_burst_rider_buffs_attachment_window():
    rules = build_power_of_inheritance_rules(RAPI_VALUES)
    # own_burst_activate 트리거 1건: projectile_attachment_damage_up 4.212 / 10s self
    assert len(rules) == 1 and rules[0].trigger == "own_burst_activate"


def test_attachment_damage_grows_inside_power_of_inheritance_burst_window():
    """End-to-end regression through simulate_raid: the launcher's percent and
    damage_type (from build_attachable_projectiles_scheduled_nukes) actually
    get scaled by the Stage 3 rider's windowed projectile_attachment_damage_up.
    There's no reproducible "before the launcher was registered" baseline (no
    attachment-typed damage existed then), so this compares a deck with the
    rider rules against one without, on a fixed attach time inside her burst
    window (own_burst_activate fires at t=2.0 for this deck; window is
    [2.0, 12.0))."""
    attach_percent = build_attachable_projectiles_scheduled_nukes(RAPI_VALUES)[0]["percent"]
    scheduled_nukes = {"rapi-red-hood": [
        {"schedule": lambda context, fight_duration: [5.0],
         "percent": attach_percent, "damage_type": "projectile_attachment"},
    ]}
    deck = [
        {"slug": "tier1", "burst_tier": 1, "element": "Iron", "cooldown": 20.0},
        {"slug": "tier2", "burst_tier": 2, "element": "Iron", "cooldown": 20.0},
        {"slug": "rapi-red-hood", "burst_tier": 3, "element": "Fire", "cooldown": 40.0},
    ]
    base_stats = {
        "tier1": {"atk": 0.0, "def": 0.0, "max_hp": 0.0},
        "tier2": {"atk": 0.0, "def": 0.0, "max_hp": 0.0},
        "rapi-red-hood": {"atk": 1000.0, "def": 0.0, "max_hp": 10000.0},
    }
    kwargs = dict(
        deck=deck, burst_damage_percents={}, base_stats=base_stats,
        enemy_def=0.0, gauge_charge_time=2.0, fight_duration=30.0,
        base_crit_rate=0.0, scheduled_nukes=scheduled_nukes,
    )
    without_rider = simulate_raid(
        rules_by_slug={"rapi-red-hood": build_attachable_projectiles_rules(ATTACHABLE_PROJECTILES)},
        **kwargs,
    )
    with_rider = simulate_raid(
        rules_by_slug={"rapi-red-hood": (
            build_attachable_projectiles_rules(ATTACHABLE_PROJECTILES)
            + build_power_of_inheritance_rules(RAPI_VALUES)
        )},
        **kwargs,
    )

    def nuke(result):
        return [e for e in result["damage_log"] if e["source"] == "scheduled"][0]["damage"]

    permanent_up = float(ATTACHABLE_PROJECTILES["description_value_01"]) / 100
    windowed_up = float(POWER_OF_INHERITANCE["description_value_11"]) / 100
    expected_ratio = (1 + permanent_up + windowed_up) / (1 + permanent_up)
    assert nuke(with_rider) == pytest.approx(nuke(without_rider) * expected_ratio)
