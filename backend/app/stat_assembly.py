"""Assemble a NIKKE's solo-raid (level 400) stats from investment data.

Solo raid normalizes every account to character level 400, so the deck builder
needs level-400 ATK and HP. blablalink does not serve those - ShiftyPad computes
it in the browser - and scraping it costs one page load per unit. Computing it
instead is what lets a roster be read from the API alone, which is the
precondition for syncing a roster we cannot scrape (i.e. anyone else's).

THE MODEL (reproduces all 159 collected units exactly)

    atk = base[class][level] * (1 + 0.02*grade) * (1 + 0.02*core)
          + core*core_flat_atk(unit) + grade*grade_attack
          + extra_flat

The two breakthrough terms MULTIPLY - grade 3 with core 1 measures 1.0812, not
the 1.08 an additive model predicts. This also identifies `grade_ratio=200` in
the game tables as "2% per step", which earlier research had recorded as
unknown. Affinity does NOT belong to this multiplier: units sharing a grade but
differing in affinity (4 / 10 / 12 / 20) all measure exactly 1.02.

`extra_flat` is assembled by the caller from the helpers below - affinity_atk,
corporation_atk, equipment_atk, cube_atk and collectible_atk. It is deliberately
NOT defaulted to a guess, so an un-modelled unit reads as obviously wrong rather
than plausibly wrong.

WHAT IS NOT YET DERIVED

Why the per-core flat varies between units of the same class - see
CORE_FLAT_ATK_BY_RESOURCE_ID. Pilgrims and the awakened Counters are worth more
per core, three further units are worth less, and the values themselves are
measured rather than read off a game table. HP is modelled the same way (see the
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


# Flat ATK per core, on top of the 2% core step above. The stat_enhance table
# lists core_attack = 200 for every class, but that value does not reproduce a
# single measured unit; these do. Read off ShiftyPad's core screen, where each
# extra core is worth a fixed amount at a fixed level: an Attacker (Brid) gains
# 2,034 per core at level 400 and 6,950 at 663, and subtracting the 2% step
# (base * 0.02 * 1.06) leaves ~119 at BOTH levels - so the remainder is flat and
# level-independent. Fitted across every cored unit of the class.
CORE_FLAT_ATK = {"Attacker": 118.95, "Supporter": 113.29, "Defender": 107.87}

# Pilgrims are worth about 20% more per core than their class. Measured on eight
# units (five Attackers, three Defenders) with no counter-example: every Pilgrim
# in the ground truth lands here and no unit of another corporation does.
#
# Supporter came later and from a different source (2026-07-25): no cored Pilgrim
# Supporter exists in the ground truth, so it was read off ShiftyPad by holding a
# unit at level 400 / grade 3 and stepping ONLY the core, which cancels affinity,
# equipment, cube, favorite item and research (scripts/solve_core_flat.py).
# Grave measures 1718 ATK per core across three independent spans (core 0->1,
# 0->2, 0->3) and Little Mermaid reproduces that delta to the digit, which is
# what 122.382 is: 1718 - base(Supporter, 400) * 0.02 * 1.06.
#
# Dorothy and Nayuta read 4.67 and 22.33 per core LOWER, and the reason is
# visible rather than guessed: their ATK and HP deficits independently correspond
# to the same offset in LEVEL steps (0.94/0.90 and 4.28/4.26 steps, where one
# level is worth 5.30 ATK and 159.00 HP per core). A differing per-core flat has
# no reason to make two stats agree on a level offset - so those two readings sat
# below level 400, not on a different value. Worth rereading to close it out; the
# residual it could move is 5 ATK per core, 0.015% of such a unit's ATK.
CORE_FLAT_ATK_PILGRIM = {"Attacker": 142.90, "Defender": 127.22,
                         "Supporter": 122.382}

# The awakened Counters - Rapi: Red Hood, Anis: Star and Neon: Vision Eye - land
# between their class and a Pilgrim. What marks them is the game's own
# `corporation_sub_type: OVERSPEC`, which the per-character stat file carries and
# an ordinary unit leaves empty. Every Pilgrim is OVERSPEC too, and worth more
# still, so the two are separate rows rather than one bonus.
CORE_FLAT_ATK_OVERSPEC = {"Attacker": 132.95, "Defender": 116.79}

# Units whose per-core flat is none of the above. Keyed by resource_id because
# that is what identifies a unit unambiguously.
#
# These three are NOT explained. Every scalar field of their CDN stat file was
# compared against their class peers' and none separates them: same base curves,
# same rarity, no sub_type, and stat_enhance_id is shared with units that measure
# the class value. They are measured, not derived.
CORE_FLAT_ATK_BY_RESOURCE_ID = {
    91: 94.22,    # Vesti
    280: 94.22,   # Rosanna
    380: 91.15,   # Nero
}


class UnmeasuredStat(KeyError):
    """A stat this account needs was never measured, so no honest value exists.

    Distinct from the KeyErrors that mean "the caller passed something bogus":
    this one is a gap in the ground truth, and the only account that can trigger
    it is one that happens to own a unit nobody has measured. A caller assembling
    a whole roster catches it to drop that ONE unit rather than fail the sync -
    see roster_assembly.assemble_roster. Subclasses KeyError so existing handlers
    keep working.
    """


def core_flat_atk(
    character_class: str,
    *,
    corporation: str | None = None,
    corporation_sub_type: str | None = None,
    resource_id: int | None = None,
) -> float:
    """Flat ATK each core is worth for this unit.

    A unit's own measured value wins over its corporation's, which wins over
    OVERSPEC, which wins over its class's - most units only have the class value.
    """
    if character_class not in CORE_FLAT_ATK:
        raise KeyError(
            f"no core flat for class {character_class!r}; have {sorted(CORE_FLAT_ATK)}"
        )
    if resource_id in CORE_FLAT_ATK_BY_RESOURCE_ID:
        return CORE_FLAT_ATK_BY_RESOURCE_ID[resource_id]
    # Corporation alone settles a Pilgrim: all eight measured are OVERSPEC, so a
    # caller that does not know the sub_type still gets the right answer.
    table = (
        CORE_FLAT_ATK_PILGRIM
        if corporation == "PILGRIM"
        else CORE_FLAT_ATK_OVERSPEC
        if corporation_sub_type == "OVERSPEC"
        else CORE_FLAT_ATK
    )
    try:
        return table[character_class]
    except KeyError:
        # No cored Pilgrim or OVERSPEC Supporter exists in the ground truth, so
        # that value was never measured. Falling back to the class value would be
        # wrong by ~14-30 per core, so say so rather than answer plausibly.
        raise UnmeasuredStat(
            f"core flat ATK for a {corporation or corporation_sub_type} "
            f"{character_class} was never measured"
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


def collectible_atk(tables: dict[str, Any], item_tid: int, item_level: int) -> int:
    """Flat ATK from the equipped collectible or favorite item."""
    if not item_tid:
        return 0
    curve = tables["collectible_sample"]["atk"]
    if item_tid >= FAVORITE_ITEM_TID_BASE:
        # Measured: four units holding a favorite item at level 2 all contribute
        # 9,688 - the collectible curve's top entry, not its level-2 entry.
        return curve[-1]
    if item_level <= 0:
        # The curve has an entry at index 0 (3,029) but units at level 0 measure
        # no contribution at all, so a tid without a level is an unequipped slot.
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
# fitted against measured raid400_hp across every cored unit of the tier, do.
CORE_FLAT_HP = {"Attacker": 6347.944, "Supporter": 6294.678, "Defender": 6601.727}

# The awakened Counters (corporation_sub_type: OVERSPEC) and the Pilgrims measure
# the SAME per-core HP - unlike ATK, where Pilgrims sit above OVERSPEC. Since
# every Pilgrim is OVERSPEC too, one row covers both. Fitted on 7 Attackers and
# 4 Defenders against measured HP.
#
# Supporter comes from the same ShiftyPad reading as CORE_FLAT_ATK_PILGRIM's:
# 54,109 HP per core on Grave, matched to the digit by Little Mermaid, less
# base(Supporter, 400) * 0.02 * 1.06. Every PILGRIM Supporter is OVERSPEC and
# every OVERSPEC Supporter is PILGRIM (Chime, Dorothy, Grave, Little Mermaid,
# Nayuta, Rapunzel are the same six units either way), so this one row is the
# whole Supporter story - no PILGRIM/OVERSPEC split can arise for them.
CORE_FLAT_HP_OVERSPEC = {"Attacker": 6663.054, "Defender": 6986.799,
                         "Supporter": 6240.184}

# Units whose per-core HP flat is none of the above, keyed by resource_id - the
# same three units that are ATK outliers, and unexplained here too. Measured, not
# derived. (Vesti and Rosanna share an ATK outlier but differ slightly in HP.)
CORE_FLAT_HP_BY_RESOURCE_ID = {
    91: 5791.386,    # Vesti
    280: 5791.040,   # Rosanna
    380: 5921.039,   # Nero
}


def core_flat_hp(
    character_class: str,
    *,
    corporation: str | None = None,
    corporation_sub_type: str | None = None,
    resource_id: int | None = None,
) -> float:
    """Flat HP each core is worth for this unit.

    A unit's own measured value wins over OVERSPEC/Pilgrim, which wins over its
    class's - most units only have the class value. Unlike core_flat_atk there is
    a single OVERSPEC tier (Pilgrims measure the same per-core HP as Counters).
    """
    if character_class not in CORE_FLAT_HP:
        raise KeyError(
            f"no core flat for class {character_class!r}; have {sorted(CORE_FLAT_HP)}"
        )
    if resource_id in CORE_FLAT_HP_BY_RESOURCE_ID:
        return CORE_FLAT_HP_BY_RESOURCE_ID[resource_id]
    is_overspec = corporation == "PILGRIM" or corporation_sub_type == "OVERSPEC"
    table = CORE_FLAT_HP_OVERSPEC if is_overspec else CORE_FLAT_HP
    try:
        return table[character_class]
    except KeyError:
        # No cored OVERSPEC/Pilgrim Supporter exists in the ground truth, so its
        # per-core HP was never measured. Say so rather than answer plausibly.
        raise UnmeasuredStat(
            f"core flat HP for a {corporation or corporation_sub_type} "
            f"{character_class} was never measured"
        ) from None


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
    curve = tables["collectible_sample"]["hp"]
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
    corporation: str | None = None,
    corporation_sub_type: str | None = None,
    resource_id: int | None = None,
    extra_flat_hp: float = 0.0,
) -> float:
    """Solo-raid HP for one unit, the HP sibling of assemble_atk. DEF is not
    modelled - the simulator never reads it. `extra_flat_hp` is assembled by the
    caller from affinity_hp, research_hp, equipment_hp, cube_hp, collectible_hp.
    """
    enhance = tables["classes"][character_class]["stat_enhance"]
    scaled = base_hp(tables, character_class, level) * breakthrough_multiplier(grade, core)
    flat = grade * enhance["grade_hp"]
    if core:
        flat += core * core_flat_hp(
            character_class,
            corporation=corporation,
            corporation_sub_type=corporation_sub_type,
            resource_id=resource_id,
        )
    return scaled + flat + extra_flat_hp


def assemble_atk(
    tables: dict[str, Any],
    *,
    character_class: str,
    level: int,
    grade: int,
    core: int,
    corporation: str | None = None,
    corporation_sub_type: str | None = None,
    resource_id: int | None = None,
    extra_flat: float = 0.0,
) -> float:
    """Solo-raid ATK for one unit. `extra_flat` covers what is not yet derived.

    The identity arguments only select the per-core flat, so a unit without cores
    needs none of them.
    """
    enhance = tables["classes"][character_class]["stat_enhance"]
    scaled = base_atk(tables, character_class, level) * breakthrough_multiplier(grade, core)
    flat = grade * enhance["grade_attack"]
    if core:
        flat += core * core_flat_atk(
            character_class,
            corporation=corporation,
            corporation_sub_type=corporation_sub_type,
            resource_id=resource_id,
        )
    return scaled + flat + extra_flat
