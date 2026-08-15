"""Pydantic models for user-specific Nikke progression data (from ShiftyPad).

Fixed character metadata (element/weapon/class/burst position) is NOT modeled
here - it's looked up from api.dotgg.gg via dotgg_client using character_slug,
to avoid keeping a second copy of data that never varies per-user.
"""
from pydantic import BaseModel, Field


class SkillLevels(BaseModel):
    skill1: int = Field(ge=1, le=10)
    skill2: int = Field(ge=1, le=10)
    burst: int = Field(ge=1, le=10)


class OverloadLine(BaseModel):
    """One overload roll on one gear piece, before same-type rolls are summed.

    `slot` is head / torso / arm / leg, `index` the option row (1..3) the roll
    occupies on that piece, and `level` the 1..15 tier it rolled at - together
    the three place a roll on the game's own gear screen, which squares the
    four pieces up, lists each piece's rolls in row order, and emphasises a
    line by its level rather than its percent.

    `index` and `level` are optional because a roster synced before they were
    carried has neither, and inventing them would fake an emphasis the player
    never rolled. Such a roster shows the summed view instead.
    """

    slot: str
    value: float
    index: int | None = None
    level: int | None = None


class OverloadOption(BaseModel):
    """One aggregated overload stat line, summed across all 4 gear pieces."""

    name: str
    value: float
    # The rolls `value` is the sum of, when the sync supplied them. Charge speed
    # rounds per roll rather than on the total and a total cannot be decomposed
    # back, so the rolls are what the rule needs - see
    # overload_decode.charge_speed_percent_from_lines. None means "not known":
    # a hand-edited value, or a roster synced before lines were carried.
    lines: list[OverloadLine] | None = None


class UserNikkeState(BaseModel):
    character_slug: str
    level: int = Field(ge=1)
    hp: float = Field(ge=0)
    atk: float = Field(ge=0)
    def_: float = Field(ge=0)
    actual_hp: float | None = Field(default=None, ge=0)
    actual_atk: float | None = Field(default=None, ge=0)
    actual_def: float | None = Field(default=None, ge=0)
    skill_levels: SkillLevels
    # hp/atk/def above are the user's displayed stats. The harmony cube is NOT
    # re-added on top of them here; cube_effects supplies its two damage stats
    # and stat_assembly.cube_atk / cube_hp handle the flat stats on the sync
    # path. overload_options ARE additive (see overload_effects).
    overload_options: list[OverloadOption] = Field(default_factory=list)
    # The equipped collectible (소장품). Named for what it is rather than for
    # blablalink's `favorite_item_*`, which carries ordinary R/SR collectibles
    # too - the rarity is read off the tid, not the field name. Its weapon-group
    # skill is a real damage source; see collectible_effects.
    collectible_tid: int = Field(default=0, ge=0)
    collectible_level: int = Field(default=0, ge=0)
