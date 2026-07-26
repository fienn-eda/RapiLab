"""End-to-end: Diesel: Winter Sweets' two locked states, run through the real
roster -> simulate_raid path rather than asserted on rule objects.

Her Intro/Highlight state is the only thing that differs between the two
slugs, and it is decided by BURST SCHEDULING - so the thing worth testing is
that the `burst_delay` wired for `diesel-winter-sweets-highlight` actually
reaches burst_cycle and holds her out of the opening cycle. A Highlight slug
that still burst in cycle 1 would be collecting a four-times-larger Sustained
Damage buff on top of a burst it never gave up, which is exactly the
over-count the delay exists to prevent.
"""
import pytest

from app.roster import NikkeSpec, assemble_simulation_inputs
from app.raid_simulator import simulate_raid
from tests.test_roster import anis_star_spec, helm_spec, takina_spec
from tests.test_skill_rules_diesel_winter_sweets import VALUES

DIESEL_STATS = {"atk": 400000, "def": 50000, "max_hp": 9000000}
DIESEL_WEAPON = {
    "weapon": "RL", "damage_percent": 61.3, "max_ammo": 6,
    "reload_time": 2.0, "charge_time": 1.0, "charge_damage_percent": 250.0,
}


def _diesel(slug):
    return NikkeSpec(
        slug=slug, burst_tier=3, burst_cooldown=40.0, element="Fire", weapon="RL",
        base_stats=DIESEL_STATS, skill_values=VALUES, weapon_stats=DIESEL_WEAPON,
    )


def _run(diesel_slug):
    # Helm is the tier-3 mate who covers whichever cycle Diesel sits out.
    deck = [
        anis_star_spec(),
        takina_spec(),
        _diesel(diesel_slug),
        helm_spec(),
    ]
    return simulate_raid(
        **assemble_simulation_inputs(deck),
        enemy_def=0, gauge_charge_time=2.0, fight_duration=180.0, mode="manual",
    )


def _burst_times(result, slug):
    return [e["time"] for e in result["events"] if e["type"] == "burst" and e["slug"] == slug]


def test_intro_diesel_bursts_in_the_opening_cycle():
    result = _run("diesel-winter-sweets-intro")
    fires = _burst_times(result, "diesel-winter-sweets-intro")

    assert fires, "Intro Diesel must take the tier-3 slot she is leftmost for"
    first_full_burst = min(
        e["time"] for e in result["events"] if e["type"] == "full_burst_start"
    )
    # Her cast OPENS that Full Burst, so it lands one FULL_BURST_OPEN_DELAY
    # before the window's own start rather than exactly on it.
    assert fires[0] == pytest.approx(first_full_burst)


def test_highlight_diesel_is_held_out_of_the_opening_cycle():
    result = _run("diesel-winter-sweets-highlight")
    fires = _burst_times(result, "diesel-winter-sweets-highlight")
    full_bursts = sorted(
        e["time"] for e in result["events"] if e["type"] == "full_burst_start"
    )

    assert full_bursts, "a tier-mate must still cover the skipped cycle"
    assert fires, "she bursts from the second cycle onwards"
    assert fires[0] > full_bursts[0]


def test_holding_her_burst_still_costs_the_deck_no_full_burst():
    intro = _run("diesel-winter-sweets-intro")
    highlight = _run("diesel-winter-sweets-highlight")

    def cycles(result):
        return sum(1 for e in result["events"] if e["type"] == "full_burst_start")

    assert cycles(highlight) == cycles(intro)


def test_highlight_outdamages_intro_over_a_full_fight():
    # The whole reason the state matters: Highlight's Sustained Damage buff is
    # ~4x Intro's, and it more than pays for the burst she gives up in the
    # opening cycle. This is what makes even-cycle bursting the stronger line.
    intro = _run("diesel-winter-sweets-intro")
    highlight = _run("diesel-winter-sweets-highlight")

    assert highlight["total_damage"] > intro["total_damage"]
