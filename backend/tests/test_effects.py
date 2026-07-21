import pytest

from app.effects import Effect, EffectRegistry, Pulse, RoundGrant


def make_member(slug, element):
    return {"slug": slug, "element": element}


def test_slugs_scoped_effect_applies_only_to_listed_slugs():
    # A "slugs:a,b" scope targets exactly those units - used for "N allies with
    # the highest final ATK" buffs, resolved to concrete slugs at application time.
    registry = EffectRegistry()
    registry.add(
        Effect(stat="atk_percent", value=0.4, scope="slugs:scarlet,blast", duration=10, source_slug="miranda"),
        applied_at=0.0,
    )
    scarlet = make_member("scarlet", "Fire")
    blast = make_member("blast", "Wind")
    liter = make_member("liter", "Iron")

    assert registry.total_for(stat="atk_percent", target=scarlet, now=1.0) == 0.4
    assert registry.total_for(stat="atk_percent", target=blast, now=1.0) == 0.4
    assert registry.total_for(stat="atk_percent", target=liter, now=1.0) == 0.0


def test_slugs_scoped_effect_single_slug():
    registry = EffectRegistry()
    registry.add(
        Effect(stat="crit_rate", value=0.85, scope="slugs:scarlet", duration=10, source_slug="miranda"),
        applied_at=0.0,
    )
    assert registry.total_for("crit_rate", make_member("scarlet", "Fire"), now=1.0) == 0.85
    assert registry.total_for("crit_rate", make_member("blast", "Wind"), now=1.0) == 0.0


def test_add_round_grant_and_round_grants_accessor():
    # A RoundGrant is a pending "next-N-shots" buff, converted to a timed Effect
    # once the affected units' shot times are known (see raid_simulator).
    registry = EffectRegistry()
    grant = RoundGrant(
        stat="pierce_damage_up", value=0.2013, scope="squad",
        source_slug="zwei", shots=1, granted_at=12.0,
    )
    registry.add_round_grant(grant)
    assert registry.round_grants() == [grant]


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


def test_truncate_open_ended_closes_a_permanent_effect_at_the_given_time():
    # For a continuous buff a Nikke's own later trigger explicitly ends (e.g.
    # Grave's Heat Emission ends when she reuses her burst) - mutates the
    # stored effect's duration so any later total_for query (including ones
    # for times before the truncation, from raid_simulator's replay-style
    # second pass over normal-attack shots) respects the closed window.
    registry = EffectRegistry()
    registry.add(Effect("pierce_damage_up", 0.5, "squad", None, "grave"), applied_at=10.0)
    target = make_member("ally", "Fire")

    assert registry.total_for("pierce_damage_up", target, now=50.0) == 0.5  # still open

    registry.truncate_open_ended("pierce_damage_up", "grave", now=30.0)

    assert registry.total_for("pierce_damage_up", target, now=29.9) == 0.5   # active before truncation
    assert registry.total_for("pierce_damage_up", target, now=30.0) == 0.0   # inactive at truncation instant
    assert registry.total_for("pierce_damage_up", target, now=50.0) == 0.0   # inactive after


def test_truncate_open_ended_is_a_no_op_when_no_matching_open_effect_exists():
    registry = EffectRegistry()
    registry.truncate_open_ended("pierce_damage_up", "grave", now=30.0)  # should not raise
    target = make_member("ally", "Fire")
    assert registry.total_for("pierce_damage_up", target, now=50.0) == 0.0


def test_truncate_open_ended_only_affects_matching_stat_and_source():
    registry = EffectRegistry()
    registry.add(Effect("pierce_damage_up", 0.5, "squad", None, "grave"), applied_at=10.0)
    registry.add(Effect("pierce_damage_up", 0.3, "squad", None, "other"), applied_at=10.0)
    registry.add(Effect("attack_damage_up", 0.2, "squad", None, "grave"), applied_at=10.0)

    registry.truncate_open_ended("pierce_damage_up", "grave", now=30.0)

    target = make_member("ally", "Fire")
    assert registry.total_for("pierce_damage_up", target, now=50.0) == 0.3  # untouched (different source)
    assert registry.total_for("attack_damage_up", target, now=50.0) == 0.2  # untouched (different stat)


