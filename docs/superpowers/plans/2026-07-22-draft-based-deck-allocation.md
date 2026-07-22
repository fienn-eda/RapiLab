# Draft-Based Deck Allocation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let a user seed the 5-deck raid recommender with a partial or complete deck draft (units pinned per deck, each locked or flexible) and get an optimized allocation that fills empty seats, corrects burst order, and — for a complete draft — reports a monotone baseline→within-draft→bench-inclusive comparison that is never worse than what they submitted.

**Architecture:** A new completion primitive in `deck_search.py` finds the best deck *containing* a required unit set over all compatible burst-tier shapes. `allocate_decks` gains a `draft`/`locked` seam that seeds decks from that primitive and masks locked seats out of the swap hill-climb. A `recommend_from_draft` orchestrator runs the warm-started and from-scratch allocations and returns up to three tiers. The FastAPI `/api/recommend-raid` gains an optional `draft` input and additive response fields; a new `GET /api/supported-units` feeds the palette. The frontend (executed by the frontend-builder subagent against `frontend/README.md`) adds a tier-grouped palette, a 5×5 draft editor with per-unit lock toggles, and a three-tier results view, consuming the static `frontend/public/portraits/manifest.json` for icons.

**Tech Stack:** Python 3 / FastAPI / Pydantic / pytest (backend); React + Vite + TypeScript / Vitest (frontend). Multiprocessing via existing `app.sim_pool.SimPool`.

## Global Constraints

- **Backward compatibility:** `allocate_decks(..., draft=None)` and `POST /api/recommend-raid` with no `draft` MUST be bit-identical to today. New response fields are additive; existing top-level fields (`decks`, `combined_total_damage`, `excluded_slugs`, `leftover_slugs`) keep their current shape and meaning (= the bench-inclusive `recommended` tier).
- **No survival/HP/gimmick simulation.** Engine stays a pure damage maximizer. Survival enters only as user-supplied `locked` units.
- **Burst order is engine-assigned**, never taken from input. Draft slots are membership only. Ordering + seat rules (`_intra_tier_orderings`, `_buffer_seat_valid`, `_tier1_seating_valid`, `_no_variant_clash`) always apply.
- **Never recommend worse than the user's config:** for a complete draft, `recommended ≥ within_draft ≥ baseline` must hold by construction.
- **Deck shapes are exactly** `ALLOWED_SHAPES = ((1,1,3),(1,2,2),(2,1,2))` (in `deck_search.py`). Every produced deck is one of these.
- **Engine-supported slugs** come from `app.skill_rules.registry.ENCODED_SLUGS`. Mode variants expand via `app.user_roster.MODE_VARIANTS`; variant burst tiers via `VARIANT_BURST_TIERS`.
- **No invented URLs / fields.** Portraits are consumed from the committed `frontend/public/portraits/manifest.json` (`{slug: filename}`, prefix `/portraits/`), chip fallback when a slug is absent.
- **Worktree data:** run `python scripts/sync_worktree_data.py` before running the backend/tests in a fresh worktree (`data/` is gitignored). Backend tests: `cd backend && python -m pytest <path> -v`. Frontend: `cd frontend && npx vitest run <path>`.

---

## File Structure

**Backend**
- `backend/app/deck_search.py` — add `best_completions(...)` (completion primitive) + a shape-completion generator. Modify.
- `backend/app/deck_allocation.py` — add `draft`/`locked` to `allocate_decks`, thread a lock mask through the swap pass; add `recommend_from_draft(...)` orchestrator + an `InfeasibleDraft` exception. Modify.
- `backend/app/api.py` — add `DraftUnit`/`DraftDeck` request models, `draft` on `RecommendRaidRequest`, additive response fields, wire `recommend_from_draft`; add `GET /api/supported-units` + `SupportedUnit` model. Modify.
- `backend/app/supported_units.py` — new: assemble the supported-unit metadata list from the registry + meta loader. Create.
- `backend/tests/test_deck_completion.py`, `test_deck_allocation_draft.py`, `test_recommend_from_draft.py`, `test_api_recommend_raid_draft.py`, `test_supported_units.py` — new test files.

**Frontend** (frontend-builder, against `frontend/README.md`)
- `frontend/src/api/supportedUnitsClient.ts` (+ `.mock.ts`), `frontend/src/hooks/useSupportedUnits.ts` — new.
- `frontend/src/hooks/usePortraitManifest.ts` — new (loads `/portraits/manifest.json`).
- `frontend/src/components/DraftPalette.tsx`, `DraftEditor.tsx`, `DraftResults.tsx` — new.
- `frontend/src/types/recommend.ts`, `frontend/src/api/recommendRaidClient.ts` (+ `.mock.ts`), `frontend/src/components/RecommendPanel.tsx` — modify (add `draft`, tier fields, mode wiring).
- `frontend/README.md` — the data contract (updated in Task 6, consumed by all frontend tasks).

---

## Phase 1 — Backend + API

### Task 1: Completion primitive — best deck containing a required set

**Files:**
- Modify: `backend/app/deck_search.py`
- Test: `backend/tests/test_deck_completion.py`

