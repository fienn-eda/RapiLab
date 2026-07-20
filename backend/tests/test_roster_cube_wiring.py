"""The assumed harmony cube reaches every unit's simulation inputs.

Cube effects were dead for the entire roster before this: roster.py read
percent keys off a PveCube that never defined them. A unit test on the
effect builder alone would not have caught that, so the second test here
runs the simulation and checks the damage actually moves.
"""
import pytest

from app.roster import NikkeSpec, assemble_simulation_inputs
from app.raid_simulator import simulate_raid
from app.skill_rules import registry


_BLANK_TEST_SLUGS = ("attacker", "filler-tier1", "filler-tier2")


@pytest.fixture(autouse=True)
def _blank_test_slugs():
    # These slugs are synthetic, used only here, to isolate the cube's
    # contribution from a real Nikke's own skill effects. None has an entry
    # in the real registry (build_nikke_rules raises for unknown slugs), so
    # register a no-op builder for each for the duration of this module's
    # tests.
    for slug in _BLANK_TEST_SLUGS:
        registry._BUILDERS[slug] = lambda sv: ([], None)
    yield
    for slug in _BLANK_TEST_SLUGS:
        del registry._BUILDERS[slug]


def make_spec(slug, element="Iron", atk=2000, burst_tier=3):
    return NikkeSpec(
        slug=slug,
        burst_tier=burst_tier,
        burst_cooldown=40.0,
        element=element,
        weapon="AR",
        base_stats={"atk": atk, "def": 0, "max_hp": 0},
        skill_values={},
        weapon_stats={},
    )


def test_every_spec_gets_the_cube_buffs_without_asking_for_them():
    inputs = assemble_simulation_inputs([make_spec("attacker")])
    rules = inputs["rules_by_slug"]["attacker"]

    granted = []

    class _Registry:
        def add(self, effect, applied_at=None):
            granted.append(effect)

    for rule in rules:
        if rule.trigger == "battle_start":
            rule.action(None, "attacker", 0.0, _Registry())

    by_stat = {e.stat: e for e in granted}
    assert round(by_stat["reload_speed_percent"].value, 4) == 0.2969
    assert round(by_stat["other_elemental_bonus"].value, 4) == 0.1909
    assert by_stat["reload_speed_percent"].source_slug == "attacker"


def test_the_cube_superior_code_bonus_moves_damage_against_a_weak_boss():
    # Iron > Electric, so the cube's 19.09% superior code damage applies and
    # nothing else in this deck does. Compare against the same fight with the
    # element bonus group left bare.
    # burst_cycle only ever completes a Full Burst when the deck has a member
    # of every tier (see burst_cycle.py's "full_burst_missed" gate), so
    # "attacker" needs tier 1/2 fillers even though only its own burst nuke
    # is exercised below.
    spec = make_spec("attacker", burst_tier=3)
    filler_tier1 = make_spec("filler-tier1", burst_tier=1)
    filler_tier2 = make_spec("filler-tier2", burst_tier=2)
    inputs = assemble_simulation_inputs([spec, filler_tier1, filler_tier2])
    kwargs = dict(
        burst_damage_percents={"attacker": 500.0},
        base_stats=inputs["base_stats"],
        enemy_def=0,
        gauge_charge_time=5.0,
        fight_duration=20.0,
        mode="auto",
        base_crit_rate=0.0,
    )
    with_cube = simulate_raid(
        inputs["deck"], inputs["rules_by_slug"], boss_element="Electric", **kwargs
    )
    bare = simulate_raid(
        inputs["deck"], {"attacker": []}, boss_element="Electric", **kwargs
    )

    assert with_cube["total_damage"] > bare["total_damage"]
    # 1.1 element multiplier + 0.1909 cube bonus, vs 1.1 alone.
    assert round(with_cube["total_damage"] / bare["total_damage"], 4) == round(
        1.2909 / 1.1, 4
    )
