import pytest

"""Burst-3 attacker batch eb1: Noir, Isabel, Liberalio (least engine-blocked).
Values are the real max-level (base-skill) figures from lootandwaifus, slots
numbered left-to-right per skill.
"""
from app.effects import Effect, EffectRegistry
from app.skill_rules.isabel import (
    POINTED_FEATHER_COOLDOWN,
    build_isabel_rules,
    pointed_feather_percent,
    sonic_chaser_burst_percent,
)
from app.skill_rules.liberalio import (
    build_calm_depths_charge_rules,
    build_liberalio_per_shot_rules,
    build_liberalio_rules,
    build_strange_currents_immunity_rules,
    submerged_world_burst_percent,
)
from app.skill_rules.noir import build_noir_rules, finale_burst_percent
from app.squad_engine import SquadContext, SquadMember, fire_trigger

ALLY = {"slug": "ally", "element": "Iron"}


def deck_ctx(src_slug, element="Wind"):
    return SquadContext([
        SquadMember(src_slug, burst_tier=3, element=element),
        SquadMember("ally", burst_tier=1, element="Iron"),
    ])


# --- Noir (SG/Wind) ---
NOIR_ATK = 100000
NOIR = {
    "lucky_charm": {"description_value_01": "14.08"},
    "finale": {
        "description_value_01": "351.64", "description_value_02": "13.93", "description_value_03": "10",
        "description_value_04": "23.23", "description_value_05": "10", "description_value_06": "11.61",
        "description_value_07": "30", "description_value_08": "19.36", "description_value_09": "30",
    },
    "caster_atk": NOIR_ATK,
}


def test_noir_lucky_charm_squad_atk_from_battle_start():
    reg = EffectRegistry()
    fire_trigger("battle_start", {"noir": build_noir_rules(NOIR)}, deck_ctx("noir"), reg, 0.0)
    assert round(reg.total_for("flat_atk", ALLY, 0.0), 2) == round(0.1408 * NOIR_ATK, 2)


def test_noir_finale_burst_parts_buffs_stack_then_expire():
    reg = EffectRegistry()
    fire_trigger("own_burst_activate", {"noir": build_noir_rules(NOIR)}, deck_ctx("noir"), reg, 0.0)
    # both parts buffs active in the first 10s -> sum
    assert round(reg.total_for("damage_to_parts_up", ALLY, 0.0), 4) == round(0.2323 + 0.1936, 4)
    assert round(reg.total_for("damage_to_parts_up", ALLY, 11.0), 4) == 0.1936  # 10s one expired
    assert reg.total_for("damage_to_parts_up", ALLY, 31.0) == 0.0  # 30s one expired


def test_noir_finale_burst_percent():
    assert finale_burst_percent(NOIR) == 351.64


# --- Isabel (SG/Electric) ---
ISABEL = {
    "marked_target": {
        "description_value_01": "6.26", "description_value_02": "45", "description_value_03": "18.03",
        "description_value_04": "45", "description_value_05": "17.28", "description_value_06": "45",
    },
    "pointed_feather": {"description_value_01": "5", "description_value_02": "170.58"},
    "sonic_chaser": {
        "description_value_01": "149.85", "description_value_02": "39.96", "description_value_03": "5",
        "description_value_04": "299.7", "description_value_05": "349.65", "description_value_06": "5",
    },
}


def test_isabel_marked_target_escalates_and_refreshes_over_bursts():
    reg = EffectRegistry()
    ctx = deck_ctx("isabel", "Electric")
    rules = {"isabel": build_isabel_rules(ISABEL)}
    isa = {"slug": "isabel", "element": "Electric"}

    fire_trigger("own_burst_activate", rules, ctx, reg, 0.0)   # burst 1 -> MT1 crit rate
    assert round(reg.total_for("crit_rate", isa, 0.0), 4) == 0.0626
    assert reg.total_for("other_critical_damage_sources", isa, 0.0) == 0.0

    fire_trigger("own_burst_activate", rules, ctx, reg, 40.0)  # burst 2 -> + MT2 crit damage
    assert round(reg.total_for("other_critical_damage_sources", isa, 40.0), 4) == 0.1803
    assert round(reg.total_for("crit_rate", isa, 40.0), 4) == 0.0626  # refreshed, not stacked (2x)
    assert reg.total_for("atk_percent", isa, 40.0) == 0.0

    fire_trigger("own_burst_activate", rules, ctx, reg, 80.0)  # burst 3 -> + MT3 ATK
    assert round(reg.total_for("atk_percent", isa, 80.0), 4) == 0.1728


def test_isabel_sonic_chaser_squad_damage_taken_debuff():
    reg = EffectRegistry()
    fire_trigger("own_burst_activate", {"isabel": build_isabel_rules(ISABEL)}, deck_ctx("isabel", "Electric"), reg, 0.0)
    assert round(reg.total_for("damage_taken_up", ALLY, 0.0), 4) == 0.3996
    assert reg.total_for("damage_taken_up", ALLY, 6.0) == 0.0  # 5s expired


