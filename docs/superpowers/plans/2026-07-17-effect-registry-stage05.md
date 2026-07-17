# EffectRegistry Stage 0.5 (Epoch Memo) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Cut `total_for` call count ~10× by memoizing the fixed 18-stat damage bundle per (target, state-epoch), targeting ≤50 ms per 180 s sim (Stage 0 landed at 133.66 ms) with bit-identical outputs.

**Architecture:** `EffectRegistry.state_epoch(target, now)` bisects a per-(slug, element) merged boundary timeline (union over ALL stats); within one epoch every stat total is constant, so `raid_simulator` resolves the whole stat bundle once per `(slug, epoch, registry.version)`. Spec: `docs/superpowers/specs/2026-07-17-effect-registry-performance-design.md`, Stage 0.5 section.

**Tech Stack:** Python 3 stdlib only.

## Global Constraints

- Run tests from `backend/`: `PYTHONIOENCODING=utf-8 python3 -m pytest tests/ -q` — the interpreter is **`python3`, NOT `python`**.
- Baseline suite: **656 passed**. No existing test may be edited; outputs must stay bit-identical (never relax an exact-equality assert).
- `EffectRegistry`: existing methods keep exact signatures/semantics; the ONLY additions are `state_epoch(target, now)` and a read-only `version` property (spec amendment).
- Only these files change: `backend/app/effects.py`, `backend/app/raid_simulator.py`, new `backend/tests/test_effects_state_epoch.py`, `docs/roadmap.md`, this plan file.
- **No git remote**: commit only; never push or open PRs.
- If working in a fresh worktree, `data/` (gitignored) is absent — copy it first: `Copy-Item -Recurse C:\Users\fienn\Desktop\NikkeDeckBuilder\data <worktree-root>\data` (PowerShell).
- If the measured result still exceeds 50 ms after Task 2, do NOT add machinery — record the number and profile findings (spec stop condition).

---

### Task 1: `state_epoch` + `version` on EffectRegistry

**Files:**
- Modify: `backend/app/effects.py`
- Create: `backend/tests/test_effects_state_epoch.py`

**Interfaces:**
- Consumes: existing `Effect`, `EffectRegistry`, `_matches_scope`, `bisect_right` (already imported).
- Produces: module-level `_matches_target(effect, target) -> bool`; `EffectRegistry.version` (read-only int property); `EffectRegistry.state_epoch(target: dict, now: float) -> int`. Task 2 keys memos as `(slug, state_epoch(...), version)`.

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_effects_state_epoch.py`:

```python
"""state_epoch semantics: the epoch index changes exactly at the boundaries of
effects MATCHING the target (any stat), never at unrelated ones - the
invariant raid_simulator's stat-bundle memo (Stage 0.5) relies on."""
from app.effects import Effect, EffectRegistry

A = {"slug": "a", "element": "Fire"}
B = {"slug": "b", "element": "Water"}


def test_state_epoch_changes_only_at_matching_boundaries():
    reg = EffectRegistry()
    reg.add(Effect("atk_percent", 0.1, "squad", 5.0, "a"), applied_at=1.0)
    # self-scoped to "b": its boundaries must NOT create epochs for target A
    reg.add(Effect("crit_rate", 0.05, "self", None, "b"), applied_at=2.0)
    assert reg.state_epoch(A, 0.0) == reg.state_epoch(A, 0.9)   # before anything
    assert reg.state_epoch(A, 1.0) != reg.state_epoch(A, 0.9)   # start boundary
    assert reg.state_epoch(A, 3.0) == reg.state_epoch(A, 1.0)   # b's start is invisible to A
    assert reg.state_epoch(A, 6.0) != reg.state_epoch(A, 3.0)   # end boundary (1.0 + 5.0)
    assert reg.state_epoch(B, 2.0) != reg.state_epoch(B, 1.9)   # self-scope boundary for B


