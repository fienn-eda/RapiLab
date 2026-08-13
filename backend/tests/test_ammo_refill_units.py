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


# "Activates when entering Full Burst. Affects all allies.", "Max Ammunition
# Capacity +5 round(s) for 10 sec.", "Reload 39.88% magazine(s)."
# (char_noir.json skills[1], lv10)
NOIR_RABBIT_TWINS_B = {
    "description_value_01": "5", "description_value_02": "10",
    "description_value_03": "39.88",
}
NOIR = {"rabbit_twins_b": NOIR_RABBIT_TWINS_B}

# "Affects all allies.", "Attack damage +10.13% for 10 sec.", "Reloads
# 33.26% magazine(s).", "Affects self.", "ATK +17.28% ... for 10 sec."
# (char_little-mermaid.json skills[2], lv10)
LITTLE_MERMAID_SIRENS_SONG = {
    "description_value_01": "10.13", "description_value_02": "10",
    "description_value_03": "33.26", "description_value_04": "17.28",
    "description_value_05": "10",
}
LITTLE_MERMAID = {"sirens_song": LITTLE_MERMAID_SIRENS_SONG}


def test_noir_reloads_the_whole_squad_on_full_burst_entry():
    grant = get_ammo_refill_grant("noir", NOIR)
    assert grant == {"percent": 39.88, "scope": "squad", "event": "full_burst_enter"}


def test_little_mermaid_reloads_the_whole_squad_at_her_own_burst():
    grant = get_ammo_refill_grant("little-mermaid", LITTLE_MERMAID)
    assert grant == {"percent": 33.26, "scope": "squad", "event": "own_burst"}


def test_a_deck_with_noir_refills_every_seat():
    """Not a damage assertion - the point is that four other units' shot
    timelines receive a refill they could not have declared themselves."""
    from app.raid_simulator import resolve_ammo_refills

    deck = [
        {"slug": "noir", "ammo_refill_grant": get_ammo_refill_grant("noir", NOIR)},
        {"slug": "liberalio"},
        {"slug": "scarlet-black-shadow"},
    ]
    refills = resolve_ammo_refills(deck, [{"type": "full_burst_start", "time": 5.0}])
    assert set(refills) == {"noir", "liberalio", "scarlet-black-shadow"}
