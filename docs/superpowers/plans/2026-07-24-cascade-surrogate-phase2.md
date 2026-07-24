# 캐스케이드 대리모델 Phase 2 (탐색 통합) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 유닛 단독 표본-회귀 대리모델로 후보 조합을 값싸게 랭킹하고 top-K만 진짜 시뮬하도록 `search_best_decks`를 바꿔, 할당 비용의 91.5%를 차지하는 "풀 조합 순서 전수 시뮬"을 걷어낸다.

**Architecture:** 신규 `backend/app/cascade.py`가 적합·풀 선정·조합 랭킹을 맡는다. `deck_search`는 `cascade`를 **임포트하지 않고** 덕타이핑 객체로 주입받는다(아래 Global Constraints의 순환 임포트 항목). `deck_allocation`이 두 모듈을 이어붙인다. 엔진(`raid_simulator`)과 API 계약은 무변경.

**Tech Stack:** Python 3.13, numpy, pytest. 기존 모듈: `app/surrogate.py`(피처·ridge·예측), `app/deck_search.py`(조합 열거·prune·시뮬 배치), `app/sim_pool.py`(ProcessPool).

## Global Constraints

- **`python3`를 쓸 것.** 이 머신의 `python`은 pydantic/numpy가 없다. 모든 명령은 `python3`.
- **작업 디렉터리는 워크트리 루트** `C:\Users\fienn\Desktop\NikkeDeckBuilder\.claude\worktrees\simpool-optimization`. 원본 저장소로 `cd` 하지 말 것.
- **pytest는 `backend/`에서 실행**한다: `cd backend && python3 -m pytest ...`
- **순환 임포트 금지.** `surrogate.py`가 이미 `deck_search`를 임포트한다. 따라서 `cascade.py`는 `deck_search`/`surrogate`를 임포트해도 되지만, **`deck_search.py`는 `cascade`를 임포트해서는 안 된다** — `search_best_decks`가 캐스케이드 객체를 인자로 주입받는다. 이는 `deck_search._score_batch`가 `sim_pool`을 임포트하지 않고 `pool`을 덕타이핑으로 받는 기존 선례와 같은 해법이다.
- **기존 스위트 유지:** 작업 전 기준선은 **1215 passed / 3 skipped**. 모든 태스크의 마지막에 이 수치가 줄지 않아야 한다(늘어나는 건 정상).
- **주석 규칙(프로젝트 CLAUDE.md):** 주석은 **무엇을/왜**를 적고, 변경 이력이나 "예전엔 이랬다"는 적지 않는다.
- **커밋은 자주.** 각 태스크 끝에 커밋한다. 훅을 우회하지 말 것(`--no-verify` 금지).

---

## File Structure

| 파일 | 책임 |
|---|---|
| `backend/app/cascade.py` (신규) | 대리모델 적합, 지문/캐시, 넓힌 풀 선정, 조합 랭킹(`Cascade.shortlist`) |
| `backend/tests/test_cascade.py` (신규) | 위 전부의 단위 테스트 |
| `backend/app/deck_search.py` (수정) | 예산 판정 조기 종료, `search_best_decks`에 `cascade` 주입 인자 |
| `backend/app/deck_allocation.py` (수정) | 요청당 1회 적합 후 각 탐색 호출에 전달 |
| `backend/tests/test_deck_allocation.py` (수정) | 캐스케이드 vs 전수 품질 회귀 테스트 |
| `scripts/validate_surrogate_recall.py` (수정) | 풀 분포 추출 옵션(게이트 측정용) |

---

### Task 1: 대리모델 객체와 적합 함수

**Files:**
- Create: `backend/app/cascade.py`
- Test: `backend/tests/test_cascade.py`

**Interfaces:**
- Consumes: `app.surrogate.make_feature_space(roster, include_pairs=False)`, `featurize`, `build_matrix`, `sample_feasible_combinations(roster, n_samples, seed)`, `fit_ridge(X, y, lam)`, `predict(X, beta)`, `best_ordering_damage(combos, boss, score_orderings)`
- Produces:
  - `FIT_SAMPLE_DECKS = 200`, `FIT_SEED = 20260724`, `FIT_LAMBDA = 1.0`, `DEFAULT_TOP_K = 20`, `WIDE_TIER_CAPS = {1: 4, 2: 6, 3: 12}`
  - `class SurrogateModel` with `.feature_space`, `.beta`, `.coefficient(slug) -> float`, `.covers(roster) -> bool`, `.score_combos(combos) -> np.ndarray`
  - `fit_surrogate(roster, boss, score_orderings, samples=FIT_SAMPLE_DECKS, seed=FIT_SEED, lam=FIT_LAMBDA) -> SurrogateModel | None`

`score_orderings`는 `best_ordering_damage`와 같은 주입 규약이다 — 덱 리스트를 받아 총딜 리스트를 돌려주는 콜러블. 이렇게 두면 테스트가 시뮬 없이 돌고, 실제 호출자는 `SimPool` 배치를 넘긴다.

- [ ] **Step 1: Write the failing test**

`backend/tests/test_cascade.py`:

```python
from types import SimpleNamespace

import numpy as np
import pytest

from app.cascade import SurrogateModel, fit_surrogate
from app.deck_search import BossProfile


def _u(slug, tier):
    return SimpleNamespace(slug=slug, burst_tier=tier)


def _roster(n1=4, n2=6, n3=12):
    return ([_u(f"a{i}", 1) for i in range(n1)]
            + [_u(f"b{i}", 2) for i in range(n2)]
            + [_u(f"c{i}", 3) for i in range(n3)])


BOSS = BossProfile(element="Water")


def _scorer_favouring(favoured, base=100.0, bonus=50.0):
    """Batch scorer: a deck scores `base` plus `bonus` per favoured member.
    Records every batch it was handed so tests can assert on the fit's cost."""
    calls = {"batches": 0, "decks": 0}

    def score(decks):
        calls["batches"] += 1
        calls["decks"] += len(decks)
        return [base + bonus * sum(1 for u in deck if u.slug in favoured)
                for deck in decks]

    return score, calls


def test_fit_surrogate_learns_which_units_are_valuable():
    roster = _roster()
    score, calls = _scorer_favouring({"c0", "b0"})

    model = fit_surrogate(roster, BOSS, score, samples=120)

    assert isinstance(model, SurrogateModel)
    # the favoured units must outrank their same-tier peers
    assert model.coefficient("c0") > model.coefficient("c5")
    assert model.coefficient("b0") > model.coefficient("b5")
    assert calls["decks"] > 0


def test_fit_surrogate_uses_unit_columns_only():
    model = fit_surrogate(_roster(), BOSS, _scorer_favouring({"c0"})[0], samples=120)
    assert model.feature_space.pair_col == {}
    assert model.feature_space.n_features == 1 + 22


def test_fit_surrogate_is_deterministic_for_a_seed():
    roster = _roster()
    first = fit_surrogate(roster, BOSS, _scorer_favouring({"c0"})[0], samples=120)
    second = fit_surrogate(roster, BOSS, _scorer_favouring({"c0"})[0], samples=120)
    assert np.allclose(first.beta, second.beta)


def test_fit_surrogate_returns_none_when_the_sample_is_too_thin():
    # one unit per tier -> a single feasible combination, nowhere near `samples`
    tiny = [_u("a0", 1), _u("b0", 2), _u("c0", 3), _u("c1", 3), _u("c2", 3)]
    assert fit_surrogate(tiny, BOSS, _scorer_favouring(set())[0], samples=120) is None


def test_coefficient_of_an_unknown_unit_is_zero():
    model = fit_surrogate(_roster(), BOSS, _scorer_favouring({"c0"})[0], samples=120)
    assert model.coefficient("not-in-roster") == 0.0


def test_covers_reports_whether_every_unit_has_a_column():
    roster = _roster()
    model = fit_surrogate(roster, BOSS, _scorer_favouring({"c0"})[0], samples=120)
    assert model.covers(roster[:5]) is True
    assert model.covers(roster[:4] + [_u("stranger", 3)]) is False


def test_score_combos_ranks_a_favoured_combo_above_a_plain_one():
    roster = _roster()
    model = fit_surrogate(roster, BOSS, _scorer_favouring({"c0"})[0], samples=120)
    favoured = [roster[0], roster[4], roster[10], roster[11], roster[12]]  # holds c0
    plain = [roster[1], roster[5], roster[13], roster[14], roster[15]]
    scores = model.score_combos([favoured, plain])
    assert scores.shape == (2,)
    assert scores[0] > scores[1]
```

