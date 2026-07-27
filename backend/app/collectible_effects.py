"""The collectible (소장품) a unit has equipped, as damage-relevant modifiers.

A collectible's skill differs by WEAPON GROUP, and until 2026-07-27 nothing
read it: `stat_assembly` takes only the atk/hp curves, so the engine could not
tell a collectible was equipped at all. Ade: Agent Bunny's range test found the
gap - every one of seven readings sat a uniform 1.06x below the model, which
resolved to her SR-group collectible's "차지 대미지 6.31% 배율" (see
docs/engine-gaps.md #15).

Two things here are easy to get wrong, and both have already bitten this
codebase once:

- **The level arrays are 0-based.** A collectible has a level 0, so its arrays
  hold 16 entries for levels 0..15 and are indexed directly. The harmony cube's
  hold 15 for levels 1..15 and are indexed at `level - 1`. Copying
  `cube_effects` verbatim shifts every value by one rung.
- **A value ladder can run past its own reachable cap.** Taking `ladder[-1]`
  for a maxed item can therefore read a rung the item can never reach (this is
  what made an earlier session read the cube table as discontinuous). The top
  is `levelN[-1]` used as a skill level, never the ladder's last element.

A FAVORITE ITEM (애장품, tid >= FAVORITE_ITEM_TID_BASE) always sits at the top
rung regardless of its own level, because promotion REQUIRES the SR collectible
at level 15; the favorite item's own level gates the unit's skill unlocks
instead. Fienn verified this by promoting Flora, who reports the MG ladder's
top 9.5% while sitting at SSR level 5. `stat_assembly.collectible_atk` had
already inferred the same rule from measurement; this is why it holds.
"""
import logging
from functools import lru_cache
from typing import Any

from app.effects import Effect
from app.stat_assembly import FAVORITE_ITEM_TID_BASE, load_stat_tables

logger = logging.getLogger(__name__)

# A skill group's `group_id` -> what each of its value slots means, positionally
# (`description_value_01`, `description_value_02`, ...). `None` marks a slot the
# engine has no consumer for - defensive stats (방어력, 엄폐물 최대 체력,
# 받는 대미지 감소) are deliberately unmapped, the same rule cube_effects uses.
#
# The second element of each pair says WHERE the value lands:
#   "effect" - a permanent self Effect, value/100, like any other buff
#   "weapon" - a 배율: it scales the WEAPON's own base stat rather than adding
#              to a buff bucket. The in-game tooltip defines 배율 as "기본 스탯
#              값에 스킬 계수의 비율만큼 계산되어 더해짐", so Ade's charge damage
#              6.31% takes her rocket... her SR's 250% full charge to 265.775%,
#              NOT to 256.31%.
#
# Kept as an explicit table rather than parsed out of the record's description
# text: the description is display markup, and each group only needs deciding
# once. An unmapped group_id is logged and skipped, never guessed.
#
# 900101/900102/900103 are the SR/SG/AR entries fabricated for Task 1 (see each
# record's "source" field in tables.json) - their values are provisional until
# a real in-game reading replaces them, but the STAT they map to is not in
# doubt (each record's own description names it).
COLLECTIBLE_SKILL_STATS: dict[int, list[tuple[str, str] | None]] = {
    712401: [("max_ammo_percent", "effect"), None],  # 최대 장탄 수 / 방어력 (MG)
    712002: [None, None],                            # 받는 대미지 / 엄폐물 체력 (MG)
    900101: [("charge_damage_percent", "weapon")],   # 차지 대미지 배율 (SR, provisional)
    900102: [("damage_percent", "weapon")],          # 일반 공격 대미지 배율 (SG, provisional)
    900103: [("other_core_damage_sources", "effect")],  # 코어 대미지 % (AR, provisional)
}


def skill_percents(record: dict[str, Any], item_level: int,
                   is_favorite: bool) -> dict[tuple[str, str], float]:
    """`(engine stat, placement) -> percent` for one collectible at one level.

    Slot position is a convention, not a key: the Nth entry of
    `collection_skill_group_data` is driven by the Nth `levelN` array. The data
    carries no explicit slot id (same as the harmony cube - see
    docs/insights.md).
    """
    percents: dict[tuple[str, str], float] = {}
    for slot, group in enumerate(record["collection_skill_group_data"], start=1):
        levels = record.get(f"level{slot}")
        if not levels:
            continue
        skill_level = levels[-1] if is_favorite else levels[min(item_level, len(levels) - 1)]
        if skill_level <= 0:
            continue
        mapping = COLLECTIBLE_SKILL_STATS.get(group["group_id"])
        if mapping is None:
            logger.warning("unknown collectible skill group %r - skipped", group["group_id"])
            continue
        for index, target in enumerate(mapping):
            if target is None:
                continue
            ladder = group["description_value_list"][index]["description_value"]
            percents[target] = float(ladder[skill_level - 1])
    return percents


@lru_cache(maxsize=1)
def _collectibles_table() -> dict[str, Any]:
    """The `collectibles` slice of the stat table, parsed once.

    `collectible_modifiers` is called from `roster._passive_effects`, which
    `deck_search.feasible_orderings` runs once per unit per candidate
    ordering - a combinatorial hot path. `cube_effects._assumed_percents`
    already hit this exact problem for the harmony cube and fixed it the same
    way: cache the parsed table, not the per-call result, since the result
    here varies by tid/level/source_slug but the table itself does not.
    """
    return load_stat_tables().get("collectibles", {})


def collectible_modifiers(tid: int, level: int, source_slug: str
                          ) -> tuple[dict[str, float], list[Effect]]:
    """`(weapon-stat multipliers, permanent self effects)` for one unit.

    An empty slot, or a tid the committed table does not know, contributes
    nothing - a roster collected before the field existed must not silently
    change anyone's damage.
    """
    if not tid:
        return {}, []
    record = _collectibles_table().get(str(tid))
    if record is None:
        logger.warning("no collectible record for tid %r - contributing nothing", tid)
        return {}, []
    weapon: dict[str, float] = {}
    effects: list[Effect] = []
    for (stat, placement), percent in skill_percents(
        record, level, tid >= FAVORITE_ITEM_TID_BASE
    ).items():
        if placement == "weapon":
            weapon[stat] = weapon.get(stat, 1.0) * (1 + percent / 100)
        else:
            effects.append(Effect(stat, percent / 100, "self", None, source_slug))
    return weapon, effects
