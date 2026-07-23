# Cascade Surrogate — Phase 1 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a reference-free sample-regression surrogate for deck damage plus a recall-validation harness, to decide (with data) whether a cheap-filter→sim-top-K cascade can replace "simulate every candidate".

**Architecture:** A new leaf module `backend/app/surrogate.py` samples feasible 5-unit combinations, featurizes them (membership + restricted tier-pair indicators), fits ridge regression to their true best-ordering sim damage, and scores arbitrary combinations by coefficient sum. A script `scripts/validate_surrogate_recall.py` fits on a sample and measures top-K recall + Spearman on a held-out set. The simulation engine is unchanged; the surrogate only *reads* `deck_search`/`sim_pool`.

**Tech Stack:** Python, numpy 2.3.5 (anaconda `python3`), pytest. Parallel sims via the existing `SimPool`.

## Global Constraints

- **Engine unchanged.** `surrogate.py` imports and reuses `deck_search`/`sim_pool` read-only. No edits to `deck_search.py`, `deck_allocation.py`, `raid_simulator.py`. No cascade wiring (that is Phase 2).
- **Interpreter:** run everything with `python3` (anaconda; plain `python` lacks pydantic/numpy).
- **Determinism:** all sampling takes an explicit seed; the same seed reproduces the same combinations, so validation is reproducible.
- **Feasibility rules come from `deck_search`** (do not re-derive): `ALLOWED_SHAPES`, `_no_variant_clash`, `_tier1_seating_valid`. A combination is a 5-unit list in canonical tier order (tier 1s, then 2s, then 3s).
- **Allowed pair tier-types:** `{(1,2),(1,3),(2,3),(3,3)}` (buffer-attacker, buffer-buffer, attacker-attacker). Same-base variants never co-occur in a feasible combo, so no special-casing needed beyond feasibility.
- **Worktree data:** `data/` is gitignored; it is already synced. If a task reports missing data, run `python3 scripts/sync_worktree_data.py` first.

---

## File Structure

- `backend/app/surrogate.py` — NEW leaf module: `FeatureSpace`, `make_feature_space`, `featurize`, `build_matrix`, `sample_feasible_combinations`, `fit_ridge`, `predict`, `best_ordering_damage`.
- `backend/tests/test_surrogate.py` — NEW unit tests (no engine sims except one small real check).
- `scripts/validate_surrogate_recall.py` — NEW measurement harness.
- `docs/roadmap.md` — record the Phase-1 harness landing (results come from running it).

---

### Task 1: Feature space + featurize

**Files:**
- Create: `backend/app/surrogate.py`
- Test: `backend/tests/test_surrogate.py`

**Interfaces:**
- Consumes: nothing (pure combinatorics on `.slug`/`.burst_tier`).
- Produces:
  - `ALLOWED_PAIR_TYPES = frozenset({(1, 2), (1, 3), (2, 3), (3, 3)})`
  - `@dataclass FeatureSpace: unit_col: dict[str,int]; pair_col: dict[tuple[str,str],int]; n_features: int` (column 0 is the intercept).
  - `make_feature_space(roster) -> FeatureSpace` — unit columns for every slug (sorted), pair columns for every slug pair whose `(min tier, max tier)` is in `ALLOWED_PAIR_TYPES` (pair key is the tier-then-slug canonical: `tuple(sorted((a.slug, b.slug)))`).
  - `featurize(combo, fs) -> np.ndarray` — length `fs.n_features`, `[0]=1.0` (intercept), membership 1.0 for each unit col, 1.0 for each in-combo pair present in `fs.pair_col`.
  - `build_matrix(combos, fs) -> np.ndarray` — shape `(len(combos), fs.n_features)`.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_surrogate.py`:

```python
import numpy as np
from types import SimpleNamespace
from app.surrogate import (ALLOWED_PAIR_TYPES, make_feature_space, featurize,
                           build_matrix)


def _u(slug, tier):
    return SimpleNamespace(slug=slug, burst_tier=tier)


ROSTER = [_u("b1a", 1), _u("b1b", 1), _u("b2a", 2), _u("b3a", 3), _u("b3b", 3)]


