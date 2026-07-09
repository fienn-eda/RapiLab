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


def test_critical_hit_applies_150_percent_major_modifier():
    # Major modifier base is 1 + 0.5 (crit) when is_critical=True
    damage = calculate_damage(atk=1000, enemy_def=0, is_critical=True)
    assert damage == 1500


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
        is_critical=True,
        core_hit_bonus=1.0,
        full_burst_bonus=1.0,
        element_multiplier=1.1,
        damage_taken_up=0.1,
    )
    base_damage = 2000 * 1.5 - 500 * 1.2
    major_modifier = 1 + 0.5 + 1.0 + 1.0 * 0.5
    expected = base_damage * major_modifier * 1.1 * 1.1
    assert round(damage, 5) == round(expected, 5)