주의: `_roster()`가 4/6/12명이라 `roster[10]`은 `c0`이다(인덱스 0~3=a, 4~9=b, 10~21=c).

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python3 -m pytest tests/test_cascade.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.cascade'`

- [ ] **Step 3: Write minimal implementation**

`backend/app/cascade.py`:

```python
"""Cheap-filter stage for deck search: rank candidate combinations with a
fitted surrogate and simulate only the top-K.

Measured on a 41-unit roster, 91.5% of an allocate_decks run's simulations go
into scoring every intra-tier ordering of the pruned candidate pool. This module
replaces that exhaustive pass with a ranking that costs a matrix multiply, so
simulation cost is pinned to K instead of to the pool's size.

The surrogate is unit-only (no pair terms) by design, not by simplification:
pair columns grow quadratically with the roster and a determined ridge fit needs
at least as many SIMULATED sample decks as it has columns, so pairs cost about
as many simulations as the search they would replace (measured 1.22x). Unit
columns grow linearly, so a 200-deck fit serves a 78-unit roster as easily as a
41-unit one - see docs/decisions.md.

Because the coefficients are per-unit and the model is additive, a fit made on
the FULL roster scores any subset of it. That is what lets one fit serve every
iteration of allocate_decks' greedy peel.

This module may import deck_search; deck_search must NOT import this one
(surrogate.py already imports deck_search, so the reverse edge would be a
cycle). search_best_decks receives a Cascade by injection instead - the same
shape as its duck-typed `pool` argument.
"""
from dataclasses import dataclass

import numpy as np

from app.surrogate import (best_ordering_damage, build_matrix, fit_ridge,
                           make_feature_space, predict,
                           sample_feasible_combinations)

# Decks sampled and truly simulated to fit the model. 200 comfortably exceeds
# the 79 unit columns a full 78-unit roster produces, which is what a
# determined ridge fit needs.
FIT_SAMPLE_DECKS = 200
FIT_SEED = 20260724
FIT_LAMBDA = 1.0

# Combinations handed to the real simulator. Set by the Phase 2 recall gate
# (see docs/superpowers/plans/2026-07-24-cascade-surrogate-phase2.md, Task 4).
DEFAULT_TOP_K = 20

# The cascade's candidate pool, wider than deck_search.PRUNED_TIER_CAPS. The
# tight caps there exist only because everything in that pool gets simulated;
# once simulation cost is pinned to K, a wider pool costs a matrix multiply.
WIDE_TIER_CAPS = {1: 4, 2: 6, 3: 12}


@dataclass
class SurrogateModel:
    """Fitted coefficients plus the column layout they were fit in."""

    feature_space: object
    beta: np.ndarray

    def coefficient(self, slug):
        """The unit's learned value; 0.0 for a unit the fit never saw."""
        col = self.feature_space.unit_col.get(slug)
        return 0.0 if col is None else float(self.beta[col])

    def covers(self, roster):
        return all(u.slug in self.feature_space.unit_col for u in roster)

    def score_combos(self, combos):
        return predict(build_matrix(combos, self.feature_space), self.beta)


def fit_surrogate(roster, boss, score_orderings, samples=FIT_SAMPLE_DECKS,
                  seed=FIT_SEED, lam=FIT_LAMBDA):
    """Fit the ranking model, or None when the roster is too small to support it.

    `score_orderings` is the same injected batch scorer best_ordering_damage
    takes: a callable from a list of ordered decks to their total damages.

    Returning None rather than a weak model is deliberate - the caller falls
    back to the exhaustive path, which is correct but slower. A model fit on a
    handful of decks would instead silently mis-rank.
    """
    combos = sample_feasible_combinations(roster, samples, seed=seed)
    feature_space = make_feature_space(roster, include_pairs=False)
    if len(combos) < feature_space.n_features:
        return None
    y = best_ordering_damage(combos, boss, score_orderings)
    beta = fit_ridge(build_matrix(combos, feature_space), np.array(y), lam=lam)
    return SurrogateModel(feature_space=feature_space, beta=beta)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python3 -m pytest tests/test_cascade.py -q`
Expected: PASS (8 passed)

- [ ] **Step 5: Run the whole suite**

Run: `cd backend && python3 -m pytest -q`
Expected: 1223 passed, 3 skipped (기준선 1215 + 신규 8)

- [ ] **Step 6: Commit**

```bash
git add backend/app/cascade.py backend/tests/test_cascade.py
git commit -m "Add the cascade's fitted surrogate model

Unit-only columns and an injected batch scorer, so the fit is testable without
touching the simulator. Returns None on a roster too small to determine the
fit rather than handing back a model that would silently mis-rank."
```

---

### Task 2: 지문과 요청 간 fit 캐시

**Files:**
- Modify: `backend/app/cascade.py`
- Test: `backend/tests/test_cascade.py`

**Interfaces:**
- Consumes: Task 1의 `fit_surrogate`, `SurrogateModel`
- Produces:
  - `roster_fingerprint(roster, boss) -> str`
  - `cached_fit_surrogate(roster, boss, score_orderings) -> SurrogateModel | None`
  - `clear_fit_cache() -> None` (테스트용)
  - `FIT_CACHE_SIZE = 8`

- [ ] **Step 1: Write the failing test**

`backend/tests/test_cascade.py` 하단에 추가:

```python
from dataclasses import replace as _dc_replace  # noqa: E402  (top of file in practice)

from app.cascade import (FIT_CACHE_SIZE, cached_fit_surrogate, clear_fit_cache,
                         roster_fingerprint)


def _investable(slug, tier):
    """A roster unit carrying the investment fields the fingerprint reads."""
    return SimpleNamespace(
        slug=slug, burst_tier=tier, burst_cooldown=20.0, element="Water",
        weapon="AR", base_stats={"atk": 60000.0, "def": 3000.0, "max_hp": 1e6},
        skill_values={"s": {"description_value_01": "10"}},
        weapon_stats={"weapon": "AR", "damage_percent": 100.0},
        overload_options=[])


def _investable_roster():
    return ([_investable(f"a{i}", 1) for i in range(4)]
            + [_investable(f"b{i}", 2) for i in range(6)]
            + [_investable(f"c{i}", 3) for i in range(12)])


def test_fingerprint_is_stable_across_roster_order():
    roster = _investable_roster()
    assert roster_fingerprint(roster, BOSS) == roster_fingerprint(roster[::-1], BOSS)


def test_fingerprint_changes_when_investment_changes():
    roster = _investable_roster()
    before = roster_fingerprint(roster, BOSS)
    roster[0].skill_values = {"s": {"description_value_01": "11"}}
    assert roster_fingerprint(roster, BOSS) != before


def test_fingerprint_changes_when_overload_changes():
    roster = _investable_roster()
    before = roster_fingerprint(roster, BOSS)
    roster[0].overload_options = [{"stat": "atk_percent", "value": 0.1}]
    assert roster_fingerprint(roster, BOSS) != before


def test_fingerprint_changes_with_the_boss():
    roster = _investable_roster()
    assert (roster_fingerprint(roster, BOSS)
            != roster_fingerprint(roster, BossProfile(element="Fire")))


def test_cached_fit_reuses_the_model_for_the_same_roster_and_boss():
    clear_fit_cache()
    roster = _investable_roster()
    score, calls = _scorer_favouring({"c0"})

    first = cached_fit_surrogate(roster, BOSS, score)
    decks_after_first = calls["decks"]
    second = cached_fit_surrogate(roster, BOSS, score)

    assert second is first                      # same object, not an equal one
    assert calls["decks"] == decks_after_first  # no second round of simulation


def test_cached_fit_refits_when_a_skill_level_changes():
    clear_fit_cache()
    roster = _investable_roster()
    score, calls = _scorer_favouring({"c0"})

    cached_fit_surrogate(roster, BOSS, score)
    decks_after_first = calls["decks"]
    roster[0].skill_values = {"s": {"description_value_01": "11"}}
    cached_fit_surrogate(roster, BOSS, score)

    assert calls["decks"] > decks_after_first


def test_cache_evicts_the_oldest_entry_past_its_bound():
    clear_fit_cache()
    score, _ = _scorer_favouring({"c0"})
    rosters = []
    for i in range(FIT_CACHE_SIZE + 1):
        roster = _investable_roster()
        roster[0].slug = f"a0-variant{i}"      # a distinct fingerprint each time
        rosters.append(roster)
        cached_fit_surrogate(roster, BOSS, score)

    # the first roster fell out, so asking again re-simulates
    score2, calls2 = _scorer_favouring({"c0"})
    cached_fit_surrogate(rosters[0], BOSS, score2)
    assert calls2["decks"] > 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python3 -m pytest tests/test_cascade.py -q`
Expected: FAIL — `ImportError: cannot import name 'FIT_CACHE_SIZE' from 'app.cascade'`

- [ ] **Step 3: Write minimal implementation**

`backend/app/cascade.py` 상단 임포트에 추가:

```python
from collections import OrderedDict
from dataclasses import astuple, dataclass
import hashlib
import json
```

파일 하단에 추가:

```python
# Fits are keyed by content, so nothing ever needs explicit invalidation - a
# changed skill level or overload simply produces a different key. Bounded so a
# long-lived server process cannot grow without limit.
FIT_CACHE_SIZE = 8

_fit_cache = OrderedDict()


def roster_fingerprint(roster, boss):
    """A stable digest of everything that changes a deck's damage.

    Cube effects are assumed uniform per slug (roster._passive_effects), so the
    slug covers them. Sorted by slug and dumped with sorted keys, so the digest
    does not depend on roster order or dict insertion order.
    """
    units = [
        {
            "slug": unit.slug,
            "burst_tier": unit.burst_tier,
            "burst_cooldown": getattr(unit, "burst_cooldown", None),
            "element": getattr(unit, "element", None),
            "weapon": getattr(unit, "weapon", None),
            "base_stats": getattr(unit, "base_stats", None),
            "skill_values": getattr(unit, "skill_values", None),
            "weapon_stats": getattr(unit, "weapon_stats", None),
            "overload_options": getattr(unit, "overload_options", None),
        }
        for unit in sorted(roster, key=lambda u: u.slug)
    ]
    payload = json.dumps({"units": units, "boss": astuple(boss)},
                         sort_keys=True, default=str)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def cached_fit_surrogate(roster, boss, score_orderings):
    """fit_surrogate, reusing a previous fit for the same roster state and boss.

    Safe on two counts: the engine has no RNG, so an identical key with a fixed
    sample seed yields an identical fit; and the model only chooses WHICH decks
    to simulate, so even a wrong hit would cost ranking quality, never the
    correctness of a reported damage number.
    """
    key = roster_fingerprint(roster, boss)
    if key in _fit_cache:
        _fit_cache.move_to_end(key)
        return _fit_cache[key]
    model = fit_surrogate(roster, boss, score_orderings)
    _fit_cache[key] = model
    _fit_cache.move_to_end(key)
    while len(_fit_cache) > FIT_CACHE_SIZE:
        _fit_cache.popitem(last=False)
    return model


def clear_fit_cache():
    _fit_cache.clear()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python3 -m pytest tests/test_cascade.py -q`
Expected: PASS (15 passed)

- [ ] **Step 5: Run the whole suite**

Run: `cd backend && python3 -m pytest -q`
Expected: 1230 passed, 3 skipped

- [ ] **Step 6: Commit**

```bash
git add backend/app/cascade.py backend/tests/test_cascade.py
git commit -m "Cache surrogate fits by roster state and boss

Content-addressed, so a changed skill level or overload produces a different
key and no explicit invalidation is needed. Bounded at 8 entries."
```

---

### Task 3: 넓힌 후보 풀 선정

**Files:**
- Modify: `backend/app/cascade.py`
- Test: `backend/tests/test_cascade.py`

**Interfaces:**
- Consumes: Task 1의 `SurrogateModel.coefficient`, `WIDE_TIER_CAPS`; `app.deck_search.prune_candidate_pool(roster, boss, pool=None)`
- Produces: `widened_pool(roster, boss, model, pool=None, caps=WIDE_TIER_CAPS) -> list[unit]`

`prune_candidate_pool`의 선택을 **먼저** 넣고 남은 자리를 **티어별로** 계수 순으로 채운다. 티어별로 채우는 이유: 합법 덱은 세 티어를 모두 요구하므로, 계수를 티어 구분 없이 정렬하면 한 티어가 굶을 수 있다.

- [ ] **Step 1: Write the failing test**

