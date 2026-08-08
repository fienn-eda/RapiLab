"""Naga - a Burst-2 Electric SG supporter whose core-damage buffs are her whole
contribution, half of them behind an ally's shield."""
from app.effects import EffectRegistry
from app.skill_rules.naga import (
    SUPPORT_SHOT_COUNT,
    build_naga_rules,
    build_support_of_friendship_per_shot_rules,
)
from app.squad_engine import SquadContext, SquadMember, fire_trigger

# ShiftyPad native slots (data/shiftypad/naga.json, level 10).
GUARDIAN_OF_FRIENDSHIP = {
    "description_value_01": "12", "description_value_02": "14.57",
    "description_value_03": "85.17", "description_value_04": "10",
}
SUPPORT_OF_FRIENDSHIP = {
    "description_value_01": "5", "description_value_02": "2",
    "description_value_03": "40.07", "description_value_04": "5",
    "description_value_05": "5", "description_value_06": "2",
    "description_value_07": "9.58",
}
AS_LONG_AS_WERE_WITH_FRIENDS = {
    "description_value_01": "10", "description_value_02": "16.18",
    "description_value_03": "10", "description_value_04": "31.02",
    "description_value_05": "10",
}
CASTER_ATK = 70000.0
NAGA = {
    "guardian_of_friendship": GUARDIAN_OF_FRIENDSHIP,
    "support_of_friendship": SUPPORT_OF_FRIENDSHIP,
    "as_long_as_were_with_friends": AS_LONG_AS_WERE_WITH_FRIENDS,
    "caster_atk": CASTER_ATK,
}

SELF = {"slug": "naga", "element": "Electric"}
ALLY = {"slug": "ally", "element": "Fire"}
CARRY = {"slug": "carry", "element": "Water"}


def _ctx(shielder=False):
    members = [
        SquadMember("naga", burst_tier=2, element="Electric", weapon="SG"),
        SquadMember("carry", burst_tier=3, element="Water", weapon="AR"),
        SquadMember("ally", burst_tier=1, element="Fire", weapon="MG"),
    ]
    if shielder:
        # Crown is in SHIELD_PROVIDER_SLUGS - a shield that reaches the squad.
        members[2] = SquadMember("crown", burst_tier=1, element="Iron", weapon="MG")
    return SquadContext(members, base_atk={"naga": 5.0, "carry": 100.0, "ally": 50.0, "crown": 50.0})


def test_the_burst_grants_her_pierce_and_a_squad_flat_atk():
    reg = EffectRegistry()
    fire_trigger("own_burst_activate", {"naga": build_naga_rules(NAGA)}, _ctx(), reg, 10.0)
    assert reg.total_for("has_pierce", SELF, 10.0) == 1.0
    assert reg.total_for("has_pierce", CARRY, 10.0) == 0.0  # "Affects self"
    assert reg.total_for("has_pierce", SELF, 20.1) == 0.0  # 10 sec
    assert reg.total_for("flat_atk", CARRY, 10.0) == 0.1618 * CASTER_ATK


def test_without_a_shielder_neither_shield_bullet_fires():
    reg = EffectRegistry()
    ctx = _ctx(shielder=False)
    rules = {"naga": build_naga_rules(NAGA)}
    fire_trigger("battle_start", rules, ctx, reg, 0.0)
    fire_trigger("own_burst_activate", rules, ctx, reg, 10.0)
    assert reg.total_for("other_core_damage_sources", CARRY, 10.0) == 0.0
    # Only the unconditional half of the burst's ATK grant.
    assert reg.total_for("flat_atk", CARRY, 10.0) == 0.1618 * CASTER_ATK


def test_a_squad_shielder_arms_both_shield_bullets():
    """The engine models no shield EVENT, so deck presence is the question that
    can be asked - and presence promotes the bullet to permanent (the ceiling,
    same ruling as Flora's Iris)."""
    reg = EffectRegistry()
    ctx = _ctx(shielder=True)
    rules = {"naga": build_naga_rules(NAGA)}
    fire_trigger("battle_start", rules, ctx, reg, 0.0)
    assert round(reg.total_for("other_core_damage_sources", CARRY, 0.0), 4) == 0.8517
    assert round(reg.total_for("other_core_damage_sources", CARRY, 179.0), 4) == 0.8517

    fire_trigger("own_burst_activate", rules, ctx, reg, 10.0)
    both = (0.1618 + 0.3102) * CASTER_ATK
    assert reg.total_for("flat_atk", CARRY, 10.0) == both
    assert reg.total_for("flat_atk", CARRY, 20.1) == 0.0  # 10 sec


