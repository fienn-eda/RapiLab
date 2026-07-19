# Roster Sync — Fetch + Assemble Slice Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A backend that turns `(intl_open_id, nikke_area_id)` + an injected blablalink session into the collector `roster.json` shape the frontend `parseRosterJson` already consumes — with level-400 HP/ATK and overload computed, verified by parity against the collector's own scrape.

**Architecture:** Two pure layers plus a formula extension. `blablalink_api.py` fetches (session injected, mockable). `roster_assembly.py` joins the fetched dicts with committed reference tables and computes each unit's stats + overload, reusing `stat_assembly.py` (ATK, already 159/159) and a new `overload_decode.py`. HP is added to `stat_assembly.py` by fitting against measured HP already in `roster.json`; DEF is 0 (the simulator never reads it). The output matches the `RosterUnit` contract so the existing frontend import path is reused unchanged.

**Tech Stack:** Python 3 (backend, pytest), the committed `data/nikke-stat-tables/tables.json` snapshot, the committed `tools/collect-blablalink/nikke-directory.json`. No new dependencies.

## Global Constraints

- **Run Python as** `/c/Users/Fienn/anaconda3/python` (the repo's `python` is a Store stub; `python3` too). Pytest: `/c/Users/Fienn/anaconda3/python -m pytest`.
- **Gitignored local data is required for the parity/fit tests** — `tools/collect-blablalink/{roster.json,details.json}` and `data/nikke-stat-tables/tables.json`. In a fresh worktree run `/c/Users/Fienn/anaconda3/python scripts/sync_worktree_data.py` FIRST; `data/` and the collector dumps do not come with a worktree.
- **Tolerance is 0.** Integer game stats: a fitted model must reproduce measurements exactly, not approximately. Near-miss = model still wrong (the lesson that produced the ATK fit).
- **Never invent constants.** HP coefficients and the overload value table are DERIVED by the fit scripts in this plan against local data, then pasted. Do not guess them.
- **Match surrounding style** in `stat_assembly.py` (measured-not-assumed comments, domain naming).
- Backend suite must stay green: `/c/Users/Fienn/anaconda3/python -m pytest` from `backend/` (was 792 passing).

---

## File Structure

- Create `backend/app/overload_decode.py` — option_id → (type, level), value lookup, per-type consolidation, type→name.
- Create `backend/app/blablalink_api.py` — `SessionCaller` protocol + `fetch_roster`.
- Create `backend/app/roster_assembly.py` — join fetched dicts + tables → per-unit stats/overload; `to_roster_json`.
- Modify `backend/app/stat_assembly.py` — add `base_hp`, HP breakthrough/flat constants, `assemble_hp`.
- Modify `data/nikke-stat-tables/tables.json` — add `overload` value table (derived). HP curves already present under `classes[c]["hp"]`.
- Modify `scripts/build_stat_ground_truth.py` — add measured HP to the fixture and reuse the consolidated field-extraction.
- Modify `backend/tests/fixtures/stat_ground_truth.json` — regenerated to carry measured HP.
- Create tests: `backend/tests/test_overload_decode.py`, `backend/tests/test_roster_assembly.py`, `backend/tests/test_blablalink_api.py`; extend `backend/tests/test_stat_assembly.py` with HP.

---

## Task 1: Overload option_id decode

**Files:**
- Create: `backend/app/overload_decode.py`
- Test: `backend/tests/test_overload_decode.py`

**Interfaces:**
- Produces: `decode_option(option_id: int) -> tuple[int, int] | None` returning `(effect_type, level)` or `None` for an empty slot (id 0) or a non-`700xxxx` id.

- [ ] **Step 1: Write the failing test**

```python
# backend/tests/test_overload_decode.py
from app.overload_decode import decode_option


def test_decode_option_splits_type_and_level():
    # 700 TT LL: measured on ShiftyPad gear (probe 2026-07-19).
    assert decode_option(7000811) == (8, 11)   # type 8, level 11
    assert decode_option(7001002) == (10, 2)   # type 10, level 2
    assert decode_option(7000905) == (9, 5)


def test_decode_option_empty_slot_is_none():
    assert decode_option(0) is None


def test_decode_option_rejects_a_non_overload_id():
    # Anything not 700-prefixed and 7 digits is not an overload option.
    assert decode_option(3111001) is None   # an equip tid
    assert decode_option(123) is None
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd backend && /c/Users/Fienn/anaconda3/python -m pytest tests/test_overload_decode.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.overload_decode'`

- [ ] **Step 3: Write minimal implementation**

```python
# backend/app/overload_decode.py
"""Decode ShiftyPad overload options.

Each equipped gear slot carries up to three overload options as
`{slot}_equip_option{1,2,3}_id` in GetUserCharacterDetails. The id encodes the
effect and its roll: 700 + TT (effect type, 2 digits) + LL (level 1..15, 2
digits) - e.g. 7000811 is effect type 8 at level 11. Confirmed by pairing the
raw ids against ShiftyPad's parsed overload lines across 77 of Fienn's units
(2026-07-19). Value and effect name are resolved in later helpers.
"""


def decode_option(option_id: int) -> tuple[int, int] | None:
    """`(effect_type, level)` for one overload option, or None for an empty slot."""
    s = str(option_id)
    if len(s) != 7 or not s.startswith("700"):
        return None
    return int(s[3:5]), int(s[5:7])
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd backend && /c/Users/Fienn/anaconda3/python -m pytest tests/test_overload_decode.py -q`
Expected: PASS (3 passed)

- [ ] **Step 5: Commit**

```bash
git add backend/app/overload_decode.py backend/tests/test_overload_decode.py
git commit -m "feat: decode overload option_id into (effect type, level)"
```

---

## Task 2: HP model — measured HP in the fixture, then fit

**Files:**
- Modify: `scripts/build_stat_ground_truth.py` (add measured HP to each unit)
- Modify: `backend/tests/fixtures/stat_ground_truth.json` (regenerated)
- Modify: `backend/app/stat_assembly.py` (add `base_hp`, HP flat constants, `assemble_hp`)
- Modify: `backend/tests/test_stat_assembly.py` (HP parity, mirroring the ATK tests)

**Interfaces:**
- Consumes: `load_stat_tables`, `breakthrough_multiplier`, `core_flat_atk` (existing).
- Produces: `base_hp(tables, character_class, level) -> int`; `assemble_hp(tables, *, character_class, level, grade, core, corporation=None, corporation_sub_type=None, resource_id=None, extra_flat_hp=0.0) -> float`.

- [ ] **Step 1: Add measured HP + HP equipment stat to the fixture builder**

In `scripts/build_stat_ground_truth.py`, change the `"measured"` line to also carry HP, and add each equip piece's HP stat is NOT needed here (equipment HP comes from the tables at assemble time). Only measured HP is added:

```python
                "measured": {
                    "raid400_atk": u["raid400"]["atk"],
                    "actual_atk": u["actual"]["atk"],
                    "raid400_hp": u["raid400"]["hp"],
                    "actual_hp": u["actual"]["hp"],
                },
```

- [ ] **Step 2: Regenerate the fixture and eyeball it**

Run:
```bash
/c/Users/Fienn/anaconda3/python scripts/sync_worktree_data.py    # ensure roster/details present
/c/Users/Fienn/anaconda3/python scripts/build_stat_ground_truth.py
/c/Users/Fienn/anaconda3/python -c "import json;u=json.load(open('backend/tests/fixtures/stat_ground_truth.json',encoding='utf-8'))['units'][0];print(u['name_en'],u['measured'])"
```
Expected: prints a unit whose `measured` now has `raid400_hp`/`actual_hp` keys.

- [ ] **Step 3: Write the failing HP parity test**

Add to `backend/tests/test_stat_assembly.py`:

```python
def test_base_hp_reads_the_class_curve(tables):
    # HP curves are class-uniform too (Quency.hp == Rapi.hp), same as ATK.
    assert base_hp(tables, "Attacker", 1) == 13500
    assert base_hp(tables, "Supporter", 1) == 15000
    assert base_hp(tables, "Defender", 1) == 16500


def test_full_hp_model_reproduces_the_whole_roster(
    tables, ground_truth, ground_truth_ranks, identity
):
    """Level-400 HP for every collected unit, exactly (mirrors the ATK parity)."""
    exact, off = 0, []
    for u in ground_truth:
        flat = (
            affinity_hp(tables, u["class"], u["attractive_lv"])
            + corporation_hp(tables, u["corporation"], ground_truth_ranks)
            + sum(
                equipment_hp(
                    tables, x["tid"], x["lv"],
                    equip_corporation_type=x["corporation_type"],
                    unit_corporation=u["corporation"],
                )
                for x in u["equip"]
            )
            + cube_hp(tables, u["harmony_cube_lv"])
            + collectible_hp(tables, u["favorite_item_tid"], u["favorite_item_lv"])
        )
        predicted = assemble_hp(
            tables, character_class=u["class"], level=400,
            grade=u["grade"], core=u["core"], corporation=u["corporation"],
            **identity[u["name_en"]], extra_flat_hp=flat,
        )
        delta = u["measured"]["raid400_hp"] - predicted
        exact += abs(delta) < 1.0
        if abs(delta) >= 1.0:
            off.append((u["name_en"], round(delta, 1)))
    assert off == [], off
    assert exact == 159, f"only {exact}/159 exact"
```

Also add the imports at the top of the test: `base_hp, assemble_hp, affinity_hp, corporation_hp, equipment_hp, cube_hp, collectible_hp`.

- [ ] **Step 4: Run it to confirm it fails**

Run: `cd backend && /c/Users/Fienn/anaconda3/python -m pytest tests/test_stat_assembly.py -q`
Expected: FAIL — `ImportError` for the HP helpers.

- [ ] **Step 5: Derive the HP model with a fit script**

Write `/c/Users/fienn/.claude/jobs/<tmp>/fit_hp.py` (a scratch script, not committed) modeled exactly on the ATK derivation: `hp = base_hp[class][400] * breakthrough_multiplier(grade, core) + core*CORE_FLAT_HP + grade*grade_hp + extra_flat_hp`, solving per-unit residuals `delta/core` for the per-core HP flat and grouping by the SAME tiers ATK used (class / PILGRIM / OVERSPEC / by-resource-id). Reuse `data/blablalink-cdn` HP columns for affinity/equipment/cube/collectible HP (the same tables that hold ATK also hold HP under the parallel `*_hp`/HP-stat entries). Run it until every one of the 159 units solves to delta 0, watching the HP rounding rule (half-up vs the observed 24590.5→24590). **Record the derived constants and rounding rule; do not invent them.**

Run: `/c/Users/Fienn/anaconda3/python /c/Users/fienn/.claude/jobs/<tmp>/fit_hp.py`
Expected: prints per-tier CORE_FLAT_HP values with worst |delta| < 1, and the equipment/affinity/cube/collectible HP lookups that close all 159.

- [ ] **Step 6: Encode the derived HP model in `stat_assembly.py`**

Add, using the constants the fit produced (shape shown; fill the derived numbers):

```python
# HP base curve, class-uniform like ATK (verified: two Attackers' hp arrays are
# byte-identical). Level 1..1200 under classes[c]["hp"].
def base_hp(tables, character_class: str, level: int) -> int:
    curve = tables["classes"][character_class]["hp"]
    if not 1 <= level <= len(curve):
        raise ValueError(f"level {level} outside the table's 1..{len(curve)}")
    return curve[level - 1]

# Per-core / per-grade flat HP, DERIVED against measured raid400_hp (fit_hp.py),
# same tier structure as ATK. FILL from the fit output.
CORE_FLAT_HP = {"Attacker": ..., "Supporter": ..., "Defender": ...}
# ... plus PILGRIM/OVERSPEC/by-resource-id rows IF the fit shows HP tiers too;
# if the fit shows HP has no such tiers, use the class dict alone and say so.

def core_flat_hp(character_class, *, corporation=None, corporation_sub_type=None, resource_id=None) -> float:
    # Mirror core_flat_atk's resolution order IF and only if the fit shows HP
    # tiers; otherwise return CORE_FLAT_HP[character_class]. Match what the data says.
    ...

def assemble_hp(tables, *, character_class, level, grade, core,
                corporation=None, corporation_sub_type=None, resource_id=None,
                extra_flat_hp: float = 0.0) -> float:
    enhance = tables["classes"][character_class]["stat_enhance"]
    scaled = base_hp(tables, character_class, level) * breakthrough_multiplier(grade, core)
    flat = grade * enhance["grade_hp"]
    if core:
        flat += core * core_flat_hp(character_class, corporation=corporation,
                                    corporation_sub_type=corporation_sub_type, resource_id=resource_id)
    return scaled + flat + extra_flat_hp
```

Add the HP versions of the flat helpers — `affinity_hp`, `corporation_hp`, `equipment_hp`, `cube_hp`, `collectible_hp` — each a copy of its ATK sibling reading the HP column/stat instead of ATK (the fit script in Step 5 establishes exactly which column). Keep the ATK functions untouched.

- [ ] **Step 7: Run the HP parity test until 159/159**

Run: `cd backend && /c/Users/Fienn/anaconda3/python -m pytest tests/test_stat_assembly.py -q`
Expected: PASS — including `test_full_hp_model_reproduces_the_whole_roster` at 159/159.

- [ ] **Step 8: Commit**

```bash
git add backend/app/stat_assembly.py backend/tests/test_stat_assembly.py \
        scripts/build_stat_ground_truth.py backend/tests/fixtures/stat_ground_truth.json
git commit -m "feat: level-400 HP, fitted to measured HP at 159/159 (DEF stays 0, unused)"
```

---

## Task 3: Overload value table + consolidation

**Files:**
- Modify: `backend/app/overload_decode.py` (add value lookup + `assemble_overload` + type→name)
- Modify: `data/nikke-stat-tables/tables.json` (add derived `overload` table)
- Test: `backend/tests/test_overload_decode.py`

**Interfaces:**
- Consumes: `decode_option` (Task 1).
- Produces: `assemble_overload(tables, detail: dict) -> list[dict]` returning ShiftyPad-style consolidated lines `[{"name": str, "value": float}, ...]`, one per visible effect type, values summed across the four gear slots. Effect types that fold into base stats (6, 13) are excluded from the returned lines.

- [ ] **Step 1: Derive the value table and type→name map from the Rosetta**

Write a scratch script `/c/Users/fienn/.claude/jobs/<tmp>/fit_overload.py`: for every unit in `tools/collect-blablalink/roster.json` with an `overload` array, decode its `{slot}_equip_option{1,2,3}_id` from `details.json` (join by directory `name_code`↔`resource_id`), group `(type→[levels])`, and pair against the parsed `overload` lines. From single-slot/single-level occurrences, read off `value(type, level)`; verify by summing multi-slot cases against the scraped consolidated value. Emit: (a) `overload.values[type][level]`, (b) `overload.type_name[type]` (Korean), (c) which types are base-stat-folded (expected 6, 13). Run until every one of the 77 overloaded units reproduces its scraped lines exactly.

Run: `/c/Users/Fienn/anaconda3/python /c/Users/fienn/.claude/jobs/<tmp>/fit_overload.py`
Expected: prints the value table + name map + the folded-type set, with 77/77 units matching.

- [ ] **Step 2: Write the failing tests**

```python
# add to backend/tests/test_overload_decode.py
import json
from pathlib import Path
import pytest
from app.overload_decode import assemble_overload
from app.stat_assembly import load_stat_tables

ROSTER = Path(__file__).resolve().parents[2] / "tools" / "collect-blablalink" / "roster.json"
DETAILS = Path(__file__).resolve().parents[2] / "tools" / "collect-blablalink" / "details.json"
DIRECTORY = Path(__file__).resolve().parents[2] / "tools" / "collect-blablalink" / "nikke-directory.json"


@pytest.fixture(scope="module")
def tables():
    return load_stat_tables()


def test_assemble_overload_reproduces_every_scraped_unit(tables):
    """The decoded+valued overload must equal ShiftyPad's parsed lines for all 77."""
    if not (ROSTER.exists() and DETAILS.exists()):
        pytest.skip("local collector dumps not synced")
    directory = {e["name_code"]: e for e in json.loads(DIRECTORY.read_text(encoding="utf-8"))}
    by_rid = {e["resource_id"]: e for e in directory.values()}
    raw = json.loads(DETAILS.read_text(encoding="utf-8"))
    details = {d["name_code"]: d for d in raw["character_details"]}
    off = []
    checked = 0
    for u in json.loads(ROSTER.read_text(encoding="utf-8"))["units"]:
        scraped = u.get("overload") or []
        if not scraped:
            continue
        entry = by_rid.get(u["resource_id"])
        d = details.get(entry["name_code"]) if entry else None
        if not d:
            continue
        checked += 1
        got = {o["name"]: round(o["value"], 2) for o in assemble_overload(tables, d)}
        want = {o["name"]: round(o["value"], 2) for o in scraped}
        if got != want:
            off.append((u["name_en"], got, want))
    assert checked >= 70
    assert off == [], off[:5]
```

- [ ] **Step 3: Run to confirm it fails**

Run: `cd backend && /c/Users/Fienn/anaconda3/python -m pytest tests/test_overload_decode.py -q`
Expected: FAIL — `ImportError: cannot import name 'assemble_overload'`.

- [ ] **Step 4: Add the `overload` table to the snapshot**

Paste the derived table from Step 1 into `data/nikke-stat-tables/tables.json` under a new top-level `"overload"` key: `{"values": {"5": {"1": ..., "15": ...}, ...}, "type_name": {"5": "우월코드 대미지 증가", ...}, "base_stat_folded": [6, 13]}`. Values and names are the fit output — do not invent.

- [ ] **Step 5: Implement value lookup + consolidation**

```python
# append to backend/app/overload_decode.py
import collections

_SLOTS = ("head", "torso", "arm", "leg")


def overload_value(tables, effect_type: int, level: int) -> float:
    return tables["overload"]["values"][str(effect_type)][str(level)]


def assemble_overload(tables, detail: dict) -> list[dict]:
    """ShiftyPad-style consolidated overload lines for one unit's four gear slots.

    Options of the same effect type sum across slots into one line (this is how
    ShiftyPad displays them). Types that fold into the base stat panel rather
    than the Equipment Effects list are dropped from the returned lines.
    """
    folded = set(tables["overload"]["base_stat_folded"])
    names = tables["overload"]["type_name"]
    totals: dict[int, float] = collections.defaultdict(float)
    for slot in _SLOTS:
        for n in (1, 2, 3):
            dec = decode_option(detail.get(f"{slot}_equip_option{n}_id", 0))
            if dec is None:
                continue
            etype, level = dec
            if etype in folded:
                continue
            totals[etype] += overload_value(tables, etype, level)
    return [{"name": names[str(t)], "value": round(v, 2)} for t, v in totals.items()]
```

- [ ] **Step 6: Run until 77/77**

Run: `cd backend && /c/Users/Fienn/anaconda3/python -m pytest tests/test_overload_decode.py -q`
Expected: PASS (decode tests + overload parity).

- [ ] **Step 7: Commit**

```bash
git add backend/app/overload_decode.py backend/tests/test_overload_decode.py data/nikke-stat-tables/tables.json
git commit -m "feat: reconstruct overload lines from option ids, verified 77/77 vs ShiftyPad"
```

---

## Task 4: Roster assembly — join + compute + output shape

**Files:**
- Create: `backend/app/roster_assembly.py`
- Test: `backend/tests/test_roster_assembly.py`
- Modify: `scripts/build_stat_ground_truth.py` (reuse the shared extractor; regression: identical fixture)

**Interfaces:**
- Consumes: `stat_assembly.assemble_atk/assemble_hp` + the flat helpers, `overload_decode.assemble_overload`, `stat_assembly.load_stat_tables`.
- Produces:
  - `extract_inputs(directory_entry, owned, detail) -> dict` — the calculator-input record (class/corporation/grade/core/attractive_lv/equip[4]/cube/favorite), i.e. exactly the per-unit dict `build_stat_ground_truth.py` builds today, minus `measured`.
  - `assemble_unit(tables, directory_entry, owned, detail, research_ranks) -> dict` — one `RosterUnit`.
  - `assemble_roster(tables, directory, raw) -> list[dict]` and `to_roster_json(units) -> dict`.

- [ ] **Step 1: Write the failing parity test**

```python
# backend/tests/test_roster_assembly.py
"""Parity: the API+calculator path must reproduce the collector's scraped roster."""
import json
from pathlib import Path
import pytest
from app.roster_assembly import assemble_roster, to_roster_json
from app.stat_assembly import load_stat_tables

ROOT = Path(__file__).resolve().parents[2]
ROSTER = ROOT / "tools" / "collect-blablalink" / "roster.json"
DETAILS = ROOT / "tools" / "collect-blablalink" / "details.json"
DIRECTORY = ROOT / "tools" / "collect-blablalink" / "nikke-directory.json"


@pytest.fixture(scope="module")
def tables():
    return load_stat_tables()


def test_assemble_roster_matches_the_collector_scrape(tables):
    if not (ROSTER.exists() and DETAILS.exists()):
        pytest.skip("local collector dumps not synced")
    directory = json.loads(DIRECTORY.read_text(encoding="utf-8"))
    raw = json.loads(DETAILS.read_text(encoding="utf-8"))
    scraped = {u["resource_id"]: u for u in json.loads(ROSTER.read_text(encoding="utf-8"))["units"]}

    out = {u["resource_id"]: u for u in assemble_roster(tables, directory, raw)}
    off = []
    for rid, want in scraped.items():
        got = out.get(rid)
        if got is None:
            off.append((want["name_en"], "missing from assembled"))
            continue
        if abs(got["raid400"]["atk"] - want["raid400"]["atk"]) >= 1:
            off.append((want["name_en"], "atk", got["raid400"]["atk"], want["raid400"]["atk"]))
        if abs(got["raid400"]["hp"] - want["raid400"]["hp"]) >= 1:
            off.append((want["name_en"], "hp", got["raid400"]["hp"], want["raid400"]["hp"]))
        gov = {o["name"]: round(o["value"], 2) for o in got.get("overload", [])}
        wov = {o["name"]: round(o["value"], 2) for o in (want.get("overload") or [])}
        if gov != wov:
            off.append((want["name_en"], "overload", gov, wov))
    assert off == [], off[:5]
```

- [ ] **Step 2: Run to confirm it fails**

Run: `cd backend && /c/Users/Fienn/anaconda3/python -m pytest tests/test_roster_assembly.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.roster_assembly'`.

- [ ] **Step 3: Implement the assembler**

```python
# backend/app/roster_assembly.py
"""Assemble a fetched blablalink roster into the collector roster.json shape.

The frontend's parseRosterJson consumes that shape, so slug mapping, signature
promotion and merge are reused unchanged. This module only joins the three
fetched payloads with the committed reference tables and computes each unit's
level-400 HP/ATK and overload.
"""
from app import stat_assembly as sa
from app.overload_decode import assemble_overload

SLOTS = ("head", "torso", "arm", "leg")


def extract_inputs(entry: dict, owned: dict, detail: dict) -> dict:
    """The calculator-input record for one unit (class/corp/grade/core/investment)."""
    return {
        "name_en": entry["name_en"],
        "resource_id": entry["resource_id"],
        "class": entry["class"],
        "corporation": entry["corporation"],
        "corporation_sub_type": entry.get("corporation_sub_type"),
        "level": owned["lv"],
        "grade": detail["grade"],
        "core": detail["core"],
        "attractive_lv": detail.get("attractive_lv", 0),
        "favorite_item_lv": detail.get("favorite_item_lv", 0),
        "favorite_item_tid": detail.get("favorite_item_tid", 0),
        "harmony_cube_lv": detail.get("harmony_cube_lv", 0),
        "skill1_lv": detail.get("skill1_lv", 1),
        "skill2_lv": detail.get("skill2_lv", 1),
        "ulti_skill_lv": detail.get("ulti_skill_lv", 1),
        "equip": [
            {
                "slot": s,
                "tid": detail.get(f"{s}_equip_tid", 0),
                "tier": detail.get(f"{s}_equip_tier", 0),
                "corporation_type": detail.get(f"{s}_equip_corporation_type", 0),
                "lv": detail.get(f"{s}_equip_lv", 0),
            }
            for s in SLOTS
        ],
    }


def _extra_flat_atk(tables, inp, research):
    return (
        sa.affinity_atk(tables, inp["class"], inp["attractive_lv"])
        + sa.corporation_atk(tables, inp["corporation"], research)
        + sum(sa.equipment_atk(tables, e["tid"], e["lv"],
                               equip_corporation_type=e["corporation_type"],
                               unit_corporation=inp["corporation"]) for e in inp["equip"])
        + sa.cube_atk(tables, inp["harmony_cube_lv"])
        + sa.collectible_atk(tables, inp["favorite_item_tid"], inp["favorite_item_lv"])
    )


def _extra_flat_hp(tables, inp, research):
    return (
        sa.affinity_hp(tables, inp["class"], inp["attractive_lv"])
        + sa.corporation_hp(tables, inp["corporation"], research)
        + sum(sa.equipment_hp(tables, e["tid"], e["lv"],
                              equip_corporation_type=e["corporation_type"],
                              unit_corporation=inp["corporation"]) for e in inp["equip"])
        + sa.cube_hp(tables, inp["harmony_cube_lv"])
        + sa.collectible_hp(tables, inp["favorite_item_tid"], inp["favorite_item_lv"])
    )


def assemble_unit(tables, entry: dict, owned: dict, detail: dict, research: dict) -> dict:
    inp = extract_inputs(entry, owned, detail)
    ident = dict(corporation=inp["corporation"],
                 corporation_sub_type=inp["corporation_sub_type"],
                 resource_id=inp["resource_id"])
    atk = sa.assemble_atk(tables, character_class=inp["class"], level=400,
                          grade=inp["grade"], core=inp["core"],
                          extra_flat=_extra_flat_atk(tables, inp, research), **ident)
    hp = sa.assemble_hp(tables, character_class=inp["class"], level=400,
                        grade=inp["grade"], core=inp["core"],
                        extra_flat_hp=_extra_flat_hp(tables, inp, research), **ident)
    return {
        "name_en": inp["name_en"],
        "resource_id": inp["resource_id"],
        "raid400": {"hp": round(hp), "atk": round(atk), "def": 0},
        "skill_levels": {
            "skill1": inp["skill1_lv"],
            "skill2": inp["skill2_lv"],
            "burst": inp["ulti_skill_lv"],
        },
        "overload": assemble_overload(tables, detail),
    }


def assemble_roster(tables, directory: list, raw: dict) -> list[dict]:
    by_code = {e["name_code"]: e for e in directory}
    details = {d["name_code"]: d for d in raw["character_details"]}
    owned = {o["name_code"]: o for o in raw["owned"]}
    research = {str(r["tid"]): r["lv"] for r in raw["recycle_room_researches"]}
    units = []
    for code, o in owned.items():
        entry, d = by_code.get(code), details.get(code)
        if entry is None or d is None:
            continue
        units.append(assemble_unit(tables, entry, o, d, research))
    units.sort(key=lambda u: u["name_en"])
    return units


def to_roster_json(units: list[dict]) -> dict:
    return {"units": units}
```

- [ ] **Step 4: Run the parity test until it passes**

Run: `cd backend && /c/Users/Fienn/anaconda3/python -m pytest tests/test_roster_assembly.py -q`
Expected: PASS — assembled ATK/HP/overload match the scrape for every unit. (Resolve any per-unit misses the same way the calculator was verified: they indicate a mapping bug, not a tolerance.)

- [ ] **Step 5: Point the fixture builder at the shared extractor**

In `scripts/build_stat_ground_truth.py`, replace the inline per-unit dict construction with `roster_assembly.extract_inputs(entry, o, d)` plus the `"measured"` block, so the builder and the sync path share one extractor. Then regenerate and diff to prove no change:

```bash
/c/Users/Fienn/anaconda3/python scripts/build_stat_ground_truth.py --out /tmp/gt_new.json
/c/Users/Fienn/anaconda3/python -c "import json;a=json.load(open('backend/tests/fixtures/stat_ground_truth.json',encoding='utf-8'));b=json.load(open('/tmp/gt_new.json',encoding='utf-8'));print('IDENTICAL' if a==b else 'DIFF')"
```
Expected: `IDENTICAL`.

- [ ] **Step 6: Commit**

```bash
git add backend/app/roster_assembly.py backend/tests/test_roster_assembly.py scripts/build_stat_ground_truth.py
git commit -m "feat: assemble a fetched roster into the collector shape, parity-tested vs the scrape"
```

---

## Task 5: Fetch layer — SessionCaller + fetch_roster

**Files:**
- Create: `backend/app/blablalink_api.py`
- Test: `backend/tests/test_blablalink_api.py`

**Interfaces:**
- Produces: `SessionCaller` (Protocol with `call(endpoint: str, body: dict) -> dict`); `fetch_roster(caller: SessionCaller, open_id: str, area: int = 81) -> dict` returning `{"owned": [...], "character_details": [...], "recycle_room_researches": [...]}` — the shape `assemble_roster` (Task 4) consumes.

- [ ] **Step 1: Write the failing test with a fake caller**

```python
# backend/tests/test_blablalink_api.py
from app.blablalink_api import fetch_roster


class FakeCaller:
    """Records calls and replays canned data, standing in for a live session."""
    def __init__(self, responses):
        self.responses = responses
        self.calls = []

    def call(self, endpoint, body):
        self.calls.append((endpoint, body))
        return self.responses[endpoint]


def test_fetch_roster_makes_three_calls_and_bundles_them():
    caller = FakeCaller({
        "GetUserCharacters": {"characters": [{"name_code": 5001, "lv": 400, "core": 3, "grade": 3}]},
        "GetUserCharacterDetails": {"character_details": [{"name_code": 5001, "grade": 3, "core": 3}]},
        "GetUserProfileOutpostInfo": {"outpost_info": {"recycle_room_researches": [{"tid": 1201, "lv": 170}]}},
    })
    out = fetch_roster(caller, "OPENID", area=81)

    # Owned first (its name_codes feed the details call), then details, then outpost.
    assert [c[0] for c in caller.calls] == [
        "GetUserCharacters", "GetUserCharacterDetails", "GetUserProfileOutpostInfo",
    ]
    # Every call carries the identity params.
    for _, body in caller.calls:
        assert body["intl_open_id"] == "OPENID"
        assert body["nikke_area_id"] == 81
    # Details is asked for exactly the owned name_codes.
    assert caller.calls[1][1]["name_codes"] == [5001]
    # Bundled shape is what assemble_roster consumes.
    assert out["owned"][0]["name_code"] == 5001
    assert out["character_details"][0]["name_code"] == 5001
    assert out["recycle_room_researches"] == [{"tid": 1201, "lv": 170}]
```

- [ ] **Step 2: Run to confirm it fails**

Run: `cd backend && /c/Users/Fienn/anaconda3/python -m pytest tests/test_blablalink_api.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'app.blablalink_api'`.

- [ ] **Step 3: Implement the fetch layer**

```python
# backend/app/blablalink_api.py
"""Fetch a blablalink roster over an injected session.

The three endpoints and their param shape were confirmed by cross-account
reconnaissance (2026-07-19): GetUserCharacters -> owned, GetUserCharacterDetails
(name_codes: whole roster in one call) -> investment, GetUserProfileOutpostInfo
-> corporation research ranks. nikke_area_id is 81 for the international server
(NOT the ShiftyPad region id in a share-URL uid). The session is injected as a
SessionCaller so this module never handles credentials; see spec sub-project 4.
"""
from typing import Protocol


class SessionCaller(Protocol):
    def call(self, endpoint: str, body: dict) -> dict:
        """POST to api.blablalink.com/api/game/proxy/Game/<endpoint>; raise on code != 0."""
        ...


def fetch_roster(caller: SessionCaller, open_id: str, area: int = 81) -> dict:
    base = {"intl_open_id": open_id, "nikke_area_id": area}
    owned = caller.call("GetUserCharacters", dict(base)).get("characters", [])
    detail = caller.call(
        "GetUserCharacterDetails",
        {**base, "name_codes": [c["name_code"] for c in owned]},
    )
    outpost = caller.call("GetUserProfileOutpostInfo", dict(base))
    return {
        "owned": owned,
        "character_details": detail.get("character_details", []),
        "recycle_room_researches": outpost["outpost_info"]["recycle_room_researches"],
    }
```

- [ ] **Step 4: Run to verify it passes**

Run: `cd backend && /c/Users/Fienn/anaconda3/python -m pytest tests/test_blablalink_api.py -q`
Expected: PASS.

- [ ] **Step 5: Commit**

```bash
git add backend/app/blablalink_api.py backend/tests/test_blablalink_api.py
git commit -m "feat: session-injected blablalink fetch layer (3 calls -> assembler shape)"
```

---

## Task 6: Full-suite green + end-to-end smoke

**Files:** none new (verification task).

- [ ] **Step 1: Run the whole backend suite**

Run: `cd backend && /c/Users/Fienn/anaconda3/python -m pytest -q`
Expected: PASS — the prior 792 plus the new decode/HP/overload/assembly/fetch tests; no regressions.

- [ ] **Step 2: End-to-end smoke through the fake caller**

Feed `fetch_roster` (FakeCaller replaying a few real recorded units) into `assemble_roster` and assert the output validates against the `RosterUnit` shape (keys `name_en`, `resource_id`, `raid400{hp,atk,def}`, `skill_levels{skill1,skill2,burst}`, `overload[]`). Add this as `test_roster_assembly.py::test_fetch_then_assemble_end_to_end` using 2-3 units copied from `details.json`/`roster.json`.

```python
def test_fetch_then_assemble_end_to_end(tables):
    # A tiny hand-built payload in fetch_roster's output shape -> assemble_roster.
    directory = json.loads(DIRECTORY.read_text(encoding="utf-8"))
    raw = {
        "owned": [{"name_code": 5129, "lv": 400, "core": 6, "grade": 3}],  # Rapi: Red Hood
        "character_details": [{"name_code": 5129, "grade": 3, "core": 6,
                               "attractive_lv": 40, "harmony_cube_lv": 0,
                               "favorite_item_tid": 0, "favorite_item_lv": 0,
                               "skill1_lv": 10, "skill2_lv": 10, "ulti_skill_lv": 10}],
        "recycle_room_researches": [{"tid": 1201, "lv": 170}, {"tid": 1204, "lv": 190}],
    }
    units = assemble_roster(tables, directory, raw)
    u = units[0]
    assert set(u) == {"name_en", "resource_id", "raid400", "skill_levels", "overload"}
    assert set(u["raid400"]) == {"hp", "atk", "def"}
    assert set(u["skill_levels"]) == {"skill1", "skill2", "burst"}
    assert u["raid400"]["def"] == 0
```

- [ ] **Step 3: Run the smoke test**

Run: `cd backend && /c/Users/Fienn/anaconda3/python -m pytest tests/test_roster_assembly.py::test_fetch_then_assemble_end_to_end -q`
Expected: PASS.

- [ ] **Step 4: Commit**

```bash
git add backend/tests/test_roster_assembly.py
git commit -m "test: end-to-end fetch->assemble smoke, RosterUnit shape validated"
```

---

## Notes for the executor

- **The parity/fit tests need the gitignored dumps.** They `pytest.skip` when absent, so they are green-but-vacuous in CI and only bite on Fienn's machine (or any checkout with `roster.json`/`details.json`). This is deliberate — the same posture as the existing stat ground truth.
- **HP and overload are the only derivation tasks.** Their constants come out of the two fit scripts (Tasks 2.5, 3.1), verified by the 159/77 parity gates. If a fit does not close to 0, that is a model bug to chase (as with the ATK per-core-flat), not a tolerance to widen.
- **DEF is 0 on purpose** — `raid_simulator.py` reads only `base_stats[slug]["atk"]` and `["max_hp"]`; it never reads DEF.
- **Signature/favorite-item auto-detection is out of scope** (Phase 7 잔여 ③). The favorite item tid is used inside assembly for `collectible_atk`/`collectible_hp` but is not emitted; the frontend's `SIGNATURE_OWNED` set still governs signature promotion.
