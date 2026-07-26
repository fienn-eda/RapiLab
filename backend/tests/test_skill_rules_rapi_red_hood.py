from types import SimpleNamespace

import pytest

from app.effects import EffectRegistry
from app.elements import ELEMENT_ADVANTAGE_BONUS
from app.raid_simulator import simulate_raid
from app.skill_rules.rapi_red_hood import (
    SKILL_VALUE_MANIFESTS,
    build_attachable_projectiles_rules,
    build_attachable_projectiles_scheduled_nukes,
    build_battlefield_assessment_rules,
    build_power_of_inheritance_rules,
    build_power_of_inheritance_stage1_rules,
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
    assert round(registry.total_for("damage_to_interruption_parts_up", rapi, now=5.0), 4) == 0.48
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
    assert registry.total_for("element_advantage_grant", rapi, now=100.0) == 1.0

    # non-Electric boss: no advantage grant, but the projectile-explosion buff
    # is unconditional and still lands
    wind_ctx = SquadContext(list(members), boss_element="Wind")
    registry = EffectRegistry()
    fire_trigger("battle_start", rules, wind_ctx, registry, time=0.0)
    assert registry.total_for("element_advantage_grant", rapi, now=100.0) == 0.0
    assert round(registry.total_for("projectile_explosion_damage_up", rapi, now=100.0), 4) == 1.006


def test_electric_boss_advantage_actually_raises_her_damage():
    """Regression through the DAMAGE path, not just the effect registry: her
    "applies Elemental Advantage damage to Electric Code enemies" clause must
    make her burst hit +10% harder against an Electric boss. Asserting only
    that the effect is produced is what let a version slip through where the
    effect existed but was discarded by the damage formula's advantage gate."""
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
        deck=deck, burst_damage_percents={"rapi-red-hood": 500.0}, base_stats=base_stats,
        enemy_def=0.0, gauge_charge_time=2.0, fight_duration=30.0,
        base_crit_rate=0.0, boss_element="Electric",
    )
    without = simulate_raid(rules_by_slug={"rapi-red-hood": []}, **kwargs)
    with_advantage = simulate_raid(
        rules_by_slug={"rapi-red-hood": build_attachable_projectiles_rules(ATTACHABLE_PROJECTILES)},
        **kwargs,
    )

    # Fire is naturally neutral against Electric, so the baseline gets no bonus.
    assert without["total_damage"] == 5000.0
    assert with_advantage["total_damage"] == pytest.approx(
        5000.0 * (1 + ELEMENT_ADVANTAGE_BONUS)
    )
    assert with_advantage["total_damage"] > without["total_damage"]


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
    "battlefield_assessment": VALUES,
    "attachable_projectiles": ATTACHABLE_PROJECTILES,
    "power_of_inheritance": POWER_OF_INHERITANCE,
}


class _FakeRegistry:
    """Minimal registry stand-in exposing a bare `.added` list - same pattern
    as test_skill_rules_cinderella_crystal_wave.py's helper (buff_rule's
    action only ever calls `registry.add`)."""

    def __init__(self):
        self.added = []

    def add(self, effect, applied_at):
        self.added.append((effect.stat, effect.value, effect.scope, effect.duration))


def _applied_buffs(rule):
    reg = _FakeRegistry()
    rule.action(context_without_burst1_ally(), "rapi-red-hood-b1", 0.0, reg)
    return reg.added


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


# Task 7: the B1-variant seat (Combat Assist standing in for Burst 1) uses
# Power of Inheritance's Stage 1 branch instead of Stage 3 - no damage, just
# a self burst-cooldown pulse and a squad flat-ATK buff off her own ATK.
def test_stage1_burst_is_support_only_cdr_and_caster_atk():
    values = {**RAPI_VALUES, "caster_atk": 100000.0}
    rules = build_power_of_inheritance_stage1_rules(values)
    assert len(rules) == 2
    # rules[0]: own_burst_activate cdr_pulse self 20.0
    # rules[1]: own_burst_activate buff flat_atk 100000*0.1801 squad 10.0
    assert ("flat_atk", pytest.approx(18010.0), "squad", 10.0) in _applied_buffs(rules[1])


