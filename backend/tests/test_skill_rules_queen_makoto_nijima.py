"""Queen (Makoto Nijima) - a Burst-3 Fire SG attacker from the Persona collab.

Two things decide almost everything she does: whether the boss is Wind Code
(her 1 More, and every bullet hanging off it), and whether Yukiko Amagi is in
the deck (Baton Pass has no audience without her, and Follow Up no source).
"""
import pytest

from app.effects import EffectRegistry
from app.skill_rules.queen_makoto_nijima import (
    build_queen_makoto_nijima_rules,
    mafreidyne_burst_percent,
)
from app.squad_engine import SquadContext, SquadMember, fire_trigger

# ShiftyPad native slots (data/shiftypad/queen-makoto-nijima.json, level 10).
PERSONA_JOHANNA = {
    "description_value_01": "13.59", "description_value_02": "14.78",
    "description_value_03": "548.99", "description_value_04": "548.99",
    "description_value_05": "50.28", "description_value_06": "15",
}
FIST_OF_JUSTICE = {
    "description_value_01": "25.56", "description_value_02": "17.95",
    "description_value_03": "90.01", "description_value_04": "10",
    "description_value_05": "3", "description_value_06": "35.2",
    "description_value_07": "3", "description_value_08": "0",
    "description_value_09": "30",
}
MAFREIDYNE = {
    "description_value_01": "1421.69", "description_value_02": "30.27",
    "description_value_03": "10",
}
CASTER_ATK = 80000.0
QUEEN = {
    "persona_johanna": PERSONA_JOHANNA,
    "fist_of_justice": FIST_OF_JUSTICE,
    "mafreidyne": MAFREIDYNE,
    "caster_atk": CASTER_ATK,
}

SLUG = "queen-makoto-nijima"
SELF = {"slug": SLUG, "element": "Fire"}
YUKIKO = {"slug": "yukiko-amagi", "element": "Fire"}
PLAIN_B3 = {"slug": "ally-b3", "element": "Iron"}

BATON_PASS_STACK = CASTER_ATK * 0.352


def _ctx(boss_element="Wind", with_yukiko=True):
    members = [SquadMember(SLUG, burst_tier=3, element="Fire", weapon="SG")]
    if with_yukiko:
        members.append(SquadMember("yukiko-amagi", burst_tier=3, element="Fire", weapon="MG"))
    members += [
        SquadMember("ally-b3", burst_tier=3, element="Iron", weapon="AR"),
        SquadMember("ally-b1", burst_tier=1, element="Iron", weapon="AR"),
    ]
    return SquadContext(members, boss_element=boss_element)


def _rules():
    return {SLUG: build_queen_makoto_nijima_rules(QUEEN)}


def _nuke_pulses(reg):
    return [(p.value, p.damage_type) for p in reg.drain_pulses("instant_damage_percent")]


def test_burst_percent_is_the_distributed_nuke():
    assert mafreidyne_burst_percent(QUEEN) == 1421.69


def test_persona_johanna_arms_her_continuous_buffs_at_battle_start():
    reg = EffectRegistry()
    fire_trigger("battle_start", _rules(), _ctx(), reg, 0.0)
    # Nuke Boost + Fist of Justice!'s opening Attack Damage, both continuous.
    assert reg.total_for("other_elemental_bonus", SELF, 0.0) == pytest.approx(0.1359)
    assert reg.total_for("other_elemental_bonus", SELF, 500.0) == pytest.approx(0.1359)
    assert reg.total_for("attack_damage_up", SELF, 500.0) == pytest.approx(0.30)
    # ...and the 15-sec ATK buff that re-arms every Full Burst end.
    assert reg.total_for("atk_percent", SELF, 14.9) == pytest.approx(0.5028)
    assert reg.total_for("atk_percent", SELF, 15.1) == 0.0


def test_her_continuous_buffs_stay_on_herself():
    reg = EffectRegistry()
    fire_trigger("battle_start", _rules(), _ctx(), reg, 0.0)
    for stat in ("other_elemental_bonus", "attack_damage_up", "atk_percent"):
        assert reg.total_for(stat, YUKIKO, 1.0) == 0.0


def test_the_atk_buff_re_arms_when_full_burst_ends():
    reg = EffectRegistry()
    fire_trigger("full_burst_end", _rules(), _ctx(), reg, 40.0)
    assert reg.total_for("atk_percent", SELF, 54.9) == pytest.approx(0.5028)
    assert reg.total_for("atk_percent", SELF, 55.1) == 0.0


def test_her_burst_grants_one_more_against_a_wind_boss():
    reg = EffectRegistry()
    fire_trigger("own_burst_activate", _rules(), _ctx(), reg, 20.0)
    assert reg.total_for("atk_percent", SELF, 29.9) == pytest.approx(0.3027)
    assert reg.total_for("atk_percent", SELF, 30.1) == 0.0


def test_one_more_does_not_happen_without_elemental_advantage():
    reg = EffectRegistry()
    fire_trigger("own_burst_activate", _rules(), _ctx(boss_element="Iron"), reg, 20.0)
    assert reg.total_for("atk_percent", SELF, 21.0) == 0.0
    assert _nuke_pulses(reg) == []


