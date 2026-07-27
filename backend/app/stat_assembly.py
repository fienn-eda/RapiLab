"""Assemble a NIKKE's solo-raid (level 400) stats from investment data.

Solo raid normalizes every account to character level 400, so the deck builder
needs level-400 ATK and HP. blablalink does not serve those - ShiftyPad computes
it in the browser - and scraping it costs one page load per unit. Computing it
instead is what lets a roster be read from the API alone, which is the
precondition for syncing a roster we cannot scrape (i.e. anyone else's).

THE MODEL (reproduces all 159 collected units exactly)

    atk = base[class][level] * (1 + 0.02*grade) * (1 + 0.02*core)
          + grade*grade_attack
          + affinity_flat * (1 + 0.02*core)
          + core*core_flat_atk(unit)
          + extra_flat

The two breakthrough terms MULTIPLY - grade 3 with core 1 measures 1.0812, not
the 1.08 an additive model predicts. This also identifies `grade_ratio=200` in
the game tables as "2% per step", which earlier research had recorded as
unknown. Affinity is NOT part of the GRADE step (units sharing a grade but
differing in affinity all measure exactly 1.02) but it IS part of the core step -
each core is worth 2% of the affinity bonus as well as 2% of base.

That last term was found on 2026-07-25 and is what the model had been missing.
Adding affinity outside the multiplier still reproduced all 159 units, because it
was absorbed into the per-core flats - which worked only because every cored unit
inside a fitted group happens to share one affinity level. Two things gave it
away: three units (Vesti, Rosanna, Nero) carried per-unit rows recorded as
unexplained, and they are exactly the cored units at affinity 10 where their class
row was fitted at 30; and four Pilgrim/MISSILIS Supporters read off ShiftyPad at
affinities 20-40 disagreed by up to 22 per core under the old reading and agree to
0.67 under this one. Putting affinity in its place deleted those three rows AND
the OVERSPEC tier (also affinity in disguise: every cored OVERSPEC unit sits at
affinity 40) and left ATK needing one Pilgrim row and HP needing none.

`extra_flat` is assembled by the caller from the helpers below - corporation_atk,
equipment_atk, cube_atk and collectible_atk, but NOT affinity_atk, which travels
separately for the reason above. It is deliberately NOT defaulted to a guess, so
an un-modelled unit reads as obviously wrong rather than plausibly wrong.

WHAT IS NOT YET DERIVED

Why a Pilgrim is worth ~10 more ATK per core than everyone else, and why the
per-core flats are what they are rather than something the game tables state -
they are still fitted, not read off a table. HP is modelled the same way (see the
HP section below) and also reproduces all 159; DEF is not, as no caller reads it.
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


def core_scale(core: int) -> float:
    """What one core step scales, for the terms it reaches beyond base.

    The affinity bonus is one of them; grade's step is not (units sharing a grade
    but differing in affinity all measure exactly 1.02 for the grade term).
    """
    return 1 + BREAKTHROUGH_STEP * core


# Flat ATK per core, on top of the 2% core step above. The stat_enhance table
# lists core_attack = 200 for every class, but that value does not reproduce a
# single measured unit; these do. Read off ShiftyPad's core screen, where each
# extra core is worth a fixed amount at a fixed level: an Attacker (Brid) gains
# 2,034 per core at level 400 and 6,950 at 663, and subtracting the 2% step
# (base * 0.02 * 1.06) leaves ~119 at BOTH levels - so the remainder is flat and
# level-independent. Refitted 2026-07-25 across every cored unit of the class,
# once affinity moved inside the core step (see `assemble_atk`); the numbers each
# dropped by 0.02 * that group's affinity, which is what they had been absorbing.
CORE_FLAT_ATK = {"Attacker": 86.152, "Supporter": 85.992, "Defender": 85.968}

# Pilgrims are worth about 10 more per core than their class. Measured on eight
# ground-truth units (five Attackers, three Defenders) with no counter-example.
#
# Supporter is NOT one of them: no cored Pilgrim Supporter exists in the ground
# truth, and reading four Supporters off ShiftyPad the same way (Grave, Dorothy,
# Nayuta - Pilgrims - plus Naga, a MISSILIS Supporter) puts all four in one
# cluster 0.67 wide. Whatever Pilgrim does for an Attacker (+9.95) or a Defender
# (+10.05), it does nothing measurable for a Supporter, so this row repeats the
# class value rather than leaving the combination unmeasured.
CORE_FLAT_ATK_PILGRIM = {"Attacker": 96.151, "Defender": 96.022,
                         "Supporter": CORE_FLAT_ATK["Supporter"]}

# There is no OVERSPEC tier. It looked like one because every cored OVERSPEC unit
# in the ground truth sits at affinity 40 while the class rows were fitted on
# affinity 30 - so the gap it appeared to open was affinity's core scaling in
# disguise. Refitting with affinity in its proper place puts OVERSPEC Attackers at
# 86.119 against 86.152 for everyone else, i.e. on the same row.


class UnmeasuredStat(KeyError):
    """A stat this account needs was never measured, so no honest value exists.

    Distinct from the KeyErrors that mean "the caller passed something bogus":
    this one is a gap in the ground truth, and the only account that can trigger
    it is one that happens to own a unit nobody has measured. A caller assembling
    a whole roster catches it to drop that ONE unit rather than fail the sync -
    see roster_assembly.assemble_roster. Subclasses KeyError so existing handlers
    keep working.
    """


def core_flat_atk(character_class: str, *, corporation: str | None = None) -> float:
    """Flat ATK each core is worth for this unit: a Pilgrim row over a class row.

    There used to be a third, per-unit row for Vesti, Rosanna and Nero, recorded as
    unexplained. They are explained: they are the only cored units in the ground
    truth at affinity 10 where their class row was fitted at 30, and once affinity
    scales with the core step (`assemble_atk`) they land on the class value within
    0.01. No unit needs an override any more.
    """
    if character_class not in CORE_FLAT_ATK:
        raise KeyError(
            f"no core flat for class {character_class!r}; have {sorted(CORE_FLAT_ATK)}"
        )
    table = CORE_FLAT_ATK_PILGRIM if corporation == "PILGRIM" else CORE_FLAT_ATK
    try:
        return table[character_class]
    except KeyError:
        # Every class is covered for both tiers today, so this is reachable only
        # by a class the tables have never seen. Falling back would be wrong by
        # ~10 per core, so say so rather than answer plausibly.
        raise UnmeasuredStat(
            f"core flat ATK for a {corporation} {character_class} was never measured"
        ) from None


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
    # The affinity table's floor is level 1, which yields a zero bonus - clamp
    # rather than let level 0 (or a raw missing-field default of 0) crash.
    affinity_level = max(affinity_level, 1)
    column = _AFFINITY_ATK_COLUMN[character_class]
    for row in tables["affinity"]:
        if row["attractive_level"] == affinity_level:
            return row[column]
    raise KeyError(f"no affinity row for level {affinity_level}")


def corporation_atk(tables: dict[str, Any], corporation: str, research_ranks: dict[str, int]) -> int:
    """Flat ATK from the account's corporation research rank.

    Account-wide, not per unit: two otherwise identical units of different
    corporations differ here. `research_ranks` maps research tid -> rank, as
    returned by GetUserProfileOutpostInfo.recycle_room_researches. That payload
    omits rows the account never researched, so a missing tid is rank 0.
    """
    tid = CORPORATION_RESEARCH_TID[corporation]
    rank = research_ranks.get(tid, 0)
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


# A favorite item (애장품) is the SSR upgrade of an SR collectible and is priced
# as "collectible at max level" regardless of its own level. Its tid is in the
# 2xxxxx block; ordinary collectibles are 1xxxxx. This doubles as the ownership
# signal for a unit's signature form.
FAVORITE_ITEM_TID_BASE = 200000


def cube_atk(tables: dict[str, Any], cube_level: int) -> int:
    """Flat ATK from the equipped harmony cube.

    Cube ATK depends only on level, not on which cube: units wearing different
    cubes at the same level measure the same contribution.
    """
    if cube_level <= 0:
        return 0
    return tables["resilience_cube"]["atk"][cube_level - 1]


def _collectible_curve(tables: dict[str, Any], item_tid: int, stat: str) -> list[int]:
    """The stat curve of THIS collectible, not of collectibles in general.

    An R collectible is worth less than half an SR one at the same level (4,736
    vs 9,688 ATK at the top), so reading one curve for every tid over-credits
    every R holder. `collectible_sample` is the SR curve and stays the fallback
    for a tid the committed table does not know - the same shape the effect
    resolver uses, and the value the model was fitted against.
    """
    record = tables.get("collectibles", {}).get(str(item_tid))
    if record is None:
        return tables["collectible_sample"][stat]
    return record[stat]


def collectible_atk(tables: dict[str, Any], item_tid: int, item_level: int) -> int:
    """Flat ATK from the equipped collectible or favorite item."""
    if not item_tid:
        return 0
    curve = _collectible_curve(tables, item_tid, "atk")
    if item_tid >= FAVORITE_ITEM_TID_BASE:
        # Measured: four units holding a favorite item at level 2 all contribute
        # 9,688 - the collectible curve's top entry, not its level-2 entry. The
        # game's own favorite-item records agree: their curve is flat at that
        # value across all three of their levels.
        return curve[-1]
    if item_level <= 0:
        # A LEVEL-0 COLLECTIBLE IS EQUIPPED - it just carries no stat yet. Its
        # SKILL is already active (Fienn read all nine of his level-0 holders
        # in-game, 2026-07-27: Helm: Aquamarine's +10.22% core damage and the
        # rest, exactly the ladder's first rung), while its ATK/HP start at
        # level 1. The curve does have an entry at index 0, and crediting it
        # breaks 31 of the 159 measured units by exactly that entry (3,029 for
        # SR, 638 for R) - so the array's index 0 is not a level-0 stat.
        #
        # Equipped-vs-empty is answered by the TID, never by the level: an empty
        # slot reports tid 0. `collectible_effects` keys on the tid for that
        # reason; the two functions differ because the two axes really differ.
        return 0
    return curve[item_level]


def owns_favorite_item(item_tid: int) -> bool:
    """Whether this unit's collectible slot holds a favorite item (애장품)."""
    return item_tid >= FAVORITE_ITEM_TID_BASE