def test_isabel_sonic_chaser_staged_additional_damage_escalates_by_burst_count():
    reg = EffectRegistry()
    ctx = deck_ctx("isabel", "Electric")
    rules = {"isabel": build_isabel_rules(ISABEL)}

    fire_trigger("own_burst_activate", rules, ctx, reg, 0.0)   # burst 1: MT1 only, no additional
    assert reg.drain_pulses("instant_damage_percent") == []

    fire_trigger("own_burst_activate", rules, ctx, reg, 40.0)  # burst 2: MT2 additional
    assert [round(p.value, 2) for p in reg.drain_pulses("instant_damage_percent")] == [299.7]

    fire_trigger("own_burst_activate", rules, ctx, reg, 80.0)  # burst 3: MT2 + MT3 additional
    assert sorted(round(p.value, 2) for p in reg.drain_pulses("instant_damage_percent")) == [299.7, 349.65]


def test_isabel_burst_and_periodic_percents():
    assert sonic_chaser_burst_percent(ISABEL) == 149.85
    assert pointed_feather_percent(ISABEL) == 170.58
    assert POINTED_FEATHER_COOLDOWN == 15.0


# --- Liberalio (SR/Wind) ---
LIBERALIO = {
    "calm_depths": {
        "description_value_01": "160", "description_value_02": "3", "description_value_03": "20.83",
        "description_value_04": "60", "description_value_05": "40.5", "description_value_06": "5",
        "description_value_07": "12.74", "description_value_08": "10",
    },
    "strange_currents": {"description_value_01": "231", "description_value_02": "1"},
    "submerged_world": {"description_value_01": "50", "description_value_02": "10", "description_value_03": "925"},
}
LIB = {"slug": "liberalio", "element": "Wind"}


def test_liberalio_full_burst_and_burst_self_buffs():
    reg = EffectRegistry()
    ctx = deck_ctx("liberalio")
    rules = {"liberalio": build_liberalio_rules(LIBERALIO)}
    fire_trigger("full_burst_enter", rules, ctx, reg, 0.0)
    assert round(reg.total_for("atk_percent", LIB, 0.0), 4) == 1.6      # ATK 160% for 3s
    assert reg.total_for("atk_percent", LIB, 3.1) == 0.0
    fire_trigger("own_burst_activate", rules, ctx, reg, 0.0)
    assert round(reg.total_for("attack_damage_up", LIB, 0.0), 4) == 0.5  # burst attack damage 50% 10s


def test_liberalio_burst_percent():
    assert submerged_world_burst_percent(LIBERALIO) == 925.0


def test_liberalio_per_shot_structure():
    ps = build_liberalio_per_shot_rules(LIBERALIO)
    assert len(ps) == 7
    assert ps[0][:2] == (1, "after")   # Raging Current
    assert ps[1][:2] == (1, "every")   # on-core attack damage
    assert [x[:2] for x in ps[2:]] == [(n, "after") for n in range(1, 6)]  # 5 additional-damage hits


def test_liberalio_raging_current_is_permanent_attack_damage():
    ps = build_liberalio_per_shot_rules(LIBERALIO)
    reg = EffectRegistry()
    ctx = deck_ctx("liberalio")
    for rule in ps[0][2]:
        rule.action(ctx, "liberalio", 2.0, reg)
    assert round(reg.total_for("attack_damage_up", LIB, 500.0), 4) == 2.31  # 231%, permanent


def test_liberalio_on_core_attack_damage_refreshes_for_60s():
    ps = build_liberalio_per_shot_rules(LIBERALIO)
    reg = EffectRegistry()
    ctx = deck_ctx("liberalio")
    for rule in ps[1][2]:
        rule.action(ctx, "liberalio", 2.0, reg)
    assert round(reg.total_for("attack_damage_up", LIB, 2.0), 4) == 0.2083
    assert reg.total_for("attack_damage_up", LIB, 63.0) == 0.0  # 60s window expired


def test_liberalio_additional_full_charge_nuke_emits_pulse():
    ps = build_liberalio_per_shot_rules(LIBERALIO)
    reg = EffectRegistry()
    ctx = deck_ctx("liberalio")
    for rule in ps[2][2]:  # first of the 5 additional-damage hits
        rule.action(ctx, "liberalio", 2.0, reg)
    assert [round(p.value, 2) for p in reg.drain_pulses("instant_damage_percent")] == [40.5]


# Module-level fixture aliases so the assembly verification harness
# (test_skill_value_assembly.py) can resolve each sub-skill fixture by name.
MARKED_TARGET = ISABEL["marked_target"]
POINTED_FEATHER = ISABEL["pointed_feather"]
SONIC_CHASER = ISABEL["sonic_chaser"]
CALM_DEPTHS = LIBERALIO["calm_depths"]
STRANGE_CURRENTS = LIBERALIO["strange_currents"]
SUBMERGED_WORLD = LIBERALIO["submerged_world"]
FINALE = NOIR["finale"]
LUCKY_CHARM = NOIR["lucky_charm"]


