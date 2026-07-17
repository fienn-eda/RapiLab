"""Searches a roster for the highest-damage single deck.

Feasibility + exhaustive-over-a-pruned-space hybrid (per the plan): a deck is
5 Nikkes with at least one of each burst tier (1/2/3), else it can never
reach Full Burst. Within a feasible combination, only the relative order of
same-tier Nikkes affects the result - burst_cycle fires the leftmost eligible
per tier, so intra-tier order decides who nukes vs who is a backup buffer.
Cross-tier order never matters (tiers always fire 1->2->3), so decks are
emitted in canonical tier order.

feasible_orderings is pure combinatorics on burst_tier (no simulation), so it
works on any object exposing `.burst_tier`. Scoring goes through the roster
assembly layer + simulate_raid.

Known simplification (from the plan): flexible-burst units (Anis: Star's
re-entry, Rapi: Red Hood's Combat Assist standing in for Burst 1) are placed
by their nominal burst_tier for feasibility; their branch effects are still
simulated correctly, but the scheduler slots them nominally.
"""
from dataclasses import dataclass
from itertools import combinations, permutations

from app.raid_simulator import simulate_raid
from app.roster import assemble_simulation_inputs


@dataclass
class BossProfile:
    element: str | None = None
    core_hittable: bool = False
    enemy_def: float = 0.0
    fight_duration: float = 180.0
    gauge_charge_time: float = 2.0
    mode: str = "manual"
    part_destructible: bool = False


# Real decks come in exactly these B1/B2/B3 shapes (Fienn, 2026-07-17);
# "at least one of each tier" also admits shapes that never occur in play.
ALLOWED_SHAPES = ((1, 1, 3), (1, 2, 2), (2, 1, 2))


def shape_combinations(roster):
    """Canonical tier-ordered 5-unit combinations, restricted to the shapes
    real play uses. Pure combinatorics on `.burst_tier` (like
    feasible_orderings); intra-tier order is the input order."""
    by_tier = {1: [], 2: [], 3: []}
    for unit in roster:
        if unit.burst_tier in by_tier:
            by_tier[unit.burst_tier].append(unit)
    for n1, n2, n3 in ALLOWED_SHAPES:
        for c1 in combinations(by_tier[1], n1):
            for c2 in combinations(by_tier[2], n2):
                for c3 in combinations(by_tier[3], n3):
                    yield list(c1) + list(c2) + list(c3)


def feasible_orderings(roster):
    for combo in combinations(roster, 5):
        by_tier = {1: [], 2: [], 3: []}
        infeasible = False
        for unit in combo:
            if unit.burst_tier not in by_tier:
                infeasible = True
                break
            by_tier[unit.burst_tier].append(unit)
        if infeasible or not all(by_tier[t] for t in (1, 2, 3)):
            continue
        for order1 in permutations(by_tier[1]):
            for order2 in permutations(by_tier[2]):
                for order3 in permutations(by_tier[3]):
                    yield list(order1) + list(order2) + list(order3)


def evaluate_deck(ordered_deck, boss: BossProfile):
    inputs = assemble_simulation_inputs(ordered_deck)
    return simulate_raid(
        **inputs,
        enemy_def=boss.enemy_def,
        gauge_charge_time=boss.gauge_charge_time,
        fight_duration=boss.fight_duration,
        mode=boss.mode,
        core_hittable=boss.core_hittable,
        boss_element=boss.element,
        part_destructible=boss.part_destructible,
    )


def _summarize(ordered_deck, result):
    burst = sum(e["damage"] for e in result["damage_log"] if e["source"] == "burst")
    normal = sum(e["damage"] for e in result["damage_log"] if e["source"] == "normal_attack")
    return {
        "deck": [spec.slug for spec in ordered_deck],
        "total_damage": result["total_damage"],
        "burst_damage": burst,
        "normal_attack_damage": normal,
        "result": result,
    }


def find_best_decks(roster, boss: BossProfile, top_n=5):
    scored = [
        _summarize(ordered, evaluate_deck(ordered, boss))
        for ordered in feasible_orderings(roster)
    ]
    scored.sort(key=lambda entry: entry["total_damage"], reverse=True)
    return scored[:top_n]
