"""Assemble a NIKKE's solo-raid (level 400) stats from investment data.

Solo raid normalizes every account to character level 400, so the deck builder
needs level-400 ATK. blablalink does not serve that number - ShiftyPad computes
it in the browser - and scraping it costs one page load per unit. Computing it
instead is what lets a roster be read from the API alone, which is the
precondition for syncing a roster we cannot scrape (i.e. anyone else's).

WHAT IS DERIVED (measured against all 159 collected units, mismatches: 0)

    atk = base[class][level] * (1 + 0.02*grade) * (1 + 0.02*core)
          + core*core_attack + grade*grade_attack
          + extra_flat

The two breakthrough terms MULTIPLY - grade 3 with core 1 measures 1.0812, not
the 1.08 an additive model predicts. This also identifies `grade_ratio=200` in
the game tables as "2% per step", which earlier research had recorded as
unknown. Affinity does NOT belong to this multiplier: units sharing a grade but
differing in affinity (4 / 10 / 12 / 20) all measure exactly 1.02.

WHAT IS NOT YET DERIVED

`extra_flat` - the flat contribution of gear, cube, collectible and affinity.
Its inputs are known (the API reports tier/level per slot, cube level,
collectible level, affinity level) but the tables that price them could not be
captured: ShiftyPad never requests the equipment or affinity tables in any flow
we could reach. Callers must pass it; it is deliberately NOT defaulted to a
guess, so an un-modelled unit reads as obviously wrong rather than plausibly
wrong. See docs/superpowers/specs/2026-07-18-stat-assembly-calculator-design.md.
"""
import json
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
