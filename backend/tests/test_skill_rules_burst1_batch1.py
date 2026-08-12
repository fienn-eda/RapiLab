"""Tests for the first batch of Burst-1 supporters: Liter, Volume, Miranda.
Values are the real max-level (dollskill for Miranda) figures from dotgg.
"""
import pytest

from app.effects import EffectRegistry
from app.skill_rules.liter import build_liter_rules
from app.skill_rules.miranda import (
    build_health_up_hit_rate_rules,
    build_health_up_rules,
    build_miranda_base_rules,
    build_miranda_rules,
)
from app.skill_rules.volume import build_volume_rules
from app.squad_engine import SquadContext, SquadMember, fire_trigger

ALLY = {"slug": "ally", "element": "Fire"}


def deck_ctx(src_slug):
    return SquadContext([
        SquadMember(src_slug, burst_tier=1, element="Iron"),
        SquadMember("ally", burst_tier=3, element="Fire"),
    ])


def ranked_deck_ctx():
    # miranda (caster) + two carries + a low-ATK support, so top-2/top-1
    # highest-final-ATK targeting has a clear, checkable outcome.
    return SquadContext(
        [
            SquadMember("miranda", burst_tier=1, element="Iron"),
            SquadMember("carry_a", burst_tier=3, element="Fire"),
            SquadMember("carry_b", burst_tier=2, element="Fire"),
            SquadMember("support", burst_tier=1, element="Water"),
        ],
        base_atk={"miranda": 40000, "carry_a": 90000, "carry_b": 80000, "support": 30000},
    )


LITER = {
    "liter_boost": {
        "description_value_01": "2.34", "description_value_02": "2.7", "description_value_03": "3.17",
        "description_value_04": "45.17", "description_value_05": "5", "description_value_06": "12.46",
        "description_value_07": "5", "description_value_08": "14.42", "description_value_09": "5",
    },
    "double_boost": {"description_value_01": "66", "description_value_02": "5"},
}


def test_liter_full_burst_cdr_escalates_cumulatively():
    # Liter Boost's cooldown half carries the same "previous effects trigger
    # repeatedly" wording as Volume's Drop the Beat, on the same tier values
    # (2.34/2.70/3.17), so the tiers ADD: Fienn's 2026-07-27 range measurement
    # settled that shape.
    ctx = deck_ctx("liter")
    reg = EffectRegistry()
    rules = {"liter": build_liter_rules(LITER)}

    for want in (2.34, 2.34 + 2.7, 2.34 + 2.7 + 3.17, 2.34 + 2.7 + 3.17):
        fire_trigger("full_burst_enter", rules, ctx, reg, time=0.0)
        pulses = reg.drain_pulses("burst_cooldown_reduction_sec")
        assert round(sum(p.value for p in pulses), 4) == round(want, 4)


def test_liter_on_burst_buffs_unlock_one_tier_per_use():
    # Once: Max Ammo. Twice: + Critical Damage. Three times: + ATK. Double
    # Boost's own squad ATK is a separate bullet and lands on every use, so the
    # atk_percent total is 66% until Liter Boost's third tier adds 14.42%.
    ctx = deck_ctx("liter")
    reg = EffectRegistry()
    rules = {"liter": build_liter_rules(LITER)}

    # 20s apart, so each use's 5-sec windows have lapsed before the next.
    for use, (time, ammo, crit, atk) in enumerate([
        (0.0, 0.4517, 0.0, 0.66),
        (20.0, 0.4517, 0.1246, 0.66),
        (40.0, 0.4517, 0.1246, 0.66 + 0.1442),
        (60.0, 0.4517, 0.1246, 0.66 + 0.1442),
    ], start=1):
        fire_trigger("own_burst_activate", rules, ctx, reg, time=time)
        assert round(reg.total_for("max_ammo_percent", ALLY, time), 4) == round(ammo, 4), use
        assert round(reg.total_for("other_critical_damage_sources", ALLY, time), 4) == round(crit, 4), use
        assert round(reg.total_for("atk_percent", ALLY, time), 4) == round(atk, 4), use


