# Phase 5 — five-deck allocation layer (design)

- Date: 2026-07-17
- Status: approved (Fienn, 2026-07-17 — approach A: perf pass → pruned search →
  greedy allocation; Stage 0 runs as its own preceding plan, see
  `2026-07-17-effect-registry-performance-design.md`)
- Scope: pick up to 25 units from the user's roster and split them into up to
  five disjoint 5-unit decks that maximize **summed** damage against **one**
  boss profile, inside a web-request budget (seconds to ~1 minute). Exposed as
  a new API endpoint + frontend mode.

## Decisions already made (Fienn, 2026-07-17)

- All five decks fight the **same boss** (one BossProfile; no deck↔boss
  assignment problem).
- Partial rosters return **as many decks as possible** (0–5), consistent with
  the `excluded_slugs` honesty policy; 422 only when not even one feasible deck
  exists.
- Budget: web UI, seconds to ~1 minute per request.
- Domain knowledge to bake in (Fienn, 2026-07-17):
  1. Real decks are shaped B1/B2/B3 = (1,1,3), (1,2,2) or (2,1,2) — enumerate
     **only these shapes** (the current "≥1 of each tier" rule also admits
     shapes that never occur in play).
  2. Burst-CDR lives mostly on B1 units; two-B1 decks pair a strong non-CDR
     buffer with a CDR holder. No special handling — the simulator already
     models CDR, so shape (2,1,2) being allowed is enough for the search to
     find these.
  3. Some B2 units work as **synergy sets** (Mint+Prika, Mast+Anchor; sometimes
     solo) — candidate pruning must not separate them blindly.
  4. **SG-themed decks**: SG B3 attackers need Tove (her buffs are SG-scoped);
     typical shape Tove + (Arcana: Fortune Mate / other B2) + SG B3 ×2 +
     (CDR unit / SG B3 / other buffer). A non-SG reference context undervalues
     every SG unit, so themed candidates are generated explicitly.
  5. Diesel: Winter Sweets prefers bursting on even-numbered cycles — the
     scheduler can't express "skip a cycle" today. **Deferred** (Diesel isn't
     encoded yet); recorded as an engine gap so the deck evaluator grows a
     per-unit burst-scheduling hint only when a consumer exists.

## Components

### 1. Pruned single-deck search (Stage 1, `deck_search.py`)

The exhaustive `find_best_decks` stays (tests, small rosters). A new
budget-aware search wraps it:

1. **Shape enumeration**: combinations are generated per allowed shape
   ((1,1,3)/(1,2,2)/(2,1,2)) from per-tier unit lists instead of C(n,5)
   filtering.
2. **Candidate pool cut** (only when the roster exceeds what the budget can
   enumerate): rank units by **marginal contribution** — swap each unit into
   fixed reference decks (one with a CDR B1, one without; ~2 sims per unit) —
   and keep the top M per tier. Two guards:
   - **Synergy sets** (curated constant: `{mint, prika}`, `{mast-romantic-maid,
     anchor-innocent-maid}`, …): if one member survives the cut, its partners
     join the pool, and sets are measured together when ranking.
   - **Weapon-themed pool**: if Tove (more generally: any unit with a
     weapon-scoped buff) is in the roster, additionally enumerate decks from
     the themed sub-pool (Tove + B2s + SG B3s + utility B1s) so themed decks
     compete on score, not on surviving a mis-contextual cut.
3. **Deferred permutations**: score each combination once in canonical tier
   order; only the top K combinations get their intra-tier permutations
   evaluated (the order decides nuker-vs-backup roles; a canonical-order score
   ranks combinations well enough to shortlist).

M and K are module constants tuned empirically against the budget once Stage 0
lands (starting points: M≈15/tier, K≈50) — recorded next to the constants.

### 2. Allocation (Stage 2, new `backend/app/deck_allocation.py`)

- **Greedy peeling**: run the Stage 1 search on the remaining roster, commit
  the best deck, remove its units, repeat (≤5 decks; stop when no feasible
  deck remains). Same-boss ⇒ total = sum of independent deck scores, and deck
  damage concentrates value in the first decks, so peeling lands near the
  optimum.
- **Swap improvement**: while the time budget allows, try swapping unit pairs
  between two decks (and single units with the unused leftovers), re-simulate
  only the affected decks (2 sims), keep the swap iff the summed total
  improves. Recovers the classic greedy mistake (stacking two buffer cores in
  deck 1 when splitting them supports two decks better). Budget-bounded
  hill-climb; no optimality claim (the problem is NP-hard) — this is the
  standard practical combo for partition problems.

### 3. API

`POST /api/recommend-raid` (new; `POST /api/recommend` keeps its single-deck
contract but switches to the same budget-aware search — the candidate cut
simply doesn't engage when the roster is small enough to enumerate fully, so
small-roster behavior is unchanged):

- Request: same roster/boss payload as `/api/recommend` (+ optional
  `num_decks`, default 5).
- Response: `decks: [{deck, total_damage, burst_damage,
  normal_attack_damage}]` (ordered as allocated, deck 1 first),
  `combined_total_damage`, `excluded_slugs` (unloadable, as today),
  `leftover_slugs` (loadable but unassigned). 422 only when zero feasible
  decks exist after exclusion, naming the exclusions.

### 4. Frontend

A "레이드 (5덱)" mode on the existing recommend view: same roster input, calls
`/api/recommend-raid`, renders the deck list with per-deck damage + combined
total + leftover/excluded labels. No new input fields.

## Error handling

Reuses the roster loader exclusion policy unchanged. Time budget is a server
constant (not client input); if the budget expires mid-improvement, the current
best allocation is returned (greedy result is always available first).

## Testing

- Shape enumerator: exact expected combinations on tiny synthetic rosters.
- Candidate cut: synergy partner retained when its mate survives; themed pool
  generated when Tove present.
- Allocation: deterministic tiny-roster cases (greedy picks the known best);
  a constructed synergy-split case that greedy gets wrong and one swap fixes —
  proves the improvement pass moves total damage.
- API: response shape, partial roster (fewer than 25 loadable → fewer decks),
  zero-deck 422, excluded/leftover reporting.
- Perf smoke: full 42-unit-roster allocation completes within the budget
  (marked slow; exact wall-clock asserted loosely).

## Out of scope

- Different bosses per deck (union-raid style deck↔boss assignment).
- Per-unit burst scheduling policies (Diesel even-cycle — engine gap, needs
  its consumer encoded first).
- Global optimality guarantees; Phase 7 automation.