# --- HP model -----------------------------------------------------------------
#
# HP mirrors ATK's shape - base curve * breakthrough multiplier, plus a per-grade
# and per-core flat, plus the same assembled flat term - and every constant below
# is DERIVED against measured raid400_hp for all 159 collected units (fit closes
# at 159/159, worst |delta| 0.77, same tolerance the ATK model meets). Two things
# differ from ATK and were settled by the fit, not assumed:
#
#   * Account research: the Corporation research rows carry ATK, not HP (their hp
#     column is 0). HP research comes from the Personal (account-wide) and
#     Class-specific rows instead - see research_hp. It depends on class, not
#     corporation.
#   * Per-core flat tiers: HP does NOT split Pilgrim from OVERSPEC the way ATK
#     does - both measure the same per-core HP - so there is one OVERSPEC tier
#     that also covers Pilgrims, not two rows.
#
# Equipment HP rounds halves UP, decisively: 70 of the collected gear pieces land
# their HP bonus exactly on .5, and only half-up reproduces all 159 (half-even
# closes 145, floor 121, ceil 96). The spec's earlier 24590.5 -> 24590 note was a
# full-stat display, not this per-piece bonus.


def base_hp(tables: dict[str, Any], character_class: str, level: int) -> int:
    """Base HP before any investment - class and level alone, like base_atk.

    Class-uniform: two Attackers' full hp curves are byte-identical, so three
    class curves cover the roster. Level 1..1200 under classes[c]["hp"].
    """
    try:
        curve = tables["classes"][character_class]["hp"]
    except KeyError:
        raise KeyError(
            f"no base stat curve for class {character_class!r}; "
            f"have {sorted(tables['classes'])}"
        ) from None
    if not 1 <= level <= len(curve):
        raise ValueError(f"level {level} outside the table's 1..{len(curve)}")
    return curve[level - 1]