**Interfaces:**
- Consumes: `ALLOWED_SHAPES`, `_no_variant_clash`, `_tier1_seating_valid`, `_intra_tier_orderings`, `evaluate_deck`, `_summarize`, `_score_batch`, `BossProfile` (all in `deck_search.py`).
- Produces:
  - `best_completions(required, candidates, boss, top_n=1, pool=None) -> list[dict]` — each dict is a `_summarize(...)` result (`{"deck": [slug...], "total_damage", "burst_damage", "normal_attack_damage", "result"}`). Returns `[]` when `required`'s tier counts fit no shape or no valid completion exists. Every returned deck contains all of `required`.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_deck_completion.py
from app.deck_search import best_completions, BossProfile
from tests.helpers import make_unit  # existing helper factory; see other deck tests

BOSS = BossProfile()

def test_completion_includes_all_required_and_fills_all_tiers():
    # required = one Burst-3; completion must add B1+B2 (+ more) to a legal shape
    required = [make_unit("b3a", tier=3)]
    candidates = [make_unit("b1a", tier=1), make_unit("b2a", tier=2),
                  make_unit("b3b", tier=3), make_unit("b3c", tier=3)]
    out = best_completions(required, candidates, BOSS, top_n=1)
    assert out, "expected at least one completion"
    deck = set(out[0]["deck"])
    assert "b3a" in deck                     # required always present
    assert len(deck) == 5
    tiers = sorted(u.burst_tier for u in required + candidates if u.slug in deck)
    assert tiers[0] == 1 and 2 in tiers and 3 in tiers  # all three tiers represented

def test_completion_infeasible_returns_empty():
    # three B1 required cannot fit any ALLOWED_SHAPES (max B1 per deck is 2)
    required = [make_unit("b1a", tier=1), make_unit("b1b", tier=1), make_unit("b1c", tier=1)]
    candidates = [make_unit("b2a", tier=2), make_unit("b3a", tier=3), make_unit("b3b", tier=3)]
    assert best_completions(required, candidates, BOSS) == []
```

If `tests/helpers.make_unit` does not exist, first check how existing `backend/tests/test_deck_search.py` / `test_deck_allocation.py` construct `NikkeSpec` fixtures and reuse that exact construction (do not invent a factory).

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_deck_completion.py -v`
Expected: FAIL with `ImportError: cannot import name 'best_completions'`.

- [ ] **Step 3: Write minimal implementation**

```python
# backend/app/deck_search.py  (add near shape_combinations)
from collections import Counter

def _shape_completions(required, candidates):
    """Yield 5-unit decks (canonical tier order) that contain every unit in
    `required`, filling the rest from `candidates`, for every ALLOWED_SHAPES
    compatible with required's per-tier counts. Pure combinatorics on burst_tier."""
    req_counts = Counter(u.burst_tier for u in required)
    if any(t not in (1, 2, 3) for t in req_counts):
        return
    cand_by_tier = {1: [], 2: [], 3: []}
    for u in candidates:
        if u.burst_tier in cand_by_tier:
            cand_by_tier[u.burst_tier].append(u)
    for n1, n2, n3 in ALLOWED_SHAPES:
        need = {1: n1 - req_counts.get(1, 0),
                2: n2 - req_counts.get(2, 0),
                3: n3 - req_counts.get(3, 0)}
        if any(v < 0 for v in need.values()):
            continue  # required already exceeds this shape's tier slot
        for f1 in combinations(cand_by_tier[1], need[1]):
            for f2 in combinations(cand_by_tier[2], need[2]):
                for f3 in combinations(cand_by_tier[3], need[3]):
                    deck = list(required) + list(f1) + list(f2) + list(f3)
                    # canonical tier order for _no_variant_clash / seating checks
                    deck.sort(key=lambda u: u.burst_tier)
                    if _no_variant_clash(deck) and _tier1_seating_valid(deck):
                        yield deck

def best_completions(required, candidates, boss, top_n=1, pool=None):
    orderings = _all_intra_tier_orderings(_shape_completions(required, candidates))
    if not orderings:
        return []
    totals = _score_batch(orderings, boss, pool)
    ranked = sorted(zip(totals, orderings), key=lambda p: p[0], reverse=True)
    return [_summarize(o, evaluate_deck(o, boss)) for _, o in ranked[:top_n]]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_deck_completion.py -v`
Expected: PASS (2 passed).

- [ ] **Step 5: Commit**

```bash
git add backend/app/deck_search.py backend/tests/test_deck_completion.py
git commit -m "Add best-deck-completion primitive for a required unit set"
```

---

### Task 2: `allocate_decks` draft seam + locked swap mask

**Files:**
- Modify: `backend/app/deck_allocation.py`
- Test: `backend/tests/test_deck_allocation_draft.py`

