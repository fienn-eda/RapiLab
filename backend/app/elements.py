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


# beaten element -> the attacker that beats it. Derived from _STRONG_AGAINST
# rather than written out, so the two can never disagree.
_WEAK_TO = {beaten: attacker for attacker, beaten in _STRONG_AGAINST.items()}


def weakness_of(boss_element: str) -> str:
    """The attacker element that holds advantage over `boss_element`.

    The boss's "weakness" in the UI's language: the element a player fields to
    break an elemental-interrupt gimmick.
    """
    if boss_element not in _WEAK_TO:
        raise KeyError(f"unknown element: {boss_element!r}")
    return _WEAK_TO[boss_element]


# 5속성의 이름. 순환에서 유도한다 - 목록을 따로 적으면 순환이 바뀌는 날 둘이
# 어긋나고, 어긋난 쪽이 검증에 쓰이면 없는 속성이 통과한다.
ELEMENTS = frozenset(_STRONG_AGAINST)
