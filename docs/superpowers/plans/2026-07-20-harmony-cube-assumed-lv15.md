# Harmony Cube — Assumed Resilience Lv.15 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make harmony cube effects reach the simulation for every unit by assuming everyone wears a Resilience Cube Lv.15, and stop crediting superior-code damage to units without elemental advantage.

**Architecture:** The cube stops being per-unit input and becomes a global constant derived from the committed stat table. `cube_effects` reads the cube's skill-level ladder out of `tables.json` and caches the two resulting percentages; `roster._passive_effects` applies them to every spec unconditionally. The cube input disappears from the model and the UI. Separately, `damage_formula` gates `other_elemental_bonus` on elemental advantage, which is where that stat belongs in the real game.

**Tech Stack:** Python 3 / FastAPI / pytest (backend), React 19 / TypeScript / Vite / Vitest (frontend).

## Global Constraints

- Work only in the worktree `C:\Users\fienn\Desktop\NikkeDeckBuilder\.claude\worktrees\plans-frontend3-encoding`. Do NOT `cd` to the original repository root.
- Branch: `wip/harmony-cube-lv15` (already created, already merged up to trunk `84138af`).
- Run backend tests with `python3 -m pytest` from `backend/` — plain `python` on this machine has no pytest.
- **Baseline: 1004 backend tests pass.** Any task that ends with fewer passing than it started (minus tests it deliberately deleted) is a failure.
- Never use bare `git stash` / `git stash pop` — the stash stack is shared with other worktrees.
- Cube percentages are **29.69** (reload speed) and **19.09** (superior code damage) at Lv.15, confirmed against the in-game tooltip. Never invent other values; derive them from the table.
- UI copy is **English** throughout this app (`App.tsx`: "Enter each owned Nikke's investment data from ShiftyPad."). The spec quotes the notice in Korean for readability; implement it in English to match surrounding code.
- Test output must be pristine. A test that expects a warning log must capture and assert it, not let it print.

---

### Task 1: Gate superior-code damage on elemental advantage

`damage_formula.py` adds `other_elemental_bonus` to the element bonus group regardless of whether the attacker has elemental advantage. In game, "우월 코드 공격 대미지 ▲" only applies when the attacker holds advantage. Nothing currently tests the non-advantaged case, which is why the bug survived.

**Files:**
- Modify: `backend/app/damage_formula.py:96`
- Test: `backend/tests/test_raid_simulator.py` (append)

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces: no new public names. Behaviour change only — after this task, `other_elemental_bonus` contributes 0 when `element_multiplier == 1.0`.

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/test_raid_simulator.py`. It mirrors the existing `test_boss_element_grants_advantage_bonus_to_matching_attackers` directly above it, including its helpers (`make_deck`, `make_base_stats`) and its `Effect(..., "self", None, "attacker")` convention where a rule registered on `buffer` grants a self-scoped effect whose owner is named by `source_slug`.

```python
def test_superior_code_damage_applies_only_with_elemental_advantage():
    # make_deck's attacker is Iron; Iron > Electric. other_elemental_bonus is
    # the "Superior Code Damage" stat, which joins the element bonus group:
    # it must raise damage against an Electric boss and do nothing at all
    # against a neutral Fire boss.
    def grant_superior_code(context, caster_slug, time, registry):
        registry.add(
            Effect("other_elemental_bonus", 0.5, "self", None, "attacker"),
            applied_at=time,
        )

    rules_by_slug = {
        "buffer": [SkillRule(trigger="battle_start", action=grant_superior_code)],
        "midtier": [],
        "attacker": [],
    }
    kwargs = dict(
        rules_by_slug=rules_by_slug,
        burst_damage_percents={"attacker": 500.0},
        base_stats=make_base_stats(attacker_atk=2000),
        enemy_def=0,
        gauge_charge_time=5.0,
        fight_duration=20.0,
        mode="auto",
        base_crit_rate=0.0,
    )
    neutral = simulate_raid(make_deck(), boss_element="Fire", **kwargs)
    advantaged = simulate_raid(make_deck(), boss_element="Electric", **kwargs)

    # Neutral: element bonus group is 1.0 + nothing.
    assert neutral["total_damage"] == 10000.0
    # Advantaged: 1.1 from the element multiplier plus the 0.5 bonus.
    assert round(advantaged["total_damage"], 5) == round(10000.0 * 1.6, 5)
