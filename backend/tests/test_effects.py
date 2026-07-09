from app.effects import Effect, EffectRegistry, Pulse


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


def test_drain_pulses_returns_and_clears_matching_pulses():
    registry = EffectRegistry()
    registry.add_pulse(
        Pulse(stat="burst_cooldown_reduction_sec", value=7.48, scope="squad", source_slug="anis-star")
    )

    drained = registry.drain_pulses("burst_cooldown_reduction_sec")
    assert len(drained) == 1
    assert drained[0].value == 7.48

    assert registry.drain_pulses("burst_cooldown_reduction_sec") == []


def test_drain_pulses_only_matches_requested_stat():
    registry = EffectRegistry()
    registry.add_pulse(Pulse(stat="stat_a", value=1.0, scope="squad", source_slug="x"))
    registry.add_pulse(Pulse(stat="stat_b", value=2.0, scope="squad", source_slug="x"))

    drained = registry.drain_pulses("stat_a")
    assert len(drained) == 1
    assert drained[0].stat == "stat_a"
    assert [p.stat for p in registry.drain_pulses("stat_b")] == ["stat_b"]


def test_multiple_pulses_of_same_stat_all_returned():
    registry = EffectRegistry()
    registry.add_pulse(Pulse(stat="s", value=1.0, scope="squad", source_slug="a"))
    registry.add_pulse(Pulse(stat="s", value=2.0, scope="squad", source_slug="b"))

    drained = registry.drain_pulses("s")
    assert sorted(p.value for p in drained) == [1.0, 2.0]
