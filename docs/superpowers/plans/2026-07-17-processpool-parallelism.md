# ProcessPool Simulation Parallelism Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Cut the 42-unit five-deck allocation from 282 s toward the seconds-to-a-minute budget by fanning `evaluate_deck` batches out to a `ProcessPoolExecutor` (Fienn's chosen throughput lever, 2026-07-17 — tier-cap shrinking was rejected as a search-quality loss).

**Architecture:** `evaluate_deck(ordered_deck, boss)` is a pure ~100 ms function; the search layers issue hundreds-to-thousands of independent calls in map-shaped batches (canonical combo scoring, permutation refinement, candidate-pool measurement, final ordering polish). A new `SimPool` wraps a lazily-spawned `ProcessPoolExecutor`: workers are initialized once with the roster's specs + boss (so tasks travel as slug tuples, not re-pickled specs), and batches below a spawn threshold run inline so tiny requests/tests never pay pool cost. The swap hill-climb stays serial (each accepted swap changes the state the next candidate is judged against) — it is already capped at 45 s.

**Tech Stack:** stdlib `concurrent.futures.ProcessPoolExecutor` (Windows spawn), pytest. No new dependencies.

## Global Constraints

- Results must be bit-identical to the serial path (same floats, same ordering/tie behavior) — parity is tested, not assumed.
- `workers=None` (the default everywhere) keeps today's serial behavior; existing tests must stay green unchanged.
- Windows spawn: every function handed to the executor (worker fn, initializer) must be module-top-level in `app.sim_pool`.
- No import cycle: `app.sim_pool` imports from `app.deck_search`; `deck_search` must NOT import `sim_pool` (it takes an optional `pool` object instead).
- Python: `C:/Users/fienn/anaconda3/python.exe`; run tests with `PYTHONIOENCODING=utf-8` (project rule).

---

### Task 1: `SimPool` — serial inline path

**Files:**
- Create: `backend/app/sim_pool.py`
- Test: `backend/tests/test_sim_pool.py`

**Interfaces:**
- Produces: `SimPool(roster, boss, workers=None, spawn_threshold=None)` with `score_many(decks) -> list[float]`, `summarize_many(decks) -> list[dict]` (slim: `deck`/`total_damage`/`burst_damage`/`normal_attack_damage`, NO `result` key), `close()`, context-manager protocol. Module constant `SPAWN_THRESHOLD = 32`. `resolve_workers(workers)` (`None/0/1 -> 1`, `"auto" -> max(1, cpu_count-1)`, int passthrough).
- Consumes: `app.deck_search.evaluate_deck`.

- [ ] **Step 1: Write the failing tests** — parity of both methods against direct `evaluate_deck` on a tiny 5-unit roster (reuse `test_deck_search.real_five_roster()` and a 20 s boss so each sim is fast), and laziness (`_executor` stays `None` in serial mode).

```python
# backend/tests/test_sim_pool.py
from app.deck_search import BossProfile, evaluate_deck
from app.sim_pool import SimPool, resolve_workers
from tests.test_deck_search import real_five_roster


def short_boss():
    return BossProfile(element=None, core_hittable=False, fight_duration=20.0)


def test_resolve_workers_serial_values():
    assert resolve_workers(None) == 1
    assert resolve_workers(0) == 1
    assert resolve_workers(1) == 1
    assert resolve_workers(4) == 4
    assert resolve_workers("auto") >= 1


def test_serial_score_many_matches_direct_evaluate_deck():
    roster, boss = real_five_roster(), short_boss()
    deck_a, deck_b = list(roster), [roster[0], roster[1], roster[4], roster[3], roster[2]]
    with SimPool(roster, boss, workers=None) as pool:
        totals = pool.score_many([deck_a, deck_b])
    assert totals == [evaluate_deck(deck_a, boss)["total_damage"],
                      evaluate_deck(deck_b, boss)["total_damage"]]
    assert totals[0] != totals[1]  # ordering matters, so the two differ


def test_serial_summarize_many_matches_direct_evaluate_deck():
    roster, boss = real_five_roster(), short_boss()
    deck = list(roster)
    with SimPool(roster, boss, workers=None) as pool:
        (summary,) = pool.summarize_many([deck])
    result = evaluate_deck(deck, boss)
    assert summary == {
        "deck": [u.slug for u in deck],
        "total_damage": result["total_damage"],
        "burst_damage": sum(e["damage"] for e in result["damage_log"] if e["source"] == "burst"),
        "normal_attack_damage": sum(
            e["damage"] for e in result["damage_log"] if e["source"] == "normal_attack"),
    }


def test_serial_mode_never_spawns_an_executor():
    roster, boss = real_five_roster(), short_boss()
    with SimPool(roster, boss, workers=None) as pool:
        pool.score_many([list(roster)] * 40)  # over SPAWN_THRESHOLD, still serial
        assert pool._executor is None
```

