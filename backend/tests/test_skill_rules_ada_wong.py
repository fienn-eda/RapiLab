"""Ada Wong: Covert Support bursted-B3 subset buffs (gap #3), Flash Grenade
during-FB true-damage periodic nuke with own-burst 1s enhancement (gap #6),
Secret Agent self buffs + Special Modification as a one-shot segment (x4 charge
time AND the full Charge Damage - see the module docstring for why a segment is
what finally lets both halves land)."""
from app.effects import EffectRegistry
from app.raid_simulator import simulate_raid
from app.skill_rules._helpers import round_buff_rule
from app.skill_rules.ada_wong import build_ada_wong_rules, build_flash_grenade_periodic_nuke
from app.skill_rules.registry import build_nikke_rules, get_periodic_nuke
from app.squad_engine import SquadContext, SquadMember, fire_trigger

# Real level-10 values (lootandwaifus 2026-07-16 file), slots numbered by
# left-to-right appearance.
COVERT_SUPPORT = {
    "description_value_01": "60",   # bursted-B3 ATK % of caster's ATK
    "description_value_02": "10",   # its duration
    "description_value_03": "50",   # bursted-B3 True Damage %
    "description_value_04": "10",   # its duration
    "description_value_05": "10",   # HP recovery % (not modeled)
    "description_value_06": "10",   # its duration
}
FLASH_GRENADE = {
    "description_value_01": "2",    # tick interval during Full Burst (sec)
    "description_value_02": "420",  # % of final ATK as True Damage per tick
    "description_value_03": "1",    # enhanced interval after her own burst (sec)
    "description_value_04": "10",   # enhancement duration (sec)
}
SECRET_AGENT = {
    "description_value_01": "40",    # self ATK %
    "description_value_02": "10",    # its duration
    "description_value_03": "42",    # self True Damage %
    "description_value_04": "10",    # its duration
    "description_value_05": "1",     # Special Modification round count
    "description_value_06": "300",   # Charge Speed down % (time x4)
    "description_value_07": "1500",  # Charge Damage up %
}
VALUES = {
    "covert_support": COVERT_SUPPORT,
    "flash_grenade": FLASH_GRENADE,
    "secret_agent": SECRET_AGENT,
    "caster_atk": 100000.0,
}


def build():
    return build_ada_wong_rules(VALUES)


def test_registry_burst_percent_is_none():
    rules, burst_percent = build_nikke_rules("ada-wong", VALUES)
    assert burst_percent is None
    assert rules
    assert get_periodic_nuke("ada-wong", VALUES) == build_flash_grenade_periodic_nuke(VALUES)


def test_covert_support_hits_only_bursted_b3_allies():
    ctx = SquadContext([
        SquadMember("ada-wong", 3, "Electric"),
        SquadMember("bursted-b3", 3, "Fire"),
        SquadMember("idle-b3", 3, "Fire"),
        SquadMember("bursted-b1", 1, "Fire"),
    ])
    ctx.burst_used_this_cycle.update({"ada-wong", "bursted-b3", "bursted-b1"})
    registry = EffectRegistry()
    fire_trigger("full_burst_enter", {"ada-wong": build()}, ctx, registry, time=5.0)

    bursted = {"slug": "bursted-b3", "element": "Fire"}
    assert registry.total_for("flat_atk", bursted, 5.0) == 60000.0  # 60% of 100000
    assert registry.total_for("true_damage_up", bursted, 5.0) == 0.50
    # Ada herself matches once her burst fired
    ada = {"slug": "ada-wong", "element": "Electric"}
    assert registry.total_for("flat_atk", ada, 5.0) == 60000.0
    # non-bursted B3 and bursted B1 excluded
    assert registry.total_for("flat_atk", {"slug": "idle-b3", "element": "Fire"}, 5.0) == 0.0
    assert registry.total_for("flat_atk", {"slug": "bursted-b1", "element": "Fire"}, 5.0) == 0.0
    # 10s durations
    assert registry.total_for("flat_atk", bursted, 15.1) == 0.0
    assert registry.total_for("true_damage_up", bursted, 15.1) == 0.0


def test_secret_agent_self_buffs():
    ctx = SquadContext([SquadMember("ada-wong", 3, "Electric")])
    registry = EffectRegistry()
    fire_trigger("own_burst_activate", {"ada-wong": build()}, ctx, registry, time=5.0)

    ada = {"slug": "ada-wong", "element": "Electric"}
    assert registry.total_for("atk_percent", ada, 5.0) == 0.40
    assert registry.total_for("true_damage_up", ada, 5.0) == 0.42
    assert registry.total_for("atk_percent", ada, 15.1) == 0.0

    # Special Modification is NOT a round grant any more: it has to change the
    # charge TIME as well as the damage, which only a segment can state.
    assert registry.round_grants() == []


def test_special_modification_is_one_slow_heavy_shot_then_the_plain_rl():
    from app.skill_rules.ada_wong import build_special_modification_weapon_mode_schedule

    values = dict(VALUES, caster_weapon_stats={
        "weapon": "RL", "damage_percent": 61.3, "charge_time": 1.0,
        "charge_damage_percent": 250.0, "max_ammo": 6, "reload_time": 2.0})
    schedule = build_special_modification_weapon_mode_schedule(values)

    class _Context:
        burst_times = {"ada-wong": [2.6, 42.6]}

    segments = schedule(_Context(), 180.0)
    assert [s["start"] for s in segments] == [2.6, 42.6]
    for segment in segments:
        # "for 1 round(s)" - exactly one shot, then the base weapon resumes.
        assert segment["until_shots"] == 1
        # Charge Speed v300% = charge time x4, the half the old net-damage
        # approximation could never pay.
        assert segment["profile"]["charge_time"] == 4.0
        # Charge Damage is one additive group: her weapon's 250% plus the
        # skill's 1500%, NOT the 275% the scaled-down approximation implied.
        assert segment["profile"]["charge_damage_percent"] == 1750.0
        assert segment["profile"]["damage_percent"] == 61.3


