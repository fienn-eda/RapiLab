"""Splits a roster into up to five disjoint decks against ONE boss profile,
maximizing summed damage (Phase 5). Same boss => total = sum of independent
deck scores, so: greedy peeling (best deck on the remaining roster, repeat)
lands near the optimum, and a budget-bounded same-tier swap hill-climb
recovers its classic mistake (stacking synergy cores in deck 1 when splitting
them supports two decks better). No optimality claim - set partitioning is
NP-hard; this is the standard practical combo."""
import time

from app.deck_search import (BossProfile, _intra_tier_orderings, _score_batch,
                             _summarize, best_completions, evaluate_deck,
                             search_best_decks)
from app.sim_pool import SimPool, resolve_workers


class InfeasibleDraft(ValueError):
    """A draft deck's locked/placed units fit no legal deck shape, or the pool
    is exhausted before every drafted deck can be completed."""


def allocate_decks(roster, boss: BossProfile, num_decks=5, draft=None,
                   locked=frozenset(), time_budget_sec=45.0, workers=None):
    # Serial (the default) never constructs a SimPool, so the sim path stays
    # exactly the pre-parallelism one (and test stubs of evaluate_deck keep
    # working - SimPool holds its own module binding they can't patch).
    pool = SimPool(roster, boss, workers=workers) if resolve_workers(workers) > 1 else None
    try:
        by_slug = {u.slug: u for u in roster}
        draft = draft or []
        placed = {u.slug for deck in draft for u in deck}
        remaining = [u for u in roster if u.slug not in placed]

        decks = []  # each: ordered list of units (canonical order from the search)
        for seed in draft:                       # seed decks: complete around placed units
            found = best_completions(seed, remaining, boss, top_n=1, pool=pool)
            if not found:
                raise InfeasibleDraft(
                    f"cannot complete a legal deck from {[u.slug for u in seed]}")
            units = [by_slug[s] for s in found[0]["deck"]]
            decks.append(units)
            used = {u.slug for u in units} - placed   # newly-pulled fillers leave the pool
            remaining = [u for u in remaining if u.slug not in used]

        while len(decks) < num_decks:            # free decks: greedy peeling (unchanged)
            found = search_best_decks(remaining, boss, top_n=1, pool=pool)
            if not found:
                break
            units = [by_slug[slug] for slug in found[0]["deck"]]
            decks.append(units)
            used = {u.slug for u in units}
            remaining = [u for u in remaining if u.slug not in used]

        # time_budget_sec caps the swap-improvement phase ONLY, starting when the
        # swap phase itself starts: greedy peeling above and the final ordering
        # polish below are unbudgeted, so a valid (if unimproved) allocation is
        # returned even with a zero budget. The hill-climb stays serial: each
        # accepted swap changes the state the next candidate is judged against.
        deadline = time.monotonic() + time_budget_sec
        _swap_pass(decks, remaining, boss, deadline, locked=locked)

        summaries = [_best_ordering_summary(units, boss, pool) for units in decks]
        return {"decks": summaries,
                "leftover_slugs": sorted(u.slug for u in remaining)}
    finally:
        if pool is not None:
            pool.close()


def _score(units, boss):
    return evaluate_deck(units, boss)["total_damage"]


def _swap_pass(decks, leftovers, boss, deadline, locked=frozenset()):
    """Hill-climb: try same-tier unit swaps between two decks (and between a
    deck and the leftovers), re-scoring only the affected deck(s); keep a swap
    iff the summed total improves. Same-tier swaps preserve the deck shapes.
    Loops until a full pass finds no improvement or the deadline passes.
    `locked` slugs are never chosen as a swap source, pinning a drafted seat."""
    if not decks:
        return
    scores = [_score(units, boss) for units in decks]
    improved = True
    while improved and time.monotonic() < deadline:
        improved = False
        for i in range(len(decks)):
            for j in range(i + 1, len(decks)):
                improved |= _try_pair_swaps(decks, scores, i, j, boss, deadline, locked)
            improved |= _try_leftover_swaps(decks, scores, i, leftovers, boss, deadline, locked)