```

- [ ] **Step 2: Run test to verify it fails**

Run from `backend/`:
```
python3 -m pytest tests/test_raid_simulator.py::test_superior_code_damage_applies_only_with_elemental_advantage -v
```
Expected: FAIL on the first assertion — `assert 15000.0 == 10000.0`. The neutral case currently receives the bonus it should not.

- [ ] **Step 3: Write the implementation**

In `backend/app/damage_formula.py`, replace line 96:

```python
    element_bonus_damage = element_multiplier + other_elemental_bonus
```

with:

```python
    # "Superior Code Damage" only applies when the attacker actually holds
    # elemental advantage; element_multiplier is already that indicator
    # (1.1 with advantage, 1.0 without - see elements.py).
    has_element_advantage = element_multiplier > 1.0
    element_bonus_damage = element_multiplier + (
        other_elemental_bonus if has_element_advantage else 0.0
    )
```

- [ ] **Step 4: Run the full suite**

Run from `backend/`:
```
python3 -m pytest -q
```
Expected: `1005 passed`. No previously-passing test may break — this was measured before planning: gating the term breaks zero existing tests.

- [ ] **Step 5: Commit**

```bash
git add backend/app/damage_formula.py backend/tests/test_raid_simulator.py
git commit -m "Apply superior code damage only with elemental advantage"
```

---

### Task 2: Derive the cube's percentages from the stat table

Read the two effect percentages out of the committed cube table instead of hardcoding them, and rename the table key from `cube_sample` to what it actually is.

The table stores, per cube level 1..15, the **skill level** each of the cube's three skill slots has reached (`level1` / `level2` / `level3`), and per slot a ladder of percentages indexed by that skill level. At cube level 15: `level1=3`, `level2=6`, `level3=0` (slot 3 never unlocks — this cube has exactly two effects).

**Files:**
- Modify: `data/nikke-stat-tables/tables.json` (rename one key)
- Modify: `backend/app/stat_assembly.py:276`, `backend/app/stat_assembly.py:472`
- Modify: `backend/app/cube_effects.py`
- Test: `backend/tests/test_cube_effects.py` (replace contents)

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces:
  - `cube_effects.CUBE_SKILL_STATS: dict[str, str]` — cube skill name → engine stat name.
  - `cube_effects.ASSUMED_CUBE_LEVEL: int` (= 15).
  - `cube_effects.cube_skill_percents(tables: dict, cube_level: int) -> dict[str, float]` — engine stat name → percent (e.g. `{"reload_speed_percent": 29.69, "other_elemental_bonus": 19.09}`).
  - `cube_effects.assumed_cube_effects(source_slug: str) -> list[Effect]` — loads and caches the table itself; Task 3 calls this.
  - `cube_to_effects` stays in place untouched for now. It is dead code the moment Task 3 rewires `roster.py`, and Task 3 deletes it. Leaving it here keeps this task's end state green.

- [ ] **Step 1: Rename the table key**

Verify there is exactly one occurrence, then rename it:

```bash
grep -c '"cube_sample"' data/nikke-stat-tables/tables.json
sed -i 's/"cube_sample"/"resilience_cube"/' data/nikke-stat-tables/tables.json
grep -c '"resilience_cube"' data/nikke-stat-tables/tables.json
```
Expected: `1`, then `1`. Use `sed -i` rather than a JSON round-trip so the rest of the file's formatting is untouched.

Then update the two readers in `backend/app/stat_assembly.py` — line 276 inside `cube_atk` and line 472 inside `cube_hp`:

```python
    return tables["resilience_cube"]["atk"][cube_level - 1]
```
```python
    return tables["resilience_cube"]["hp"][cube_level - 1]
```

- [ ] **Step 2: Run the suite to confirm the rename is complete**

Run from `backend/`:
```
python3 -m pytest -q
```
Expected: `1005 passed`. A `KeyError: 'cube_sample'` here means a reader was missed.

- [ ] **Step 3: Write the failing tests**

Create `backend/tests/test_assumed_cube.py`. Leave the existing `test_cube_effects.py` alone — Task 3 deletes it together with the function it covers.

```python
import logging

import pytest

from app.cube_effects import (
    ASSUMED_CUBE_LEVEL,
    assumed_cube_effects,
    cube_skill_percents,
)
from app.stat_assembly import load_stat_tables


@pytest.fixture(scope="module")
def tables():
    return load_stat_tables()


def test_assumed_level_matches_the_in_game_tooltip(tables):
    # Resilience Cube (렐릭 베어 큐브) Lv.15, confirmed against the in-game
    # tooltip by Fienn on 2026-07-20.
    assert cube_skill_percents(tables, ASSUMED_CUBE_LEVEL) == {
        "reload_speed_percent": 29.69,
        "other_elemental_bonus": 19.09,
    }