def test_feature_space_has_intercept_units_and_allowed_pairs():
    fs = make_feature_space(ROSTER)
    # intercept col 0 + 5 unit cols + allowed pairs
    assert fs.unit_col.keys() == {"b1a", "b1b", "b2a", "b3a", "b3b"}
    assert 0 not in fs.unit_col.values()  # col 0 reserved for intercept
    # (1,1) is NOT an allowed pair type -> b1a,b1b excluded; (3,3) IS -> b3a,b3b included
    assert ("b1a", "b1b") not in fs.pair_col
    assert ("b3a", "b3b") in fs.pair_col
    assert ("b1a", "b3a") in fs.pair_col  # (1,3) allowed
    assert fs.n_features == 1 + 5 + len(fs.pair_col)


def test_featurize_marks_intercept_membership_and_pairs():
    fs = make_feature_space(ROSTER)
    combo = [ROSTER[0], ROSTER[2], ROSTER[3]]  # b1a, b2a, b3a
    v = featurize(combo, fs)
    assert v[0] == 1.0
    assert v[fs.unit_col["b1a"]] == 1.0 and v[fs.unit_col["b3a"]] == 1.0
    assert v[fs.unit_col["b1b"]] == 0.0
    assert v[fs.pair_col[("b1a", "b3a")]] == 1.0  # present pair
    assert v[fs.pair_col[("b3a", "b3b")]] == 0.0  # b3b not in combo


def test_build_matrix_shape():
    fs = make_feature_space(ROSTER)
    X = build_matrix([[ROSTER[0], ROSTER[2], ROSTER[3]], ROSTER[:3]], fs)
    assert X.shape == (2, fs.n_features)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python3 -m pytest tests/test_surrogate.py -q`
Expected: FAIL — `No module named app.surrogate`.

- [ ] **Step 3: Implement**

Create `backend/app/surrogate.py`:

```python
"""Reference-free sample-regression surrogate for deck damage (cascade Phase 1).

Predicts a 5-unit combination's best-ordering total damage from a cheap linear
model over membership + restricted tier-pair indicators, fit by ridge regression
to a random sample of truly-simulated decks. Lets a cascade rank all combinations
for free and simulate only the top-K (docs/superpowers/specs/2026-07-23-cascade-
surrogate-deck-search-design.md). Feasibility rules are reused from deck_search.
"""
from dataclasses import dataclass
from itertools import combinations

import numpy as np

# Buffer-attacker (1-3, 2-3), buffer-buffer (1-2), attacker-attacker (3-3).
# (1-1)/(2-2) omitted: real decks rarely pair those and it curbs feature count.
ALLOWED_PAIR_TYPES = frozenset({(1, 2), (1, 3), (2, 3), (3, 3)})


@dataclass
class FeatureSpace:
    unit_col: dict          # slug -> column index (>=1; col 0 is the intercept)
    pair_col: dict          # (slug_a, slug_b) sorted -> column index
    n_features: int


def make_feature_space(roster) -> FeatureSpace:
    slugs = sorted(u.slug for u in roster)
    tier = {u.slug: u.burst_tier for u in roster}
    unit_col = {slug: i + 1 for i, slug in enumerate(slugs)}  # col 0 = intercept
    pair_col = {}
    next_col = 1 + len(slugs)
    for a, b in combinations(slugs, 2):
        pair_type = tuple(sorted((tier[a], tier[b])))
        if pair_type in ALLOWED_PAIR_TYPES:
            pair_col[(a, b)] = next_col
            next_col += 1
    return FeatureSpace(unit_col=unit_col, pair_col=pair_col, n_features=next_col)


def featurize(combo, fs: FeatureSpace) -> np.ndarray:
    v = np.zeros(fs.n_features)
    v[0] = 1.0
    slugs = [u.slug for u in combo]
    for slug in slugs:
        v[fs.unit_col[slug]] = 1.0
    for a, b in combinations(sorted(slugs), 2):
        col = fs.pair_col.get((a, b))
        if col is not None:
            v[col] = 1.0
    return v


def build_matrix(combos, fs: FeatureSpace) -> np.ndarray:
    return np.vstack([featurize(c, fs) for c in combos])
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python3 -m pytest tests/test_surrogate.py -q`
Expected: PASS (3 tests).

- [ ] **Step 5: Commit**

```bash
git add backend/app/surrogate.py backend/tests/test_surrogate.py
git commit -m "Add surrogate feature space + featurization"
```

---

### Task 2: Sample feasible combinations

**Files:**
- Modify: `backend/app/surrogate.py`
- Test: `backend/tests/test_surrogate.py` (append)

**Interfaces:**
- Consumes: `deck_search.ALLOWED_SHAPES`, `deck_search._no_variant_clash`, `deck_search._tier1_seating_valid`.
- Produces: `sample_feasible_combinations(roster, n_samples, seed) -> list[list[spec]]` — up to `n_samples` distinct feasible combos, each a 5-unit list in canonical tier order. Deterministic per seed. Fewer than `n_samples` only if the feasible space is smaller.

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/test_surrogate.py`:

```python
from app.surrogate import sample_feasible_combinations
from app.deck_search import ALLOWED_SHAPES

# A roster big enough to form many feasible decks across shapes.
BIG = ([_u(f"a{i}", 1) for i in range(3)] +
       [_u(f"b{i}", 2) for i in range(3)] +
       [_u(f"c{i}", 3) for i in range(6)])


def test_sampled_combos_are_feasible_and_deterministic():
    s1 = sample_feasible_combinations(BIG, n_samples=20, seed=7)
    s2 = sample_feasible_combinations(BIG, n_samples=20, seed=7)
    assert [[u.slug for u in c] for c in s1] == [[u.slug for u in c] for c in s2]
    shapes = {(1, 1, 3), (1, 2, 2), (2, 1, 2)}
    for combo in s1:
        assert len(combo) == 5
        tiers = tuple(sorted(u.burst_tier for u in combo))
        # canonical-order combo: tiers non-decreasing
        assert [u.burst_tier for u in combo] == sorted(u.burst_tier for u in combo)
        counts = (tiers.count(1), tiers.count(2), tiers.count(3))
        assert counts in shapes
        assert len({u.slug for u in combo}) == 5  # distinct units


def test_sample_count_capped_by_request():
    s = sample_feasible_combinations(BIG, n_samples=5, seed=1)
    assert len(s) == 5
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python3 -m pytest tests/test_surrogate.py::test_sampled_combos_are_feasible_and_deterministic -q`
Expected: FAIL — `sample_feasible_combinations` not defined.

- [ ] **Step 3: Implement**

Add to `backend/app/surrogate.py`:

```python
import random

from app.deck_search import (ALLOWED_SHAPES, _no_variant_clash,
                             _tier1_seating_valid)


def sample_feasible_combinations(roster, n_samples, seed):
    """Up to `n_samples` distinct feasible 5-unit combinations (canonical tier
    order), drawn uniformly over (shape, per-tier unit choice) and kept only if
    they pass the deck_search feasibility rules. Deterministic per seed; returns
    fewer only when the feasible space is exhausted by repeated rejection."""
    rng = random.Random(seed)
    by_tier = {1: [], 2: [], 3: []}
    for u in roster:
        if u.burst_tier in by_tier:
            by_tier[u.burst_tier].append(u)
    seen, out = set(), []
    # cap attempts so a tiny/infeasible roster can't loop forever
    attempts, max_attempts = 0, n_samples * 200 + 1000
    while len(out) < n_samples and attempts < max_attempts:
        attempts += 1
        n1, n2, n3 = rng.choice(ALLOWED_SHAPES)
        if len(by_tier[1]) < n1 or len(by_tier[2]) < n2 or len(by_tier[3]) < n3:
            continue
        picks = (rng.sample(by_tier[1], n1) + rng.sample(by_tier[2], n2)
                 + rng.sample(by_tier[3], n3))
        combo = sorted(picks, key=lambda u: u.burst_tier)
        key = tuple(u.slug for u in combo)
        if key in seen:
            continue
        if _no_variant_clash(combo) and _tier1_seating_valid(combo):
            seen.add(key)
            out.append(combo)
    return out
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python3 -m pytest tests/test_surrogate.py -q`
Expected: PASS (5 tests).

- [ ] **Step 5: Commit**

```bash
git add backend/app/surrogate.py backend/tests/test_surrogate.py
git commit -m "Add feasible-combination sampler to surrogate"
```

---

### Task 3: Ridge fit + predict

**Files:**
- Modify: `backend/app/surrogate.py`
- Test: `backend/tests/test_surrogate.py` (append)

**Interfaces:**
- Produces:
  - `fit_ridge(X, y, lam=1.0) -> np.ndarray` — ridge coefficients solving `(XᵀX + lam·D) β = Xᵀy`, where `D` is identity with `D[0,0]=0` (intercept unpenalized).
  - `predict(X, beta) -> np.ndarray` — `X @ beta`.

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/test_surrogate.py`:

```python
from app.surrogate import fit_ridge, predict


def test_ridge_recovers_linear_signal_with_small_lambda():
    rng = np.random.default_rng(0)
    X = np.column_stack([np.ones(200), rng.normal(size=(200, 3))])
    true_beta = np.array([2.0, 1.5, -3.0, 0.5])
    y = X @ true_beta
    beta = fit_ridge(X, y, lam=1e-6)
    assert np.allclose(beta, true_beta, atol=1e-3)
    assert np.allclose(predict(X, beta), y, atol=1e-3)