def test_one_more_fires_her_distributed_nuke():
    reg = EffectRegistry()
    fire_trigger("own_burst_activate", _rules(), _ctx(), reg, 20.0)
    assert _nuke_pulses(reg) == [(548.99, "distributed")]


def test_yukikos_burst_fires_the_follow_up_nuke():
    """Follow Up is Yukiko's grant, so the bullet answers HER burst - the one
    bullet in the pair that needs the cross-unit trigger."""
    ctx = _ctx()
    ctx.last_burst_slug = "yukiko-amagi"
    reg = EffectRegistry()
    fire_trigger("ally_burst_activate", _rules(), ctx, reg, 60.0)
    assert _nuke_pulses(reg) == [(548.99, "distributed")]


def test_another_burst_3_allys_burst_does_not_fire_the_follow_up_nuke():
    ctx = _ctx()
    ctx.last_burst_slug = "ally-b3"
    reg = EffectRegistry()
    fire_trigger("ally_burst_activate", _rules(), ctx, reg, 60.0)
    assert _nuke_pulses(reg) == []


def test_the_follow_up_nuke_needs_elemental_advantage_too():
    """Yukiko passes Follow Up when HER 1 More takes effect, and 1 More needs a
    Wind Code enemy - so against anything else the bullet never arms."""
    ctx = _ctx(boss_element="Iron")
    ctx.last_burst_slug = "yukiko-amagi"
    reg = EffectRegistry()
    fire_trigger("ally_burst_activate", _rules(), ctx, reg, 60.0)
    assert _nuke_pulses(reg) == []


def test_entering_burst_stage_3_grants_distributed_damage():
    """"Activates when entering Burst Stage 3" is about the STAGE, so it fires
    in the cycles another Burst 3 takes the slot as well as her own."""
    ctx = _ctx()
    ctx.last_burst_slug = "ally-b3"
    reg = EffectRegistry()
    fire_trigger("ally_burst_activate", _rules(), ctx, reg, 60.0)
    assert reg.total_for("distributed_damage_up", SELF, 69.9) == pytest.approx(0.9001)
    assert reg.total_for("distributed_damage_up", SELF, 70.1) == 0.0
    assert reg.total_for("distributed_damage_up", YUKIKO, 60.0) == 0.0


def test_a_burst_1_allys_burst_does_not_grant_distributed_damage():
    ctx = _ctx()
    ctx.last_burst_slug = "ally-b1"
    reg = EffectRegistry()
    fire_trigger("ally_burst_activate", _rules(), ctx, reg, 60.0)
    assert reg.total_for("distributed_damage_up", SELF, 60.0) == 0.0


def test_nuke_amp_ends_at_full_burst_end_and_leaves_nuke_boost_standing():
    """Her two Elemental Advantage bullets sit on one stat: Nuke Boost "cannot
    be removed" while Nuke Amp names Full Burst end as its deactivation. Closing
    both would delete the permanent one for the rest of the fight."""
    rules = _rules()
    reg = EffectRegistry()
    fire_trigger("battle_start", rules, _ctx(), reg, 0.0)
    fire_trigger("own_burst_activate", rules, _ctx(), reg, 20.0)
    assert reg.total_for("other_elemental_bonus", SELF, 25.0) == pytest.approx(0.3915)

    fire_trigger("full_burst_end", rules, _ctx(), reg, 30.0)
    assert reg.total_for("other_elemental_bonus", SELF, 25.0) == pytest.approx(0.3915)
    assert reg.total_for("other_elemental_bonus", SELF, 30.0) == pytest.approx(0.1359)
    assert reg.total_for("other_elemental_bonus", SELF, 500.0) == pytest.approx(0.1359)


def test_baton_pass_reaches_yukiko_and_nobody_else():
    """"all standard Burst 3 allies (except the skill user) in the Persona
    state" - a plain Burst 3 ally is not in it, and neither is the caster."""
    reg = EffectRegistry()
    fire_trigger("own_burst_activate", _rules(), _ctx(), reg, 20.0)
    assert reg.total_for("flat_atk", YUKIKO, 500.0) == pytest.approx(BATON_PASS_STACK)
    assert reg.total_for("flat_atk", PLAIN_B3, 500.0) == 0.0
    assert reg.total_for("flat_atk", SELF, 500.0) == 0.0


def test_baton_pass_has_no_audience_without_a_persona_ally():
    reg = EffectRegistry()
    fire_trigger("own_burst_activate", _rules(), _ctx(with_yukiko=False), reg, 20.0)
    assert reg.total_for("flat_atk", PLAIN_B3, 500.0) == 0.0


def test_baton_pass_stacks_per_burst_and_stops_at_three():
    ctx = _ctx()
    rules = _rules()
    reg = EffectRegistry()
    for cycle, time in enumerate((20.0, 60.0, 100.0, 140.0, 180.0), start=1):
        fire_trigger("own_burst_activate", rules, ctx, reg, time)
        expected = min(cycle, 3) * BATON_PASS_STACK
        assert reg.total_for("flat_atk", YUKIKO, time) == pytest.approx(expected)


def test_baton_pass_needs_elemental_advantage():
    reg = EffectRegistry()
    fire_trigger("own_burst_activate", _rules(), _ctx(boss_element="Iron"), reg, 20.0)
    assert reg.total_for("flat_atk", YUKIKO, 500.0) == 0.0