def test_a_mid_level_cube_reads_lower_rungs_of_each_ladder(tables):
    # At cube level 5 the slots sit at skill level 2 and 1 respectively.
    assert cube_skill_percents(tables, 5) == {
        "reload_speed_percent": 22.27,
        "other_elemental_bonus": 8.48,
    }


def test_a_slot_that_has_not_unlocked_yet_is_omitted(tables):
    # level2 is still 0 at cube level 4, so only the reload slot contributes.
    assert set(cube_skill_percents(tables, 4)) == {"reload_speed_percent"}


def test_an_unmapped_cube_skill_is_skipped_with_a_warning(tables, caplog):
    doctored = dict(tables)
    cube = dict(tables["resilience_cube"])
    groups = [dict(g) if g else g for g in cube["harmonycube_skill_group"]]
    groups[1]["name_localkey"] = "미지의 HC"
    cube["harmonycube_skill_group"] = groups
    doctored["resilience_cube"] = cube

    with caplog.at_level(logging.WARNING, logger="app.cube_effects"):
        percents = cube_skill_percents(doctored, ASSUMED_CUBE_LEVEL)

    assert set(percents) == {"reload_speed_percent"}
    assert "미지의 HC" in caplog.text


def test_assumed_cube_effects_are_permanent_self_buffs():
    effects = assumed_cube_effects("anis-star")
    by_stat = {e.stat: e for e in effects}
    assert round(by_stat["reload_speed_percent"].value, 4) == 0.2969
    assert round(by_stat["other_elemental_bonus"].value, 4) == 0.1909
    for effect in effects:
        assert effect.scope == "self"
        assert effect.duration is None
        assert effect.source_slug == "anis-star"
```

- [ ] **Step 4: Run tests to verify they fail**

Run from `backend/`:
```
python3 -m pytest tests/test_cube_effects.py -v
```
Expected: collection error — `ImportError: cannot import name 'cube_skill_percents' from 'app.cube_effects'`.

- [ ] **Step 5: Write the implementation**

Rewrite `backend/app/cube_effects.py` as below. Keep the existing `cube_to_effects` function at the bottom of the file exactly as it is — Task 3 deletes it once nothing imports it.

```python
"""The harmony cube every unit is assumed to wear, as permanent self Effects.

Cube choice is not user input. A cube type can only be worn by 12 units at
once, but decks re-equip between fights, so in solo raid all 25 units fight
with a cube on and the equip state at collection time is noise. We therefore
assume a Resilience Cube (렐릭 베어 큐브) at Lv.15 for everyone.

The percentages are derived from the committed stat table rather than
hardcoded. That table stores, per cube level, the *skill level* each of the
cube's skill slots has reached (level1/level2/level3), and per slot a ladder
of percentages indexed by that skill level. At Lv.15 the slots sit at skill
level 3 and 6, giving reload speed 29.69% and superior code damage 19.09% -
both confirmed against the in-game tooltip (Fienn, 2026-07-20).

Only stats that affect raid DPS are mapped. A cube must never contribute
atk/def/max_hp here: the flat cube stats are already handled by
stat_assembly.cube_atk / cube_hp on the sync path, so re-adding them would
double-count.
"""
import logging
from functools import lru_cache

from app.effects import Effect
from app.stat_assembly import load_stat_tables

logger = logging.getLogger(__name__)

# Cube skill name (as it appears in the table) -> the engine stat it feeds.
CUBE_SKILL_STATS = {
    "퀵 리로드 HC": "reload_speed_percent",
    "안티 코드 HC": "other_elemental_bonus",
}

ASSUMED_CUBE_LEVEL = 15


def cube_skill_percents(tables: dict, cube_level: int) -> dict[str, float]:
    """Engine stat -> percent for the assumed cube at `cube_level`."""
    cube = tables["resilience_cube"]
    percents: dict[str, float] = {}
    for slot, group in enumerate(cube["harmonycube_skill_group"], start=1):
        if group is None:
            continue
        skill_level = cube[f"level{slot}"][cube_level - 1]
        if skill_level <= 0:
            continue
        name = group["name_localkey"]
        stat = CUBE_SKILL_STATS.get(name)
        if stat is None:
            logger.warning("unknown harmony cube skill %r - skipped", name)
            continue
        ladder = group["description_value_list"][0]["description_value"]
        percents[stat] = float(ladder[skill_level - 1])
    return percents


@lru_cache(maxsize=1)
def _assumed_percents() -> tuple[tuple[str, float], ...]:
    """The assumed cube's percentages, read once. Tuple so lru_cache is safe."""
    return tuple(cube_skill_percents(load_stat_tables(), ASSUMED_CUBE_LEVEL).items())


