"""Splits a roster into up to five disjoint decks against ONE boss profile,
maximizing summed damage (Phase 5). Disjoint by OWNED CHARACTER, not by slug:
the decks are fielded simultaneously, so a character encoded as several
MODE_VARIANTS candidates still holds at most one seat in the whole allocation
(see deck_search's `variant_base`). Same boss => total = sum of independent
deck scores, so: greedy peeling (best deck on the remaining roster, repeat)
lands near the optimum, and a budget-bounded same-tier swap hill-climb
recovers its classic mistake (stacking synergy cores in deck 1 when splitting
them supports two decks better). No optimality claim - set partitioning is
NP-hard; this is the standard practical combo."""
import time

from app.cascade import Cascade, cached_fit_surrogate
from app.deck_search import (SEARCH_SIM_BUDGET, BossProfile,
                             _intra_tier_orderings, _orderings_within_budget,
                             _score_batch, _summarize, best_completions,
                             evaluate_deck, search_best_decks, variant_base)
from app.sim_pool import SimPool, resolve_workers


# Swap candidates scored per batch, per worker. The batch is what SimPool fans
# out, so it has to be wide enough to fill the pool - but every candidate in a
# batch is scored before the deadline is checked again, so a wider batch also
# overshoots the deadline further. Scaling with the worker count holds that
# overshoot near-constant (~a second at today's ~100 ms simulation) whatever the
# machine, and the floor keeps the serial path's granularity close to the
# one-candidate-at-a-time walk this replaced.
SWAP_BATCH_PER_WORKER = 4
_MIN_SWAP_BATCH = 4


class InfeasibleDraft(ValueError):
    """A draft deck's locked/placed units fit no legal deck shape, the pool is
    exhausted before every drafted deck can be completed, or the draft spends one
    owned character on two decks (two MODE_VARIANTS candidates of one base)."""


def _seed_choices(seed, alternatives):
    """Every concrete reading of one drafted deck.

    A drafted seat can name an owned character the engine models in several
    modes (MODE_VARIANTS). Which mode she runs in is the ENGINE's call, not the
    player's - Bready's is decided by the buffers sharing her deck - so the seat
    arrives as a representative spec plus `alternatives`, and the caller picks by
    completing the deck each way and keeping the best. Seats with no alternative
    contribute one reading, so a draft without ambiguity yields exactly the seed
    it was given and pays nothing.
    """
    if not alternatives:
        return [seed]
    readings = [[]]
    for unit in seed:
        options = alternatives.get(unit.slug, (unit,))
        readings = [reading + [option] for reading in readings for option in options]
    return readings