```python
from app.cascade import WIDE_TIER_CAPS, widened_pool


class _FakeModel:
    """Coefficients straight from a dict, so pool tests don't need a real fit."""

    def __init__(self, values):
        self.values = values

    def coefficient(self, slug):
        return self.values.get(slug, 0.0)


def test_widened_pool_keeps_every_pruned_unit(monkeypatch):
    roster = _roster()
    pruned = [roster[0], roster[4], roster[10], roster[11], roster[12]]
    monkeypatch.setattr("app.cascade.prune_candidate_pool",
                        lambda r, b, p=None: pruned)

    out = widened_pool(roster, BOSS, _FakeModel({}))

    assert set(u.slug for u in pruned) <= set(u.slug for u in out)


def test_widened_pool_respects_the_tier_caps(monkeypatch):
    roster = _roster(n1=8, n2=10, n3=20)
    monkeypatch.setattr("app.cascade.prune_candidate_pool",
                        lambda r, b, p=None: list(r)[:5])

    out = widened_pool(roster, BOSS, _FakeModel({}))

    counts = {t: sum(1 for u in out if u.burst_tier == t) for t in (1, 2, 3)}
    assert counts == WIDE_TIER_CAPS


def test_widened_pool_fills_remaining_seats_by_coefficient_within_tier(monkeypatch):
    roster = _roster(n1=8, n2=10, n3=20)
    monkeypatch.setattr("app.cascade.prune_candidate_pool", lambda r, b, p=None: [])
    # c19 is the best tier-3 unit; a7 the best tier-1. Both must be picked even
    # though a tier-blind sort by coefficient would fill up on tier 3 alone.
    model = _FakeModel({f"c{i}": i for i in range(20)} | {"a7": 1000.0})

    out = widened_pool(roster, BOSS, model)
    slugs = {u.slug for u in out}

    assert "c19" in slugs and "c8" in slugs   # top 12 of tier 3
    assert "c7" not in slugs                  # 13th, cut
    assert "a7" in slugs


def test_widened_pool_returns_units_in_tier_order(monkeypatch):
    roster = _roster()
    monkeypatch.setattr("app.cascade.prune_candidate_pool", lambda r, b, p=None: [])
    out = widened_pool(roster, BOSS, _FakeModel({}))
    tiers = [u.burst_tier for u in out]
    assert tiers == sorted(tiers)


def test_widened_pool_handles_a_roster_smaller_than_the_caps(monkeypatch):
    roster = _roster(n1=1, n2=1, n3=3)
    monkeypatch.setattr("app.cascade.prune_candidate_pool", lambda r, b, p=None: [])
    out = widened_pool(roster, BOSS, _FakeModel({}))
    assert len(out) == 5
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python3 -m pytest tests/test_cascade.py -q`
Expected: FAIL — `ImportError: cannot import name 'widened_pool' from 'app.cascade'`

- [ ] **Step 3: Write minimal implementation**

`backend/app/cascade.py` 임포트에 추가:

```python
from app.deck_search import prune_candidate_pool
```

파일 하단에 추가:

```python
def widened_pool(roster, boss, model, pool=None, caps=WIDE_TIER_CAPS):
    """The cascade's candidate pool: prune's picks, widened by coefficient.

    prune_candidate_pool goes in first because it is a genuinely different
    heuristic - marginal contribution measured in a reference deck, not a fitted
    coefficient - so the two filters' blind spots do not coincide. That is the
    safety net: a deck the surrogate undervalues can still reach the shortlist.

    Seats are filled PER TIER. A legal deck needs all three burst tiers, so a
    tier-blind sort by coefficient could starve one of them entirely.
    """
    chosen = {tier: [] for tier in caps}
    taken = set()

    def offer(unit):
        bucket = chosen.get(unit.burst_tier)
        if bucket is None or unit.slug in taken or len(bucket) >= caps[unit.burst_tier]:
            return
        bucket.append(unit)
        taken.add(unit.slug)

    for unit in prune_candidate_pool(roster, boss, pool):
        offer(unit)
    for unit in sorted(roster, key=lambda u: model.coefficient(u.slug), reverse=True):
        offer(unit)
    return [unit for tier in sorted(chosen) for unit in chosen[tier]]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python3 -m pytest tests/test_cascade.py -q`
Expected: PASS (20 passed)

- [ ] **Step 5: Run the whole suite**

Run: `cd backend && python3 -m pytest -q`
Expected: 1235 passed, 3 skipped

- [ ] **Step 6: Commit**

```bash
git add backend/app/cascade.py backend/tests/test_cascade.py
git commit -m "Select the cascade's widened candidate pool

prune's picks go in first as a differently-blind second filter, then seats fill
by coefficient per tier - a tier-blind sort could starve a burst tier a legal
deck requires."
```

---

### Task 4: 재검증 게이트 (측정 태스크 — K를 정한다)

**Files:**
- Modify: `scripts/validate_surrogate_recall.py`
- Modify: `backend/app/cascade.py` (측정 결과로 `DEFAULT_TOP_K` 확정)

**Interfaces:**
- Consumes: Task 1–3 전부
- Produces: 확정된 `DEFAULT_TOP_K` 값, 또는 **캐스케이드 미채택 판정**

이 태스크는 TDD가 아니라 **측정**이다. Phase 1의 recall은 전체 로스터에서 균등 추출한 조합에서 쟀지만, 캐스케이드가 실제로 마주하는 건 **넓힌 풀에서 나온 조합**이고 그 안은 이미 걸러진 강한 유닛뿐이라 분산이 좁다 — 순위 문제가 더 어려워지는 방향이다.

- [ ] **Step 1: 하네스에 풀 분포 추출 옵션 추가**

`scripts/validate_surrogate_recall.py`의 인자 정의부에 추가:

```python
    p.add_argument("--pool-draw", action="store_true",
                   help="draw the holdout from the cascade's widened pool instead "
                        "of the whole roster - the distribution the cascade "
                        "actually ranks, where every candidate is already strong")
```

`combos = sample_feasible_combinations(specs, args.fit + args.holdout, seed=args.seed)` 를 다음으로 교체:

```python
    if args.pool_draw:
        # Fit on the full roster exactly as the cascade does, then draw the
        # holdout from the pool that fit produces.
        seed_scorer = (lambda decks: [evaluate_deck(d, boss)["total_damage"]
                                      for d in decks])
        seed_model = fit_surrogate(specs, boss, seed_scorer)
        if seed_model is None:
            print("ERROR: roster too small to fit the pool-selection model.", flush=True)
            sys.exit(1)
        pool_units = widened_pool(specs, boss, seed_model)
        print(f"widened pool: {len(pool_units)} units", flush=True)
        combos = sample_feasible_combinations(
            pool_units, args.fit + args.holdout, seed=args.seed)
    else:
        combos = sample_feasible_combinations(
            specs, args.fit + args.holdout, seed=args.seed)
```

임포트 추가:

```python
from app.cascade import fit_surrogate, widened_pool  # noqa: E402
```

- [ ] **Step 2: 게이트 실행 — 78유닛, 풀 분포, 5시드**

각 시드마다 실행(백그라운드 권장, 시드당 수십 분):

