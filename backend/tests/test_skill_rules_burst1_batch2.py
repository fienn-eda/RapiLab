"""Tests for the second batch of Burst-1 supporters: Rouge, Zwei, D: Killer
Wife. Values are the real max-level (dollskill for Zwei) figures from dotgg.
"""
from app.effects import EffectRegistry
from app.skill_rules.d_killer_wife import build_assault_formation_rules, build_d_killer_wife_rules
from app.skill_rules.rouge import (
    build_card_throw_rules,
    build_coin_flip_per_shot_rules,
    build_coin_flip_rules,
    build_game_master_rules,
)
from app.skill_rules.zwei import (
    build_overcharge_weapon_mode_schedule,
    build_frame_analysis_resources,
    build_pierce_equation_per_shot_rules,
    build_zwei_base_rules,
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
    fire_trigger("battle_start", {"rouge": _coin_flip()}, ctx, reg, 0.0)
    assert round(reg.total_for("attack_damage_up", ALLY, 0.0), 4) == 0.0665
    assert round(reg.total_for("attack_damage_up", ALLY, 999.0), 4) == 0.0665  # continuous
    assert ctx.has_status("rouge", "Sword Coin") is True


ROUGE_MAX_HP = 10_000_000.0


def _coin_flip():
    return build_coin_flip_rules({**ROUGE_COIN_FLIP, "caster_max_hp": ROUGE_MAX_HP})


def test_rouge_shield_coin_arms_after_thirty_full_charges_and_needs_sword_coin():
    ps = build_coin_flip_per_shot_rules(ROUGE_COIN_FLIP)
    assert len(ps) == 1
    threshold, mode, rules = ps[0]
    assert (threshold, mode) == (30, "after")

    # Sword Coin 없이는 사슬이 시작되지 않는다.
    bare = deck_ctx("rouge")
    reg = EffectRegistry()
    for rule in rules:
        if rule.condition(bare, "rouge"):
            rule.action(bare, "rouge", 30.0, reg)
    assert bare.has_status("rouge", "Shield Coin") is False

    ctx = deck_ctx("rouge")
    ctx.set_status("rouge", "Sword Coin")
    for rule in rules:
        if rule.condition(ctx, "rouge"):
            rule.action(ctx, "rouge", 30.0, reg)
    assert ctx.has_status("rouge", "Shield Coin") is True


def test_rouge_double_sword_coin_needs_five_bursts_and_shield_coin():
    ctx = deck_ctx("rouge")
    ctx.set_status("rouge", "Shield Coin")
    reg = EffectRegistry()
    rules = {"rouge": _coin_flip()}
    for cycle in range(1, 5):
        fire_trigger("own_burst_activate", rules, ctx, reg, float(cycle))
        assert ctx.has_status("rouge", "Double Sword Coin") is False
        assert reg.total_for("flat_max_hp", ALLY, float(cycle)) == 0.0
    fire_trigger("own_burst_activate", rules, ctx, reg, 5.0)
    assert ctx.has_status("rouge", "Double Sword Coin") is True
    assert round(reg.total_for("flat_max_hp", ALLY, 5.0), 2) == round(ROUGE_MAX_HP * 0.1508, 2)
    assert round(reg.total_for("flat_max_hp", ALLY, 999.0), 2) == round(ROUGE_MAX_HP * 0.1508, 2)


def test_rouge_double_sword_coin_never_arms_without_shield_coin():
    ctx = deck_ctx("rouge")
    reg = EffectRegistry()
    rules = {"rouge": _coin_flip()}
    for cycle in range(1, 8):
        fire_trigger("own_burst_activate", rules, ctx, reg, float(cycle))
    assert ctx.has_status("rouge", "Double Sword Coin") is False
    assert reg.total_for("flat_max_hp", ALLY, 7.0) == 0.0


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


# Base ("skills") level-10 values - slug "zwei". Note Overcharge Formula's squad
# Pierce sits at slots 05/06 here: the base text never says "Pierce Attacks 101",
# so no literal 101 consumes a slot and shifts the rest along.
ZWEI_BASE_PIERCE_EQUATION = {
    "description_value_01": "20.13", "description_value_02": "1",
    "description_value_03": "10.06", "description_value_04": "10",
}
ZWEI_BASE_FRAME_ANALYSIS = {
    "description_value_01": "5", "description_value_02": "7.52",
    "description_value_03": "18.63", "description_value_04": "5",  # 5 sec, not 10
}
ZWEI_BASE_OVERCHARGE_FORMULA = {
    "description_value_01": "1.5",    # transform charge time (1.2 with the item)
    "description_value_02": "50.69",
    "description_value_03": "300",
    "description_value_04": "1",
    "description_value_05": "15.48",  # squad Pierce Damage %
    "description_value_06": "10",     # duration
}
ZWEI_BASE = {
    "pierce_equation": ZWEI_BASE_PIERCE_EQUATION,
    "frame_analysis": ZWEI_BASE_FRAME_ANALYSIS,
    "overcharge_formula": ZWEI_BASE_OVERCHARGE_FORMULA,
}

ZWEI = {
    "pierce_equation": {
        "description_value_01": "20.13", "description_value_02": "1", "description_value_03": "10.06",
        "description_value_04": "10", "description_value_05": "24.99", "description_value_06": "3", "description_value_07": "1",
    },
    # lootandwaifus slot order (dv05 is the "Pierce Attacks 101" name, not a value).
    "frame_analysis": {
        "description_value_01": "5", "description_value_02": "7.52", "description_value_03": "18.63",
        "description_value_04": "10", "description_value_05": "101", "description_value_06": "15",
        "description_value_07": "5", "description_value_08": "3",
    },
    # Migrated off dotgg, which carries no slot for the transform's charge time
    # or Full Charge multiplier (the rapi-red-hood / nayuta precedent).
    "overcharge_formula": {
        "description_value_01": "1.2",    # transform charge time
        "description_value_02": "50.69",  # transform damage %
        "description_value_03": "300",    # Full Charge Damage, % of that damage
        "description_value_04": "1",      # Max Ammunition Capacity -> one shot
        "description_value_05": "101",    # "Pierce Attacks 101" name, not a value
        "description_value_06": "25.03",  # squad Pierce Damage %
        "description_value_07": "10",     # duration (also the status window)
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


def test_card_throw_max_hp_rides_the_real_eight_full_charge_counter():
    """Card Throw's two bullets share one trigger but not one mechanism.

    The CDR stays a per-cycle pulse because a burst-cooldown change has to be
    known before the rotation is scheduled, and per-shot rules run after it.
    The Max HP grant has no such ordering constraint - it is a damage INPUT that
    phase 2 reads at each instance's own time - so it rides the counter the
    skill actually names, every 8 full charges (Rouge is an SR, so every shot).
    """
    from app.skill_rules.rouge import build_card_throw_per_shot_rules

    rules = build_card_throw_per_shot_rules(ROUGE_CARD_THROW, caster_max_hp=500_000.0)
    threshold, mode, skill_rules = rules[0]
    assert (threshold, mode) == (8, "every")

    reg = EffectRegistry()
    ctx = deck_ctx("rouge")
    for rule in skill_rules:
        rule.action(ctx, "rouge", 4.0, reg)
    # 5% of her own 500,000 Max HP, to every ally, for 5 sec.
    assert round(reg.total_for("flat_max_hp", ALLY, 4.0), 2) == 25_000.0
    assert reg.total_for("flat_max_hp", ALLY, 9.1) == 0.0


def test_card_throw_max_hp_refreshes_rather_than_stacking():
    """8 full charges is ~8 sec for an SR against a 5-sec buff, but a deck that
    speeds her charge can re-arm it inside its own window - the game refreshes
    a re-application, it does not sum them."""
    from app.skill_rules.rouge import build_card_throw_per_shot_rules

    _, _, skill_rules = build_card_throw_per_shot_rules(
        ROUGE_CARD_THROW, caster_max_hp=500_000.0)[0]
    reg = EffectRegistry()
    ctx = deck_ctx("rouge")
    for rule in skill_rules:
        rule.action(ctx, "rouge", 4.0, reg)
        rule.action(ctx, "rouge", 6.0, reg)
    assert round(reg.total_for("flat_max_hp", ALLY, 6.0), 2) == 25_000.0  # not 50,000


def test_d_killer_wife_pierce_buff_reaches_sniper_allies_only():
    """"Affects all allies with a Sniper Rifle" - an exact weapon filter, so an
    AR ally that happens to hold Pierce does not collect her Pierce Damage."""
    ctx = SquadContext([
        SquadMember("d-killer-wife", burst_tier=1, element="Electric", weapon="SR"),
        SquadMember("sniper-ally", burst_tier=3, element="Fire", weapon="SR"),
        SquadMember("ally", burst_tier=2, element="Fire", weapon="AR"),
    ])
    reg = EffectRegistry()
    fire_trigger("full_burst_enter", {"d-killer-wife": build_d_killer_wife_rules(DKW)}, ctx, reg, 0.0)
    assert round(reg.total_for("pierce_damage_up", {"slug": "sniper-ally", "element": "Fire"}, 0.0), 4) == 0.1355
    assert round(reg.total_for("pierce_damage_up", {"slug": "d-killer-wife", "element": "Electric"}, 0.0), 4) == 0.1355
    assert reg.total_for("pierce_damage_up", ALLY, 0.0) == 0.0


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
    # Two per-shot rules share this builder: Assault Formation every 5 full
    # charges, and Calm Sniping's one-round Pierce grant every 3.
    rules = build_assault_formation_rules(DKW["assault_formation"])
    assert [(t, m) for t, m, _ in rules] == [(5, "every"), (3, "every")]
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
ZWEI_SIG_PIERCE_EQUATION = ZWEI["pierce_equation"]
ZWEI_SIG_FRAME_ANALYSIS = ZWEI["frame_analysis"]
ZWEI_SIG_OVERCHARGE_FORMULA = ZWEI["overcharge_formula"]

PIERCE_EQUATION = ZWEI["pierce_equation"]
FRAME_ANALYSIS = ZWEI["frame_analysis"]
OVERCHARGE_FORMULA = ZWEI["overcharge_formula"]


def test_overcharge_formula_transform_is_a_single_charged_pierce_shot():
    """Max Ammunition Capacity: 1 means the window is one shot, not a duration -
    the Maxwell Pierce Shot shape. The text says plain "Charge Time", not "fixed
    at", so it goes in as a charge_time and stays open to Charge Speed buffs."""
    schedule = build_overcharge_weapon_mode_schedule(ZWEI)
    ctx = deck_ctx("zwei")
    ctx.burst_times["zwei"] = [12.0, 52.0]

    segments = schedule(ctx, 180.0)
    assert [seg["start"] for seg in segments] == [12.0, 52.0]
    assert all(seg["until_shots"] == 1 for seg in segments)

    profile = segments[0]["profile"]
    assert profile["charge_time"] == 1.2
    assert profile["damage_percent"] == 50.69
    assert profile["charge_damage_percent"] == 300


def test_zwei_base_reads_the_burst_pierce_from_its_own_slot():
    # The Favorite Item's text names "Pierce Attacks 101", so the literal 101
    # eats slot 05 and shifts its squad Pierce to 06. The base has no such name,
    # so its Pierce is at 05 - reading the signature indices here would pick up
    # the duration instead of the buff.
    ctx = deck_ctx("zwei")
    reg = EffectRegistry()
    rules = {"zwei": build_zwei_base_rules(ZWEI_BASE)}

    fire_trigger("own_burst_activate", rules, ctx, reg, time=0.0)

    ally = {"slug": "ally", "element": "Iron"}
    assert round(reg.total_for("pierce_damage_up", ally, 0.0), 4) == 0.1548
    assert reg.total_for("pierce_damage_up", ally, 10.1) == 0.0


def test_zwei_base_full_burst_crit_rate_lasts_five_seconds_not_ten():
    ctx = deck_ctx("zwei")
    reg = EffectRegistry()
    rules = {"zwei": build_zwei_base_rules(ZWEI_BASE)}

    fire_trigger("full_burst_enter", rules, ctx, reg, time=0.0)

    ally = {"slug": "ally", "element": "Iron"}
    assert round(reg.total_for("crit_rate", ally, 0.0), 4) == 0.1863
    assert reg.total_for("crit_rate", ally, 5.1) == 0.0  # the item doubles this window


def test_zwei_transform_schedule_anchors_on_the_slug_it_is_built_for():
    # Both builds transform; each must follow its OWN burst times, or the
    # signature slug would find none and silently never transform.
    schedule = build_overcharge_weapon_mode_schedule(ZWEI, slug="zwei-signature")

    class Ctx:
        burst_times = {"zwei": [5.0], "zwei-signature": [7.0]}

    windows = schedule(Ctx(), 60.0)
    assert [w["start"] for w in windows] == [7.0]
    assert windows[0]["profile"]["charge_time"] == 1.2