# Flat HP per core, on top of the 2% core step. Like ATK's per-core flat, the
# stat_enhance table's core_hp = 200 does not reproduce a single unit; these,
# refitted 2026-07-25 with affinity inside the core step (see `assemble_hp`), do.
#
# HP needs no corporation row at all. The OVERSPEC/Pilgrim tier that used to sit
# here was affinity in disguise - every cored OVERSPEC unit in the ground truth is
# at affinity 40 while the class rows were fitted at 30 - and once affinity scales
# properly, class alone reproduces all 159 units (worst 0.87). ATK still needs a
# Pilgrim row; HP does not.
CORE_FLAT_HP = {"Attacker": 5610.022, "Supporter": 5474.792, "Defender": 5699.796}


def core_flat_hp(character_class: str) -> float:
    """Flat HP each core is worth for this unit - class alone settles it.

    Both the OVERSPEC/Pilgrim tier and the three per-unit rows that used to live
    here were affinity in disguise; see `core_flat_atk`. HP, unlike ATK, needs no
    corporation row at all once affinity is scaled properly.
    """
    if character_class not in CORE_FLAT_HP:
        raise KeyError(
            f"no core flat for class {character_class!r}; have {sorted(CORE_FLAT_HP)}"
        )
    return CORE_FLAT_HP[character_class]