```bash
for s in 3 7 11 23 42; do
  python3 scripts/validate_surrogate_recall.py --units 78 --fit 1200 --holdout 300 \
      --seed $s --surrogate regression --no-pairs --fit-subset 200 --pool-draw
done
```

각 실행의 `best-of-top-K damage` 열을 K=10/20/50/100에 대해 기록한다.

- [ ] **Step 3: K를 결정 규칙으로 고른다**

**중앙값 시드가 100%를 회수하고 최악 시드가 95% 이상인 가장 작은 K**를 채택한다.

**K ≤ 100에서 이를 만족하는 값이 없으면 여기서 멈춘다** — 캐스케이드를 채택하지 않고 Task 5만 진행한 뒤(그 태스크는 순수 이득이라 독립적으로 유효하다) Task 6–8을 폐기하고 Fienn에게 보고한다. 게이트는 실패할 수 있으며, 그 결과도 사전 합의된 결론이다.

- [ ] **Step 4: 확정값을 코드에 반영**

`backend/app/cascade.py`의 `DEFAULT_TOP_K`를 측정된 값으로 바꾸고, 주석에 근거를 남긴다:

```python
# Combinations handed to the real simulator. Chosen by the Phase 2 recall gate:
# the smallest K where the median seed recovered 100% of the best deck's damage
# and the worst of 5 seeds stayed above 95%, measured at 78 units on
# combinations drawn from the widened pool (docs/decisions.md).
DEFAULT_TOP_K = <측정값>
```

- [ ] **Step 5: 측정 결과를 문서화**

`docs/decisions.md`의 Phase 1 항목 아래에 게이트 결과(시드별 표, 채택 K, 또는 미채택 판정)를 덧붙인다.

- [ ] **Step 6: Commit**

```bash
git add scripts/validate_surrogate_recall.py backend/app/cascade.py docs/decisions.md
git commit -m "Gate the cascade on recall measured in the pool distribution

Phase 1 measured recall on combinations drawn uniformly from the whole roster,
but the cascade ranks combinations drawn from a pool of already-strong units -
a narrower spread and a harder ranking problem. Re-measured at 78 units across
5 seeds, and pinned K to the smallest value meeting the pre-agreed bar."
```

---

### Task 5: 예산 판정의 전수 열거 제거

**Files:**
- Modify: `backend/app/deck_search.py` (`_all_intra_tier_orderings` 아래, `search_best_decks` 위)
- Test: `backend/tests/test_deck_search.py`

**Interfaces:**
- Produces: `_orderings_within_budget(roster, sim_budget) -> list | None`

이 태스크는 캐스케이드와 독립적인 순수 이득이다 — 게이트가 실패해도 유효하다.

- [ ] **Step 1: Write the failing test**

`backend/tests/test_deck_search.py` 하단에 추가:

```python
from app.deck_search import _all_intra_tier_orderings, _orderings_within_budget
from app.deck_search import shape_combinations


def test_orderings_within_budget_returns_them_all_when_under():
    roster = fake_roster([1, 2, 3, 3, 3])
    out = _orderings_within_budget(roster, sim_budget=1000)
    assert out == _all_intra_tier_orderings(shape_combinations(roster))


def test_orderings_within_budget_returns_none_when_over():
    roster = fake_roster([1, 2, 3, 3, 3])
    assert _orderings_within_budget(roster, sim_budget=2) is None


def test_orderings_within_budget_stops_early_instead_of_enumerating_everything():
    """A budget of 1 must not walk the whole space - the point of the helper."""
    roster = fake_roster([1, 1, 1, 2, 2, 2, 3, 3, 3, 3, 3, 3, 3, 3])
    full = len(_all_intra_tier_orderings(shape_combinations(roster)))
    assert full > 100                       # the space really is large
    assert _orderings_within_budget(roster, sim_budget=1) is None
```

세 번째 테스트는 조기 종료를 직접 관찰하진 않지만, 다음 스텝의 구현이 `sim_budget`을 넘는 즉시 반환하도록 강제한다. 조기 종료 자체는 구현이 리스트 길이로만 판정하므로 구조적으로 보장된다.

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python3 -m pytest tests/test_deck_search.py -q -k orderings_within_budget`
Expected: FAIL — `ImportError: cannot import name '_orderings_within_budget'`

- [ ] **Step 3: Write minimal implementation**

`backend/app/deck_search.py`, `_all_intra_tier_orderings` 정의 바로 아래에 추가:

```python
def _orderings_within_budget(roster, sim_budget):
    """Every intra-tier ordering of `roster`, or None once they exceed the budget.

    Only the ANSWER to "does this fit the budget" is needed when it doesn't, so
    the walk stops at the first ordering past it. Enumerating the full space to
    then discard it costs real time on a large roster - a 78-unit roster has
    millions of orderings, and the parent-side generation showed up as ~23% of a
    profiled allocation.
    """
    out = []
    for combo in shape_combinations(roster):
        for ordered in _intra_tier_orderings(combo):
            out.append(ordered)
            if len(out) > sim_budget:
                return None
    return out
```

`search_best_decks` 본문 앞부분을 다음으로 교체:

```python
    candidates = list(roster)
    orderings = _orderings_within_budget(candidates, sim_budget)
    if orderings is None:
        candidates = prune_candidate_pool(roster, boss, pool)
        orderings = _all_intra_tier_orderings(shape_combinations(candidates))
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python3 -m pytest tests/test_deck_search.py -q`
Expected: PASS

- [ ] **Step 5: Run the whole suite**

Run: `cd backend && python3 -m pytest -q`
Expected: 1238 passed, 3 skipped

- [ ] **Step 6: Commit**

```bash
git add backend/app/deck_search.py backend/tests/test_deck_search.py
git commit -m "Stop enumerating every ordering just to reject the budget

The full walk was built and thrown away whenever it exceeded sim_budget, which
on a 78-unit roster means millions of orderings. Stop at the first one past the
budget instead."
```

---

### Task 6: `Cascade.shortlist`와 `search_best_decks` 주입

**Files:**
- Modify: `backend/app/cascade.py`
- Modify: `backend/app/deck_search.py` (`search_best_decks`)
- Test: `backend/tests/test_cascade.py`, `backend/tests/test_deck_search.py`

**Interfaces:**
- Consumes: Task 1–3, Task 5의 `_orderings_within_budget`
- Produces:
  - `class Cascade` with `.model`, `.top_k`, `.caps`, `.shortlist(roster, boss, pool=None) -> list[list[unit]] | None`
  - `search_best_decks(roster, boss, top_n=5, sim_budget=1200, pool=None, cascade=None)`

`shortlist`가 `None`을 돌려주면 호출자는 오늘의 전수 경로로 폴백한다.

- [ ] **Step 1: Write the failing test**

`backend/tests/test_cascade.py`:

```python
from app.cascade import Cascade


def test_shortlist_returns_top_k_combinations(monkeypatch):
    roster = _roster()
    monkeypatch.setattr("app.cascade.prune_candidate_pool", lambda r, b, p=None: [])
    model = fit_surrogate(roster, BOSS, _scorer_favouring({"c0"})[0], samples=120)

    combos = Cascade(model, top_k=7).shortlist(roster, BOSS)

    assert len(combos) == 7
    assert all(len(c) == 5 for c in combos)


