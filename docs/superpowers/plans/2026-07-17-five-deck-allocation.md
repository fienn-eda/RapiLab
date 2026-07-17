# Five-Deck Allocation (Phase 5, backend) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Split the user's roster into up to five disjoint 5-unit decks maximizing summed damage against one boss, exposed as `POST /api/recommend-raid`, inside a seconds-to-~1-minute budget at the measured 103 ms/sim.

**Architecture:** Prika rotation prerequisite → shape-constrained combination enumeration ((1,1,3)/(1,2,2)/(2,1,2)) → budget-aware single-deck search (canonical-order scoring, permutations only for the top K, marginal-contribution candidate cut with synergy-set and SG-theme guards) → greedy peeling + same-tier swap hill-climb. Spec: `docs/superpowers/specs/2026-07-17-five-deck-allocation-design.md`.

**Tech Stack:** Python 3 stdlib. Search-level multiprocessing is deliberately NOT in this plan (YAGNI — listed in the docs task as the future throughput lever if quality/budget proves insufficient). The spec's frontend component ships as a separate follow-up plan once this API is live.

## Global Constraints

- Run tests from `backend/`: `PYTHONIOENCODING=utf-8 python3 -m pytest tests/ -q` — interpreter is **`python3`, NOT `python`**.
- Baseline suite: **659 passed**. Existing tests may not be edited, with ONE sanctioned exception in Task 1: the Prika `one_more_song` fixture gains the NEW key `"description_value_06": "21"` (extension verified against the L10 lootandwaifus text "Effect 4: Affects self. Cooldown of Burst Skill ▲ 21 sec." — existing keys untouched).
- Fienn domain rules baked in: deck shapes limited to (1,1,3)/(1,2,2)/(2,1,2); synergy sets `{mint, prika}` and `{mast-romantic-maid, anchor-innocent-maid}` must survive candidate cuts together; SG B3 units are only meaningful with Tove.
- **No git remote**: commit only; never push or open PRs.
- If working in a fresh worktree, `data/` (gitignored) is absent — copy it first: `Copy-Item -Recurse C:\Users\fienn\Desktop\NikkeDeckBuilder\data <worktree-root>\data` (PowerShell).
- Search-layer unit tests stub `evaluate_deck` via monkeypatch (each sim costs ~103 ms — real sims belong only in the few end-to-end tests).

---

### Task 1: Prika Encore self burst-cooldown +21 s (rotation prerequisite)

**Files:**
- Modify: `backend/app/skill_rules/prika.py`
- Modify: `backend/tests/test_skill_rules_prika.py` (fixture key ADDED + new test appended)

**Interfaces:**
- Consumes: existing `Pulse` (`app.effects`), the `burst_cooldown_reduction_sec` pulse path — `raid_simulator.on_full_burst_end` sums drained pulse values per slug (self scope → caster only, see `cdr_targets` ~line 470) and `burst_cycle` applies `last_used_at[slug] -= value`, so a NEGATIVE value pushes the owner's next burst later. Verify `cdr_targets` handles `"self"` before relying on it; if it doesn't, STOP and report (do not extend it silently).
- Produces: with Mint present, the simulator reproduces Fienn's rotation — Prika bursts only in cycle 1, Mint takes every later tier-2 slot (each Encore adds +21 s to Prika's cooldown, outrunning the ~20 s cycle forever).

- [ ] **Step 1: Write the failing rotation test**

