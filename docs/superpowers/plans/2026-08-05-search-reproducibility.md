# 탐색 재현성 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 스왑 언덕오르기의 예산을 벽시계에서 **검토한 후보 교환 수**로 바꿔, 같은 로스터·같은 보스가 언제 어느 머신에서도 같은 덱 배분을 내게 한다.

**Architecture:** 예산의 단위만 바꾸는 것이 아니라 **역할**이 바뀐다 — 상한은 품질 노브가 아니라 폭주 방지 장치가 되고, 등반은 수렴까지 돈다. 후보 수로 과금하고 배치를 남은 몫까지 자르면, 상한이 물리는 지점까지 머신 독립이 된다. 수렴 여부는 `swap_converged`로 API를 타고 화면까지 올라간다.

**Tech Stack:** Python 3.14 / FastAPI / pytest (백엔드), React + TypeScript + Vitest (프론트)

**설계 근거:** `docs/superpowers/specs/2026-08-05-search-reproducibility-design.md` (커밋 `d3ca3695`)

## Global Constraints

- 브랜치는 **`wip/search-reproducibility`**. 트렁크는 `wip/scaffolding`이고 리모트에 `main`은 없다.
- 기준선(2026-08-05 실행 확인, 트렁크 `13ddd5b5`): 백엔드 **1905 passed / 3 skipped** · 프론트 **522 passed / 54 파일**. 테스트를 삭제하거나 축소하지 않는다 — 커버리지 축소는 실패보다 나쁘다.
- 백엔드 테스트: `cd backend && python3 -m pytest -q`. 프론트: `cd frontend && npm test`.
- 예산 파라미터 이름은 **`swap_budget`**, 상수 이름은 **`SWAP_CANDIDATE_BUDGET`**, 단위는 **검토한 후보 교환 수**(시뮬 수가 아니다).
- **`swap_budget=0`은 스왑 단계를 통째로 건너뛴다**는 기존 뜻을 유지한다. 백엔드 테스트 20여 곳이 이 뜻에 의존한다.
- 주석은 **무엇을·왜**만 쓴다. "예전엔 이랬다" 같은 이력은 쓰지 않는다 (`CLAUDE.md`).
- `deck_allocation.py`의 코드 주석은 영어, `docs/`와 프론트 사용자 문구는 한국어 — 각 파일의 기존 관례를 따른다.
- pre-commit 훅을 건너뛰지 않는다.

---

## File Structure

**수정:**
- `backend/app/deck_allocation.py` — 예산의 단위·역할 교체, 수렴 신호 생성
- `backend/app/api.py` — `RecommendRaidResponse.swap_converged`
- `backend/tests/test_deck_allocation.py` — 호출부 갱신, 벽시계 전용 헬퍼 삭제, 재현성 테스트 신설
- `backend/tests/test_deck_allocation_draft.py`, `backend/tests/test_elemental_interrupt_constraint.py` — 키워드 인자 갱신
- `scripts/measure_swap_budget.py` — 후보 단위로 재작성 (상수의 근거를 만드는 도구)
- `scripts/measure_swap_phase.py` — `_swap_pass`/`_try_swaps` 래퍼를 새 시그니처에 맞춤
- `frontend/src/types/recommend.ts`, `frontend/src/types/profile.ts`, `frontend/src/hooks/useRecommendRaid.ts`, `frontend/src/components/RecommendPanel.tsx`, `RaidResults.tsx`, `DraftResults.tsx` — 수렴 신호 배선 + 대기 문구
- `docs/decisions.md`, `docs/insights.md`, `docs/roadmap.md`

**확인만 (변경 없을 가능성이 높음):**
- `scripts/measure_allocation_phase_split.py`, `scripts/audit_swap_ordering.py` — `_swap_pass`를 감싸지만 위임만 한다

---

## Task 1: 예산의 단위를 후보 교환 수로 바꾼다

**Files:**
- Modify: `backend/app/deck_allocation.py:11`(import), `:37-58`(상수), `:161-163`(시그니처), `:285-297`, `:307-354`(`_swap_pass`), `:390-507`(`_try_swaps`)
- Modify: `backend/tests/test_deck_allocation.py` (호출부 다수 + 헬퍼 삭제)
- Modify: `backend/tests/test_deck_allocation_draft.py:51,98,115,215`
- Modify: `backend/tests/test_elemental_interrupt_constraint.py:231,244,255,268,302,322,343,372`

**Interfaces:**
- Consumes: 없음 (첫 태스크)
- Produces:
  - `SWAP_CANDIDATE_BUDGET: int` — `deck_allocation` 모듈 상수
  - `allocate_decks(roster, boss, num_decks=5, draft=None, locked=frozenset(), swap_budget=SWAP_CANDIDATE_BUDGET, workers=None, alternatives=None, cancel=None) -> dict` — 반환 dict는 이 태스크에서 바뀌지 않는다(`decks`, `leftover_slugs`)
  - `_swap_pass(decks, leftovers, boss, budget: int, locked=frozenset(), pool=None, batch=_MIN_SWAP_BATCH, cancel=None) -> bool` — 반환값은 **수렴 여부**
  - `_try_swaps(decks, scores, i, partner, j, boss, share: int, locked, pool, batch, gimmick_active=False) -> tuple[bool, int, bool]` — `(improved, used, exhausted)`

- [ ] **Step 1: 기준선을 눈으로 확인한다**

```bash
cd backend && python3 -m pytest -q
```

Expected: `1905 passed, 3 skipped`. 다르면 여기서 멈추고 보고한다 — 이 계획의 모든 숫자가 이 기준선 위에 있다.

- [ ] **Step 2: 상수를 교체한다**

`backend/app/deck_allocation.py`의 `SWAP_TIME_BUDGET_SEC` 블록(37-58행, 주석 포함 전체)을 **삭제**하고 그 자리에 넣는다:

```python
# How much of the swap-improvement climb one allocate_decks call may spend,
# counted in CANDIDATE EXCHANGES examined - not simulations. Charging per
# simulation would let the batch width (which scales with the worker count)
# decide WHERE a binding budget cuts, and a binding budget is exactly the moment
# reproducibility is needed. Counting candidates and truncating each batch to
# what is left makes the cut point the same on every machine.
#
# A runaway guard, not a quality knob. The climb reaches a local optimum and
# stops on its own: the accept test is a strict improvement on an objective that
# only rises, over a finite space of unit-to-deck assignments, so it cannot
# cycle. This number bounds only how long getting there may take - and the UI
# offers cancel besides (RecommendPanel.tsx's 취소 button).
#
# PROVISIONAL - large enough that it never binds, so the climb always runs to
# convergence. Task 5 of docs/superpowers/plans/2026-08-05-search-reproducibility.md
# replaces it with a measured value and the table that justifies it.
SWAP_CANDIDATE_BUDGET = 1_000_000
```

같은 파일 11행의 `import time`을 **삭제한다** — 이 태스크가 마지막 사용처를 없앤다.

- [ ] **Step 3: `allocate_decks`의 시그니처와 호출을 바꾼다**

161-163행:

```python
def allocate_decks(roster, boss: BossProfile, num_decks=5, draft=None,
                   locked=frozenset(), swap_budget=SWAP_CANDIDATE_BUDGET, workers=None,
                   alternatives=None, cancel=None):
```

285-297행의 주석과 호출:

```python
        # swap_budget caps the swap-improvement phase ONLY: greedy peeling above
        # and the final ordering polish below are unbudgeted, so a valid (if
        # unimproved) allocation is returned even with a budget of zero. The
        # hill-climb's DECISIONS stay sequential - each accepted swap changes the
        # state the next candidate is judged against - but the candidates it
        # judges are scored in batches through the same pool the peel used, which
        # is what lets the phase converge instead of being cut off mid-climb.
        cancel.check()
        _swap_pass(decks, remaining, boss, swap_budget, locked=locked, pool=pool,
                   batch=max(_MIN_SWAP_BATCH, worker_count * SWAP_BATCH_PER_WORKER),
                   cancel=cancel)
```

