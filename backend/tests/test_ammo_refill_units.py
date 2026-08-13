"""The two self-scoped reload clauses that had no engine shape until the
refill primitive: Tove's Favorite Item shot counter and Asuka's one-shot burst
grant.

Each asserts the SHAPE the encoding declares (an AmmoRefund / a grant dict),
not a damage number - a damage delta measured against the same code that
produces it proves nothing.
"""
from app.attack_rate import AmmoRefund
from app.skill_rules.registry import get_ammo_refill_grant, get_skill_ammo_refund

# "Activates after 10 normal attack(s)", "Reload 5.31% of the magazine",
# "Max Ammunition Capacity +2", "stacks up to 3 time(s)", "lasts for 5 sec",
# "Critical Damage +5.24%", "for 5 sec" (char_tove-nikke.json dollskills[0], lv10)
TOVE_SIGNATURE_EMERGENCY_CRAFTED_BULLETS = {
    "description_value_01": "10", "description_value_02": "5.31",
    "description_value_03": "2", "description_value_04": "3",
    "description_value_05": "5", "description_value_06": "5.24",
    "description_value_07": "5",
}
TOVE_SIGNATURE = {"emergency_crafted_bullets": TOVE_SIGNATURE_EMERGENCY_CRAFTED_BULLETS}

# "Effect 1: Normal Attack Damage Multiplier -40% for 9 sec", "Effect 2:
# Reloads 21% magazine(s)", "Effect 3: ATK +46.8%", "Effect 4: Attack Damage
# +36%", "Deals 6.62% of final ATK as additional damage"
# (char_asuka-shikinami-langley-wille.json skills[2], lv10, after the
# manifest's drop_tokens for the "Effect N" labels and repeated durations)
ASUKA_ANNIHILATION_STATE = {
    "description_value_01": "40", "description_value_02": "9",
    "description_value_03": "21", "description_value_04": "46.8",
    "description_value_05": "36", "description_value_06": "6.62",
}
ASUKA = {"annihilation_state": ASUKA_ANNIHILATION_STATE}


def test_tove_signature_reloads_a_percentage_every_ten_shots():
    refund, element = get_skill_ammo_refund("tove-signature", TOVE_SIGNATURE)
    assert refund == AmmoRefund(every_shots=10, percent=5.31)
    assert element is None


def test_tove_signature_hands_back_three_rounds_of_her_sixty():
    refund, _element = get_skill_ammo_refund("tove-signature", TOVE_SIGNATURE)
    assert refund.rounds_for(60) == 3


def test_tove_base_keeps_its_probability_roll_deferred():
    # "There is a 5% chance of activating when attacking" - the engine is
    # deterministic, so the base build stays out of _SKILL_AMMO_REFUNDS.
    assert get_skill_ammo_refund("tove", TOVE_SIGNATURE) is None


def test_asuka_reloads_a_fifth_of_her_magazine_at_her_own_burst():
    grant = get_ammo_refill_grant("asuka-shikinami-langley-wille", ASUKA)
    assert grant == {"percent": 21.0, "scope": "self", "event": "own_burst"}
