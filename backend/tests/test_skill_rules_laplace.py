from app.effects import EffectRegistry
from app.skill_rules.laplace import (
    build_hero_bomber_per_shot_rules,
    laplace_buster_burst_percent,
)
from app.squad_engine import SquadContext, SquadMember

# Real skill level 10 values from lootandwaifus.com (base build).
HERO_BOMBER = {
    "description_value_01": "81.66",  # last-bullet additional damage % of final ATK
    "description_value_02": "14.78",  # deferred: parts-hit additional damage %
}
LAPLACE_BUSTER = {
    "description_value_01": "897.6",  # First Damage % of final ATK (modeled as the burst nuke)
    "description_value_02": "14.52",  # deferred: transformed-weapon Normal Damage %
    "description_value_03": "5",      # deferred: transform duration
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
    assert pulses[0].full_burst_bonus_eligible is True  # "as additional damage"
