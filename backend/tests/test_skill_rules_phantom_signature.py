"""Phantom's Favorite Item build - the extra Thief's Dagger source unlocks the
whole Thief's Vision chain her base build can never reach."""
from app.effects import EffectRegistry
from app.skill_rules.phantom_signature import (
    VISION_PROC_SHOTS,
    build_phantom_signature_per_shot_rules,
    build_phantom_signature_rules,
    secret_trick_signature_burst_percent,
)
from app.squad_engine import SquadContext, SquadMember, fire_trigger

# lootandwaifus dollskills, level 10, every number numbered left-to-right.
CALLING_CARD = {
    "description_value_01": "32.19", "description_value_02": "5",
    "description_value_03": "25.75", "description_value_04": "3",
    "description_value_05": "5", "description_value_06": "30",
    "description_value_07": "25.75", "description_value_08": "3",
    "description_value_09": "5", "description_value_10": "75.17",
    "description_value_11": "1",
}
THIEFS_VISION = {
    "description_value_01": "84.33", "description_value_02": "12.86",
    "description_value_03": "3", "description_value_04": "250",
    "description_value_05": "10", "description_value_06": "85.12",
    "description_value_07": "5", "description_value_08": "31.92",
    "description_value_09": "10",
}
SECRET_TRICK = {
    "description_value_01": "1457.28", "description_value_02": "18",
    "description_value_03": "30", "description_value_04": "50",
    "description_value_05": "10",
}
PHANTOM_SIG = {
    "calling_card": CALLING_CARD,
    "thiefs_vision": THIEFS_VISION,
    "secret_trick": SECRET_TRICK,
}

SELF = {"slug": "phantom-signature", "element": "Water"}
ALLY = {"slug": "ally", "element": "Fire"}


def _ctx(boss_element=None):
    return SquadContext([
        SquadMember("phantom-signature", burst_tier=3, element="Water", weapon="AR"),
        SquadMember("ally", burst_tier=1, element="Fire", weapon="MG"),
    ], boss_element=boss_element)


def _fire(trigger, boss_element=None, time=0.0):
    reg = EffectRegistry()
    fire_trigger(trigger, {"phantom-signature": build_phantom_signature_rules(PHANTOM_SIG)},
                 _ctx(boss_element), reg, time)
    return reg


def test_burst_percent_matches_the_base_build():
    assert secret_trick_signature_burst_percent(PHANTOM_SIG) == 1457.28


def test_burst_grants_self_max_ammo_and_a_fire_gated_damage_taken_debuff():
    reg = _fire("own_burst_activate", boss_element="Fire", time=20.0)
    assert round(reg.total_for("max_ammo_percent", SELF, 20.0), 4) == 0.50
    assert reg.total_for("max_ammo_percent", ALLY, 20.0) == 0.0
    assert round(reg.total_for("damage_taken_up", ALLY, 20.0), 4) == 0.18
    assert reg.total_for("damage_taken_up", SELF, 50.1) == 0.0  # 30s

    off_element = _fire("own_burst_activate", boss_element="Water", time=20.0)
    assert off_element.total_for("damage_taken_up", SELF, 20.0) == 0.0
    assert round(off_element.total_for("max_ammo_percent", SELF, 20.0), 4) == 0.50


def test_three_shot_counters_including_the_vision_proc():
    rules = build_phantom_signature_per_shot_rules(PHANTOM_SIG)
    assert sorted(every for every, _mode, _rules in rules) == [1, 10, VISION_PROC_SHOTS]


def test_vision_proc_emits_both_nukes_with_the_right_typing():
    rules = build_phantom_signature_per_shot_rules(PHANTOM_SIG)
    vision = next(r for every, _m, r in rules if every == VISION_PROC_SHOTS)
    reg = EffectRegistry()
    fire_trigger("per_shot", {"phantom-signature": vision}, _ctx(), reg, 5.0)

    pulses = reg.drain_pulses("instant_damage_percent")
    by_percent = {p.value: p for p in pulses}
    assert sorted(by_percent) == [84.33, 250.0]
    # "as additional damage" -> opted into the Full Burst Bonus check.
    assert by_percent[84.33].full_burst_bonus_eligible is True
    # "as Distributed Damage" -> typed so her Distributed Damage buffs apply.
    assert by_percent[250.0].damage_type == "distributed"
    assert by_percent[250.0].full_burst_bonus_eligible is False


def test_vision_proc_also_stacks_self_distributed_damage():
    rules = build_phantom_signature_per_shot_rules(PHANTOM_SIG)
    vision = next(r for every, _m, r in rules if every == VISION_PROC_SHOTS)
    reg = EffectRegistry()
    ctx = _ctx()
    fire_trigger("per_shot", {"phantom-signature": vision}, ctx, reg, 5.0)
    assert round(reg.total_for("distributed_damage_up", SELF, 5.0), 4) == 0.1286
    # A second proc inside the grant's lifetime stacks, as the skill's "stacks
    # up to 3 times" says - the cycle sustains 2-3, not a pinned cap.
    fire_trigger("per_shot", {"phantom-signature": vision}, ctx, reg, 10.0)
    assert round(reg.total_for("distributed_damage_up", SELF, 10.0), 4) == round(0.1286 * 2, 4)
    assert reg.total_for("distributed_damage_up", SELF, 20.1) == 0.0
