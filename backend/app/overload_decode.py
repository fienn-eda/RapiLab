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


# The four gear slots overload rolls on. One line of a given effect per slot,
# so the slot count is also the most lines any one option can carry.
GEAR_SLOTS = ("head", "torso", "arm", "leg")


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


def charge_speed_percent_from_lines(values) -> float:
    """The charge speed these overload LINES actually grant, in percent.

    Lines of the same roll sum first, and each of those groups rounds to a whole
    percent - so three lines of 4.63 / 4.63 / 4.33 grant 9 + 4 = 13%, not the
    13.59% they add up to and not the 5 + 5 + 4 = 14% that rounding each line on
    its own would give. Grouping can cost the player a point exactly as here,
    because 4.63 rounds up alone and 9.26 rounds down together.

    Confirmed by Prika, whose single 4.92% line makes a 1.00-sec charge 57
    frames rather than the 58 the raw sum floors to - 6.22 sigma, with her pause
    reading the matching 22 frames independently
    (docs/measurements/prika-charge.md). Reported by arca.live/b/nikketgv/169159561.

    This is charge speed ONLY. No measurement says an ATK or crit overload line
    rounds the same way, and blablalink displays their exact sums, so applying
    it there would be inventing a rule.

    `round` is banker's rounding, which differs from round-half-up on a group
    summing to exactly x.5. The one such group the 15 roll values can make is
    3.75 twice, and both conventions send 7.5 to 8 - so the choice is currently
    unobservable rather than decided.
    """
    grouped: dict[float, float] = collections.defaultdict(float)
    for value in values:
        grouped[round(value, 2)] += value
    return float(sum(round(total) for total in grouped.values()))


def assemble_overload(tables, detail: dict) -> list[dict]:
    """ShiftyPad-style consolidated overload lines for one unit's four gear slots.

    Options of the same effect type sum across slots into one line (this is how
    ShiftyPad displays them), and `lines` keeps the per-slot rolls that sum was
    made of. The display total is what blablalink shows and what the roster form
    edits; the lines are what `charge_speed_percent_from_lines` needs, since a
    total alone cannot be decomposed back into the rolls that produced it.

    Types that fold into the base stat panel rather than the Equipment Effects
    list are dropped from the returned lines.

    An effect type absent from the reference tables is dropped with a warning
    instead of raising: only Fienn's roster was ever measured, and another
    account's unit must still assemble. The warning names the (type, level) so
    the tables can be completed from a real observation.
    """
    folded = set(tables["overload"]["base_stat_folded"])
    names = tables["overload"]["type_name"]
    totals: dict[int, float] = collections.defaultdict(float)
    lines: dict[int, list[dict]] = collections.defaultdict(list)
    for slot in GEAR_SLOTS:
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
            value = overload_value(tables, etype, level)
            totals[etype] += value
            lines[etype].append({"slot": slot, "value": value})
    return [{"name": names[str(t)], "value": round(v, 2), "lines": lines[t]}
            for t, v in totals.items()]
