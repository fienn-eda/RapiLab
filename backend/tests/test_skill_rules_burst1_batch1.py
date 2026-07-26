"""Tests for the first batch of Burst-1 supporters: Liter, Volume, Miranda.
Values are the real max-level (dollskill for Miranda) figures from dotgg.
"""
from app.effects import EffectRegistry
from app.skill_rules.liter import build_liter_rules
from app.skill_rules.miranda import (
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


def test_liter_full_burst_cdr_and_burst_squad_buffs():
    ctx = deck_ctx("liter")
    reg = EffectRegistry()
    rules = {"liter": build_liter_rules(LITER)}

    fire_trigger("full_burst_enter", rules, ctx, reg, time=2.0)
    assert reg.drain_pulses("burst_cooldown_reduction_sec")[0].value == 3.17

    fire_trigger("own_burst_activate", rules, ctx, reg, time=2.0)
    assert round(reg.total_for("atk_percent", ALLY, 2.0), 4) == round(0.1442 + 0.66, 4)
    assert round(reg.total_for("max_ammo_percent", ALLY, 2.0), 4) == 0.4517
    assert round(reg.total_for("other_critical_damage_sources", ALLY, 2.0), 4) == 0.1246


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

    # Escalates to the tier unlocked so far. Whether a later tier REPLACES the
    # earlier ones or ADDS to them is undetermined by the measurement (they
    # agree at activation 1) - see volume.CDR_TIERS_ARE_CUMULATIVE.
    for want in (2.34, 2.7, 3.17, 3.17):
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
    assert len(rules) == 1
    threshold, mode, skill_rules = rules[0]
    assert (threshold, mode) == (30, "every")

    reg = EffectRegistry()
    ctx = deck_ctx("miranda")
    for rule in skill_rules:
        rule.action(ctx, "miranda", 3.0, reg)
    miranda = {"slug": "miranda", "element": "Iron"}
    assert round(reg.total_for("atk_percent", miranda, 3.0), 4) == 0.5006  # self ATK
    assert reg.total_for("atk_percent", ALLY, 3.0) == 0.0  # self-only
    assert reg.total_for("atk_percent", miranda, 8.1) == 0.0  # 5s window expired


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
