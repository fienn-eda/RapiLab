"""Tests for the third batch of Burst-1 supporters: Little Mermaid, Moran,
Tove, Soline: Frost Ticket. Values are the real max-level (dollskill for
Moran/Tove) figures from dotgg.
"""
from app.effects import EffectRegistry
from app.skill_rules.little_mermaid import build_little_mermaid_rules
from app.skill_rules.moran import build_moran_rules
from app.skill_rules.soline_frost_ticket import build_soline_frost_ticket_rules
from app.skill_rules.tove import build_tove_rules
from app.squad_engine import SquadContext, SquadMember, fire_trigger

ALLY = {"slug": "ally", "element": "Fire"}


def deck_ctx(src_slug):
    return SquadContext([
        SquadMember(src_slug, burst_tier=1, element="Water"),
        SquadMember("ally", burst_tier=3, element="Fire"),
    ])


LM = {
    "bubble_order": {
        "description_value_01": "7.48", "description_value_02": "4", "description_value_03": "10",
        "description_value_04": "400", "description_value_05": "37",
    },
    "bubble_wave": {
        "description_value_01": "5.05",  # Bubble: enemy Damage Taken %, continuous
    },
    "sirens_song": {
        "description_value_01": "10.13", "description_value_02": "10", "description_value_03": "33.26",
        "description_value_04": "17.28", "description_value_05": "10",
    },
}

# Module-level aliases so the assembly verification harness
# (test_skill_value_assembly.py) can resolve each sub-skill fixture by name.
BUBBLE_ORDER = LM["bubble_order"]
BUBBLE_WAVE = LM["bubble_wave"]
SIRENS_SONG = LM["sirens_song"]


def test_little_mermaid_cdr_and_attack_damage_and_self_atk():
    reg = EffectRegistry()
    rules = {"little-mermaid": build_little_mermaid_rules(LM)}
    fire_trigger("full_burst_end", rules, deck_ctx("little-mermaid"), reg, 0.0)
    assert reg.drain_pulses("burst_cooldown_reduction_sec")[0].value == 7.48
    fire_trigger("full_burst_enter", rules, deck_ctx("little-mermaid"), reg, 0.0)
    assert round(reg.total_for("attack_damage_up", ALLY, 0.0), 4) == 0.04
    reg2 = EffectRegistry()
    fire_trigger("own_burst_activate", rules, deck_ctx("little-mermaid"), reg2, 0.0)
    assert round(reg2.total_for("attack_damage_up", ALLY, 0.0), 4) == 0.1013
    lm = {"slug": "little-mermaid", "element": "Water"}
    assert round(reg2.total_for("atk_percent", lm, 0.0), 4) == 0.1728


def test_little_mermaid_bubble_debuff_is_a_permanent_squad_enemy_damage_taken():
    reg = EffectRegistry()
    rules = {"little-mermaid": build_little_mermaid_rules(LM)}
    # "Bubble: Damage Taken +5.05% continuously" activates when the enemy
    # appears (= battle start in a raid), permanent, squad-scoped enemy debuff.
    fire_trigger("battle_start", rules, deck_ctx("little-mermaid"), reg, 0.0)
    assert round(reg.total_for("damage_taken_up", ALLY, 0.0), 4) == 0.0505
    assert round(reg.total_for("damage_taken_up", ALLY, 170.0), 4) == 0.0505  # permanent


MORAN = {
    "leave_it_to_me": {"description_value_10": "7.48"},
    "fair_and_square": {"description_value_09": "42.57", "description_value_10": "10"},
    "caster_atk": 300000,
}


def test_moran_squad_cdr_and_caster_scaled_flat_atk():
    reg = EffectRegistry()
    rules = {"moran": build_moran_rules(MORAN)}
    fire_trigger("full_burst_enter", rules, deck_ctx("moran"), reg, 0.0)
    assert reg.drain_pulses("burst_cooldown_reduction_sec")[0].value == 7.48
    fire_trigger("own_burst_activate", rules, deck_ctx("moran"), reg, 0.0)
    assert round(reg.total_for("flat_atk", ALLY, 0.0), 2) == round(300000 * 0.4257, 2)


TOVE = {
    "modification_successful": {"description_value_01": "10.08", "description_value_02": "42.24"},
    "miracle_of_makeshifts": {"description_value_01": "2.32", "description_value_02": "15"},
    "caster_atk": 300000,
}


def test_tove_squad_crit_rate_and_stacked_flat_atk():
    reg = EffectRegistry()
    rules = {"tove": build_tove_rules(TOVE)}
    fire_trigger("battle_start", rules, deck_ctx("tove"), reg, 0.0)
    assert round(reg.total_for("crit_rate", ALLY, 0.0), 4) == 0.1008
    fire_trigger("own_burst_activate", rules, deck_ctx("tove"), reg, 0.0)
    # 2.32% of ATK per stack * 3 max stacks = 6.96% of 300000 = 20880
    assert round(reg.total_for("flat_atk", ALLY, 0.0), 2) == round(300000 * 0.0232 * 3, 2)


def test_soline_frost_ticket_only_cdr():
    reg = EffectRegistry()
    rules = {"soline-frost-ticket": build_soline_frost_ticket_rules({"check_ticket": {"description_value_03": "7.48"}})}
    fire_trigger("full_burst_enter", rules, deck_ctx("soline-frost-ticket"), reg, 0.0)
    assert reg.drain_pulses("burst_cooldown_reduction_sec")[0].value == 7.48
