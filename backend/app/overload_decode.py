"""Decode ShiftyPad overload options.

Each equipped gear slot carries up to three overload options as
`{slot}_equip_option{1,2,3}_id` in GetUserCharacterDetails. The id encodes the
effect and its roll: 700 + TT (effect type, 2 digits) + LL (level 1..15, 2
digits) - e.g. 7000811 is effect type 8 at level 11. Confirmed by pairing the
raw ids against ShiftyPad's parsed overload lines across 77 of Fienn's units
(2026-07-19). Value and effect name are resolved in later helpers.
"""


import collections
import logging

logger = logging.getLogger(__name__)

# An overload option rolls at level 1..15; anything else means a bad decode.
MIN_LEVEL, MAX_LEVEL = 1, 15


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
    scraped ShiftyPad roster - see stat_assembly's `load_stat_tables`. That
    roster only rolled some of the 15 levels per type, so a level it never
    measured is filled from the type's endpoints: each type is an arithmetic
    progression in level, and treating it as one reproduces every measured
    level to within the table's own 2-decimal rounding. The fill is
    cross-checked rather than merely smooth - types 8 and 9 share a curve, and
    9's unmeasured level 15 fills to 8's measured 14.63.

    Raises KeyError for a level outside the roll range or an effect type this
    roster never saw; callers that must survive another account's roster check
    `known_effect_type` first.
    """
    if not MIN_LEVEL <= level <= MAX_LEVEL:
        raise KeyError(f"overload level {level} is outside the {MIN_LEVEL}..{MAX_LEVEL} roll range")
    observed = tables["overload"]["values"][str(effect_type)]
    if str(level) in observed:
        return observed[str(level)]
    points = sorted((int(lv), v) for lv, v in observed.items())
    (lo, lo_value), (hi, hi_value) = points[0], points[-1]
    step = (hi_value - lo_value) / (hi - lo)
    return round(lo_value + step * (level - lo), 2)


def known_effect_type(tables, effect_type: int) -> bool:
    """Whether both a value curve and a display name exist for this effect type."""
    overload = tables["overload"]
    return str(effect_type) in overload["values"] and str(effect_type) in overload["type_name"]


def assemble_overload(tables, detail: dict) -> list[dict]:
    """ShiftyPad-style consolidated overload lines for one unit's four gear slots.

    Options of the same effect type sum across slots into one line (this is how
    ShiftyPad displays them). Types that fold into the base stat panel rather
    than the Equipment Effects list are dropped from the returned lines.

    An effect type absent from the reference tables is dropped with a warning
    instead of raising: only Fienn's roster was ever measured, and another
    account's unit must still assemble. The warning names the (type, level) so
    the tables can be completed from a real observation.
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
            if not known_effect_type(tables, etype):
                logger.warning(
                    "unknown overload effect type %s (level %s) - line dropped", etype, level
                )
                continue
            totals[etype] += overload_value(tables, etype, level)
    return [{"name": names[str(t)], "value": round(v, 2)} for t, v in totals.items()]