def test_state_epoch_covers_element_and_slugs_scopes():
    reg = EffectRegistry()
    reg.add(Effect("atk_percent", 0.1, "element:Fire", 4.0, "x"), applied_at=1.0)
    reg.add(Effect("flat_atk", 10.0, "slugs:b", 2.0, "x"), applied_at=7.0)
    assert reg.state_epoch(A, 1.0) != reg.state_epoch(A, 0.5)   # Fire matches A
    assert reg.state_epoch(B, 1.0) == reg.state_epoch(B, 0.5)   # not Water
    assert reg.state_epoch(B, 7.5) != reg.state_epoch(B, 6.5)   # slugs:b matches B
    assert reg.state_epoch(A, 7.5) == reg.state_epoch(A, 6.5)   # not A


def test_version_and_epoch_react_to_every_mutation_kind():
    reg = EffectRegistry()
    v0 = reg.version
    e0 = reg.state_epoch(A, 10.0)
    reg.add(Effect("atk_percent", 0.1, "squad", None, "x"), applied_at=5.0)
    v1 = reg.version
    assert v1 != v0
    assert reg.state_epoch(A, 10.0) != e0            # cache rebuilt, boundary seen
    reg.add_refreshing(Effect("atk_percent", 0.1, "squad", 3.0, "x"), applied_at=6.0)
    v2 = reg.version
    assert v2 != v1
    reg.truncate_open_ended("atk_percent", "x", now=8.0)
    assert reg.version != v2
```

- [ ] **Step 2: Run them to verify they fail**

Run (from `backend/`): `PYTHONIOENCODING=utf-8 python3 -m pytest tests/test_effects_state_epoch.py -q`
Expected: FAIL — `AttributeError: 'EffectRegistry' object has no attribute 'state_epoch'` (or `version`).

- [ ] **Step 3: Implement in `backend/app/effects.py`**

3a. Add module-level `_matches_target` directly below `_matches_scope`:

```python
def _matches_target(effect: Effect, target: dict) -> bool:
    """One matching semantics for both the per-stat segment tables and the
    merged epoch timeline: "self" matches via source_slug, everything else
    via _matches_scope."""
    if effect.scope == "self":
        return effect.source_slug == target["slug"]
    return _matches_scope(effect.scope, target)
```

3b. In `__init__`, add one line next to `self._segment_tables = ...`:

```python
        self._epoch_tables: dict[tuple, tuple[int, list]] = {}
```

3c. Rewrite `_build_segment_table`'s scope filter to use the helper — replace

```python
            if effect.scope == "self":
                if effect.source_slug != target["slug"]:
                    continue
            elif not _matches_scope(effect.scope, target):
                continue
```

with

```python
            if not _matches_target(effect, target):
                continue
```

3d. Add to `EffectRegistry` (below `total_for`/`_build_segment_table`):

```python
    @property
    def version(self) -> int:
        """Monotonic mutation counter - lets callers key their own memos on
        registry state (see raid_simulator's stat-bundle memo)."""
        return self._version

    def state_epoch(self, target: dict, now: float) -> int:
        """Index of the piecewise-constant state segment `now` falls in for
        this target: within one epoch NO effect matching the target starts or
        ends (under any stat), so every stat total is constant - callers may
        resolve whole stat bundles once per (target, epoch, version)."""
        key = (target["slug"], target.get("element"))
        cached = self._epoch_tables.get(key)
        if cached is None or cached[0] != self._version:
            boundary_set = set()
            for effect, applied_at in self._entries:
                if not _matches_target(effect, target):
                    continue
                boundary_set.add(applied_at)
                if effect.duration is not None:
                    boundary_set.add(applied_at + effect.duration)
            cached = (self._version, sorted(boundary_set))
            self._epoch_tables[key] = cached
        return bisect_right(cached[1], now)
