from app.damage_formula import calculate_damage


def test_base_damage_only_no_modifiers():
    # ATK 1000, no % buffs, no flat bonuses, enemy DEF 0 -> base damage passes through untouched
    damage = calculate_damage(atk=1000, enemy_def=0)
    assert damage == 1000


def test_atk_percent_buff_increases_base_damage():
    damage = calculate_damage(atk=1000, atk_percent=0.5, enemy_def=0)
    assert damage == 1500


def test_enemy_defense_reduces_damage():
    damage = calculate_damage(atk=1000, enemy_def=300, enemy_def_percent=0)
    assert damage == 700


def test_attack_coefficient_scales_the_whole_base_damage():
    # The attack/skill coefficient (e.g. normal attack 61.3% of ATK, Aegis
    # Cannon 8236.8%) multiplies Base Damage as a whole, per nikke.gg's formula
    # (Base Damage x Final ATK modifiers). Default 1.0 leaves damage unchanged.
    assert calculate_damage(atk=1000, enemy_def=0, attack_coefficient=5.0) == 5000
    assert calculate_damage(atk=1000, enemy_def=0, attack_coefficient=0.613) == 613


def test_attack_coefficient_applies_after_defense_subtraction():
    # This is the case that distinguishes correct from the old "fold coefficient
    # into ATK" bug: defense is subtracted at base-ATK scale, THEN the whole
    # (offense - defense) is multiplied by the coefficient. (1000 - 200) * 5.
    assert calculate_damage(atk=1000, enemy_def=200, attack_coefficient=5.0) == 4000


def test_attack_coefficient_scales_flat_atk_since_it_is_inside_base_damage():
    # "% Caster's ATK" (flat_atk) sits inside the Base Damage parenthesis, so it
    # is multiplied by the coefficient too: (1000 + 500) * 2.
    assert calculate_damage(atk=1000, flat_atk=500, enemy_def=0, attack_coefficient=2.0) == 3000


def test_guaranteed_crit_applies_50_percent_major_modifier():
    # crit_rate=1.0 (always crits) -> major modifier gains the 0.5 base crit bonus
    damage = calculate_damage(atk=1000, enemy_def=0, crit_rate=1.0)
    assert damage == 1500


def test_zero_crit_rate_adds_no_crit_contribution():
    damage = calculate_damage(atk=1000, enemy_def=0, crit_rate=0.0)
    assert damage == 1000


def test_crit_rate_scales_the_expected_crit_bonus():
    # expected major = 1 + crit_rate * 0.5; at 0.15 base crit that's +7.5%
    assert calculate_damage(atk=1000, enemy_def=0, crit_rate=0.15) == 1075
    assert calculate_damage(atk=1000, enemy_def=0, crit_rate=0.5) == 1250


def test_crit_damage_sources_only_count_scaled_by_crit_rate():
    # crit damage buffs raise the crit hit's bonus but only take effect on the
    # crit fraction of hits: expected major = 1 + crit_rate * (0.5 + sources).
    assert calculate_damage(atk=1000, enemy_def=0, crit_rate=1.0, other_critical_damage_sources=0.2) == 1700
    # with no chance to crit, crit damage sources are inert
    assert calculate_damage(atk=1000, enemy_def=0, crit_rate=0.0, other_critical_damage_sources=0.2) == 1000


def test_core_hit_applies_bonus():
    # core hit bonus of 1.0 (a "full" 100% extra) -> major modifier 1 + 1.0
    damage = calculate_damage(atk=1000, enemy_def=0, core_hit_bonus=1.0)
    assert damage == 2000


def test_full_burst_bonus_is_scaled_by_half():
    # Full Burst Bonus x 0.5 term in Major Modifiers
    damage = calculate_damage(atk=1000, enemy_def=0, full_burst_bonus=1.0)
    assert damage == 1500


def test_element_advantage_multiplies_damage():
    damage = calculate_damage(atk=1000, enemy_def=0, element_multiplier=1.1)
    assert round(damage, 5) == 1100


def test_charge_damage_multiplier_applies():
    damage = calculate_damage(atk=1000, enemy_def=0, charge_damage_bonus=1.5)
    assert damage == 2500


def test_damage_up_sources_stack_additively():
    damage = calculate_damage(
        atk=1000, enemy_def=0, attack_damage_up=0.2, true_damage_up=0.1
    )
    assert round(damage, 5) == 1300


