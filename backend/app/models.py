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
    level: int = Field(ge=1, le=15)


class UserNikkeState(BaseModel):
    character_slug: str
    level: int = Field(ge=1)
    core_level: int = Field(ge=0)
    hp: float = Field(ge=0)
    atk: float = Field(ge=0)
    def_: float = Field(ge=0)
    actual_hp: float | None = Field(default=None, ge=0)
    actual_atk: float | None = Field(default=None, ge=0)
    actual_def: float | None = Field(default=None, ge=0)
    skill_levels: SkillLevels
    # hp/atk/def above ALREADY include the equipped cube's contribution: Fienn
    # confirmed ShiftyPad reflects the cube in the displayed stats when one is
    # equipped, and shows bare character stats when none is. Cube stats are
    # therefore never re-added on top - the opposite of overload_options, which
    # ShiftyPad shows separately and which ARE additive (see overload_effects).
    overload_options: list[OverloadOption] = Field(default_factory=list)
    pve_cube: PveCube | None = None
