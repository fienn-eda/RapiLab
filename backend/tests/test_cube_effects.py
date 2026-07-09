from app.cube_effects import cube_to_effects


def test_relic_bear_cube_maps_reload_and_superior_code_damage():
    # Relic Bear Cube lvl 15: Reloading Speed +29.69%, Superior Code Damage
    # +19.09% (the cube all 5 of Fienn's Nikkes wear).
    effects = cube_to_effects(
        name="Relic Bear Cube",
        reload_speed_percent=29.69,
        superior_code_damage_percent=19.09,
        source_slug="anis-star",
    )
    by_stat = {e.stat: e for e in effects}
    assert round(by_stat["reload_speed_percent"].value, 4) == 0.2969
    assert round(by_stat["other_elemental_bonus"].value, 4) == 0.1909
    for effect in effects:
        assert effect.scope == "self"
        assert effect.duration is None
        assert effect.source_slug == "anis-star"


def test_cube_with_only_reload_omits_the_other_stat():
    effects = cube_to_effects(
        name="Reload Cube", reload_speed_percent=14.84, source_slug="crown"
    )
    stats = {e.stat for e in effects}
    assert stats == {"reload_speed_percent"}


def test_cube_with_no_effects_returns_empty():
    effects = cube_to_effects(name="Empty Cube", source_slug="crown")
    assert effects == []