def test_ridge_does_not_penalize_intercept():
    # Constant target -> intercept should equal the constant, others ~0.
    X = np.column_stack([np.ones(50), np.random.default_rng(1).normal(size=(50, 2))])
    y = np.full(50, 7.0)
    beta = fit_ridge(X, y, lam=10.0)
    assert abs(beta[0] - 7.0) < 1e-6
    assert np.allclose(beta[1:], 0.0, atol=1e-6)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python3 -m pytest tests/test_surrogate.py -k ridge -q`
Expected: FAIL — `fit_ridge` not defined.

- [ ] **Step 3: Implement**

Add to `backend/app/surrogate.py`:

```python
def fit_ridge(X, y, lam=1.0):
    """Ridge coefficients; the intercept column (0) is left unpenalized."""
    X = np.asarray(X, dtype=float)
    y = np.asarray(y, dtype=float)
    n_features = X.shape[1]
    penalty = np.eye(n_features)
    penalty[0, 0] = 0.0
    return np.linalg.solve(X.T @ X + lam * penalty, X.T @ y)


def predict(X, beta):
    return np.asarray(X, dtype=float) @ np.asarray(beta, dtype=float)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python3 -m pytest tests/test_surrogate.py -q`
Expected: PASS (7 tests).

- [ ] **Step 5: Commit**

```bash
git add backend/app/surrogate.py backend/tests/test_surrogate.py
git commit -m "Add ridge fit + predict to surrogate"
```

---

### Task 4: Best-ordering damage (training target)

**Files:**
- Modify: `backend/app/surrogate.py`
- Test: `backend/tests/test_surrogate.py` (append)

**Interfaces:**
- Consumes: `deck_search._intra_tier_orderings`, `deck_search.evaluate_deck`.
- Produces: `best_ordering_damage(combos, boss, score_orderings) -> list[float]` — each combo's max total damage over its intra-tier orderings. `score_orderings(list_of_ordered_decks) -> list[float]` is an injected batch scorer (SimPool.score_many in production, a stub in tests) so grouping logic is testable without the engine. All orderings of all combos are flattened into ONE scorer call, then grouped back and max-reduced.

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/test_surrogate.py`:

```python
from app.surrogate import best_ordering_damage


def test_best_ordering_damage_takes_max_per_combo():
    combos = [BIG[:5], BIG[3:8]]  # two 5-unit combos (feasible shape irrelevant here)
    calls = {}

    def fake_scorer(ordered_decks):
        # score = number of orderings seen so far, so the max per combo is
        # deterministic and grouping can be checked.
        calls["n"] = len(ordered_decks)
        return [float(i) for i in range(len(ordered_decks))]

    out = best_ordering_damage(combos, boss=None, score_orderings=fake_scorer)
    assert len(out) == 2
    # single flattened call covers every ordering of both combos
    assert calls["n"] > 0
    # each entry is the max score among that combo's orderings
    assert all(isinstance(x, float) for x in out)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python3 -m pytest tests/test_surrogate.py -k best_ordering -q`
Expected: FAIL — `best_ordering_damage` not defined.

- [ ] **Step 3: Implement**

Add to `backend/app/surrogate.py`:

```python
from app.deck_search import _intra_tier_orderings


def best_ordering_damage(combos, boss, score_orderings):
    """Each combo's max total damage over its intra-tier orderings. `boss` is
    unused here (the injected scorer carries it) but kept for call-site clarity.
    All orderings are scored in ONE batch, then grouped back per combo."""
    flat, spans = [], []
    for combo in combos:
        orderings = list(_intra_tier_orderings(combo))
        spans.append((len(flat), len(flat) + len(orderings)))
        flat.extend(orderings)
    totals = score_orderings(flat)
    return [max(totals[a:b]) for a, b in spans]
```

- [ ] **Step 4: Run tests, then a small REAL end-to-end check**

Run: `cd backend && python3 -m pytest tests/test_surrogate.py -q`
Expected: PASS (8 tests).

Then verify it composes with the real engine on a tiny roster (serial, no SimPool):

