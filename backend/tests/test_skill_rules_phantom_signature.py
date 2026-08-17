"""Phantom's Favorite Item build - the extra Thief's Dagger source unlocks the
whole Thief's Vision chain her base build can never reach."""
from app.effects import EffectRegistry
from app.skill_rules.phantom_signature import (
    VISION_PROC_SHOTS,
    build_dagger_resource_specs,
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


def test_hit_rate_is_not_a_flat_battle_start_grant():
    """It rides the live dagger count instead (see the resource spec below), so
    nothing hands it out up front. Pinned because the earlier encoding DID grant
    a permanent one-stack floor here, and leaving both in place would double it."""
    reg = _fire("battle_start")
    assert reg.total_for("hit_rate", SELF, 0.0) == 0.0
    assert reg.total_for("hit_rate", ALLY, 0.0) == 0.0


def test_the_dagger_drives_hit_rate_as_a_live_count():
    """Her Hit Rate is the stack count's step function, self-scope, each stack
    expiring on its own 5 sec clock - not the base build's one-stack floor."""
    (spec,) = build_dagger_resource_specs(PHANTOM_SIG)
    assert spec.cap == 3
    (buff,) = spec.buffs
    assert (buff.stat, buff.scope) == ("hit_rate", "self")
    assert (spec.lifetime, spec.lifetime_refreshes) == (5.0, True)
    assert [round(buff.value_fn(n), 4) for n in (0, 1, 2, 3)] == [
        0.0, 0.2575, 0.515, 0.7725]


def test_the_dagger_spends_itself_at_the_cap():
    """The consumption is what makes the count a sawtooth. Its times come from
    the SAME walk as the fills, so the two cannot disagree."""
    (spec,) = build_dagger_resource_specs(PHANTOM_SIG)
    assert spec.fill[0] == "computed"
    (reset,) = spec.resets
    assert (reset["trigger"], reset["value"]) == ("computed", 0)

    shots = [i / 12.0 for i in range(1, 400)]
    fills = spec.fill[1](shots)
    spends = reset["times"](shots)
    assert fills and spends
    # Every spend is a shot that also filled - the cap is reached BY a fill.
    assert set(spends) <= set(fills)


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
    # "as Distributed Damage" -> typed so her Distributed Damage buffs apply.
    assert by_percent[250.0].damage_type == "distributed"


def test_the_10_shot_pair_refreshes_instead_of_stacking():
    """That bullet carries no "Stacks up to N times" clause - unlike the two that
    do - so a re-application replaces the live grant. At 12 AR shots/sec the
    counter fires every 0.83 sec, far inside both durations."""
    by_count = {every: shot_rules for every, _mode, shot_rules in
                build_phantom_signature_per_shot_rules(PHANTOM_SIG)}
    reg = EffectRegistry()
    ctx = _ctx()
    for shot in range(10, 121, 10):
        fire_trigger("per_shot", {"phantom-signature": by_count[10]}, ctx, reg, shot / 12.0)
    assert round(reg.total_for("atk_percent", SELF, 10.0), 4) == 0.8512
    assert round(reg.total_for("distributed_damage_up", SELF, 10.0), 4) == 0.3192


def test_her_two_distributed_damage_bullets_stay_independent():
    """One refreshes and one stacks, and both grant self `distributed_damage_up` -
    so the refreshing bullet must not sweep away the Vision proc's stacks."""
    by_count = {every: shot_rules for every, _mode, shot_rules in
                build_phantom_signature_per_shot_rules(PHANTOM_SIG)}
    reg = EffectRegistry()
    ctx = _ctx()
    fire_trigger("per_shot", {"phantom-signature": by_count[VISION_PROC_SHOTS]}, ctx, reg, 5.0)
    fire_trigger("per_shot", {"phantom-signature": by_count[10]}, ctx, reg, 5.1)
    assert round(reg.total_for("distributed_damage_up", SELF, 5.1), 4) == round(0.1286 + 0.3192, 4)


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
