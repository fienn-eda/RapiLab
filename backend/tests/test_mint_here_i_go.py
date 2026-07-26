"""End-to-end for Mint's Here I Go! (squad ATK on every Full Charge while
Singing) through simulate_raid: the SOLO path (per-cycle Dancing/Singing parity
reconstructed from her burst times) and the COMBO path (Prika's Encore pins
Singing from a specific time, so shots BEFORE the pin are correctly excluded).
"""
from app.raid_simulator import simulate_raid
from app.skill_rules.mint import build_here_i_go_rules, build_mint_rules
from app.skill_rules.prika import build_prika_rules

HERE_I_GO = {"description_value_01": "45.02", "description_value_02": "3", "caster_atk": 200000}
PRIKA_SHOW = {"description_value_01": "3.04", "description_value_02": "25",
              "description_value_03": "25", "description_value_04": "25"}
PRIKA_ENCORE = {"description_value_01": "19.98", "description_value_02": "10", "description_value_03": "21",
                "description_value_04": "25.01", "description_value_05": "10", "description_value_06": "21"}
MINT_SING = {"description_value_01": "30.02", "description_value_02": "10", "description_value_03": "40",
             "description_value_04": "10", "description_value_05": "45.05", "description_value_06": "10"}
MINT_FANTASTIC = {"description_value_01": "19.94", "description_value_02": "10", "description_value_03": "50",
                  "description_value_04": "10", "description_value_05": "32.72", "description_value_06": "10"}


def _rl_weapon():
    return {"weapon": "RL", "damage_percent": 10.0, "max_ammo": 10,
            "reload_time": 2.0, "charge_time": 1.0, "charge_damage_percent": 0.0}


def test_solo_here_i_go_toggles_squad_atk_with_dancing_and_singing_cycles():
    # Mint is the only Burst-2, so she bursts every cycle: cycle 1 -> Dancing
    # [5,25), cycle 2 -> Singing [25,45). Her rules are isolated to Here I Go
    # (empty event rules) so the buff is the only squad effect. An attacker
    # periodic nuke every 1s samples the timeline.
    deck = [
        {"slug": "b1", "burst_tier": 1, "element": "Iron", "cooldown": 20.0},
        {"slug": "mint", "burst_tier": 2, "element": "Iron", "cooldown": 20.0},
        {"slug": "attacker", "burst_tier": 3, "element": "Iron", "cooldown": 20.0},
    ]
    base_stats = {"b1": {"atk": 0, "def": 0, "max_hp": 0},
                  "mint": {"atk": 200000, "def": 0, "max_hp": 0},
                  "attacker": {"atk": 10000, "def": 0, "max_hp": 0}}
    result = simulate_raid(
        deck,
        {"b1": [], "mint": [], "attacker": []},
        burst_damage_percents={},
        base_stats=base_stats,
        enemy_def=0,
        gauge_charge_time=5.0,
        fight_duration=40.0,
        mode="auto",
        base_crit_rate=0.0,
        weapon_stats={"mint": _rl_weapon()},
        per_shot_rules={"mint": build_here_i_go_rules(HERE_I_GO)},
        periodic_nukes={"attacker": {"cooldown": 1.0, "percent": 100.0}},
    )
    periodic = {round(e["time"], 1): e["damage"] for e in result["damage_log"] if e["source"] == "periodic"}
    assert periodic[10.0] == 10000.0             # Dancing cycle -> no Here I Go buff
    assert round(periodic[30.0], 2) == 100040.0  # Singing cycle -> +45.02% of Mint's 200000 ATK (flat_atk 90040)


def test_combo_here_i_go_excludes_shots_before_prikas_encore_pins_singing():
    # Prika bursts cycle 1, Mint bursts cycle 2 (t=25) -> Encore pins Singing at
    # t=25. Mint's shots BEFORE t=25 must NOT carry Here I Go, so the attacker's
    # cycle-1 burst reflects only Prika's Charge Damage (+25%), no Mint flat_atk.
    deck = [
        {"slug": "b1", "burst_tier": 1, "element": "Iron", "cooldown": 20.0},
        {"slug": "prika", "burst_tier": 2, "element": "Water", "cooldown": 40.0},
        {"slug": "mint", "burst_tier": 2, "element": "Iron", "cooldown": 20.0},
        {"slug": "attacker", "burst_tier": 3, "element": "Iron", "cooldown": 20.0},
    ]
    rules_by_slug = {
        "b1": [],
        "prika": build_prika_rules({"get_ready_for_an_amazing_show": PRIKA_SHOW, "one_more_song": PRIKA_ENCORE}),
        "mint": build_mint_rules({"lets_sing_together": MINT_SING, "fantastic_performance": MINT_FANTASTIC}),
        "attacker": [],
    }
    base_stats = {"b1": {"atk": 0, "def": 0, "max_hp": 0},
                  "prika": {"atk": 0, "def": 0, "max_hp": 0},
                  "mint": {"atk": 200000, "def": 0, "max_hp": 0},
                  "attacker": {"atk": 10000, "def": 0, "max_hp": 0}}
    result = simulate_raid(
        deck,
        rules_by_slug,
        burst_damage_percents={"attacker": 100.0},
        base_stats=base_stats,
        enemy_def=0,
        gauge_charge_time=5.0,
        fight_duration=30.0,
        mode="auto",
        base_crit_rate=0.0,
        weapon_stats={"mint": _rl_weapon(), "attacker": _rl_weapon()},
        per_shot_rules={"mint": build_here_i_go_rules(HERE_I_GO)},
    )
    attacker_bursts = {round(e["time"], 1): e["damage"] for e in result["damage_log"] if e["source"] == "burst"}
    # Bare: Mint's flat_atk has not landed (her shots precede the Singing pin),
    # and Prika's Charge Damage never reaches a BURST nuke - Charge Damage is a
    # normal-attack-only modifier, whatever weapon the caster holds.
    assert attacker_bursts[5.0] == 10000.0
