"""Splits a roster into up to five disjoint decks against ONE boss profile,
maximizing summed damage (Phase 5). Same boss => total = sum of independent
deck scores, so: greedy peeling (best deck on the remaining roster, repeat)
lands near the optimum, and a budget-bounded same-tier swap hill-climb
recovers its classic mistake (stacking synergy cores in deck 1 when splitting
them supports two decks better). No optimality claim - set partitioning is
NP-hard; this is the standard practical combo."""
import time

from app.deck_search import (BossProfile, _intra_tier_orderings, _summarize,
                             evaluate_deck, search_best_decks)


def allocate_decks(roster, boss: BossProfile, num_decks=5, time_budget_sec=45.0):
    # time_budget_sec caps the swap-improvement phase ONLY: greedy peeling and
    # the final ordering polish always run to completion, so a valid (if
    # unimproved) allocation is returned even with a zero budget.
    deadline = time.monotonic() + time_budget_sec
    remaining = list(roster)
    decks = []  # each: ordered list of units (canonical order from the search)
    by_slug = {u.slug: u for u in roster}
    while len(decks) < num_decks:
        found = search_best_decks(remaining, boss, top_n=1)
        if not found:
            break
        units = [by_slug[slug] for slug in found[0]["deck"]]
        decks.append(units)
        used = {u.slug for u in units}
        remaining = [u for u in remaining if u.slug not in used]

    _swap_pass(decks, remaining, boss, deadline)

    summaries = [_best_ordering_summary(units, boss) for units in decks]
    return {"decks": summaries,
            "leftover_slugs": sorted(u.slug for u in remaining)}


def _score(units, boss):
    return evaluate_deck(units, boss)["total_damage"]


def _swap_pass(decks, leftovers, boss, deadline):
    """Hill-climb: try same-tier unit swaps between two decks (and between a
    deck and the leftovers), re-scoring only the affected deck(s); keep a swap
    iff the summed total improves. Same-tier swaps preserve the deck shapes.
    Loops until a full pass finds no improvement or the deadline passes."""
    if not decks:
        return
    scores = [_score(units, boss) for units in decks]
    improved = True
    while improved and time.monotonic() < deadline:
        improved = False
        for i in range(len(decks)):
            for j in range(i + 1, len(decks)):
                improved |= _try_pair_swaps(decks, scores, i, j, boss, deadline)
            improved |= _try_leftover_swaps(decks, scores, i, leftovers, boss, deadline)


def _try_pair_swaps(decks, scores, i, j, boss, deadline):
    improved = False
    for a in range(5):
        for b in range(5):
            if time.monotonic() >= deadline:
                return improved
            if decks[i][a].burst_tier != decks[j][b].burst_tier:
                continue
            decks[i][a], decks[j][b] = decks[j][b], decks[i][a]
            new_i, new_j = _score(decks[i], boss), _score(decks[j], boss)
            if new_i + new_j > scores[i] + scores[j]:
                scores[i], scores[j] = new_i, new_j
                improved = True
            else:
                decks[i][a], decks[j][b] = decks[j][b], decks[i][a]
    return improved


def _try_leftover_swaps(decks, scores, i, leftovers, boss, deadline):
    improved = False
    for a in range(5):
        for k in range(len(leftovers)):
            if time.monotonic() >= deadline:
                return improved
            if decks[i][a].burst_tier != leftovers[k].burst_tier:
                continue
            decks[i][a], leftovers[k] = leftovers[k], decks[i][a]
            new_i = _score(decks[i], boss)
            if new_i > scores[i]:
                scores[i] = new_i
                improved = True
            else:
                decks[i][a], leftovers[k] = leftovers[k], decks[i][a]
    return improved


def _best_ordering_summary(units, boss):
    # Final polish: the swap pass scored canonical orders only; pick the best
    # intra-tier ordering for the finished deck (a handful of sims per deck).
    best = None
    for ordered in _intra_tier_orderings(units):
        summary = _summarize(ordered, evaluate_deck(ordered, boss))
        if best is None or summary["total_damage"] > best["total_damage"]:
            best = summary
    return best