**Interfaces:**
- Consumes: `best_completions` (Task 1); existing `search_best_decks`, `evaluate_deck`, `_best_ordering_summary`, `_swap_pass` internals.
- Produces:
  - `class InfeasibleDraft(ValueError)` with a human-readable message.
  - `allocate_decks(roster, boss, num_decks=5, draft=None, locked=frozenset(), time_budget_sec=45.0, workers=None) -> {"decks": [summary...], "leftover_slugs": [...]}`. `draft`: `list[list[NikkeSpec]]` (units placed per deck, in draft order). `locked`: `set[str]` of slugs that must stay in their drafted deck (masked from swaps). `draft=None` ⇒ current behavior exactly.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_deck_allocation_draft.py
from app.deck_allocation import allocate_decks, InfeasibleDraft
from app.deck_search import BossProfile
import pytest
from tests.helpers import make_unit   # or the fixture construction used by test_deck_allocation.py

BOSS = BossProfile()

def _roster():
    return ([make_unit(f"b1{i}", tier=1) for i in range(4)]
            + [make_unit(f"b2{i}", tier=2) for i in range(4)]
            + [make_unit(f"b3{i}", tier=3) for i in range(8)])

def test_draft_none_matches_plain_allocation():
    r = _roster()
    assert allocate_decks(r, BOSS, num_decks=2, draft=None, workers=None) == \
           allocate_decks(r, BOSS, num_decks=2, workers=None)

def test_locked_unit_stays_in_its_deck():
    r = _roster()
    draft = [[next(u for u in r if u.slug == "b30")]]  # seed deck 0 with b30, locked
    out = allocate_decks(r, BOSS, num_decks=2, draft=draft,
                         locked={"b30"}, workers=None)
    assert "b30" in out["decks"][0]["deck"]

def test_infeasible_draft_raises():
    r = _roster()
    b1s = [u for u in r if u.burst_tier == 1][:3]
    with pytest.raises(InfeasibleDraft):
        allocate_decks(r, BOSS, num_decks=1, draft=[b1s], locked=set(), workers=None)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_deck_allocation_draft.py -v`
Expected: FAIL with `ImportError: cannot import name 'InfeasibleDraft'` (or `allocate_decks() got an unexpected keyword argument 'draft'`).

- [ ] **Step 3: Write minimal implementation**

```python
# backend/app/deck_allocation.py
from app.deck_search import best_completions   # add to existing imports

class InfeasibleDraft(ValueError):
    """A draft deck's locked/placed units fit no legal deck shape, or the pool
    is exhausted before every drafted deck can be completed."""

def allocate_decks(roster, boss, num_decks=5, draft=None, locked=frozenset(),
                   time_budget_sec=45.0, workers=None):
    pool = SimPool(roster, boss, workers=workers) if resolve_workers(workers) > 1 else None
    try:
        by_slug = {u.slug: u for u in roster}
        draft = draft or []
        placed = {u.slug for deck in draft for u in deck}
        remaining = [u for u in roster if u.slug not in placed]

        decks = []
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
            units = [by_slug[s] for s in found[0]["deck"]]
            decks.append(units)
            used = {u.slug for u in units}
            remaining = [u for u in remaining if u.slug not in used]

        deadline = time.monotonic() + time_budget_sec
        _swap_pass(decks, remaining, boss, deadline, locked=locked)

        summaries = [_best_ordering_summary(units, boss, pool) for units in decks]
        return {"decks": summaries,
                "leftover_slugs": sorted(u.slug for u in remaining)}
    finally:
        if pool is not None:
            pool.close()