def test_a_burst_past_the_bell_opens_no_segment():
    from app.skill_rules.ada_wong import build_special_modification_weapon_mode_schedule

    values = dict(VALUES, caster_weapon_stats={
        "weapon": "RL", "damage_percent": 61.3, "charge_time": 1.0,
        "charge_damage_percent": 250.0, "max_ammo": 6, "reload_time": 2.0})

    class _Context:
        burst_times = {"ada-wong": [2.6, 190.0]}

    assert [s["start"] for s in
            build_special_modification_weapon_mode_schedule(values)(_Context(), 180.0)] == [2.6]


def test_flash_grenade_spec():
    spec = build_flash_grenade_periodic_nuke(VALUES)
    assert spec == {
        "cooldown": 2.0,
        "percent": 420.0,
        "damage_type": "true",
        "during_full_burst": True,
        "own_burst_interval": (1.0, 10.0),
    }


def _run_deck(rules_by_ada, periodic_nukes=None, ada_tier=3, weapon_stats=None):
    deck = [
        {"slug": "b1", "burst_tier": 1, "element": "Fire", "cooldown": 20.0},
        {"slug": "b2", "burst_tier": 2, "element": "Fire", "cooldown": 20.0},
        {"slug": "ada-wong", "burst_tier": ada_tier, "element": "Electric", "cooldown": 40.0},
    ]
    if ada_tier != 3:
        deck.append({"slug": "b3", "burst_tier": 3, "element": "Fire", "cooldown": 20.0})
    return simulate_raid(
        deck=deck,
        rules_by_slug={m["slug"]: (rules_by_ada if m["slug"] == "ada-wong" else []) for m in deck},
        burst_damage_percents={},
        base_stats={m["slug"]: {"atk": 100000.0} for m in deck},
        enemy_def=0,
        gauge_charge_time=5.0,
        fight_duration=30.0,
        base_crit_rate=0.0,
        periodic_nukes=periodic_nukes or {},
        weapon_stats=weapon_stats or {},
    )


def _fb_windows(result):
    return list(zip(
        (e["time"] for e in result["events"] if e["type"] == "full_burst_start"),
        (e["time"] for e in result["events"] if e["type"] == "full_burst_end"),
    ))


def test_flash_grenade_ticks_at_1s_in_windows_opened_by_her_burst():
    result = _run_deck([], periodic_nukes={"ada-wong": build_flash_grenade_periodic_nuke(VALUES)})
    windows = _fb_windows(result)
    ticks = [e for e in result["damage_log"] if e["source"] == "periodic"]
    assert ticks
    for e in ticks:
        assert e["damage_type"] == "true"
        assert any(start < e["time"] < end for start, end in windows)
    # Ada is the only B3 -> every window opens with her burst -> 1s ticks.
    start, end = windows[0]
    in_window = sorted(e["time"] for e in ticks if start <= e["time"] < end)
    assert in_window == [start + i for i in range(1, 10)]


def test_flash_grenade_keeps_2s_ticks_when_ada_never_bursts():
    # Ada parked as a second B1 behind an always-ready one: she never bursts,
    # so no window gets the 1s enhancement.
    result = _run_deck([], periodic_nukes={"ada-wong": build_flash_grenade_periodic_nuke(VALUES)},
                       ada_tier=1)
    windows = _fb_windows(result)
    ticks = sorted(e["time"] for e in result["damage_log"] if e["source"] == "periodic")
    start, end = windows[0]
    in_window = [t for t in ticks if start <= t < end]
    assert in_window == [start + 2.0, start + 4.0, start + 6.0, start + 8.0]


def test_true_damage_up_raises_flash_grenade_ticks():
    # Ada's own Secret Agent true_damage_up is a consumer of her true-typed
    # Flash Grenade ticks.
    spec = {"ada-wong": build_flash_grenade_periodic_nuke(VALUES)}
    without = _run_deck([], periodic_nukes=spec)
    with_rules = _run_deck(build(), periodic_nukes=spec)
    tick_without = next(e for e in without["damage_log"] if e["source"] == "periodic")
    tick_with = next(e for e in with_rules["damage_log"] if e["source"] == "periodic")
    assert tick_with["time"] == tick_without["time"]
    assert tick_with["damage"] > tick_without["damage"]


def test_one_round_charge_speed_grant_is_inert_mid_magazine():
    # The magazine-boundary trap behind the Special Modification net
    # approximation (Fienn ruling 2026-07-16, Task-7 verification): charge
    # speed is evaluated once per magazine start, so a 1-round
    # charge_speed_percent Effect granted mid-magazine covers no magazine
    # boundary and never slows anything - modeling the raw pair would credit
    # the +1500% charge damage without paying the x4 charge time.
    weapon = {"ada-wong": {"weapon": "RL", "damage_percent": 68.44, "max_ammo": 6,
                           "reload_time": 2.0, "charge_time": 1.0,
                           "charge_damage_percent": 250.0}}
    slow_pair = [round_buff_rule("own_burst_activate",
                                 [("charge_speed_percent", -0.75, "self")], shots=1)]
    base = _run_deck([], weapon_stats=weapon)
    slowed = _run_deck(slow_pair, weapon_stats=weapon)
    times_base = [round(e["time"], 6) for e in base["damage_log"] if e["source"] == "normal_attack"]
    times_slowed = [round(e["time"], 6) for e in slowed["damage_log"] if e["source"] == "normal_attack"]
    assert times_base and times_base == times_slowed
