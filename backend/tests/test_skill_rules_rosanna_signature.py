"""Rosanna's Favorite Item build - adds a permanent elemental buff, a shot-counted
Frenzy source her base build can never reach, and a Water-Code damage-taken debuff."""
from app.attack_rate import generate_shot_times
from app.effects import EffectRegistry
from app.skill_rules.registry import get_resource_specs
from app.skill_rules.rosanna_signature import (
    build_frenzy_resources,
    build_rosanna_signature_per_shot_rules,
    build_rosanna_signature_rules,
    vendetta_signature_burst_percent,
)
from app.squad_engine import SquadContext, SquadMember, fire_trigger

# lootandwaifus dollskills, level 10, every number in the text numbered left-to-right.
ON_THE_LAM = {
    "description_value_01": "120", "description_value_02": "10",
    "description_value_03": "19.34", "description_value_04": "3",
    "description_value_05": "10", "description_value_06": "2",
    "description_value_07": "5", "description_value_08": "20",
}
CAPO_DEI_CAPI = {
    "description_value_01": "5", "description_value_02": "22.61",
    "description_value_03": "10", "description_value_04": "30",
    "description_value_05": "36.54", "description_value_06": "1",
    "description_value_07": "400", "description_value_08": "500",
    "description_value_09": "22.61", "description_value_10": "10",
    "description_value_11": "30",
}
VENDETTA = {
    "description_value_01": "2", "description_value_02": "1310.4",
    "description_value_03": "561.6", "description_value_04": "29",
    "description_value_05": "30",
}
ROSANNA_SIG = {"on_the_lam": ON_THE_LAM, "capo_dei_capi": CAPO_DEI_CAPI, "vendetta": VENDETTA}

SELF = {"slug": "rosanna-signature", "element": "Electric"}
ALLY = {"slug": "ally", "element": "Fire"}


def _ctx(boss_element=None):
    return SquadContext([
        SquadMember("rosanna-signature", burst_tier=1, element="Electric", weapon="MG"),
        SquadMember("ally", burst_tier=3, element="Fire", weapon="AR"),
    ], boss_element=boss_element)


def _fire(trigger, boss_element=None, time=0.0):
    reg = EffectRegistry()
    fire_trigger(trigger, {"rosanna-signature": build_rosanna_signature_rules(ROSANNA_SIG)},
                 _ctx(boss_element), reg, time)
    return reg


def test_burst_percent_matches_the_base_build():
    assert vendetta_signature_burst_percent(ROSANNA_SIG) == 1310.4 + 561.6


def test_stage_target_elemental_buff_is_permanent_and_self_only():
    # "when the stage target appears" - a raid always has an enemy, so it is on
    # from t=0 (the documented always-on-in-raid convention).
    reg = _fire("battle_start")
    assert round(reg.total_for("other_elemental_bonus", SELF, 0.0), 4) == 0.20
    assert round(reg.total_for("other_elemental_bonus", SELF, 179.0), 4) == 0.20
    assert reg.total_for("other_elemental_bonus", ALLY, 0.0) == 0.0


def test_water_code_damage_taken_debuff_is_squad_scoped_and_gated():
    reg = _fire("own_burst_activate", boss_element="Water", time=20.0)
    assert round(reg.total_for("damage_taken_up", SELF, 20.0), 4) == 0.29
    assert round(reg.total_for("damage_taken_up", ALLY, 20.0), 4) == 0.29  # all attackers share it
    assert reg.total_for("damage_taken_up", SELF, 50.1) == 0.0  # 30s
    assert _fire("own_burst_activate", boss_element="Fire", time=20.0).total_for(
        "damage_taken_up", SELF, 20.0) == 0.0


def test_the_crit_counter_is_the_only_per_shot_rule_left():
    """Frenzy moved to a resource when its cap was found to bind; the crit
    bullet names no stack count, so it stays a refreshing per-shot rule."""
    rules = build_rosanna_signature_per_shot_rules(ROSANNA_SIG)
    assert [every for every, _mode, _rules in rules] == [120]
    assert {mode for _every, mode, _rules in rules} == {"every"}

    (_every, _mode, shot_rules), = rules
    reg = EffectRegistry()
    fire_trigger("per_shot", {"rosanna-signature": shot_rules}, _ctx(), reg, 5.0)
    assert round(reg.total_for("crit_rate", SELF, 5.0), 4) == 0.1934


def test_frenzy_is_a_ten_stack_self_atk_counter_every_500_shots():
    (spec,) = build_frenzy_resources(ROSANNA_SIG)
    assert spec.name == "frenzy"
    assert spec.fill == ("per_shot_every", 500)
    assert spec.cap == 10
    (buff,) = spec.buffs
    assert buff.stat == "atk_percent"
    assert buff.scope == "self"
    assert round(buff.value_fn(1), 4) == 0.2261
    assert round(buff.value_fn(10), 4) == 2.261


def test_frenzy_reaches_its_cap_because_her_cadence_outruns_the_timer():
    """"Stacks up to 10 times and lasts for 30 sec" is ONE timer every new
    stack restarts (the Raven ruling; Fienn confirmed the cap binds in game,
    2026-08-17), so the count climbs while consecutive fills stay inside 30
    sec. Her MG puts 500 shots ~15 sec apart, nowhere near it, so the chain
    cannot break and a permanent accumulation is the faithful model - the same
    reasoning Leona's Roar is encoded on. Read as 10 independent timers, she
    sat at the 2-3 instances that happen to overlap."""
    (spec,) = build_frenzy_resources(ROSANNA_SIG)
    assert spec.buffs[0].lifetime is None

    shots = generate_shot_times("MG", 300, 1.67, 0.0, 180.0)
    fills = shots[499::500]
    gaps = [b - a for a, b in zip(fills, fills[1:])]
    stated_duration = float(CAPO_DEI_CAPI["description_value_11"])
    assert max(gaps) < stated_duration, f"a gap of {max(gaps):.2f}s would drop the count"


def test_the_registry_threads_frenzy_through_as_a_resource():
    """A builder nobody calls is silently inert - and Frenzy must not ALSO
    remain a per-shot rule, or every stack would land twice."""
    specs = get_resource_specs("rosanna-signature", ROSANNA_SIG)
    assert specs is not None and len(specs) == 1
    assert specs[0].name == "frenzy"
    assert all(every != 500
               for every, _mode, _rules in build_rosanna_signature_per_shot_rules(ROSANNA_SIG))