def assumed_cube_effects(source_slug: str) -> list[Effect]:
    """The assumed cube's always-on buffs on one wearer."""
    return [
        Effect(stat, percent / 100, "self", None, source_slug)
        for stat, percent in _assumed_percents()
    ]
```

- [ ] **Step 6: Run tests to verify they pass**

Run from `backend/`:
```
python3 -m pytest tests/test_assumed_cube.py -v
```
Expected: 5 passed.

- [ ] **Step 7: Run the full suite**

Run from `backend/`:
```
python3 -m pytest -q
```
Expected: `1010 passed` (1004 baseline + 1 from Task 1 + 5 new). Nothing may break: this task only adds functions and renames a key whose two readers were both updated.

- [ ] **Step 8: Commit**

```bash
git add data/nikke-stat-tables/tables.json backend/app/stat_assembly.py backend/app/cube_effects.py backend/tests/test_assumed_cube.py
git commit -m "Derive the assumed cube's percentages from the stat table"
```

---

### Task 3: Apply the assumed cube to every spec

Cube effects have never reached the simulation: `roster._passive_effects` passed `spec.cube.get("reload_speed_percent")` and `spec.cube.get("superior_code_damage_percent")`, keys that `PveCube` (fields `name` / `level` only) never defines, so `cube_to_effects` always returned `[]`. Remove the per-unit cube entirely and apply the assumed cube to everyone.

**Files:**
- Modify: `backend/app/roster.py` (imports, `NikkeSpec.cube`, `_passive_effects`, module docstring)
- Modify: `backend/app/user_roster.py:92`
- Modify: `backend/app/models.py` (delete `PveCube`, delete `UserNikkeState.pve_cube`)
- Modify: `backend/app/cube_effects.py` (delete `cube_to_effects`, now unused)
- Delete: `backend/tests/test_cube_effects.py` (all three tests cover `cube_to_effects`)
- Test: `backend/tests/test_roster_cube_wiring.py` (create)

**Interfaces:**
- Consumes: `cube_effects.assumed_cube_effects(source_slug)` from Task 2.
- Produces: `NikkeSpec` no longer has a `cube` field; `UserNikkeState` no longer has `pve_cube`; `models.PveCube` and `cube_effects.cube_to_effects` no longer exist. Task 5 relies on `pve_cube` being ignored by the API.

- [ ] **Step 1: Write the failing test**

Create `backend/tests/test_roster_cube_wiring.py`. The second test is the one that matters: it proves the cube actually moves damage end to end, which is exactly what the old wiring failed to do while still passing its unit tests.

```python
"""The assumed harmony cube reaches every unit's simulation inputs.

Cube effects were dead for the entire roster before this: roster.py read
percent keys off a PveCube that never defined them. A unit test on the
effect builder alone would not have caught that, so the second test here
runs the simulation and checks the damage actually moves.
"""
from app.roster import NikkeSpec, assemble_simulation_inputs
from app.raid_simulator import simulate_raid


def make_spec(slug, element="Iron", atk=2000):
    return NikkeSpec(
        slug=slug,
        burst_tier=3,
        burst_cooldown=40.0,
        element=element,
        weapon="AR",
        base_stats={"atk": atk, "def": 0, "max_hp": 0},
        skill_values={},
        weapon_stats={},
    )


def test_every_spec_gets_the_cube_buffs_without_asking_for_them():
    inputs = assemble_simulation_inputs([make_spec("attacker")])
    rules = inputs["rules_by_slug"]["attacker"]

    granted = []

    class _Registry:
        def add(self, effect, applied_at=None):
            granted.append(effect)

    for rule in rules:
        if rule.trigger == "battle_start":
            rule.action(None, "attacker", 0.0, _Registry())

    by_stat = {e.stat: e for e in granted}
    assert round(by_stat["reload_speed_percent"].value, 4) == 0.2969
    assert round(by_stat["other_elemental_bonus"].value, 4) == 0.1909
    assert by_stat["reload_speed_percent"].source_slug == "attacker"


