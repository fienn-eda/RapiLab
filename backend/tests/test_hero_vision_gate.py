"""Hero Vision, Laplace's stack counter, and the max-stacks gate it feeds.

Both Laplace builds carry the same bullet - "11.9% of final ATK as true damage
when Hero Vision is at max stacks" - and until now neither read the counter:
the base build deferred the bullet outright and the signature ASSUMED the gate
was open for its whole transform. Measurement says neither is right (see
`docs/engine-gaps.md`), so these tests pin the counter and the gate.

The two builds fall on opposite sides of the same arithmetic, which is what
makes the pair worth testing together: a stack lasts 5 sec on the base build
and 15 sec on the signature, so reaching the 5-stack cap needs 1.00 Full Charge
attacks/sec on the base and 0.33/sec on the signature.
"""
import pytest

from app.raid_simulator import _resource_fill_times, simulate_raid
from app.skill_rules.laplace import (
    HERO_VISION,
    build_buster_scheduled_nukes,
    build_hero_vision_resources,
)
from app.skill_rules.laplace_signature import (
    build_buster_scheduled_nukes as build_signature_buster_scheduled_nukes,
)
from app.skill_rules.laplace_signature import (
    build_buster_weapon_mode_schedule,
    build_hero_vision_signature_resources,
)
from app.squad_engine import SquadContext, SquadMember

# Real skill level 10 values from lootandwaifus.com, slot indices read off the
# parsed data rather than counted in the bullet text.
HERO_VISION_BASE = {
    "description_value_01": "3.57",  # Explosion Radius (not a damage multiplier)
    "description_value_02": "5",     # stacks up to 5
    "description_value_03": "5",     # ...and lasts for 5 sec
}
HERO_VISION_SIGNATURE = {**HERO_VISION_BASE, "description_value_03": "15"}
LAPLACE_BUSTER_BASE = {
    "description_value_01": "897.6",
    "description_value_02": "14.52",
    "description_value_03": "5",     # transform duration
    "description_value_04": "11.9",  # the gated true-damage rider
}
LAPLACE_BUSTER_SIGNATURE = {
    "description_value_01": "1455.72",
    "description_value_02": "22.2",
    "description_value_03": "10",
    "description_value_04": "11.9",
}


def base_values():
    return {"hero_vision": HERO_VISION_BASE, "laplace_buster": LAPLACE_BUSTER_BASE}


def signature_values():
    return {"hero_vision": HERO_VISION_SIGNATURE,
            "laplace_buster": LAPLACE_BUSTER_SIGNATURE}


def make_context(slug):
    return SquadContext([SquadMember(slug, burst_tier=3, element="Iron")])


# --------------------------------------------------------------------------
# The resource itself
# --------------------------------------------------------------------------

def test_hero_vision_cap_and_lifetime_come_from_the_data():
    (base,) = build_hero_vision_resources(base_values())
    (signature,) = build_hero_vision_signature_resources(signature_values())
    assert base.name == signature.name == HERO_VISION
    assert base.cap == signature.cap == 5
    # The lifetime is NOT a ResourceSpec field - it is read at gate time, so it
    # rides the gate tuple. This is where the two builds diverge.
    assert base.fill[2] == 5.0        # the base transform's own duration
    assert signature.fill[2] == 10.0  # the signature's


def test_buster_ticks_do_not_fill_hero_vision():
    """The gauge is fed by Full Charge attacks. During the transform her weapon
    IS the Buster - fixed-rate ticks, not charge shots - and those ticks land in
    `shot_times` exactly like her ordinary shots, so the fill kind has to drop
    the transform window or the gauge feeds itself while it is being read."""
    (spec,) = build_hero_vision_resources(base_values())
    burst = 10.0
    # Three Full Charge shots before the burst, then dense Buster ticks inside
    # the 5-sec transform, then Full Charge shots again after it.
    full_charge_before = [7.0, 8.4, 9.8]
    buster_ticks = [burst + k / 9.3 for k in range(1, 47)]
    full_charge_after = [16.4, 17.8]
    shot_times = sorted(full_charge_before + buster_ticks + full_charge_after)

    fills = _resource_fill_times(
        spec.fill, shot_times, True, 180.0, (), [burst],
    )
    assert fills == pytest.approx(full_charge_before + full_charge_after)


def test_full_charge_shots_after_the_transform_still_fill():
    """The window that must be excluded is HER TRANSFORM, not the squad's Full
    Burst. Those differ: a Full Burst runs 10 sec while the base transform runs
    5, so filtering on the Full Burst window would silently drop five seconds of
    genuine Full Charge attacks and hold the gauge below its cap for free."""
    (spec,) = build_hero_vision_resources(base_values())
    burst = 10.0
    # A shot 6 sec after the burst: inside a 10-sec Full Burst window, but well
    # outside the 5-sec transform, so it IS a Full Charge attack.
    shot_times = [16.0]
    fills = _resource_fill_times(spec.fill, shot_times, True, 180.0,
                                 [(burst, burst + 10.0)], [burst])
    assert fills == [16.0]


