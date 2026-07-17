# EffectRegistry query performance pass (design)

- Date: 2026-07-17
- Status: approved (Fienn, 2026-07-17 — Stage 0 of the Phase 5 plan, run as its
  own preceding plan)
- Scope: make `EffectRegistry.total_for` fast enough that a 180-second raid
  simulation drops from ~2.4 s to tens of milliseconds, **without changing any
  simulation output**. Prerequisite for the 5-deck allocation layer (Phase 5)
  and an immediate win for the existing `POST /api/recommend` exhaustive search.

## Problem (measured, 2026-07-17)

Profiling one `evaluate_deck` call (5-unit deck, 180 s fight):

- total 2.99 s, of which `EffectRegistry.total_for` is **2.79 s (93%)**.
- ~20,800 damage instances × ~12 stat lookups = **255K `total_for` calls**.
- Each call linearly scans **every** registered effect (`_is_active` ran
  5.25M times): the cost is the data structure, not the math.

At 2.4 s/sim the exhaustive deck search is already unusable for real rosters
(42 loadable units → C(42,5) ≈ 850K combos), and Phase 5 multiplies the demand.

## Approach: per-key piecewise-constant segment table

`total_for(stat, target, now)` answers "sum of active matching effect values at
time `now`". Effects are intervals `[applied_at, applied_at + duration)` (open
ended when `duration is None`). For a fixed query key the answer is a
**step function of time**, so it can be precomputed once and queried by binary
search:

1. **Cache key** = `(stat, target["slug"], target["element"])` — the only
   target fields scope matching reads. A deck has ≤ ~6 distinct targets and
   ~12 stats, so at most a few dozen tables per sim.
2. **Build (lazy, on first query of a key)**: filter entries to those matching
   the key's stat + scope (including the `self`/`source_slug` rule), collect
   all interval boundaries, sort+dedupe them into segments. For each segment,
   sum the values of the intervals covering it **in original insertion order**.
3. **Query**: `bisect_right` into the segment boundaries, return the
   precomputed segment total. O(log n) per call.

### Bit-exactness (why insertion-order summation)

Float addition is not associative. The naive loop sums active values in
insertion order; summing in time order (classic prefix-sum deltas) could flip
last-ULP bits and trip strict-equality asserts. Summing each segment in
insertion order performs **the exact same additions in the exact same order**
as the naive loop for any time inside the segment, so results are
bit-identical, not approximately equal.

### Invalidation (the correctness hazard)

Stored effects are **mutated in place**: `add_refreshing` truncates earlier
effects' durations, `truncate_open_ended` closes open-ended ones, and both are
documented as valid at any point relative to queries (replay-style passes rely
on it). Therefore:

- The registry keeps a `_version` counter bumped by every mutating method
  (`add`, `add_refreshing`, `truncate_open_ended`).
- Each cached table records the version it was built at; a stale table is
  rebuilt on next query. Interleaved mutate/query phases stay correct and only
  cost rebuilds; the 255K-query damage pass (phase 2, no mutations) builds each
  table once.
- **Audit task**: grep for writes to `Effect.duration` (or `_entries`) outside
  registry methods; any found must be routed through a registry method first.
  The registry's mutation methods become the single mutation path.

### Untouched

- Public API: `total_for`, `add`, `add_refreshing`, `truncate_open_ended`,
  `drain_pulses`, round grants — signatures and semantics unchanged. Callers
  (raid_simulator, skill rules, tests) need no edits.
- Pulses and RoundGrants keep their list storage (drained once / converted
  once; not hot).
- No simulator algorithm changes, no numpy, no parallelism — YAGNI unless the
  segment table falls short of the target (decide on measurement).

## Verification

1. **Full suite green unchanged** (654 passed baseline) — no test edits.
2. **Parity test** (new, permanent): a reference naive implementation (the
   current loop, kept as a private module-level function in the test) compared
   against `total_for` for **exact equality** across real simulations — run
   2–3 real decks, then query every (stat, member, t) over a dense time grid
   plus all boundary instants, including after refresh/truncate mutations.
3. **Benchmark** (repeatable script, committed to `scripts/`): evaluate_deck
   before/after. Target: ≤ 50 ms per 180 s sim (~50×). Record the measured
   number in the plan's completion notes; if the target is missed, measure
   where the remaining time goes before adding machinery.

## Consequences

- Registry gains internal state (cache + version) — slightly more complex, but
  the mutation-method audit actually tightens the module's boundary.
- Existing `/api/recommend` gets faster with no API change; the exhaustive
  search's combinatorial limit remains (addressed by the Phase 5 allocation
  design, separate spec).

---

## Stage 0.5 — per-target epoch memo (added 2026-07-17, Fienn-approved)

Stage 0 measured 133.66 ms/sim (18×) but missed the ≤50 ms target. Profiling
shows no single hotspot: the residual is flat call overhead — 255K `total_for`
calls per sim, ~12–18 of them per damage instance with the SAME (target, time).
Decision (Fienn, 2026-07-17): reduce the call **count**, not per-call cost.

### Approach

1. **`EffectRegistry.state_epoch(target, now) -> int`** (new method): bisect
   into a per-(slug, element) **merged** boundary timeline — the union of
   interval boundaries of every effect matching the target under ANY stat.
   Within one epoch no matching effect starts or ends, so every stat total is
   constant. Cached and version-invalidated exactly like the segment tables.
   A read-only **`version` property** is also added so callers can key memos.
2. **Shared matching**: the scope-match logic is extracted into a module-level
   `_matches_target(effect, target)` used by both `_build_segment_table` and
   the merged-boundary builder — one matching semantics, no duplication.
3. **`raid_simulator` stat-bundle memo**: phase-2 damage computation resolves
   a fixed 18-stat bundle (every registry stat `_damage_instance`,
   `normal_attack_type` and `_normal_attack_percent` can read) once per
   `(slug, state_epoch, registry.version)` and reads bundle entries instead of
   calling `total_for` per stat. Per-instance non-registry terms
   (attack_coefficient, extra_flat_atk/extra_charge_bonus, the full-burst
   window check, element multiplier) stay per-instance.

### Why outputs stay bit-identical

Bundle values come from the same `total_for`; the epoch invariant guarantees a
bundle built at any time inside the epoch reads the same per-segment constants
as a query at any other time inside it, and the version key drops stale
bundles whenever the registry mutates (so replay-late effects behave exactly
as before). Verification: full suite green unchanged, parity net untouched,
new unit tests for `state_epoch` semantics, benchmark re-measured.

### Amendment to the API constraint

Stage 0's "public API unchanged" becomes "existing methods unchanged; two
additions: `state_epoch(target, now)` and the `version` property".

### Stop condition

Target: ≤50 ms re-measured. If missed again, stop and report where the time
goes — no further machinery inside this stage.
