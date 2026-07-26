"""End-to-end: the Prika->Mint Encore synergy through the full simulate_raid
pipeline, using the REAL builders and the `ally_burst_activate` cross-unit
trigger. The deck's cooldowns force the intended rotation - Prika bursts first
(cycle 1), Mint bursts after (cycle 2) - and the assertion checks that Prika's
Encore squad Attack Damage (fired on Mint's burst) reaches the attacker's burst
nuke that cycle. Real skill values match test_skill_rules_mint/prika.
"""
from app.raid_simulator import simulate_raid
from app.skill_rules.mint import build_mint_rules
from app.skill_rules.prika import build_prika_rules

MINT_SING_TOGETHER = {
    "description_value_01": "30.02", "description_value_02": "10", "description_value_03": "40",
    "description_value_04": "10", "description_value_05": "45.05", "description_value_06": "10",
}
MINT_FANTASTIC = {
    "description_value_01": "19.94", "description_value_02": "10", "description_value_03": "50",
    "description_value_04": "10", "description_value_05": "32.72", "description_value_06": "10",
}
PRIKA_SHOW = {
    "description_value_01": "3.04", "description_value_02": "25",
    "description_value_03": "25", "description_value_04": "25",
}
PRIKA_ENCORE = {
    "description_value_01": "19.98", "description_value_02": "10", "description_value_03": "21",
    "description_value_04": "25.01", "description_value_05": "10", "description_value_06": "21",
}


def test_encore_squad_attack_damage_reaches_the_attacker_burst_through_the_pipeline():
    deck = [
        {"slug": "b1", "burst_tier": 1, "element": "Iron", "cooldown": 20.0},
        {"slug": "prika", "burst_tier": 2, "element": "Water", "cooldown": 40.0},
        {"slug": "mint", "burst_tier": 2, "element": "Iron", "cooldown": 20.0},
        {"slug": "attacker", "burst_tier": 3, "element": "Iron", "cooldown": 20.0},
    ]
    rules_by_slug = {
        "b1": [],
        "prika": build_prika_rules({"get_ready_for_an_amazing_show": PRIKA_SHOW, "one_more_song": PRIKA_ENCORE}),
        "mint": build_mint_rules({"lets_sing_together": MINT_SING_TOGETHER, "fantastic_performance": MINT_FANTASTIC}),
        "attacker": [],
    }
    base_stats = {s: {"atk": 0, "def": 0, "max_hp": 0} for s in ("b1", "prika", "mint")}
    base_stats["attacker"] = {"atk": 10000, "def": 0, "max_hp": 0}

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
        # The attacker has to hold a CHARGE weapon for Prika's Charge Damage to
        # mean anything - it multiplies a fully-charged shot and does nothing
        # for an SMG/MG/AR/SG bearer (Fienn, 2026-07-26). A charge-weapon ally
        # is who that buff is for, so that is who this pipeline test uses.
        weapon_stats={"attacker": {
            "weapon": "SR", "damage_percent": 0.0, "max_ammo": 6,
            "reload_time": 2.0, "charge_time": 1.0, "charge_damage_percent": 100.0,
        }},
    )

    attacker_bursts = {round(e["time"], 1): e["damage"] for e in result["damage_log"] if e["source"] == "burst"}
    # Cycle 1 (t=5): Prika bursts (leftmost B2). Only her Charge Damage (+25%,
    # permanent since Mint is in the deck) reaches the attacker; Mint has not
    # bursted so she is not Singing and grants nothing yet.
    assert attacker_bursts[5.0] == 10000 * 1.25  # 12500.0
    # Cycle 2 (t=25): Prika on cooldown, so Mint bursts. Via ally_burst_activate,
    # Prika's Encore fires (she is in Performance): Encore Attack Damage +25.01%,
    # Mint's Sing Along Attack Damage +30.02% and Crit Damage +45.05%, and -
    # because Encore pins Mint Singing - Mint's Fantastic Performance Crit Rate
    # +19.94% and Pierce +32.72% all reach the attacker's burst.
    #   Charge 1.25 * (1 + AD 0.5503 + Pierce 0.3272) * (1 + 0.1994*(0.5 + 0.4505))
    assert round(attacker_bursts[25.0], 4) == round(
        10000 * 1.25 * (1 + 0.3002 + 0.2501 + 0.3272) * (1 + 0.1994 * (0.5 + 0.4505)), 4
    )  # 27916.7751
