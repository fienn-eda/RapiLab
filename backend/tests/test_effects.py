from app.effects import Effect, EffectRegistry


def make_member(slug, element):
    return {"slug": slug, "element": element}


def test_self_scoped_effect_only_applies_to_source():
    registry = EffectRegistry()
    registry.add(
        Effect(stat="atk_percent", value=0.3, scope="self", duration=10, source_slug="anis"),
        applied_at=0.0,
    )
    anis = make_member("anis", "Iron")
    other = make_member("rapi", "Fire")

    assert registry.total_for(stat="atk_percent", target=anis, now=1.0) == 0.3
    assert registry.total_for(stat="atk_percent", target=other, now=1.0) == 0.0


def test_squad_scoped_effect_applies_to_everyone():
    registry = EffectRegistry()
    registry.add(
        Effect(stat="damage_taken_up", value=0.1, scope="squad", duration=5, source_slug="centi"),
        applied_at=0.0,
    )
    anis = make_member("anis", "Iron")
    rapi = make_member("rapi", "Fire")

    assert registry.total_for(stat="damage_taken_up", target=anis, now=2.0) == 0.1
    assert registry.total_for(stat="damage_taken_up", target=rapi, now=2.0) == 0.1


def test_element_scoped_effect_only_applies_to_matching_element():
    registry = EffectRegistry()
    registry.add(
        Effect(
            stat="atk_percent",
            value=0.2,
            scope="element:Iron",
            duration=10,
            source_slug="anis",
        ),
        applied_at=0.0,
    )
    iron_member = make_member("crown", "Iron")
    fire_member = make_member("rapi", "Fire")

    assert registry.total_for(stat="atk_percent", target=iron_member, now=1.0) == 0.2
    assert registry.total_for(stat="atk_percent", target=fire_member, now=1.0) == 0.0


def test_effect_expires_after_duration():
    registry = EffectRegistry()
    registry.add(
        Effect(stat="atk_percent", value=0.3, scope="self", duration=10, source_slug="anis"),
        applied_at=0.0,
    )
    anis = make_member("anis", "Iron")

    assert registry.total_for(stat="atk_percent", target=anis, now=9.99) == 0.3
    assert registry.total_for(stat="atk_percent", target=anis, now=10.01) == 0.0


def test_multiple_stacking_effects_of_same_stat_sum():
    registry = EffectRegistry()
    registry.add(
        Effect(stat="atk_percent", value=0.3, scope="self", duration=10, source_slug="anis"),
        applied_at=0.0,
    )
    registry.add(
        Effect(stat="atk_percent", value=0.2, scope="self", duration=10, source_slug="anis"),
        applied_at=1.0,
    )
    anis = make_member("anis", "Iron")

    assert round(registry.total_for(stat="atk_percent", target=anis, now=2.0), 5) == 0.5


def test_permanent_effect_has_no_duration():
    registry = EffectRegistry()
    registry.add(
        Effect(stat="core_hit_bonus", value=1.0, scope="self", duration=None, source_slug="anis"),
        applied_at=0.0,
    )
    anis = make_member("anis", "Iron")

    assert registry.total_for(stat="core_hit_bonus", target=anis, now=99999) == 1.0


def test_total_for_unaffected_stat_is_zero():
    registry = EffectRegistry()
    anis = make_member("anis", "Iron")
    assert registry.total_for(stat="atk_percent", target=anis, now=0.0) == 0.0