VOLUME = {
    "drop_the_beat": {
        "description_value_01": "2.34", "description_value_02": "2.7", "description_value_03": "3.17",
        "description_value_04": "10.77", "description_value_05": "5", "description_value_06": "12.46",
        "description_value_07": "5", "description_value_08": "14.42", "description_value_09": "5",
    },
    "turn_up": {"description_value_01": "31.9", "description_value_02": "5"},
}


def test_volume_crit_damage_tiers_unlock_one_per_burst_use():
    # "Effects vary according to the number of uses. Each subsequent effect
    # triggers all effects before it" - so the sum is the STEADY state, reached
    # on the third use, not the opening value. Fienn's range measurement pinned
    # the first use at tier 1 alone (2026-07-27).
    ctx = deck_ctx("volume")
    reg = EffectRegistry()
    rules = {"volume": build_volume_rules(VOLUME)}

    # 20s apart, so each use's 5-sec windows have lapsed before the next.
    for use, (time, want) in enumerate(
        [(0.0, 0.1077), (20.0, 0.1077 + 0.1246), (40.0, 0.3765), (60.0, 0.3765)], start=1
    ):
        fire_trigger("own_burst_activate", rules, ctx, reg, time=time)
        assert round(reg.total_for("other_critical_damage_sources", ALLY, time), 4) == round(want, 4), use
    assert round(reg.total_for("crit_rate", ALLY, 60.0), 4) == 0.319


def test_volume_burst_cooldown_reduction_escalates_the_same_way():
    # Same bullet shape, same wording, on the Full Burst counter instead.
    ctx = deck_ctx("volume")
    reg = EffectRegistry()
    rules = {"volume": build_volume_rules(VOLUME)}

    # Cumulative, like the crit half: every unlocked tier fires and they add
    # (Fienn, 2026-07-27).
    for want in (2.34, 2.34 + 2.7, 2.34 + 2.7 + 3.17, 2.34 + 2.7 + 3.17):
        fire_trigger("full_burst_enter", rules, ctx, reg, time=0.0)
        assert round(sum(p.value for p in reg.drain_pulses("burst_cooldown_reduction_sec")), 4) == round(want, 4)


# Base ("skills") level-10 values - slug "miranda". Health Up! stops at slot 06
# (both steps are Hit Rate) and Wake Up! stops at slot 02, so the base build has
# no per-shot rule and no self buffs at all.
MIRANDA_BASE_HEALTH_UP = {
    "description_value_01": "30", "description_value_02": "5.44", "description_value_03": "5",
    "description_value_04": "30", "description_value_05": "3.79", "description_value_06": "5",
}
MIRANDA_BASE_WAKE_UP = {
    "description_value_01": "32.99", "description_value_02": "10",
}
MIRANDA_BASE_POWERING_UP = {
    "description_value_01": "1", "description_value_02": "40.4", "description_value_03": "10",
    "description_value_04": "56.23", "description_value_05": "10",
}
MIRANDA_BASE = {
    "health_up": MIRANDA_BASE_HEALTH_UP,
    "wake_up": MIRANDA_BASE_WAKE_UP,
    "powering_up": MIRANDA_BASE_POWERING_UP,
}

# Favorite Item ("dollskills") level-10 values - slug "miranda-signature".
MIRANDA_SIG_HEALTH_UP = {
    "description_value_01": "30", "description_value_02": "5.44", "description_value_03": "5",
    "description_value_04": "30", "description_value_05": "3.79", "description_value_06": "5",
    "description_value_07": "30", "description_value_08": "50.06", "description_value_09": "5",
}
MIRANDA_SIG_WAKE_UP = {
    "description_value_01": "32.99", "description_value_02": "10", "description_value_03": "30.1",
    "description_value_04": "10", "description_value_05": "23.7", "description_value_06": "10",
    "description_value_07": "1", "description_value_08": "85.42", "description_value_09": "1",
}
MIRANDA_SIG_POWERING_UP = {
    "description_value_01": "2", "description_value_02": "40.4", "description_value_03": "10",
    "description_value_04": "56.23", "description_value_05": "10",
}
MIRANDA = {
    "health_up": MIRANDA_SIG_HEALTH_UP,
    "wake_up": MIRANDA_SIG_WAKE_UP,
    "powering_up": MIRANDA_SIG_POWERING_UP,
}