def test_shortlist_is_ordered_by_predicted_score(monkeypatch):
    roster = _roster()
    monkeypatch.setattr("app.cascade.prune_candidate_pool", lambda r, b, p=None: [])
    model = fit_surrogate(roster, BOSS, _scorer_favouring({"c0", "b0"})[0], samples=120)

    combos = Cascade(model, top_k=10).shortlist(roster, BOSS)
    scores = model.score_combos(combos)

    assert list(scores) == sorted(scores, reverse=True)


def test_shortlist_declines_a_roster_the_model_does_not_cover(monkeypatch):
    roster = _roster()
    monkeypatch.setattr("app.cascade.prune_candidate_pool", lambda r, b, p=None: [])
    model = fit_surrogate(roster, BOSS, _scorer_favouring({"c0"})[0], samples=120)

    assert Cascade(model).shortlist(roster + [_u("stranger", 3)], BOSS) is None


def test_shortlist_declines_when_no_legal_combination_exists(monkeypatch):
    roster = _roster()
    model = fit_surrogate(roster, BOSS, _scorer_favouring({"c0"})[0], samples=120)
    monkeypatch.setattr("app.cascade.prune_candidate_pool", lambda r, b, p=None: [])
    # a subset with no tier-2 unit can form no legal deck
    tierless = [u for u in roster if u.burst_tier != 2]

    assert Cascade(model).shortlist(tierless, BOSS) is None


def test_shortlist_returns_everything_when_k_exceeds_the_pool(monkeypatch):
    roster = _roster(n1=1, n2=1, n3=3)
    monkeypatch.setattr("app.cascade.prune_candidate_pool", lambda r, b, p=None: [])
    model = _FakeModel({})
    model.covers = lambda r: True
    model.score_combos = lambda combos: np.zeros(len(combos))

    combos = Cascade(model, top_k=1000).shortlist(roster, BOSS)
    assert len(combos) == 1
```

`backend/tests/test_deck_search.py`:

```python
def test_search_best_decks_uses_the_cascade_when_over_budget():
    """The cascade's shortlist must be what gets simulated, not the pruned pool."""
    roster = fake_roster([1, 1, 2, 2, 3, 3, 3, 3])
    chosen = [[roster[0], roster[2], roster[4], roster[5], roster[6]]]

    class _StubCascade:
        def shortlist(self, r, b, pool=None):
            return chosen

    found = search_best_decks(roster, BossProfile(element="Water"), top_n=1,
                              sim_budget=1, cascade=_StubCascade())

    assert {u.slug for u in chosen[0]} == set(found[0]["deck"])


def test_search_best_decks_falls_back_when_the_cascade_declines():
    roster = fake_roster([1, 1, 2, 2, 3, 3, 3, 3])

    class _DecliningCascade:
        def shortlist(self, r, b, pool=None):
            return None

    found = search_best_decks(roster, BossProfile(element="Water"), top_n=1,
                              sim_budget=1, cascade=_DecliningCascade())

    assert len(found) == 1          # the exhaustive path still produced a deck
```

주의: `test_deck_search.py`의 `fake_roster`는 `FakeUnit(slug, burst_tier)`만 갖는다. `search_best_decks`는 실제 시뮬을 부르므로, 이 두 테스트는 기존 파일에서 `search_best_decks`를 이미 쓰는 테스트와 같은 방식(실제 스펙 픽스처 또는 `evaluate_deck` 스텁)을 따라야 한다. **구현자는 파일 상단을 읽고 그 파일이 이미 쓰는 방식에 맞출 것.** 기존 테스트가 `anis_star_spec`/`crown_spec`/`helm_spec`을 임포트하고 있으므로, 그 스펙들로 8유닛 로스터를 구성하는 편이 안전하다.

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python3 -m pytest tests/test_cascade.py tests/test_deck_search.py -q`
Expected: FAIL — `ImportError: cannot import name 'Cascade' from 'app.cascade'`

- [ ] **Step 3: Write minimal implementation**

`backend/app/cascade.py`의 **기존** `deck_search` 임포트 줄(Task 3에서 `prune_candidate_pool`을 추가한 그 줄)을 확장한다 — 새 임포트 줄을 만들지 말 것:

```python
from app.deck_search import prune_candidate_pool, shape_combinations
```

파일 하단에 추가:

```python
@dataclass
class Cascade:
    """Ranks a roster's combinations and hands back only the top-K to simulate.

    Injected into search_best_decks rather than imported by it: surrogate.py
    already imports deck_search, so a deck_search -> cascade edge would be a
    cycle. This mirrors how `pool` is threaded in.
    """

    model: SurrogateModel
    top_k: int = DEFAULT_TOP_K
    caps: dict = None

    def shortlist(self, roster, boss, pool=None):
        """The combinations worth simulating, or None to defer to the caller's
        own (exhaustive) path."""
        if not self.model.covers(roster):
            return None
        units = widened_pool(roster, boss, self.model, pool,
                             self.caps or WIDE_TIER_CAPS)
        combos = list(shape_combinations(units))
        if not combos:
            return None
        ranking = np.argsort(-self.model.score_combos(combos))[:self.top_k]
        return [combos[i] for i in ranking]
```

`backend/app/deck_search.py`의 `search_best_decks` 시그니처와 본문 앞부분을 교체:

```python
def search_best_decks(roster, boss: BossProfile, top_n=5, sim_budget=1200,
                      pool=None, cascade=None):
```

독스트링 끝에 한 문단 추가:

```
    `cascade` (duck-typed, see app.cascade.Cascade) is consulted when the
    budget is blown: its shortlist replaces the exhaustive scoring of the
    pruned pool. It may decline by returning None, in which case the pruned
    exhaustive path runs unchanged. This module never imports the cascade -
    surrogate.py already imports this one.
```

본문 앞부분:

```python
    candidates = list(roster)
    orderings = _orderings_within_budget(candidates, sim_budget)
    if orderings is None:
        combos = cascade.shortlist(roster, boss, pool) if cascade is not None else None
        if combos is None:
            combos = shape_combinations(prune_candidate_pool(roster, boss, pool))
        orderings = _all_intra_tier_orderings(combos)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python3 -m pytest tests/test_cascade.py tests/test_deck_search.py -q`
Expected: PASS

- [ ] **Step 5: Run the whole suite**

Run: `cd backend && python3 -m pytest -q`
Expected: 1245 passed, 3 skipped

- [ ] **Step 6: Commit**

```bash
git add backend/app/cascade.py backend/app/deck_search.py backend/tests/
git commit -m "Let search_best_decks simulate a cascade's shortlist

The cascade is injected, not imported: surrogate.py already imports deck_search,
so the reverse edge would be a cycle. It can decline, and the exhaustive pruned
path stays as the fallback."
```

---

### Task 7: `allocate_decks` 배선 — 요청당 1회 적합

**Files:**
- Modify: `backend/app/deck_allocation.py` (`allocate_decks`)
- Test: `backend/tests/test_deck_allocation.py`