- [ ] **Step 2: Run to verify failure** — `PYTHONIOENCODING=utf-8 python -m pytest tests/test_sim_pool.py -q` → FAIL (`ModuleNotFoundError: app.sim_pool`).

- [ ] **Step 3: Implement `app/sim_pool.py`** (worker-path methods included now but unreachable until Task 2's spawn logic — keep `_map` inline-only in this task):

```python
"""Process-pool deck evaluation for the budget-heavy search phases (Phase 5
throughput lever - ProcessPool parallelism, Fienn 2026-07-17).

evaluate_deck is a pure ~100 ms function of (ordered specs, boss); the search
layers issue map-shaped batches of independent calls. SimPool fans a batch out
to a ProcessPoolExecutor. Workers are initialized ONCE with the roster's specs
and the boss (spawn pickles initargs a single time), so each task travels as a
tuple of slugs - not as repeatedly re-pickled spec objects.

Small batches never spawn: batches below spawn_threshold run inline, so tiny
rosters, tests, and API smoke requests pay zero pool cost. The executor is
created lazily on the first big batch and reused until close().
"""
import os
from concurrent.futures import ProcessPoolExecutor

from app.deck_search import evaluate_deck

SPAWN_THRESHOLD = 32

_WORKER_SPECS = None
_WORKER_BOSS = None


def _init_worker(specs_by_slug, boss):
    global _WORKER_SPECS, _WORKER_BOSS
    _WORKER_SPECS = specs_by_slug
    _WORKER_BOSS = boss


def _slim_summary(deck_slugs, result):
    burst = sum(e["damage"] for e in result["damage_log"] if e["source"] == "burst")
    normal = sum(e["damage"] for e in result["damage_log"] if e["source"] == "normal_attack")
    return {"deck": list(deck_slugs), "total_damage": result["total_damage"],
            "burst_damage": burst, "normal_attack_damage": normal}


def _score_slugs(slugs):
    deck = [_WORKER_SPECS[s] for s in slugs]
    return evaluate_deck(deck, _WORKER_BOSS)["total_damage"]


def _summarize_slugs(slugs):
    deck = [_WORKER_SPECS[s] for s in slugs]
    return _slim_summary(slugs, evaluate_deck(deck, _WORKER_BOSS))


def resolve_workers(workers):
    """None/0/1 -> serial; "auto" -> leave one core for the event loop."""
    if workers in (None, 0, 1):
        return 1
    if workers == "auto":
        return max(1, (os.cpu_count() or 2) - 1)
    return int(workers)


class SimPool:
    """Batched deck evaluation: inline below spawn_threshold, pooled above."""

    def __init__(self, roster, boss, workers=None, spawn_threshold=None):
        self._specs = {u.slug: u for u in roster}
        self._boss = boss
        self._workers = resolve_workers(workers)
        self._spawn_threshold = spawn_threshold
        self._executor = None

    def score_many(self, decks):
        return self._map(_score_slugs, lambda deck: evaluate_deck(deck, self._boss)["total_damage"], decks)

    def summarize_many(self, decks):
        return self._map(
            _summarize_slugs,
            lambda deck: _slim_summary([u.slug for u in deck], evaluate_deck(deck, self._boss)),
            decks,
        )

    def _map(self, worker_fn, inline_fn, decks):
        return [inline_fn(deck) for deck in decks]

    def close(self):
        if self._executor is not None:
            self._executor.shutdown()
            self._executor = None

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        self.close()
```

- [ ] **Step 4: Run to verify pass** — `PYTHONIOENCODING=utf-8 python -m pytest tests/test_sim_pool.py -q` → 4 passed.
- [ ] **Step 5: Commit** — `git add backend/app/sim_pool.py backend/tests/test_sim_pool.py && git commit -m "feat: SimPool batched deck evaluation (serial inline path)"`

### Task 2: `SimPool` — process-pool spawn path

**Files:**
- Modify: `backend/app/sim_pool.py` (`_map` only)
- Test: `backend/tests/test_sim_pool.py`

**Interfaces:**
- Produces: `_map` spawns the executor when `workers > 1` AND `len(batch) >= threshold` (threshold = `self._spawn_threshold` if set, else module `SPAWN_THRESHOLD` read at call time so tests can monkeypatch it); reuses it across batches; `chunksize = max(1, n // (workers * 4))`.

- [ ] **Step 1: Write the failing tests**

```python
def test_pooled_results_match_serial_bit_for_bit():
    roster, boss = real_five_roster(), short_boss()
    decks = [list(roster), [roster[0], roster[1], roster[4], roster[3], roster[2]]]
    with SimPool(roster, boss, workers=None) as serial:
        expected_scores = serial.score_many(decks)
        expected_summaries = serial.summarize_many(decks)
    with SimPool(roster, boss, workers=2, spawn_threshold=1) as pooled:
        assert pooled.score_many(decks) == expected_scores
        assert pooled._executor is not None  # the pool really spawned
        assert pooled.summarize_many(decks) == expected_summaries


def test_small_batches_stay_inline_even_with_workers():
    roster, boss = real_five_roster(), short_boss()
    with SimPool(roster, boss, workers=2) as pool:  # default threshold 32
        pool.score_many([list(roster)])
        assert pool._executor is None
```

- [ ] **Step 2: Run to verify failure** — `test_pooled_results_match_serial_bit_for_bit` FAILS on `pooled._executor is not None` (inline-only `_map`).
- [ ] **Step 3: Implement** — replace `_map`:

```python
    def _map(self, worker_fn, inline_fn, decks):
        threshold = self._spawn_threshold if self._spawn_threshold is not None else SPAWN_THRESHOLD
        if self._workers <= 1 or len(decks) < threshold:
            return [inline_fn(deck) for deck in decks]
        if self._executor is None:
            self._executor = ProcessPoolExecutor(
                max_workers=self._workers,
                initializer=_init_worker,
                initargs=(self._specs, self._boss),
            )
        slug_tuples = [tuple(u.slug for u in deck) for deck in decks]
        chunksize = max(1, len(slug_tuples) // (self._workers * 4))
        return list(self._executor.map(worker_fn, slug_tuples, chunksize=chunksize))
```

- [ ] **Step 4: Run to verify pass** (spawn test takes a few seconds on Windows — acceptable, it's the only spawning test in the file). Then the full suite once: no regressions, pristine output (watch for `filterwarnings = error` tripping on multiprocessing warnings; if one fires, fix the resource handling — e.g. explicit `close()` — never loosen the filter).
- [ ] **Step 5: Commit** — `git commit -m "feat: SimPool lazy ProcessPoolExecutor spawn path"`

### Task 3: `deck_search` accepts a pool

**Files:**
- Modify: `backend/app/deck_search.py` (`search_best_decks`, `prune_candidate_pool`; add module-level `_score_batch`)
- Test: `backend/tests/test_deck_search.py`

**Interfaces:**
- Produces: `search_best_decks(roster, boss, top_n=5, sim_budget=1200, permutation_top_k=40, pool=None)`, `prune_candidate_pool(roster, boss, pool=None)`, `_score_batch(decks, boss, pool) -> list[float]`. `pool=None` reproduces today's behavior exactly. Return contract of `search_best_decks` unchanged (summaries still carry `"result"`).
- Consumes: `SimPool.score_many` / `SimPool.summarize_many` (duck-typed — deck_search must NOT import sim_pool).

- [ ] **Step 1: Write the failing test** (in `test_deck_search.py`; import `SimPool` in the test, not in deck_search):

```python
def test_search_best_decks_pool_parity():
    from app.sim_pool import SimPool
    roster, boss = real_five_roster(), short_boss()
    serial = search_best_decks(roster, boss, top_n=3)
    with SimPool(roster, boss, workers=2, spawn_threshold=1) as pool:
        pooled = search_best_decks(roster, boss, top_n=3, pool=pool)
    assert [d["deck"] for d in pooled] == [d["deck"] for d in serial]
    assert [d["total_damage"] for d in pooled] == [d["total_damage"] for d in serial]
    assert all("result" in d for d in pooled)  # return contract kept
```

- [ ] **Step 2: Run to verify failure** — `TypeError: search_best_decks() got an unexpected keyword argument 'pool'`.
- [ ] **Step 3: Implement.** Add the batch helper and rework the two map sites. The permutation refinement is restructured to score slim summaries first and re-simulate only the returned `top_n` to attach `"result"` — identical floats (evaluate_deck is pure), same tie behavior (stable sort over enumeration order):

```python
def _score_batch(decks, boss, pool):
    if pool is None:
        return [evaluate_deck(deck, boss)["total_damage"] for deck in decks]
    return pool.score_many(decks)
```

In `prune_candidate_pool`, replace the per-unit measurement loop (keep `_measure_against` for `_reference_b1_variants`, which stays serial — it's a handful of B1 sims):

```python
    scores = {}
    for reference_b1 in _reference_b1_variants(by_tier, boss):
        reference = _reference_deck(by_tier, reference_b1)
        baseline = evaluate_deck(reference, boss)["total_damage"]
        reference_slugs = {u.slug for u in reference}
        candidates, swapped = [], []
        for unit in roster:
            if unit.slug in reference_slugs:
                scores[unit.slug] = max(scores.get(unit.slug, 0.0), 0.0)
                continue
            slot = {1: 0, 2: 1, 3: 4}[unit.burst_tier]
            deck = list(reference)
            deck[slot] = unit
            candidates.append(unit)
            swapped.append(deck)
        for unit, total in zip(candidates, _score_batch(swapped, boss, pool)):
            scores[unit.slug] = max(scores.get(unit.slug, 0.0), total - baseline)
```

In `search_best_decks` (signature gains `pool=None`; `prune_candidate_pool(roster, boss, pool)`):

```python
    canonical = sorted(
        ((total, i) for i, total in enumerate(_score_batch(combos, boss, pool))),
        key=lambda pair: pair[0], reverse=True,
    )
    orderings = [ordered
                 for _, i in canonical[:permutation_top_k]
                 for ordered in _intra_tier_orderings(combos[i])]
    if pool is None:
        slim = [{"deck": [u.slug for u in o],
                 "total_damage": evaluate_deck(o, boss)["total_damage"]} for o in orderings]
    else:
        slim = pool.summarize_many(orderings)
    ranked = sorted(zip(slim, orderings), key=lambda p: p[0]["total_damage"], reverse=True)
    return [_summarize(ordered, evaluate_deck(ordered, boss)) for _, ordered in ranked[:top_n]]
```

  Note the canonical sort keys ONLY on total (original sorted `(total, i)` tuples reverse, which reverse-sorts the index tiebreak too — key on `pair[0]` with stable sort keeps enumeration order on ties instead; if the existing parity/regression tests object, revert to the exact original tuple sort. `sorted(..., reverse=True)` is stable either way).

- [ ] **Step 4: Run** — new test + the whole `test_deck_search.py` and `test_deck_allocation.py` files pass (allocation exercises `search_best_decks(pool=None)`; any existing test asserting exhaustive/refined ordering must stay green — if one fails on tie order, apply the revert noted above).
- [ ] **Step 5: Commit** — `git commit -m "feat: deck_search accepts a SimPool (canonical scoring, refinement, prune batches)"`

### Task 4: `deck_allocation` wires the pool end-to-end

**Files:**
- Modify: `backend/app/deck_allocation.py` (`allocate_decks`, `_best_ordering_summary`)
- Test: `backend/tests/test_deck_allocation.py` (or wherever `allocate_decks` tests live — follow the existing file)

**Interfaces:**
- Produces: `allocate_decks(roster, boss, num_decks=5, time_budget_sec=45.0, workers=None)`. `_best_ordering_summary(units, boss, pool=None)`.
- Consumes: `SimPool` (imported in deck_allocation — no cycle: sim_pool ← deck_search ← nothing new), `search_best_decks(..., pool=)`, `_score_batch`.

- [ ] **Step 1: Write the failing test**

```python
def test_allocate_decks_workers_parity():
    roster, boss = ...  # the file's existing small fixture roster + short boss
    serial = allocate_decks(roster, boss, num_decks=2, time_budget_sec=0.0)
    pooled = allocate_decks(roster, boss, num_decks=2, time_budget_sec=0.0, workers=2)
    assert [d["deck"] for d in pooled["decks"]] == [d["deck"] for d in serial["decks"]]
    assert pooled["leftover_slugs"] == serial["leftover_slugs"]
```

(`time_budget_sec=0.0` keeps the nondeterministic-duration swap phase out of the parity comparison; the swap phase itself is deterministic given time, but a wall-clock deadline can cut it at different points across runs.)

- [ ] **Step 2: Run to verify failure** — `TypeError: allocate_decks() got an unexpected keyword argument 'workers'`.
- [ ] **Step 3: Implement:**

```python
from app.deck_search import (BossProfile, _intra_tier_orderings, _score_batch,
                             _summarize, evaluate_deck, search_best_decks)
from app.sim_pool import SimPool


def allocate_decks(roster, boss: BossProfile, num_decks=5, time_budget_sec=45.0, workers=None):
    with SimPool(roster, boss, workers=workers) as pool:
        remaining = list(roster)
        decks = []
        by_slug = {u.slug: u for u in roster}
        while len(decks) < num_decks:
            found = search_best_decks(remaining, boss, top_n=1, pool=pool)
            ...  # unchanged
        deadline = time.monotonic() + time_budget_sec
        _swap_pass(decks, remaining, boss, deadline)  # serial: hill-climb state is sequential
        summaries = [_best_ordering_summary(units, boss, pool) for units in decks]
        return {"decks": summaries,
                "leftover_slugs": sorted(u.slug for u in remaining)}
```

`_best_ordering_summary` becomes batch-scored with first-wins tie behavior preserved:

```python
def _best_ordering_summary(units, boss, pool=None):
    orderings = list(_intra_tier_orderings(units))
    totals = _score_batch(orderings, boss, pool)
    best_i = max(range(len(orderings)), key=lambda i: (totals[i], -i))
    return _summarize(orderings[best_i], evaluate_deck(orderings[best_i], boss))
```

- [ ] **Step 4: Run** — new test + full `test_deck_allocation.py` green.
- [ ] **Step 5: Commit** — `git commit -m "feat: allocate_decks fans deck evaluation out to a SimPool (workers param)"`

### Task 5: API passes `workers="auto"`

**Files:**
- Modify: `backend/app/api.py` (both endpoint bodies)
- Test: existing `backend/tests/test_api*.py` must stay green unchanged (their tiny rosters stay under `SPAWN_THRESHOLD`, so no pool ever spawns in tests).

- [ ] **Step 1: Modify `recommend`** — wrap its `search_best_decks` call: `with SimPool(specs, profile, workers="auto") as pool: results = search_best_decks(specs, profile, top_n=request.top_n, pool=pool)` (import `SimPool` at top; match the endpoint's actual local variable names when editing).
- [ ] **Step 2: Modify `recommend_raid`** — add `workers="auto"` to its `allocate_decks(...)` call.
- [ ] **Step 3: Run the API tests** — `PYTHONIOENCODING=utf-8 python -m pytest tests/ -q` → all green, no slowdown (assert by eye: suite stays in single-digit seconds).
- [ ] **Step 4: Commit** — `git commit -m "feat: API deck search/allocation use ProcessPool parallelism (workers=auto)"`

### Task 6: Measure, document, ship

**Files:**
- Modify: `docs/roadmap.md` (Phase 5 section + top summary), `docs/decisions.md` via `/document` if the measurement forces a follow-up decision.

- [ ] **Step 1: Re-run the 42-loadable-unit allocation measurement** (same shape as the 282 s baseline: full loadable roster via `load_roster`, `enemy_def=31784`, `num_decks=5`, default 45 s swap budget, `workers="auto"`), wall-clock it, record decks/leftovers/combined total to compare against the baseline (3 decks / 5.18 B — B1 scarcity since fixed, so expect 5 decks and a different total; the comparable number is wall-clock).
- [ ] **Step 2: Update `docs/roadmap.md`** — record the measured time and whether the budget is met; if still over, note the remaining lever (swap-phase batching) as the follow-up.
- [ ] **Step 3: Full suite + commit docs** — `PYTHONIOENCODING=utf-8 python -m pytest tests/ -q` green, then `git commit -m "docs: ProcessPool parallelism measurement"`.
