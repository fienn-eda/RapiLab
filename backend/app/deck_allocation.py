"""Splits a roster into up to five disjoint decks against ONE boss profile,
maximizing summed damage (Phase 5). Disjoint by OWNED CHARACTER, not by slug:
the decks are fielded simultaneously, so a character encoded as several builds
still holds at most one seat in the whole allocation (see deck_search's
`character_of`). Same boss => total = sum of independent deck scores, so:
greedy peeling (best deck on the remaining roster, repeat)
lands near the optimum, and a budget-bounded same-tier swap hill-climb
recovers its classic mistake (stacking synergy cores in deck 1 when splitting
them supports two decks better). No optimality claim - set partitioning is
NP-hard; this is the standard practical combo."""
import time

from app.cancellation import NEVER
from app.cascade import Cascade, cached_fit_surrogate
from app.deck_search import (SEARCH_SIM_BUDGET, BossProfile,
                             _intra_tier_orderings, _orderings_within_budget,
                             _score_batch, _summarize, best_completions,
                             character_of, completions_fit_budget,
                             deck_breaks_gimmick, deck_is_valid, evaluate_deck,
                             search_best_decks, weakness_holders)
from app.elements import weakness_of
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

# Wall-clock ceiling on the swap-improvement phase. A CEILING, not a cost: the
# climb exits the moment a full pass finds no improvement, so a configuration
# that converges early pays nothing for a higher number here - it only ever
# binds where it is actually still buying damage.
#
# Chosen by measurement, `scripts/measure_swap_budget.py` on Fienn's roster
# (78 usable, 5 decks, Fire boss / 수냉 약점, 속성 저지 필수, DEF 31,784, 180 s):
#
#     budget   combined total   vs peel   end-to-end   converged
#         0s   22,564,405,444    +0.00%        85.4s   yes
#        45s   27,901,137,219   +23.65%       111.9s   NO - cut off
#       120s   30,637,712,508   +35.78%       187.6s   NO - cut off
#       300s   30,659,850,448   +35.88%       243.1s   yes  (climbed 176.6s)
#
# 45 was costing 9.8% of the allocation here. The value curve is flat past
# 120s (120 captures 99.93% of 300's), so 180 is 120 plus headroom: the climb
# is wall-clock, so how long convergence takes depends on machine load, and a
# ceiling set at the measured convergence point would bind again on a busier
# machine. The earlier "45s is not the bottleneck" reading (2026-08-02) was a
# Wind boss with the gimmick OFF - the constraint changes the search, so that
# measurement never covered this case.
SWAP_TIME_BUDGET_SEC = 180.0


class InfeasibleDraft(ValueError):
    """A draft deck's locked/placed units fit no legal deck shape, the pool is
    exhausted before every drafted deck can be completed, or the draft spends one
    owned character on two decks (two builds of one character)."""


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