- [ ] **Step 4: `_swap_pass`를 통째로 교체한다**

307행부터 354행까지(함수 전체)를 다음으로 바꾼다:

```python
def _swap_pass(decks, leftovers, boss, budget, locked=frozenset(), pool=None,
               batch=_MIN_SWAP_BATCH, cancel=None):
    """Hill-climb: try unit swaps between two decks (and between a deck and the
    leftovers), re-scoring only the affected deck(s); keep a swap iff the summed
    total improves. Loops until a full pass finds no improvement or `budget`
    candidate exchanges have been examined. `locked` slugs are never chosen as a
    swap source, pinning a drafted seat.

    Returns whether the climb CONVERGED. "No improvement in the last pass" is
    not enough on its own: an item cut short by its share may simply not have
    reached the candidates that would have improved it, so a pass counts as
    conclusive only when every item also exhausted its candidate list.
    """
    if not decks:
        return True
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
    spent = 0
    improved = True
    complete = True
    while improved and spent < budget:
        improved = False
        complete = True
        for done, (i, j) in enumerate(items):
            # The longest phase in the run - it climbs until it converges or the
            # budget runs out - so it is asked per work item rather than only
            # once per pass.
            cancel.check()
            # An item may spend only its EQUAL SHARE of what is left, so a
            # budget that binds cuts every deck a little instead of being spent
            # entirely on the first one. Measured on Fienn's roster (2026-08-04,
            # 5 decks, gimmick on): deck 1's five items took the whole budget and
            # decks 2-5 got no swap AT ALL - which left a bench unit worth
            # +969,725,138 unseated beside deck 3. An item that runs out of
            # candidates before its share is up hands the rest to the items
            # behind it, so a climb that fits inside the budget converges exactly
            # as an unbudgeted one would.
            share = (budget - spent) // (len(items) - done)
            partner = leftovers if j is None else decks[j]
            gained, used, exhausted = _try_swaps(decks, scores, i, partner, j,
                                                 boss, share, locked, pool, batch,
                                                 gimmick_active)
            improved |= gained
            spent += used
            complete &= exhausted
    return not improved and complete
```

- [ ] **Step 5: `_try_swaps`의 시그니처·루프·반환을 바꾼다**

390-391행 (시그니처):

```python
def _try_swaps(decks, scores, i, partner, j, boss, share, locked, pool, batch,
               gimmick_active=False):
```

같은 함수 docstring의 배치 문단(406-411행)에 한 문장을 더한다:

```python
    Candidates are scored a batch at a time so a SimPool can fan them out. The
    walk over a scored batch keeps the serial rule exactly: accept the FIRST
    candidate that improves, in this order. An acceptance makes the rest of that
    batch stale - those scores describe a deck that no longer exists - so the
    loop re-batches from the next candidate instead of trusting them. Wasted
    scoring is bounded by the batch and rare in practice: measured on a 78-unit
    roster, under 1% of candidates are ever accepted. Batch width therefore never
    decides WHICH candidate is accepted, only how many are scored ahead of the
    acceptance - which is what lets a converged climb agree across machines with
    different core counts.
```

465-489행의 루프 머리와 예산 검사를 바꾼다. 기존:

```python
    width = 1 if j is None else 2      # decks re-scored per candidate
    improved = False
    start = 0
    while start < len(candidates):
        if time.monotonic() >= deadline:
            return improved
        chunk = candidates[start:start + batch]
```

새로:

```python
    width = 1 if j is None else 2      # decks re-scored per candidate
    improved = False
    start = 0
    used = 0
    while start < len(candidates) and used < share:
        # Truncating the chunk to what the share still allows is what keeps the
        # cut point off the machine: a wider batch would otherwise overshoot the
        # share by up to its own width.
        chunk = candidates[start:start + min(batch, share - used)]
```

487-489행 (미채택 경로):

```python
        if accepted is None:
            start += len(chunk)
            used += len(chunk)
            continue
```

496행 (채택 경로) 바로 뒤에 과금을 더한다:

```python
        start += accepted + 1
        used += accepted + 1
```

507행 (반환):

```python
    return improved, used, start >= len(candidates)
```

- [ ] **Step 6: 벽시계 전용 테스트 헬퍼를 삭제한다**

`backend/tests/test_deck_allocation.py` 192-222행의 `_ScoringClock` 클래스와 `patch_scoring_clock` 함수를 **삭제한다.** 둘 다 "예산이 벽시계라서" 존재하던 것이고, 후보 예산은 원하는 지점에서 정확히 물리므로 시계를 뺏을 이유가 없어진다. 7행의 `import time`도 삭제한다.

- [ ] **Step 7: 같은 파일의 호출부를 전부 갱신한다**

`backend/tests/test_deck_allocation.py`:

- `time_budget_sec=0.0` → `swap_budget=0` (69, 81, 327, 356, 475, 520, 530, 531, 573, 588, 612행)
- `time_budget_sec=30.0` → `swap_budget=10_000` (102행)
- `da._swap_pass(..., time.monotonic() + 30.0, ...)` → `da._swap_pass(..., 10_000, ...)` (134-135, 150-151, 249, 382-383, 408, 428, 451, 497-498행)
- 523-534행 `test_allocate_decks_workers_parity`의 주석에서 벽시계 언급을 고친다:

```python
def test_allocate_decks_workers_parity():
    # Real 5-spec roster (stubs can't cross the SimPool process/module
    # boundary); swap_budget=0 keeps this comparison on the peel alone. The
    # climb's own width-independence under a BINDING budget is asserted by
    # test_batch_width_never_changes_a_cut_off_climb_either.
    from tests.test_deck_search import real_five_roster, short_boss

    roster, boss = real_five_roster(), short_boss()
    serial = da.allocate_decks(roster, boss, num_decks=2, swap_budget=0)
    pooled = da.allocate_decks(roster, boss, num_decks=2, swap_budget=0, workers=2)
```

- 180-189행의 테스트를 이름째 바꾼다:

```python
def test_a_zero_budget_leaves_the_decks_untouched(monkeypatch):
    """allocate_decks relies on this to return a valid (if unimproved)
    allocation when the swap phase is given nothing to spend."""
    deck, bench = _swap_fixture()
    before = [u.slug for u in deck]
    patch_scorer(monkeypatch, _bench_scorer)

    da._swap_pass([deck], bench, BossProfile(), 0)

    assert [u.slug for u in deck] == before
```

- 225-232행의 기본값 테스트:

```python
def test_the_swap_budget_default_is_the_named_constant():
    """The climb's ceiling is a MEASURED number, and the measurement that chose
    it is written beside the constant. Every test in this file passes an
    explicit budget, so nothing else here would notice the default drifting back
    to a bare literal - and a literal in the signature is exactly how the number
    and the note justifying it come apart."""
    default = inspect.signature(da.allocate_decks).parameters["swap_budget"].default
    assert default is da.SWAP_CANDIDATE_BUDGET
```

- [ ] **Step 8: 잘리는 예산 테스트를 시계 없이 다시 쓴다**

255-294행 `test_a_binding_budget_still_reaches_the_last_deck`의 마지막 부분(282-294행)을 바꾼다. 픽스처와 `score`는 그대로 두고, `clock` 세 줄만 교체한다:

```python
    patch_scorer(monkeypatch, score)
    # Six work items ((0,1) (0,2) (0,bench) (1,2) (1,bench) (2,bench)), so a
    # budget of 60 gives each of them ten candidates - enough for the last one
    # to reach `w`, who is the first bench unit it judges. Spending it all on
    # the first item, the way an unfair split does, never gets there.
    converged = da._swap_pass(decks, bench, BossProfile(), 60)

    assert not converged, (
        "the budget never bound, so this fixture proves nothing about a climb "
        "that is cut off")
    assert "w" in [u.slug for u in decks[2]], (
        "the last deck never got a swap - the budget was spent before its turn")
```

