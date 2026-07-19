"""Decode ShiftyPad overload options.

Each equipped gear slot carries up to three overload options as
`{slot}_equip_option{1,2,3}_id` in GetUserCharacterDetails. The id encodes the
effect and its roll: 700 + TT (effect type, 2 digits) + LL (level 1..15, 2
digits) - e.g. 7000811 is effect type 8 at level 11. Confirmed by pairing the
raw ids against ShiftyPad's parsed overload lines across 77 of Fienn's units
(2026-07-19). Value and effect name are resolved in later helpers.
"""


import collections


def decode_option(option_id: int) -> tuple[int, int] | None:
    """`(effect_type, level)` for one overload option, or None for an empty slot."""
    s = str(option_id)
    if len(s) != 7 or not s.startswith("700"):
        return None
    return int(s[3:5]), int(s[5:7])


_SLOTS = ("head", "torso", "arm", "leg")


def overload_value(tables, effect_type: int, level: int) -> float:
    """Percent an overload option of this effect type and roll grants.

    Values come from `tables["overload"]`, fitted per (type, level) against the
    scraped ShiftyPad roster - see stat_assembly's `load_stat_tables`. Only the
    (type, level) pairs that actually occur in that roster are present; an
    unobserved level raises KeyError rather than returning a guessed number.
    """
    return tables["overload"]["values"][str(effect_type)][str(level)]


def assemble_overload(tables, detail: dict) -> list[dict]:
    """ShiftyPad-style consolidated overload lines for one unit's four gear slots.

    Options of the same effect type sum across slots into one line (this is how
    ShiftyPad displays them). Types that fold into the base stat panel rather
    than the Equipment Effects list are dropped from the returned lines.
    """
    folded = set(tables["overload"]["base_stat_folded"])
    names = tables["overload"]["type_name"]
    totals: dict[int, float] = collections.defaultdict(float)
    for slot in _SLOTS:
        for n in (1, 2, 3):
            dec = decode_option(detail.get(f"{slot}_equip_option{n}_id", 0))
            if dec is None:
                continue
            etype, level = dec
            if etype in folded:
                continue
            totals[etype] += overload_value(tables, etype, level)
    return [{"name": names[str(t)], "value": round(v, 2)} for t, v in totals.items()]
