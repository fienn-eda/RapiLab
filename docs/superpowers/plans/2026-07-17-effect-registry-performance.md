# EffectRegistry Performance Pass (Stage 0) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `EffectRegistry.total_for` O(log n) per query via a per-key piecewise-constant segment table, dropping a 180 s raid sim from ~2.4 s to tens of ms with **bit-identical** outputs.

**Architecture:** `total_for` answers are step functions of time per `(stat, target slug, target element)` key. A lazily built, version-invalidated cache stores each key's segment boundaries + per-segment totals (summed in insertion order for bit-exactness); queries become one `bisect_right`. Spec: `docs/superpowers/specs/2026-07-17-effect-registry-performance-design.md`.

**Tech Stack:** Python 3 stdlib only (`bisect`). No new dependencies.

## Global Constraints

- Run tests from `backend/`: `PYTHONIOENCODING=utf-8 python3 -m pytest tests/ -q` — the interpreter is **`python3`, NOT `python`** on this machine.
- Baseline suite: **654 passed**. No existing test may be edited; outputs must be bit-identical (never relax an exact-equality assert to approx).
- `EffectRegistry`'s public API (`add`, `add_refreshing`, `truncate_open_ended`, `total_for`, `drain_pulses`, `add_round_grant`, `round_grants`) keeps its exact signatures and semantics.
- Only these files change: `backend/app/effects.py`, new `backend/tests/test_effects_parity.py`, new `scripts/bench_evaluate_deck.py`, `docs/roadmap.md`.
- **No git remote exists**: commit only; never push or open PRs.
- If working in a fresh worktree, `data/` (gitignored) is absent — copy it first: `Copy-Item -Recurse C:\Users\fienn\Desktop\NikkeDeckBuilder\data <worktree-root>\data` (PowerShell). The full suite needs it.
- Audit already done (2026-07-17): `_entries` / `Effect.duration` / `Effect.value` are mutated **nowhere** outside `effects.py`'s own methods, so bumping a version counter inside the mutating methods invalidates correctly.

---

### Task 1: Parity net (before touching the implementation)

**Files:**
- Create: `backend/tests/test_effects_parity.py`

**Interfaces:**
- Consumes: `app.effects.Effect`, `EffectRegistry`, `_matches_scope` (existing).
- Produces: the permanent parity tests Task 2 must keep green. Nothing else imports this file.

Note on TDD shape: this is a pure refactor, so the net passes **before and during** the rewrite; its job is to fail the moment Task 2's cache diverges from the frozen naive loop (especially after in-place mutations). That replaces the usual red step.

- [x] **Step 1: Write the parity test file**