- [ ] **Step 9: 나머지 두 테스트 파일의 키워드를 갱신한다**

`backend/tests/test_deck_allocation_draft.py`:
- 51행 `time_budget_sec=30.0` → `swap_budget=10_000`
- 98, 115, 215행 `time_budget_sec=0.0` → `swap_budget=0`

`backend/tests/test_elemental_interrupt_constraint.py`:
- 268, 302행 `time_budget_sec=30.0` → `swap_budget=10_000`
- 231, 244, 255, 322, 343, 372행 `time_budget_sec=0.0` → `swap_budget=0`

- [ ] **Step 10: 전체 스위트를 돌린다**

```bash
cd backend && python3 -m pytest -q
```

Expected: `1905 passed, 3 skipped` — 이 태스크는 동작을 바꾸지 않고 예산의 단위만 바꾼다. 실패가 남으면 고치기 전에 원인을 보고한다.

- [ ] **Step 11: 커밋**

```bash
git add backend/app/deck_allocation.py backend/tests/test_deck_allocation.py backend/tests/test_deck_allocation_draft.py backend/tests/test_elemental_interrupt_constraint.py
git commit -m "Budget the swap climb in candidate exchanges instead of seconds

A wall-clock deadline made the same roster and boss return different decks -
28.05 / 23.86 / 28.17B across three runs of one input. Candidates are counted
instead, each work item's batch truncated to the share it has left, so where a
binding budget cuts stops depending on the machine's core count. The ceiling
becomes a runaway guard rather than a quality knob; it is provisional here and
Task 5 measures the real one.

_swap_pass now reports whether the climb converged, which needs both halves:
no improvement in the last pass, AND every item having exhausted its candidate
list, since an item cut short by its share never saw the rest of its own.

The _ScoringClock test helper goes with the deadline it existed for - a
candidate budget binds exactly where the test asks it to."
```

---

## Task 2: 재현성을 못박는 테스트

**Files:**
- Modify: `backend/tests/test_deck_allocation.py` (신규 테스트 3종)

**Interfaces:**
- Consumes: Task 1의 `allocate_decks(swap_budget=...)`, `_swap_pass(...) -> bool`, `_try_swaps(...) -> (improved, used, exhausted)`
- Produces: 없음 (테스트만)

- [ ] **Step 1: 세 테스트를 쓴다**

`backend/tests/test_deck_allocation.py`의 `test_allocate_decks_workers_parity` **바로 뒤**에 넣는다:

```python
def test_batch_width_never_changes_a_cut_off_climb_either(monkeypatch):
    """The reproducibility guarantee, at the only point it can fail.

    Worker count reaches the climb as batch width (`worker_count *
    SWAP_BATCH_PER_WORKER`), and a CONVERGED climb agrees across widths whatever
    the budget is counted in - it runs out of improving swaps either way, which
    test_batch_width_never_changes_the_outcome already pins. What can disagree is
    a climb the budget CUTS: a wider batch consuming the budget faster stops
    somewhere else. Charging by how far the candidate walk advanced, and
    truncating each batch to the share that is left, makes the cut land on the
    same candidate at every width.
    """
    outcomes = []
    for batch in (1, 4, 64):
        decks = [[Unit(f"{p}1", 3), Unit(f"{p}2", 1), Unit(f"{p}3", 2),
                  Unit(f"{p}4", 3), Unit(f"{p}5", 3)] for p in "abc"]
        bench = [Unit(f"f{i}", 3) for i in range(11)]
        # Every f unit seated is worth more, so acceptances happen throughout -
        # the walk's accept path is where batch width could diverge.
        patch_scorer(monkeypatch, lambda slugs: 100.0 + 5.0 * len(
            [s for s in slugs if s.startswith("f")]))
        converged = da._swap_pass(decks, bench, BossProfile(), 40, batch=batch)
        outcomes.append((converged,
                         [[u.slug for u in deck] for deck in decks],
                         sorted(u.slug for u in bench)))

    assert outcomes[0][0] is False, (
        "the budget never bound, so this proves only what convergence already did")
    assert len(set(map(str, outcomes))) == 1, outcomes


def test_a_cut_off_climb_returns_the_same_allocation_twice(monkeypatch):
    """Same input, same answer - the whole point. Asserted where it used to
    fail: a budget that binds, so the run is decided by where the climb stopped
    rather than by where it converged."""
    def run():
        decks = [[Unit(f"{p}1", 3), Unit(f"{p}2", 1), Unit(f"{p}3", 2),
                  Unit(f"{p}4", 3), Unit(f"{p}5", 3)] for p in "abc"]
        bench = [Unit(f"f{i}", 3) for i in range(11)]
        patch_scorer(monkeypatch, lambda slugs: 100.0 + len(
            [s for s in slugs if s.startswith("f")]) * 5.0)
        converged = da._swap_pass(decks, bench, BossProfile(), 40)
        return converged, [[u.slug for u in deck] for deck in decks]

    first, second = run(), run()

    assert first[0] is False, "the budget never bound - nothing is being proven"
    assert first == second


def test_an_item_spends_no_more_than_its_share(monkeypatch):
    """The equal split is what keeps a binding budget from being eaten by deck
    1, so `used` has to respect it exactly - the batch is truncated for this
    reason and nothing else asserts the truncation directly.

    The deck is (1,2,3,3,3) and every bench unit a Burst 3, so only the three
    Burst-3 seats yield admissible candidates: 3 x 20 = 60, far more than the
    share of 7 can reach."""
    decks = [roster_of({"x1": 1, "x2": 2, "x3": 3, "x4": 3, "x5": 3})]
    bench = [Unit(f"b{i}", 3) for i in range(20)]
    scores = [100.0]

    calls = []

    def fake_score_batch(trials, boss, pool):
        calls.append(len(trials))
        return [1.0] * len(trials)

    monkeypatch.setattr(da, "_score_batch", fake_score_batch)
    improved, used, exhausted = da._try_swaps(
        decks, scores, 0, bench, None, BossProfile(), 7,
        frozenset(), None, 4)

    assert improved is False          # every trial scores 1.0, below the 100 baseline
    assert used == 7                  # exactly the share, never over
    assert exhausted is False         # 5 x 20 candidates, so 7 cannot finish them
    assert calls == [4, 3]            # the second batch is truncated to what is left
```

- [ ] **Step 2: 돌려서 통과하는지 본다**

```bash
cd backend && python3 -m pytest -q tests/test_deck_allocation.py
```

Expected: 전부 통과.

**왜 SimPool을 안 쓰는가** (2026-08-05, 실행 중 확인): 워커 수가 등반에 닿는 통로는 `batch = max(_MIN_SWAP_BATCH, worker_count * SWAP_BATCH_PER_WORKER)` **하나뿐**이다 — `SimPool._map`은 `executor.map`이라 순서를 보존하고 양쪽 다 같은 순수 `evaluate_deck`을 부른다. `_swap_pass`가 `batch`를 인자로 받으므로 폭을 직접 흔드는 쪽이 변수를 격리한다. (원래 이 자리에 `real_five_roster()`로 `workers=1` vs `workers=2`를 비교하는 테스트를 적었으나 **성립하지 않는다**: 그 픽스처는 정확히 5유닛이라 `num_decks=2`가 덱 하나에 빈 벤치를 만들어 어떤 예산에서도 스왑 후보가 0개다.)

예산 40이 물리지 않고 수렴하거나 세 폭의 결과가 갈리면 **픽스처를 맞추지 말고 보고한다** — 후자는 보장 자체가 깨진 것이다.

- [ ] **Step 3: 뮤테이션 — 테스트가 진짜로 잡는지 깨서 확인한다**

`deck_allocation.py`의 배치 잘라내기를 임시로 되돌린다:

```python
        chunk = candidates[start:start + batch]
```

```bash
cd backend && python3 -m pytest -q tests/test_deck_allocation.py
```

Expected: **`test_an_item_spends_no_more_than_its_share`가 실패**한다 (`calls == [4, 4]`, `used == 8`). 실패하지 않으면 그 테스트는 장식이므로 **되돌리지 말고 보고한다.**

확인했으면 `min(batch, share - used)`를 복구하고 다시 돌려 초록인지 본다.

- [ ] **Step 4: 커밋**

```bash
git add backend/tests/test_deck_allocation.py
git commit -m "Pin the reproducibility guarantee where it used to break

Three assertions the old budget could not carry: a cut-off climb agreeing
across worker counts, the same input twice giving the same allocation, and an
item spending exactly its share. The last one is what holds the batch
truncation in place - removing that one line turns its batch sizes from [4, 3]
into [4, 4], which was checked by doing it."
```

---

## Task 3: `swap_converged`를 백엔드에 배선한다

**Files:**
- Modify: `backend/app/deck_allocation.py:299-301`(`allocate_decks` 반환), `:588-615`(`recommend_from_draft`)
- Modify: `backend/tests/test_recommend_from_draft.py` (신규 테스트 2종)

**Interfaces:**
- Consumes: Task 1의 `_swap_pass(...) -> bool`
- Produces:
  - `allocate_decks(...)` 반환 dict에 `"swap_converged": bool` 추가
  - `recommend_from_draft(...)` 반환 dict에 `"swap_converged": bool` 추가 (실제로 돈 `allocate_decks` 호출들의 AND)

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`backend/tests/test_recommend_from_draft.py` 끝에 붙인다. 파일 상단의 기존 import·헬퍼 이름을 먼저 읽고 그것을 쓴다 — 아래는 `test_deck_allocation.py`와 같은 `roster_of`/`patch_scorer`를 쓴다고 가정한 형태이므로, 이 파일의 헬퍼 이름이 다르면 그쪽에 맞춘다.

```python
def test_a_converged_allocation_reports_that_it_converged(monkeypatch):
    """The flag is what the UI uses to decide whether to warn, so a run that
    finished must not carry the warning."""
    roster = roster_of({
        "a1": 1, "a2": 2, "a3": 3, "a4": 3, "a5": 3,
        "b1": 1, "b2": 2, "b3": 3, "b4": 3, "b5": 3,
    })
    patch_scorer(monkeypatch, lambda slugs: 100.0)

    out = da.recommend_from_draft(roster, BossProfile(), num_decks=2)

    assert out["swap_converged"] is True


def test_a_budget_that_binds_reports_that_it_did_not_converge(monkeypatch):
    """allocate_decks' flag has to survive the trip up through
    recommend_from_draft - including the branch that rebuilds `recommended`
    from within_draft, which carries only the keys it is handed."""
    roster = roster_of({
        "a1": 1, "a2": 2, "a3": 3, "a4": 3, "a5": 3,
        "b1": 1, "b2": 2, "b3": 3, "b4": 3, "b5": 3,
    })
    patch_scorer(monkeypatch, lambda slugs: 100.0)

    alloc = da.allocate_decks(roster, BossProfile(), num_decks=2, swap_budget=1)

    assert alloc["swap_converged"] is False
```

- [ ] **Step 2: 실패를 확인한다**

```bash
cd backend && python3 -m pytest -q tests/test_recommend_from_draft.py -k converged
```

Expected: FAIL — `KeyError: 'swap_converged'`

- [ ] **Step 3: `allocate_decks`가 플래그를 싣는다**

`deck_allocation.py` 293-301행:

```python
        cancel.check()
        converged = _swap_pass(decks, remaining, boss, swap_budget, locked=locked,
                               pool=pool,
                               batch=max(_MIN_SWAP_BATCH,
                                         worker_count * SWAP_BATCH_PER_WORKER),
                               cancel=cancel)

        summaries = [best_ordering_summary(units, boss, pool) for units in decks]
        return {"decks": summaries,
                "leftover_slugs": sorted(u.slug for u in remaining),
                "swap_converged": converged}
```

- [ ] **Step 4: `recommend_from_draft`가 접어서 올린다**

563-570행의 두 갈래 뒤에 누적 리스트를 만들고, 594-595행의 재조립과 614-615행의 반환을 바꾼다:

```python
    # Every allocate_decks call that actually ran counts: the answer the player
    # sees is only as complete as the least complete search behind it.
    converged = [recommended["swap_converged"]]

    within_draft = None
    baseline_total = None
    if _is_complete(draft, num_decks):
```

```python
        within_draft = _better(w, s)
        converged += [w["swap_converged"], s["swap_converged"]]
```

```python
        if _combined(within_draft) > _combined(recommended):
            recommended = {"decks": within_draft["decks"],
                           "leftover_slugs": _leftover_against(within_draft, roster),
                           "swap_converged": within_draft["swap_converged"]}
```

```python
    return {"recommended": recommended, "within_draft": within_draft,
            "baseline_total_damage": baseline_total, "pinned_by_deck": pinned_by_deck,
            "swap_converged": all(converged)}
```

- [ ] **Step 5: 통과를 확인하고 전체를 돌린다**

```bash
cd backend && python3 -m pytest -q
```

Expected: `1910 passed, 3 skipped` (1905 + Task 2의 3건 + 이 태스크의 2건)

- [ ] **Step 6: 커밋**

```bash
git add backend/app/deck_allocation.py backend/tests/test_recommend_from_draft.py
git commit -m "Report whether the swap climb converged

A cut-off climb is not just a shorter one: the equal split means each item
stops partway down its own candidate list and starts over from the front next
pass, so the tail is never seen. The player is owed that fact, so it travels
with the allocation.

recommend_from_draft folds it over every allocate_decks call that ran, and the
branch that rebuilds `recommended` out of within_draft carries it explicitly -
that dict is built key by key, so a flag not named there is silently dropped."
```

---

## Task 4: 계측·감사 스크립트를 새 단위에 맞춘다

**Files:**
- Modify: `scripts/measure_swap_budget.py` (후보 단위로 재작성)
- Modify: `scripts/measure_swap_phase.py:84-93, 127-128, 152-156`
- Verify: `scripts/measure_allocation_phase_split.py`, `scripts/audit_swap_ordering.py`

**Interfaces:**
- Consumes: Task 1·3의 `allocate_decks(swap_budget=...)`, `_swap_pass(...) -> bool`
- Produces: `python3 scripts/measure_swap_budget.py --budgets ...`가 후보 수를 받고 **수렴까지 쓴 후보 수**를 출력한다 (Task 5가 이 출력을 쓴다)

- [ ] **Step 1: `measure_swap_budget.py`를 후보 단위로 바꾼다**

44-51행의 `_timed_swap_pass`를 삭제하고 대신 넣는다:

```python
def _accounted_swap_pass(original, record):
    """Wrap _swap_pass to record what the climb actually spent and whether it
    converged. The candidates a run consumed is the number this script exists to
    produce - it is what the production ceiling is set from."""
    def wrapped(decks, leftovers, boss, budget, **kwargs):
        spent = {"candidates": 0}
        real_try = da._try_swaps

        def counting_try(*a, **kw):
            improved, used, exhausted = real_try(*a, **kw)
            spent["candidates"] += used
            return improved, used, exhausted

        da._try_swaps = counting_try
        started = time.perf_counter()
        try:
            converged = original(decks, leftovers, boss, budget, **kwargs)
            record.append((spent["candidates"], time.perf_counter() - started,
                           converged))
            return converged
        finally:
            da._try_swaps = real_try
    return wrapped
```

57-59행의 `--budgets` 기본값과 도움말:

```python
    p.add_argument("--budgets", default="0,2000,8000,40000",
                   help="swap budgets in CANDIDATE EXCHANGES, comma separated. "
                        "0 is the peel-only baseline; a run that converges "
                        "reports what it spent, which is the number the "
                        "production ceiling is chosen from")
```

83행: `budgets = [float(b) for b in ...]` → `budgets = [int(b) for b in args.budgets.split(",")]`

101-128행의 표를 후보 열로 바꾼다:

```python
    print(f"{'budget':>9} {'combined total':>18} {'vs peel':>9} "
          f"{'candidates':>11} {'swap took':>10} {'end-to-end':>11}  converged")

    baseline = None
    original = da._swap_pass
    for budget in budgets:
        record = []
        da._swap_pass = _accounted_swap_pass(original, record)
        started = time.perf_counter()
        try:
            out = da.allocate_decks(specs, boss, num_decks=args.decks,
                                    swap_budget=budget, workers=workers)
        finally:
            da._swap_pass = original
        # What the player actually waits for: the peel is unbudgeted, so a
        # bigger swap budget does not buy time one-for-one.
        end_to_end = time.perf_counter() - started
        total = sum(d["total_damage"] for d in out["decks"])
        if baseline is None:
            baseline = total
        spent, took, converged = record[0] if record else (0, 0.0, True)
        print(f"{budget:>9,} {total:>18,.0f} {total / baseline - 1:>+8.2%} "
              f"{spent:>11,} {took:>9.1f}s {end_to_end:>10.1f}s  "
              f"{'yes' if converged else 'NO - cut off'}", flush=True)
```

모듈 docstring의 `Usage` 줄도 새 기본값으로 고친다:

```
    python3 scripts/measure_swap_budget.py [--budgets 0,2000,8000,40000]
```

- [ ] **Step 2: `measure_swap_phase.py`의 래퍼를 맞춘다**

84-93행:

```python
    def wrap_pass(self, func, budget):
        def wrapped(decks, leftovers, boss, candidate_budget, **kwargs):
            self.started = time.perf_counter()
            self.candidates_per_pass = _full_pass_candidates(decks, leftovers)
            try:
                return func(decks, leftovers, boss, candidate_budget, **kwargs)
            finally:
                self.elapsed = self.since_start()
                self.hit_budget = self.candidates_spent >= budget
        return wrapped
```

69-82행의 `wrap_try`가 이제 3-튜플을 받으므로 소모량도 센다:

```python
    def wrap_try(self, func):
        """Attribute a _try_swaps call's sims to the kind of swap it tries
        (`j is None` means the partner is the leftover bench), and checkpoint
        the summed score it leaves behind."""
        def wrapped(decks, scores, i, partner, j, *args, **kwargs):
            before = list(scores)
            self.kind = "leftover" if j is None else "pair"
            try:
                improved, used, exhausted = func(decks, scores, i, partner, j,
                                                 *args, **kwargs)
                self.candidates_spent += used
                return improved, used, exhausted
            finally:
                self.kind = None
                self.accepted += sum(1 for b, a in zip(before, scores) if a != b)
                self.checkpoints.append((self.since_start(), sum(scores)))
        return wrapped
```

`__init__`(46-54행)에 `self.candidates_spent = 0`과 `self.hit_budget = False`를 더한다.

127-128행:

```python
    p.add_argument("--budget", type=int, default=40_000,
                   help="swap phase budget in candidate exchanges (default 40000)")
```

155-156행:

```python
    da.allocate_decks(specs, boss, num_decks=args.decks,
                      swap_budget=args.budget, workers=workers)
```

145-147행의 출력 문구에서 `swap budget {args.budget:.0f}s` → `swap budget {args.budget:,} candidates`. 파일 뒷부분에 `hit_deadline`을 읽는 곳이 있으면 `hit_budget`으로 바꾼다.

- [ ] **Step 3: 나머지 두 스크립트를 확인한다**

```bash
cd C:/Users/fienn/Desktop/NikkeDeckBuilder && grep -n "time_budget_sec\|deadline\|hit_deadline" scripts/*.py
```

Expected: `measure_allocation_phase_split.py`와 `audit_swap_ordering.py`는 `_swap_pass`를 위임만 하므로 `deadline`이라는 **이름**만 남아 있을 수 있다. 남아 있으면 `budget`으로 고친다. `time_budget_sec` 호출이 남아 있으면 `swap_budget`으로 고친다. 아무것도 안 걸리면 그대로 둔다.

- [ ] **Step 4: 스크립트가 실제로 도는지 확인한다**

```bash
cd C:/Users/fienn/Desktop/NikkeDeckBuilder && python3 scripts/measure_swap_budget.py --budgets 0,500 --decks 2
```

Expected: 두 줄이 나오고 `candidates` 열이 채워진다. 예산 0줄은 `candidates` 0, `converged yes`.

- [ ] **Step 5: 커밋**

```bash
git add scripts/measure_swap_budget.py scripts/measure_swap_phase.py
git commit -m "Measure the swap budget in the unit it is now spent in

measure_swap_budget's job changed with the budget: the number the production
ceiling is chosen from is no longer 'how many seconds did it take' but 'how
many candidates did convergence cost', so the run reports that directly and
takes its converged verdict from _swap_pass rather than inferring it from
elapsed time against the budget."
```

---

## Task 5: 계측하고 상한을 확정한다 (Fienn 승인 게이트)

**Files:**
- Modify: `backend/app/deck_allocation.py` (`SWAP_CANDIDATE_BUDGET`의 값과 근거 주석)

**Interfaces:**
- Consumes: Task 4의 `measure_swap_budget.py`
- Produces: 측정으로 정해진 `SWAP_CANDIDATE_BUDGET`과 그 옆의 근거 표

- [ ] **Step 1: 수렴 비용을 잰다 (속성저지 ON — 가장 무거운 조건)**

```bash
cd C:/Users/fienn/Desktop/NikkeDeckBuilder && python3 scripts/measure_swap_budget.py --element Fire --elemental-interrupt --decks 5 --workers auto --budgets 0,2000,8000,40000
```

측정 조건은 현 상수의 근거와 **같게** 둔다(Fienn 로스터 · 5덱 · Fire 보스 = 수냉 약점 · def 31,784 · 180초 · 코어 맞힘). 40000줄이 `converged yes`로 나와야 하고, 그 줄의 `candidates`가 **수렴 비용**이다. `NO - cut off`이면 `--budgets`에 더 큰 값을 붙여 다시 돈다.

- [ ] **Step 2: 속성저지 OFF도 잰다**

```bash
cd C:/Users/fienn/Desktop/NikkeDeckBuilder && python3 scripts/measure_swap_budget.py --element Fire --decks 5 --workers auto --budgets 0,40000
```

- [ ] **Step 3: 빈자리만 모드의 대기시간을 잰다 (Task 7의 문구용)**

`recommend_from_draft`가 `allocate_decks`를 세 번 부르는 경로다. 예산은 호출당이므로 **상수와는 무관**하고, 재는 이유는 문구 하나뿐이다.

```bash
cd C:/Users/fienn/Desktop/NikkeDeckBuilder && python3 scripts/profile_recommend_allocation.py --no-profile
```

Expected: Phase B가 `scratch` / `warm` / `within_draft` 각각의 벽시계를 찍는다. 합계를 적어 둔다.

- [ ] **Step 4: 두 숫자를 Fienn에게 보고하고 배수를 받는다 — 여기서 멈춘다**

보고할 것: 속성저지 ON/OFF의 수렴 후보 수와 그때의 벽시계, 전부최적화·빈자리만 끝-끝 대기, 그리고 추천(관측 수렴량의 **5배**). 추천 근거는 벤치 크기다 — 지금 로스터는 78유닛(벤치 ~53)이고 전 캐릭터 보유자는 벤치가 ~134라 항목당 후보가 2.5배쯤 되며, 패스 수 증가까지 감안하면 3~5배다. **이건 추정이지 측정이 아니다.**