```

Thread `locked` through the swap helpers — a locked seat is never chosen as a swap source:

```python
def _swap_pass(decks, leftovers, boss, deadline, locked=frozenset()):
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_deck_allocation_draft.py tests/test_deck_allocation.py -v`
Expected: PASS (new file green; existing `test_deck_allocation.py` still green — proves `draft=None` unchanged).

- [ ] **Step 5: Commit**

```bash
git add backend/app/deck_allocation.py backend/tests/test_deck_allocation_draft.py
git commit -m "Seed allocate_decks from a draft and lock pinned seats out of swaps"
```

---

### Task 3: Three-tier orchestrator (`recommend_from_draft`)

**Files:**
- Modify: `backend/app/deck_allocation.py`
- Test: `backend/tests/test_recommend_from_draft.py`

**Interfaces:**
- Consumes: `allocate_decks` (Task 2), `_best_ordering_summary`, `evaluate_deck`.
- Produces:
  - `recommend_from_draft(roster, boss, num_decks=5, draft=None, locked=frozenset(), workers=None) -> dict` with keys:
    - `recommended`: `{"decks": [summary...], "leftover_slugs": [...]}` — best over the full roster.
    - `within_draft`: same shape, or `None` — only when the draft is complete (`len(draft)==num_decks` and every drafted deck has 5 units); pool = drafted units only.
    - `baseline_total_damage`: `float | None` — the exact drafted groupings scored at best order; only for a complete draft.
  - `pinned_by_deck`: `list[list[str]]` — locked slugs per recommended deck (for the API to attach `pinned_slugs`).

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_recommend_from_draft.py
from app.deck_allocation import recommend_from_draft
from app.deck_search import BossProfile
from tests.helpers import make_unit

BOSS = BossProfile()

def _full_roster():
    return ([make_unit(f"b1{i}", tier=1) for i in range(6)]
            + [make_unit(f"b2{i}", tier=2) for i in range(6)]
            + [make_unit(f"b3{i}", tier=3) for i in range(14)])

def _complete_draft(roster, num_decks=2):
    # deterministic 5-unit decks respecting a (1,1,3) shape
    b1 = [u for u in roster if u.burst_tier == 1]
    b2 = [u for u in roster if u.burst_tier == 2]
    b3 = [u for u in roster if u.burst_tier == 3]
    decks = []
    for d in range(num_decks):
        decks.append([b1[d], b2[d], b3[3*d], b3[3*d+1], b3[3*d+2]])
    return decks

def test_complete_draft_yields_monotone_tiers():
    r = _full_roster()
    draft = _complete_draft(r, num_decks=2)
    out = recommend_from_draft(r, BOSS, num_decks=2, draft=draft, workers=None)
    base = out["baseline_total_damage"]
    within = sum(d["total_damage"] for d in out["within_draft"]["decks"])
    rec = sum(d["total_damage"] for d in out["recommended"]["decks"])
    assert base is not None and out["within_draft"] is not None
    assert base <= within + 1e-6
    assert within <= rec + 1e-6

def test_incomplete_draft_has_no_baseline():
    r = _full_roster()
    draft = [[next(u for u in r if u.burst_tier == 1)]]  # one B1 pinned, rest empty
    out = recommend_from_draft(r, BOSS, num_decks=2, draft=draft, workers=None)
    assert out["baseline_total_damage"] is None
    assert out["within_draft"] is None
    assert out["recommended"]["decks"]

def test_zero_base_recommended_matches_plain_allocation():
    # no draft: recommended must be the single from-scratch allocation (no
    # doubled warm pass), bit-identical to allocate_decks with no draft.
    from app.deck_allocation import allocate_decks
    r = _full_roster()
    out = recommend_from_draft(r, BOSS, num_decks=2, draft=None, workers=None)
    assert out["recommended"] == allocate_decks(r, BOSS, num_decks=2, workers=None)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_recommend_from_draft.py -v`
Expected: FAIL with `ImportError: cannot import name 'recommend_from_draft'`.

- [ ] **Step 3: Write minimal implementation**

```python
# backend/app/deck_allocation.py
def _combined(alloc):
    return sum(d["total_damage"] for d in alloc["decks"])

def _is_complete(draft, num_decks):
    return len(draft) == num_decks and all(len(deck) == 5 for deck in draft)

def recommend_from_draft(roster, boss, num_decks=5, draft=None,
                         locked=frozenset(), workers=None):
    draft = draft or []
    # bench-inclusive recommendation: warm-start from the draft (guarantees
    # >= baseline) and from-scratch (explores all shapes); keep the better.
    # With no draft, warm == scratch, so run the scratch pass ALONE - this keeps
    # the zero-base path a single allocate_decks call, bit-identical to today.
    scratch = allocate_decks(roster, boss, num_decks=num_decks, workers=workers)
    if draft:
        warm = allocate_decks(roster, boss, num_decks=num_decks, draft=draft,
                              locked=locked, workers=workers)
        recommended = warm if _combined(warm) >= _combined(scratch) else scratch
    else:
        recommended = scratch

    within_draft = None
    baseline_total = None
    if _is_complete(draft, num_decks):
        drafted = [u for deck in draft for u in deck]
        w = allocate_decks(drafted, boss, num_decks=num_decks, draft=draft,
                           locked=locked, workers=workers)
        s = allocate_decks(drafted, boss, num_decks=num_decks, workers=workers)
        within_draft = w if _combined(w) >= _combined(s) else s
        baseline_total = sum(
            _best_ordering_summary(deck, boss)["total_damage"] for deck in draft)

    # locked slugs per recommended deck, for the API's pinned_slugs
    pinned_by_deck = [[s for s in d["deck"] if s in locked]
                      for d in recommended["decks"]]
    return {"recommended": recommended, "within_draft": within_draft,
            "baseline_total_damage": baseline_total, "pinned_by_deck": pinned_by_deck}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_recommend_from_draft.py -v`
Expected: PASS (2 passed).

- [ ] **Step 5: Commit**

```bash
git add backend/app/deck_allocation.py backend/tests/test_recommend_from_draft.py
git commit -m "Add three-tier draft orchestrator (baseline/within-draft/recommended)"
```

---

### Task 4: Supported-units assembly + `GET /api/supported-units`

**Files:**
- Create: `backend/app/supported_units.py`
- Modify: `backend/app/api.py`
- Test: `backend/tests/test_supported_units.py`