```python
"""Parity net for the EffectRegistry segment-table rewrite (perf design spec,
2026-07-17): a FROZEN copy of the pre-rewrite naive total_for loop is compared
against registry.total_for for exact (bit-identical) equality - every scope
kind, refreshing truncation, open-ended closing, zero-length windows, and
queries interleaved with mutations (cache-invalidation coverage). The suite's
hundreds of exact numeric asserts are the end-to-end net; this file is the
targeted, adversarial one. Do not "modernize" naive_total_for - its point is
to stay identical to the old loop, insertion order and all."""
from app.effects import Effect, EffectRegistry, _matches_scope

A = {"slug": "a", "element": "Fire"}
B = {"slug": "b", "element": "Water"}


def naive_total_for(registry, stat, target, now):
    total = 0.0
    for effect, applied_at in registry._entries:
        if effect.stat != stat:
            continue
        if effect.duration is None:
            active = now >= applied_at
        else:
            active = applied_at <= now < applied_at + effect.duration
        if not active:
            continue
        if effect.scope == "self":
            if effect.source_slug == target["slug"]:
                total += effect.value
        elif _matches_scope(effect.scope, target):
            total += effect.value
    return total


def build_adversarial_registry():
    reg = EffectRegistry()
    reg.add(Effect("atk_percent", 0.1, "squad", None, "a"), applied_at=0.0)
    reg.add(Effect("atk_percent", 0.07, "self", 10.0, "a"), applied_at=1.0)
    reg.add(Effect("atk_percent", 0.03, "element:Water", 5.0, "b"), applied_at=2.0)
    reg.add(Effect("atk_percent", 0.11, "slugs:a,b", 4.0, "b"), applied_at=2.5)
    reg.add(Effect("crit_rate", 0.05, "squad", 3.0, "a"), applied_at=0.5)
    # Refreshing re-applications from one source truncate the previous window;
    # the same-timestamp one produces a zero-length window.
    for t in (3.0, 4.0, 5.0, 5.0):
        reg.add_refreshing(Effect("flat_atk", 100.0, "squad", 3.0, "a"), applied_at=t)
    # A different source must stay independent of the refresh chain above.
    reg.add_refreshing(Effect("flat_atk", 50.0, "squad", 2.0, "b"), applied_at=4.5)
    # Close the open-ended atk_percent from source "a" at t=8.
    reg.truncate_open_ended("atk_percent", "a", now=8.0)
    return reg


def probe_times(reg):
    boundaries = set()
    for effect, applied_at in reg._entries:
        boundaries.add(applied_at)
        if effect.duration is not None:
            boundaries.add(applied_at + effect.duration)
    probes = set()
    for b in boundaries:
        probes.update((b - 0.25, b, b + 0.25))
    probes.update(x * 0.5 for x in range(41))  # dense 0..20 grid
    return sorted(probes)


def assert_parity(reg):
    for stat in ("atk_percent", "crit_rate", "flat_atk", "never_granted"):
        for target in (A, B):
            for now in probe_times(reg):
                expected = naive_total_for(reg, stat, target, now)
                got = reg.total_for(stat, target, now)
                assert got == expected, (stat, target["slug"], now, got, expected)


def test_parity_on_adversarial_registry():
    assert_parity(build_adversarial_registry())


def test_parity_survives_mutations_after_queries():
    # assert_parity warms any cache; each later mutation - including in-place
    # duration truncations that never go through add() - must invalidate it.
    reg = build_adversarial_registry()
    assert_parity(reg)
    reg.add(Effect("atk_percent", 0.2, "squad", 6.0, "b"), applied_at=9.0)
    assert_parity(reg)
    reg.add_refreshing(Effect("flat_atk", 100.0, "squad", 3.0, "a"), applied_at=6.0)
    assert_parity(reg)
    reg.add(Effect("crit_rate", 0.02, "self", None, "b"), applied_at=1.0)
    reg.truncate_open_ended("crit_rate", "b", now=12.0)
    assert_parity(reg)
```

- [x] **Step 2: Run the new tests — they pass against the current naive implementation**

Run (from `backend/`): `PYTHONIOENCODING=utf-8 python3 -m pytest tests/test_effects_parity.py -q`
Expected: `2 passed`

- [x] **Step 3: Run the full suite to confirm the baseline**

Run: `PYTHONIOENCODING=utf-8 python3 -m pytest tests/ -q`
Expected: `656 passed` (654 baseline + these 2)

- [x] **Step 4: Commit**

```bash
git add backend/tests/test_effects_parity.py
git commit -m "test: parity net for the EffectRegistry segment-table rewrite"
```

---

### Task 2: Segment-table cache in EffectRegistry

**Files:**
- Modify: `backend/app/effects.py` (class `EffectRegistry`, lines ~105-181)
- Test: `backend/tests/test_effects_parity.py` (Task 1, unchanged), full suite

**Interfaces:**
- Consumes: existing `Effect` dataclass, `_matches_scope`.
- Produces: `total_for(stat: str, target: dict, now: float) -> float` — same signature, now O(log n); internal `_version: int`, `_segment_tables: dict`. No caller changes anywhere.

- [x] **Step 1: Add the import**

At the top of `backend/app/effects.py` (stdlib import before the dataclasses import):

```python
from bisect import bisect_right
```

- [x] **Step 2: Add cache state to `__init__` and bump the version in every mutating method**

Replace `EffectRegistry.__init__`, `add`, `add_refreshing`, `truncate_open_ended` bodies as follows (docstrings of `add_refreshing`/`truncate_open_ended` stay exactly as they are — omitted here for brevity, do not delete them):

```python
    def __init__(self):
        self._entries: list[tuple[Effect, float]] = []
        self._pulses: list[Pulse] = []
        self._round_grants: list[RoundGrant] = []
        # total_for is served from per-(stat, slug, element) segment tables;
        # every mutation bumps _version so stale tables rebuild on next query.
        # Mutations happen ONLY through the methods below (audited 2026-07-17).
        self._version = 0
        self._segment_tables: dict[tuple, tuple[int, list, list]] = {}

    def add(self, effect: Effect, applied_at: float) -> None:
        self._entries.append((effect, applied_at))
        self._version += 1
```