**Fienn의 답을 받기 전에는 다음 스텝으로 가지 않는다.**

- [ ] **Step 5: 상수와 근거 표를 확정한다**

Task 1이 넣은 PROVISIONAL 주석 블록을 지우고 실측 표로 바꾼다. 아래의 `<...>`는 Step 1~3에서 **실제로 관측한 값**으로 채운다 — 추정치를 적지 않는다.

```python
# How much of the swap-improvement climb one allocate_decks call may spend,
# counted in CANDIDATE EXCHANGES examined - not simulations. Charging per
# simulation would let the batch width (which scales with the worker count)
# decide WHERE a binding budget cuts, and a binding budget is exactly the moment
# reproducibility is needed. Counting candidates and truncating each batch to
# what is left makes the cut point the same on every machine.
#
# A runaway guard, not a quality knob. The climb reaches a local optimum and
# stops on its own: the accept test is a strict improvement on an objective that
# only rises, over a finite space of unit-to-deck assignments, so it cannot
# cycle. This number bounds only how long getting there may take - and the UI
# offers cancel besides (RecommendPanel.tsx's 취소 button).
#
# Measured by scripts/measure_swap_budget.py on Fienn's roster (78 usable,
# 5 decks, Fire boss / 수냉 약점, DEF 31,784, 180 s):
#
#     gimmick   candidates to converge   swap took   end-to-end
#          on              <...>            <...>s      <...>s
#         off              <...>            <...>s      <...>s
#
# The ceiling is <N>x the heavier of those. Roster size is what moves the
# number - candidate lists scale with the bench, and a player who owns every
# unit has one about 2.5x this roster's - so the multiple is headroom for a
# roster nobody has measured, not for this one. Caveat: ONE roster.
#
# Candidates, not seconds, so what this costs in wall clock depends on the
# machine: <...>s on Fienn's at workers=auto.
SWAP_CANDIDATE_BUDGET = <값>
```

- [ ] **Step 6: 스위트를 돌린다**

```bash
cd backend && python3 -m pytest -q
```

Expected: `1910 passed, 3 skipped`. `test_the_swap_budget_default_is_the_named_constant`가 상수를 잡고 있으므로 이름이 어긋나면 여기서 걸린다.

- [ ] **Step 7: 커밋**

```bash
git add backend/app/deck_allocation.py
git commit -m "Set the swap ceiling from what convergence actually costs

Measured on Fienn's roster with the gimmick on and off; the number beside the
constant is the table it came from. The multiple over the observed cost is
headroom for a bench larger than any roster measured, since candidate lists
scale with it - not slack for this one, which converges well inside."
```

---

## Task 6: 수렴 신호를 화면까지 올린다

**Files:**
- Modify: `backend/app/api.py:137-144`, `:414-422`
- Modify: `frontend/src/types/recommend.ts:115-129`
- Modify: `frontend/src/types/profile.ts:23-30`
- Modify: `frontend/src/hooks/useRecommendRaid.ts`
- Modify: `frontend/src/components/RecommendPanel.tsx:76-90, 191-220`
- Modify: `frontend/src/components/RaidResults.tsx`, `DraftResults.tsx:20-34, 107`
- Modify: `frontend/src/hooks/useRecommendRaid.test.ts`, `frontend/src/components/RaidResults.test.tsx`

**Interfaces:**
- Consumes: Task 3의 `recommend_from_draft(...)["swap_converged"]`
- Produces: `RecommendRaidResponse.swap_converged: boolean`, `StoredResult.swapConverged?: boolean`, `RaidResults`/`DraftResults`의 `swapConverged?: boolean` prop

- [ ] **Step 1: 백엔드 응답에 싣는다**

`backend/app/api.py` 137-144행:

```python
class RecommendRaidResponse(BaseModel):
    decks: list[RaidDeck]
    combined_total_damage: float
    excluded_slugs: list[str]
    leftover_slugs: list[str]
    within_draft: DraftAllocation | None = None
    baseline_total_damage: float | None = None
    # 탐색이 상한에 걸리지 않고 끝까지 갔는지. 기본 True - 이 필드를 모르는
    # 클라이언트에게 경고를 띄우지 않는다.
    swap_converged: bool = True
    engine_version: str
```

414-422행의 생성자에 한 줄:

```python
        leftover_slugs=rec["leftover_slugs"],
        within_draft=within,
        baseline_total_damage=out["baseline_total_damage"],
        swap_converged=out["swap_converged"],
        engine_version=engine_version(),
```

- [ ] **Step 2: 백엔드 응답 테스트를 더한다**

`backend/tests/test_api_recommend_raid_draft.py`에는 이미 `/api/recommend-raid`로 200을 받는 테스트가 있다. **그 테스트의 요청 구성(클라이언트 생성 + json 본문)을 그대로 복사해** 파일 끝에 새 테스트를 만들고, 단언만 아래 두 줄로 바꾼다. 요청 본문을 새로 지어내지 않는다 — 이 테스트가 확인하려는 것은 요청 형식이 아니라 응답에 필드가 실렸는지다.

```python
def test_the_raid_response_says_whether_the_search_converged():
    """The client only warns when this is False, so it has to arrive at all -
    and an ordinary request, which converges, must not carry the warning."""
    # ... 위 테스트와 똑같은 client / 요청 본문 ...
    assert response.status_code == 200
    assert response.json()["swap_converged"] is True
```

```bash
cd backend && python3 -m pytest -q tests/test_api_recommend_raid_draft.py
```

- [ ] **Step 3: 프론트 타입에 더한다**

`frontend/src/types/recommend.ts` 115-129행의 인터페이스에:

```typescript
  baseline_total_damage: number | null // the user's exact drafted groupings scored;
  // non-null only for a COMPLETE draft. Monotone guarantee (complete draft):
  // baseline_total_damage <= sum(within_draft.decks.total_damage) <= combined_total_damage
  // 탐색이 상한에 걸리지 않고 끝까지 갔는지. false면 더 나은 배분이 남아 있을 수 있다.
  swap_converged: boolean
```

`frontend/src/types/profile.ts` 23-30행:

```typescript
export interface StoredResult {
  decks: RaidDeck[]
  combinedTotalDamage: number
  excludedSlugs: string[]
  leftoverSlugs: string[]
  withinDraft: DraftAllocation | null
  baselineTotalDamage: number | null
  /** 없을 수 있다 — 이 필드가 생기기 전에 저장된 결과. 없으면 경고하지 않는다. */
  swapConverged?: boolean
}
```

- [ ] **Step 4: 훅에 상태를 더한다**

`frontend/src/hooks/useRecommendRaid.ts`:

```typescript
  baselineTotalDamage: number | null
  /** 탐색이 상한에 걸리지 않고 끝까지 갔는지. */
  swapConverged: boolean
```

```typescript
  const [baselineTotalDamage, setBaselineTotalDamage] = useState<number | null>(null)
  const [swapConverged, setSwapConverged] = useState(true)
```

```typescript
          setBaselineTotalDamage(response.baseline_total_damage)
          setSwapConverged(response.swap_converged)
```

```typescript
    baselineTotalDamage,
    swapConverged,
    error,
```

`frontend/src/hooks/useRecommendRaid.test.ts`의 응답 목 두 곳(65-67행, 101-109행)에 `swap_converged: true`를 더한다.

- [ ] **Step 5: 결과 컴포넌트가 경고를 낸다**

`frontend/src/components/RaidResults.tsx`의 props에:

```typescript
  /** Usable units the allocation left out of every deck. */
  leftoverSlugs?: string[]
  /** false일 때만 경고한다 — 없으면(옛 저장 결과) 아무 말도 하지 않는다. */
  swapConverged?: boolean
```

```typescript
export function RaidResults({
  decks,
  combinedTotalDamage,
  excludedSlugs = [],
  leftoverSlugs = [],
  swapConverged,
  ...lookups
}: RaidResultsProps) {
```

