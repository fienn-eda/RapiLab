from app.effects import EffectRegistry
from app.skill_rules.laplace import (
    BUSTER_RATE_OF_FIRE,
    build_buster_weapon_mode_schedule,
    build_hero_bomber_per_shot_rules,
    laplace_buster_burst_percent,
)
from app.squad_engine import SquadContext, SquadMember

# Real skill level 10 values from lootandwaifus.com (base build).
HERO_VISION = {
    "description_value_01": "3.57",  # Explosion Radius (not a damage multiplier)
    "description_value_02": "5",     # stacks up to 5 time(s)
    "description_value_03": "5",     # ...and lasts for 5 sec (15 on the signature)
}
HERO_BOMBER = {
    "description_value_01": "81.66",  # last-bullet additional damage % of final ATK
    "description_value_02": "14.78",  # deferred: parts-hit additional damage %
}
LAPLACE_BUSTER = {
    "description_value_01": "897.6",  # First Damage % of final ATK (modeled as the burst nuke)
    "description_value_02": "14.52",  # transformed-weapon Normal Damage %
    "description_value_03": "5",      # transform duration
    "description_value_04": "11.9",   # deferred: true damage at max Hero Vision stacks
}


def make_context():
    return SquadContext([SquadMember("laplace", burst_tier=3, element="Iron")])


def test_burst_percent_is_first_damage():
    assert laplace_buster_burst_percent({"laplace_buster": LAPLACE_BUSTER}) == 897.6


def test_hero_bomber_last_bullet_nuke():
    rules = build_hero_bomber_per_shot_rules({"hero_bomber": HERO_BOMBER})
    assert len(rules) == 1
    threshold, mode, subrules = rules[0]
    assert (threshold, mode) == (None, "last_bullet")

    registry = EffectRegistry()
    subrules[0].action(make_context(), "laplace", 5.0, registry)
    pulses = registry.drain_pulses("instant_damage_percent")
    assert len(pulses) == 1
    assert pulses[0].value == 81.66


def test_buster_segment_normal_damage_over_the_five_second_window():
    """The Buster transform's Normal Damage phase: a 5-sec segment firing at the
    same rate Fienn measured on her signature Buster (9.3/s), so ~46 ticks. The
    First Damage is the burst nuke, not part of this segment."""
    schedule = build_buster_weapon_mode_schedule({"laplace_buster": LAPLACE_BUSTER})
    ctx = make_context()
    ctx.burst_times["laplace"] = [10.0, 60.0]

    segments = schedule(ctx, 180.0)
    assert [seg["start"] for seg in segments] == [10.0, 60.0]
    assert [seg["end"] for seg in segments] == [15.0, 65.0]  # 5-sec window

    profile = segments[0]["profile"]
    assert profile["damage_percent"] == 14.52
    assert profile["rate_of_fire"] == BUSTER_RATE_OF_FIRE == 9.3
    # base build never gets the signature's max-Hero-Vision true conversion.
    assert profile.get("damage_type") is None
