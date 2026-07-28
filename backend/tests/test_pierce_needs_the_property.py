"""Pierce Damage Up needs TWO things, and these pin both.

1. The unit must actually HAVE Pierce - the skill-text marker is [관통 특화] /
   "Gain Pierce" (Fienn, 2026-07-26). The property is its own registry stat,
   `has_pierce`, so a unit that gains it for a window is credited for exactly
   that window.
2. The damage instance must be her NORMAL ATTACK. Pierce is "normal attacks
   hitting everything in their path" (references/damage-formula-reference.md),
   so a skill instance fired by a piercing unit collects none of the bucket.

These used to measure requirement 1 on BURST damage, which quietly asserted the
opposite of requirement 2. Fienn's Snow White: Heavy Arms range footage
(2026-07-28) settled it: her Auto Fire pulses were carrying her +13.09% where
the game gives them nothing.

Per-unit grants are pinned in each unit's own test.
"""
from app.raid_simulator import simulate_raid
from app.skill_rules._helpers import buff_rule

DECK = [
    {"slug": "b1", "burst_tier": 1, "element": "Iron", "cooldown": 20.0},
    {"slug": "b2", "burst_tier": 2, "element": "Iron", "cooldown": 20.0},
    {"slug": "striker", "burst_tier": 3, "element": "Iron", "cooldown": 20.0, "weapon": "AR"},
]
BASE_STATS = {s["slug"]: {"atk": 10000, "def": 0, "max_hp": 0} for s in DECK}
# 100% of ATK per shot with no reload, so a normal attack's damage IS the bucket.
WEAPON = {"weapon": "AR", "damage_percent": 100.0, "max_ammo": 999,
          "reload_time": 0.0, "charge_time": 0.0, "charge_damage_percent": 100.0}

HOLDS_PIERCE = [buff_rule("battle_start", [("has_pierce", 1.0, "self", None)])]


def _log(striker_rules, fight_duration=1.5):
    return simulate_raid(
        DECK,
        {"b1": [buff_rule("battle_start", [("pierce_damage_up", 0.5, "squad", None)])],
         "b2": [], "striker": striker_rules},
        burst_damage_percents={"striker": 100.0},
        base_stats=BASE_STATS,
        enemy_def=0,
        # The fight ends before any Full Burst window opens, so nothing but the
        # Damage-Up bucket separates these numbers.
        gauge_charge_time=30.0,
        fight_duration=fight_duration,
        base_crit_rate=0.0,
        weapon_stats={"striker": WEAPON},
    )["damage_log"]


def _first(striker_rules, source):
    return next(e["damage"] for e in _log(striker_rules) if e["source"] == source)


def test_a_squad_pierce_buff_does_nothing_for_an_ally_without_pierce():
    assert _first([], "normal_attack") == 10000.0


def test_the_same_buff_counts_in_full_on_a_pierce_holders_normal_attack():
    assert _first(HOLDS_PIERCE, "normal_attack") == 15000.0


def test_a_pierce_holder_collects_nothing_on_her_skill_damage():
    # Requirement 2. Same unit, same instant, same buff - only the instance
    # differs, and a per-shot nuke is not a normal attack.
    nuke = [(1, "every", [_pulse()])]
    log = simulate_raid(
        DECK,
        {"b1": [buff_rule("battle_start", [("pierce_damage_up", 0.5, "squad", None)])],
         "b2": [], "striker": HOLDS_PIERCE},
        burst_damage_percents={"striker": 100.0}, base_stats=BASE_STATS, enemy_def=0,
        gauge_charge_time=30.0, fight_duration=1.5, base_crit_rate=0.0,
        weapon_stats={"striker": WEAPON}, per_shot_rules={"striker": nuke},
    )["damage_log"]
    shot = next(e["damage"] for e in log if e["source"] == "normal_attack")
    pulse = next(e["damage"] for e in log if e["source"] == "per_shot_nuke")

    assert shot == 15000.0
    assert pulse == 10000.0


def test_pierce_is_credited_only_while_the_property_is_actually_held():
    # A Pierce window opened at battle start and lasting 0.5 sec has lapsed by
    # the later shots, so the buff finds no property to credit.
    lapsed = [buff_rule("battle_start", [("has_pierce", 1.0, "self", 0.5)])]
    shots = [e["damage"] for e in _log(lapsed) if e["source"] == "normal_attack"]

    assert shots[-1] == 10000.0


def _pulse():
    from app.skill_rules._helpers import instant_nuke_pulse_rule
    return instant_nuke_pulse_rule("per_shot", 100.0)