기존 `raid-results__note` 문단 **바로 뒤**에 넣는다:

```tsx
      {swapConverged === false && (
        <p className="raid-results__note" role="status">
          탐색이 상한에 걸려 끝까지 가지 못했어요. 더 나은 배분이 남아 있을 수 있어요.
        </p>
      )}
```

`frontend/src/components/DraftResults.tsx` 20-34행의 props에 같은 줄을 더하고, 구조분해에 `swapConverged`를 넣고, 107행의 `<RaidResults ...>`에 `swapConverged={swapConverged}`를 넘긴다.

- [ ] **Step 6: 컴포넌트 테스트를 더한다**

`frontend/src/components/RaidResults.test.tsx`에. `decks`는 이 파일이 29·41·49행에서 이미 쓰는 픽스처를 **그대로 재사용**하고, `screen`은 파일 상단의 기존 import를 쓴다 — 새로 만들지 않는다:

```tsx
  it('탐색이 잘렸을 때만 경고한다', () => {
    // decks: 이 파일의 기존 픽스처
    const { rerender } = render(
      <RaidResults decks={decks} combinedTotalDamage={100} swapConverged={false} />,
    )
    expect(screen.getByText(/상한에 걸려 끝까지 가지 못했어요/)).toBeInTheDocument()

    rerender(<RaidResults decks={decks} combinedTotalDamage={100} swapConverged={true} />)
    expect(screen.queryByText(/상한에 걸려 끝까지 가지 못했어요/)).not.toBeInTheDocument()

    rerender(<RaidResults decks={decks} combinedTotalDamage={100} />)
    expect(screen.queryByText(/상한에 걸려 끝까지 가지 못했어요/)).not.toBeInTheDocument()
  })
```

`decks`의 객체 모양은 같은 파일 위쪽의 기존 픽스처를 그대로 재사용한다 — 먼저 읽고 맞춘다.

- [ ] **Step 7: 캐시 경로에 배선한다**

`frontend/src/components/RecommendPanel.tsx` 76-90행의 `toStoredResult`:

```typescript
const toStoredResult = (raid: {
  decks: StoredResult['decks']
  combinedTotalDamage: number
  excludedSlugs: string[]
  leftoverSlugs: string[]
  withinDraft: StoredResult['withinDraft']
  baselineTotalDamage: number | null
  swapConverged: boolean
}): StoredResult => ({
  decks: raid.decks,
  combinedTotalDamage: raid.combinedTotalDamage,
  excludedSlugs: raid.excludedSlugs,
  leftoverSlugs: raid.leftoverSlugs,
  withinDraft: raid.withinDraft,
  baselineTotalDamage: raid.baselineTotalDamage,
  swapConverged: raid.swapConverged,
})
```

191행의 구조분해 끝에 `swapConverged`를 더하고, 197-204행의 `toStoredResult({...})` 인자에 `swapConverged`를 더하고, 213행부터의 의존성 배열에도 `swapConverged`를 더한다.

653-663행과 664-676행의 `<RaidResults>`·`<DraftResults>`에 각각 한 줄:

```tsx
            leftoverSlugs={displayResult.leftoverSlugs}
            swapConverged={displayResult.swapConverged}
```

- [ ] **Step 8: 프론트 스위트를 돌린다**

```bash
cd frontend && npm test
```

Expected: 522 + 신규 1건 = **523 passed**. 타입 오류가 나면 `npm run build`로 확인한다.

- [ ] **Step 9: 커밋**

```bash
git add backend/app/api.py backend/tests/test_api_recommend_raid_draft.py frontend/src
git commit -m "Tell the player when the search stopped short

The flag defaults to true on the wire and is optional in the stored result, so
neither an older client nor a result cached before this field existed shows a
warning it has no evidence for. The copy says a better allocation may remain
rather than that this one is worse: a cut-off climb stops partway down each
item's candidate list, so what it missed is unseen, not rejected."
```

---

## Task 7: 대기 문구 — 문자열은 유지, 주석만 갱신

**Fienn 결정 (2026-08-05, Task 5 게이트에서):** 실측은 전부최적화 **182초** ·
빈자리만 **227초**(≈3~4분)인데, 사용자 문구 **"보통 2~5분"은 그대로 둔다.**
벽시계 상한이 사라져 느린 머신에서 더 걸리는 것이 이제 실제 위험이고, 넓은 밴드가
그 몫을 한다 — 실측에 딱 맞춰 좁히면 코어 적은 머신에서 거짓이 된다. 그래서 아래
Step 2(테스트 세 곳)는 **하지 않는다.**

남는 것은 **그 위의 코드 주석 하나**다. 사라진 `SWAP_TIME_BUDGET_SEC`을 이름으로
지목하고 2026-08-04 수치를 인용하고 있어 지금은 거짓이다. 새 주석은 새 상수·새
실측을 싣고, **문구의 폭이 실측보다 넓은 이유**를 적어 다음 사람이 3~4분으로
좁히지 않게 한다.

**Files:**
- Modify: `frontend/src/components/RecommendPanel.tsx` — 진행 문구 위의 JSX 주석만
- 테스트 변경 없음 (`App.test.tsx`·`RecommendPanel.test.tsx`의 `/2~5분/` 셋은 그대로 통과)

**Interfaces:**
- Consumes: Task 5의 끝-끝 실측과 수렴 후보 수
- Produces: 없음

<details>
<summary>원래 계획의 Step 1~2 (문자열을 3~4분으로 바꾸는 안) — 미채택</summary>

- [ ] **Step 1: 문구를 바꾼다**

`RecommendPanel.tsx` 605-616행. `<A>`·`<B>`는 Task 5 Step 3에서 **실제로 잰** 분 단위 값으로 채운다:

```tsx
        {(mode === 'raid' || mode === 'draft') && raid.status === 'loading' && (
          <p className="recommend-form__progress" role="status">
            {/* 실측(Fienn 로스터 78기·5덱, 2026-08-05): 전부 최적화 <A>초,
                편성이 꽉 찬 빈자리만 최적화 <B>초 — 후자는 배분을 세 번 돌린다
                (recommend_from_draft의 recommended + within_draft 둘). 스왑 단계
                상한은 backend/app/deck_allocation.py의 SWAP_CANDIDATE_BUDGET인데
                단위가 후보 수라 벽시계로 환산하면 머신마다 다르다. 개선이 끊기면
                상한을 다 쓰지 않고 끝나므로 얇은 로스터는 훨씬 빠르다. */}
            {mode === 'raid' ? '전부 최적화 중' : '빈자리만 최적화 중'} — 수천 번의
            시뮬레이션을 실행하며 보통 <A~B>분이 걸려요. 머신 성능에 따라 더 걸릴 수
            있어요. 아직 진행 중이니 완료되면 버튼이 다시 활성화돼요.
          </p>
        )}
```

- [ ] **Step 2: 문구를 무는 테스트 세 곳을 맞춘다**

`frontend/src/App.test.tsx:211`, `:313`, `frontend/src/components/RecommendPanel.test.tsx:416`의 `/2~5분/`을 새 값의 정규식으로 바꾼다. 셋 다 같은 문구를 보므로 값이 어긋나지 않게 한 번에 고친다.

</details>

- [ ] **Step 1: 주석을 갱신한다**

`RecommendPanel.tsx`의 진행 문구 위 JSX 주석을 새 상수·새 실측으로 바꾸고, 문구의
폭이 실측보다 넓은 이유를 적는다. **`보통 2~5분` 문자열은 건드리지 않는다.**

- [ ] **Step 2: 낡은 상수 이름이 남아 있지 않은지 확인한다**

```bash
grep -rn "SWAP_TIME_BUDGET_SEC" --include="*.py" --include="*.ts" --include="*.tsx" backend frontend scripts
```

Expected: 매치 없음.

- [ ] **Step 3: 프론트 스위트를 돌린다**