**Interfaces:**
- Consumes: `app.skill_rules.registry.ENCODED_SLUGS`, `app.user_roster.MODE_VARIANTS` / `VARIANT_BURST_TIERS`, `app.skill_values.load_character_data`, `app.user_roster.DATA_DIR`.
- Produces:
  - `supported_units(data_dir=DATA_DIR) -> list[dict]` where each dict is `{"slug": str, "name": str, "burst_tier": int, "element": str}`. `name` = `meta.get("name")` or humanized slug; `element` = `meta["element"]`; `burst_tier` = `VARIANT_BURST_TIERS.get(slug)` or `int(meta["burst"])`. Slugs whose data can't be loaded are skipped (never 500).
  - `GET /api/supported-units -> list[SupportedUnit]` where `SupportedUnit(slug, name, burst_tier, element)`.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_supported_units.py
from fastapi.testclient import TestClient
from app.api import app
from app.supported_units import supported_units

def test_supported_units_have_required_fields():
    units = supported_units()
    assert units, "expected a non-empty supported-unit list"
    for u in units:
        assert set(u) == {"slug", "name", "burst_tier", "element"}
        assert u["burst_tier"] in (1, 2, 3)
    slugs = {u["slug"] for u in units}
    assert "crown" in slugs   # a known encoded B1

def test_supported_units_endpoint():
    client = TestClient(app)
    resp = client.get("/api/supported-units")
    assert resp.status_code == 200
    body = resp.json()
    assert isinstance(body, list) and body
    assert {"slug", "name", "burst_tier", "element"} <= set(body[0])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_supported_units.py -v`
Expected: FAIL with `ModuleNotFoundError: No module named 'app.supported_units'`.

- [ ] **Step 3: Write minimal implementation**

```python
# backend/app/supported_units.py
from app.skill_rules.registry import ENCODED_SLUGS
from app.user_roster import DATA_DIR, VARIANT_BURST_TIERS, MODE_VARIANTS
from app.skill_values import load_character_data

# variant slug -> its data slug (e.g. cinderella-crystal-wave-mg -> base)
_VARIANT_DATA_SLUG = {v: base for base, variants in MODE_VARIANTS.items()
                      for v in variants}

def _humanize(slug):
    return slug.replace("-", " ").title()

def supported_units(data_dir=DATA_DIR):
    out = []
    for slug in ENCODED_SLUGS:
        data_slug = _VARIANT_DATA_SLUG.get(slug, slug)
        try:
            meta = load_character_data("lootandwaifus", data_slug, data_dir)
            burst_tier = VARIANT_BURST_TIERS.get(slug, int(meta["burst"]))
            element = meta["element"]
        except (FileNotFoundError, KeyError, TypeError, ValueError):
            continue
        out.append({"slug": slug,
                    "name": meta.get("name") or _humanize(slug),
                    "burst_tier": burst_tier,
                    "element": element})
    return out
```

```python
# backend/app/api.py  (add model + route)
from app.supported_units import supported_units as _supported_units

class SupportedUnit(BaseModel):
    slug: str
    name: str
    burst_tier: int
    element: str

@app.get("/api/supported-units", response_model=list[SupportedUnit])
def supported_units_route() -> list[SupportedUnit]:
    return [SupportedUnit(**u) for u in _supported_units()]
```

Confirm `MODE_VARIANTS`/`VARIANT_BURST_TIERS` are importable from `app.user_roster` (grep before writing; if they live elsewhere, import from there). If `meta` has no `"name"` key the humanized-slug fallback applies — do not fail.

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && python -m pytest tests/test_supported_units.py -v`
Expected: PASS (2 passed).

- [ ] **Step 5: Commit**

```bash
git add backend/app/supported_units.py backend/app/api.py backend/tests/test_supported_units.py
git commit -m "Serve engine-supported units (slug/name/tier/element) for the palette"
```

---

### Task 5: Wire `draft` into `POST /api/recommend-raid`

**Files:**
- Modify: `backend/app/api.py`
- Test: `backend/tests/test_api_recommend_raid_draft.py`

**Interfaces:**
- Consumes: `recommend_from_draft` (Task 3), `InfeasibleDraft` (Task 2), existing `load_roster`, `BossProfile`, `DeckRecommendation`.
- Produces (request/response additions):
  - `DraftUnit(slug: str, locked: bool = False)`, `DraftDeck(units: list[DraftUnit])`.
  - `RecommendRaidRequest.draft: list[DraftDeck] = []`.
  - `DeckRecommendation.pinned_slugs: list[str] = []`.
  - `DraftAllocation(decks: list[DeckRecommendation], combined_total_damage: float, leftover_slugs: list[str])`.
  - `RecommendRaidResponse.within_draft: DraftAllocation | None = None`, `.baseline_total_damage: float | None = None`. Existing top-level fields unchanged, populated from the `recommended` tier.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_api_recommend_raid_draft.py
from fastapi.testclient import TestClient
from app.api import app
# Reuse the roster payload builder the existing raid API test uses:
from tests.test_api_recommend_raid import _roster_payload, _boss_payload  # adjust to real names

client = TestClient(app)

def test_draft_omitted_is_backward_compatible():
    body = {"roster": _roster_payload(), "boss": _boss_payload(), "num_decks": 2}
    resp = client.post("/api/recommend-raid", json=body)
    assert resp.status_code == 200
    data = resp.json()
    assert data["within_draft"] is None
    assert data["baseline_total_damage"] is None
    assert "decks" in data and "combined_total_damage" in data