def test_the_cube_superior_code_bonus_moves_damage_against_a_weak_boss():
    # Iron > Electric, so the cube's 19.09% superior code damage applies and
    # nothing else in this deck does. Compare against the same fight with the
    # element bonus group left bare.
    spec = make_spec("attacker")
    inputs = assemble_simulation_inputs([spec])
    kwargs = dict(
        burst_damage_percents={"attacker": 500.0},
        base_stats=inputs["base_stats"],
        enemy_def=0,
        gauge_charge_time=5.0,
        fight_duration=20.0,
        mode="auto",
        base_crit_rate=0.0,
    )
    with_cube = simulate_raid(
        inputs["deck"], inputs["rules_by_slug"], boss_element="Electric", **kwargs
    )
    bare = simulate_raid(
        inputs["deck"], {"attacker": []}, boss_element="Electric", **kwargs
    )

    assert with_cube["total_damage"] > bare["total_damage"]
    # 1.1 element multiplier + 0.1909 cube bonus, vs 1.1 alone.
    assert round(with_cube["total_damage"] / bare["total_damage"], 4) == round(
        1.2909 / 1.1, 4
    )
```

`assemble_simulation_inputs` returns a dict keyed `"deck"`, `"rules_by_slug"`, `"burst_damage_percents"`, `"base_stats"`, `"weapon_stats"` and a dozen more (see the return statement at the end of `backend/app/roster.py`), so the dict access above is correct as written.

- [ ] **Step 2: Run tests to verify they fail**

Run from `backend/`:
```
python3 -m pytest tests/test_roster_cube_wiring.py -v
```
Expected: FAIL — no cube effects are granted, so `by_stat["reload_speed_percent"]` raises `KeyError`.

- [ ] **Step 3: Remove the dead per-unit cube from roster.py**

In `backend/app/roster.py`:

Change the import on line 17:
```python
from app.cube_effects import assumed_cube_effects
```

Delete the `cube: dict | None = None` field from `NikkeSpec`.

Replace `_passive_effects` entirely:
```python
def _passive_effects(spec: NikkeSpec):
    """Overload plus the harmony cube every unit is assumed to wear."""
    return overload_options_to_effects(spec.overload_options, spec.slug) + (
        assumed_cube_effects(spec.slug)
    )
```

Update the module docstring's first paragraph, which still describes the cube as per-unit investment. Replace "the user's investment (skill values, overload options, cube)" with "the user's investment (skill values, overload options)" and leave the rest intact.

- [ ] **Step 4: Remove the cube from the request model**

In `backend/app/user_roster.py`, delete line 92 entirely:
```python
        cube=state.pve_cube.model_dump() if state.pve_cube else None,
```

In `backend/app/models.py`, delete the whole `PveCube` class, delete the `pve_cube: PveCube | None = None` field from `UserNikkeState`, and delete the now-false comment block above `overload_options` that begins "hp/atk/def above ALREADY include the equipped cube's contribution" — replace it with:
```python
    # hp/atk/def above are the user's displayed stats. The harmony cube is NOT
    # re-added on top of them here; cube_effects supplies its two damage stats
    # and stat_assembly.cube_atk / cube_hp handle the flat stats on the sync
    # path. overload_options ARE additive (see overload_effects).