def _gimmick_budget(available, boss, decks_left, seed=()):
    """The gimmick constraint for ONE deck about to be built, budgeting the
    weakness units across the decks still to build. None when there is nothing to
    enforce (gimmick off, element-less boss, or no weakness unit left at all).

    A deck must hold at least one weakness unit and at most
    `max(1, seed_held, w - decks_left + 1)` of them, where `seed_held` is how
    many weakness units `seed` (this deck's already-drafted seats, if any)
    holds by itself. The CAP is what keeps the greedy peel from starving later
    decks: without it, deck 1 can take two of three weakness units and deck 3
    gets none, which drops the satisfied count below the min(M, N) the design
    promises. Flooring at `seed_held` matters only on the seed path - the free
    peel has no seed, so `seed=()` leaves its cap exactly
    `max(1, w - decks_left + 1)`. Without the floor, a draft that pins two
    weakness units into one deck against a thin remaining pool can compute a
    cap below what the seed already holds, making the constrained completion
    unsatisfiable and falling through to the caller's unconstrained
    `complete(None)` retry - which drops the cap for that deck ENTIRELY,
    defeating the starvation guard exactly where a thin roster needs it most.

    On a real roster the cap never binds - 60-80 units carry 12-16 of any one
    element, so it sits at 8 or more and a 5-unit deck cannot reach it. It bites
    only on thin rosters, which is exactly where the starvation happens.

    On a thin roster the cap can still cost a DECK, not just bind uselessly:
    fuzzed over 300 thin rosters with a tied scorer, the constrained argmax
    sometimes picked a completion that spent a scarce burst tier, leaving the
    next deck's remaining pool fitting no ALLOWED_SHAPES at all - fewer decks
    formed than the unconstrained peel would have managed (17/300 runs). The
    min(M, N) satisfied-count invariant still held everywhere in the same fuzz
    (0/300 breaks with the cap, 107/300 without), so this is a real but
    separate cost from what the cap is FOR - shape starvation, not filter
    emptiness - and it is thin-roster-only for the same reason the cap itself
    is: a real 60-80-unit roster's cap sits at 8+ and a 5-unit deck cannot
    reach it, so it never forces this tradeoff there either.
    """
    w = weakness_holders(available, boss)
    if w == 0:
        return None
    weakness = weakness_of(boss.element)
    seed_held = sum(1 for u in seed if u.element == weakness)
    cap = max(1, seed_held, w - decks_left + 1)

    def ok(units):
        held = sum(1 for u in units if u.element == weakness)
        return 1 <= held <= cap

    return ok


def _satisfied_count(decks, boss):
    """How many of these decks can break the boss's gimmick. 0 whenever there is
    no gimmick, which makes the swap guard below inert on the common path."""
    if not boss.elemental_interrupt_required or boss.element is None:
        return 0
    return sum(1 for deck in decks if deck_breaks_gimmick(deck, boss))


def _gimmick_floor(decks, boss):
    """The number of gimmick-breaking decks a swap may not take us below: never
    fewer than we already hold.

    Takes no target/cap parameter: the most this roster could ever satisfy is
    min(M, N) (M = weakness-element units on the roster, N = decks), but that
    bound cannot bind here and needs no explicit clamp. Satisfied decks are
    disjoint - each holds at least one of the M weakness units, and a unit
    sits in only one deck - so `_satisfied_count(decks, boss)` can never
    exceed min(M, N) in the first place; neither M nor N changes under a
    swap. Kept as a named, tested function (not inlined as `_satisfied_count`)
    because it states the invariant the swap guard actually relies on.
    """
    return _satisfied_count(decks, boss)


