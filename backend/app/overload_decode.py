"""Decode ShiftyPad overload options.

Each equipped gear slot carries up to three overload options as
`{slot}_equip_option{1,2,3}_id` in GetUserCharacterDetails. The id encodes the
effect and its roll: 700 + TT (effect type, 2 digits) + LL (level 1..15, 2
digits) - e.g. 7000811 is effect type 8 at level 11. Confirmed by pairing the
raw ids against ShiftyPad's parsed overload lines across 77 of Fienn's units
(2026-07-19). Value and effect name are resolved in later helpers.
"""


def decode_option(option_id: int) -> tuple[int, int] | None:
    """`(effect_type, level)` for one overload option, or None for an empty slot."""
    s = str(option_id)
    if len(s) != 7 or not s.startswith("700"):
        return None
    return int(s[3:5]), int(s[5:7])