def test_locked_draft_unit_appears_pinned():
    roster = _roster_payload()
    lock_slug = roster[0]["character_slug"]
    body = {"roster": roster, "boss": _boss_payload(), "num_decks": 2,
            "draft": [{"units": [{"slug": lock_slug, "locked": True}]}]}
    resp = client.post("/api/recommend-raid", json=body)
    assert resp.status_code == 200
    decks = resp.json()["decks"]
    assert any(lock_slug in d["pinned_slugs"] for d in decks)

def test_infeasible_draft_returns_422():
    roster = _roster_payload()
    b1s = [s["character_slug"] for s in roster][:3]  # assume first three are B1 in fixture
    body = {"roster": roster, "boss": _boss_payload(), "num_decks": 1,
            "draft": [{"units": [{"slug": s, "locked": True} for s in b1s]}]}
    resp = client.post("/api/recommend-raid", json=body)
    assert resp.status_code == 422
```

If the existing raid test exposes no reusable payload helper, build the roster/boss dict inline from `backend/tests/test_api_recommend_raid.py`'s existing request body (copy its structure verbatim — do not invent fields).

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && python -m pytest tests/test_api_recommend_raid_draft.py -v`
Expected: FAIL (`within_draft` key missing / `draft` rejected).

- [ ] **Step 3: Write minimal implementation**