# Account research that adds HP: the Personal (account-wide) row and the
# Class-specific row. The Corporation rows carry ATK, not HP - their hp column is
# 0 - which is why HP research keys on class where ATK keys on corporation.
PERSONAL_RESEARCH_TID = "1001"
CLASS_RESEARCH_TID = {"Attacker": "1101", "Defender": "1102", "Supporter": "1103"}


def research_hp(tables: dict[str, Any], character_class: str, research_ranks: dict[str, int]) -> int:
    """Flat HP from the account's Personal + Class research ranks.

    Account-wide Personal research plus the unit's class research; both are 750/
    450 per rank in the table and confirmed against measured HP (an ungeared,
    coreless, grade-0 Attacker's whole HP-over-base residual is affinity + this).
    `research_ranks` maps research tid -> rank, as returned by
    GetUserProfileOutpostInfo.recycle_room_researches, which omits rows the
    account never researched - a missing tid is rank 0.
    """
    total = 0
    for tid in (PERSONAL_RESEARCH_TID, CLASS_RESEARCH_TID[character_class]):
        rank = research_ranks.get(tid, 0)
        per_rank = next(r["hp"] for r in tables["recycle_research"] if str(r["id"]) == tid)
        total += rank * per_rank
    return total


_AFFINITY_HP_COLUMN = {
    "Attacker": "attacker_hp_rate",
    "Supporter": "supporter_hp_rate",
    "Defender": "defender_hp_rate",
}


def affinity_hp(tables: dict[str, Any], character_class: str, affinity_level: int) -> int:
    """Flat HP from affinity rank, the HP sibling of affinity_atk.

    The column is named `..._hp_rate` but holds a flat value, the same as the ATK
    column; confirmed by fit against measured HP.
    """
    # The affinity table's floor is level 1, which yields a zero bonus - clamp
    # rather than let level 0 (or a raw missing-field default of 0) crash.
    affinity_level = max(affinity_level, 1)
    column = _AFFINITY_HP_COLUMN[character_class]
    for row in tables["affinity"]:
        if row["attractive_level"] == affinity_level:
            return row[column]
    raise KeyError(f"no affinity row for level {affinity_level}")