def allocate_decks(roster, boss: BossProfile, num_decks=5, draft=None,
                   locked=frozenset(), time_budget_sec=SWAP_TIME_BUDGET_SEC, workers=None,
                   alternatives=None, cancel=None):
    """`cancel` (see app.cancellation) stops a run whose caller went away.

    It reaches the search two ways, because the search has two kinds of waiting
    in it: the loops below ask it between iterations, and the pool registers
    itself so a cancel arriving mid-batch folds the worker processes rather
    than waiting out a batch that can run tens of seconds.
    """
    cancel = cancel or NEVER
    # Serial (the default) never constructs a SimPool, so the sim path stays
    # exactly the pre-parallelism one (and test stubs of evaluate_deck keep
    # working - SimPool holds its own module binding they can't patch).
    worker_count = resolve_workers(workers)
    pool = SimPool(roster, boss, workers=workers) if worker_count > 1 else None
    try:
        if pool is not None:
            cancel.attach(pool)
        cancel.check()
        by_slug = {u.slug: u for u in roster}
        draft = draft or []
        # Pooling is per OWNED CHARACTER, not per slug: the player fields all of
        # these decks simultaneously, so seating one build of a character spends
        # her and retires her other builds too. Keying on the slug instead let
        # one Rapi: Red Hood hold a seat in deck 2 as B3 and another in deck 4
        # as B1 - a formation the game cannot produce.
        drafted = [character_of(u.slug) for deck in draft for u in deck]
        placed = set(drafted)
        if len(drafted) != len(placed):
            twice = sorted({b for b in placed if drafted.count(b) > 1})
            raise InfeasibleDraft(
                f"one owned character drafted into more than one deck: {twice}")
        remaining = [u for u in roster if character_of(u.slug) not in placed]

        # One fit serves the whole allocation: the surrogate is additive over
        # unit membership, so coefficients learned on the full roster score any
        # subset of it - the same fit ranks a seeded deck's completions and
        # every peeled deck after it. Fitted on first demand and at most once,
        # so an allocation whose searches all fit their budget never pays for
        # it; `roster` (not `remaining`) keys the shared cache entry.
        fitted = {}

        def ranker():
            if "cascade" not in fitted:
                model = cached_fit_surrogate(
                    roster, boss, lambda decks: _score_batch(decks, boss, pool))
                fitted["cascade"] = Cascade(model) if model is not None else None
            return fitted["cascade"]

        decks = []  # each: ordered list of units (canonical order from the search)
        for seed in draft:                       # seed decks: complete around placed units
            cancel.check()
            # One completion per concrete reading of the seed; the best wins, so
            # a drafted character's mode is chosen by what her finished deck
            # actually scores rather than by declaration order.
            readings = _seed_choices(seed, alternatives)
            # Ask for the ranker only once a reading has actually blown the
            # completion budget - the probe stops at the first ordering past it,
            # so asking costs nothing when the answer is no.
            cascade = None if all(
                completions_fit_budget(reading, remaining) for reading in readings
            ) else ranker()
            # The seat budget counts the seed's own weakness units as available:
            # a drafted deck that already holds one needs no second. `seed=`
            # also floors the CAP at what the seed already holds, so a draft
            # that pins two weakness units into one deck can never compute a
            # cap below 2 and fall through to the unconstrained retry below.
            gimmick = _gimmick_budget(list(readings[0]) + remaining, boss,
                                      num_decks - len(decks), seed=readings[0])

            def complete(deck_filter):
                return max(
                    (c for reading in readings
                     for c in best_completions(reading, remaining, boss, top_n=1,
                                               pool=pool, cascade=cascade,
                                               deck_filter=deck_filter)),
                    key=lambda c: c["total_damage"], default=None)

            found = complete(gimmick)
            if found is None and gimmick is not None:
                # The draft cannot break the gimmick - the player filled the seats
                # with units that lack the weakness element. Solve it unconstrained
                # rather than refuse a deck they can field; the UI flags it instead
                # (design B.2 / B.6).
                found = complete(None)
            if found is None:
                raise InfeasibleDraft(
                    f"cannot complete a legal deck from {[u.slug for u in seed]}")
            units = [by_slug[s] for s in found["deck"]]
            decks.append(units)
            # newly-pulled fillers leave the pool
            used = {character_of(u.slug) for u in units} - placed
            remaining = [u for u in remaining if character_of(u.slug) not in used]

        # Probed against `remaining`, not `roster`, so a small leftover pool
        # never pays for a fit nothing will use; `probed` bounds the question to
        # once for the whole peel.
        cascade = None
        probed = False
        while len(decks) < num_decks:            # free decks: greedy peeling (unchanged)
            cancel.check()
            if not probed:
                probed = True
                if _orderings_within_budget(remaining, SEARCH_SIM_BUDGET) is None:
                    cascade = ranker()
            gimmick = _gimmick_budget(remaining, boss, num_decks - len(decks))
            # No unconstrained retry needed here, unlike the seed path above:
            # search_best_decks already falls back to an unfiltered resolve
            # whenever a non-None deck_filter empties the search space (see its
            # `if not orderings and deck_filter is not None` retry in
            # deck_search.py), so passing `gimmick` straight through already
            # gets "as many decks as we can" for free. best_completions has no
            # such retry of its own - a deliberate Task 9 asymmetry - which is
            # why the seed path still needs its own explicit fallback.
            found = search_best_decks(remaining, boss, top_n=1, pool=pool,
                                      cascade=cascade, deck_filter=gimmick)
            if not found:
                break
            units = [by_slug[slug] for slug in found[0]["deck"]]
            decks.append(units)
            used = {character_of(u.slug) for u in units}
            remaining = [u for u in remaining if character_of(u.slug) not in used]

        # time_budget_sec caps the swap-improvement phase ONLY, starting when the
        # swap phase itself starts: greedy peeling above and the final ordering
        # polish below are unbudgeted, so a valid (if unimproved) allocation is
        # returned even with a zero budget. The hill-climb's DECISIONS stay
        # sequential - each accepted swap changes the state the next candidate is
        # judged against - but the candidates it judges are scored in batches
        # through the same pool the peel used, which is what lets the phase reach
        # a local optimum inside the budget instead of being cut off mid-climb.
        deadline = time.monotonic() + time_budget_sec
        cancel.check()
        _swap_pass(decks, remaining, boss, deadline, locked=locked, pool=pool,
                   batch=max(_MIN_SWAP_BATCH, worker_count * SWAP_BATCH_PER_WORKER),
                   cancel=cancel)

        summaries = [best_ordering_summary(units, boss, pool) for units in decks]
        return {"decks": summaries,
                "leftover_slugs": sorted(u.slug for u in remaining)}
    finally:
        if pool is not None:
            pool.close()


