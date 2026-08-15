import pytest
from pydantic import ValidationError

from app.models import OverloadOption, SkillLevels, UserNikkeState


def test_user_nikke_state_minimal_construction():
    state = UserNikkeState(
        character_slug="anis",
        level=200,
        hp=50000,
        atk=8000,
        def_=2000,
        skill_levels=SkillLevels(skill1=1, skill2=1, burst=1),
    )
    assert state.character_slug == "anis"
    assert state.overload_options == []


def test_user_nikke_state_with_overload_options():
    state = UserNikkeState(
        character_slug="anis",
        level=200,
        hp=60000,
        atk=9500,
        def_=2200,
        skill_levels=SkillLevels(skill1=10, skill2=10, burst=10),
        overload_options=[
            OverloadOption(name="Elemental Damage", value=5.58),
            OverloadOption(name="Core Hit Damage", value=20.0),
        ],
    )
    assert len(state.overload_options) == 2


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
            hp=-1,
            atk=8000,
            def_=2000,
            skill_levels=SkillLevels(skill1=1, skill2=1, burst=1),
        )


def test_user_nikke_state_accepts_actual_level_stats():
    s = UserNikkeState(
        character_slug="rapi-red-hood", level=400,
        hp=3532402, atk=143543, def_=20986,
        actual_hp=9727100, actual_atk=418862, actual_def=55537,
        skill_levels=SkillLevels(skill1=10, skill2=10, burst=10),
        overload_options=[],
    )
    assert s.actual_atk == 418862


def test_actual_level_stats_default_to_none():
    s = UserNikkeState(
        character_slug="liter", level=400,
        hp=1, atk=1, def_=1,
        skill_levels=SkillLevels(skill1=1, skill2=1, burst=1),
        overload_options=[],
    )
    assert s.actual_atk is None


def test_an_overload_line_keeps_the_row_and_level_the_gear_screen_needs():
    """Parsing must not quietly drop what the per-piece view is drawn from.

    The gear screen lays a piece's rolls out in option-row order and emphasises
    each by the level it rolled at, so `index` and `level` are part of the wire
    contract rather than decoration. Pydantic ignores undeclared fields instead
    of rejecting them, so leaving them off the model loses them with no error -
    and this model is the declared source of truth the TypeScript mirror is
    kept in step with.
    """
    option = OverloadOption.model_validate({
        "name": "우월코드 대미지 증가",
        "value": 29.16,
        "lines": [{"slot": "head", "index": 2, "value": 29.16, "level": 15}],
    })
    [line] = option.lines
    assert (line.index, line.level) == (2, 15)


def test_an_overload_line_synced_before_the_gear_screen_still_parses():
    """A roster stored before those fields existed must not become unloadable."""
    option = OverloadOption.model_validate({
        "name": "공격력 증가",
        "value": 4.77,
        "lines": [{"slot": "arm", "value": 4.77}],
    })
    [line] = option.lines
    assert (line.index, line.level) == (None, None)