**Interfaces:**
- Consumes: Task 2의 `cached_fit_surrogate`, Task 5의 `_orderings_within_budget`, Task 6의 `Cascade`
- Produces: 변경 없는 공개 시그니처 — `allocate_decks(roster, boss, num_decks=5, draft=None, locked=frozenset(), time_budget_sec=45.0, workers=None)`

- [ ] **Step 1: Write the failing test**

`backend/tests/test_deck_allocation.py` 하단에 추가:

이 파일에는 이미 두 헬퍼가 있다 — 새로 만들지 말고 재사용할 것: `roster_of(tiers_by_slug)`(가짜 `Unit(slug, tier)` 리스트)와 `patch_scorer(monkeypatch, scorer)`(`deck_search`와 `deck_allocation` 양쪽의 `evaluate_deck`을 스텁). `patch_scorer`가 걸려 있으면 적합도 스텁 스코어러를 타므로 **가짜 유닛으로도 실제 적합 경로가 그대로 돈다.**

```python
from app.cascade import clear_fit_cache


def _wide_roster():
    """Big enough that search_best_decks blows its ordering budget."""
    tiers = {}
    for i in range(6):
        tiers[f"w1-{i}"] = 1
    for i in range(6):
        tiers[f"w2-{i}"] = 2
    for i in range(12):
        tiers[f"w3-{i}"] = 3
    return roster_of(tiers)


def test_allocation_fits_the_surrogate_once_for_the_whole_peel(monkeypatch):
    """One fit must serve every greedy-peel iteration - the additive model is
    what makes that valid, and refitting per iteration would erase the saving."""
    clear_fit_cache()
    patch_scorer(monkeypatch, lambda slugs: float(len(slugs)))
    fits = {"n": 0}
    real_fit = da.cached_fit_surrogate

    def counting_fit(roster, boss, score_orderings):
        fits["n"] += 1
        return real_fit(roster, boss, score_orderings)

    monkeypatch.setattr(da, "cached_fit_surrogate", counting_fit)

    da.allocate_decks(_wide_roster(), BossProfile(), num_decks=3,
                      time_budget_sec=0.0)

    assert fits["n"] == 1


def test_small_rosters_never_fit_a_surrogate(monkeypatch):
    """Existing tests use tiny rosters and stub evaluate_deck; they must keep
    taking the untouched exhaustive path."""
    clear_fit_cache()
    patch_scorer(monkeypatch, lambda slugs: float(len(slugs)))
    fits = {"n": 0}
    monkeypatch.setattr(da, "cached_fit_surrogate",
                        lambda *a, **k: fits.__setitem__("n", fits["n"] + 1))

    da.allocate_decks(roster_of({"a1": 1, "a2": 2, "a3": 3, "a4": 3, "a5": 3}),
                      BossProfile(), num_decks=1, time_budget_sec=0.0)

    assert fits["n"] == 0
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python3 -m pytest tests/test_deck_allocation.py -q -k surrogate`
Expected: FAIL — `AttributeError: module 'app.deck_allocation' has no attribute 'cached_fit_surrogate'`

- [ ] **Step 3: Write minimal implementation**

`backend/app/deck_allocation.py` 임포트에 추가:

```python
from app.cascade import Cascade, cached_fit_surrogate
from app.deck_search import _orderings_within_budget, _score_batch
```

(`_score_batch`는 이미 임포트되어 있다 — 중복 추가하지 말 것.)

`allocate_decks` 본문에서 `decks = []` 바로 앞에 추가:

```python
        # One fit serves the whole peel: the surrogate is additive over unit
        # membership, so coefficients learned on the full roster score any
        # subset of it. Only rosters that would actually blow the search budget
        # pay for a fit - everything smaller keeps the exhaustive path.
        cascade = None
        if _orderings_within_budget(roster, SEARCH_SIM_BUDGET) is None:
            model = cached_fit_surrogate(
                roster, boss, lambda decks: _score_batch(decks, boss, pool))
            if model is not None:
                cascade = Cascade(model)
```

`search_best_decks` 호출을 교체:

```python
            found = search_best_decks(remaining, boss, top_n=1, pool=pool,
                                      cascade=cascade)
```

`backend/app/deck_search.py`에 예산 기본값을 상수로 노출(두 모듈이 같은 값을 봐야 한다):

```python
# search_best_decks' default ordering budget, exported so callers can ask the
# same question the search will ask.
SEARCH_SIM_BUDGET = 1200
```

그리고 `search_best_decks`의 기본 인자를 `sim_budget=SEARCH_SIM_BUDGET`로 바꾼다. `deck_allocation`의 임포트에 `SEARCH_SIM_BUDGET`를 추가한다.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python3 -m pytest tests/test_deck_allocation.py -q`
Expected: PASS

- [ ] **Step 5: Run the whole suite**

Run: `cd backend && python3 -m pytest -q`
Expected: 1247 passed, 3 skipped

- [ ] **Step 6: Commit**

```bash
git add backend/app/deck_allocation.py backend/app/deck_search.py backend/tests/test_deck_allocation.py
git commit -m "Fit the surrogate once per allocation and thread it through the peel

The model is additive over unit membership, so one fit on the full roster
scores every shrinking remainder. Rosters small enough to enumerate never fit
at all, which keeps the existing stubbed tests on the untouched path."
```

---

### Task 8: 품질 회귀 테스트와 수용 측정

**Files:**
- Modify: `backend/tests/test_deck_allocation.py`
- Modify: `docs/roadmap.md`, `docs/decisions.md`

**Interfaces:**
- Consumes: Task 6–7의 통합 경로

- [ ] **Step 1: Write the failing test**

작은 로스터는 기본적으로 캐스케이드를 우회하므로 `sim_budget=1`로 강제하고, 같은 로스터를 전수로도 돌려 비교한다.

**실제 엔진이 아니라 스텁 스코어러를 쓴다.** 실제 인코딩 스펙으로 이 테스트를 구성하려면 티어별 정원을 채울 만큼의 픽스처가 없고(현재 1×B1·3×B2·2×B3뿐이라 형성 가능한 조합이 3개), 전체 로스터를 로드하면 적합에만 ~970 시뮬(약 100초)이 들어 단위 테스트로 부적합하다. 이 테스트가 검증하는 건 **엔진의 정확도가 아니라 탐색 기계장치가 품질을 잃지 않는지**이므로 스코어러는 주입된 것으로 충분하다.

스코어러에 **유닛 단독 모델이 원리적으로 볼 수 없는 페어 시너지**를 심어 둔다 — 캐스케이드가 실제로 마주하는 위험(시너지를 놓치는 것)을 그대로 재현하는 형태다.

```python
from app.cascade import Cascade, fit_surrogate
from app.deck_search import _score_batch, search_best_decks

# Per-unit values plus a synergy the unit-only surrogate cannot represent, so
# the test probes the cascade's actual failure mode rather than a model it fits
# perfectly.
_UNIT_VALUE = {f"q3-{i}": 100.0 + 10 * i for i in range(10)}
_UNIT_VALUE.update({f"q2-{i}": 50.0 + 5 * i for i in range(5)})
_UNIT_VALUE.update({f"q1-{i}": 30.0 + 3 * i for i in range(5)})
_SYNERGY = frozenset({"q1-0", "q3-9"})


