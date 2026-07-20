"""Tests for the second batch of Burst-1 supporters: Rouge, Zwei, D: Killer
Wife. Values are the real max-level (dollskill for Zwei) figures from dotgg.
"""
from app.effects import EffectRegistry
from app.skill_rules.d_killer_wife import build_assault_formation_rules, build_d_killer_wife_rules
from app.skill_rules.rouge import build_card_throw_rules, build_coin_flip_rules, build_game_master_rules
from app.skill_rules.zwei import (
    build_frame_analysis_resources,
    build_pierce_equation_per_shot_rules,
    build_zwei_rules,
)
from app.squad_engine import SquadContext, SquadMember, fire_trigger

ALLY = {"slug": "ally", "element": "Fire"}

# Rouge Lv.10 (lootandwaifus), slots left-to-right.
ROUGE_COIN_FLIP = {
    "description_value_01": "6.65",  # Sword Coin: Attack Damage %
    "description_value_02": "30",    # Shield Coin full-charge count (deferred)
    "description_value_03": "15.2",  # Shield Coin Damage Taken % (deferred)
    "description_value_04": "5",     # Double Sword Coin burst count (deferred)
    "description_value_05": "15.08", # Double Sword Coin Max HP % (deferred)
}
ROUGE_GAME_MASTER = {
    "description_value_01": "15.07", "description_value_02": "10",  # squad ATK % of caster, dur
    "description_value_03": "10.15", "description_value_04": "10",  # Sword Coin Max HP % of caster, dur
    "description_value_05": "20.1", "description_value_06": "10",   # Shield Coin Max HP %, dur
    "description_value_07": "30.02", "description_value_08": "10",  # Double Sword Coin Max HP %, dur
}
ROUGE_CARD_THROW = {
    "description_value_01": "8",   # full-charge count
    "description_value_02": "5",   # Max HP % (survival, not modeled)
    "description_value_03": "5",   # Max HP duration (not modeled)
    "description_value_04": "7",   # Cooldown reduction sec
}


def deck_ctx(src_slug):
    return SquadContext([
        SquadMember(src_slug, burst_tier=1, element="Electric"),
        SquadMember("ally", burst_tier=3, element="Fire"),
    ])


def test_rouge_coin_flip_sword_coin_squad_attack_damage_from_battle_start():
    # Back-row assumption -> Sword Coin active from battle start (squad approx of
    # "self + 2 adjacent"); also sets the Sword Coin status Game Master reads.
    ctx = deck_ctx("rouge")
    reg = EffectRegistry()
    fire_trigger("battle_start", {"rouge": build_coin_flip_rules(ROUGE_COIN_FLIP)}, ctx, reg, 0.0)
    assert round(reg.total_for("attack_damage_up", ALLY, 0.0), 4) == 0.0665
    assert round(reg.total_for("attack_damage_up", ALLY, 999.0), 4) == 0.0665  # continuous
    assert ctx.has_status("rouge", "Sword Coin") is True


def test_rouge_card_throw_cdr_applied_per_cycle():
    # Full-charge-8 CDR modeled as a per-cycle squad CDR pulse (the condition is
    # met every cycle - a full charge ~1s, 8 within a cycle is near-certain).
    reg = EffectRegistry()
    fire_trigger("full_burst_end", {"rouge": build_card_throw_rules(ROUGE_CARD_THROW)}, deck_ctx("rouge"), reg, 0.0)
    pulses = reg.drain_pulses("burst_cooldown_reduction_sec")
    assert len(pulses) == 1
    assert pulses[0].value == 7.0
    assert pulses[0].scope == "squad"


def test_rouge_game_master_squad_atk_is_caster_scaled_15_07_percent():
    values = {**ROUGE_GAME_MASTER, "caster_atk": 300000, "caster_max_hp": 10000000}
    reg = EffectRegistry()
    fire_trigger("own_burst_activate", {"rouge": build_game_master_rules(values)}, deck_ctx("rouge"), reg, 0.0)
    # 15.07% of Rouge's 300000 ATK = 45210 flat ATK to the squad (NOT 30.02%)
    assert round(reg.total_for("flat_atk", ALLY, 0.0), 2) == 45210.0
    assert reg.total_for("flat_atk", ALLY, 10.1) == 0.0