Append to `backend/tests/test_skill_rules_prika.py` (reuse the module's existing Prika fixture dict for `build_prika_rules`; the snippet below names it `PRIKA` — adapt to the actual fixture name in the file, and add `"description_value_06": "21"` to its `one_more_song` sub-dict):

```python
def test_prika_bursts_once_then_mint_owns_the_tier2_slot():
    # Fienn (2026-07-17): Encore raises Prika's own burst cooldown +21s per
    # trigger, so after her cycle-1 burst Mint bursts every later cycle.
    # Encore itself only needs a deck member SLUGGED "mint" to burst (the
    # ally_bursted gate) - Mint's own rules aren't required for rotation.
    from app.raid_simulator import simulate_raid

    deck = [
        {"slug": "b1", "burst_tier": 1, "element": "Fire", "cooldown": 20.0},
        {"slug": "prika", "burst_tier": 2, "element": "Water", "cooldown": 40.0},
        {"slug": "mint", "burst_tier": 2, "element": "Iron", "cooldown": 20.0},
        {"slug": "b3", "burst_tier": 3, "element": "Fire", "cooldown": 20.0},
    ]
    result = simulate_raid(
        deck=deck,
        rules_by_slug={"prika": build_prika_rules(PRIKA), "b1": [], "mint": [], "b3": []},
        burst_damage_percents={},
        base_stats={m["slug"]: {"atk": 10000} for m in deck},
        enemy_def=0,
        gauge_charge_time=5.0,
        fight_duration=180.0,
        base_crit_rate=0.0,
    )
    bursts = [e for e in result["events"] if e["type"] == "burst" and e["tier"] == 2]
    prika_bursts = [e for e in bursts if e["slug"] == "prika"]
    mint_bursts = [e for e in bursts if e["slug"] == "mint"]
    assert len(prika_bursts) == 1 and prika_bursts[0]["time"] < 10.0
    assert len(mint_bursts) >= 5  # every later cycle
```

- [ ] **Step 2: Run it to verify it fails**

Run (from `backend/`): `PYTHONIOENCODING=utf-8 python3 -m pytest tests/test_skill_rules_prika.py -q`
Expected: the new test FAILS with `len(prika_bursts) == 1` violated (she re-bursts around t≈45 today); every pre-existing test in the file still passes.

- [ ] **Step 3: Implement in `backend/app/skill_rules/prika.py`**

In `build_prika_rules`, read the new slot next to the other encore values:

```python
    encore_cd_increase = float(encore["description_value_06"])
```

In `apply_encore`, after the existing `registry.add(...)`, add (plus `Pulse` to the `app.effects` import):

```python
        # Effect 4: "Affects self. Cooldown of Burst Skill ▲ 21 sec." - a
        # NEGATIVE value through the burst-CDR pulse path pushes Prika's own
        # next burst later, which is what makes Mint own the tier-2 slot from
        # cycle 2 on (each Encore outruns the ~20s cycle).
        registry.add_pulse(
            Pulse("burst_cooldown_reduction_sec", -encore_cd_increase, "self", caster_slug)
        )
```

Update the module docstring: move the "Encore's ... self Burst-cooldown +21 sec" line from "Not modeled" to the modeled list (rotation-relevant: it displaces Mint's burst in the sim when missing).

- [ ] **Step 4: Run the file's tests, then the full suite**

Run: `PYTHONIOENCODING=utf-8 python3 -m pytest tests/test_skill_rules_prika.py tests/test_skill_value_assembly.py -q`
Expected: all pass (the assembly harness now also verifies slot 06 == 21 against real data).
Run: `PYTHONIOENCODING=utf-8 python3 -m pytest tests/ -q`
Expected: `660 passed` (659 + 1).

- [ ] **Step 5: Commit**

```bash
git add backend/app/skill_rules/prika.py backend/tests/test_skill_rules_prika.py
git commit -m "feat: encode Prika Encore self burst-cooldown +21s (Mint owns tier-2 slot from cycle 2)"
```

---

### Task 2: Shape-constrained combination enumeration

**Files:**
- Modify: `backend/app/deck_search.py`
- Test: `backend/tests/test_deck_search.py` (append only)

**Interfaces:**
- Consumes: nothing new (pure combinatorics on `.burst_tier`, like `feasible_orderings`).
- Produces: `ALLOWED_SHAPES` and `shape_combinations(roster)` yielding canonical tier-ordered 5-unit lists. Tasks 3-5 enumerate through it. `feasible_orderings` stays untouched (existing tests/API compat until Task 6).

- [ ] **Step 1: Write the failing tests**

Append to `backend/tests/test_deck_search.py` (it already defines `FakeUnit`/`fake_roster`):

```python
def test_shape_combinations_yields_only_the_three_real_shapes():
    from app.deck_search import shape_combinations
    roster = fake_roster([1, 1, 1, 2, 2, 2, 3, 3, 3, 3])
    shapes = {tuple(sum(1 for u in c if u.burst_tier == t) for t in (1, 2, 3))
              for c in shape_combinations(roster)}
    assert shapes == {(1, 1, 3), (1, 2, 2), (2, 1, 2)}


def test_shape_combinations_count_and_canonical_order():
    from app.deck_search import shape_combinations
    roster = fake_roster([1, 1, 2, 2, 3, 3, 3])  # 2 B1, 2 B2, 3 B3
    combos = list(shape_combinations(roster))
    # (1,1,3): 2*2*C(3,3)=4 · (1,2,2): 2*1*C(3,2)=6 · (2,1,2): 1*2*3=6
    assert len(combos) == 16
    for combo in combos:
        assert [u.burst_tier for u in combo] == sorted(u.burst_tier for u in combo)


def test_shape_combinations_empty_when_a_tier_is_missing():
    from app.deck_search import shape_combinations
    assert list(shape_combinations(fake_roster([1, 1, 3, 3, 3]))) == []
```

- [ ] **Step 2: Run to verify failure** — `PYTHONIOENCODING=utf-8 python3 -m pytest tests/test_deck_search.py -q` → ImportError on `shape_combinations`.

- [ ] **Step 3: Implement in `backend/app/deck_search.py`**

```python
# Real decks come in exactly these B1/B2/B3 shapes (Fienn, 2026-07-17);
# "at least one of each tier" also admits shapes that never occur in play.
ALLOWED_SHAPES = ((1, 1, 3), (1, 2, 2), (2, 1, 2))


def shape_combinations(roster):
    """Canonical tier-ordered 5-unit combinations, restricted to the shapes
    real play uses. Pure combinatorics on `.burst_tier` (like
    feasible_orderings); intra-tier order is the input order."""
    by_tier = {1: [], 2: [], 3: []}
    for unit in roster:
        if unit.burst_tier in by_tier:
            by_tier[unit.burst_tier].append(unit)
    for n1, n2, n3 in ALLOWED_SHAPES:
        for c1 in combinations(by_tier[1], n1):
            for c2 in combinations(by_tier[2], n2):
                for c3 in combinations(by_tier[3], n3):
                    yield list(c1) + list(c2) + list(c3)
```

- [ ] **Step 4: Run the file's tests** — expected all pass; full suite `663 passed` (660 + 3).

- [ ] **Step 5: Commit**

```bash
git add backend/app/deck_search.py backend/tests/test_deck_search.py
git commit -m "feat: shape-constrained deck combination enumeration"
```

---

### Task 3: Budget-aware single-deck search (canonical → top-K permutations)

**Files:**
- Modify: `backend/app/deck_search.py`
- Test: `backend/tests/test_deck_search.py` (append only)

**Interfaces:**
- Consumes: `shape_combinations`, `evaluate_deck`, `_summarize` (existing), `prune_candidate_pool` (Task 4 — this task calls it only behind the budget check; until Task 4 lands, define it here as raising `NotImplementedError` and keep this task's tests under the budget so the branch is never taken).
- Produces: `search_best_decks(roster, boss, top_n=5, sim_budget=1200, permutation_top_k=40) -> list[summary]` (same summary dicts as `find_best_decks`). Tasks 5-6 call it.

- [ ] **Step 1: Write the failing tests**

Append to `backend/tests/test_deck_search.py`:

```python
def _fake_scorer(scores_by_key):
    # Stand-in for evaluate_deck: scores keyed by (frozenset of slugs, tuple of
    # slugs) with fallbacks, so tests can rank combinations and orderings
    # without running 103ms sims.
    def fake_evaluate(ordered_deck, boss):
        key_exact = tuple(u.slug for u in ordered_deck)
        key_set = frozenset(key_exact)
        total = scores_by_key.get(key_exact, scores_by_key.get(key_set, 1.0))
        return {"total_damage": total, "damage_log": []}
    return fake_evaluate


def test_search_best_decks_refines_order_only_for_top_combos(monkeypatch):
    import app.deck_search as ds
    roster = fake_roster([1, 2, 2, 3, 3, 3])
    # Canonical order of the {u1,u2} B2 pair is (u1, u2); make the swapped
    # order strictly better so only permutation refinement can find it.
    best_set = frozenset({"u0", "u1", "u2", "u3", "u4"})
    scores = {best_set: 100.0, ("u0", "u2", "u1", "u3", "u4"): 130.0}
    monkeypatch.setattr(ds, "evaluate_deck", _fake_scorer(scores))
    results = ds.search_best_decks(roster, BossProfile(), top_n=1)
    assert results[0]["total_damage"] == 130.0
    assert results[0]["deck"][1:3] == ["u2", "u1"]


def test_search_best_decks_respects_permutation_top_k(monkeypatch):
    import app.deck_search as ds
    roster = fake_roster([1, 2, 2, 3, 3, 3])
    calls = []

    def counting_evaluate(ordered_deck, boss):
        calls.append(tuple(u.slug for u in ordered_deck))
        return {"total_damage": 1.0, "damage_log": []}

    monkeypatch.setattr(ds, "evaluate_deck", counting_evaluate)
    ds.search_best_decks(roster, BossProfile(), top_n=1, permutation_top_k=1)
    # 5 canonical combos for this roster ((1,1,3): 2, (1,2,2): 3); with
    # permutation_top_k=1 exactly ONE combo is refined - 4 orderings if it is
    # a (1,2,2) (2!x2!), 6 if a (1,1,3) (3!). All-refined would be 29 calls.
    assert 5 < len(calls) <= 5 + 6
```

- [ ] **Step 2: Run to verify failure** — AttributeError/ImportError on `search_best_decks`.

- [ ] **Step 3: Implement in `backend/app/deck_search.py`**

```python
def _intra_tier_orderings(combo):
    by_tier = {1: [], 2: [], 3: []}
    for unit in combo:
        by_tier[unit.burst_tier].append(unit)
    for o1 in permutations(by_tier[1]):
        for o2 in permutations(by_tier[2]):
            for o3 in permutations(by_tier[3]):
                yield list(o1) + list(o2) + list(o3)


def prune_candidate_pool(roster, boss):  # implemented in the next task
    raise NotImplementedError


def search_best_decks(roster, boss: BossProfile, top_n=5, sim_budget=1200, permutation_top_k=40):
    """Budget-aware replacement for exhaustive find_best_decks: canonical
    tier-order scores rank the shape combinations (intra-tier order only
    decides nuker-vs-backup roles), and only the top K get their permutations
    evaluated. When canonical enumeration alone would blow the budget, the
    roster is first cut to a candidate pool (prune_candidate_pool)."""
    pool = list(roster)
    combos = list(shape_combinations(pool))
    if len(combos) > sim_budget:
        pool = prune_candidate_pool(roster, boss)
        combos = list(shape_combinations(pool))
    canonical = sorted(
        ((evaluate_deck(combo, boss)["total_damage"], i) for i, combo in enumerate(combos)),
        reverse=True,
    )
    refined = []
    for _, i in canonical[:permutation_top_k]:
        for ordered in _intra_tier_orderings(combos[i]):
            refined.append(_summarize(ordered, evaluate_deck(ordered, boss)))
    refined.sort(key=lambda entry: entry["total_damage"], reverse=True)
    return refined[:top_n]
```

Note: the canonical pass keeps only `total_damage` (cheap) and re-evaluates
orderings in the refinement pass — the canonical ordering is among each
combo's `_intra_tier_orderings`, so its score is never lost.

- [ ] **Step 4: Run tests** — file green; full suite `665 passed` (663 + 2).

- [ ] **Step 5: Commit**

```bash
git add backend/app/deck_search.py backend/tests/test_deck_search.py
git commit -m "feat: budget-aware single-deck search (canonical scoring + top-K permutation refinement)"
```

---

### Task 4: Candidate pool cut (marginal contribution + synergy/theme guards)

**Files:**
- Modify: `backend/app/deck_search.py` (replace the `NotImplementedError` stub)
- Test: `backend/tests/test_deck_search.py` (append only)

**Interfaces:**
- Consumes: `evaluate_deck`, `shape_combinations`.
- Produces: `prune_candidate_pool(roster, boss) -> list[unit]` plus module constants `SYNERGY_SETS`, `WEAPON_SYNERGY_ANCHORS`, `PRUNED_TIER_CAPS`. Units need `.slug`, `.burst_tier`; real NikkeSpecs also expose `.base_stats["atk"]`, `.weapon_stats["damage_percent"]`, `.weapon` — tests' fakes must add those fields.

- [ ] **Step 1: Write the failing tests**

Append to `backend/tests/test_deck_search.py`:

```python
@dataclass
class FakeSpec:
    slug: str
    burst_tier: int
    weapon: str = "AR"
    base_stats: dict = None
    weapon_stats: dict = None

    def __post_init__(self):
        self.base_stats = self.base_stats or {"atk": 1000.0}
        self.weapon_stats = self.weapon_stats or {"damage_percent": 100.0}


def _big_fake_roster():
    units = [FakeSpec(f"b1_{i}", 1) for i in range(4)]
    units += [FakeSpec(f"b2_{i}", 2) for i in range(6)]
    units += [FakeSpec(f"b3_{i}", 3) for i in range(12)]
    return units


def test_prune_candidate_pool_respects_tier_caps(monkeypatch):
    import app.deck_search as ds
    monkeypatch.setattr(ds, "evaluate_deck", _fake_scorer({}))
    pool = ds.prune_candidate_pool(_big_fake_roster(), BossProfile())
    counts = {t: sum(1 for u in pool if u.burst_tier == t) for t in (1, 2, 3)}
    assert counts[1] <= ds.PRUNED_TIER_CAPS[1]
    assert counts[2] <= ds.PRUNED_TIER_CAPS[2]
    assert counts[3] <= ds.PRUNED_TIER_CAPS[3]


def test_prune_keeps_synergy_partners_together(monkeypatch):
    import app.deck_search as ds
    roster = _big_fake_roster()
    roster += [FakeSpec("mint", 2), FakeSpec("prika", 2)]

    def scorer(ordered_deck, boss):
        slugs = {u.slug for u in ordered_deck}
        # the pair measured together is dominant; mint alone is weakest
        if {"mint", "prika"} <= slugs:
            return {"total_damage": 10_000.0, "damage_log": []}
        if "mint" in slugs:
            return {"total_damage": 1.0, "damage_log": []}
        return {"total_damage": 100.0, "damage_log": []}

    monkeypatch.setattr(ds, "evaluate_deck", scorer)
    pool_slugs = {u.slug for u in ds.prune_candidate_pool(roster, BossProfile())}
    assert {"mint", "prika"} <= pool_slugs


def test_prune_includes_sg_theme_around_tove(monkeypatch):
    import app.deck_search as ds
    roster = _big_fake_roster()  # all AR
    roster += [FakeSpec("tove", 1, weapon="AR")]
    roster += [FakeSpec(f"sg_{i}", 3, weapon="SG",
                        base_stats={"atk": 1.0}) for i in range(2)]  # tiny prior

    monkeypatch.setattr(ds, "evaluate_deck", _fake_scorer({}))
    pool_slugs = {u.slug for u in ds.prune_candidate_pool(roster, BossProfile())}
    assert "tove" in pool_slugs
    assert {"sg_0", "sg_1"} <= pool_slugs  # anchored theme survives the cut
```

- [ ] **Step 2: Run to verify failure** — `NotImplementedError` (and missing constants).

- [ ] **Step 3: Implement in `backend/app/deck_search.py`** (replace the stub)

```python
# Curated two-unit sets that only work together (Fienn, 2026-07-17): candidate
# cuts must measure them as a pair and never separate them.
SYNERGY_SETS = (frozenset({"mint", "prika"}),
                frozenset({"mast-romantic-maid", "anchor-innocent-maid"}))

# A weapon-scoped buffer anchors a themed sub-pool: its weapon's B3 attackers
# are only meaningful with it in the deck (Fienn: "SG B3s need Tove"), so they
# join the pool whenever the anchor is rostered, bypassing the mis-contextual
# marginal cut.
WEAPON_SYNERGY_ANCHORS = {"tove": "SG"}

# Per-tier pool caps sized so shape_combinations stays a few hundred combos
# (~103 ms/sim budget); synergy/theme guards may exceed them slightly.
PRUNED_TIER_CAPS = {1: 2, 2: 3, 3: 6}


def _prior(unit):
    # Round-0 prior (no sims): investment-adjusted ATK x weapon hit percent.
    # Only seeds the reference decks - the swap-in measurement corrects it.
    return unit.base_stats["atk"] * unit.weapon_stats["damage_percent"]


def _reference_deck(by_tier, b1):
    return [b1, by_tier[2][0], *by_tier[3][:3]]


def _measure_against(reference, unit, boss):
    # Swap the candidate into its tier slot (B3 replaces the reference's
    # weakest B3, the last one) and score the whole deck.
    slot = {1: 0, 2: 1, 3: 4}[unit.burst_tier]
    deck = list(reference)
    if unit.slug in {u.slug for u in deck}:
        deck_score = evaluate_deck(deck, boss)["total_damage"]
        return deck_score
    deck[slot] = unit
    return evaluate_deck(deck, boss)["total_damage"]


def prune_candidate_pool(roster, boss: BossProfile):
    """Cut the roster to a pool the budget can enumerate. Scores are marginal
    contributions in reference-deck context (two passes: prior-seeded B1, then
    best-measured B1 - CDR holders change cycle count, Fienn rule 2/3), with
    synergy sets measured as pairs and weapon-themed units pulled in around
    their anchor rather than trusting the mis-contextual cut."""
    by_tier = {t: sorted((u for u in roster if u.burst_tier == t),
                         key=_prior, reverse=True) for t in (1, 2, 3)}
    if not (by_tier[1] and by_tier[2] and len(by_tier[3]) >= 3):
        return list(roster)  # too small to cut; search handles infeasibility

    scores = {}
    for reference_b1 in _reference_b1_variants(by_tier, boss):
        reference = _reference_deck(by_tier, reference_b1)
        for unit in roster:
            score = _measure_against(reference, unit, boss)
            scores[unit.slug] = max(scores.get(unit.slug, 0.0), score)

    # Synergy sets: measured as a pair in a (1,2,2) shell; both members share it.
    shell_b1, shell_b3 = by_tier[1][0], by_tier[3][:2]
    slugs = {u.slug: u for u in roster}
    for pair in SYNERGY_SETS:
        if pair <= slugs.keys():
            members = [slugs[s] for s in sorted(pair)]
            deck = [shell_b1, *members, *shell_b3]
            pair_score = evaluate_deck(deck, boss)["total_damage"]
            for member in members:
                scores[member.slug] = max(scores[member.slug], pair_score)

    pool = []
    for tier, cap in PRUNED_TIER_CAPS.items():
        ranked = sorted(by_tier[tier], key=lambda u: scores[u.slug], reverse=True)
        pool.extend(ranked[:cap])

    pool_slugs = {u.slug for u in pool}
    for pair in SYNERGY_SETS:  # companion pull-in
        if pair & pool_slugs and pair <= slugs.keys():
            pool.extend(slugs[s] for s in pair if s not in pool_slugs)
            pool_slugs |= pair
    for anchor, weapon in WEAPON_SYNERGY_ANCHORS.items():  # themed pull-in
        if anchor in slugs:
            themed = [u for u in roster
                      if u.slug == anchor
                      or (u.burst_tier == 3 and getattr(u, "weapon", None) == weapon)]
            pool.extend(u for u in themed if u.slug not in pool_slugs)
            pool_slugs |= {u.slug for u in themed}
    return pool


def _reference_b1_variants(by_tier, boss):
    # Pass 1: prior-seeded B1. Pass 2: the B1 whose swap-in measured best
    # (usually the CDR holder - shorter cycles change everyone's value).
    first = by_tier[1][0]
    yield first
    reference = _reference_deck(by_tier, first)
    best_b1 = max(by_tier[1],
                  key=lambda u: _measure_against(reference, u, boss))
    if best_b1.slug != first.slug:
        yield best_b1
```

- [ ] **Step 4: Run tests** — file green; full suite `668 passed` (665 + 3).

- [ ] **Step 5: Commit**

```bash
git add backend/app/deck_search.py backend/tests/test_deck_search.py
git commit -m "feat: marginal-contribution candidate pool cut with synergy-set and SG-theme guards"
```

---

### Task 5: Greedy peeling + same-tier swap allocation

**Files:**
- Create: `backend/app/deck_allocation.py`
- Test: `backend/tests/test_deck_allocation.py`

**Interfaces:**
- Consumes: `search_best_decks`, `evaluate_deck`, `_summarize`, `shape_combinations` from `app.deck_search`; `BossProfile`.
- Produces: `allocate_decks(roster, boss, num_decks=5, time_budget_sec=45.0) -> {"decks": [summary...], "leftover_slugs": [...]}` — decks ordered as allocated, each summary the `_summarize` dict shape. Task 6's endpoint calls it.

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_deck_allocation.py`:

```python
"""Allocation layer: greedy peeling picks disjoint decks best-first; the
same-tier swap pass recovers the classic greedy mistake (stacking two strong
supporters in deck 1 when splitting them wins). All search/sim calls are
stubbed - real sims live in the API end-to-end test."""
from dataclasses import dataclass

import app.deck_allocation as da
from app.deck_search import BossProfile


@dataclass(frozen=True)
class Unit:
    slug: str
    burst_tier: int


def roster_of(tiers_by_slug):
    return [Unit(s, t) for s, t in tiers_by_slug.items()]


def patch_scorer(monkeypatch, scorer):
    # allocate_decks calls evaluate_deck both directly AND through
    # search_best_decks (deck_search's own module binding) - patch both.
    import app.deck_search as ds

    def fake_evaluate(ordered_deck, boss):
        return {"total_damage": scorer({u.slug for u in ordered_deck}),
                "damage_log": []}

    monkeypatch.setattr(ds, "evaluate_deck", fake_evaluate)
    monkeypatch.setattr(da, "evaluate_deck", fake_evaluate)


def test_greedy_peels_disjoint_decks_best_first(monkeypatch):
    roster = roster_of({
        "a1": 1, "a2": 2, "a3": 3, "a4": 3, "a5": 3,
        "b1": 1, "b2": 2, "b3": 3, "b4": 3, "b5": 3,
    })
    # unambiguous optimum (no score ties): exactly the a-deck, then the b-deck
    def score(slugs):
        if slugs == {"a1", "a2", "a3", "a4", "a5"}:
            return 100.0
        if slugs == {"b1", "b2", "b3", "b4", "b5"}:
            return 50.0
        return 10.0

    patch_scorer(monkeypatch, score)
    out = da.allocate_decks(roster, BossProfile(), num_decks=5, time_budget_sec=0.0)
    assert len(out["decks"]) == 2                      # 10 units -> 2 decks
    assert sorted(out["decks"][0]["deck"]) == ["a1", "a2", "a3", "a4", "a5"]
    used = [slug for d in out["decks"] for slug in d["deck"]]
    assert len(used) == len(set(used))                 # disjoint
    assert out["leftover_slugs"] == []


def test_partial_roster_returns_fewer_decks(monkeypatch):
    roster = roster_of({"a1": 1, "a2": 2, "a3": 3, "a4": 3, "a5": 3, "x": 3})
    # decks containing x score lower, so the leftover is deterministically x
    patch_scorer(monkeypatch, lambda s: 0.5 if "x" in s else 1.0)
    out = da.allocate_decks(roster, BossProfile(), num_decks=5, time_budget_sec=0.0)
    assert len(out["decks"]) == 1                      # only one feasible deck
    assert out["leftover_slugs"] == ["x"]              # honest leftover report


def test_swap_pass_fixes_a_greedy_split(monkeypatch):
    # Two B2 buffers m/n; greedy stacks both winners into deck 1 context via
    # (1,2,2), but the optimum puts one per deck. Scores: a deck with exactly
    # one of {m,n} scores 100; with both, 120; with neither, 10. Greedy total
    # = 120 + 10 = 130; swapped total = 100 + 100 = 200.
    roster = roster_of({
        "m": 2, "n": 2, "a1": 1, "a3": 3, "a4": 3,
        "b1": 1, "b2": 2, "b3": 3, "b4": 3, "b5": 3,
    })

    def score(slugs):
        both = {"m", "n"} <= slugs
        one = bool({"m", "n"} & slugs) and not both
        return 120.0 if both else 100.0 if one else 10.0

    patch_scorer(monkeypatch, score)
    out = da.allocate_decks(roster, BossProfile(), num_decks=2, time_budget_sec=30.0)
    per_deck = [set(d["deck"]) & {"m", "n"} for d in out["decks"]]
    assert all(len(x) == 1 for x in per_deck)          # one buffer per deck
    assert sum(d["total_damage"] for d in out["decks"]) == 200.0
```

- [ ] **Step 2: Run to verify failure** — ModuleNotFoundError on `app.deck_allocation`.

- [ ] **Step 3: Implement `backend/app/deck_allocation.py`**

```python
"""Splits a roster into up to five disjoint decks against ONE boss profile,
maximizing summed damage (Phase 5). Same boss => total = sum of independent
deck scores, so: greedy peeling (best deck on the remaining roster, repeat)
lands near the optimum, and a budget-bounded same-tier swap hill-climb
recovers its classic mistake (stacking synergy cores in deck 1 when splitting
them supports two decks better). No optimality claim - set partitioning is
NP-hard; this is the standard practical combo."""
import time

from app.deck_search import (BossProfile, _intra_tier_orderings, _summarize,
                             evaluate_deck, search_best_decks)


def allocate_decks(roster, boss: BossProfile, num_decks=5, time_budget_sec=45.0):
    deadline = time.monotonic() + time_budget_sec
    remaining = list(roster)
    decks = []  # each: ordered list of units (canonical order from the search)
    by_slug = {u.slug: u for u in roster}
    while len(decks) < num_decks:
        found = search_best_decks(remaining, boss, top_n=1)
        if not found:
            break
        units = [by_slug[slug] for slug in found[0]["deck"]]
        decks.append(units)
        used = {u.slug for u in units}
        remaining = [u for u in remaining if u.slug not in used]

    _swap_pass(decks, remaining, boss, deadline)

    summaries = [_best_ordering_summary(units, boss) for units in decks]
    return {"decks": summaries,
            "leftover_slugs": sorted(u.slug for u in remaining)}


def _score(units, boss):
    return evaluate_deck(units, boss)["total_damage"]


def _swap_pass(decks, leftovers, boss, deadline):
    """Hill-climb: try same-tier unit swaps between two decks (and between a
    deck and the leftovers), re-scoring only the affected deck(s); keep a swap
    iff the summed total improves. Same-tier swaps preserve the deck shapes.
    Loops until a full pass finds no improvement or the deadline passes."""
    if not decks:
        return
    scores = [_score(units, boss) for units in decks]
    improved = True
    while improved and time.monotonic() < deadline:
        improved = False
        for i in range(len(decks)):
            for j in range(i + 1, len(decks)):
                improved |= _try_pair_swaps(decks, scores, i, j, boss, deadline)
            improved |= _try_leftover_swaps(decks, scores, i, leftovers, boss, deadline)


def _try_pair_swaps(decks, scores, i, j, boss, deadline):
    improved = False
    for a in range(5):
        for b in range(5):
            if time.monotonic() >= deadline:
                return improved
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


def _try_leftover_swaps(decks, scores, i, leftovers, boss, deadline):
    improved = False
    for a in range(5):
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


def _best_ordering_summary(units, boss):
    # Final polish: the swap pass scored canonical orders only; pick the best
    # intra-tier ordering for the finished deck (a handful of sims per deck).
    best = None
    for ordered in _intra_tier_orderings(units):
        summary = _summarize(ordered, evaluate_deck(ordered, boss))
        if best is None or summary["total_damage"] > best["total_damage"]:
            best = summary
    return best
```

Note for the swap test: with `time_budget_sec=30.0` the stubbed scorer makes
each "sim" free, so the pass runs to no-improvement, and greedy's 120/10 split
must end 100/100.

- [ ] **Step 4: Run tests** — file green; full suite `671 passed` (668 + 3).

- [ ] **Step 5: Commit**

```bash
git add backend/app/deck_allocation.py backend/tests/test_deck_allocation.py
git commit -m "feat: five-deck allocation via greedy peeling + same-tier swap hill-climb"
```

---

### Task 6: API endpoint + switch /api/recommend to the budget-aware search + docs

**Files:**
- Modify: `backend/app/api.py`
- Test: `backend/tests/test_api_recommend.py` (append only)
- Modify: `docs/roadmap.md`, `docs/encoded-nikkes.md`(only if Prika row wording needs the CD note — otherwise skip)

**Interfaces:**
- Consumes: `allocate_decks` (Task 5), `search_best_decks` (Task 3), existing `load_roster`/`_reject_unknown_overload_options`/`RecommendRequest` machinery in api.py.
- Produces: `POST /api/recommend-raid` — request = same roster/boss payload plus optional `num_decks` (default 5, 1..5); response = `{"decks": [...], "combined_total_damage": float, "excluded_slugs": [...], "leftover_slugs": [...]}` with the same per-deck fields `/api/recommend` uses. `/api/recommend` internally switches `find_best_decks` → `search_best_decks` (identical behavior for rosters small enough to enumerate — the cut only engages over budget).

- [ ] **Step 1: Write the failing tests**

Append to `backend/tests/test_api_recommend.py`:

```python
def test_recommend_raid_partitions_roster_and_reports_leftovers():
    roster = [_nikke(slug) for slug in FEASIBLE] + [_nikke("totally-unknown")]
    response = client.post("/api/recommend-raid", json={"roster": roster, "boss": BOSS})
    assert response.status_code == 200
    body = response.json()
    assert body["excluded_slugs"] == ["totally-unknown"]
    assert len(body["decks"]) == 1                      # 5 loadable units -> 1 deck
    deck = body["decks"][0]
    assert set(deck) == {"deck", "total_damage", "burst_damage", "normal_attack_damage"}
    assert sorted(deck["deck"]) == sorted(FEASIBLE)
    assert body["leftover_slugs"] == []
    assert body["combined_total_damage"] == deck["total_damage"]


def test_recommend_raid_infeasible_is_422_naming_exclusions():
    response = client.post(
        "/api/recommend-raid",
        json={"roster": [_nikke("totally-unknown")] * 5, "boss": BOSS},
    )
    assert response.status_code == 422
    assert "totally-unknown" in str(response.json()["detail"])
```

- [ ] **Step 2: Run to verify failure** — 404 on the new route.

- [ ] **Step 3: Implement in `backend/app/api.py`**

Import `allocate_decks` and `search_best_decks`; in the existing `recommend`
handler replace `find_best_decks(...)` with `search_best_decks(...)` (same
arguments). Then add, following the existing request/response model style in
the file:

```python
class RecommendRaidRequest(RecommendRequest):
    num_decks: int = Field(5, ge=1, le=5)


class RecommendRaidResponse(BaseModel):
    decks: list[DeckSummary]
    combined_total_damage: float
    excluded_slugs: list[str]
    leftover_slugs: list[str]


@app.post("/api/recommend-raid", response_model=RecommendRaidResponse)
def recommend_raid(request: RecommendRaidRequest) -> RecommendRaidResponse:
    _reject_unknown_overload_options(request.roster)
    specs, excluded = load_roster(request.roster)
    boss = BossProfile(
        element=request.boss.element,
        core_hittable=request.boss.core_hittable,
        enemy_def=request.boss.enemy_def,
        fight_duration=request.boss.fight_duration,
        part_destructible=request.boss.part_destructible,
    )
    result = allocate_decks(specs, boss, num_decks=request.num_decks)
    if not result["decks"]:
        raise HTTPException(
            status_code=422,
            detail=f"no feasible deck from the usable roster (excluded: {excluded})",
        )
    return RecommendRaidResponse(
        decks=result["decks"],
        combined_total_damage=sum(d["total_damage"] for d in result["decks"]),
        excluded_slugs=excluded,
        leftover_slugs=result["leftover_slugs"],
    )
```

Adapt names to the file's actual model/style: if api.py already has a
per-deck summary model, reuse it for `decks`; if `/api/recommend` returns
plain dicts instead, declare `decks: list[dict]` and serialize exactly the
way that handler does (same four keys, raw `result` key dropped).
`BossProfile` construction must mirror the existing handler's, whatever
fields it passes.

- [ ] **Step 4: Run the API tests, then the full suite**

Run: `PYTHONIOENCODING=utf-8 python3 -m pytest tests/test_api_recommend.py -q`
Expected: all pass (existing `/api/recommend` tests unchanged and green — the
switch to `search_best_decks` must not move them; if one fails, the search is
diverging on a small roster and the bug is in Task 3's code, not the test).
Run: `PYTHONIOENCODING=utf-8 python3 -m pytest tests/ -q`
Expected: `673 passed` (671 + 2).

- [ ] **Step 5: Measure real-roster allocation wall-clock (spec's perf smoke, run manually — too slow for the suite)**

Write a throwaway script (do NOT commit it) that builds the full loadable
roster the way `scripts/bench_evaluate_deck.py` builds its 5 units (same
`_nikke` payload for every slug in `app.skill_rules.registry.ENCODED_SLUGS`,
loaded via `load_roster` — excluded ones drop out), calls
`allocate_decks(specs, BossProfile(element="Water", fight_duration=180.0))`,
and prints `time.monotonic()` elapsed plus each deck's slugs/total. Record
the elapsed seconds — expected within the spec's seconds-to-~1-minute budget
(the tier caps were sized for it); if it materially exceeds ~90 s, record the
number and report it (constants tuning is the controller's decision, not
yours).

- [ ] **Step 6: Update docs**

`docs/roadmap.md`: mark Phase 5 as 🔄 in the 한눈에 보기 table with one line
(백엔드 완료 — greedy+swap, `/api/recommend-raid`; 프론트 배선은 후속 소플랜),
update the top summary test count to 673 and add the measured allocation
wall-clock from Step 5, note the Prika Encore CD encode under "Phase 5 선행
소작업" as `[x]`. Also record the future throughput lever: "시뮬 병렬화
(ProcessPool)는 품질/예산이 실측으로 부족할 때만".

- [ ] **Step 7: Commit**

```bash
git add backend/app/api.py backend/tests/test_api_recommend.py docs/roadmap.md
git commit -m "feat: POST /api/recommend-raid five-deck allocation endpoint; recommend switches to budget-aware search"
```
