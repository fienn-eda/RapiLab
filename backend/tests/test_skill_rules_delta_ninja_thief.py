"""Delta: Ninja Thief - a Burst-2 Water MG defender whose damage contribution is
two enemy Damage-Taken debuffs plus a Distributed-Damage burst."""
from app.effects import EffectRegistry
from app.skill_rules.delta_ninja_thief import (
    build_delta_ninja_thief_rules,
    ninja_overdrive_burst_percent,
)
from app.squad_engine import SquadContext, SquadMember, fire_trigger

# ShiftyPad native slots (data/shiftypad/delta-ninja-thief.json, level 10).
NINJUTSU_ACID_BOMB = {
    "description_value_01": "12", "description_value_02": "15",
    "description_value_03": "15.04", "description_value_04": "10",
    "description_value_05": "8", "description_value_06": "10",
}
NINJUTSU_CAMOUFLAGE = {
    "description_value_01": "12.25", "description_value_02": "10",
    "description_value_03": "200", "description_value_04": "12.25",
    "description_value_05": "10", "description_value_06": "10",
    "description_value_07": "11.22", "description_value_08": "4",
    "description_value_09": "165.28", "description_value_10": "4",
}
NINJA_OVERDRIVE = {
    "description_value_01": "20", "description_value_02": "10",
    "description_value_03": "15", "description_value_04": "10",
    "description_value_05": "170", "description_value_06": "20.13",
    "description_value_07": "10", "description_value_08": "20.13",
    "description_value_09": "10",
}
CASTER_ATK = 80000.0
DELTA = {
    "ninjutsu_acid_bomb": NINJUTSU_ACID_BOMB,
    "ninjutsu_camouflage": NINJUTSU_CAMOUFLAGE,
    "ninja_overdrive": NINJA_OVERDRIVE,
    "caster_atk": CASTER_ATK,
}

SELF = {"slug": "delta-ninja-thief", "element": "Water"}
ALLY = {"slug": "ally", "element": "Fire"}


def _ctx():
    return SquadContext([
        SquadMember("delta-ninja-thief", burst_tier=2, element="Water", weapon="MG"),
        SquadMember("ally", burst_tier=3, element="Fire", weapon="AR"),
    ])


def test_burst_percent_is_the_distributed_nuke():
    assert ninja_overdrive_burst_percent(DELTA) == 170.0


def test_acid_bomb_debuffs_the_enemy_on_full_burst_enter():
    """"Affects all enemies" - a Damage Taken debuff sits on the enemy, so every
    attacker in the deck collects it (squad scope)."""
    reg = EffectRegistry()
    fire_trigger(
        "full_burst_enter", {"delta-ninja-thief": build_delta_ninja_thief_rules(DELTA)},
        _ctx(), reg, 12.0,
    )
    assert round(reg.total_for("damage_taken_up", SELF, 12.0), 4) == 0.12
    assert round(reg.total_for("damage_taken_up", ALLY, 26.9), 4) == 0.12
    assert reg.total_for("damage_taken_up", ALLY, 27.1) == 0.0  # 15 sec


def test_her_burst_adds_the_hyper_acid_bomb_debuff_and_a_self_atk_buff():
    reg = EffectRegistry()
    fire_trigger(
        "own_burst_activate", {"delta-ninja-thief": build_delta_ninja_thief_rules(DELTA)},
        _ctx(), reg, 10.0,
    )
    # Hyper Acid Bomb: 8% for 10 sec, on the enemy.
    assert round(reg.total_for("damage_taken_up", ALLY, 10.0), 4) == 0.08
    assert reg.total_for("damage_taken_up", ALLY, 20.1) == 0.0
    # "Affects self" - the ally must not see her ATK buff.
    assert round(reg.total_for("atk_percent", SELF, 10.0), 4) == 0.1504
    assert reg.total_for("atk_percent", ALLY, 10.0) == 0.0


def test_ninja_overdrive_buffs_the_squad_distributed_damage_and_flat_atk():
    reg = EffectRegistry()
    fire_trigger(
        "own_burst_activate", {"delta-ninja-thief": build_delta_ninja_thief_rules(DELTA)},
        _ctx(), reg, 10.0,
    )
    assert round(reg.total_for("distributed_damage_up", ALLY, 10.0), 4) == 0.20
    # "ATK +15% of the skill user's ATK" is a flat grant off HER ATK, not a
    # percentage of the recipient's.
    assert reg.total_for("flat_atk", ALLY, 10.0) == 0.15 * CASTER_ATK
    assert reg.total_for("flat_atk", ALLY, 20.1) == 0.0  # 10 sec


def test_no_shield_heal_or_taunt_bullet_registers_a_stat():
    """Every Ninjutsu Camouflage bullet is survivability. The occurrence of the
    IFAK heal matters (she is in HEAL_PROVIDER_SLUGS); none of the amounts do."""
    reg = EffectRegistry()
    ctx = _ctx()
    rules = {"delta-ninja-thief": build_delta_ninja_thief_rules(DELTA)}
    for trigger in ("battle_start", "own_burst_activate", "full_burst_enter", "full_burst_end"):
        fire_trigger(trigger, rules, ctx, reg, 12.0)
    assert reg.total_for("flat_max_hp", SELF, 12.0) == 0.0
    assert reg.total_for("shield_amount", SELF, 12.0) == 0.0


def test_battle_start_registers_nothing():
    """Her whole battle-start skill is the Defender-count branch, all of it
    survivability - so nothing should land at t=0."""
    reg = EffectRegistry()
    fire_trigger(
        "battle_start", {"delta-ninja-thief": build_delta_ninja_thief_rules(DELTA)},
        _ctx(), reg, 0.0,
    )
    for stat in ("atk_percent", "flat_atk", "damage_taken_up", "distributed_damage_up"):
        assert reg.total_for(stat, SELF, 0.0) == 0.0
