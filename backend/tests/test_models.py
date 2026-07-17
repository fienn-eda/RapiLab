import pytest
from pydantic import ValidationError

from app.models import OverloadOption, PveCube, SkillLevels, UserNikkeState


def test_user_nikke_state_minimal_construction():
    state = UserNikkeState(
        character_slug="anis",
        level=200,
        core_level=0,
        hp=50000,
        atk=8000,
        def_=2000,
        skill_levels=SkillLevels(skill1=1, skill2=1, burst=1),
    )
    assert state.character_slug == "anis"
    assert state.overload_options == []
    assert state.pve_cube is None


def test_user_nikke_state_with_overload_and_cube():
    state = UserNikkeState(
        character_slug="anis",
        level=200,
        core_level=3,
        hp=60000,
        atk=9500,
        def_=2200,
        skill_levels=SkillLevels(skill1=10, skill2=10, burst=10),
        overload_options=[
            OverloadOption(name="Elemental Damage", value=5.58),
            OverloadOption(name="Core Hit Damage", value=20.0),
        ],
        pve_cube=PveCube(name="Bastion Cube", level=10),
    )
    assert len(state.overload_options) == 2
    assert state.pve_cube.name == "Bastion Cube"


def test_skill_levels_must_be_within_valid_range():
    with pytest.raises(ValidationError):
        SkillLevels(skill1=0, skill2=1, burst=1)

    with pytest.raises(ValidationError):
        SkillLevels(skill1=11, skill2=1, burst=1)


def test_user_nikke_state_rejects_negative_stats():
    with pytest.raises(ValidationError):
        UserNikkeState(
            character_slug="anis",
            level=200,
            core_level=0,
            hp=-1,
            atk=8000,
            def_=2000,
            skill_levels=SkillLevels(skill1=1, skill2=1, burst=1),
        )


def test_user_nikke_state_accepts_actual_level_stats():
    s = UserNikkeState(
        character_slug="rapi-red-hood", level=400, core_level=0,
        hp=3532402, atk=143543, def_=20986,
        actual_hp=9727100, actual_atk=418862, actual_def=55537,
        skill_levels=SkillLevels(skill1=10, skill2=10, burst=10),
        overload_options=[], pve_cube=None,
    )
    assert s.actual_atk == 418862


def test_actual_level_stats_default_to_none():
    s = UserNikkeState(
        character_slug="liter", level=400, core_level=0,
        hp=1, atk=1, def_=1,
        skill_levels=SkillLevels(skill1=1, skill2=1, burst=1),
        overload_options=[], pve_cube=None,
    )
    assert s.actual_atk is None