```

- [ ] **Step 5: Delete the now-unused old path**

Delete the `cube_to_effects` function from `backend/app/cube_effects.py` — nothing imports it any more. Then:

```bash
git rm backend/tests/test_cube_effects.py
```

- [ ] **Step 6: Run the new tests, then the full suite**

Run from `backend/`:
```
python3 -m pytest tests/test_roster_cube_wiring.py -v
python3 -m pytest -q
```
Expected: the new tests pass. The full suite will report failures in any test that constructs `UserNikkeState(... pve_cube=...)` or `NikkeSpec(... cube=...)`. Fix each by deleting the argument — do not re-add the field. Final count: 1010 from Task 2, plus 2 new, minus the 3 deleted = **1009 passed**.

- [ ] **Step 7: Commit**

```bash
git add backend/app/roster.py backend/app/user_roster.py backend/app/models.py backend/app/cube_effects.py backend/tests/test_roster_cube_wiring.py backend/tests/test_cube_effects.py
git commit -m "Give every unit the assumed cube instead of dead per-unit input"
```

---

### Task 4: Assume Lv.15 for the cube's flat stats on the sync path

`roster_assembly` feeds the collected `harmony_cube_lv` into `cube_atk` / `cube_hp`, so a unit that had no cube equipped at collection time gets no flat cube stats. Since we now assume everyone wears Lv.15, the flat stats must follow. This is safe from double-counting because the sync path computes ATK from itemised terms (`assemble_atk(base + grade/core + extra_flat)`) rather than reading a displayed total.

**The assumption must be a parameter, not a hardcode.** `backend/tests/test_roster_assembly.py::test_assemble_roster_matches_the_collector_scrape` compares assembled ATK/HP against the collector's scraped `roster.json`, which reflects each unit's **real** cube. That test is what validates our stat formula against ground truth. Baking Lv.15 into `extract_inputs` would break it for the 128 units collected with no cube (by 2,780 ATK / 83,400 HP each) and, worse, would destroy its ability to catch formula bugs at all. So `assemble_roster` takes the assumed level as a defaulted parameter, and the parity test opts out of the assumption.

**Files:**
- Modify: `backend/app/roster_assembly.py` (`extract_inputs`, `assemble_unit`, `assemble_roster`)
- Test: `backend/tests/test_roster_assembly.py` (append one test; modify the parity test's call)

**Interfaces:**
- Consumes: `cube_effects.ASSUMED_CUBE_LEVEL` from Task 2.
- Produces:
  - `extract_inputs(entry, owned, detail, assume_cube_level=None)` — when `assume_cube_level` is an int it replaces the collected `harmony_cube_lv`; when `None` the collected value is used.
  - `assemble_unit(tables, entry, owned, detail, research, assume_cube_level=None)` — passes the parameter through.
  - `assemble_roster(tables, directory, raw, assume_cube_level=ASSUMED_CUBE_LEVEL)` — **defaults to the assumption**, so `api.py` needs no change.

- [ ] **Step 1: Write the failing test**

Append to `backend/tests/test_roster_assembly.py`. It reuses the file's existing `tables` fixture and the `DIRECTORY` constant already defined at the top.

```python
def test_the_assumed_cube_level_overrides_what_was_collected(tables):
    # Collection-time equip state is noise: decks re-equip between fights, so
    # every unit fights with a Lv.15 cube on. Assembling the same uncubed unit
    # with and without the assumption must differ by exactly the Lv.15 rung of
    # the cube's flat stat tables.
    from app.cube_effects import ASSUMED_CUBE_LEVEL
    from app.roster_assembly import assemble_roster

    directory = json.loads(DIRECTORY.read_text(encoding="utf-8"))
    raw = {
        "owned": [{"name_code": 5129, "lv": 400, "core": 6, "grade": 3}],
        "character_details": [{"name_code": 5129, "grade": 3, "core": 6,
                               "attractive_lv": 40, "harmony_cube_lv": 0,
                               "favorite_item_tid": 0, "favorite_item_lv": 0,
                               "skill1_lv": 10, "skill2_lv": 10, "ulti_skill_lv": 10}],
        "recycle_room_researches": [
            {"tid": 1001, "lv": 170}, {"tid": 1101, "lv": 190}, {"tid": 1201, "lv": 150},
        ],
    }
    as_collected = assemble_roster(tables, directory, raw, assume_cube_level=None)[0]
    assumed = assemble_roster(tables, directory, raw)[0]

    cube = tables["resilience_cube"]
    assert assumed["raid400"]["atk"] - as_collected["raid400"]["atk"] == (
        cube["atk"][ASSUMED_CUBE_LEVEL - 1]
    )
    assert assumed["raid400"]["hp"] - as_collected["raid400"]["hp"] == (
        cube["hp"][ASSUMED_CUBE_LEVEL - 1]
    )
```

- [ ] **Step 2: Run test to verify it fails**

Run from `backend/`:
```
python3 -m pytest tests/test_roster_assembly.py -k assumed_cube -v
```
Expected: FAIL — `TypeError: assemble_roster() got an unexpected keyword argument 'assume_cube_level'`.

- [ ] **Step 3: Write the implementation**

In `backend/app/roster_assembly.py`, add to the imports:
```python
from app.cube_effects import ASSUMED_CUBE_LEVEL
```

Give `extract_inputs` the parameter and use it. Change its signature and the `harmony_cube_lv` entry:
```python
def extract_inputs(entry: dict, owned: dict, detail: dict,
                   assume_cube_level: int | None = None) -> dict:
```
```python
        # Equip state at collection time is noise - a cube type is limited to
        # 12 wearers, but decks re-equip between fights, so every unit fights
        # with a cube on. assume_cube_level=None keeps the collected value,
        # which is what the collector-parity test needs to stay a real check
        # on the stat formula.
        "harmony_cube_lv": (
            detail.get("harmony_cube_lv", 0)
            if assume_cube_level is None
            else assume_cube_level
        ),
```

Thread it through `assemble_unit`:
```python
def assemble_unit(tables, entry: dict, owned: dict, detail: dict, research: dict,
                  assume_cube_level: int | None = None) -> dict:
    inp = extract_inputs(entry, owned, detail, assume_cube_level)
```

And through `assemble_roster`, defaulting to the assumption:
```python
def assemble_roster(tables, directory: list, raw: dict,
                    assume_cube_level: int | None = ASSUMED_CUBE_LEVEL) -> list[dict]:
```
with its one call site inside the loop becoming:
```python
        units.append(assemble_unit(tables, entry, o, d, research, assume_cube_level))