def test_rouge_game_master_sword_coin_max_hp_fires_only_when_sword_coin_active():
    values = {**ROUGE_GAME_MASTER, "caster_atk": 300000, "caster_max_hp": 10000000}
    rules = {"rouge": build_game_master_rules(values)}

    # Without Sword Coin status -> no Max HP buff.
    reg = EffectRegistry()
    fire_trigger("own_burst_activate", rules, deck_ctx("rouge"), reg, 0.0)
    assert reg.total_for("flat_max_hp", ALLY, 0.0) == 0.0

    # With Sword Coin (set by Coin Flip) -> flat Max HP = 10.15% of caster Max HP.
    ctx = deck_ctx("rouge")
    ctx.set_status("rouge", "Sword Coin")
    reg2 = EffectRegistry()
    fire_trigger("own_burst_activate", rules, ctx, reg2, 0.0)
    assert round(reg2.total_for("flat_max_hp", ALLY, 0.0), 2) == round(10000000 * 0.1015, 2)


ZWEI = {
    "pierce_equation": {
        "description_value_01": "20.13", "description_value_02": "1", "description_value_03": "10.06",
        "description_value_04": "10", "description_value_05": "24.99", "description_value_06": "3", "description_value_07": "1",
    },
    "frame_analysis": {
        "description_value_01": "5", "description_value_02": "7.52", "description_value_03": "18.63",
        "description_value_04": "10", "description_value_05": "15", "description_value_06": "3", "description_value_07": "5",
    },
    "overcharge_formula": {
        "description_value_01": "50.69", "description_value_02": "1", "description_value_03": "25.03", "description_value_04": "10",
    },
}


def test_zwei_pierce_and_crit_rate_on_full_burst_and_burst():
    reg = EffectRegistry()
    rules = {"zwei": build_zwei_rules(ZWEI)}
    fire_trigger("full_burst_enter", rules, deck_ctx("zwei"), reg, 0.0)
    assert round(reg.total_for("pierce_damage_up", ALLY, 0.0), 4) == 0.1006  # 10-sec pierce
    assert round(reg.total_for("crit_rate", ALLY, 0.0), 4) == 0.1863
    fire_trigger("own_burst_activate", rules, deck_ctx("zwei"), reg, 0.0)
    # note: separate ctx above; re-fire on same reg to check burst pierce adds
    reg2 = EffectRegistry()
    fire_trigger("own_burst_activate", rules, deck_ctx("zwei"), reg2, 0.0)
    assert round(reg2.total_for("pierce_damage_up", ALLY, 0.0), 4) == 0.2503


def test_zwei_full_burst_grants_squad_pierce_for_one_round():
    # Pierce Equation's Pierce ▲20.13% "for 1 round" is a bullet-count grant on
    # the whole squad (each ally's next shot), distinct from the 10-sec pierce.
    reg = EffectRegistry()
    rules = {"zwei": build_zwei_rules(ZWEI)}
    fire_trigger("full_burst_enter", rules, deck_ctx("zwei"), reg, 0.0)
    grants = [g for g in reg.round_grants() if g.stat == "pierce_damage_up"]
    assert len(grants) == 1
    assert grants[0].scope == "squad"
    assert round(grants[0].value, 4) == 0.2013
    assert grants[0].shots == 1


def test_zwei_pierce_equation_stacks_pierce_per_full_burst_normal_attack():
    # Pierce Equation's second bullet: EVERY normal attack during Full Burst
    # (slot 05 = 24.99%, slot 07 = "for 1 round"), so it rides the
    # Full-Burst-window-gated per-shot trigger with a threshold of 1.
    rules = build_pierce_equation_per_shot_rules(ZWEI)
    assert len(rules) == 1
    threshold, mode, skill_rules = rules[0]
    assert (threshold, mode) == (1, "every_during_full_burst")

    reg = EffectRegistry()
    for rule in skill_rules:
        rule.action(deck_ctx("zwei"), "zwei", 4.0, reg)
    grants = reg.round_grants()
    assert len(grants) == 1
    assert grants[0].stat == "pierce_damage_up"
    assert grants[0].scope == "squad"
    assert round(grants[0].value, 4) == 0.2499
    assert grants[0].shots == 1
    # "stacks up to 3 time(s)" (slot 06) - an ally never holds more at once.
    assert grants[0].cap == 3
    assert grants[0].cap_group is not None


