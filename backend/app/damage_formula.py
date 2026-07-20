"""Implements the NIKKE damage formula documented at https://nikke.gg/damage-formula/

Final Damage =
    Base Damage
    x Final ATK Modifiers   (= attack/skill coefficient x (1 + rare buffs))
    x Major Modifiers
    x Element Bonus Damage
    x Charge Damage
    x Damage Up
    x Damage Taken

Base Damage = (Base Attack x (1 + ATK%) + flat ATK) - (enemy DEF x (1 + DEF%) + flat DEF)

Critically, the attack/skill coefficient (`attack_coefficient`: normal-attack
% of ATK, or a skill's "X% of final ATK") multiplies Base Damage AS A WHOLE -
after defense is subtracted - not the ATK stat alone. Passing `atk` already
multiplied by the coefficient would mis-scale the defense subtraction and any
flat ATK, so callers must pass the raw summary ATK and the coefficient
separately.
"""


def _base_damage(atk, atk_percent, flat_atk, enemy_def, enemy_def_percent, flat_enemy_def):
    offense = atk * (1 + atk_percent) + flat_atk
    defense = enemy_def * (1 + enemy_def_percent) + flat_enemy_def
    return offense - defense


def _major_modifiers(
    crit_rate,
    other_critical_damage_sources,
    core_hit_bonus,
    other_core_damage_sources,
    full_burst_bonus,
    effective_range_bonus,
):
    # Expected-value crit: a hit crits with probability crit_rate, and a crit
    # adds (0.5 base + crit damage sources) to the major modifier. Averaged over
    # many hits that is crit_rate * (0.5 + sources). Crit damage sources are
    # therefore inert without any crit chance, matching the game.
    expected_crit_term = crit_rate * (0.5 + other_critical_damage_sources)
    return (
        1
        + expected_crit_term
        + core_hit_bonus
        + other_core_damage_sources
        + full_burst_bonus * 0.5
        + effective_range_bonus * 0.3
    )


def calculate_damage(
    atk,
    enemy_def,
    atk_percent=0.0,
    flat_atk=0.0,
    enemy_def_percent=0.0,
    flat_enemy_def=0.0,
    attack_coefficient=1.0,
    final_atk_modifier=0.0,
    crit_rate=0.0,
    other_critical_damage_sources=0.0,
    core_hit_bonus=0.0,
    other_core_damage_sources=0.0,
    full_burst_bonus=0.0,
    effective_range_bonus=0.0,
    element_multiplier=1.0,
    other_elemental_bonus=0.0,
    charge_damage_bonus=0.0,
    attack_damage_up=0.0,
    sustained_damage_up=0.0,
    true_damage_up=0.0,
    pierce_damage_up=0.0,
    damage_to_parts_up=0.0,
    shield_damage_up=0.0,
    projectile_explosion_damage_up=0.0,
    projectile_attachment_damage_up=0.0,
    damage_taken_up=0.0,
    distributed_damage_up=0.0,
):
    base_damage = _base_damage(
        atk, atk_percent, flat_atk, enemy_def, enemy_def_percent, flat_enemy_def
    )
    # "Final ATK modifiers" = the attack/skill coefficient (Final ATK damage of
    # Attack/Skill) x (1 + rare Final ATK modifier buffs). The coefficient
    # multiplies the whole Base Damage, i.e. AFTER defense is subtracted.
    final_atk_modifiers = attack_coefficient * (1 + final_atk_modifier)
    major_modifiers = _major_modifiers(
        crit_rate,
        other_critical_damage_sources,
        core_hit_bonus,
        other_core_damage_sources,
        full_burst_bonus,
        effective_range_bonus,
    )
    # "Superior Code Damage" only applies when the attacker actually holds
    # elemental advantage; element_multiplier is already that indicator
    # (1.1 with advantage, 1.0 without - see elements.py).
    has_element_advantage = element_multiplier > 1.0
    element_bonus_damage = element_multiplier + (
        other_elemental_bonus if has_element_advantage else 0.0
    )
    charge_damage = 1 + charge_damage_bonus
    damage_up = 1 + (
        attack_damage_up
        + sustained_damage_up
        + true_damage_up
        + pierce_damage_up
        + damage_to_parts_up
        + shield_damage_up
        + projectile_explosion_damage_up
        + projectile_attachment_damage_up
    )
    damage_taken = 1 + damage_taken_up + distributed_damage_up

    return (
        base_damage
        * final_atk_modifiers
        * major_modifiers
        * element_bonus_damage
        * charge_damage
        * damage_up
        * damage_taken
    )