def test_b1_variant_registered_as_tier1_candidate():
    from app.skill_rules.registry import (
        ENCODED_SLUGS, MODE_VARIANTS, VARIANT_BURST_TIERS, build_nikke_rules)
    assert MODE_VARIANTS["rapi-red-hood"] == ("rapi-red-hood", "rapi-red-hood-b1")
    assert VARIANT_BURST_TIERS["rapi-red-hood-b1"] == 1
    assert "rapi-red-hood-b1" in ENCODED_SLUGS
    rules, burst_percent = build_nikke_rules(
        "rapi-red-hood-b1", {**RAPI_VALUES, "caster_atk": 100000.0})
    assert burst_percent is None                       # Stage 1 use has no damage


def test_b1_variant_manifest_carries_data_slug_for_weapon_stats_load():
    assert SKILL_VALUE_MANIFESTS["rapi-red-hood-b1"]["data_slug"] == "rapi-red-hood"
    assert SKILL_VALUE_MANIFESTS["rapi-red-hood-b1"]["dotgg_slug"] == "rapi-red-hood"


# Step 4 end-to-end verification (Fienn's brief): seat the B1 variant as a
# deck's ONLY Burst-1 unit and confirm, through simulate_raid, that the
# already-encoded branch logic actually fires from that seat.
def test_b1_variant_combat_assist_buff_reaches_squad_damage():
    """(1) Combat Assist engages (no other Burst-1 ally in the deck), so her
    battlefield_assessment combat_assist_branch fires on full_burst_enter and
    the squad's attack_damage_up buff actually multiplies an ally's burst
    damage - compared against the same deck with her branch absent (what
    happens in-game once a real Burst-1 ally cancels Combat Assist, Fienn's
    rationale for excluding her from decks with another B1). Only cycle 1's
    damage is compared, so neither run's later-cycle CDR pulses matter here."""
    deck = [
        {"slug": "rapi-red-hood-b1", "burst_tier": 1, "element": "Fire", "cooldown": 40.0},
        {"slug": "tier2", "burst_tier": 2, "element": "Iron", "cooldown": 20.0},
        {"slug": "tier3", "burst_tier": 3, "element": "Iron", "cooldown": 20.0},
    ]
    base_stats = {
        "rapi-red-hood-b1": {"atk": 0.0, "def": 0.0, "max_hp": 0.0},
        "tier2": {"atk": 0.0, "def": 0.0, "max_hp": 0.0},
        "tier3": {"atk": 1000.0, "def": 0.0, "max_hp": 0.0},
    }
    kwargs = dict(
        deck=deck, base_stats=base_stats, burst_damage_percents={"tier3": 1000.0},
        enemy_def=0.0, gauge_charge_time=2.0, fight_duration=15.0,
    )
    with_ca = simulate_raid(
        rules_by_slug={"rapi-red-hood-b1": build_battlefield_assessment_rules(VALUES)}, **kwargs)
    without_ca = simulate_raid(rules_by_slug={"rapi-red-hood-b1": []}, **kwargs)

    def tier3_burst_damage(result):
        hits = [e["damage"] for e in result["damage_log"] if e["source"] == "burst"]
        assert len(hits) == 1
        return hits[0]

    expected_ratio = 1 + float(VALUES["description_value_05"]) / 100
    assert tier3_burst_damage(with_ca) == pytest.approx(
        tier3_burst_damage(without_ca) * expected_ratio)


