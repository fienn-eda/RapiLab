from app.effects import Effect, Pulse
from app.raid_simulator import simulate_raid
from app.squad_engine import SkillRule


def make_deck():
    return [
        {"slug": "buffer", "burst_tier": 1, "element": "Iron", "cooldown": 20.0},
        {"slug": "midtier", "burst_tier": 2, "element": "Iron", "cooldown": 20.0},
        {"slug": "attacker", "burst_tier": 3, "element": "Iron", "cooldown": 40.0},
    ]


def make_base_stats(attacker_atk=10000):
    return {
        "buffer": {"atk": 0, "def": 0, "max_hp": 0},
        "midtier": {"atk": 0, "def": 0, "max_hp": 0},
        "attacker": {"atk": attacker_atk, "def": 0, "max_hp": 0},
    }


def test_battle_start_buff_is_active_by_the_time_the_burst_fires():
    def grant_atk_buff(context, caster_slug, time, registry):
        registry.add(Effect("atk_percent", 0.5, "self", None, "attacker"), applied_at=time)

    rules_by_slug = {
        "buffer": [SkillRule(trigger="battle_start", action=grant_atk_buff)],
        "midtier": [],
        "attacker": [],
    }
    result = simulate_raid(
        make_deck(),
        rules_by_slug,
        burst_damage_percents={"attacker": 1000.0},
        base_stats=make_base_stats(),
        enemy_def=0,
        gauge_charge_time=5.0,
        fight_duration=20.0,
        mode="auto",
    )

    assert len(result["damage_log"]) == 1
    entry = result["damage_log"][0]
    assert entry == {"slug": "attacker", "time": 5.0, "damage": 150000.0, "source": "burst"}
    assert result["total_damage"] == 150000.0


def test_core_hittable_true_doubles_burst_damage_via_200_percent_core_bonus():
    rules_by_slug = {"buffer": [], "midtier": [], "attacker": []}
    without_core = simulate_raid(
        make_deck(),
        rules_by_slug,
        burst_damage_percents={"attacker": 500.0},
        base_stats=make_base_stats(attacker_atk=2000),
        enemy_def=0,
        gauge_charge_time=5.0,
        fight_duration=20.0,
        mode="auto",
    )
    with_core = simulate_raid(
        make_deck(),
        rules_by_slug,
        burst_damage_percents={"attacker": 500.0},
        base_stats=make_base_stats(attacker_atk=2000),
        enemy_def=0,
        gauge_charge_time=5.0,
        fight_duration=20.0,
        mode="auto",
        core_hittable=True,
    )
    # per Fienn's in-game tooltip check, core damage is a uniform 200% across
    # every weapon type (+1.0 to the major modifier), i.e. exactly double a
    # hit with no other modifiers active.
    assert with_core["total_damage"] == without_core["total_damage"] * 2
    assert without_core["total_damage"] == 10000.0


def test_burst_damage_with_no_buffs_uses_plain_percent_of_atk():
    rules_by_slug = {"buffer": [], "midtier": [], "attacker": []}
    result = simulate_raid(
        make_deck(),
        rules_by_slug,
        burst_damage_percents={"attacker": 500.0},
        base_stats=make_base_stats(attacker_atk=2000),
        enemy_def=0,
        gauge_charge_time=5.0,
        fight_duration=20.0,
        mode="auto",
    )
    # atk_for_hit = 2000 * 5.0 = 10000; no buffs, no enemy def -> damage == 10000
    assert result["total_damage"] == 10000.0


def test_own_burst_activate_only_fires_for_the_unit_whose_tier_just_fired():
    fired = []

    def record(context, caster_slug, time, registry):
        fired.append(caster_slug)

    rules_by_slug = {
        "buffer": [SkillRule(trigger="own_burst_activate", action=record)],
        "midtier": [SkillRule(trigger="own_burst_activate", action=record)],
        "attacker": [SkillRule(trigger="own_burst_activate", action=record)],
    }
    simulate_raid(
        make_deck(),
        rules_by_slug,
        burst_damage_percents={},
        base_stats=make_base_stats(),
        enemy_def=0,
        gauge_charge_time=5.0,
        fight_duration=20.0,
        mode="auto",
    )
    # each unit's own_burst_activate should fire exactly once, for itself only
    assert sorted(fired) == ["attacker", "buffer", "midtier"]