```python
# backend/app/api.py
from app.deck_allocation import recommend_from_draft, InfeasibleDraft

class DraftUnit(BaseModel):
    slug: str
    locked: bool = False

class DraftDeck(BaseModel):
    units: list[DraftUnit]

# add field to DeckRecommendation:
#     pinned_slugs: list[str] = []

class DraftAllocation(BaseModel):
    decks: list[DeckRecommendation]
    combined_total_damage: float
    leftover_slugs: list[str]

# add fields to RecommendRaidRequest:
#     draft: list[DraftDeck] = []
# add fields to RecommendRaidResponse:
#     within_draft: DraftAllocation | None = None
#     baseline_total_damage: float | None = None

def _to_recs(decks, pinned_by_deck=None):
    pinned_by_deck = pinned_by_deck or [[] for _ in decks]
    return [DeckRecommendation(
                deck=d["deck"], total_damage=d["total_damage"],
                burst_damage=d["burst_damage"],
                normal_attack_damage=d["normal_attack_damage"],
                pinned_slugs=pinned)
            for d, pinned in zip(decks, pinned_by_deck)]

@app.post("/api/recommend-raid", response_model=RecommendRaidResponse)
def recommend_raid(request: RecommendRaidRequest) -> RecommendRaidResponse:
    _reject_unknown_overload_options(request.roster)
    specs, excluded = load_roster(request.roster)
    boss = BossProfile(
        element=request.boss.element, core_hittable=request.boss.core_hittable,
        enemy_def=request.boss.enemy_def, fight_duration=request.boss.fight_duration,
        part_destructible=request.boss.part_destructible,
    )
    by_slug = {u.slug: u for u in specs}
    # resolve draft slugs -> specs; unknown/unsupported slug is a client error
    draft, locked = [], set()
    for deck in request.draft:
        seat = []
        for u in deck.units:
            if u.slug not in by_slug:
                raise HTTPException(422, f"draft references unusable slug: {u.slug}")
            seat.append(by_slug[u.slug])
            if u.locked:
                locked.add(u.slug)
        draft.append(seat)
    seen = [u.slug for deck in draft for u in deck]
    if len(seen) != len(set(seen)):
        raise HTTPException(422, "a unit appears in more than one draft deck")

    try:
        out = recommend_from_draft(specs, boss, num_decks=request.num_decks,
                                   draft=draft, locked=locked, workers="auto")
    except InfeasibleDraft as e:
        raise HTTPException(422, str(e))

    rec = out["recommended"]
    if not rec["decks"]:
        raise HTTPException(422, f"no feasible deck from the usable roster (excluded: {excluded})")
    rec_decks = _to_recs(rec["decks"], out["pinned_by_deck"])
    within = None
    if out["within_draft"] is not None:
        wd = out["within_draft"]
        within = DraftAllocation(
            decks=_to_recs(wd["decks"]),
            combined_total_damage=sum(d["total_damage"] for d in wd["decks"]),
            leftover_slugs=wd["leftover_slugs"])
    return RecommendRaidResponse(
        decks=rec_decks,
        combined_total_damage=sum(d.total_damage for d in rec_decks),
        excluded_slugs=excluded,
        leftover_slugs=rec["leftover_slugs"],
        within_draft=within,
        baseline_total_damage=out["baseline_total_damage"],
    )
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd backend && python -m pytest tests/test_api_recommend_raid_draft.py tests/test_api_recommend_raid.py -v`
Expected: PASS (new file green; existing raid API test still green — additive fields didn't break it).

- [ ] **Step 5: Commit**

```bash
git add backend/app/api.py backend/tests/test_api_recommend_raid_draft.py
git commit -m "Accept a draft on /api/recommend-raid and return three-tier results"
```

---

### Task 6: Full backend regression + frontend contract in README

**Files:**
- Modify: `frontend/README.md`
- Test: full backend suite.

- [ ] **Step 1: Run the whole backend suite**

Run: `cd backend && python -m pytest -q`
Expected: all green (prior baseline + the new tests). If any pre-existing test regressed, fix the cause before proceeding (do not edit tests to pass).

- [ ] **Step 2: Document the data contract for the frontend**

Add a "Draft-based raid recommendation" section to `frontend/README.md` describing exactly:
- `GET /api/supported-units` → `[{slug, name, burst_tier, element}]`.
- `POST /api/recommend-raid` request adds `draft: [{units: [{slug, locked}]}]` (optional; omit = zero-base).
- Response adds `decks[].pinned_slugs: string[]`, `within_draft: {decks, combined_total_damage, leftover_slugs} | null`, `baseline_total_damage: number | null` (both non-null only when the draft is complete = `num_decks` decks × 5 units).
- Portraits: read `/portraits/manifest.json` (`{slug: filename}`), render `/portraits/<filename>`, chip fallback when a slug is absent.
- Draft slots are membership only (no burst order); a unit may appear in at most one deck.

- [ ] **Step 3: Commit**

```bash
git add frontend/README.md
git commit -m "Document the draft-based raid API contract for the frontend"
```

---

## Phase 2 — Frontend (frontend-builder subagent, against `frontend/README.md`)

> Each task works only inside `frontend/`, treats backend as read-only reference, and implements to the Task 6 contract. Tests are Vitest; run `cd frontend && npx vitest run` and `npx tsc -b` per task. A live mock client mirrors the real one (existing pattern: `recommendRaidClient.mock.ts`).

### Task 7: Supported-units + portrait manifest data hooks

**Files:**
- Create: `frontend/src/api/supportedUnitsClient.ts`, `frontend/src/api/supportedUnitsClient.mock.ts`, `frontend/src/hooks/useSupportedUnits.ts`, `frontend/src/hooks/usePortraitManifest.ts`
- Create: `frontend/src/hooks/useSupportedUnits.test.ts`, `frontend/src/hooks/usePortraitManifest.test.ts`
- Modify: `frontend/src/types/recommend.ts` (add `SupportedUnit`, `PortraitManifest` types)

**Interfaces:**
- Produces: `useSupportedUnits(): {units: SupportedUnit[], loading, error}`, `usePortraitManifest(): {portraitFor(slug): string | null}` (returns `/portraits/<file>` or null). `SupportedUnit = {slug, name, burstTier, element}`.

- [ ] Step 1: Write failing tests — mock `fetch('/api/supported-units')` returns a two-unit list; assert `useSupportedUnits` exposes them mapped to camelCase. Mock `fetch('/portraits/manifest.json')` returns `{portraits:{crown:"c.webp"}}`; assert `portraitFor("crown")==="/portraits/c.webp"` and `portraitFor("nope")===null`.
- [ ] Step 2: Run `npx vitest run src/hooks/useSupportedUnits.test.ts src/hooks/usePortraitManifest.test.ts` → FAIL (modules missing).
- [ ] Step 3: Implement the two clients/hooks + types. `usePortraitManifest` reads `manifest.portraits[slug]`.
- [ ] Step 4: Run the two test files → PASS; `npx tsc -b` clean.
- [ ] Step 5: Commit `feat(frontend): supported-units + portrait manifest hooks`.

### Task 8: Tier-grouped draft palette

**Files:**
- Create: `frontend/src/components/DraftPalette.tsx`, `frontend/src/components/DraftPalette.test.tsx`

**Interfaces:**
- Consumes: `useSupportedUnits`, `usePortraitManifest`, the user roster from `useRoster` (existing).
- Produces: `<DraftPalette owned={slugs} used={Set<slug>} onPick={(slug)=>void} />` — renders owned ∩ supported units grouped under B1/B2/B3 headers; each unit shows portrait (or a class/element-tinted chip fallback with the name); a `used` slug is disabled (already placed).

- [ ] Step 1: Failing test — given owned=[crown(1),liter(1),modernia(3)] and supported metadata, assert three appear under the correct tier headers, that a unit in `used` renders disabled, and that clicking a unit calls `onPick` with its slug.
- [ ] Step 2: Run → FAIL.
- [ ] Step 3: Implement grouping (`burstTier` → section), portrait-or-chip rendering, disabled state.
- [ ] Step 4: Run test → PASS; `tsc -b` clean.
- [ ] Step 5: Commit `feat(frontend): tier-grouped draft palette with portraits`.

### Task 9: 5×5 draft editor with lock toggle + no-reuse

**Files:**
- Create: `frontend/src/components/DraftEditor.tsx`, `frontend/src/components/DraftEditor.test.tsx`

**Interfaces:**
- Produces: `<DraftEditor numDecks={n} value={Draft} onChange={(Draft)=>void} />` where `Draft = { decks: {slug, locked}[][] }`. Places a picked unit into the first deck with a free seat (or a chosen deck), enforces ≤5 per deck and a slug in at most one deck, and a per-seat lock toggle. Emits the `draft` payload shape (`[{units:[{slug,locked}]}]`) via a `toRequestDraft(value)` helper.

- [ ] Step 1: Failing tests — placing a unit adds it to a deck; placing a 6th into a full deck is rejected; the same slug cannot be added twice; toggling lock flips `locked`; `toRequestDraft` produces `[{units:[{slug,locked}]}]` and omits empty decks.
- [ ] Step 2: Run → FAIL.
- [ ] Step 3: Implement editor state, seat/lock interactions, `toRequestDraft`.
- [ ] Step 4: Run tests → PASS; `tsc -b` clean.
- [ ] Step 5: Commit `feat(frontend): 5x5 draft editor with lock toggles and no-reuse`.

### Task 10: Draft results (three-tier) + wire into RecommendPanel

**Files:**
- Modify: `frontend/src/types/recommend.ts` (add `draft`, `pinned_slugs`, `within_draft`, `baseline_total_damage`), `frontend/src/api/recommendRaidClient.ts` + `.mock.ts`, `frontend/src/components/RecommendPanel.tsx`
- Create: `frontend/src/components/DraftResults.tsx`, `frontend/src/components/DraftResults.test.tsx`

**Interfaces:**
- Consumes: the extended `RecommendRaidResponse`; `DraftEditor.toRequestDraft`.
- Produces: `<DraftResults response={...} />` — when `within_draft`/`baseline_total_damage` are present, renders the three tiers **baseline → within_draft (+Δ1) → recommended (+Δ2)** with per-deck diff vs the submitted draft and `pinned_slugs` badges; otherwise renders the single recommended allocation (reusing `RaidResults`/`DeckCard`). Adds a "draft optimize" mode to `RecommendPanel` that sends `draft`.

- [ ] Step 1: Failing tests — response with the three tier fields renders all three totals and the two deltas; response with nulls renders only the recommended allocation; a 422 body renders the infeasible-draft message. `recommendRaidClient` sends `draft` in the request body (assert via mock).
- [ ] Step 2: Run → FAIL.
- [ ] Step 3: Implement `DraftResults`, extend types + client + mock, add the mode + submit path in `RecommendPanel`.
- [ ] Step 4: Run the frontend suite `npx vitest run` → all PASS; `npx tsc -b` clean; `npm run build` clean.
- [ ] Step 5: Commit `feat(frontend): three-tier draft results wired into the recommender`.

---

## Phase 3 — End-to-end verification

### Task 11: Live E2E + roadmap/docs update

- [ ] **Step 1: Live smoke** — start the backend (`verify` skill or `cd backend && uvicorn app.api:app`), and with a real synced roster POST `/api/recommend-raid` (a) with no draft (b) with one locked B1 partial draft (c) with a complete 2-deck draft; confirm (a) matches today, (b) keeps the locked unit, (c) returns monotone `baseline ≤ within_draft ≤ recommended`. Record the numbers.
- [ ] **Step 2: Measure** the complete-draft path runtime on the real loadable roster and note it against the ~97s zero-base baseline (spec expects same order of magnitude — `recommended` runs a from-scratch pass).
- [ ] **Step 3:** Update `docs/roadmap.md` (Phase 5 note: draft-based allocation landed) and add a `/document` decision entry (draft+lock model; never-worse guarantee; `gauge_charge_time`/`mode` left fixed).
- [ ] **Step 4: Commit** `docs: record draft-based deck allocation landing + measurements`.

---

## Self-Review

**Spec coverage:** draft+lock model → Tasks 2,5; completion across all tiers → Task 1; order correction via existing seat rules → Tasks 1–2 (uses `_intra_tier_orderings`/`_buffer_seat_valid`); three-tier improve-existing + never-worse → Task 3; infeasible-draft 422 → Tasks 2,5; supported-units → Task 4; portraits (resolved gate, static manifest) → Tasks 7–8; frontend palette/editor/lock/3-tier → Tasks 7–10; backward compat → Global Constraints + Tasks 2,5 regression steps; `gauge_charge_time`/`mode` non-exposure → unchanged (no task needed, documented in Task 11). No spec requirement left unmapped.

**Placeholders:** backend steps carry full code; two flagged verification points ("reuse the existing fixture factory", "reuse the raid test payload helper") are instructions to match existing patterns rather than invent — resolve them by reading the named existing test files, not by fabricating. Frontend tasks are specified to `frontend/README.md` contract per this repo's frontend-builder convention.

**Type consistency:** `best_completions(required, candidates, boss, top_n, pool)` used identically in Tasks 1–2; `allocate_decks(..., draft, locked, ...)` and `recommend_from_draft(...)` keys (`recommended`/`within_draft`/`baseline_total_damage`/`pinned_by_deck`) consumed unchanged in Tasks 3,5; API `DraftUnit/DraftDeck/DraftAllocation/pinned_slugs/within_draft/baseline_total_damage` names match spec §② and are used consistently in Task 5 and Phase 2.
