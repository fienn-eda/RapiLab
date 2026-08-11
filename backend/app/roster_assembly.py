"""Assemble a fetched blablalink roster into the collector roster.json shape.

The frontend's parseRosterJson consumes that shape, so slug mapping, signature
promotion and merge are reused unchanged. This module only joins the three
fetched payloads with the committed reference tables and computes each unit's
level-400 HP/ATK and overload.
"""
import json
from pathlib import Path

from app import stat_assembly as sa
from app.paths import directory_snapshot
from app.cube_effects import ASSUMED_CUBE_LEVEL
from app.overload_decode import assemble_overload

# The committed public directory snapshot: resource_id / name_code / class /
# corporation per unit. A Nikke released after this snapshot is absent, and
# assemble_roster skips it silently - refresh the snapshot when that happens
# (the sync endpoint's telemetry counts unknown name_codes for exactly this).
DIRECTORY = directory_snapshot()


def load_directory(path: Path = DIRECTORY) -> list[dict]:
    """The directory snapshot assemble_roster joins owned units against."""
    return json.loads(path.read_text(encoding="utf-8"))

SLOTS = ("head", "torso", "arm", "leg")


def extract_inputs(entry: dict, owned: dict, detail: dict,
                   assume_cube_level: int | None = None) -> dict:
    """The calculator-input record for one unit (class/corp/grade/core/investment)."""
    return {
        "name_en": entry["name_en"],
        "resource_id": entry["resource_id"],
        "class": entry["class"],
        "corporation": entry["corporation"],
        "corporation_sub_type": entry.get("corporation_sub_type"),
        "level": owned["lv"],
        "grade": detail["grade"],
        "core": detail["core"],
        "attractive_lv": detail.get("attractive_lv", 0),
        "favorite_item_lv": detail.get("favorite_item_lv", 0),
        "favorite_item_tid": detail.get("favorite_item_tid", 0),
        # Equip state at collection time is noise - a cube type is limited to
        # 12 wearers, but decks re-equip between fights, so every unit fights
        # with a cube on. assume_cube_level=None keeps the collected value,
        # which is what the collector-parity test needs to stay a real check
        # on the stat formula.
        "harmony_cube_lv": (
            detail.get("harmony_cube_lv", 0)
            if assume_cube_level is None
            else assume_cube_level
        ),
        "skill1_lv": detail.get("skill1_lv", 1),
        "skill2_lv": detail.get("skill2_lv", 1),
        "ulti_skill_lv": detail.get("ulti_skill_lv", 1),
        "equip": [
            {
                "slot": s,
                "tid": detail.get(f"{s}_equip_tid", 0),
                "tier": detail.get(f"{s}_equip_tier", 0),
                "corporation_type": detail.get(f"{s}_equip_corporation_type", 0),
                "lv": detail.get(f"{s}_equip_lv", 0),
            }
            for s in SLOTS
        ],
    }


def _gear_atk(tables, inp):
    """Equipment + cube + collectible: the terms that sit OUTSIDE the core step.

    Affinity and the corporation research ride inside it, so both travel to
    assemble_atk on their own parameters (see stat_assembly's model docstring).
    """
    return (
        sum(sa.equipment_atk(tables, e["tid"], e["lv"],
                             equip_corporation_type=e["corporation_type"],
                             unit_corporation=inp["corporation"]) for e in inp["equip"])
        + sa.cube_atk(tables, inp["harmony_cube_lv"])
        + sa.collectible_atk(tables, inp["favorite_item_tid"], inp["favorite_item_lv"])
    )


def _gear_hp(tables, inp):
    """HP sibling of `_gear_atk`. HP account research is Personal+Class
    (research_hp), not Corporation - the Corporation rows carry ATK only - and
    like its ATK counterpart it rides inside the core step."""
    return (
        sum(sa.equipment_hp(tables, e["tid"], e["lv"],
                            equip_corporation_type=e["corporation_type"],
                            unit_corporation=inp["corporation"]) for e in inp["equip"])
        + sa.cube_hp(tables, inp["harmony_cube_lv"])
        + sa.collectible_hp(tables, inp["favorite_item_tid"], inp["favorite_item_lv"])
    )