In `add_refreshing`, add one line at the end (after the existing append):

```python
        self._entries.append((effect, applied_at))
        self._version += 1
```

In `truncate_open_ended`, add one line at the end of the method (after the loop):

```python
        self._version += 1
```

- [x] **Step 3: Replace `total_for` with the cached lookup + builder**

Replace the current `total_for` (keep `_is_active` — `add_refreshing` still uses it):

```python
    def total_for(self, stat: str, target: dict, now: float) -> float:
        # .get for element: the old loop only read target["element"] when an
        # element:-scoped effect was actually present, so the cache key must
        # not introduce a new KeyError for element-less targets.
        key = (stat, target["slug"], target.get("element"))
        cached = self._segment_tables.get(key)
        if cached is None or cached[0] != self._version:
            cached = self._build_segment_table(stat, target)
            self._segment_tables[key] = cached
        _, boundaries, totals = cached
        return totals[bisect_right(boundaries, now)]

    def _build_segment_table(self, stat: str, target: dict):
        """Piecewise-constant totals for one (stat, target) query key: between
        consecutive interval boundaries the active set is constant, so each
        segment's total is precomputed and a query is one bisect. Each segment
        is summed over entries in insertion order - the exact additions the
        old linear scan performed for any time inside that segment - so
        results are bit-identical to it, not approximately equal."""
        intervals = []
        for effect, applied_at in self._entries:
            if effect.stat != stat:
                continue
            if effect.scope == "self":
                if effect.source_slug != target["slug"]:
                    continue
            elif not _matches_scope(effect.scope, target):
                continue
            end = None if effect.duration is None else applied_at + effect.duration
            intervals.append((applied_at, end, effect.value))
        boundary_set = set()
        for start, end, _ in intervals:
            boundary_set.add(start)
            if end is not None:
                boundary_set.add(end)
        boundaries = sorted(boundary_set)
        totals = [0.0]  # the earliest boundary is the earliest start, so
        for b in boundaries:  # queries before it see no active effect
            total = 0.0
            for start, end, value in intervals:
                if start <= b and (end is None or b < end):
                    total += value
            totals.append(total)
        return (self._version, boundaries, totals)
```

Semantics note (why this matches `_is_active` exactly): a query at `now` lands
in the segment starting at `boundaries[i]` where `boundaries[i] <= now <
boundaries[i+1]` (`bisect_right` → index `i+1` → `totals[i+1]`, which was
evaluated at representative point `b = boundaries[i]`). An interval is active
on that whole segment iff `start <= b and (end is None or b < end)` — the same
half-open `[applied_at, applied_at + duration)` rule, including zero-length
(`start == end` → never active) and truncated-negative windows.

- [x] **Step 4: Run the parity tests**

Run: `PYTHONIOENCODING=utf-8 python3 -m pytest tests/test_effects_parity.py -q`
Expected: `2 passed` (if `test_parity_survives_mutations_after_queries` fails, a mutating method is missing its `_version` bump)

- [x] **Step 5: Run the full suite**

Run: `PYTHONIOENCODING=utf-8 python3 -m pytest tests/ -q`
Expected: `656 passed` — zero failures; any failure means an output diverged and must be fixed in `effects.py`, never in the failing test.

- [x] **Step 6: Commit**

```bash
git add backend/app/effects.py
git commit -m "perf: serve EffectRegistry.total_for from version-invalidated segment tables"
```

---

### Task 3: Benchmark script + measurement

**Files:**
- Create: `scripts/bench_evaluate_deck.py`

**Interfaces:**
- Consumes: `app.models.UserNikkeState`, `app.user_roster.load_roster`, `app.deck_search.BossProfile/evaluate_deck/feasible_orderings` (all existing).
- Produces: a repeatable CLI benchmark; its measured ms/sim number goes into the completion notes and `docs/roadmap.md` (Task 4).

- [x] **Step 1: Write the script**