```bash
cd frontend && npm test
```

Expected: **523 passed** — 주석만 바꿨으므로 움직이면 안 된다.

- [ ] **Step 4: 커밋**

```bash
git add frontend/src
git commit -m "Say how long the wait is now, and that the machine decides

The climb runs to convergence instead of to a clock, so the ceiling no longer
promises an upper bound in seconds - on fewer cores the same search simply
takes longer. The copy says so; without that line it is merely false on a
slower machine."
```

---

## Task 8: 문서

**Files:**
- Modify: `docs/decisions.md` (새 항목을 파일 맨 위 최신 항목 자리에)
- Modify: `docs/insights.md`
- Modify: `docs/roadmap.md`

**Interfaces:**
- Consumes: Task 5의 측정값
- Produces: 없음

- [ ] **Step 1: `docs/decisions.md`에 새 항목을 쓴다**

기존 "스왑 예산: 항목별 균등 배분 + 상한 45초 → 180초"(145행) 항목은 **고치지 않는다.** 그 항목의 대안 (b)가 채택된 것이므로 새 항목이 뒤집는 형태로 쓴다 (ADR 관례). 아래 골격에 Task 5의 실측을 채운다:

```markdown
## 스왑 예산을 벽시계에서 후보 교환 수로 — 상한은 폭주 방지용이 되고 등반은 수렴까지 간다

- Date: 2026-08-05
- Context: 같은 로스터·같은 보스로 추천을 두 번 눌러도 다른 덱이 나온다(45초 3회
  = 28.05 / 23.86 / 28.17B). 탐색의 비결정 요소는 스왑 단계의 벽시계 데드라인
  하나뿐이고, 나머지는 전부 결정적이다 — 이건 추론이 아니라 실측이다:
  `PYTHONHASHSEED` 1과 2에서 수렴하는 배분이 마지막 자리까지 같았다
  (`6089389733.91905`). 아래 「미채택 대안 (b)」로 남겨둔 항목이 이것이다.
- Decision (Fienn, 2026-08-05): **후보 교환 수로 과금하고 수렴까지 돌린다.**
  상한 `SWAP_CANDIDATE_BUDGET = <값>`은 품질 노브가 아니라 폭주 방지 장치다.
- Why 후보 수인가: 시뮬 수로 세면 배치 폭(워커 수에 비례)이 **상한이 물리는
  지점**을 정하는데, 물리는 그 순간이 정확히 재현성이 필요한 순간이다. 후보 수로
  세고 배치를 남은 몫까지 자르면 그 지점이 머신 독립이 된다.
- Why 상한을 잃어도 안전한가: 등반은 반드시 끝난다 — 수용 조건이 강부등호라 총딜이
  단조 증가하고 상태공간이 유한하다. 상한은 정확성이 아니라 인내심 장치이고,
  UI에 취소 버튼이 있다.
- 공짜로 따라온 것: 배치 폭은 **어느 후보가 채택되는지를 바꾸지 않는다**. 그래서
  수렴하면 코어 수가 다른 머신도 같은 답을 낸다.
- Alternatives considered: **(a) 벽시계 비상 상한 병행** — 잡히는 순간이 곧
  재현성이 필요한 순간이라 보장을 잃는다. **(b) GPU** — 엔진이 이벤트 리스트
  시뮬이라 모양이 안 맞고 등반의 순간 동시성이 ~44 시뮬이며, 결정적으로 CPU/GPU
  부동소수점 차이가 재현성 축을 새로 연다. **(c) 진행률 표시** — 값어치는 있으나
  스트리밍/폴링이 필요해 별건.
- Consequences: <Task 5의 대기시간 실측>. 상한에 걸린 런은 `swap_converged=false`로
  화면에 알린다. 백엔드 1905 → 1911 passed / 3 skipped, 프론트 522 → 523.
  캐비엇: **로스터 하나**에서 고른 숫자다.
```

- [ ] **Step 2: `docs/insights.md`에 성질을 남긴다**

```markdown
### 배치 폭은 어느 후보가 채택되는지를 바꾸지 않는다

`_try_swaps`는 후보를 고정 순서로 훑어 **처음 개선하는 것**을 받아들이고, 배치는
몇 개를 미리 채점하느냐만 정한다(채택 뒤의 꼬리는 버려진다). 그래서 배치 폭은
낭비 채점량만 바꾸고 결과는 안 바꾼다 — **수렴한 등반은 코어 수가 다른 머신에서도
같은 답**을 낸다.

이 성질이 예산의 단위를 정했다. 시뮬 수로 과금하면 배치 폭이 소모 속도를 바꿔
**상한이 물리는 지점**이 머신마다 달라지는데, 물리는 그 순간이 정확히 재현성이
필요한 순간이다. 후보 수로 과금하고 배치를 남은 몫까지 자르면 그 지점까지 닫힌다.

**"비결정 요소는 하나뿐"은 실측으로 확인할 수 있다.** 파이썬은 프로세스마다 문자열
해시를 무작위화하므로, 집합 순회가 순서 결정에 닿는 곳이 하나라도 있으면 그 주장은
거짓이 된다. `PYTHONHASHSEED`를 달리해 두 번 돌려 비교하면 코드를 다 읽지 않고도
판정된다 (2026-08-05: 수렴 배분이 `6089389733.91905`까지 일치).
```

- [ ] **Step 3: `docs/roadmap.md`를 갱신한다**

- 994행 "배분 탐색의 폭이 ±5%다" 항목에 한 줄을 더한다: 그 항목이 지목한 축 중 **스왑 예산 쪽은 닫혔다**(예산이 더 이상 어느 국소최적에 앉을지를 정하지 않는다). 남은 축은 그리디 peel의 근시안과 대리모델의 unit-only 한계다.
- 1106행의 `SWAP_TIME_BUDGET_SEC = 180` 언급을 `SWAP_CANDIDATE_BUDGET = <값>`으로 고친다.
- 새 완료 항목으로 이번 작업을 적고 기준선을 갱신한다.

- [ ] **Step 4: 커밋**

```bash
git add docs/decisions.md docs/insights.md docs/roadmap.md
git commit -m "docs: record the budget's change of unit and of role"
```

---

## Task 9: 끝-끝 확인

**Files:** 없음 (검증만)

- [ ] **Step 1: 두 스위트를 돌린다**

```bash
cd backend && python3 -m pytest -q
cd ../frontend && npm test
```

Expected: 백엔드 `1911 passed, 3 skipped`(1905 + Task 2의 3 + Task 3의 2 + Task 6의 1), 프론트 `523 passed`.

- [ ] **Step 2: 실제 앱에서 같은 답이 두 번 나오는지 본다**

`/verify` 스킬로 백엔드를 띄우고 실제 로스터로 **전부 최적화를 두 번** 돌려 5덱 구성과 합계가 같은지 확인한다. 단위 테스트는 작은 픽스처에서만 도므로, 78유닛·5덱에서 재현되는지는 끝-끝으로만 알 수 있다.

- [ ] **Step 3: 결과를 보고한다**

두 스위트의 숫자, 끝-끝 두 런의 합계, 걸린 시간, `swap_converged` 값을 보고한다. 어긋나면 **고치기 전에 보고한다** — 여기서 어긋나는 것은 계획의 전제가 틀렸다는 뜻이다.

---

## 완료 조건

- 같은 로스터·같은 보스로 두 번 돌린 전부최적화가 **같은 덱·같은 합계**를 낸다
- 상한이 물린 런에서 `workers=1`과 `workers=2`가 같은 배분을 낸다 (Task 2)
- 배치 잘라내기를 지우면 테스트가 빨개진다 (Task 2 Step 3에서 확인 완료)
- `SWAP_CANDIDATE_BUDGET` 옆에 그 값을 만든 측정 표가 있다
- 상한에 걸린 런이 화면에 그 사실을 말한다
