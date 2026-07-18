"""Assemble a NIKKE's solo-raid (level 400) stats from investment data.

Solo raid normalizes every account to character level 400, so the deck builder
needs level-400 ATK. blablalink does not serve that number - ShiftyPad computes
it in the browser - and scraping it costs one page load per unit. Computing it
instead is what lets a roster be read from the API alone, which is the
precondition for syncing a roster we cannot scrape (i.e. anyone else's).

WHAT IS DERIVED (the multiplier: measured against all 159 collected units, 0 mismatches)

    atk = base[class][level] * (1 + 0.02*grade) * (1 + 0.02*core)
          + core*core_attack + grade*grade_attack
          + extra_flat

The two breakthrough terms MULTIPLY - grade 3 with core 1 measures 1.0812, not
the 1.08 an additive model predicts. This also identifies `grade_ratio=200` in
the game tables as "2% per step", which earlier research had recorded as
unknown. Affinity does NOT belong to this multiplier: units sharing a grade but
differing in affinity (4 / 10 / 12 / 20) all measure exactly 1.02.

`extra_flat` is assembled by the caller from the helpers below - affinity_atk,
corporation_atk and equipment_atk - which together reproduce 59 of the 74
collected units that wear gear but no cube or collectible.

WHAT IS NOT YET DERIVED

Cube and collectible contributions (85 of the 159 collected units carry one or
both), and a shortfall on 15 gear-only units. Those 15 all come out slightly
HIGH and two of them wear no gear at all, so the gap is not in the equipment
model. `extra_flat` is deliberately NOT defaulted to a guess, so an
un-modelled unit reads as obviously wrong rather than plausibly wrong.
See docs/superpowers/specs/2026-07-18-stat-assembly-calculator-design.md.
"""
import json
import math
from pathlib import Path
from typing import Any

STAT_TABLES = (
    Path(__file__).resolve().parents[2] / "data" / "nikke-stat-tables" / "tables.json"
)

# Each breakthrough step (grade or core) is worth this share of base ATK. Named
# `grade_ratio` in the game tables, where it is stored as 200 = 2%.
BREAKTHROUGH_STEP = 0.02


def load_stat_tables(path: Path = STAT_TABLES) -> dict[str, Any]:
    """The committed snapshot of the public class curves and coefficients."""
    return json.loads(path.read_text(encoding="utf-8"))


def base_atk(tables: dict[str, Any], character_class: str, level: int) -> int:
    """Base ATK before any investment - a function of class and level alone.

    Base stats are uniform across characters of the same class, verified by
    diffing two Attackers' full curves, so three class curves cover the roster.
    """
    try:
        curve = tables["classes"][character_class]["attack"]
    except KeyError:
        raise KeyError(
            f"no base stat curve for class {character_class!r}; "
            f"have {sorted(tables['classes'])}"
        ) from None
    if not 1 <= level <= len(curve):
        raise ValueError(f"level {level} outside the table's 1..{len(curve)}")
    return curve[level - 1]


def breakthrough_multiplier(grade: int, core: int) -> float:
    """Grade and core each scale base ATK by 2% per step, multiplicatively."""
    return (1 + BREAKTHROUGH_STEP * grade) * (1 + BREAKTHROUGH_STEP * core)


# Which recycle-room research row ranks each corporation. Only PILGRIM and
# ABNORMAL are individually confirmed (their ranks differ from the rest, and
# PILGRIM units measure exactly rank*25); ELYSION / MISSILIS / TETRA all sit at
# the same rank on the account measured, so their tids are indistinguishable so
# far and are assigned in table order. Revisit if two of them ever diverge.
CORPORATION_RESEARCH_TID = {
    "ELYSION": "1201",
    "MISSILIS": "1202",
    "TETRA": "1203",
    "PILGRIM": "1204",
    "ABNORMAL": "1205",
}

_AFFINITY_ATK_COLUMN = {
    "Attacker": "attacker_attack_rate",
    "Supporter": "supporter_attack_rate",
    "Defender": "defender_attack_rate",
}