def _swap_pass(decks, leftovers, boss, deadline, locked=frozenset(), pool=None,
               batch=_MIN_SWAP_BATCH, cancel=None):
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
    locked = {character_of(slug) for slug in locked}
    cancel = cancel or NEVER
    scores = _score_batch(decks, boss, pool)
    # The guard only needs to know WHETHER the gimmick can bind at all, not the
    # cap min(M, N) (M = weakness-element units, N = decks) itself - that bound
    # never binds `_gimmick_floor`'s invariant (see its docstring), so nothing
    # downstream needs the number. The climb may move weakness units between
    # decks freely; what it may not do is lower the number of decks that hold
    # one.
    gimmick_active = weakness_holders(
        [u for deck in decks for u in deck] + list(leftovers), boss) > 0
    # One pass's work items: for each deck, every deck after it, then the bench.
    items = [(i, j) for i in range(len(decks))
             for j in [*range(i + 1, len(decks)), None]]
    improved = True
    while improved and time.monotonic() < deadline:
        improved = False
        for done, (i, j) in enumerate(items):
            # The longest phase in the run - it climbs until it converges or the
            # budget runs out - so it is asked per work item rather than only
            # once per pass.
            cancel.check()
            # An item may spend only its EQUAL SHARE of what is left, so a
            # budget that binds cuts every deck a little instead of being spent
            # entirely on the first one. Measured on Fienn's roster (2026-08-04,
            # 5 decks, gimmick on): deck 1's five items took all 45 seconds and
            # decks 2-5 got no swap AT ALL - which left a bench unit worth
            # +969,725,138 unseated beside deck 3. An item that runs out of
            # candidates before its share is up hands the rest to the items
            # behind it, so a climb that fits inside the budget converges
            # exactly as it did before.
            now = time.monotonic()
            partner = leftovers if j is None else decks[j]
            improved |= _try_swaps(decks, scores, i, partner, j, boss,
                                   now + (deadline - now) / (len(items) - done),
                                   locked, pool, batch, gimmick_active)


