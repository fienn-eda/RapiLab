"""Eunhwa: Tactical Upgrade - a Burst-2 Fire SR attacker who deals true damage
while Camouflaged, and whose burst swaps her rifle for one exploding round."""
from app.effects import EffectRegistry
from app.skill_rules.eunhwa_tactical_upgrade import (
    build_camouflage_per_shot_rules,
    build_eunhwa_tactical_upgrade_rules,
    build_explosive_round_weapon_mode_schedule,
)
from app.squad_engine import SquadContext, SquadMember, fire_trigger

# ShiftyPad native slots (data/shiftypad/eunhwa-tactical-upgrade.json, level 10).
CAMOUFLAGE_SCARF = {"description_value_01": "5", "description_value_02": "42.24"}
AS_FORMATION = {
    "description_value_01": "8.16", "description_value_02": "41.81",
    "description_value_03": "5.11", "description_value_04": "30.97",
    "description_value_05": "42.24",
}
EXPLOSIVE_ROUND = {
    "description_value_01": "105.6", "description_value_02": "1",
    "description_value_03": "27.87", "description_value_04": "10",
}
EUNHWA = {
    "camouflage_scarf": CAMOUFLAGE_SCARF,
    "as_formation": AS_FORMATION,
    "explosive_round": EXPLOSIVE_ROUND,
}

SELF = {"slug": "eunhwa-tactical-upgrade", "element": "Fire"}
EMMA = {"slug": "emma-tactical-upgrade", "element": "Fire"}
OUTSIDER = {"slug": "outsider", "element": "Water"}


def _ctx(with_emma=False):
    members = [
        SquadMember("eunhwa-tactical-upgrade", burst_tier=2, element="Fire", weapon="SR"),
        SquadMember("outsider", burst_tier=3, element="Water", weapon="AR"),
    ]
    if with_emma:
        members.append(
            SquadMember("emma-tactical-upgrade", burst_tier=1, element="Fire", weapon="MG"))
    return SquadContext(members)


def test_as_formation_is_permanent_from_battle_start():
    reg = EffectRegistry()
    fire_trigger(
        "battle_start", {"eunhwa-tactical-upgrade": build_eunhwa_tactical_upgrade_rules(EUNHWA)},
        _ctx(), reg, 0.0,
    )
    # Effect 2 "Affects all allies", Effect 3 "Affects self" - read per bullet.
    assert round(reg.total_for("charge_damage_bonus", OUTSIDER, 179.0), 4) == 0.4181
    assert round(reg.total_for("atk_percent", SELF, 179.0), 4) == 0.4224
    assert reg.total_for("atk_percent", OUTSIDER, 0.0) == 0.0


def test_the_same_squad_crit_rate_reaches_only_absolute_squad_members():
    """"Affects all allies from the same squad" is her in-fiction squad
    (Absolute), not the deck - so a deck-mate outside it gets nothing."""
    reg = EffectRegistry()
    fire_trigger(
        "battle_start", {"eunhwa-tactical-upgrade": build_eunhwa_tactical_upgrade_rules(EUNHWA)},
        _ctx(with_emma=True), reg, 0.0,
    )
    assert round(reg.total_for("crit_rate", SELF, 0.0), 4) == 0.0816
    assert round(reg.total_for("crit_rate", EMMA, 0.0), 4) == 0.0816
    assert reg.total_for("crit_rate", OUTSIDER, 0.0) == 0.0


def test_the_lt_formation_bonus_needs_emma_in_the_deck():
    reg = EffectRegistry()
    fire_trigger(
        "battle_start", {"eunhwa-tactical-upgrade": build_eunhwa_tactical_upgrade_rules(EUNHWA)},
        _ctx(with_emma=False), reg, 0.0,
    )
    assert reg.total_for("projectile_explosion_damage_up", OUTSIDER, 0.0) == 0.0
    assert reg.total_for("true_damage_up", OUTSIDER, 0.0) == 0.0

    reg = EffectRegistry()
    fire_trigger(
        "battle_start", {"eunhwa-tactical-upgrade": build_eunhwa_tactical_upgrade_rules(EUNHWA)},
        _ctx(with_emma=True), reg, 0.0,
    )
    assert round(reg.total_for("projectile_explosion_damage_up", OUTSIDER, 0.0), 4) == 0.0511
    assert round(reg.total_for("true_damage_up", OUTSIDER, 0.0), 4) == 0.3097


