"""The harmony cube every unit is assumed to wear, as permanent self Effects.

Cube choice is not user input. A cube type can only be worn by 12 units at
once, but decks re-equip between fights, so in solo raid all 25 units fight
with a cube on and the equip state at collection time is noise. We therefore
assume a Resilience Cube (렐릭 베어 큐브) at Lv.15 for everyone.

The percentages are derived from the committed stat table rather than
hardcoded. That table stores, per cube level, the *skill level* each of the
cube's skill slots has reached (level1/level2/level3), and per slot a ladder
of percentages indexed by that skill level. At Lv.15 the slots sit at skill
level 3 and 6, giving reload speed 29.69% and superior code damage 19.09% -
both confirmed against the in-game tooltip (Fienn, 2026-07-20).

Only stats that affect raid DPS are mapped. A cube must never contribute
atk/def/max_hp here: the flat cube stats are already handled by
stat_assembly.cube_atk / cube_hp on the sync path, so re-adding them would
double-count.
"""
import logging
from functools import lru_cache

from app.effects import Effect
from app.stat_assembly import load_stat_tables

logger = logging.getLogger(__name__)

# Cube skill name (as it appears in the table) -> the engine stat it feeds.
CUBE_SKILL_STATS = {
    "퀵 리로드 HC": "reload_speed_percent",
    "안티 코드 HC": "other_elemental_bonus",
}

ASSUMED_CUBE_LEVEL = 15


def cube_skill_percents(tables: dict, cube_level: int) -> dict[str, float]:
    """Engine stat -> percent for the assumed cube at `cube_level`."""
    cube = tables["resilience_cube"]
    percents: dict[str, float] = {}
    for slot, group in enumerate(cube["harmonycube_skill_group"], start=1):
        if group is None:
            continue
        skill_level = cube[f"level{slot}"][cube_level - 1]
        if skill_level <= 0:
            continue
        name = group["name_localkey"]
        stat = CUBE_SKILL_STATS.get(name)
        if stat is None:
            logger.warning("unknown harmony cube skill %r - skipped", name)
            continue
        ladder = group["description_value_list"][0]["description_value"]
        percents[stat] = float(ladder[skill_level - 1])
    return percents


@lru_cache(maxsize=1)
def _assumed_percents() -> tuple[tuple[str, float], ...]:
    """The assumed cube's percentages, read once. Tuple so lru_cache is safe."""
    return tuple(cube_skill_percents(load_stat_tables(), ASSUMED_CUBE_LEVEL).items())


def assumed_cube_effects(source_slug: str) -> list[Effect]:
    """The assumed cube's always-on buffs on one wearer."""
    return [
        Effect(stat, percent / 100, "self", None, source_slug)
        for stat, percent in _assumed_percents()
    ]


def cube_to_effects(
    name,
    source_slug,
    reload_speed_percent=None,
    superior_code_damage_percent=None,
):
    effects = []
    if reload_speed_percent is not None:
        effects.append(
            Effect("reload_speed_percent", reload_speed_percent / 100, "self", None, source_slug)
        )
    if superior_code_damage_percent is not None:
        effects.append(
            Effect("other_elemental_bonus", superior_code_damage_percent / 100, "self", None, source_slug)
        )
    return effects