def allocate_decks(roster, boss: BossProfile, num_decks=5, draft=None,
                   locked=frozenset(), time_budget_sec=45.0, workers=None,
                   alternatives=None):
    # Serial (the default) never constructs a SimPool, so the sim path stays
    # exactly the pre-parallelism one (and test stubs of evaluate_deck keep
    # working - SimPool holds its own module binding they can't patch).
    worker_count = resolve_workers(workers)
    pool = SimPool(roster, boss, workers=workers) if worker_count > 1 else None
    try:
        by_slug = {u.slug: u for u in roster}
        draft = draft or []
        # Pooling is per OWNED CHARACTER, not per slug: the player fields all of
        # these decks simultaneously, so seating one MODE_VARIANTS candidate
        # spends the character and retires her other candidates too. Keying on
        # the slug instead let one Rapi: Red Hood hold a seat in deck 2 as B3 and
        # another in deck 4 as B1 - a formation the game cannot produce.
        drafted = [variant_base(u.slug) for deck in draft for u in deck]
        placed = set(drafted)
        if len(drafted) != len(placed):
            twice = sorted({b for b in placed if drafted.count(b) > 1})
            raise InfeasibleDraft(
                f"one owned character drafted into more than one deck: {twice}")
        remaining = [u for u in roster if variant_base(u.slug) not in placed]

        decks = []  # each: ordered list of units (canonical order from the search)
        for seed in draft:                       # seed decks: complete around placed units
            # One completion per concrete reading of the seed; the best wins, so
            # a drafted character's mode is chosen by what her finished deck
            # actually scores rather than by declaration order.
            found = max(
                (c for reading in _seed_choices(seed, alternatives)
                 for c in best_completions(reading, remaining, boss, top_n=1,
                                           pool=pool)),
                key=lambda c: c["total_damage"], default=None)
            if found is None:
                raise InfeasibleDraft(
                    f"cannot complete a legal deck from {[u.slug for u in seed]}")
            units = [by_slug[s] for s in found["deck"]]
            decks.append(units)
            # newly-pulled fillers leave the pool
            used = {variant_base(u.slug) for u in units} - placed
            remaining = [u for u in remaining if variant_base(u.slug) not in used]

        # One fit serves the whole peel: the surrogate is additive over unit
        # membership, so coefficients learned on the full roster score any
        # subset of it. Deferred to the first peel iteration (and probed
        # against `remaining`, not `roster`) so a draft the seed loop already
        # completes - or a small leftover pool - never pays for a fit nothing
        # will use; `probed` still bounds the cost to one fit for the whole
        # peel, same as before.
        cascade = None
        probed = False
        while len(decks) < num_decks:            # free decks: greedy peeling (unchanged)
            if not probed:
                probed = True
                if _orderings_within_budget(remaining, SEARCH_SIM_BUDGET) is None:
                    model = cached_fit_surrogate(
                        roster, boss, lambda decks: _score_batch(decks, boss, pool))
                    if model is not None:
                        cascade = Cascade(model)
            found = search_best_decks(remaining, boss, top_n=1, pool=pool,
                                      cascade=cascade)
            if not found:
                break
            units = [by_slug[slug] for slug in found[0]["deck"]]
            decks.append(units)
            used = {variant_base(u.slug) for u in units}
            remaining = [u for u in remaining if variant_base(u.slug) not in used]

        # time_budget_sec caps the swap-improvement phase ONLY, starting when the
        # swap phase itself starts: greedy peeling above and the final ordering
        # polish below are unbudgeted, so a valid (if unimproved) allocation is
        # returned even with a zero budget. The hill-climb's DECISIONS stay
        # sequential - each accepted swap changes the state the next candidate is
        # judged against - but the candidates it judges are scored in batches
        # through the same pool the peel used, which is what lets the phase reach
        # a local optimum inside the budget instead of being cut off mid-climb.
        deadline = time.monotonic() + time_budget_sec
        _swap_pass(decks, remaining, boss, deadline, locked=locked, pool=pool,
                   batch=max(_MIN_SWAP_BATCH, worker_count * SWAP_BATCH_PER_WORKER))

        summaries = [_best_ordering_summary(units, boss, pool) for units in decks]
        return {"decks": summaries,
                "leftover_slugs": sorted(u.slug for u in remaining)}
    finally:
        if pool is not None:
            pool.close()


def _swap_pass(decks, leftovers, boss, deadline, locked=frozenset(), pool=None,
               batch=_MIN_SWAP_BATCH):
    """Hill-climb: try same-tier unit swaps between two decks (and between a
    deck and the leftovers), re-scoring only the affected deck(s); keep a swap
    iff the summed total improves. Same-tier swaps preserve the deck shapes.
    Loops until a full pass finds no improvement or the deadline passes.
    `locked` slugs are never chosen as a swap source, pinning a drafted seat."""
    if not decks:
        return
    # Read locks per OWNED CHARACTER: a drafted seat may name a character whose
    # MODE_VARIANTS candidate the engine chose, so locking `bready` has to hold
    # whichever of her candidates ended up seated.
    locked = {variant_base(slug) for slug in locked}
    scores = _score_batch(decks, boss, pool)
    improved = True
    while improved and time.monotonic() < deadline:
        improved = False
        for i in range(len(decks)):
            for j in range(i + 1, len(decks)):
                improved |= _try_swaps(decks, scores, i, decks[j], j, boss,
                                       deadline, locked, pool, batch)
            improved |= _try_swaps(decks, scores, i, leftovers, None, boss,
                                   deadline, locked, pool, batch)