```python
"""Benchmark one evaluate_deck call (a full 180 s raid simulation).

Why: deck-search cost = (number of sims) x (per-sim cost). This measures the
second factor so search-budget constants (candidate-pool size M, permutation
top-K, allocation swap budget) can be tuned against real numbers instead of
guesses. Run after any engine perf change and record the result in
docs/roadmap.md. Baseline before the segment-table rewrite (2026-07-17):
~2410 ms/sim, 93% of it in EffectRegistry.total_for linear scans.

Usage (any cwd):
    python3 scripts/bench_evaluate_deck.py [-n CALLS]
"""
import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

from app.models import UserNikkeState  # noqa: E402
from app.user_roster import load_roster  # noqa: E402
from app.deck_search import BossProfile, evaluate_deck, feasible_orderings  # noqa: E402

# Loadable tier-1/2/3 mix with heavy per-shot activity (MG attackers).
SLUGS = ["little-mermaid", "arcana", "grave", "drake", "modernia"]


def _nikke(slug):
    return UserNikkeState.model_validate({
        "character_slug": slug, "level": 200, "core_level": 0,
        "hp": 1_000_000.0, "atk": 60_000.0, "def_": 3_000.0,
        "skill_levels": {"skill1": 10, "skill2": 10, "burst": 10},
    })


def main():
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("-n", type=int, default=50, help="timed calls (default 50)")
    args = parser.parse_args()

    specs, excluded = load_roster([_nikke(s) for s in SLUGS])
    if excluded:
        sys.exit(f"ERROR: benchmark roster units failed to load: {excluded}")
    orderings = list(feasible_orderings(specs))
    boss = BossProfile(element="Water", fight_duration=180.0)

    evaluate_deck(orderings[0], boss)  # warmup
    t0 = time.perf_counter()
    for i in range(args.n):
        evaluate_deck(orderings[i % len(orderings)], boss)
    per_call_ms = (time.perf_counter() - t0) / args.n * 1000

    print(f"deck: {[s.slug for s in orderings[0]]}")
    print(f"avg evaluate_deck over {args.n} calls: {per_call_ms:.2f} ms")
    for budget_s in (10, 60):
        print(f"  -> sims per {budget_s}s budget: {int(budget_s * 1000 / per_call_ms):,}")


if __name__ == "__main__":
    main()
```

- [x] **Step 2: Run it and record the number**

Run (from the repo/worktree root): `python3 scripts/bench_evaluate_deck.py`
Expected: `avg evaluate_deck ... ms` at or under **50 ms** (spec target, ~50×; baseline 2410 ms). Copy the actual line into the completion notes at the bottom of this plan. If it misses 50 ms, do NOT add machinery — profile again (`cProfile`, sort by cumulative) and report where the remaining time goes; the spec makes further work a measured decision.

- [x] **Step 3: Commit**

```bash
git add scripts/bench_evaluate_deck.py
git commit -m "feat: repeatable evaluate_deck benchmark script"
```

---

### Task 4: Docs

**Files:**
- Modify: `docs/roadmap.md` (the summary block at the top, lines ~10-20)
- Modify: this plan file (completion notes)

- [x] **Step 1: Update the roadmap summary**

In the top summary block of `docs/roadmap.md`, update the test line to the new count and prepend a line to the summary (keeping the existing entries as "이전:"):

```markdown
- 테스트: **656 passed** (2026-07-17, **Stage 0 EffectRegistry 성능 패스** —
  total_for를 버전-무효화 세그먼트 테이블로 교체(비트 동일 출력, 패리티 넷 2건
  추가). evaluate_deck 180초 시뮬 ~2410ms → <실측값>ms. was 654)
```

Replace `<실측값>` with the measured number from Task 3.

- [x] **Step 2: Append completion notes to this plan**

At the bottom of this file add:

```markdown
## Completion notes

- Measured: evaluate_deck <실측값> ms/sim (was 2410 ms baseline), <date>.
- Suite: 656 passed.
```

- [x] **Step 3: Commit**

```bash
git add docs/roadmap.md docs/superpowers/plans/2026-07-17-effect-registry-performance.md
git commit -m "docs: record Stage 0 perf-pass results"
```

---

## Completion notes

- Measured: evaluate_deck 133.66 ms/sim (was 2410 ms baseline; spec target <=50 ms missed — residual is flat Python call overhead, no single hotspot; further optimization decision pending with Fienn), 2026-07-17.
- Suite: 656 passed.