def _stats_at_level(tables, inp: dict, research: dict, level: int) -> dict:
    """One unit's ATK/HP at `level`, in the wire shape.

    Solo raid normalizes every account to character level 400; union raid has no
    level correction and is fought at the account's synchro level. Those two are
    the only callers, and the level is the only thing that differs between them.
    """
    atk = sa.assemble_atk(tables, character_class=inp["class"], level=level,
                          grade=inp["grade"], core=inp["core"],
                          affinity_flat=sa.affinity_atk(
                              tables, inp["class"], inp["attractive_lv"]),
                          research_flat=sa.corporation_atk(
                              tables, inp["corporation"], research),
                          extra_flat=_gear_atk(tables, inp))
    hp = sa.assemble_hp(tables, character_class=inp["class"], level=level,
                        grade=inp["grade"], core=inp["core"],
                        affinity_flat_hp=sa.affinity_hp(
                            tables, inp["class"], inp["attractive_lv"]),
                        research_flat_hp=sa.research_hp(
                            tables, inp["class"], research),
                        extra_flat_hp=_gear_hp(tables, inp))
    # DEF is not modelled - no caller reads it (stat_assembly's module docstring).
    return {"hp": round(hp), "atk": round(atk), "def": 0}


def assemble_unit(tables, entry: dict, owned: dict, detail: dict, research: dict,
                  assume_cube_level: int | None = None,
                  synchro_level: int | None = None) -> dict:
    inp = extract_inputs(entry, owned, detail, assume_cube_level)
    unit = {
        "name_en": inp["name_en"],
        "resource_id": inp["resource_id"],
        # Not consumed by the simulation - already folded into the stat sets -
        # but the UI shows them so the user can confirm their roster imported
        # correctly.
        "grade": inp["grade"],
        "core": inp["core"],
        # Ownership, not a stat: a dual-slot unit's Favorite Item swaps in a
        # different skill encoding ("-signature"), so the frontend needs to know
        # per user rather than consult a hand-maintained list. The stat effect
        # of the item is already folded into the stat sets.
        "favorite_item": sa.owns_favorite_item(inp["favorite_item_tid"]),
        # The item's flat ATK/HP is already folded in; this is its SKILL, which
        # is a separate damage source the engine reads per unit
        # (collectible_effects). `favorite_item` above stays - it answers a
        # different question, namely which skill encoding to use.
        "collectible": {
            "tid": inp["favorite_item_tid"],
            "level": inp["favorite_item_lv"],
        },
        "raid400": _stats_at_level(tables, inp, research, 400),
        "skill_levels": {
            "skill1": inp["skill1_lv"],
            "skill2": inp["skill2_lv"],
            "burst": inp["ulti_skill_lv"],
        },
        "overload": assemble_overload(tables, detail),
    }
    # Union raid has no level normalization, so it needs the same unit at the
    # account's synchro level. Absent when the sync did not carry that level -
    # inventing one would be a silent distortion of up to 24% between units.
    if synchro_level is not None:
        unit["actual"] = _stats_at_level(tables, inp, research, synchro_level)
    return unit


def assemble_roster(tables, directory: list, raw: dict,
                    assume_cube_level: int | None = ASSUMED_CUBE_LEVEL,
                    ) -> tuple[list[dict], list[dict]]:
    """`(units, unmeasured)` for one collected account.

    `unmeasured` names the units dropped because the ground truth has no honest
    value for them - today, a cored PILGRIM/OVERSPEC Supporter, whose per-core
    flat ATK and HP nobody has measured (stat_assembly's `UnmeasuredStat`). One
    such unit used to raise straight out of the endpoint, so a single gap made a
    whole ACCOUNT unsyncable; dropping just that unit keeps the other ~150
    usable, and naming it here is what keeps the drop from looking like the
    Nikke simply vanished.

    `raw["synchro_level"]`이 있으면 유닛마다 그 레벨의 `actual` 스탯이 함께 나온다.
    """
    by_code = {e["name_code"]: e for e in directory}
    details = {d["name_code"]: d for d in raw["character_details"]}
    owned = {o["name_code"]: o for o in raw["owned"]}
    research = {str(r["tid"]): r["lv"] for r in raw["recycle_room_researches"]}
    # The account's synchro device level, when the sync carried it. `or None`
    # also folds a 0 into "absent": level 0 is outside the stat table's 1..1200
    # and would raise rather than produce an honest number.
    synchro_level = raw.get("synchro_level") or None
    units, unmeasured = [], []
    for code, o in owned.items():
        entry, d = by_code.get(code), details.get(code)
        if entry is None or d is None:
            continue
        # Raid content is SSR-only (collect.js filters the same way before
        # scraping roster.json); the R/SR directory rows a fresh account starts
        # with have no affinity table entry and are not real roster units.
        if entry.get("original_rare") != "SSR":
            continue
        try:
            units.append(assemble_unit(tables, entry, o, d, research,
                                       assume_cube_level, synchro_level))
        except sa.UnmeasuredStat as gap:
            unmeasured.append({"name_en": entry["name_en"], "reason": str(gap.args[0])})
    units.sort(key=lambda u: u["name_en"])
    unmeasured.sort(key=lambda u: u["name_en"])
    return units, unmeasured


def to_roster_json(units: list[dict], unmeasured: list[dict] | None = None) -> dict:
    return {"units": units, "unmeasured": unmeasured or []}