def _try_swaps(decks, scores, i, partner, j, boss, deadline, locked, pool, batch):
    """Same-tier swaps between deck `i` and `partner` - either another deck
    (`j` is its index, so its score counts toward the improvement too) or the
    leftover bench (`j` is None, and a benched unit contributes nothing).

    Candidates are scored a batch at a time so a SimPool can fan them out. The
    walk over a scored batch keeps the serial rule exactly: accept the FIRST
    candidate that improves, in this order. An acceptance makes the rest of that
    batch stale - those scores describe a deck that no longer exists - so the
    loop re-batches from the next candidate instead of trusting them. Wasted
    scoring is bounded by the batch and rare in practice: measured on a 78-unit
    roster, under 1% of candidates are ever accepted.

    Tier and lock, the filters that decide which pairs are candidates at all,
    never go stale: a same-tier swap leaves both seats' tiers unchanged and never
    moves a locked unit. That is what makes scoring a candidate before reaching
    it safe in the first place.

    The one filter that CAN flip is `seated`, which upholds the one-owned-
    character rule across the whole allocation. Bringing a bench unit in spends
    that character, so any other candidate offering one of her remaining
    MODE_VARIANTS slugs stops being legal the moment a swap is accepted - the
    unscanned tail is pruned there rather than trusted. Deck-to-deck swaps need
    no such filter: both units are already seated, so exchanging them cannot
    make a character appear twice.
    """
    # Bench swaps only: the incoming character must not already hold a seat -
    # in THIS deck or any other, since the player fields all of them at once.
    seated = None if j is not None else {variant_base(u.slug)
                                         for deck in decks for u in deck}
    # `locked` arrives already keyed by owned character (see _swap_pass).
    candidates = [(a, k)
                  for a in range(5) if variant_base(decks[i][a].slug) not in locked
                  for k in range(len(partner))
                  if variant_base(partner[k].slug) not in locked
                  and decks[i][a].burst_tier == partner[k].burst_tier
                  and (seated is None or variant_base(partner[k].slug) not in seated)]
    width = 1 if j is None else 2      # decks re-scored per candidate
    improved = False
    start = 0
    while start < len(candidates):
        if time.monotonic() >= deadline:
            return improved
        chunk = candidates[start:start + batch]
        trials = []
        for a, k in chunk:
            deck_i = list(decks[i])
            deck_i[a] = partner[k]
            trials.append(deck_i)
            if j is not None:
                deck_j = list(partner)
                deck_j[k] = decks[i][a]
                trials.append(deck_j)
        totals = _score_batch(trials, boss, pool)

        baseline = scores[i] + (0.0 if j is None else scores[j])
        accepted = next((n for n in range(len(chunk))
                         if sum(totals[n * width:(n + 1) * width]) > baseline),
                        None)
        if accepted is None:
            start += len(chunk)
            continue
        a, k = chunk[accepted]
        decks[i][a], partner[k] = partner[k], decks[i][a]
        scores[i] = totals[accepted * width]
        if j is not None:
            scores[j] = totals[accepted * width + 1]
        improved = True
        start += accepted + 1
        if seated is not None:
            # `partner[k]` now holds the unit that LEFT deck i, and the character
            # who came in occupies decks[i][a]. Drop the unscanned candidates
            # that would seat her a second time.
            seated.discard(variant_base(partner[k].slug))
            seated.add(variant_base(decks[i][a].slug))
            candidates = candidates[:start] + [
                (a2, k2) for a2, k2 in candidates[start:]
                if variant_base(partner[k2].slug) not in seated]
    return improved


def _combined(alloc):
    return sum(d["total_damage"] for d in alloc["decks"])


def _is_complete(draft, num_decks):
    return len(draft) == num_decks and all(len(deck) == 5 for deck in draft)


def _better(a, b):
    return a if _combined(a) >= _combined(b) else b


def _leftover_against(alloc, roster):
    # Base-keyed like the peel: a seated character's OTHER candidate slugs are
    # not benched units the player could still field, so they never reach the
    # bench (which the UI reads as "not allocated to a deck").
    used = {variant_base(s) for d in alloc["decks"] for s in d["deck"]}
    return sorted(u.slug for u in roster if variant_base(u.slug) not in used)


