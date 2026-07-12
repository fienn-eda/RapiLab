"""Cross-unit interaction: Asuka Shikinami Langley: Wille and Maiden: Ice
Rose are BOTH canonically Burst-3, so a deck fielding both makes them share
the tier-3 slot (alternating via the engine's leftmost-eligible rotation,
see test_burst_cycle.py). Each has her own end-to-end test elsewhere, but
always as the SOLE burst-3 unit - never alongside a competitor at the same
tier. This test targets what only shows up with two real units sharing that
tier in the SAME simulate_raid call:

- dynamic_hit_count_nukes dispatches per-slug: Asuka's `fire_delay=9.0` and
  Maiden's default `fire_delay=0.0` must each apply only to their own spec,
  not bleed into the other's.
- Resource fills/resets are keyed by (slug, name), so Asuka's "anti_at_field"
  resource and Maiden's "mp" resource - and each woman's own burst-time
  bookkeeping - must stay independent even though both slugs share
  on-and-off occupancy of the same burst tier (each only fires every OTHER
  cycle here, not every cycle like in their solo tests).
- `full_burst_windows` is a single SQUAD-WIDE list fed by every tier-3
  firing, not just the owner's own. With two different units opening windows
  in the same run, Asuka's `full_burst_bonus_eligible=True` nuke must still
  land in only the window her own delayed fire falls into, and Maiden's
  (default-False) nuke - landing at the exact instant HER OWN window opens -
  must NOT pick up a bonus it never opted into.

Also demonstrates that Maiden's module docstring's "provable no-op" claim
about her MP resource's second fill rule (+1 on entering Full Burst, gated
on MP already being >=1) is scoped to solo tier-3 play - see this test's
own inline comment on `maiden_hits` for the mechanism.
"""
from app.raid_simulator import simulate_raid
from app.skill_rules.asuka_shikinami_langley_wille import (
    build_annihilation_dynamic_hit_count_nukes,
    build_anti_at_field_resources,
)
from app.skill_rules.maiden_ice_rose import build_diamond_dust_dynamic_hit_count_nukes, build_mp_resources

ASUKA_VALUES = {
    "anti_at_field": {
        "description_value_01": "471.86", "description_value_02": "15.62",
        "description_value_03": "0.83", "description_value_04": "30",
        "description_value_05": "30", "description_value_06": "2",
        "description_value_07": "10",
    },
    "annihilation_state": {
        "description_value_01": "40", "description_value_02": "9",
        "description_value_03": "21", "description_value_04": "46.8",
        "description_value_05": "36", "description_value_06": "6.62",
        "description_value_07": "1",
    },
}

MAIDEN_VALUES = {
    "diamond_dust": {"description_value_01": "1372.8", "description_value_02": "10"},
}


def test_asuka_and_maiden_dynamic_hit_count_nukes_dispatch_independently_when_sharing_burst_tier_3():
    # Both are Burst-3, so the engine's leftmost-eligible rotation alternates
    # them: with equal 40s cooldowns and buffer/midtier filling tiers 1/2
    # every cycle, Asuka (listed first) takes cycle 1's tier-3 slot at t=5.0,
    # Maiden takes cycle 2's at t=25.0 (confirmed via burst_cycle directly -
    # 20s cadence once alternation kicks in). fight_duration=40.0 captures
    # exactly these two bursts and no third.
    deck = [
        {"slug": "buffer", "burst_tier": 1, "element": "Iron", "cooldown": 20.0},
        {"slug": "midtier", "burst_tier": 2, "element": "Iron", "cooldown": 20.0},
        {"slug": "asuka-shikinami-langley-wille", "burst_tier": 3, "element": "Wind", "cooldown": 40.0},
        {"slug": "maiden-ice-rose", "burst_tier": 3, "element": "Electric", "cooldown": 40.0},
    ]
    base_stats = {
        "buffer": {"atk": 0, "def": 0, "max_hp": 0},
        "midtier": {"atk": 0, "def": 0, "max_hp": 0},
        "asuka-shikinami-langley-wille": {"atk": 10000, "def": 0, "max_hp": 0},
        "maiden-ice-rose": {"atk": 10000, "def": 0, "max_hp": 50000},
    }
    weapon_stats = {
        "asuka-shikinami-langley-wille": {
            "weapon": "MG", "damage_percent": 5.0, "max_ammo": 3000,
            "reload_time": 1.0, "charge_time": 0.0, "charge_damage_percent": 0.0,
        },
    }
    result = simulate_raid(
        deck,
        {"buffer": [], "midtier": [], "asuka-shikinami-langley-wille": [], "maiden-ice-rose": []},
        burst_damage_percents={}, base_stats=base_stats,
        enemy_def=0, gauge_charge_time=5.0, fight_duration=40.0, mode="auto", base_crit_rate=0.0,
        weapon_stats=weapon_stats,
        resource_specs={
            "asuka-shikinami-langley-wille": build_anti_at_field_resources(ASUKA_VALUES),
            "maiden-ice-rose": build_mp_resources(MAIDEN_VALUES),
        },
        dynamic_hit_count_nukes={
            "asuka-shikinami-langley-wille": build_annihilation_dynamic_hit_count_nukes(ASUKA_VALUES),
            "maiden-ice-rose": build_diamond_dust_dynamic_hit_count_nukes(MAIDEN_VALUES),
        },
    )
    hits = [e for e in result["damage_log"] if e["source"] == "dynamic_hit_count_nuke"]
    asuka_hits = [h for h in hits if h["slug"] == "asuka-shikinami-langley-wille"]
    maiden_hits = [h for h in hits if h["slug"] == "maiden-ice-rose"]

    # Asuka: unaffected by Maiden's presence - her burst still fires at
    # t=5.0, her Anti A.T. Field resource (her own MG shots only) still caps
    # at 30 stacks before the delayed nuke fires 9s later, and that nuke
    # still lands inside HER OWN full burst window [5.0, 15.0) for the bonus.
    assert len(asuka_hits) == 30
    assert all(round(h["time"], 4) == 14.0 for h in asuka_hits)
    assert all(round(h["damage"], 4) == 993.0 for h in asuka_hits)  # 10000*6.62%*1.5

    # Maiden: her own burst only comes up every OTHER cycle here (Asuka takes
    # cycle 1), which flips a rule her module docstring calls a "provable
    # no-op" in solo play - MP's second fill ("+1 if MP is currently >=1, on
    # entering Full Burst") was a no-op ONLY because her own burst (which
    # resets MP to 0) always fires immediately before full_burst_start in the
    # SAME cycle when she's the sole tier-3 unit. Here, cycle 1's
    # full_burst_start is opened by ASUKA's burst instead, so Maiden's MP -
    # already filled to 1 by buffer's tier-1 fire earlier that same cycle -
    # is still 1 (not reset) when full_burst_start fires, so the >=1 rule
    # legitimately fires too, bumping MP to 2. Cycle 2's tier-1 fire is a
    # no-op (MP already !=0), then Maiden's own burst (cycle 2) reads that
    # pre-reset count of 2, hits twice, and resets to 0. Both fire at her own
    # burst time (no fire_delay), with no full-burst bonus even though
    # t=25.0 is also the instant her own window opens.
    assert len(maiden_hits) == 2
    assert all(round(h["time"], 4) == 25.0 for h in maiden_hits)
    assert all(round(h["damage"], 4) == 205920.0 for h in maiden_hits)  # 15000 * 13.728, no bonus
