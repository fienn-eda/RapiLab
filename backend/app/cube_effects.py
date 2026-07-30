"""The harmony cube a unit wears, as permanent self Effects and ammo rules.

Cube choice is not user input. A cube type can only be worn by 12 units at
once, but decks re-equip between fights, so in solo raid all 25 units fight
with a cube on and the equip state at collection time is noise. Everyone is
therefore assumed to wear a Resilience Cube (렐릭 베어 큐브) at Lv.15, and only
the recorded raid names the cubes actually worn (scripts/raid_record.py).

The percentages are derived from the committed stat tables rather than
hardcoded. A table stores, per cube level, the *skill level* each of the
cube's skill slots has reached (level1/level2/level3), and per slot a ladder
of values indexed by that skill level. At Lv.15 the Resilience slots sit at
skill level 3 and 6, giving reload speed 29.69% and superior code damage
19.09% - both confirmed against the in-game tooltip (Fienn, 2026-07-20).

The two cubes modeled here differ only in slot 1: the Tactical Bear (택티컬
베어) spends it on rounds rather than reload speed, which is a magazine
mechanic rather than a stat and leaves through `cube_ammo_refund`.

Only stats that affect raid DPS are mapped. A cube must never contribute
atk/def/max_hp here: the flat cube stats are already handled by
stat_assembly.cube_atk / cube_hp on the sync path, so re-adding them would
double-count. Both cubes carry identical flat stats, so a wearer's ATK/HP do
not depend on which one this module was asked for.
"""
import json
import logging
from functools import lru_cache

from app.attack_rate import AmmoRefund
from app.effects import Effect
from app.stat_assembly import STAT_TABLES, load_stat_tables

logger = logging.getLogger(__name__)

# Cube skill name (as it appears in the table) -> the engine stat it feeds.
CUBE_SKILL_STATS = {
    "퀵 리로드 HC": "reload_speed_percent",
    "안티 코드 HC": "other_elemental_bonus",
}

# The one cube skill that hands back ROUNDS instead of moving a stat. It is
# deliberately outside CUBE_SKILL_STATS: cube_ammo_refund reads it, and the
# percent path skips it rather than warning about an unmapped skill.
CUBE_REFUND_SKILL = "리로드 업 HC"

DEFAULT_CUBE = "resilience"
CUBE_NAMES = ("resilience", "tactical_bear")

ASSUMED_CUBE_LEVEL = 15


@lru_cache(maxsize=None)
def load_cube(name: str) -> dict:
    """One harmony cube's committed stat-table record.

    The Resilience cube rides in tables.json (it was the only cube collected
    when the global assumption landed); the Tactical Bear sits in its own file
    beside it. Both are the game's own record shape, so one reader serves both.
    """
    if name == "resilience":
        return load_stat_tables()["resilience_cube"]
    if name == "tactical_bear":
        return json.loads(
            (STAT_TABLES.parent / "tactical-bear-cube.json").read_text(encoding="utf-8"))
    raise KeyError(f"unknown harmony cube {name!r}; have {CUBE_NAMES}")


def cube_skill_percents(cube: dict, cube_level: int) -> dict[str, float]:
    """Engine stat -> percent for this cube at `cube_level`."""
    percents: dict[str, float] = {}
    for slot, group in enumerate(cube["harmonycube_skill_group"], start=1):
        if group is None:
            continue
        skill_level = cube[f"level{slot}"][cube_level - 1]
        if skill_level <= 0:
            continue
        name = group["name_localkey"]
        if name == CUBE_REFUND_SKILL:
            continue
        stat = CUBE_SKILL_STATS.get(name)
        if stat is None:
            logger.warning("unknown harmony cube skill %r - skipped", name)
            continue
        ladder = group["description_value_list"][0]["description_value"]
        percents[stat] = float(ladder[skill_level - 1])
    return percents


def cube_ammo_refund(cube: dict, cube_level: int) -> AmmoRefund | None:
    """The rounds this cube hands back mid-magazine, or None if it hands none.

    The skill's two description values are the trigger ("10발 사격 시") and the
    rounds ("탄환 충전 3발"), each a ladder indexed by the slot's skill level.
    """
    for slot, group in enumerate(cube["harmonycube_skill_group"], start=1):
        if group is None or group["name_localkey"] != CUBE_REFUND_SKILL:
            continue
        skill_level = cube[f"level{slot}"][cube_level - 1]
        if skill_level <= 0:
            return None
        values = group["description_value_list"]
        every = float(values[0]["description_value"][skill_level - 1])
        rounds = float(values[1]["description_value"][skill_level - 1])
        if every != int(every) or rounds != int(rounds):
            raise ValueError(
                f"fractional ammo refund {rounds} every {every} shots at skill "
                f"level {skill_level} - the magazine walker counts whole rounds")
        return AmmoRefund(int(every), int(rounds))
    return None


@lru_cache(maxsize=None)
def cube_refund_for(cube_name: str) -> AmmoRefund | None:
    """The assumed-level refund of the cube a NikkeSpec names."""
    return cube_ammo_refund(load_cube(cube_name), ASSUMED_CUBE_LEVEL)


@lru_cache(maxsize=None)
def _assumed_percents(cube_name: str) -> tuple[tuple[str, float], ...]:
    """One cube's percentages, read once. Tuple so lru_cache is safe."""
    return tuple(cube_skill_percents(load_cube(cube_name), ASSUMED_CUBE_LEVEL).items())


def assumed_cube_effects(source_slug: str, cube_name: str = DEFAULT_CUBE) -> list[Effect]:
    """This wearer's cube as always-on self buffs."""
    return [
        Effect(stat, percent / 100, "self", None, source_slug)
        for stat, percent in _assumed_percents(cube_name)
    ]