def recommend_from_draft(roster, boss, num_decks=5, draft=None,
                         locked=frozenset(), workers=None, alternatives=None):
    """Three-tier recommendation around a player's in-progress draft:
    `recommended` (best over the full roster), `within_draft` (best reshuffle
    of only the drafted units, once the draft is complete) and
    `baseline_total_damage` (the draft's exact groupings, scored as-is) - so a
    caller can show the player how much a reshuffle or a bench swap-in would
    gain over what they already placed. `pinned_by_deck` echoes back which
    locked slugs ended up in which recommended deck, for the API to attach
    `pinned_slugs` - the slug the deck actually holds, which for a drafted
    MODE_VARIANTS character is the candidate the engine chose, not the owned slug
    the caller sent. `alternatives` carries the other candidates of such a seat
    (see `_seed_choices`)."""
    draft = draft or []
    # Locks are per owned character, so a lock on `bready` still holds after the
    # engine settles on one of her candidates.
    locked = {variant_base(slug) for slug in locked}
    # from-scratch pass honors hard locks (seed ONLY the locked units, leaving
    # flexible seats free to explore all shapes) - without this, a scratch win
    # could drop a locked unit. Empty when there are no locks => pure from-scratch.
    locked_seed = [[u for u in deck if variant_base(u.slug) in locked]
                   for deck in draft]
    locked_seed = [d for d in locked_seed if d]
    if draft:
        # The full-roster from-scratch pass is cut here (measured redundant:
        # scripts/measure_scratch_delta.py, docs/roadmap.md) - draft-seeded
        # `warm` (which swaps bench units into weak seats) plus `within_draft`
        # below already match or beat it on realistic drafts (0% loss across
        # 6/8 measured scenarios), losing at most ~2.2% only on pathological
        # "benched the strongest units" drafts. `warm` honors `locked` via its
        # swap mask, so the lock guarantee (a locked unit is never displaced)
        # still holds. ~4x faster on a complete draft.
        recommended = allocate_decks(roster, boss, num_decks=num_decks, draft=draft,
                                     locked=locked, workers=workers,
                                     alternatives=alternatives)
    else:
        recommended = allocate_decks(roster, boss, num_decks=num_decks,
                                     draft=(locked_seed or None), locked=locked,
                                     workers=workers, alternatives=alternatives)

    within_draft = None
    baseline_total = None
    if _is_complete(draft, num_decks):
        # Every candidate of a drafted character joins the within-draft pool, or
        # a reshuffle of the drafted units alone could not reach the mode the
        # full-roster pass just chose.
        drafted = [option
                   for deck in draft for u in deck
                   for option in (alternatives or {}).get(u.slug, (u,))]
        w = allocate_decks(drafted, boss, num_decks=num_decks, draft=draft,
                           locked=locked, workers=workers, alternatives=alternatives)
        s = allocate_decks(drafted, boss, num_decks=num_decks,
                           draft=(locked_seed or None), locked=locked,
                           workers=workers, alternatives=alternatives)
        within_draft = _better(w, s)
        # within_draft's decks are a valid full-roster allocation (drafted units
        # subset of roster), so fold it into recommended to guarantee
        # recommended >= within_draft by construction; recompute its leftovers
        # against the FULL roster (bench units belong in leftover).
        if _combined(within_draft) > _combined(recommended):
            recommended = {"decks": within_draft["decks"],
                           "leftover_slugs": _leftover_against(within_draft, roster)}
        # "The draft's exact groupings, scored as-is" has no single reading for a
        # seat whose mode the engine picks, so score the best one - the same
        # standard the recommendation itself is held to, which keeps the gain the
        # UI reports from being inflated by a mode the player never chose.
        baseline_total = sum(
            max(_best_ordering_summary(reading, boss)["total_damage"]
                for reading in _seed_choices(deck, alternatives))
            for deck in draft)

    pinned_by_deck = [[s for s in d["deck"] if variant_base(s) in locked]
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
