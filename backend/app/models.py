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


class PveCube(BaseModel):
    """The PVE (combat) cube equipped. PVP/arena cubes are out of scope."""

    name: str
    level: int = Field(ge=1, le=10)


class UserNikkeState(BaseModel):
    character_slug: str
    level: int = Field(ge=1)
    core_level: int = Field(ge=0)
    hp: float = Field(ge=0)
    atk: float = Field(ge=0)
    def_: float = Field(ge=0)
    skill_levels: SkillLevels
    # Whether cube stats are already folded into hp/atk/def above or need to be
    # added separately is unconfirmed - see project plan's open questions.
    overload_options: list[OverloadOption] = Field(default_factory=list)
    pve_cube: PveCube | None = None