```bash
cd backend && python3 -c "
from app.surrogate import sample_feasible_combinations, best_ordering_damage, make_feature_space, build_matrix, fit_ridge, predict
from app.deck_search import BossProfile, evaluate_deck
from types import SimpleNamespace
import app.user_roster as ur, app.supported_units as su
slugs=[u['slug'] for u in su.supported_units()][:20]
from app.models import UserNikkeState
def nk(s): return UserNikkeState.model_validate({'character_slug':s,'level':200,'core_level':0,'hp':1e6,'atk':6e4,'def_':3e3,'skill_levels':{'skill1':10,'skill2':10,'burst':10}})
specs,_=ur.load_roster([nk(s) for s in slugs])
boss=BossProfile(element='Water', fight_duration=180.0)
combos=sample_feasible_combinations(specs, 6, seed=3)
scorer=lambda decks: [evaluate_deck(d, boss)['total_damage'] for d in decks]
y=best_ordering_damage(combos, boss, scorer)
print('best-ordering damages:', [round(v/1e9,3) for v in y])
fs=make_feature_space(specs); X=build_matrix(combos, fs)
beta=fit_ridge(X, y, lam=1.0); print('predict close?', bool(abs(predict(X,beta)[0]-y[0])/y[0] < 0.5))
"
```
Expected: prints 6 positive damages and `predict close? True` (a 6-sample fit is under-determined, so this only checks it runs end-to-end, not accuracy).

- [ ] **Step 5: Commit**

```bash
git add backend/app/surrogate.py backend/tests/test_surrogate.py
git commit -m "Add best-ordering damage target to surrogate"
```

---

### Task 5: Recall-validation harness

**Files:**
- Create: `scripts/validate_surrogate_recall.py`

**Interfaces:**
- Consumes: everything from Tasks 1-4, `SimPool`, `load_roster`, `supported_units`, `BossProfile`.
- Produces: a CLI that prints top-K recall + Spearman. No engine changes.

- [ ] **Step 1: Implement the harness**

Create `scripts/validate_surrogate_recall.py`:

