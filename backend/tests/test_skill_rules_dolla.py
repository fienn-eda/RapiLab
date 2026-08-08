"""Dolla - a Burst-2 Wind SR supporter whose whole kit is escalating squad buffs
plus a cooldowned ATK skill."""
from app.effects import EffectRegistry
from app.skill_rules.dolla import (
    ENTREPRENEURSHIP_COOLDOWN,
    build_dolla_rules,
    build_entrepreneurship_periodic_rules,
    rnd_shot_burst_percent,
)
from app.squad_engine import SquadContext, SquadMember, fire_trigger

# ShiftyPad native slots (data/shiftypad/dolla.json, level 10).
ENTREPRENEURSHIP = {"description_value_01": "16.16", "description_value_02": "5"}
RISK_SHARING = {
    "description_value_01": "1.82", "description_value_02": "2.2",
    "description_value_03": "2.6", "description_value_04": "7.72",
    "description_value_05": "5", "description_value_06": "4.21",
    "description_value_07": "5", "description_value_08": "13.22",
    "description_value_09": "5",
}
RND_SHOT = {"description_value_01": "1", "description_value_02": "734.69"}
DOLLA = {
    "entrepreneurship": ENTREPRENEURSHIP,
    "risk_sharing": RISK_SHARING,
    "rnd_shot": RND_SHOT,
}

SELF = {"slug": "dolla", "element": "Wind"}
ALLY = {"slug": "ally", "element": "Fire"}


def _ctx():
    return SquadContext([
        SquadMember("dolla", burst_tier=2, element="Wind", weapon="SR"),
        SquadMember("ally", burst_tier=3, element="Fire", weapon="AR"),
    ])


def test_burst_percent_is_the_highest_def_target_nuke():
    assert rnd_shot_burst_percent(DOLLA) == 734.69


def test_entrepreneurship_is_a_squad_atk_buff_on_its_own_cooldown():
    """A Skill 1 with a cooldown and no trigger phrase fires at t=cooldown and
    repeats - it does NOT apply at battle start."""
    assert ENTREPRENEURSHIP_COOLDOWN == 10.0
    reg = EffectRegistry()
    fire_trigger(
        "periodic",
        {"dolla": build_entrepreneurship_periodic_rules(ENTREPRENEURSHIP)},
        _ctx(), reg, 10.0,
    )
    assert round(reg.total_for("atk_percent", SELF, 10.0), 4) == 0.1616
    assert round(reg.total_for("atk_percent", ALLY, 14.9), 4) == 0.1616
    assert reg.total_for("atk_percent", ALLY, 15.1) == 0.0  # 5 sec


def test_risk_sharing_cdr_tiers_accumulate_over_full_burst_entries():
    """"Each subsequent effect triggers all effects before it" - by the third
    Full Burst the squad gets 1.82 + 2.2 + 2.6 sec, and stays there."""
    reg = EffectRegistry()
    ctx = _ctx()
    rules = {"dolla": build_dolla_rules(DOLLA)}

    fire_trigger("full_burst_enter", rules, ctx, reg, 12.0)
    assert round(sum(p.value for p in reg.drain_pulses("burst_cooldown_reduction_sec")), 4) == 1.82
    fire_trigger("full_burst_enter", rules, ctx, reg, 24.0)
    assert round(sum(p.value for p in reg.drain_pulses("burst_cooldown_reduction_sec")), 4) == 4.02
    fire_trigger("full_burst_enter", rules, ctx, reg, 36.0)
    assert round(sum(p.value for p in reg.drain_pulses("burst_cooldown_reduction_sec")), 4) == 6.62
    fire_trigger("full_burst_enter", rules, ctx, reg, 48.0)
    assert round(sum(p.value for p in reg.drain_pulses("burst_cooldown_reduction_sec")), 4) == 6.62


def test_the_cdr_pulse_is_squad_scoped():
    """"Affects all allies" - a self-scoped pulse would only speed up her own
    rotation, which is not what the text says."""
    reg = EffectRegistry()
    fire_trigger("full_burst_enter", {"dolla": build_dolla_rules(DOLLA)}, _ctx(), reg, 12.0)
    assert [p.scope for p in reg.drain_pulses("burst_cooldown_reduction_sec")] == ["squad"]


def test_risk_sharing_burst_tiers_unlock_one_stat_per_activation():
    reg = EffectRegistry()
    ctx = _ctx()
    rules = {"dolla": build_dolla_rules(DOLLA)}

    fire_trigger("own_burst_activate", rules, ctx, reg, 10.0)
    assert round(reg.total_for("atk_percent", ALLY, 10.0), 4) == 0.0772
    assert reg.total_for("crit_rate", ALLY, 10.0) == 0.0
    assert reg.total_for("other_critical_damage_sources", ALLY, 10.0) == 0.0

    fire_trigger("own_burst_activate", rules, ctx, reg, 30.0)
    assert round(reg.total_for("atk_percent", ALLY, 30.0), 4) == 0.0772
    assert round(reg.total_for("crit_rate", ALLY, 30.0), 4) == 0.0421
    assert reg.total_for("other_critical_damage_sources", ALLY, 30.0) == 0.0

    fire_trigger("own_burst_activate", rules, ctx, reg, 50.0)
    assert round(reg.total_for("atk_percent", ALLY, 50.0), 4) == 0.0772
    assert round(reg.total_for("crit_rate", ALLY, 50.0), 4) == 0.0421
    assert round(reg.total_for("other_critical_damage_sources", ALLY, 50.0), 4) == 0.1322


def test_burst_tier_buffs_last_five_seconds_and_reach_the_squad():
    reg = EffectRegistry()
    fire_trigger("own_burst_activate", {"dolla": build_dolla_rules(DOLLA)}, _ctx(), reg, 10.0)
    assert round(reg.total_for("atk_percent", SELF, 14.9), 4) == 0.0772
    assert reg.total_for("atk_percent", SELF, 15.1) == 0.0