```

- [ ] **Step 4: Keep the parity test honest**

In `backend/tests/test_roster_assembly.py::test_assemble_roster_matches_the_collector_scrape`, change the assembly call to opt out of the assumption, since it compares against a scrape that reflects real cubes:

```python
    out = {u["resource_id"]: u
           for u in assemble_roster(tables, directory, raw, assume_cube_level=None)}
```

Add a comment above it:
```python
    # Compare against what was really equipped: this test validates the stat
    # formula, not the product's Lv.15 assumption.
```

- [ ] **Step 5: Run the full suite**

Run from `backend/`:
```
python3 -m pytest -q
```
Expected: all pass, including the parity test. If parity now fails, the opt-out in Step 4 was not applied — do not widen the test's tolerance to make it pass.

- [ ] **Step 5: Commit**

```bash
git add backend/app/roster_assembly.py backend/tests/test_roster_assembly.py
git commit -m "Assume a Lv.15 cube for the sync path's flat stats too"
```

---

### Task 5: Drop the cube input from the UI and state the assumption

With the cube fixed globally, the PVE cube input does nothing. Leaving a live field that is silently ignored misleads the user, so remove it and say what is assumed instead. The `cubeKnown` merge machinery added to preserve cube data across syncs goes with it — there is no longer any cube state to preserve.

**Files:**
- Delete: `frontend/src/components/PveCubeField.tsx`
- Modify: `frontend/src/components/NikkeCard.tsx` (remove import + the `<PveCubeField>` block at lines 134-140)
- Modify: `frontend/src/types/nikkeDraft.ts` (remove `hasCube` / `pve_cube` / `cubeKnown` from the draft type, the empty draft, the validation block, the payload build, and the merge special-case)
- Modify: `frontend/src/types/userNikkeState.ts` (remove `pve_cube` from the payload type and `cubeLevel` from `CONSTRAINTS`)
- Modify: `frontend/src/lib/rosterImport.ts` (remove the `pve_cube` input field and the three draft fields it sets)
- Modify: `frontend/src/lib/exiaImport.ts` (remove the three draft fields)
- Modify: `frontend/src/App.tsx` (add the assumption notice)
- Modify tests: `frontend/src/lib/rosterImport.test.ts`, `frontend/src/lib/exiaImport.test.ts`, `frontend/src/components/NikkeCard.test.tsx`, `frontend/src/components/ImportRosterButton.test.tsx`, `frontend/src/components/RecommendPanel.test.tsx`, `frontend/src/api/recommendClient.mock.test.ts`, `frontend/src/api/recommendRaidClient.mock.test.ts`

**Interfaces:**
- Consumes: Task 3's removal of `pve_cube` from the API request model.
- Produces: `NikkeDraft` without `hasCube` / `pve_cube` / `cubeKnown`.

- [ ] **Step 1: Write the failing tests**

Add to `frontend/src/lib/rosterImport.test.ts` (replacing the three existing cube assertions, which test behaviour this task deletes):

`parseRosterJson(raw: unknown)` takes an **already-parsed object** (not a JSON string) and returns `{ drafts: NikkeDraft[]; warnings: string[] }`.

```ts
it('ignores a pve_cube field in the imported roster', () => {
  const { drafts } = parseRosterJson({
    units: [
      {
        name_en: 'Rapi',
        resource_id: 16,
        raid400: { hp: 1, atk: 2, def: 0 },
        skill_levels: { skill1: 1, skill2: 1, burst: 1 },
        overload: [],
        pve_cube: { name: 'Resilience Cube', level: 15 },
      },
    ],
  })
  expect(drafts).toHaveLength(1)
  expect(drafts[0]).not.toHaveProperty('pve_cube')
  expect(drafts[0]).not.toHaveProperty('hasCube')
  expect(drafts[0]).not.toHaveProperty('cubeKnown')
})
```

Create `frontend/src/App.test.tsx` — it does not exist yet. Follow the import style of `frontend/src/components/RecommendPanel.test.tsx` (named imports from `vitest`, `render`/`screen` from `@testing-library/react`):

```tsx
import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import App from './App'

