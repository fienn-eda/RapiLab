"""NIKKE elemental advantage.

Verified cycle (nikke.gg/code and the Fandom wiki, not assumed): each element
is strong against exactly one other and deals a +10% bonus when attacking it.

    Water > Fire > Wind > Iron > Electric > Water

Element names match the api.dotgg.gg spelling: Fire/Water/Wind/Iron/Electric.
"""

ELEMENT_ADVANTAGE_BONUS = 0.1

# attacker element -> the element it is strong against
_STRONG_AGAINST = {
    "Water": "Fire",
    "Fire": "Wind",
    "Wind": "Iron",
    "Iron": "Electric",
    "Electric": "Water",
}


def element_multiplier(attacker_element: str, boss_element: str) -> float:
    if attacker_element not in _STRONG_AGAINST or boss_element not in _STRONG_AGAINST:
        raise KeyError(f"unknown element: {attacker_element!r} / {boss_element!r}")
    if _STRONG_AGAINST[attacker_element] == boss_element:
        return 1 + ELEMENT_ADVANTAGE_BONUS
    return 1.0