def _try_pair_swaps(decks, scores, i, j, boss, deadline, locked=frozenset()):
    improved = False
    for a in range(5):
        if decks[i][a].slug in locked:
            continue
        for b in range(5):
            if time.monotonic() >= deadline:
                return improved
            if decks[j][b].slug in locked:
                continue
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


def _try_leftover_swaps(decks, scores, i, leftovers, boss, deadline, locked=frozenset()):
    improved = False
    for a in range(5):
        if decks[i][a].slug in locked:
            continue
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


def _combined(alloc):
    return sum(d["total_damage"] for d in alloc["decks"])


def _is_complete(draft, num_decks):
    return len(draft) == num_decks and all(len(deck) == 5 for deck in draft)


def _better(a, b):
    return a if _combined(a) >= _combined(b) else b


def _leftover_against(alloc, roster):
    used = {s for d in alloc["decks"] for s in d["deck"]}
    return sorted(u.slug for u in roster if u.slug not in used)


def recommend_from_draft(roster, boss, num_decks=5, draft=None,
                         locked=frozenset(), workers=None):
    """Three-tier recommendation around a player's in-progress draft:
    `recommended` (best over the full roster), `within_draft` (best reshuffle
    of only the drafted units, once the draft is complete) and
    `baseline_total_damage` (the draft's exact groupings, scored as-is) - so a
    caller can show the player how much a reshuffle or a bench swap-in would
    gain over what they already placed. `pinned_by_deck` echoes back which
    locked slugs ended up in which recommended deck, for the API to attach
    `pinned_slugs`."""
    draft = draft or []
    # from-scratch pass honors hard locks (seed ONLY the locked units, leaving
    # flexible seats free to explore all shapes) - without this, a scratch win
    # could drop a locked unit. Empty when there are no locks => pure from-scratch.
    locked_seed = [[u for u in deck if u.slug in locked] for deck in draft]
    locked_seed = [d for d in locked_seed if d]
    scratch = allocate_decks(roster, boss, num_decks=num_decks,
                             draft=(locked_seed or None), locked=locked, workers=workers)
    if draft:
        warm = allocate_decks(roster, boss, num_decks=num_decks, draft=draft,
                              locked=locked, workers=workers)
        recommended = _better(scratch, warm)
    else:
        recommended = scratch

    within_draft = None
    baseline_total = None
    if _is_complete(draft, num_decks):
        drafted = [u for deck in draft for u in deck]
        w = allocate_decks(drafted, boss, num_decks=num_decks, draft=draft,
                           locked=locked, workers=workers)
        s = allocate_decks(drafted, boss, num_decks=num_decks,
                           draft=(locked_seed or None), locked=locked, workers=workers)
        within_draft = _better(w, s)
        # within_draft's decks are a valid full-roster allocation (drafted units
        # subset of roster), so fold it into recommended to guarantee
        # recommended >= within_draft by construction; recompute its leftovers
        # against the FULL roster (bench units belong in leftover).
        if _combined(within_draft) > _combined(recommended):
            recommended = {"decks": within_draft["decks"],
                           "leftover_slugs": _leftover_against(within_draft, roster)}
        baseline_total = sum(
            _best_ordering_summary(deck, boss)["total_damage"] for deck in draft)

    pinned_by_deck = [[s for s in d["deck"] if s in locked]
                      for d in recommended["decks"]]
    return {"recommended": recommended, "within_draft": within_draft,
            "baseline_total_damage": baseline_total, "pinned_by_deck": pinned_by_deck}


def _best_ordering_summary(units, boss, pool=None):
    # Final polish: the swap pass scored canonical orders only; pick the best
    # intra-tier ordering for the finished deck (a handful of sims per deck).
    # Batch-scored; ties keep the first ordering, like the serial `>` did.
    orderings = list(_intra_tier_orderings(units))
    totals = _score_batch(orderings, boss, pool)
    best_i = max(range(len(orderings)), key=lambda i: (totals[i], -i))
    return _summarize(orderings[best_i], evaluate_deck(orderings[best_i], boss))
