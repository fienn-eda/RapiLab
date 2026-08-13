"""Yukiko Amagi - a Burst-3 Fire MG attacker from the Persona collab, and the
source of the Follow Up that arms Queen (Makoto Nijima)'s second nuke."""
import pytest

from app.effects import EffectRegistry
from app.skill_rules._helpers import HEAL_PROVIDER_SLUGS
from app.skill_rules.yukiko_amagi import (
    build_yukiko_amagi_rules,
    maragidyne_burst_percent,
)
from app.squad_engine import SquadContext, SquadMember, fire_trigger

# ShiftyPad native slots (data/shiftypad/yukiko-amagi.json, level 10).
PERSONA_KONOHANA_SAKUYA = {
    "description_value_01": "3", "description_value_02": "5.7",
    "description_value_03": "400.31", "description_value_04": "65.37",
    "description_value_05": "15",
}
SCARLET_FLOWER = {
    "description_value_01": "3", "description_value_02": "5.7",
    "description_value_03": "90.01", "description_value_04": "17.95",
    "description_value_05": "48.15", "description_value_06": "10",
    "description_value_07": "3", "description_value_08": "80.25",
    "description_value_09": "25", "description_value_10": "55.31",
}
MARAGIDYNE = {
    "description_value_01": "1258.79", "description_value_02": "45.33",
    "description_value_03": "10",
}
CASTER_ATK = 70000.0
YUKIKO_VALUES = {
    "persona_konohana_sakuya": PERSONA_KONOHANA_SAKUYA,
    "scarlet_flower": SCARLET_FLOWER,
    "maragidyne": MARAGIDYNE,
    "caster_atk": CASTER_ATK,
}

SLUG = "yukiko-amagi"
SELF = {"slug": SLUG, "element": "Fire"}
QUEEN = {"slug": "queen-makoto-nijima", "element": "Fire"}
PLAIN_B3 = {"slug": "ally-b3", "element": "Iron"}

FOLLOW_UP_ATK = CASTER_ATK * 0.8025


def _ctx(boss_element="Wind", with_queen=True):
    members = [SquadMember(SLUG, burst_tier=3, element="Fire", weapon="MG")]
    if with_queen:
        members.append(
            SquadMember("queen-makoto-nijima", burst_tier=3, element="Fire", weapon="SG"))
    members += [
        SquadMember("ally-b3", burst_tier=3, element="Iron", weapon="AR"),
        SquadMember("ally-b1", burst_tier=1, element="Iron", weapon="AR"),
    ]
    return SquadContext(members, boss_element=boss_element)


def _rules():
    return {SLUG: build_yukiko_amagi_rules(YUKIKO_VALUES)}


def _nuke_pulses(reg):
    return [(p.value, p.damage_type) for p in reg.drain_pulses("instant_damage_percent")]


def test_burst_percent_is_the_distributed_nuke():
    assert maragidyne_burst_percent(YUKIKO_VALUES) == 1258.79


def test_she_is_registered_as_a_heal_provider():
    """Media and Mediarama both restore every ally's HP. The amount is not a
    damage quantity, but the OCCURRENCE arms Crown's Royal Attire."""
    assert SLUG in HEAL_PROVIDER_SLUGS


def test_scarlet_flower_arms_her_attack_damage_at_battle_start():
    reg = EffectRegistry()
    fire_trigger("battle_start", _rules(), _ctx(), reg, 0.0)
    assert reg.total_for("attack_damage_up", SELF, 500.0) == pytest.approx(0.5531)
    assert reg.total_for("attack_damage_up", QUEEN, 500.0) == 0.0


def test_her_timed_atk_buff_arms_at_battle_start_and_re_arms_at_full_burst_end():
    reg = EffectRegistry()
    fire_trigger("battle_start", _rules(), _ctx(), reg, 0.0)
    assert reg.total_for("atk_percent", SELF, 14.9) == pytest.approx(0.6537)
    assert reg.total_for("atk_percent", SELF, 15.1) == 0.0

    fire_trigger("full_burst_end", _rules(), _ctx(), reg, 40.0)
    assert reg.total_for("atk_percent", SELF, 54.9) == pytest.approx(0.6537)
    assert reg.total_for("atk_percent", SELF, 55.1) == 0.0


def test_her_burst_grants_one_more_against_a_wind_boss():
    reg = EffectRegistry()
    fire_trigger("own_burst_activate", _rules(), _ctx(), reg, 20.0)
    assert reg.total_for("atk_percent", SELF, 29.9) == pytest.approx(0.4533)
    assert reg.total_for("atk_percent", SELF, 30.1) == 0.0
    assert _nuke_pulses(reg) == [(400.31, "distributed")]


def test_one_more_does_not_happen_without_elemental_advantage():
    reg = EffectRegistry()
    fire_trigger("own_burst_activate", _rules(), _ctx(boss_element="Iron"), reg, 20.0)
    assert reg.total_for("atk_percent", SELF, 21.0) == 0.0
    assert _nuke_pulses(reg) == []


def test_fire_amp_runs_from_her_burst_to_full_burst_end():
    rules = _rules()
    reg = EffectRegistry()
    fire_trigger("own_burst_activate", rules, _ctx(), reg, 20.0)
    assert reg.total_for("distributed_damage_up", SELF, 25.0) == pytest.approx(0.9001)

    fire_trigger("full_burst_end", rules, _ctx(), reg, 30.0)
    assert reg.total_for("distributed_damage_up", SELF, 25.0) == pytest.approx(0.9001)
    assert reg.total_for("distributed_damage_up", SELF, 30.0) == 0.0
    assert reg.total_for("distributed_damage_up", QUEEN, 25.0) == 0.0


def test_entering_burst_stage_3_grants_elemental_advantage_damage():
    ctx = _ctx()
    ctx.last_burst_slug = "ally-b3"
    reg = EffectRegistry()
    fire_trigger("ally_burst_activate", _rules(), ctx, reg, 60.0)
    assert reg.total_for("other_elemental_bonus", SELF, 69.9) == pytest.approx(0.4815)
    assert reg.total_for("other_elemental_bonus", SELF, 70.1) == 0.0


def test_a_burst_1_allys_burst_does_not_grant_it():
    ctx = _ctx()
    ctx.last_burst_slug = "ally-b1"
    reg = EffectRegistry()
    fire_trigger("ally_burst_activate", _rules(), ctx, reg, 60.0)
    assert reg.total_for("other_elemental_bonus", SELF, 60.0) == 0.0


def test_follow_up_reaches_queen_and_nobody_else():
    reg = EffectRegistry()
    fire_trigger("own_burst_activate", _rules(), _ctx(), reg, 20.0)
    assert reg.total_for("flat_atk", QUEEN, 44.9) == pytest.approx(FOLLOW_UP_ATK)
    assert reg.total_for("flat_atk", QUEEN, 45.1) == 0.0  # 25 sec
    assert reg.total_for("flat_atk", PLAIN_B3, 21.0) == 0.0
    assert reg.total_for("flat_atk", SELF, 21.0) == 0.0


def test_follow_up_has_no_audience_without_a_persona_ally():
    reg = EffectRegistry()
    fire_trigger("own_burst_activate", _rules(), _ctx(with_queen=False), reg, 20.0)
    assert reg.total_for("flat_atk", PLAIN_B3, 21.0) == 0.0


def test_follow_up_needs_elemental_advantage():
    reg = EffectRegistry()
    fire_trigger("own_burst_activate", _rules(), _ctx(boss_element="Iron"), reg, 20.0)
    assert reg.total_for("flat_atk", QUEEN, 21.0) == 0.0