def _swap_is_fieldable(deck, a, partner, k, partner_is_deck):
    """Whether exchanging `deck`'s seat `a` with `partner`'s seat `k` leaves
    every deck it touches one the player could actually field. `partner` is
    either another deck (`partner_is_deck`) or the leftover bench, which has no
    shape of its own to keep.

    Only a CROSS-tier exchange can fail this, because it is the only kind that
    changes a deck's B1/B2/B3 shape - and the shape is what decides whether the
    deck can reach Full Burst at all. A same-tier pair is admitted without the
    check, which is what keeps the same-tier half of the climb behaving exactly
    as it did before cross-tier moves were allowed.
    """
    if deck[a].burst_tier == partner[k].burst_tier:
        return True
    trial = list(deck)
    trial[a] = partner[k]
    if not deck_is_valid(trial):
        return False
    if not partner_is_deck:
        return True
    partner_trial = list(partner)
    partner_trial[k] = deck[a]
    return deck_is_valid(partner_trial)


def _try_swaps(decks, scores, i, partner, j, boss, deadline, locked, pool, batch,
               gimmick_active=False):
    """Unit swaps between deck `i` and `partner` - either another deck (`j` is
    its index, so its score counts toward the improvement too) or the leftover
    bench (`j` is None, and a benched unit contributes nothing).

    The two seats need not share a burst tier. Real play uses three deck shapes,
    so the unit that deserves a seat is regularly not the tier of the one it
    displaces - a Burst-1 cooldown holder earns her chair from a Burst 3, taking
    a (1,1,3) deck to (2,1,2). Refusing cross-tier exchanges put every such move
    outside the search, and on a real 58-unit roster that was the whole
    difference: the climb reached a local optimum with no same-tier gain left
    anywhere, while two bench units were each worth billions in a seat of
    another tier (measured 2026-08-02, +8.45% over the five decks).

    Candidates are scored a batch at a time so a SimPool can fan them out. The
    walk over a scored batch keeps the serial rule exactly: accept the FIRST
    candidate that improves, in this order. An acceptance makes the rest of that
    batch stale - those scores describe a deck that no longer exists - so the
    loop re-batches from the next candidate instead of trusting them. Wasted
    scoring is bounded by the batch and rare in practice: measured on a 78-unit
    roster, under 1% of candidates are ever accepted.

    Lock, the filter that never goes stale, is applied once up front: no swap
    moves a locked unit, whatever its tier.

    Two filters CAN flip when a swap is accepted, so the unscanned tail is
    re-filtered rather than trusted. `seated` upholds the one-owned-character
    rule across the whole allocation: bringing a bench unit in spends that
    character, retiring her other builds (deck-to-deck swaps need no such check
    - both units are already seated, so exchanging them cannot make a character
    appear twice). `_swap_is_fieldable` is the cross-tier counterpart: an
    accepted cross-tier swap changes the deck's shape, so a later candidate
    judged legal against the OLD shape may not be legal against the new one.
    """
    # Bench swaps only: the incoming character must not already hold a seat -
    # in THIS deck or any other, since the player fields all of them at once.
    seated = None if j is not None else {character_of(u.slug)
                                         for deck in decks for u in deck}

    # `floor` only changes when a swap is actually ACCEPTED (decks[i]/partner[k]
    # mutate) - admissible() asks gimmick_ok() once per candidate pair against
    # the SAME decks state, so recomputing it inside gimmick_ok would redo the
    # same _satisfied_count walk for every pair asked. Computed once here and
    # refreshed once per acceptance below instead.
    floor = _gimmick_floor(decks, boss) if gimmick_active else 0

    def gimmick_ok(a, k):
        """The swap must not lower how many decks can break the gimmick below
        `floor` - `decks`/`partner` are read live, so the trial reflects the
        swap actually under test. An accepted swap that RAISED the count
        raises `floor` with it (see the refresh after acceptance below)."""
        if not gimmick_active:
            return True
        trial = list(decks)
        deck_i = list(decks[i])
        deck_i[a] = partner[k]
        trial[i] = deck_i
        if j is not None:
            deck_j = list(partner)
            deck_j[k] = decks[i][a]
            trial[j] = deck_j
        return _satisfied_count(trial, boss) >= floor

    def admissible(a, k):
        return ((seated is None or character_of(partner[k].slug) not in seated)
                and _swap_is_fieldable(decks[i], a, partner, k, j is not None)
                and gimmick_ok(a, k))

    # `locked` arrives already keyed by owned character (see _swap_pass).
    candidates = [(a, k)
                  for a in range(5) if character_of(decks[i][a].slug) not in locked
                  for k in range(len(partner))
                  if character_of(partner[k].slug) not in locked
                  and admissible(a, k)]
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
            # who came in occupies decks[i][a]. Both sides of that exchange move,
            # so the seat-exclusion set follows it before the tail is re-judged.
            seated.discard(character_of(partner[k].slug))
            seated.add(character_of(decks[i][a].slug))
        if gimmick_active:
            floor = _gimmick_floor(decks, boss)
        candidates = candidates[:start] + [(a2, k2) for a2, k2 in candidates[start:]
                                           if admissible(a2, k2)]
    return improved


