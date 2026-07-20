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


class OverloadOption(BaseModel):
    """One aggregated overload stat line, summed across all 4 gear pieces."""

    name: str
    value: float


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