def test_add_refreshing_does_not_stack_same_source_reapplications():
    # A buff re-applied every shot (same stat/source/scope) REFRESHES: the active
    # value stays one instance, not the sum of overlapping 3s applications.
    registry = EffectRegistry()
    for t in (0.0, 1.0, 2.0):
        registry.add_refreshing(Effect("flat_atk", 100.0, "squad", 3.0, "prika", refresh_group="bullet"), applied_at=t)
    target = make_member("ally", "Fire")
    assert registry.total_for("flat_atk", target, now=2.5) == 100.0   # single value, not 300
    assert registry.total_for("flat_atk", target, now=4.9) == 100.0   # window runs to last apply + 3s
    assert registry.total_for("flat_atk", target, now=5.1) == 0.0


def test_add_refreshing_from_different_sources_still_sum():
    registry = EffectRegistry()
    registry.add_refreshing(Effect("flat_atk", 100.0, "squad", 3.0, "prika", refresh_group="bullet"), applied_at=0.0)
    registry.add_refreshing(Effect("flat_atk", 50.0, "squad", 3.0, "mint", refresh_group="bullet"), applied_at=0.0)
    target = make_member("ally", "Fire")
    assert registry.total_for("flat_atk", target, now=1.0) == 150.0  # two sources still add


def test_add_refreshing_respects_earlier_time_queries_after_truncation():
    # Truncation is in-place, so a replay-style query for an earlier time still
    # sees exactly one active instance, never the pre-truncation overlap.
    registry = EffectRegistry()
    registry.add_refreshing(Effect("flat_atk", 100.0, "squad", 3.0, "prika", refresh_group="bullet"), applied_at=0.0)
    registry.add_refreshing(Effect("flat_atk", 100.0, "squad", 3.0, "prika", refresh_group="bullet"), applied_at=1.0)
    target = make_member("ally", "Fire")
    assert registry.total_for("flat_atk", target, now=0.5) == 100.0  # first instance, truncated at 1.0
    assert registry.total_for("flat_atk", target, now=1.5) == 100.0  # second instance


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


def test_refreshing_buff_does_not_truncate_a_different_skills_same_stat_buff():
    # Liberalio: Raging Current is a PERMANENT self attack_damage_up, and Calm
    # Depths refreshes a SMALLER self attack_damage_up on every full charge.
    # Keyed only by (stat, source, scope), the refresh silently truncated the
    # permanent one to zero on the very first shot - her biggest buff destroyed
    # by her own smaller one. Refreshing must collapse re-applications of ONE
    # skill bullet, not everything the unit grants on that stat.
    reg = EffectRegistry()
    target = {"slug": "liberalio", "element": "Wind"}

    permanent = Effect("attack_damage_up", 2.31, "self", None, "liberalio",
                       refresh_group="raging_current")
    reg.add(permanent, applied_at=1.5)
    for shot in (1.5, 2.5, 3.5):
        reg.add_refreshing(
            Effect("attack_damage_up", 0.2083, "self", 60.0, "liberalio",
                   refresh_group="on_core"),
            applied_at=shot,
        )

    # both alive: the permanent one plus ONE copy of the refreshed one
    assert reg.total_for("attack_damage_up", target, now=4.0) == pytest.approx(2.31 + 0.2083)
    assert reg.total_for("attack_damage_up", target, now=100.0) == pytest.approx(2.31)


def test_refreshing_still_collapses_repeats_of_the_same_group():
    reg = EffectRegistry()
    target = {"slug": "u", "element": "Iron"}
    for shot in (1.0, 2.0, 3.0):
        reg.add_refreshing(
            Effect("atk_percent", 0.5, "self", 10.0, "u", refresh_group="g"),
            applied_at=shot,
        )
    assert reg.total_for("atk_percent", target, now=3.5) == pytest.approx(0.5)


def test_refreshing_effects_from_different_sources_still_both_apply():
    reg = EffectRegistry()
    target = {"slug": "ally", "element": "Iron"}
    reg.add_refreshing(Effect("atk_percent", 0.3, "squad", 10.0, "a", refresh_group="g"), 1.0)
    reg.add_refreshing(Effect("atk_percent", 0.4, "squad", 10.0, "b", refresh_group="g"), 1.0)
    assert reg.total_for("atk_percent", target, now=2.0) == pytest.approx(0.7)