def test_damage_to_parts_does_not_boost_damage_dealt_to_the_body():
    """"Damage to Parts ▲ X%" raises damage dealt to PARTS, and this engine
    has no parts - it models one boss target.

    It used to ride the general Damage-Up bucket, i.e. every hit was treated as
    a parts hit. Fienn's recorded run disproves that ceiling directly: Snow
    White: Heavy Arms carries +62.64% of it refreshed on every shot and read
    1.44x against her recorded 1.68B, while removing the term entirely still
    leaves her at 1.12x - so the true contribution is at or below zero-on-body.
    Ruling: it never applies to body damage (Fienn, 2026-07-26).
    """
    assert calculate_damage(atk=1000, enemy_def=0, damage_to_parts_up=0.5) == (
        calculate_damage(atk=1000, enemy_def=0)
    )


def test_damage_taken_debuff_multiplies_final_damage():
    damage = calculate_damage(atk=1000, enemy_def=0, damage_taken_up=0.3)
    assert round(damage, 5) == 1300


def test_combined_realistic_scenario():
    # ATK 2000 with 50% ATK buff, vs enemy with 500 base DEF and 20% DEF up,
    # a crit + core hit in full burst, elemental advantage, and a 10% damage-taken debuff.
    damage = calculate_damage(
        atk=2000,
        atk_percent=0.5,
        enemy_def=500,
        enemy_def_percent=0.2,
        crit_rate=1.0,
        core_hit_bonus=1.0,
        full_burst_bonus=1.0,
        element_multiplier=1.1,
        damage_taken_up=0.1,
    )
    base_damage = 2000 * 1.5 - 500 * 1.2
    major_modifier = 1 + 0.5 + 1.0 + 1.0 * 0.5
    expected = base_damage * major_modifier * 1.1 * 1.1
    assert round(damage, 5) == round(expected, 5)


# Fienn's in-game range test of Ade: Agent Bunny (2026-07-27), solo, ATK
# 305,667, overload ATK +11.81% / Charge Damage +11.81%, every reading a
# full-charge CORE hit. Recorded damage, by Spy Lens stacks:
#
#   0-9 stacks   1,309,593 non-crit | 1,636,991 crit | 1,506,032 non-crit in range
#   10 stacks    1,901,276 non-crit | 2,376,594 crit            (out of range)
#                2,186,467 non-crit | 2,661,786 crit            (in range)
#
# The absolute numbers depend on terms the test target's DEF hides, but the
# RATIOS isolate the major-modifier bucket exactly - which is the whole reason
# range measurements beat the 180s record (see docs/insights.md).
ADE_CRIT_RATIO = 1636991 / 1309593           # 1.250000
ADE_CRIT_RATIO_IN_RANGE = 2661786 / 2186467  # 1.217391
ADE_RANGE_RATIO = 1506032 / 1309593          # 1.150000


def _major(**terms):
    """The major-modifier bucket alone, via a damage instance with every other
    multiplier neutral - base 1 ATK, no DEF, coefficient 1."""
    return calculate_damage(atk=1.0, enemy_def=0.0, **terms)


def test_core_hit_bonus_is_one_measured_against_ades_crit_pair():
    """A crit adds (0.5 + crit damage sources) to the major bucket, so a
    crit/non-crit pair on the SAME hit divides out everything else and solves
    the bucket. Ade's pair is 1.250000, and 0.5 / (1.25 - 1) = 2.0 - which is
    exactly 1 (base) + 1.0 (core hit) with no crit-damage sources, the state
    she was measured in.
    """
    non_crit = _major(crit_rate=0.0, core_hit_bonus=1.0)
    crit = _major(crit_rate=1.0, core_hit_bonus=1.0)
    assert round(non_crit, 9) == 2.0
    assert round(crit / non_crit, 6) == round(ADE_CRIT_RATIO, 6)


def test_effective_range_bonus_is_thirty_percent_of_base():
    """Being within effective range moved her core hit by exactly 1.150000,
    i.e. +0.30 on a bucket of 2.0. `effective_range_bonus` is a FLAG times
    0.3, the same shape as `full_burst_bonus` times 0.5 - this pins the 0.3.
    """
    out_of_range = _major(crit_rate=0.0, core_hit_bonus=1.0)
    in_range = _major(crit_rate=0.0, core_hit_bonus=1.0, effective_range_bonus=1.0)
    assert round(in_range / out_of_range, 6) == round(ADE_RANGE_RATIO, 6)
    assert round(in_range - out_of_range, 9) == 0.3