describe('App', () => {
  it('states the harmony cube assumption', () => {
    render(<App />)
    expect(screen.getByText(/Resilience Cube Lv\.15/i)).toBeInTheDocument()
  })
})
```

(`App.tsx` ends with `export default App`, so the default import above is correct.)

- [ ] **Step 2: Run tests to verify they fail**

Run from `frontend/`:
```
npx vitest run src/lib/rosterImport.test.ts src/App.test.tsx
```
Expected: FAIL — the draft still carries `hasCube`, and no element matches the notice text.

- [ ] **Step 3: Delete the field component and its wiring**

```bash
git rm frontend/src/components/PveCubeField.tsx
```

In `frontend/src/components/NikkeCard.tsx`, delete the `PveCubeField` import and the whole `<PveCubeField ... />` element (lines 134-140).

- [ ] **Step 4: Strip the cube out of the draft model**

In `frontend/src/types/nikkeDraft.ts`:
- Delete `hasCube: boolean`, `pve_cube: { name: string; level: string }` and the `cubeKnown: boolean` field together with its explanatory comment (lines 32-39).
- Delete `pve_cube?: { name?: string; level?: string }` from the errors type (line 51).
- Delete `hasCube: false`, `pve_cube: { name: '', level: '' }`, `cubeKnown: true` from the empty draft (lines 75-77).
- Delete the whole `let pveCube ... }` validation block (lines 167-178) and the `pve_cube: pveCube,` line from the built payload (line 196).
- Delete the `...(inc.cubeKnown ? { hasCube: inc.hasCube, pve_cube: inc.pve_cube } : {})` spread in `mergeCollectorDrafts` (lines 302-303) and the paragraph of its doc comment describing the cube exception (lines 269-274). Also drop the words "stats/cube" and ", cube," from the surrounding comment so it no longer claims to carry cube data.
- Remove the now-unused `type PveCube` import (line 9).

In `frontend/src/types/userNikkeState.ts`, delete the `pve_cube` field from the payload type and `cubeLevel: { min: 1, max: 15 },` from `CONSTRAINTS`.

In `frontend/src/lib/rosterImport.ts`, delete `pve_cube?: ...` from the input type (line 21) and the `hasCube` / `pve_cube` / `cubeKnown` fields it sets (lines 66-73).

In `frontend/src/lib/exiaImport.ts`, delete the three fields (lines 157-159) and drop "and cube" from the file's header comment on line 2.

- [ ] **Step 5: Add the notice**

In `frontend/src/App.tsx`, add a line under the existing subtitle inside `<header className="app__header">`:

```tsx
        <p className="app__subtitle">
          Enter each owned Nikke&rsquo;s investment data from ShiftyPad.
        </p>
        <p className="app__note">
          All Nikkes are simulated wearing a Resilience Cube Lv.15.
        </p>
```

Add a matching `.app__note` rule to `frontend/src/App.css`, following the existing `.app__subtitle` rule's style (read it and match its colour/size conventions rather than inventing new ones).

- [ ] **Step 6: Fix the remaining tests**

Delete `pve_cube: null` from the fixture objects in `recommendClient.mock.test.ts`, `recommendRaidClient.mock.test.ts`, `ImportRosterButton.test.tsx` (two places) and `RecommendPanel.test.tsx`. Delete the two `hasCube` / `pve_cube` assertions in `exiaImport.test.ts` (lines 165-166) and any cube assertions left in `NikkeCard.test.tsx`.

- [ ] **Step 7: Run the frontend checks**

Run from `frontend/`:
```
npx vitest run
npx tsc --noEmit
npm run lint
```
Expected: all pass. `tsc` is the real guard here — it will name every remaining reference to a deleted field.

- [ ] **Step 8: Run the backend suite once more**

Run from `backend/`:
```
python3 -m pytest -q
```
Expected: all pass. This catches any contract drift between the frontend payload and the API model.

- [ ] **Step 9: Commit**

Review what you are about to stage first — this task touches a dozen files and `git add -A` would sweep in anything unrelated:

```bash
git status
git add frontend/src
git commit -m "Remove the cube input and state the Lv.15 assumption in the UI"
```

---

## Documentation (after Task 5)

- [ ] Update `docs/engine-gaps.md`: gap #12 is resolved. Replace its body with a one-line resolved note pointing at this plan and the spec, matching how the other resolved gaps in that file are written.
- [ ] Add a `docs/decisions.md` entry: cube modelled as a global Resilience Lv.15 assumption rather than per-unit input or an engine-chosen optimum; why (free re-equip makes collection-time state noise; per-unit selection deferred); consequence (manual-entry ATK path stays inconsistent by ~2.7%, recorded in the spec).
- [ ] Add a `docs/insights.md` entry: the cube table's `level1`/`level2`/`level3` arrays are cube-level → skill-level ladders, not stats — the discontinuity in a slot's percentage list is unreachable tail beyond that slot's skill cap.
- [ ] Update `docs/roadmap.md`'s To-Do to reflect that the cube follow-up is done.
- [ ] Commit the docs.