def test_b1_variant_stage1_burst_cdr_speeds_up_her_own_recast_cycle():
    """(2) Her Stage 1 burst's self CDR pulse (-20s) actually shortens HER OWN
    burst_cycle readiness: cycle 1 always fires at gauge_charge_time (nobody
    has a "last used" time yet), so cycle 2 is the first cycle her nominal
    40s cooldown could gate - without the CDR it does (cycle 2 lands a full
    40s after cycle 1); with it, she's ready again 20s sooner, so she keeps
    pace with the rest of the squad every cycle from cycle 2 on instead of
    every other one."""
    values = {**RAPI_VALUES, "caster_atk": 0.0}
    deck = [
        {"slug": "rapi-red-hood-b1", "burst_tier": 1, "element": "Fire", "cooldown": 40.0},
        {"slug": "tier2", "burst_tier": 2, "element": "Iron", "cooldown": 0.0},
        {"slug": "tier3", "burst_tier": 3, "element": "Iron", "cooldown": 0.0},
    ]
    base_stats = {slug: {"atk": 0.0, "def": 0.0, "max_hp": 0.0}
                  for slug in ("rapi-red-hood-b1", "tier2", "tier3")}
    kwargs = dict(
        deck=deck, base_stats=base_stats, burst_damage_percents={},
        enemy_def=0.0, gauge_charge_time=2.0, fight_duration=60.0,
    )
    with_cdr = simulate_raid(
        rules_by_slug={"rapi-red-hood-b1": build_power_of_inheritance_stage1_rules(values)},
        **kwargs)
    without_cdr = simulate_raid(rules_by_slug={"rapi-red-hood-b1": []}, **kwargs)

    def burst_times(result):
        return [e["time"] for e in result["events"]
                if e["type"] == "burst" and e["slug"] == "rapi-red-hood-b1"]

    cdr_seconds = float(RAPI_VALUES["power_of_inheritance"]["description_value_02"])
    cycle1 = burst_times(without_cdr)[0]
    assert burst_times(without_cdr)[1] == pytest.approx(cycle1 + 40.0)
    assert burst_times(with_cdr)[0] == pytest.approx(cycle1)
    assert burst_times(with_cdr)[1] == pytest.approx(cycle1 + 40.0 - cdr_seconds)


def test_b1_variant_launcher_emits_through_the_real_registry_wiring():
    """(3) With a real MG weapon firing normal attacks, the 120-shot
    projectile launcher actually attaches and explodes for the b1 slug,
    confirming _SCHEDULED_NUKE_BUILDERS["rapi-red-hood-b1"] (registry.py) is
    wired correctly end to end - not just correct as a bare function call
    (already covered by test_stage3_cut_disabled_uses_flat_120_requirement
    above)."""
    from app.skill_rules.registry import get_scheduled_nukes

    values = {**RAPI_VALUES, "caster_atk": 0.0}
    scheduled = get_scheduled_nukes("rapi-red-hood-b1", values)
    assert scheduled is not None

    deck = [
        {"slug": "rapi-red-hood-b1", "burst_tier": 1, "element": "Fire", "cooldown": 40.0},
        {"slug": "tier2", "burst_tier": 2, "element": "Iron", "cooldown": 20.0},
        {"slug": "tier3", "burst_tier": 3, "element": "Iron", "cooldown": 20.0},
    ]
    base_stats = {slug: {"atk": 0.0, "def": 0.0, "max_hp": 0.0}
                  for slug in ("rapi-red-hood-b1", "tier2", "tier3")}
    weapon_stats = {
        "rapi-red-hood-b1": {"weapon": "MG", "damage_percent": 20.0, "max_ammo": 300,
                              "reload_time": 2.0, "charge_time": 0.0, "charge_damage_percent": 0.0},
    }
    result = simulate_raid(
        deck=deck,
        rules_by_slug={
            "rapi-red-hood-b1": build_attachable_projectiles_rules(ATTACHABLE_PROJECTILES),
        },
        burst_damage_percents={}, base_stats=base_stats, weapon_stats=weapon_stats,
        enemy_def=0.0, gauge_charge_time=2.0, fight_duration=60.0,
        scheduled_nukes={"rapi-red-hood-b1": scheduled},
    )
    scheduled_hits = [e for e in result["damage_log"]
                      if e["source"] == "scheduled" and e["slug"] == "rapi-red-hood-b1"]
    damage_types = {e["damage_type"] for e in scheduled_hits}
    assert "projectile_attachment" in damage_types
    assert "projectile_explosion" in damage_types
