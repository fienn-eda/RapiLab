from app.raid_simulator import simulate_raid

# A burst cycle needs one member per tier (1, 2, 3) to complete at all - see
# burst_cycle's "full_burst_missed" check - so "attacker" (tier 3, carrying
# the DoT specs under test) needs tier-1/2 squadmates even though their own
# damage is irrelevant here.
RULES_BY_SLUG = {"buffer": [], "midtier": [], "attacker": []}


def make_deck():
    return [
        {"slug": "buffer", "burst_tier": 1, "element": "Iron", "cooldown": 20.0},
        {"slug": "midtier", "burst_tier": 2, "element": "Iron", "cooldown": 20.0},
        {"slug": "attacker", "burst_tier": 3, "element": "Iron", "cooldown": 40.0},
    ]


def make_base_stats():
    return {
        "buffer": {"atk": 0, "def": 0, "max_hp": 0},
        "midtier": {"atk": 0, "def": 0, "max_hp": 0},
        "attacker": {"atk": 100000.0, "def": 5000.0, "max_hp": 500000.0},
    }


def _total(part_destructible, floor_spec, ceiling_periodic):
    result = simulate_raid(
        make_deck(),
        RULES_BY_SLUG,
        burst_damage_percents={},
        base_stats=make_base_stats(),
        enemy_def=0,
        gauge_charge_time=5.0,
        fight_duration=20.0,
        mode="auto",
        base_crit_rate=0.0,
        part_destructible=part_destructible,
        resource_scaled_nukes={"attacker": floor_spec},
        periodic_nukes={"attacker": ceiling_periodic},
    )
    return result["total_damage"]


FLOOR = [{
    "base_percent": 100.0, "tick_count": 1, "tick_interval": 1.0,
    "damage_type": "sustained", "requires_part_destructible": False,
}]
CEILING = {
    "cooldown": 1.0, "percent": 100.0, "damage_type": "sustained",
    "requires_part_destructible": True,
}


def test_floor_dot_only_fires_when_not_part_destructible():
    assert _total(False, FLOOR, CEILING) > 0  # floor spec active, ceiling skipped
    # Same floor spec must be skipped when part_destructible is True:
    only_floor = _total(True, FLOOR, {"cooldown": 1.0, "percent": 0.0})
    only_floor_off = _total(False, [], {"cooldown": 1.0, "percent": 0.0})
    assert only_floor == only_floor_off  # floor contributed nothing when flag True


def test_ceiling_periodic_only_fires_when_part_destructible():
    with_flag = _total(True, [], CEILING)
    without_flag = _total(False, [], CEILING)
    assert with_flag > 0
    assert without_flag == 0


NO_FLAG_PERIODIC = {"cooldown": 1.0, "percent": 100.0, "damage_type": "sustained"}


def test_periodic_without_flag_fires_regardless_of_part_destructible():
    # requires_part_destructible omitted + nonzero percent: must fire
    # identically whether the part is destructible or not (backward
    # compatibility with specs predating the flag).
    with_flag = _total(True, [], NO_FLAG_PERIODIC)
    without_flag = _total(False, [], NO_FLAG_PERIODIC)
    assert with_flag == without_flag
    assert with_flag > 0