def test_cooldown_reduction_pulse_from_full_burst_end_enables_a_second_cycle():
    def emit_cdr_pulse(context, caster_slug, time, registry):
        registry.add_pulse(Pulse("burst_cooldown_reduction_sec", 30.0, "squad", caster_slug))

    rules_by_slug = {
        "buffer": [SkillRule(trigger="full_burst_end", action=emit_cdr_pulse)],
        "midtier": [],
        "attacker": [],
    }
    result = simulate_raid(
        make_deck(),
        rules_by_slug,
        burst_damage_percents={"attacker": 100.0},
        base_stats=make_base_stats(attacker_atk=1000),
        enemy_def=0,
        gauge_charge_time=5.0,
        fight_duration=35.0,
        mode="auto",
    )
    # Without the pulse, cycle 2 (fire_time=20) would need attacker's 40s
    # cooldown satisfied (used at t=5, ready at t=45) - it isn't. A 30s
    # reduction applied to every Nikke's last-used-at at t=15 makes tier1/2
    # (20s cooldown, needs >=5s reduction) AND attacker (40s cooldown, needs
    # >=25s reduction) all eligible again by t=20.
    attacker_hits = [e for e in result["damage_log"] if e["slug"] == "attacker"]
    assert [e["time"] for e in attacker_hits] == [5.0, 20.0]


def test_full_burst_enter_and_full_burst_end_triggers_fire_for_all_members():
    enter_calls = []
    end_calls = []

    rules_by_slug = {
        "buffer": [
            SkillRule(trigger="full_burst_enter", action=lambda c, s, t, r: enter_calls.append((s, t))),
            SkillRule(trigger="full_burst_end", action=lambda c, s, t, r: end_calls.append((s, t))),
        ],
        "midtier": [],
        "attacker": [],
    }
    simulate_raid(
        make_deck(),
        rules_by_slug,
        burst_damage_percents={},
        base_stats=make_base_stats(),
        enemy_def=0,
        gauge_charge_time=5.0,
        fight_duration=20.0,
        mode="auto",
    )
    assert enter_calls == [("buffer", 5.0)]
    assert end_calls == [("buffer", 15.0)]


def test_normal_attack_damage_is_accumulated_for_magazine_weapons():
    rules_by_slug = {"buffer": [], "midtier": [], "attacker": []}
    weapon_stats = {
        "attacker": {
            "weapon": "AR", "damage_percent": 10.0, "max_ammo": 2,
            "reload_time": 100.0, "charge_time": 0.0, "charge_damage_percent": 100.0,
        }
    }
    result = simulate_raid(
        make_deck(),
        rules_by_slug,
        burst_damage_percents={},
        base_stats=make_base_stats(attacker_atk=1000),
        enemy_def=0,
        gauge_charge_time=5.0,
        fight_duration=1.0,
        mode="auto",
        weapon_stats=weapon_stats,
    )
    # AR fires at 12/sec (Fienn's 60fps table); with a 100s reload, only the
    # first magazine's shots within the 1s fight matter: shots at t=0 and
    # t=1/12 (2nd shot at 2/12=0.1667s is still <1.0, so both of the 2-round
    # magazine's shots land). damage_percent=10% -> atk_for_hit=100 each hit.
    normal_hits = [e for e in result["damage_log"] if e["source"] == "normal_attack"]
    assert len(normal_hits) == 2
    assert all(e["damage"] == 100.0 for e in normal_hits)
    assert result["total_damage"] == 200.0