def equipment_hp(
    tables: dict[str, Any],
    equip_tid: int,
    equip_level: int,
    *,
    equip_corporation_type: int = 0,
    unit_corporation: str | None = None,
) -> int:
    """Flat HP from one equipped gear piece, the HP sibling of equipment_atk.

    Same 10%-per-level and +30% own-corporation bonuses, added on the base rather
    than compounded, with the bonus rounded then added. HP rounds halves UP, the
    same rule ATK uses: of the collected roster 70 pieces land their HP bonus on
    .5 and only half-up reproduces all 159 units.
    """
    row = next((r for r in tables["equipment"] if r["id"] == equip_tid), None)
    if row is None:
        return 0
    base = next((s["stat_value"] for s in row["stat"] if s["stat_type"] == "Hp"), 0)
    matches = (
        unit_corporation is not None
        and equip_corporation_type == CORPORATION_EQUIP_TYPE.get(unit_corporation)
    )
    bonus = CORPORATION_MATCH_BONUS * matches + EQUIP_LEVEL_STEP * equip_level
    return base + math.floor(base * bonus + 0.5)


def cube_hp(tables: dict[str, Any], cube_level: int) -> int:
    """Flat HP from the equipped harmony cube, the HP sibling of cube_atk."""
    if cube_level <= 0:
        return 0
    return tables["resilience_cube"]["hp"][cube_level - 1]


def collectible_hp(tables: dict[str, Any], item_tid: int, item_level: int) -> int:
    """Flat HP from the equipped collectible or favorite item, HP sibling of
    collectible_atk. A favorite item is priced at the curve maximum."""
    if not item_tid:
        return 0
    curve = _collectible_curve(tables, item_tid, "hp")
    if item_tid >= FAVORITE_ITEM_TID_BASE:
        return curve[-1]
    if item_level <= 0:
        return 0
    return curve[item_level]


def assemble_hp(
    tables: dict[str, Any],
    *,
    character_class: str,
    level: int,
    grade: int,
    core: int,
    affinity_flat_hp: float = 0.0,
    extra_flat_hp: float = 0.0,
) -> float:
    """Solo-raid HP for one unit, the HP sibling of assemble_atk. DEF is not
    modelled - the simulator never reads it. `extra_flat_hp` is assembled by the
    caller from research_hp, equipment_hp, cube_hp and collectible_hp; affinity is
    passed separately because it scales with the core step (see assemble_atk).
    """
    enhance = tables["classes"][character_class]["stat_enhance"]
    scaled = base_hp(tables, character_class, level) * breakthrough_multiplier(grade, core)
    flat = grade * enhance["grade_hp"] + affinity_flat_hp * core_scale(core)
    if core:
        flat += core * core_flat_hp(character_class)
    return scaled + flat + extra_flat_hp


def assemble_atk(
    tables: dict[str, Any],
    *,
    character_class: str,
    level: int,
    grade: int,
    core: int,
    corporation: str | None = None,
    affinity_flat: float = 0.0,
    extra_flat: float = 0.0,
) -> float:
    """Solo-raid ATK for one unit. `extra_flat` covers what is not yet derived.

    AFFINITY IS NOT PART OF `extra_flat`. It scales with the core step - each core
    is worth 2% of the affinity bonus as well as 2% of base - so it arrives
    separately and gets multiplied by `core_scale`. Reading it as a plain flat
    addition is what made three units (Vesti, Rosanna, Nero) look like unexplained
    outliers and made an OVERSPEC tier appear where there is none: those are the
    units and groups whose affinity differs from the row they were fitted against.

    `corporation` only selects the per-core flat, so a unit without cores needs it
    no more than it needs affinity.
    """
    enhance = tables["classes"][character_class]["stat_enhance"]
    scaled = base_atk(tables, character_class, level) * breakthrough_multiplier(grade, core)
    flat = grade * enhance["grade_attack"] + affinity_flat * core_scale(core)
    if core:
        flat += core * core_flat_atk(character_class, corporation=corporation)
    return scaled + flat + extra_flat
