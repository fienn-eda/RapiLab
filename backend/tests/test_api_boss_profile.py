"""Every boss field the API accepts has to reach the engine's BossProfile.

This exists because one did not. `effective_range_band` was wired into the
simulator and into the recorded-raid harness on 2026-07-31, but the three
endpoints built BossProfile by listing its fields, so the recommender kept
computing with no band at all - a user could pick a mid-range boss and the AR
and MG in their deck would silently not collect the bonus.

The fix was to spread instead of list (`api.boss_profile`), and the test that
matters is the one below: it compares the two field sets rather than checking
any one name, so the next field added to BossProfileIn is covered the day it
is added rather than the day someone remembers.
"""
import dataclasses

import pytest
from pydantic import ValidationError

from app.api import BossProfileIn, boss_profile
from app.raid_simulator import _simulate_raid_once


def test_every_request_field_reaches_the_engine_profile():
    engine_fields = {f.name for f in dataclasses.fields(boss_profile(BossProfileIn()))}
    assert set(BossProfileIn.model_fields) <= engine_fields


def test_the_band_a_caller_sends_is_the_band_the_engine_gets():
    assert boss_profile(BossProfileIn(effective_range_band="mid")).effective_range_band == "mid"


def test_an_omitted_band_pays_nobody():
    # None is what "we have not read this encounter's distance" means, and it
    # is what every caller sent before the field existed.
    assert boss_profile(BossProfileIn()).effective_range_band is None


def test_a_band_outside_the_three_is_rejected_at_the_edge():
    # raid_simulator raises on an unknown band; the API should never get that
    # far, so the wire model constrains it instead.
    with pytest.raises(ValidationError):
        BossProfileIn(effective_range_band="medium")


def test_the_other_boss_fields_still_arrive():
    # The spread must not have quietly dropped anything the endpoints relied on.
    profile = boss_profile(BossProfileIn(
        element="Iron", core_hittable=True, enemy_def=31784.0,
        fight_duration=180.0, part_destructible=True))
    assert (profile.element, profile.core_hittable, profile.enemy_def,
            profile.fight_duration, profile.part_destructible) == (
        "Iron", True, 31784.0, 180.0, True)


def test_the_pierce_flag_a_caller_sends_is_the_flag_the_engine_gets():
    assert boss_profile(BossProfileIn(
        pierce_hits_body_behind_core=True)).pierce_hits_body_behind_core is True


def test_declared_part_destruction_times_reach_the_engine():
    # 튜플로 도착해야 한다. boss_profile()은 필드를 나열하지 않고 model_dump()를
    # 그대로 펼치므로(그 함수의 독스트링), 여기서 리스트가 나오면 BossProfile이
    # 선언한 tuple[float, ...]가 거짓말이 되고 아무도 안 잡는다.
    profile = boss_profile(BossProfileIn(
        part_destructible=True, part_destruction_times=[1.0, 61.0, 126.0]))
    assert profile.part_destruction_times == (1.0, 61.0, 126.0)


def test_a_caller_that_sends_no_destruction_times_gets_the_untimed_default():
    assert boss_profile(BossProfileIn()).part_destruction_times == ()


def test_the_adds_flag_a_caller_sends_is_the_flag_the_engine_gets():
    assert boss_profile(BossProfileIn(spawns_adds=True)).spawns_adds is True
    assert boss_profile(BossProfileIn()).spawns_adds is False


def test_a_negative_destruction_time_is_rejected_at_the_api_surface():
    # 전투가 시작하기 전에 깨지는 파츠는 없다. 음수가 통과하면 -5초에 열린 창이
    # 전투 시작 시점에 이미 살아 있어, 회차 로더가 막으려던 것과 같은 상태가
    # 라우트로 들어온다(코어 지름을 gt=0으로 막는 것과 같은 이유다).
    with pytest.raises(ValidationError):
        BossProfileIn(part_destruction_times=[-5.0])


def test_evaluate_deck_forwards_every_boss_field_the_simulator_accepts(monkeypatch):
    """The API's spread fixed one listing trap; this is the same trap one layer
    down. `evaluate_deck` hands simulate_raid its boss kwargs by NAME, so a new
    BossProfile field reaches the wire, reaches the engine's dataclass, and then
    silently stops - exactly how `effective_range_band` was lost on 2026-07-31.
    """
    import inspect

    from app import deck_search

    # BossProfile field -> simulate_raid parameter, where the two differ.
    ALIASES = {"element": "boss_element"}

    captured = {}

    def fake_simulate_raid(**kwargs):
        captured.update(kwargs)
        return {"total_damage": 0.0, "damage_log": [], "events": []}

    monkeypatch.setattr(deck_search, "assemble_simulation_inputs",
                        lambda deck, **kwargs: {})
    monkeypatch.setattr(deck_search, "simulate_raid", fake_simulate_raid)
    deck_search.evaluate_deck([], deck_search.BossProfile())

    # `_simulate_raid_once` is where the boss parameters are actually named -
    # the public `simulate_raid` is a fixed-point wrapper whose signature is
    # (*args, **kwargs), so introspecting it would intersect to the empty set
    # and this assertion would pass without checking anything.
    sim_params = set(inspect.signature(_simulate_raid_once).parameters)
    expected = {ALIASES.get(f.name, f.name)
                for f in dataclasses.fields(deck_search.BossProfile)} & sim_params

    assert expected <= set(captured), (
        f"evaluate_deck drops boss fields the simulator accepts: "
        f"{sorted(expected - set(captured))}")


def test_an_omitted_core_diameter_models_the_old_ceiling():
    # None means "this encounter does not model a core hit rate", which is what
    # every caller sent before the field existed - and what the recorded-raid
    # harness keeps sending, so the calibration is untouched by this work.
    assert boss_profile(BossProfileIn()).core_diameter_px is None


def test_the_core_diameter_a_caller_sends_is_the_one_the_engine_gets():
    assert boss_profile(BossProfileIn(
        core_hittable=True, core_diameter_px=62.5)).core_diameter_px == 62.5


def test_a_non_positive_core_diameter_is_rejected_at_the_edge():
    # accuracy.core_hit_rate divides by the diameter; zero or negative would
    # divide by zero or invent a positive core-hit share for an impossible
    # boss, so the wire model constrains it instead of letting either happen.
    with pytest.raises(ValidationError):
        BossProfileIn(core_diameter_px=0.0)
    with pytest.raises(ValidationError):
        BossProfileIn(core_diameter_px=-1.0)