def test_miranda_full_burst_squad_crit_damage_and_self_buffs():
    ctx = deck_ctx("miranda")
    reg = EffectRegistry()
    rules = {"miranda": build_miranda_rules(MIRANDA)}

    fire_trigger("full_burst_enter", rules, ctx, reg, time=0.0)
    assert round(reg.total_for("other_critical_damage_sources", ALLY, 0.0), 4) == 0.3299  # squad
    miranda = {"slug": "miranda", "element": "Iron"}
    assert round(reg.total_for("crit_rate", miranda, 0.0), 4) == 0.301  # self
    assert reg.total_for("crit_rate", ALLY, 0.0) == 0.0  # not squad
    assert round(reg.total_for("attack_damage_up", miranda, 0.0), 4) == 0.237  # self


def test_miranda_burst_buffs_only_the_top_two_highest_atk_allies():
    # Powering Up targets the 2 allies with the highest final ATK (except caster):
    # carry_a + carry_b, NOT the low-ATK support and NOT miranda herself.
    ctx = ranked_deck_ctx()
    reg = EffectRegistry()
    rules = {"miranda": build_miranda_rules(MIRANDA)}

    fire_trigger("own_burst_activate", rules, ctx, reg, time=0.0)
    a = {"slug": "carry_a", "element": "Fire"}
    b = {"slug": "carry_b", "element": "Fire"}
    support = {"slug": "support", "element": "Water"}
    miranda = {"slug": "miranda", "element": "Iron"}
    assert round(reg.total_for("atk_percent", a, 0.0), 4) == 0.404
    assert round(reg.total_for("atk_percent", b, 0.0), 4) == 0.404
    assert reg.total_for("atk_percent", support, 0.0) == 0.0  # lowest ATK excluded
    assert reg.total_for("atk_percent", miranda, 0.0) == 0.0  # caster excluded
    assert round(reg.total_for("other_critical_damage_sources", a, 0.0), 4) == 0.5623


def test_miranda_wake_up_grants_top1_crit_rate_for_one_round():
    # Wake Up's Crit Rate 85.42% targets the single highest-final-ATK ally
    # (carry_a) for 1 round (a bullet-count grant, its next shot).
    ctx = ranked_deck_ctx()
    reg = EffectRegistry()
    rules = {"miranda": build_miranda_rules(MIRANDA)}

    fire_trigger("full_burst_enter", rules, ctx, reg, time=0.0)
    grants = [g for g in reg.round_grants() if g.stat == "crit_rate"]
    assert len(grants) == 1
    assert grants[0].scope == "slugs:carry_a"
    assert round(grants[0].value, 4) == 0.8542
    assert grants[0].shots == 1


def test_miranda_health_up_self_atk_every_30_normal_attacks():
    rules = build_health_up_rules(MIRANDA["health_up"])
    # The two shared Hit Rate steps, then the Favorite Item's own self ATK step.
    assert len(rules) == 2
    threshold, mode, skill_rules = rules[-1]
    assert (threshold, mode) == (30, "every")

    reg = EffectRegistry()
    ctx = deck_ctx("miranda")
    for rule in skill_rules:
        rule.action(ctx, "miranda", 3.0, reg)
    miranda = {"slug": "miranda", "element": "Iron"}
    assert round(reg.total_for("atk_percent", miranda, 3.0), 4) == 0.5006  # self ATK
    assert reg.total_for("atk_percent", ALLY, 3.0) == 0.0  # self-only
    assert reg.total_for("atk_percent", miranda, 8.1) == 0.0  # 5s window expired


def _weapon_deck_ctx():
    """Miranda plus one SMG ally and one shotgun ally, so Health Up!'s
    submachine-gun step has something to include and something to exclude."""
    return SquadContext([
        SquadMember("miranda", burst_tier=1, element="Iron", weapon="SMG"),
        SquadMember("smg-ally", burst_tier=3, element="Fire", weapon="SMG"),
        SquadMember("sg-ally", burst_tier=2, element="Water", weapon="SG"),
    ])


