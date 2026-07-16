"""End-to-end floor/ceiling bracket test for Ark Ranger Black (Burst 3, Wind,
AR). Her damage is almost entirely sustained-typed DoTs gated on a
Transformation state whose duration depends on BossProfile.part_destructible
(see docs/superpowers/specs/2026-07-16-ark-ranger-black-transformation-design.md):
- floor (part_destructible=False): transformation only lasts a 10s window per
  burst.
- ceiling (part_destructible=True): transformation is permanent from battle
  start.

Assembles a real 5-unit deck (project's standard NikkeSpec + evaluate_deck
path, per test_deck_search.py/test_roster.py) with Ark Ranger as the sole
Burst-3 attacker plus already-encoded Burst-1 (Liter, Anis: Star) and Burst-2
(Crown, Takina) fillers - a deck needs all three burst tiers present or the
burst cycle never completes.
"""
from app.deck_search import BossProfile, evaluate_deck
from app.roster import NikkeSpec
from tests.test_roster import anis_star_spec, crown_spec, takina_spec

# Real level-10 values (lootandwaifus), same fixtures as
# test_skill_rules_ark_ranger_black.py.
ARK_RANGER_TRANSFORM = {
    "description_value_06": "156.19",  # ATK % while transformed
    "description_value_04": "1",       # battery decay % per interval
    "description_value_05": "0.2",     # decay interval (sec)
    "description_value_08": "30",      # normal-attack threshold (Sustained buff)
    "description_value_09": "59.6",    # Sustained Damage % (skill 1)
    "description_value_10": "5",       # its duration
}
ARK_RANGER_ULTIMATE = {
    "description_value_01": "50",      # battery % after transforming (Emergency Charge)
    "description_value_02": "266.69",  # Meteor DoT % per tick
    "description_value_03": "10",      # Meteor tick count
    "description_value_04": "135.83",  # self Sustained Damage % (burst)
    "description_value_05": "10",      # its duration
}
ARK_RANGER_TREMBLE = {"description_value_01": "45.87"}  # Ark Black Collider % per tick

# Real level-10 Liter values, same fixture as test_skill_rules_burst1_batch1.py.
LITER_VALUES = {
    "liter_boost": {
        "description_value_01": "2.34", "description_value_02": "2.7", "description_value_03": "3.17",
        "description_value_04": "45.17", "description_value_05": "5", "description_value_06": "12.46",
        "description_value_07": "5", "description_value_08": "14.42", "description_value_09": "5",
    },
    "double_boost": {"description_value_01": "66", "description_value_02": "5"},
}


def liter_spec():
    return NikkeSpec(
        slug="liter",
        burst_tier=1,
        burst_cooldown=20.0,
        element="Iron",
        weapon="SMG",
        base_stats={"atk": 250000, "def": 60000, "max_hp": 9000000},
        skill_values=LITER_VALUES,
        weapon_stats={
            "weapon": "SMG", "damage_percent": 8.0, "max_ammo": 90,
            "reload_time": 1.5, "charge_time": 0.0, "charge_damage_percent": 0.0,
        },
    )


def ark_ranger_black_spec():
    return NikkeSpec(
        slug="ark-ranger-black",
        burst_tier=3,
        burst_cooldown=40.0,  # real cooldown (data/lootandwaifus/char_ark-ranger-black.json)
        element="Wind",
        weapon="AR",  # confirmed from data/lootandwaifus/char_ark-ranger-black.json
        base_stats={"atk": 400000, "def": 55000, "max_hp": 9700000},
        skill_values={
            "transform": ARK_RANGER_TRANSFORM,
            "ultimate": ARK_RANGER_ULTIMATE,
            "tremble": ARK_RANGER_TREMBLE,
        },
        weapon_stats={
            "weapon": "AR", "damage_percent": 13.65, "max_ammo": 60,
            "reload_time": 1.0, "charge_time": 0.0, "charge_damage_percent": 100.0,
        },
    )


def _ark_ranger_deck():
    # canonical tier order (1, 1, 2, 2, 3); Ark Ranger is the sole burst-3
    # attacker so she fires every cycle regardless of intra-tier ordering.
    return [liter_spec(), anis_star_spec(), crown_spec(), takina_spec(), ark_ranger_black_spec()]


def _evaluate_ark_ranger_deck(part_destructible=False):
    boss = BossProfile(fight_duration=90.0, part_destructible=part_destructible)
    return evaluate_deck(_ark_ranger_deck(), boss)


def test_ceiling_beats_floor_for_ark_ranger():
    floor = _evaluate_ark_ranger_deck(part_destructible=False)
    ceiling = _evaluate_ark_ranger_deck(part_destructible=True)
    assert ceiling["total_damage"] > floor["total_damage"]


def test_default_boss_reproduces_floor():
    default = _evaluate_ark_ranger_deck()  # part_destructible defaults False
    floor = _evaluate_ark_ranger_deck(part_destructible=False)
    assert default["total_damage"] == floor["total_damage"]


def test_floor_result_has_nonzero_sustained_damage():
    # Guards against the DoTs being mistagged as "attack" - if they were, all
    # of Ark Ranger's Sustained Damage buffs would silently be no-ops.
    floor = _evaluate_ark_ranger_deck(part_destructible=False)
    sustained_total = sum(
        entry["damage"] for entry in floor["damage_log"] if entry["damage_type"] == "sustained"
    )
    assert sustained_total > 0