def test_normal_attack_damage_uses_live_buffs_at_shot_time():
    def grant_atk_buff(context, caster_slug, time, registry):
        registry.add(Effect("atk_percent", 1.0, "self", None, "attacker"), applied_at=time)

    rules_by_slug = {
        "buffer": [SkillRule(trigger="battle_start", action=grant_atk_buff)],
        "midtier": [],
        "attacker": [],
    }
    weapon_stats = {
        "attacker": {
            "weapon": "AR", "damage_percent": 10.0, "max_ammo": 1,
            "reload_time": 100.0, "charge_time": 0.0, "charge_damage_percent": 100.0,
        }
    }
    result = simulate_raid(
        make_deck(),
        rules_by_slug,
        burst_damage_percents={},
        base_stats=make_base_stats(attacker_atk=1000),
        enemy_def=0,
        gauge_charge_time=5.0,
        fight_duration=1.0,
        mode="auto",
        weapon_stats=weapon_stats,
    )
    # atk_for_hit=100, atk_percent buff of +100% (granted at battle_start,
    # active for the shot at t=0) doubles it to 200.
    normal_hits = [e for e in result["damage_log"] if e["source"] == "normal_attack"]
    assert normal_hits[0]["damage"] == 200.0


def test_normal_attack_damage_for_charge_weapon_applies_charge_damage_bonus():
    rules_by_slug = {"buffer": [], "midtier": [], "attacker": []}
    weapon_stats = {
        "attacker": {
            "weapon": "RL", "damage_percent": 10.0, "max_ammo": 6,
            "reload_time": 100.0, "charge_time": 1.0, "charge_damage_percent": 250.0,
        }
    }
    result = simulate_raid(
        make_deck(),
        rules_by_slug,
        burst_damage_percents={},
        base_stats=make_base_stats(attacker_atk=1000),
        enemy_def=0,
        gauge_charge_time=5.0,
        fight_duration=1.5,
        mode="auto",
        weapon_stats=weapon_stats,
    )
    # one shot at t=1.0 (charge_time); atk_for_hit=100, charge_damage_bonus
    # = 250/100-1 = 1.5 -> charge_damage multiplier = 1+1.5 = 2.5 -> 250.
    normal_hits = [e for e in result["damage_log"] if e["source"] == "normal_attack"]
    assert len(normal_hits) == 1
    assert normal_hits[0]["damage"] == 250.0


def test_slug_missing_from_weapon_stats_gets_no_normal_attack_damage():
    rules_by_slug = {"buffer": [], "midtier": [], "attacker": []}
    result = simulate_raid(
        make_deck(),
        rules_by_slug,
        burst_damage_percents={},
        base_stats=make_base_stats(attacker_atk=1000),
        enemy_def=0,
        gauge_charge_time=5.0,
        fight_duration=10.0,
        mode="auto",
        weapon_stats={},
    )
    assert result["damage_log"] == []


def test_burst_used_this_cycle_resets_between_cycles():
    seen_at_second_cycle = []

    def emit_cdr_pulse(context, caster_slug, time, registry):
        registry.add_pulse(Pulse("burst_cooldown_reduction_sec", 15.0, "squad", caster_slug))

    def check_burst_used(context, caster_slug, time, registry):
        if time > 15.0:  # only care about the second cycle's tier-1 firing
            seen_at_second_cycle.append(set(context.burst_used_this_cycle))

    rules_by_slug = {
        "buffer": [
            SkillRule(trigger="full_burst_end", action=emit_cdr_pulse),
            SkillRule(trigger="own_burst_activate", action=check_burst_used),
        ],
        "midtier": [],
        "attacker": [],
    }
    simulate_raid(
        make_deck(),
        rules_by_slug,
        burst_damage_percents={},
        base_stats=make_base_stats(),
        enemy_def=0,
        gauge_charge_time=5.0,
        fight_duration=35.0,
        mode="auto",
    )
    # at the moment buffer's tier1 burst fires in cycle 2, only itself should
    # be recorded as "used this cycle" so far - the previous cycle's usage
    # must have been cleared.
    assert seen_at_second_cycle == [{"buffer"}]
