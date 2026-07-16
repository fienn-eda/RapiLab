"""resource_fill_triggered_buffs (gap #8): a buff triggered by a resource's
FILL events, landing on OTHER squad members selected by a live filter (e.g.
Maiden's Blessings Upon You: "when MP is replenished, affects all Electric
Code allies except for self"). Applied refreshing - consecutive fills inside
the duration refresh rather than stack (NIKKE convention)."""
from app.effects import ResourceSpec
from app.raid_simulator import simulate_raid
from app.squad_engine import boss_is_element


def _deck():
    return [
        {"slug": "owner", "burst_tier": 1, "element": "Water", "cooldown": 20.0},
        {"slug": "electric-ally", "burst_tier": 2, "element": "Electric", "cooldown": 20.0},
        {"slug": "fire-ally", "burst_tier": 3, "element": "Fire", "cooldown": 20.0},
    ]


def _ar_weapon():
    return {"weapon": "AR", "damage_percent": 10.0, "max_ammo": 10000,
            "reload_time": 1.0, "charge_time": 0.0, "charge_damage_percent": 100.0}


def _run(fill_interval, fill_buffs, fight_duration=20.0, boss_element=None):
    deck = _deck()
    spec = ResourceSpec(name="gauge", fill=("periodic", fill_interval), cap=99)
    return simulate_raid(
        deck=deck,
        rules_by_slug={m["slug"]: [] for m in deck},
        burst_damage_percents={},
        base_stats={m["slug"]: {"atk": 10000} for m in deck},
        enemy_def=0,
        gauge_charge_time=5.0,
        fight_duration=fight_duration,
        base_crit_rate=0.0,
        boss_element=boss_element,
        weapon_stats={"electric-ally": _ar_weapon(), "fire-ally": _ar_weapon()},
        resource_specs={"owner": [spec]},
        resource_fill_triggered_buffs=fill_buffs,
    )


def _electric_except_owner(member, owner_slug):
    return member.element == "Electric" and member.slug != owner_slug


def _shots(result, slug):
    return [(e["time"], e["damage"]) for e in result["damage_log"]
            if e["source"] == "normal_attack" and e["slug"] == slug]


def test_buff_steps_up_at_fill_times_for_matching_members_only():
    # gauge fills at t=10; atk_percent +0.5 for 5s on Electric allies except
    # the owner -> the Electric ally's shots are 1.5x inside [10, 15) only.
    result = _run(10.0, {"owner": [{
        "resource": "gauge",
        "member_filter": _electric_except_owner,
        "buffs": [("atk_percent", 0.5, 5.0)],
    }]})
    for t, damage in _shots(result, "electric-ally"):
        expected = 1500.0 if 10.0 <= t < 15.0 else 1000.0
        assert round(damage, 4) == expected, (t, damage)
    assert all(round(d, 4) == 1000.0 for _, d in _shots(result, "fire-ally"))


def test_overlapping_fills_refresh_instead_of_stacking():
    # fills at 6/12/18, duration 8 -> windows overlap; refreshing keeps the
    # buff at its single value (1.5x, never 2x) continuously from t=6 on.
    result = _run(6.0, {"owner": [{
        "resource": "gauge",
        "member_filter": _electric_except_owner,
        "buffs": [("atk_percent", 0.5, 8.0)],
    }]})
    for t, damage in _shots(result, "electric-ally"):
        expected = 1500.0 if t >= 6.0 else 1000.0
        assert round(damage, 4) == expected, (t, damage)


def test_condition_gates_the_spec():
    # A boss_is_element("Water") spec is inert against a Fire boss. (Fire boss
    # is element-neutral for both attackers, so damage stays at baseline.)
    result = _run(10.0, {"owner": [{
        "resource": "gauge",
        "member_filter": _electric_except_owner,
        "buffs": [("atk_percent", 0.5, 5.0)],
        "condition": boss_is_element("Water"),
    }]}, boss_element="Fire")
    assert all(round(d, 4) == 1000.0 for _, d in _shots(result, "electric-ally"))


def test_default_is_a_no_op():
    baseline = _run(10.0, None)
    with_empty = _run(10.0, {})
    assert with_empty["total_damage"] == baseline["total_damage"]
