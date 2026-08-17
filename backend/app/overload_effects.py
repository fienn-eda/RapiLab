"""Converts ShiftyPad overload option values into permanent, self-scoped Effects.

Fienn confirmed overload values are additive on top of the base stat shown
in the character info tab (not already folded in), so these are modeled as
ordinary percentage-bonus Effects with duration=None (always active).

All eight stats in NAME_TO_STAT now reach damage: crit rate and the two crit /
charge damage buckets through `calculate_damage`, charge speed and max ammo
through `attack_rate` (charge cadence and magazine size), and hit rate through
`accuracy.core_hit_rate` on an encounter that sets a core diameter.

`other_elemental_bonus` is the one with a gate rather than a consumer problem:
`calculate_damage` pays it only when the holder actually has elemental
advantage, so a big roll is worth exactly zero against a same-element boss.
Cinderella: Crystal Wave is Iron and the calibration boss is Iron, which makes
her 90.01% line inert there (measured 2026-08-17).
"""
from app.effects import Effect
from app.overload_decode import (GEAR_SLOTS, MAX_LEVEL,
                                 charge_speed_percent_from_lines, overload_value)

NAME_TO_STAT = {
    "공격력 증가": "atk_percent",
    "우월코드 대미지 증가": "other_elemental_bonus",
    "크리티컬 대미지 증가": "other_critical_damage_sources",
    "크리티컬 확률 증가": "crit_rate",
    "차지 대미지 증가": "charge_damage_bonus",
    "차지 속도 증가": "charge_speed_percent",
    "최대 장탄 수 증가": "max_ammo_percent",
    "명중률 증가": "hit_rate",
}


def max_charge_speed_percent(tables) -> float:
    """The most charge speed overload alone can grant: a top roll on every slot.

    Nothing here is written down. A gear slot carries at most one line of a
    given effect (no unit in three synced accounts has two), the roll ladder
    tops out at level 15 in the committed tables, and the grouping is the rule
    above - so a re-fitted table or another slot moves this number without an
    edit. Four slots of 6.09 sum to 24.36 and group to 24.

    Raises KeyError if the tables carry no charge-speed effect type, which would
    mean the roster decoder could not name the option either.
    """
    for effect_type, name in tables["overload"]["type_name"].items():
        if NAME_TO_STAT.get(name) != "charge_speed_percent":
            continue
        top_roll = overload_value(tables, int(effect_type), MAX_LEVEL)
        return charge_speed_percent_from_lines([top_roll] * len(GEAR_SLOTS))
    raise KeyError("the overload tables carry no charge-speed effect type")


def max_atk_percent(tables) -> float:
    """The most ATK overload alone can grant: a top roll on every gear slot.

    Same shape as max_charge_speed_percent and for the same reason - nothing
    here is written down, so a re-fitted table moves this number without an
    edit. The difference is the arithmetic: charge speed rounds per roll before
    the frame grid sees it, while ATK is used exactly as displayed (see
    granted_percent), so this is a plain sum.

    Raises KeyError if the tables carry no ATK effect type.
    """
    for effect_type, name in tables["overload"]["type_name"].items():
        if NAME_TO_STAT.get(name) != "atk_percent":
            continue
        return overload_value(tables, int(effect_type), MAX_LEVEL) * len(GEAR_SLOTS)
    raise KeyError("the overload tables carry no ATK effect type")


def granted_percent(option, stat):
    """What this overload line GRANTS, which for charge speed is not what it shows.

    Charge speed rounds each same-valued group of rolls to a whole percent before
    the frame grid sees it, so a display of 9.26% grants 9 - measured on Prika,
    whose single 4.92% roll makes a 1.00-sec charge 57 frames rather than the 58
    the raw sum floors to (docs/measurements/prika-charge.md). Every other
    overload stat is used as displayed: no measurement says they round, and
    blablalink shows their exact sums.

    With no lines the total is all there is, and rounding IT is exactly the same
    rule whenever every roll was the same value - which includes the single-roll
    case, the common one. It can differ only for mixed rolls: 4.63 + 4.63 + 4.33
    grants 9 + 4 = 13 while its 13.59 total rounds to 14. So this is the closest
    the app can get without a re-sync, not a second rule.
    """
    if stat != "charge_speed_percent":
        return option.value
    lines = getattr(option, "lines", None)
    if lines:
        return charge_speed_percent_from_lines(line.value for line in lines)
    return float(round(option.value))


def overload_options_to_effects(overload_options, source_slug):
    effects = []
    for option in overload_options:
        stat = NAME_TO_STAT.get(option.name)
        if stat is None:
            raise ValueError(f"unknown overload option: {option.name}")
        effects.append(
            Effect(
                stat=stat,
                value=granted_percent(option, stat) / 100,
                scope="self",
                duration=None,
                source_slug=source_slug,
            )
        )
    return effects