def test_strange_currents_refuses_allies_charge_speed_but_keeps_her_own():
    rules = {"liberalio": build_strange_currents_immunity_rules(STRANGE_CURRENTS)}
    ctx = SquadContext([
        SquadMember("liberalio", burst_tier=3, element="Wind"),
        SquadMember("buffer", burst_tier=1, element="Iron"),
    ])
    reg = EffectRegistry()
    fire_trigger("battle_start", rules, ctx, reg, time=0.0)

    lib = {"slug": "liberalio", "element": "Wind"}
    # An ally's charge-speed buff does not reach her...
    reg.add(Effect("charge_speed_percent", 0.5, "squad", None, "buffer"), applied_at=0.0)
    assert reg.total_for("charge_speed_percent", lib, now=1.0) == 0.0
    # ...but it still reaches everyone else.
    assert reg.total_for("charge_speed_percent", {"slug": "buffer", "element": "Iron"}, now=1.0) == 0.5
    # Her own overload/cube (registered under her own slug) still applies.
    reg.add(Effect("charge_speed_percent", 0.12, "self", None, "liberalio"), applied_at=0.0)
    assert abs(reg.total_for("charge_speed_percent", lib, now=1.0) - 0.12) < 1e-9


def test_calm_depths_gives_the_lowest_atk_burst3_a_flat_charge_time_cut():
    # "12.74% of the skill user's Charge Speed" is caster-based: the percent is
    # taken against LIBERALIO's own 1.5s charge, so allies receive a flat
    # 0.1911 sec - not a percent of their own charge.
    rules = {"liberalio": build_calm_depths_charge_rules(
        LIBERALIO, {"charge_time": 1.5})}
    ctx = SquadContext(
        [
            SquadMember("liberalio", burst_tier=3, element="Wind"),
            SquadMember("scarlet-black-shadow", burst_tier=3, element="Wind"),
            SquadMember("support", burst_tier=1, element="Iron"),
        ],
        base_atk={"liberalio": 400_000, "scarlet-black-shadow": 300_000, "support": 200_000},
    )
    reg = EffectRegistry()
    fire_trigger("full_burst_enter", rules, ctx, reg, time=5.0)

    scarlet = {"slug": "scarlet-black-shadow", "element": "Wind"}
    assert reg.total_for("charge_time_reduction_sec", scarlet, now=5.0) == pytest.approx(0.1274 * 1.5)
    assert reg.total_for("charge_time_reduction_sec", scarlet, now=15.1) == 0.0
    # The lower-ATK Burst 1 is not a candidate: the skill says Burst 3 only.
    assert reg.total_for("charge_time_reduction_sec",
                         {"slug": "support", "element": "Iron"}, now=5.0) == 0.0
    # Liberalio out-ATKs Scarlet here, so she does not take her own buff.
    assert reg.total_for("charge_time_reduction_sec",
                         {"slug": "liberalio", "element": "Wind"}, now=5.0) == 0.0


def test_calm_depths_targets_liberalio_herself_when_she_is_the_lowest_atk_b3():
    # She is a Burst 3 and is deliberately NOT excluded from the ranking -
    # Korean guides frame the requirement as "Liberalio's ATK must be higher
    # than Scarlet's" for Scarlet to receive it, which only makes sense if she
    # is in the pool. With the lower ATK she wins her own buff, which is the
    # deck-building mistake those guides warn about.
    rules = {"liberalio": build_calm_depths_charge_rules(LIBERALIO, {"charge_time": 1.5})}
    ctx = SquadContext(
        [
            SquadMember("liberalio", burst_tier=3, element="Wind"),
            SquadMember("scarlet-black-shadow", burst_tier=3, element="Wind"),
        ],
        base_atk={"liberalio": 200_000, "scarlet-black-shadow": 400_000},
    )
    reg = EffectRegistry()
    fire_trigger("full_burst_enter", rules, ctx, reg, time=5.0)

    assert reg.total_for("charge_time_reduction_sec",
                         {"slug": "scarlet-black-shadow", "element": "Wind"}, now=5.0) == 0.0
    assert reg.total_for("charge_time_reduction_sec",
                         {"slug": "liberalio", "element": "Wind"}, now=5.0) > 0.0


def test_charge_speed_immunity_also_refuses_external_flat_charge_cuts():
    # Her "immunity to Increase/Decrease Charge Speed effects" is about the
    # concept, not one engine stat, so it has to cover the caster-based
    # seconds form too - otherwise a Mana or a second Liberalio would speed
    # her up through the other stat.
    rules = {"liberalio": build_strange_currents_immunity_rules(STRANGE_CURRENTS)}
    ctx = SquadContext([
        SquadMember("liberalio", burst_tier=3, element="Wind"),
        SquadMember("other", burst_tier=3, element="Wind"),
    ])
    reg = EffectRegistry()
    fire_trigger("battle_start", rules, ctx, reg, time=0.0)

    lib = {"slug": "liberalio", "element": "Wind"}
    reg.add(Effect("charge_time_reduction_sec", 0.19, "squad", None, "other"), applied_at=0.0)
    assert reg.total_for("charge_time_reduction_sec", lib, now=1.0) == 0.0
    assert reg.total_for("charge_time_reduction_sec",
                         {"slug": "other", "element": "Wind"}, now=1.0) == 0.19
