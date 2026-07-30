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