# --------------------------------------------------------------------------
# The gate
# --------------------------------------------------------------------------

def _gate_of(specs):
    (spec,) = specs
    return spec["resource_gate"]


def test_rider_is_gated_shut_below_max_stacks():
    for specs in (build_buster_scheduled_nukes(base_values()),
                  build_signature_buster_scheduled_nukes(signature_values())):
        name, cap, lifetime, scale_fn = _gate_of(specs)
        assert name == HERO_VISION
        assert cap == 5
        assert [scale_fn(count) for count in (0, 1, 4)] == [0.0, 0.0, 0.0]
        assert scale_fn(5) == 1.0


def test_gate_lifetime_is_the_builds_own_stack_duration():
    _n, _c, base_lifetime, _f = _gate_of(build_buster_scheduled_nukes(base_values()))
    _n, _c, sig_lifetime, _f = _gate_of(
        build_signature_buster_scheduled_nukes(signature_values()))
    assert (base_lifetime, sig_lifetime) == (5.0, 15.0)


def test_rider_rides_every_buster_tick():
    """The rider lands alongside each Normal Damage tick, so its cadence is the
    transform's tick cadence - 46 on the base's 5-sec window at 9.3/sec, 93 on
    the signature's measured 10-sec window."""
    (base,) = build_buster_scheduled_nukes(base_values())
    ctx = make_context("laplace")
    ctx.burst_times["laplace"] = [10.0, 60.0]
    times = base["schedule"](ctx, 180.0)
    assert len(times) == 2 * 46
    assert base["percent"] == 11.9
    assert base["damage_type"] == "true"
    # Every tick sits inside the transform window it belongs to.
    assert all(10.0 < t <= 15.0 or 60.0 < t <= 65.0 for t in times)

    (signature,) = build_signature_buster_scheduled_nukes(signature_values())
    sig_ctx = make_context("laplace-signature")
    sig_ctx.burst_times["laplace-signature"] = [10.0]
    assert len(signature["schedule"](sig_ctx, 180.0)) == 93


# --------------------------------------------------------------------------
# The gate reaches the transform's own TICKS, not just the rider beside them
# --------------------------------------------------------------------------

SIG = "laplace-signature"


def _buster_tick_types(gauge_charge_time):
    """The damage types of her normal attacks when she bursts at
    `gauge_charge_time`.

    That one number decides the gate: bursting early leaves her no time to land
    the five Full Charge attacks Hero Vision needs, bursting late gives her
    plenty. Nothing else differs between the two runs, so any difference in the
    types is the gate and only the gate.
    """
    values = signature_values()
    deck = [
        {"slug": "b1", "burst_tier": 1, "element": "Iron", "cooldown": 20.0},
        {"slug": "b2", "burst_tier": 2, "element": "Iron", "cooldown": 20.0},
        {"slug": SIG, "burst_tier": 3, "element": "Iron", "cooldown": 40.0},
    ]
    result = simulate_raid(
        deck,
        {"b1": [], "b2": [], SIG: []},
        burst_damage_percents={},
        base_stats={m["slug"]: {"atk": 10000, "def": 0, "max_hp": 0} for m in deck},
        enemy_def=2000,
        gauge_charge_time=gauge_charge_time,
        # Long enough to cover her whole 10-sec transform and no longer, so a
        # second burst never muddies the sample.
        fight_duration=gauge_charge_time + 11.0,
        mode="auto",
        base_crit_rate=0.0,
        weapon_stats={SIG: {"weapon": "RL", "damage_percent": 10.0, "max_ammo": 999,
                            "reload_time": 0.0, "charge_time": 1.0,
                            "charge_damage_percent": 100.0}},
        weapon_mode_schedules={SIG: build_buster_weapon_mode_schedule(values)},
        resource_specs={SIG: build_hero_vision_signature_resources(values)},
    )
    return {e["damage_type"] for e in result["damage_log"]
            if e["slug"] == SIG and e["source"] == "normal_attack"}


def test_buster_ticks_are_true_typed_only_while_the_gate_is_open():
    """Additional Effect 2 reads "Normal damage is applied as true damage WHEN
    Hero Vision is at max stacks", so the transform's ticks are true damage only
    for as long as the counter says so - and the counter cannot say so at a
    burst she takes before landing five Full Charge attacks.

    Fills stop for the whole transform (Buster ticks are not Full Charge
    attacks), so a window that opens shut stays shut."""
    assert "true" not in _buster_tick_types(1.0)


def test_buster_ticks_are_true_typed_when_she_bursts_at_max_stacks():
    """The other side of the same gate - without this, typing every tick
    ordinary would also pass."""
    assert "true" in _buster_tick_types(30.0)