def test_support_of_friendship_buffs_the_two_highest_atk_allies_every_five_shots():
    rules = build_support_of_friendship_per_shot_rules(SUPPORT_OF_FRIENDSHIP)
    assert [(n, mode) for n, mode, _ in rules] == [(SUPPORT_SHOT_COUNT, "every")]

    reg = EffectRegistry()
    ctx = _ctx()
    fire_trigger("per_shot", {"naga": rules[0][2]}, ctx, reg, 3.3)
    assert round(reg.total_for("other_core_damage_sources", CARRY, 3.3), 4) == 0.4007
    assert round(reg.total_for("other_core_damage_sources", ALLY, 3.3), 4) == 0.4007
    # She competes for her own slots (no "except caster" clause), but her base
    # ATK here is the lowest in the deck, so the two carries outrank her.
    assert reg.total_for("other_core_damage_sources", SELF, 3.3) == 0.0
    assert reg.total_for("other_core_damage_sources", CARRY, 8.4) == 0.0  # 5 sec


def test_naga_competes_for_her_own_slots_when_she_outranks_an_ally():
    """"2 ally unit(s) with the highest ATK" carries no "except caster" clause,
    so she is ranked alongside everyone else (Fienn, 2026-08-08) - unlike
    Miranda, whose text spells the exclusion out."""
    ctx = SquadContext(
        [
            SquadMember("naga", burst_tier=2, element="Electric", weapon="SG"),
            SquadMember("carry", burst_tier=3, element="Water", weapon="AR"),
            SquadMember("ally", burst_tier=1, element="Fire", weapon="MG"),
        ],
        base_atk={"naga": 90.0, "carry": 100.0, "ally": 10.0},
    )
    reg = EffectRegistry()
    rules = build_support_of_friendship_per_shot_rules(SUPPORT_OF_FRIENDSHIP)
    fire_trigger("per_shot", {"naga": rules[0][2]}, ctx, reg, 3.3)
    assert round(reg.total_for("other_core_damage_sources", CARRY, 3.3), 4) == 0.4007
    assert round(reg.total_for("other_core_damage_sources", SELF, 3.3), 4) == 0.4007
    assert reg.total_for("other_core_damage_sources", ALLY, 3.3) == 0.0  # outranked


def test_the_per_shot_buff_refreshes_instead_of_stacking():
    """Her shotgun fires the 5th round every 3.3-5.0 sec while the buff lasts
    5 sec, so the windows overlap on every single fill. Plain adds would sum
    them into a runaway multiple of the printed 40.07%."""
    rules = build_support_of_friendship_per_shot_rules(SUPPORT_OF_FRIENDSHIP)
    reg = EffectRegistry()
    ctx = _ctx()
    for t in (3.3, 6.6, 9.9, 13.2, 16.5):
        fire_trigger("per_shot", {"naga": rules[0][2]}, ctx, reg, t)
    assert round(reg.total_for("other_core_damage_sources", CARRY, 16.5), 4) == 0.4007


def test_the_cover_repair_and_the_heal_register_nothing():
    """"Restores 14.57% of cover HP" and the lowest-HP-ally heal are both
    survivability; only the heal's occurrence matters (HEAL_PROVIDER_SLUGS)."""
    reg = EffectRegistry()
    ctx = _ctx()
    rules = build_support_of_friendship_per_shot_rules(SUPPORT_OF_FRIENDSHIP)
    fire_trigger("per_shot", {"naga": rules[0][2]}, ctx, reg, 3.3)
    assert reg.total_for("flat_max_hp", CARRY, 3.3) == 0.0
    assert len(rules) == 1  # the heal bullet contributes no second per-shot rule