def test_zwei_pierce_stack_cap_is_separate_from_her_uncapped_full_burst_grant():
    # Both round grants are Zwei's own pierce_damage_up, but only the per-shot
    # one caps, and its cap group must not swallow the Full Burst grant.
    reg = EffectRegistry()
    fire_trigger("full_burst_enter", {"zwei": build_zwei_rules(ZWEI)}, deck_ctx("zwei"), reg, 0.0)
    for _, _, skill_rules in build_pierce_equation_per_shot_rules(ZWEI):
        for rule in skill_rules:
            rule.action(deck_ctx("zwei"), "zwei", 4.0, reg)
    by_value = {round(g.value, 4): g for g in reg.round_grants()}
    assert by_value[0.2013].cap is None       # Full Burst grant: uncapped
    assert by_value[0.2499].cap == 3
    assert by_value[0.2013].cap_group != by_value[0.2499].cap_group


def test_zwei_frame_analysis_crit_stacks_are_capped_and_gated_on_pierce_attacks_101():
    # Frame Analysis's second bullet: +15% Crit Rate (slot 05) per normal attack
    # landed while Pierce Attacks 101 is up, 5 sec each (slot 07), capped at 3
    # (slot 06). Pierce Attacks 101 is Overcharge Formula's all-ally buff, whose
    # 10-sec duration (its slot 04) is the window the stacks may be gained in.
    specs = build_frame_analysis_resources(ZWEI)
    assert len(specs) == 1
    spec = specs[0]
    assert spec.name == "pierce_attacks_101"
    assert spec.fill == ("per_shot_every_during_own_status_window", 1, 10.0)
    assert spec.cap == 3
    assert spec.resets == []

    assert len(spec.buffs) == 1
    buff = spec.buffs[0]
    assert buff.stat == "crit_rate"
    assert buff.scope == "squad"
    assert buff.lifetime == 5.0
    assert round(buff.value_fn(3), 4) == 0.45  # 3 stacks * 15%


DKW = {
    "calm_sniping": {"description_value_01": "3", "description_value_02": "13.55", "description_value_03": "10"},
    # Assault Formation (skills[1]), Lv.10, left-to-right: CDR count/sec (deferred),
    # then Attack Damage count/value/duration.
    "assault_formation": {
        "description_value_01": "8", "description_value_02": "7", "description_value_03": "5",
        "description_value_04": "5.06", "description_value_05": "10",
    },
}


def test_d_killer_wife_pierce_buff_on_full_burst():
    reg = EffectRegistry()
    fire_trigger("full_burst_enter", {"d-killer-wife": build_d_killer_wife_rules(DKW)}, deck_ctx("d-killer-wife"), reg, 0.0)
    assert round(reg.total_for("pierce_damage_up", ALLY, 0.0), 4) == 0.1355


def test_d_killer_wife_assault_formation_cdr_applied_per_cycle():
    # Assault Formation's every-8-full-charge CDR modeled as a per-cycle squad
    # CDR pulse (condition met each cycle).
    reg = EffectRegistry()
    fire_trigger("full_burst_end", {"d-killer-wife": build_d_killer_wife_rules(DKW)}, deck_ctx("d-killer-wife"), reg, 0.0)
    pulses = reg.drain_pulses("burst_cooldown_reduction_sec")
    assert len(pulses) == 1
    assert pulses[0].value == 7.0
    assert pulses[0].scope == "squad"


def test_d_killer_wife_assault_formation_squad_attack_damage_every_5_full_charges():
    rules = build_assault_formation_rules(DKW["assault_formation"])
    assert len(rules) == 1
    threshold, mode, skill_rules = rules[0]
    assert (threshold, mode) == (5, "every")  # every 5 full charges

    reg = EffectRegistry()
    for rule in skill_rules:
        rule.action(deck_ctx("d-killer-wife"), "d-killer-wife", 8.0, reg)
    assert round(reg.total_for("attack_damage_up", ALLY, 8.0), 4) == 0.0506
    assert reg.total_for("attack_damage_up", ALLY, 18.1) == 0.0  # 10s duration


# Module-level fixture aliases so the assembly verification harness
# (test_skill_value_assembly.py) can resolve each sub-skill fixture by name.
CALM_SNIPING = DKW["calm_sniping"]
ASSAULT_FORMATION = DKW["assault_formation"]
PIERCE_EQUATION = ZWEI["pierce_equation"]
FRAME_ANALYSIS = ZWEI["frame_analysis"]
OVERCHARGE_FORMULA = ZWEI["overcharge_formula"]