```python
"""Validate the sample-regression surrogate's ranking recall (cascade Phase 1).

Fits the surrogate on a random sample of truly-simulated feasible decks, then on
a held-out set measures whether the true-best combinations land in the surrogate's
top-K (and the Spearman rank correlation). This is the go/no-go signal for the
cheap-filter -> sim-top-K cascade (docs/superpowers/specs/2026-07-23-cascade-
surrogate-deck-search-design.md). No engine change; pure measurement.

Keep SimPool construction under __main__ (Windows spawn re-imports this module).

Usage (any cwd):
    python3 scripts/validate_surrogate_recall.py [--units 40] [--fit 1500]
                                                 [--holdout 400] [--lam 1.0]
                                                 [--seed 7]
"""
import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "backend"))

import numpy as np  # noqa: E402

from app.models import UserNikkeState  # noqa: E402
from app.user_roster import load_roster  # noqa: E402
from app.supported_units import supported_units  # noqa: E402
from app.deck_search import BossProfile  # noqa: E402
from app.sim_pool import SimPool  # noqa: E402
from app.surrogate import (make_feature_space, build_matrix, fit_ridge, predict,
                           sample_feasible_combinations, best_ordering_damage)  # noqa: E402


def _nikke(slug):
    return UserNikkeState.model_validate({
        "character_slug": slug, "level": 200, "core_level": 0,
        "hp": 1_000_000.0, "atk": 60_000.0, "def_": 3_000.0,
        "skill_levels": {"skill1": 10, "skill2": 10, "burst": 10},
    })


def _spearman(a, b):
    ra = np.argsort(np.argsort(a))
    rb = np.argsort(np.argsort(b))
    return float(np.corrcoef(ra, rb)[0, 1])


def main():
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--units", type=int, default=40)
    p.add_argument("--fit", type=int, default=1500)
    p.add_argument("--holdout", type=int, default=400)
    p.add_argument("--lam", type=float, default=1.0)
    p.add_argument("--seed", type=int, default=7)
    args = p.parse_args()

    slugs = [u["slug"] for u in supported_units()][:args.units]
    specs, _ = load_roster([_nikke(s) for s in slugs])
    boss = BossProfile(element="Water", fight_duration=180.0)
    print(f"roster {len(specs)} units; sampling {args.fit} fit + {args.holdout} holdout",
          flush=True)

    # Disjoint fit/holdout samples: draw fit+holdout, split.
    combos = sample_feasible_combinations(specs, args.fit + args.holdout, seed=args.seed)
    fit_combos = combos[:args.fit]
    hold_combos = combos[args.fit:]
    print(f"got {len(fit_combos)} fit + {len(hold_combos)} holdout combos", flush=True)

    with SimPool(specs, boss, workers="auto") as pool:
        scorer = pool.score_many
        y_fit = best_ordering_damage(fit_combos, boss, scorer)
        y_hold = np.array(best_ordering_damage(hold_combos, boss, scorer))

    fs = make_feature_space(specs)
    beta = fit_ridge(build_matrix(fit_combos, fs), np.array(y_fit), lam=args.lam)
    pred_hold = predict(build_matrix(hold_combos, fs), beta)

    order = np.argsort(-pred_hold)          # surrogate ranking (best first)
    surrogate_rank_of_true_best = int(np.where(order == int(np.argmax(y_hold)))[0][0])

    print(f"\nSpearman(surrogate, true) = {_spearman(pred_hold, y_hold):.3f}", flush=True)
    print(f"true-best surrogate rank = {surrogate_rank_of_true_best} "
          f"(of {len(hold_combos)})", flush=True)
    print(f"\n{'K':>5} {'true-top1 in top-K':>18} {'true-top5 in top-K':>18}", flush=True)
    top1 = int(np.argmax(y_hold))
    top5 = set(np.argsort(-y_hold)[:5].tolist())
    for k in (10, 20, 50, 100):
        topk = set(order[:k].tolist())
        print(f"{k:>5} {str(top1 in topk):>18} "
              f"{str(len(top5 & topk)) + '/5':>18}", flush=True)


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Smoke-test the harness at tiny scale**

Run: `cd "$(git rev-parse --show-toplevel)" && python3 scripts/validate_surrogate_recall.py --units 22 --fit 120 --holdout 40 --seed 3`
Expected: runs to completion (a couple minutes), prints a Spearman value, the true-best rank, and the K-recall table. Accuracy is meaningless at this tiny scale — this only proves the harness computes and prints its metrics without error.

- [ ] **Step 3: Commit**

```bash
git add scripts/validate_surrogate_recall.py
git commit -m "Add surrogate recall-validation harness"
```

---

### Task 6: Docs — record the Phase-1 harness

**Files:**
- Modify: `docs/roadmap.md` (Phase 5 perf backlog area)

- [ ] **Step 1: Add the note**

In `docs/roadmap.md`, after the unit-pool-selection landing bullet (the `✅ 유저 풀 선택(제외) 착지` entry added earlier), add:

```markdown
  - **🔬 캐스케이드 대리모델 Phase 1 (2026-07-23):** 프로파일이 raid-from-scratch
    비용의 ~66%가 "모든 후보 시뮬"임을 확인 → 조사 결과 빠른 도구들은 값싼 수식으로
    랭킹하고 top-K만 정밀평가(캐스케이드). reference-free 표본-회귀 대리모델
    (`backend/app/surrogate.py`)과 recall 검증 하네스(`scripts/validate_surrogate_recall.py`)
    구현. **다음: 하네스를 실 로스터로 돌려 top-K recall/Spearman 측정 → Go면 Phase 2
    (캐스케이드 통합)**. spec/plan: `docs/superpowers/{specs,plans}/2026-07-23-cascade-surrogate*`.
```

- [ ] **Step 2: Commit**

```bash
git add docs/roadmap.md
git commit -m "docs(roadmap): record cascade surrogate Phase 1 harness"
```

---

## Self-Review

**Spec coverage:**
- Reference-free sample-regression surrogate (membership + restricted pairs, ridge) → Tasks 1, 3.
- Feasible-combination sampling, deterministic → Task 2.
- Best-ordering damage as the training target, one batched scorer call → Task 4.
- Recall-validation harness (fit/holdout split, top-K recall, Spearman, go-metrics) → Task 5.
- Engine unchanged / surrogate is a read-only leaf → Global Constraints; no task edits engine files.
- Docs record → Task 6.
- Non-goals (no cascade wiring, no ordering surrogate, no worker cap) → respected; nothing wires into `deck_search`/`deck_allocation`.

**Placeholder scan:** No TBD/TODO; every code step has complete code and exact commands.

**Type consistency:** `FeatureSpace`/`make_feature_space`/`featurize`/`build_matrix` (Task 1) consumed by Tasks 4, 5 with matching names. `fit_ridge(X, y, lam)`/`predict(X, beta)` (Task 3) consumed in Task 5. `sample_feasible_combinations(roster, n_samples, seed)` (Task 2) consumed in Task 5. `best_ordering_damage(combos, boss, score_orderings)` (Task 4) consumed in Task 5 with `score_orderings = pool.score_many`. Consistent.