def _quality_scorer(slugs):
    total = sum(_UNIT_VALUE.get(s, 0.0) for s in slugs)
    return total + (40.0 if _SYNERGY <= set(slugs) else 0.0)


def _quality_roster():
    tiers = {f"q1-{i}": 1 for i in range(5)}
    tiers.update({f"q2-{i}": 2 for i in range(5)})
    tiers.update({f"q3-{i}": 3 for i in range(10)})
    return roster_of(tiers)


def test_cascade_search_stays_within_five_percent_of_exhaustive(monkeypatch):
    """The cascade must not cost real damage. 95% is the same bar the recall
    gate held K to, so the test and the gate cannot drift apart."""
    patch_scorer(monkeypatch, _quality_scorer)
    roster, boss = _quality_roster(), BossProfile()

    exhaustive = search_best_decks(roster, boss, top_n=1)
    model = fit_surrogate(roster, boss,
                          lambda decks: _score_batch(decks, boss, None),
                          samples=150)
    assert model is not None, "roster too small to fit - widen _quality_roster"
    cascaded = search_best_decks(roster, boss, top_n=1, sim_budget=1,
                                 cascade=Cascade(model))

    assert cascaded[0]["total_damage"] >= 0.95 * exhaustive[0]["total_damage"]
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python3 -m pytest tests/test_deck_allocation.py -q -k within_five_percent`
Expected: FAIL — Task 6이 아직 안 됐다면 `TypeError: search_best_decks() got an unexpected keyword argument 'cascade'`. Task 6까지 끝난 상태라면 이 테스트는 바로 통과할 수 있다 — 그 경우 **통과 자체가 회귀 게이트**이므로 다음 스텝으로 넘어간다.

- [ ] **Step 3: 실패한다면 원인을 고친다**

이 테스트가 실패하면 캐스케이드가 실제로 품질을 잃고 있다는 뜻이다. 확인 순서: (a) `Cascade.top_k`가 Task 4에서 정한 값인지, (b) `widened_pool`이 `prune`의 선택을 실제로 포함하는지, (c) `fit_surrogate`가 `None`을 반환해 폴백만 타고 있는 건 아닌지. **테스트의 기준(95%)이나 `_SYNERGY` 크기를 낮춰 통과시키지 말 것** — 그건 게이트를 무력화하는 것이다.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python3 -m pytest tests/test_deck_allocation.py -q`
Expected: PASS

- [ ] **Step 5: 수용 측정 — 전후 비교**

```bash
python3 scripts/measure_allocation_phase_split.py --units 40
```

Expected: `search` 단계 비중이 통합 전 **91.5%**에서 크게 떨어지고 총 시뮬 수가 줄어야 한다. 78유닛 전체 비용은:

```bash
python3 scripts/measure_cascade_budget.py --units 78 --no-pairs --fit-decks 200
```

두 결과를 기록한다. **`search` 비중이 떨어지지 않았다면 통합이 실제로 작동하지 않은 것이다** — 커밋하지 말고 원인을 찾는다.

- [ ] **Step 6: 문서 갱신**

`docs/roadmap.md`의 캐스케이드 항목을 Phase 2 착지로 바꾸고, `docs/decisions.md`에 실측 전후 수치를 남긴다.

- [ ] **Step 7: Run the whole suite**

Run: `cd backend && python3 -m pytest -q`
Expected: 1248 passed, 3 skipped

- [ ] **Step 8: Commit**

```bash
git add backend/tests/test_deck_allocation.py docs/roadmap.md docs/decisions.md
git commit -m "Hold the cascade to 95% of the exhaustive search, and record the win

The test forces the cascade on a roster small enough to also search
exhaustively, and holds it to the same 95% bar the recall gate held K to, so
the two cannot drift apart."
```

---

## Self-Review

**Spec coverage:**

| 스펙 요구 | 태스크 |
|---|---|
| `cascade.py` 신규(적합/풀/랭킹) | 1, 2, 3, 6 |
| 티어별 계수 채움 | 3 |
| `prune`을 안전망으로 유지 | 3 (`widened_pool`이 prune을 먼저 넣음) |
| 요청 내 1회 적합 + 부분집합 재사용 | 7 (+ Task 1의 `covers` 테스트) |
| 요청 간 캐시(로스터 상태+보스 키) | 2 |
| 순서 카운트 조기 종료 | 5 |
| 검증 게이트 + K 결정 규칙 + 실패 허용 | 4 |
| `WIDE_TIER_CAPS` 고정 | 1(상수), 3(사용) |
| 폴백(예산 이하 / 표본 부족 / 미커버 로스터) | 1(None 반환), 6(`shortlist` None), 7(작은 로스터 미적합) |
| 품질 회귀 테스트 95% | 8 |
| 수용 측정(phase split 전후) | 8 |
| `best_completions` 범위 밖 | 어느 태스크도 건드리지 않음 ✓ |
| 플래그 없음 | 어느 태스크도 추가하지 않음 ✓ |

**Placeholder scan:** 남은 미확정 값은 Task 4 Step 4의 `DEFAULT_TOP_K = <측정값>` 하나뿐이며, 이는 의도된 측정 산출물이다 — 같은 태스크의 Step 3이 값을 고르는 규칙과 실패 시 행동까지 정의한다. Task 7·8의 테스트는 이 저장소에 실재하는 헬퍼(`roster_of`, `patch_scorer`, `real_five_roster`)만 쓰도록 확정했고, 필요한 로스터·스코어러는 코드로 전부 적어 두었다.

**작성 중 고친 것:** 초안의 Task 7 테스트는 가짜 유닛에 진짜 시뮬을 태워 깨졌을 것이고(`patch_scorer` 누락), Task 8은 실제 인코딩 스펙으로 티어 정원을 채울 수 없어(현재 1×B1·3×B2·2×B3) 성립하지 않았다. 둘 다 주입 스코어러 기반으로 바꿨다. Task 8의 스코어러에는 **유닛 단독 모델이 원리적으로 볼 수 없는 페어 시너지**를 심어, 캐스케이드의 실제 실패 모드를 겨냥하게 했다.

**Type consistency:** `SurrogateModel.coefficient/covers/score_combos`는 Task 1에서 정의되어 3(coefficient)·6(covers, score_combos)에서 같은 이름으로 쓰인다. `fit_surrogate`의 `score_orderings` 규약은 1·2·4·8에서 동일하다. `Cascade.shortlist(roster, boss, pool=None) -> list | None`은 6에서 정의되고 6(deck_search)·7(allocate_decks)에서 같은 형태로 소비된다. `_orderings_within_budget(roster, sim_budget) -> list | None`은 5에서 정의되어 5·6·7에서 일관되게 쓰인다. `SEARCH_SIM_BUDGET`은 7에서 도입되며 같은 스텝에서 `search_best_decks`의 기본값으로도 반영된다.