def _combined(alloc):
    return sum(d["total_damage"] for d in alloc["decks"])


def _is_complete(draft, num_decks):
    return len(draft) == num_decks and all(len(deck) == 5 for deck in draft)


def _better(a, b):
    return a if _combined(a) >= _combined(b) else b


def _leftover_against(alloc, roster):
    # Character-keyed like the peel: a seated character's OTHER builds are not
    # benched units the player could still field, so they never reach the bench
    # (which the UI reads as "not allocated to a deck").
    used = {character_of(s) for d in alloc["decks"] for s in d["deck"]}
    return sorted(u.slug for u in roster if character_of(u.slug) not in used)


def recommend_from_draft(roster, boss, num_decks=5, draft=None,
                         locked=frozenset(), workers=None, alternatives=None,
                         cancel=None):
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
    locked = {character_of(slug) for slug in locked}
    # from-scratch pass honors hard locks (seed ONLY the locked units, leaving
    # flexible seats free to explore all shapes) - without this, a scratch win
    # could drop a locked unit. Empty when there are no locks => pure from-scratch.
    locked_seed = [[u for u in deck if character_of(u.slug) in locked]
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
                                     alternatives=alternatives, cancel=cancel)
    else:
        recommended = allocate_decks(roster, boss, num_decks=num_decks,
                                     draft=(locked_seed or None), locked=locked,
                                     workers=workers, alternatives=alternatives,
                                     cancel=cancel)

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
                           locked=locked, workers=workers,
                           alternatives=alternatives, cancel=cancel)
        s = allocate_decks(drafted, boss, num_decks=num_decks,
                           draft=(locked_seed or None), locked=locked,
                           workers=workers, alternatives=alternatives,
                           cancel=cancel)
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
        # UI reports from being inflated by a mode the player never chose. Not
        # every reading is fieldable (a variant swap can change burst tier and
        # break ALLOWED_SHAPES or tier-1 seating), so deck_is_valid filters them
        # the same way deck_evaluation does - a fixed deck handed to this
        # function has to ask that question explicitly, per deck_is_valid's own
        # docstring, or this baseline could score a deck the search would never
        # produce.
        baseline_total = sum(
            max(best_ordering_summary(reading, boss)["total_damage"]
                for reading in _seed_choices(deck, alternatives)
                if deck_is_valid(reading))
            for deck in draft)

    pinned_by_deck = [[s for s in d["deck"] if character_of(s) in locked]
                      for d in recommended["decks"]]
    return {"recommended": recommended, "within_draft": within_draft,
            "baseline_total_damage": baseline_total, "pinned_by_deck": pinned_by_deck}


def best_ordering_summary(units, boss, pool=None):
    # Final polish: the swap pass scored canonical orders only; pick the best
    # intra-tier ordering for the finished deck (a handful of sims per deck).
    # Batch-scored; ties keep the first ordering, like the serial `>` did.
    orderings = list(_intra_tier_orderings(units))
    totals = _score_batch(orderings, boss, pool)
    best_i = max(range(len(orderings)), key=lambda i: (totals[i], -i))
    return _summarize(orderings[best_i], evaluate_deck(orderings[best_i], boss))