```

- [ ] **Step 4: Run the new tests, the parity net, then the full suite**

Run: `PYTHONIOENCODING=utf-8 python3 -m pytest tests/test_effects_state_epoch.py tests/test_effects_parity.py -q`
Expected: `5 passed`
Run: `PYTHONIOENCODING=utf-8 python3 -m pytest tests/ -q`
Expected: `659 passed` (656 + 3 new)

- [ ] **Step 5: Commit**

```bash
git add backend/app/effects.py backend/tests/test_effects_state_epoch.py
git commit -m "feat: EffectRegistry.state_epoch + version for caller-side bundle memos"
```

---

### Task 2: Stat-bundle memo in raid_simulator

**Files:**
- Modify: `backend/app/raid_simulator.py` (module constant near `_TYPE_BUCKETS` at ~line 220; inside `simulate_raid`: `crit_rate_for`/`_damage_instance` at ~lines 285-334, `normal_attack_type` at ~336-344, `_normal_attack_percent` at ~839-847, and `normal_attack_type` call sites)

**Interfaces:**
- Consumes: `registry.state_epoch(target, now)` and `registry.version` from Task 1.
- Produces: no external interface change — `simulate_raid`'s signature and outputs are untouched (outputs bit-identical).

- [ ] **Step 1: Add the bundle-stat superset constant**

Directly below the `_TYPE_BUCKETS` dict (module level):

```python
# Every registry stat phase-2 damage computation can read (_damage_instance,
# normal_attack_type, _normal_attack_percent). All are constant within one
# state epoch, so the whole bundle is resolved once per (target, epoch,
# registry version) - see _stat_bundle in simulate_raid.
_BUNDLE_STATS = (
    "enemy_def_percent", "atk_percent", "flat_atk", "other_elemental_bonus",
    "other_critical_damage_sources", "crit_rate", "other_core_damage_sources",
    "charge_damage_bonus", "attack_damage_up", "damage_to_parts_up",
    "pierce_damage_up", "damage_taken_up",
    "sustained_damage_up", "distributed_damage_up", "true_damage_up",
    "projectile_explosion_damage_up",
    "normal_attacks_deal_true", "normal_attack_damage_multiplier",
)
```

- [ ] **Step 2: Replace `crit_rate_for` with `_stat_bundle` and rewire `_damage_instance`**

Inside `simulate_raid`, replace the current `crit_rate_for` definition:

```python
    def crit_rate_for(target, time):
        return min(1.0, base_crit_rate + registry.total_for("crit_rate", target, time))
```

with:

```python
    stat_bundles = {}

    def _stat_bundle(slug, time):
        # All _BUNDLE_STATS are constant within one state epoch, so resolve
        # them once per (target, epoch); the version key drops stale bundles
        # whenever the registry mutates, which keeps replay-late effects
        # behaving exactly as per-stat queries did.
        target = target_for(slug)
        key = (slug, registry.state_epoch(target, time), registry.version)
        bundle = stat_bundles.get(key)
        if bundle is None:
            bundle = {stat: registry.total_for(stat, target, time) for stat in _BUNDLE_STATS}
            stat_bundles[key] = bundle
        return bundle
```

Then rewrite `_damage_instance`'s body so every registry read comes from one
bundle (keep the existing comments about True Damage and Full Burst Bonus in
place; only the lookup mechanics change):

```python
    def _damage_instance(
        slug, percent, time, damage_type="attack", extra_charge_bonus=0.0, extra_flat_atk=0.0,
        full_burst_bonus_eligible=False,
    ):
        bundle = _stat_bundle(slug, time)
        # True Damage ignores enemy DEF (nikke.gg glossary).
        instance_enemy_def = 0 if damage_type == "true" else enemy_def
        # Full Burst Bonus only applies to damage a unit's skill text describes
        # as "additional damage" (Fienn, 2026-07-12) - i.e. damage actually
        # computed later than cast time, which can land inside a Full Burst
        # window. `full_burst_bonus_eligible` is an explicit per-instance opt-in
        # (set by the caller from that skill-text signal); ordinary cast-time
        # damage never sets it, so this stays inert for every other unit.
        in_full_burst = full_burst_bonus_eligible and any(
            start <= time < end for start, end in full_burst_windows
        )
        terms = dict(
            atk=base_stats[slug]["atk"],
            attack_coefficient=percent / 100,
            enemy_def=instance_enemy_def,
            enemy_def_percent=bundle["enemy_def_percent"],
            atk_percent=bundle["atk_percent"],
            flat_atk=bundle["flat_atk"] + extra_flat_atk,
            other_elemental_bonus=bundle["other_elemental_bonus"],
            other_critical_damage_sources=bundle["other_critical_damage_sources"],
            crit_rate=min(1.0, base_crit_rate + bundle["crit_rate"]),
            core_hit_bonus=CORE_HIT_BONUS if core_hittable else 0.0,
            other_core_damage_sources=(
                bundle["other_core_damage_sources"] if core_hittable else 0.0
            ),
            full_burst_bonus=1.0 if in_full_burst else 0.0,
            element_multiplier=element_bonus_for(slug),
            charge_damage_bonus=bundle["charge_damage_bonus"] + extra_charge_bonus,
            attack_damage_up=bundle["attack_damage_up"],
            damage_to_parts_up=bundle["damage_to_parts_up"],
            pierce_damage_up=bundle["pierce_damage_up"],
            damage_taken_up=bundle["damage_taken_up"],
        )
        # Type-specific Damage-Up buckets apply only to instances of that type.
        for bucket in _TYPE_BUCKETS[damage_type]:
            terms[bucket] = bundle[bucket]
        return calculate_damage(**terms)