@pytest.mark.parametrize("values", [MIRANDA_BASE_HEALTH_UP, MIRANDA_SIG_HEALTH_UP])
def test_miranda_health_up_hit_rate_reaches_the_squad_then_the_smgs(values):
    """Both bullets, on both builds: +5.44% for everyone and a further +3.79%
    for submachine guns only. Miranda carries one herself, so she collects
    both."""
    threshold, mode, skill_rules = build_health_up_hit_rate_rules(values)[0]
    assert (threshold, mode) == (30, "every")

    reg = EffectRegistry()
    ctx = _weapon_deck_ctx()
    for rule in skill_rules:
        rule.action(ctx, "miranda", 3.0, reg)
    miranda = {"slug": "miranda", "element": "Iron"}
    smg_ally = {"slug": "smg-ally", "element": "Fire"}
    sg_ally = {"slug": "sg-ally", "element": "Water"}
    assert round(reg.total_for("hit_rate", miranda, 3.0), 4) == 0.0923
    assert round(reg.total_for("hit_rate", smg_ally, 3.0), 4) == 0.0923
    assert round(reg.total_for("hit_rate", sg_ally, 3.0), 4) == 0.0544  # squad half only
    assert reg.total_for("hit_rate", miranda, 8.1) == 0.0               # 5s window


def test_miranda_health_up_hit_rate_refreshes_instead_of_stacking():
    """Neither bullet says "stacks up to", and 30 SMG rounds take ~1.5 sec
    against a 5 sec duration - so a stacking reading would pile up without
    bound. Firing the counter three times inside one window must read the same
    as firing it once."""
    threshold, mode, skill_rules = build_health_up_hit_rate_rules(MIRANDA_BASE_HEALTH_UP)[0]
    reg = EffectRegistry()
    ctx = _weapon_deck_ctx()
    for time in (1.5, 3.0, 4.5):
        for rule in skill_rules:
            rule.action(ctx, "miranda", time, reg)
    miranda = {"slug": "miranda", "element": "Iron"}
    assert round(reg.total_for("hit_rate", miranda, 4.5), 4) == 0.0923


# Module-level fixture aliases so the assembly verification harness
# (test_skill_value_assembly.py) can resolve each sub-skill fixture by name.
LITER_BOOST = LITER["liter_boost"]
DOUBLE_BOOST = LITER["double_boost"]
DROP_THE_BEAT = VOLUME["drop_the_beat"]
TURN_UP = VOLUME["turn_up"]
HEALTH_UP = MIRANDA["health_up"]
WAKE_UP = MIRANDA["wake_up"]
POWERING_UP = MIRANDA["powering_up"]


def test_miranda_base_grants_only_squad_crit_damage_on_full_burst():
    # Without the Favorite Item, Wake Up! is one bullet. The self Crit Rate and
    # Attack Damage the baked encoding used to credit every user do not exist.
    ctx = ranked_deck_ctx()
    reg = EffectRegistry()
    rules = {"miranda": build_miranda_base_rules(MIRANDA_BASE)}

    fire_trigger("full_burst_enter", rules, ctx, reg, time=0.0)

    miranda = {"slug": "miranda", "element": "Iron"}
    assert round(reg.total_for("other_critical_damage_sources", miranda, 0.0), 4) == 0.3299
    assert reg.total_for("crit_rate", miranda, 0.0) == 0.0
    assert reg.total_for("attack_damage_up", miranda, 0.0) == 0.0


def test_miranda_base_burst_buffs_only_the_single_highest_atk_ally():
    # Slot 01 is the ally count: 1 on the base build, 2 with the Favorite Item.
    ctx = ranked_deck_ctx()
    reg = EffectRegistry()
    rules = {"miranda": build_miranda_base_rules(MIRANDA_BASE)}

    fire_trigger("own_burst_activate", rules, ctx, reg, time=0.0)

    carry_a = {"slug": "carry_a", "element": "Fire"}
    carry_b = {"slug": "carry_b", "element": "Fire"}
    assert round(reg.total_for("atk_percent", carry_a, 0.0), 4) == 0.404
    assert reg.total_for("atk_percent", carry_b, 0.0) == 0.0  # second carry misses out