def test_her_burst_arms_camouflage_and_debuffs_the_target():
    reg = EffectRegistry()
    fire_trigger(
        "own_burst_activate", {"eunhwa-tactical-upgrade": build_eunhwa_tactical_upgrade_rules(EUNHWA)},
        _ctx(), reg, 10.0,
    )
    # Camouflage: her normal attacks become true damage, and she gets the
    # matching True Damage buff - both self, both for the 5-sec status.
    assert reg.total_for("normal_attacks_deal_true", SELF, 10.0) == 1.0
    assert round(reg.total_for("true_damage_up", SELF, 10.0), 4) == 0.4224
    assert reg.total_for("normal_attacks_deal_true", SELF, 15.1) == 0.0
    # Explosive Round's rider, on the enemy.
    assert round(reg.total_for("damage_taken_up", OUTSIDER, 10.0), 4) == 0.2787
    assert reg.total_for("damage_taken_up", OUTSIDER, 20.1) == 0.0


def test_camouflage_rearms_on_every_full_charge_inside_full_burst():
    rules = build_camouflage_per_shot_rules(CAMOUFLAGE_SCARF)
    assert [(n, mode) for n, mode, _ in rules] == [(1, "every_during_full_burst")]

    reg = EffectRegistry()
    ctx = _ctx()
    fire_trigger("per_shot", {"eunhwa-tactical-upgrade": rules[0][2]}, ctx, reg, 13.0)
    assert reg.total_for("normal_attacks_deal_true", SELF, 13.0) == 1.0
    assert round(reg.total_for("true_damage_up", SELF, 17.9), 4) == 0.4224
    assert reg.total_for("true_damage_up", SELF, 18.1) == 0.0


def test_the_two_camouflage_sources_are_one_status_not_two():
    """Her burst arms it and her Full-Burst charges re-arm it, and the windows
    overlap. They must collapse to one 42.24% - summing would double the buff
    for as long as both are live."""
    reg = EffectRegistry()
    ctx = _ctx()
    fire_trigger(
        "own_burst_activate",
        {"eunhwa-tactical-upgrade": build_eunhwa_tactical_upgrade_rules(EUNHWA)}, ctx, reg, 10.0)
    per_shot = build_camouflage_per_shot_rules(CAMOUFLAGE_SCARF)[0][2]
    for t in (11.4, 12.8, 14.2):
        fire_trigger("per_shot", {"eunhwa-tactical-upgrade": per_shot}, ctx, reg, t)
    assert round(reg.total_for("true_damage_up", SELF, 14.2), 4) == 0.4224
    assert reg.total_for("normal_attacks_deal_true", SELF, 14.2) == 1.0


def test_explosive_round_is_a_single_shot_weapon_segment_dealing_true_damage():
    schedule = build_explosive_round_weapon_mode_schedule(EUNHWA)
    ctx = _ctx()
    ctx.burst_times["eunhwa-tactical-upgrade"] = [10.0, 30.0]
    segments = schedule(ctx, 180.0)
    assert [s["start"] for s in segments] == [10.0, 30.0]
    assert all(s["until_shots"] == 1 for s in segments)
    profile = segments[0]["profile"]
    assert profile["weapon"] == "SR"
    assert profile["damage_percent"] == 105.6
    assert profile["charge_damage_percent"] == 300.0
    assert profile["charge_time"] == 0.3
    assert profile["max_ammo"] == 1
    assert profile["damage_type"] == "true"


def test_the_segments_charge_damage_carries_the_collectible_multiplier():
    """Every term of the transformed weapon is a skill value, so the 배율 that
    weapon_stats would normally carry has to be applied in the profile - else
    the segment silently drops the collectible (Maxwell and Red Hood were both
    in exactly that state until 2026-08-03)."""
    schedule = build_explosive_round_weapon_mode_schedule({**EUNHWA,
                                                          "caster_charge_damage_multiplier": 1.5})
    ctx = _ctx()
    ctx.burst_times["eunhwa-tactical-upgrade"] = [10.0]
    assert schedule(ctx, 180.0)[0]["profile"]["charge_damage_percent"] == 450.0