```

(`crit_rate_for` had exactly one caller — the `crit_rate=` term above — so it
is deleted, not kept as a wrapper.)

- [ ] **Step 3: Rewire `normal_attack_type` and `_normal_attack_percent`**

`normal_attack_type` drops its now-unused `target` parameter:

```python
    def normal_attack_type(slug, weapon, time):
        # A skill can convert a unit's normal attacks to a damage type for a
        # window (e.g. Takina Inoue's burst: "normal attacks deal true damage").
        if _stat_bundle(slug, time)["normal_attacks_deal_true"] > 0:
            return "true"
        # Otherwise a rocket launcher's normal attacks are projectile explosions.
        if weapon["weapon"] == "RL":
            return "projectile_explosion"
        return "attack"
```

Find its call sites (`grep -n "normal_attack_type(" backend/app/raid_simulator.py`)
and drop the `target` argument at each (they all live in this file).

`_normal_attack_percent`'s multiplier lookup becomes:

```python
        multiplier = 1 + _stat_bundle(ev["slug"], ev["time"])["normal_attack_damage_multiplier"]
```

(keep the surrounding comment; delete nothing else).

- [ ] **Step 4: Run the full suite — bit-identical gate**

Run: `PYTHONIOENCODING=utf-8 python3 -m pytest tests/ -q`
Expected: `659 passed`, zero failures. Any numeric divergence is a bug in this
task (most likely a stat missing from `_BUNDLE_STATS` or an epoch/version
keying mistake) — never adjust a test.

- [ ] **Step 5: Commit**

```bash
git add backend/app/raid_simulator.py
git commit -m "perf: memoize phase-2 stat bundles per (target, state epoch, registry version)"
```

---

### Task 3: Re-measure + docs

**Files:**
- Modify: `docs/roadmap.md` (top summary block), this plan file (completion notes)

- [ ] **Step 1: Run the benchmark**

Run (from the worktree root): `python3 scripts/bench_evaluate_deck.py`
Record the printed avg line verbatim. Target: ≤50 ms. If missed, additionally run a cProfile pass (`python3 -m cProfile -s cumulative scripts/bench_evaluate_deck.py -n 3`, top ~15 lines) and record where the time goes — no further optimization in this stage either way.

- [ ] **Step 2: Update the roadmap and completion notes**

`docs/roadmap.md` top test line: update the Stage 0 entry (the one recording 133.66ms) in place — replace its measured value with the new one and extend the note, e.g. `133.66ms → <새 실측값>ms (Stage 0.5 epoch memo, 2026-07-17)`, update the test count to **659 passed**, and state plainly whether the 50ms target is now met.

Append to the bottom of this plan file:

```markdown
## Completion notes

- Measured: evaluate_deck <실측값> ms/sim (Stage 0 was 133.66 ms; target <=50 ms <met|missed>), 2026-07-17.
- Suite: 659 passed.
```

- [ ] **Step 3: Commit**

```bash
git add docs/roadmap.md docs/superpowers/plans/2026-07-17-effect-registry-stage05.md
git commit -m "docs: record Stage 0.5 epoch-memo results"
```

---

## Completion notes

- Measured: evaluate_deck 125.07 ms/sim (Stage 0 was 133.66 ms; target <=50 ms missed), 2026-07-17.
- Suite: 659 passed.
- Profile (top 15 lines): `_stat_bundle` (185485 calls, 0.478 s cumulative), `_damage_instance` (83341 calls, 0.457 s), `state_epoch` (185485 calls, 0.161 s). Remaining time distributed across import, module init, and utility functions.