def affinity_atk(tables: dict[str, Any], character_class: str, affinity_level: int) -> int:
    """Flat ATK from affinity rank.

    The table column is named `..._rate` but holds a flat value, confirmed
    against the in-game additional-stats popup (rank 40 Attacker shows 2340,
    the cell verbatim). See capturedimages/README.md.
    """
    column = _AFFINITY_ATK_COLUMN[character_class]
    for row in tables["affinity"]:
        if row["attractive_level"] == affinity_level:
            return row[column]
    raise KeyError(f"no affinity row for level {affinity_level}")


def corporation_atk(tables: dict[str, Any], corporation: str, research_ranks: dict[str, int]) -> int:
    """Flat ATK from the account's corporation research rank.

    Account-wide, not per unit: two otherwise identical units of different
    corporations differ here. `research_ranks` maps research tid -> rank, as
    returned by GetUserProfileOutpostInfo.recycle_room_researches.
    """
    tid = CORPORATION_RESEARCH_TID[corporation]
    rank = research_ranks[tid]
    per_rank = next(r["attack"] for r in tables["recycle_research"] if str(r["id"]) == tid)
    return rank * per_rank


EQUIP_LEVEL_STEP = 0.10

# Gear made by the unit's own corporation is worth 30% more. Derived from
# measured leftovers rather than assumed: each pairing below is supported by
# several units and none conflicts. Type 0 is generic gear, which never matches.
CORPORATION_EQUIP_TYPE = {
    "ELYSION": 1,
    "MISSILIS": 2,
    "TETRA": 3,
    "PILGRIM": 4,
    "ABNORMAL": 7,
}
CORPORATION_MATCH_BONUS = 0.30


def equipment_atk(
    tables: dict[str, Any],
    equip_tid: int,
    equip_level: int,
    *,
    equip_corporation_type: int = 0,
    unit_corporation: str | None = None,
) -> int:
    """Flat ATK from one equipped gear piece at its upgrade level.

    Levelling adds 10% of the piece's own base ATK per level, confirmed on the
    in-game level-up screen across classes and slots (Attacker head 6014 -> +3007
    at LV.05; Defender arm 2551 -> +1276).

    Gear made by the unit's own corporation is worth another 30%, and the two
    bonuses ADD on the original base rather than compounding: a Defender wearing
    own-corporation T9 arms (table 1372) at LV.05 reads 2470 in game, which is
    1372 * 1.8, not the 1372 * 1.3 * 1.5 = 2675 that compounding would give.

    The **bonus** is rounded and then added, which is not the same as rounding
    the total: Defender arm at LV.05 shows 2551 + 1276 = 3827, whereas rounding
    2551 * 1.5 = 3826.5 would give 3826.

    Halves round UP, chosen by measurement: over the collected roster half-up
    reproduces 59 of 74 gear-only units against 55 for half-to-even, 45 for ceil
    and 43 for floor. Note the HP line of one capture reads 24590.5 -> 24590,
    which is not half-up; whether HP rounds differently is unresolved and does
    not matter here, since only ATK is consumed.

    The tid, not the tier, identifies the piece: a tier holds both class-specific
    and "All"-class variants whose stats differ.
    """
    row = next((r for r in tables["equipment"] if r["id"] == equip_tid), None)
    if row is None:
        return 0
    base = next((s["stat_value"] for s in row["stat"] if s["stat_type"] == "Atk"), 0)
    matches = (
        unit_corporation is not None
        and equip_corporation_type == CORPORATION_EQUIP_TYPE.get(unit_corporation)
    )
    bonus = CORPORATION_MATCH_BONUS * matches + EQUIP_LEVEL_STEP * equip_level
    return base + math.floor(base * bonus + 0.5)


def assemble_atk(
    tables: dict[str, Any],
    *,
    character_class: str,
    level: int,
    grade: int,
    core: int,
    extra_flat: float = 0.0,
) -> float:
    """Solo-raid ATK for one unit. `extra_flat` covers what is not yet derived."""
    enhance = tables["classes"][character_class]["stat_enhance"]
    scaled = base_atk(tables, character_class, level) * breakthrough_multiplier(grade, core)
    flat = core * enhance["core_attack"] + grade * enhance["grade_attack"]
    return scaled + flat + extra_flat