def test_crit_and_effective_range_stack_additively_in_the_major_bucket():
    """Her fourth reading is the cross-check: crit AND in range at once. If the
    two stacked multiplicatively the crit ratio would stay 1.25 in range; it
    measures 1.217391 instead, because 0.5 is added to a bucket that range has
    already grown to 2.3. Both terms live in the same additive bucket.
    """
    non_crit = _major(crit_rate=0.0, core_hit_bonus=1.0, effective_range_bonus=1.0)
    crit = _major(crit_rate=1.0, core_hit_bonus=1.0, effective_range_bonus=1.0)
    assert round(non_crit, 9) == 2.3
    assert round(crit / non_crit, 6) == round(ADE_CRIT_RATIO_IN_RANGE, 6)


# The same range test, solved in ABSOLUTE terms. Fienn supplied the missing
# inputs on 2026-07-27: target DEF 100, ATK 305,667 EXCLUDING overload, skill
# levels 10/7/10, and no burst. Skill 2 sitting at level 7 is what makes her
# numbers 13.78% ATK / 15.29% Pierce Damage rather than the level-10 16% /
# 18.36% - reading a measurement against max-level skill values is its own way
# to be quietly wrong.
ADE_READINGS = {
    #                       Spy Lens maxed, in effective range, crit  -> damage
    (False, False, False): 1309593,
    (False, False, True): 1636991,
    (False, True, False): 1506032,
    (True, True, False): 2186467,
    (True, True, True): 2661786,
    (True, False, False): 1901276,
    (True, False, True): 2376594,
}
ADE_ATK = 305667.0
ADE_UNMODELED_FACTOR = 1.06027  # see the test below - NOT a fudge, a receipt


def _ade_shot(spy_maxed, in_range, crit):
    """Ade's full-charge core hit under the engine's model of her kit."""
    return calculate_damage(
        atk=ADE_ATK,
        enemy_def=100.0,
        atk_percent=0.1181 + (0.1378 if spy_maxed else 0.0),  # overload + Spy Lens
        flat_atk=0.152 * ADE_ATK if spy_maxed else 0.0,       # Agent's Gaze
        pierce_damage_up=0.1529 if spy_maxed else 0.0,        # gated on having Pierce
        attack_coefficient=0.6904,                            # SR damage 69.04%
        charge_damage_bonus=1.5 + 0.1181,                     # SR 250% + overload
        core_hit_bonus=1.0,
        effective_range_bonus=1.0 if in_range else 0.0,
        crit_rate=1.0 if crit else 0.0,
        element_multiplier=1.0,
    )


def test_ade_range_readings_differ_from_the_model_by_ONE_constant_factor():
    """The structural claim, and the one worth defending.

    Seven readings span crit on/off, in/out of effective range, and Spy Lens
    below/at max - which switch three different buckets independently. The
    model reproduces every one of them to within 1e-4 of the SAME ratio. That
    is only possible if each bucket is individually right: a wrong core bonus
    or crit source breaks the in-range rows against the out-of-range ones, a
    wrong ATK term breaks the Spy-Lens rows (its flat_atk only exists there),
    and a wrong damage-up term breaks them too (pierce_damage_up shares that
    bucket). All three were checked and all three break uniformity.

    So exactly one multiplicative factor is missing, and it can only live in a
    bucket that is constant across all seven - the attack coefficient or the
    charge-damage multiplier, both weapon properties. Its source is unresolved
    (2026-07-27): dotgg reports her SR as 69.04% / 250% and 13 of the roster's
    14 SRs carry those same two numbers, so a per-unit weapon value or a
    harmony cube the engine does not model are the open candidates. See
    docs/engine-gaps.md.

    This test pins the UNIFORMITY, not the factor. If someone finds the missing
    term, this fails loudly and the constant goes to 1.0 - which is exactly the
    signal wanted, rather than a silent 6%.
    """
    ratios = {key: _ade_shot(*key) / measured for key, measured in ADE_READINGS.items()}
    assert max(ratios.values()) - min(ratios.values()) < 1e-4, ratios
    for key, ratio in ratios.items():
        assert round(ratio * ADE_UNMODELED_FACTOR, 3) == 1.0, (key, ratio)
