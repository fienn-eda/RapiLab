# Frontend Stage 3 — Roster Assembly + `/api/recommend` Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the web app produce REAL deck recommendations: an automated `UserNikkeState[] → NikkeSpec[]` assembly layer (skill-value parser + per-unit manifests + verification harness), the real FastAPI `POST /api/recommend` endpoint, and the frontend follow-up (excluded-slugs display, live-API wiring).

**Architecture:** Per the approved design spec `docs/superpowers/specs/2026-07-16-roster-assembly-api-design.md`. Each `skill_rules/<slug>.py` module declares a colocated manifest mapping its `skill_values` sub-skill keys to data-file skill indexes; a parser turns raw level data (lootandwaifus text / dotgg native slots) into `description_value_NN` dicts; a verification harness proves every manifest against the unit's own hand-transcribed test fixtures; a loader assembles `NikkeSpec`s from local data files only; FastAPI exposes `find_best_decks` over it. Frontend swaps its dev mock for the live client.

**Tech Stack:** Python (FastAPI, pydantic, pytest, httpx for TestClient), React + Vite + TypeScript (Vitest) under `frontend/`.

## Global Constraints

- Run backend tests with `PYTHONIOENCODING=utf-8 python3 -m pytest tests/ -q` from `backend/` (`python3` is the interpreter with pytest on this machine, NOT `python`).
- Frontend checks: `npx tsc --noEmit` and `npm run test` from `frontend/`.
- TDD: failing test first, minimal implementation, commit per task.
- Non-encoded / non-loadable roster entries are **excluded and reported** in `excluded_slugs` — never a 422 by themselves (Fienn, 2026-07-16). 422 only when the *usable* roster can't form a feasible deck.
- User skill levels honored from day one: parse at `levels[skill_level - 1]`.
- No network at request time: loader reads `data/lootandwaifus/char_<slug>.json` and `data/dotgg/char_*.json` only.
- Harness mismatches are fixed by **per-unit slot overrides**, never by loosening the comparison.
- Data facts (verified 2026-07-16): all 14 `data/dotgg/char_*.json` files carry weapon stats (`maxAmmo`, `damage` e.g. `"214.3%"`, `reloadTime`, `chargeTime`, `chargeDamage` e.g. `"100%"`), per-skill `cooldown`, and 10-entry `levels` of native `description_value_NN` dicts. dotgg **filenames use dotgg's own slug** (`char_drake-nikke.json` for `drake`) — index by the file's `"url"` field, never by filename. lootandwaifus files (53) are keyed by our slug (`char_drake.json`), with top-level `class/weapon/element/burst/cooldown` and `skills[i].levels` as **raw text**.
- Known limitation to flag, not solve here: `find_best_decks` is exhaustive — a large roster (30+) makes the endpoint slow. Note it in the API docstring; optimization is out of scope (discuss with Fienn separately).

---

## File Structure

- `backend/app/skill_values.py` — NEW: level parsers + manifest-driven `assemble_skill_values`.
- `backend/app/skill_rules/<unit>.py` — each gains a `SKILL_VALUE_MANIFESTS` dict (pilot: `drake.py`, `rei_ayanami.py`; then backfill).
- `backend/app/skill_rules/registry.py` — `get_skill_value_manifest(slug)` (pkgutil scan, cached).
- `backend/app/user_roster.py` — NEW: `load_nikke_spec` / `load_roster`.
- `backend/app/api.py` — NEW: FastAPI app, `POST /api/recommend`, CORS.
- `backend/requirements.txt` — add `httpx` (TestClient dependency).
- `backend/tests/test_skill_values.py`, `test_skill_value_assembly.py` (harness), `test_user_roster.py`, `test_api_recommend.py` — NEW.
- `frontend/src/types/recommend.ts`, `src/api/recommendClient.mock.ts`, `src/hooks/useRecommend.ts`, `src/components/DeckResults.tsx` + tests, `vite.config.ts` — modify.
- `frontend/README.md`, `docs/roadmap.md`, `.claude/skills/nikke-skill-encoding/SKILL.md` — docs updates.

### Manifest convention (locked in here, used by every task)

```python
# In each skill_rules/<unit>.py, next to the builders that define the key names.
# One entry per SLUG the module encodes (dual-slug modules declare both).
SKILL_VALUE_MANIFESTS = {
    "drake": {
        "source": "dotgg",                      # which source the module's slot numbering was transcribed from
        "data_slug": "drake",                   # optional; defaults to the slug. The character's canonical
                                                # data-file key (lootandwaifus filename / dotgg "url" field).
                                                # Needed when several slugs share one character file
                                                # (drake-signature -> "drake").
        "test_module": "test_skill_rules_drake",  # where the ground-truth fixtures live
        "keys": {
            # sub-skill key -> (array, index). array is "skills" or "dollskills";
            # index maps to user skill levels: 0 -> skill1, 1 -> skill2, 2 -> burst.
            # dollskills use the SAME user skill levels (a favorite item upgrades
            # the same three skills; there is no separate doll skill level in
            # UserNikkeState).
            "overcharge": ("skills", 0),
            "thunderbolt": ("skills", 1),
            "drake_special": ("skills", 2),
        },
        # optional: fixture constant name when it isn't key.upper()
        "fixtures": {"overcharge": "OVERCHARGE"},   # default key.upper(); shown here for illustration only
        # optional (lootandwaifus source only): 0-based numeric-token indexes to DROP
        # from the raw text before slot numbering — added ONLY where the harness fails.
        "drop_tokens": {"overcharge": [1]},          # illustration only
    },
}
```

---

## Task 1: Skill-value level parsers

**Files:**
- Create: `backend/app/skill_values.py`
- Test: `backend/tests/test_skill_values.py`

**Interfaces:**
- Produces: `extract_lootandwaifus_slots(level_text: str, drop_tokens: Sequence[int] = ()) -> dict[str, str]` — numeric tokens left-to-right → `{"description_value_01": "45.87", ...}` (after dropping the given 0-based token indexes).
- Produces: `dotgg_slots(level_dict: dict) -> dict[str, str]` — passthrough minus empty-string slots.

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_skill_values.py`:

```python
from app.skill_values import dotgg_slots, extract_lootandwaifus_slots

# Real Lv10 text shape from data/lootandwaifus (Ark Ranger Black, Tremble!).
TREMBLE_TEXT = (
    "■ Activates when Transformation takes effect and when the enemy appears "
    "while Transformation is in effect. Affects all enemies.\n"
    "Ark Black Collider: Deals 45.87% of final ATK as sustained damage every 1 sec "
    "until Transformation is canceled.\n"
    "■ Activates when entering Full Burst. Affects all Wind Code allies with assault rifles.\n"
    "Sustained Damage ▲ 77.5% for 10 sec."
)


def test_extracts_numeric_tokens_left_to_right():
    assert extract_lootandwaifus_slots(TREMBLE_TEXT) == {
        "description_value_01": "45.87",
        "description_value_02": "1",
        "description_value_03": "77.5",
        "description_value_04": "10",
    }


def test_drop_tokens_renumbers_remaining_slots():
    # Dropping token #1 ("1" from "every 1 sec") shifts later tokens up.
    assert extract_lootandwaifus_slots(TREMBLE_TEXT, drop_tokens=[1]) == {
        "description_value_01": "45.87",
        "description_value_02": "77.5",
        "description_value_03": "10",
    }


def test_dotgg_slots_pass_through_and_drop_empties():
    level = {"description_value_01": "1254", "description_value_02": "72.18", "description_value_03": ""}
    assert dotgg_slots(level) == {"description_value_01": "1254", "description_value_02": "72.18"}
```

- [ ] **Step 2: Run to verify failure**

Run: `PYTHONIOENCODING=utf-8 python3 -m pytest tests/test_skill_values.py -q` (from `backend/`)
Expected: FAIL — `ModuleNotFoundError: No module named 'app.skill_values'`

- [ ] **Step 3: Implement**

Create `backend/app/skill_values.py`:

```python
"""Turns raw character skill-level data into the `description_value_NN` slot
dicts the skill_rules builders consume.

lootandwaifus stores each level as raw text; encoders hand-numbered its numeric
tokens left-to-right when transcribing fixtures, so the extractor reproduces
exactly that convention. Some encoders skipped non-value numbers (trigger
phrases like "Burst stage 3"); those units carry a per-unit `drop_tokens`
override in their SKILL_VALUE_MANIFESTS, added only where the assembly
verification harness fails (see test_skill_value_assembly.py) — never
speculatively. dotgg levels are already native slot dicts and pass through.
"""
import re

_NUMBER = re.compile(r"\d+(?:\.\d+)?")


def extract_lootandwaifus_slots(level_text, drop_tokens=()):
    dropped = set(drop_tokens)
    tokens = [t for i, t in enumerate(_NUMBER.findall(level_text)) if i not in dropped]
    return {f"description_value_{i + 1:02d}": token for i, token in enumerate(tokens)}


def dotgg_slots(level_dict):
    return {key: value for key, value in level_dict.items() if value != ""}
```

- [ ] **Step 4: Run to verify pass** — same command, expected: 3 passed.
- [ ] **Step 5: Commit** — `git add backend/app/skill_values.py backend/tests/test_skill_values.py && git commit -m "Skill-value level parsers (lootandwaifus token extraction, dotgg passthrough)"`

---

## Task 2: Manifest-driven assembly + registry aggregation + pilot manifests

**Files:**
- Modify: `backend/app/skill_values.py` (add `assemble_skill_values`)
- Modify: `backend/app/skill_rules/drake.py`, `backend/app/skill_rules/rei_ayanami.py` (add `SKILL_VALUE_MANIFESTS`)
- Modify: `backend/app/skill_rules/registry.py` (add `get_skill_value_manifest`)
- Test: `backend/tests/test_skill_values.py` (extend)

**Interfaces:**
- Consumes: Task 1 parsers.
- Produces: `assemble_skill_values(slug, manifest, skill_levels: dict, data_dir: Path = DATA_DIR) -> dict[str, dict]` — `{"overcharge": {"description_value_01": ...}, ...}` at the given per-skill levels (`{"skill1": 10, "skill2": 10, "burst": 10}`). Raises `KeyError`/`FileNotFoundError`/`IndexError` on unusable data (loader turns those into exclusion).
- Produces: `registry.get_skill_value_manifest(slug) -> dict | None` — merged `SKILL_VALUE_MANIFESTS` from every module in `app.skill_rules` (pkgutil scan, cached).

- [ ] **Step 1: Write the failing tests** (append to `backend/tests/test_skill_values.py`)

```python
from app.skill_rules.registry import get_skill_value_manifest
from app.skill_values import assemble_skill_values


def test_registry_exposes_pilot_manifests():
    manifest = get_skill_value_manifest("drake")
    assert manifest["source"] == "dotgg"
    assert manifest["keys"]["drake_special"] == ("skills", 2)
    assert get_skill_value_manifest("not-a-slug") is None


def test_assemble_drake_max_level_from_real_data_file():
    manifest = get_skill_value_manifest("drake")
    values = assemble_skill_values(
        "drake", manifest, {"skill1": 10, "skill2": 10, "burst": 10}
    )
    # Ground truth: DRAKE_SPECIAL fixture in test_skill_rules_drake.py.
    assert float(values["drake_special"]["description_value_01"]) == 1254.0


def test_assemble_respects_user_skill_level():
    manifest = get_skill_value_manifest("drake")
    lv10 = assemble_skill_values("drake", manifest, {"skill1": 10, "skill2": 10, "burst": 10})
    lv1 = assemble_skill_values("drake", manifest, {"skill1": 10, "skill2": 10, "burst": 1})
    assert float(lv1["drake_special"]["description_value_01"]) < float(
        lv10["drake_special"]["description_value_01"]
    )
```

- [ ] **Step 2: Run to verify failure** — `ImportError: cannot import name 'get_skill_value_manifest'`.

- [ ] **Step 3: Implement**

Append to `backend/app/skill_values.py`:

```python
import json
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"

_SKILL_INDEX_TO_LEVEL_KEY = {0: "skill1", 1: "skill2", 2: "burst"}

_dotgg_url_index: dict[Path, dict] = {}


def _dotgg_path_for(data_slug, data_dir):
    """dotgg filenames use dotgg's own slug (char_drake-nikke.json for "drake"),
    so files are indexed once by their "url" field, never located by filename."""
    dotgg_dir = Path(data_dir) / "dotgg"
    if dotgg_dir not in _dotgg_url_index:
        index = {}
        for path in sorted(dotgg_dir.glob("char_*.json")):
            data = json.loads(path.read_text(encoding="utf-8"))
            index[data.get("url")] = path
        _dotgg_url_index[dotgg_dir] = index
    path = _dotgg_url_index[dotgg_dir].get(data_slug)
    if path is None:
        raise FileNotFoundError(f"no dotgg data file with url {data_slug!r}")
    return path


def load_character_data(source, data_slug, data_dir=DATA_DIR):
    if source == "dotgg":
        path = _dotgg_path_for(data_slug, data_dir)
    else:
        path = Path(data_dir) / "lootandwaifus" / f"char_{data_slug}.json"
    return json.loads(path.read_text(encoding="utf-8"))


def assemble_skill_values(slug, manifest, skill_levels, data_dir=DATA_DIR):
    data = load_character_data(manifest["source"], manifest.get("data_slug", slug), data_dir)
    values = {}
    for key, (array, index) in manifest["keys"].items():
        level = skill_levels[_SKILL_INDEX_TO_LEVEL_KEY[index]]
        raw_level = data[array][index]["levels"][level - 1]
        if manifest["source"] == "dotgg":
            values[key] = dotgg_slots(raw_level)
        else:
            values[key] = extract_lootandwaifus_slots(
                raw_level, manifest.get("drop_tokens", {}).get(key, ())
            )
    return values
```

Add to `backend/app/skill_rules/drake.py` (after the docstring/imports):

```python
SKILL_VALUE_MANIFESTS = {
    "drake": {
        "source": "dotgg",
        "test_module": "test_skill_rules_drake",
        "keys": {
            "overcharge": ("skills", 0),
            "thunderbolt": ("skills", 1),
            "drake_special": ("skills", 2),
        },
    },
    "drake-signature": {
        "source": "dotgg",
        "data_slug": "drake",
        "test_module": "test_skill_rules_drake",
        "keys": {
            "overcharge": ("dollskills", 0),
            "thunderbolt": ("dollskills", 1),
            "drake_special": ("dollskills", 2),
        },
        "fixtures": {
            "overcharge": "OVERCHARGE_SIG",
            "thunderbolt": "THUNDERBOLT_SIG",
            "drake_special": "DRAKE_SPECIAL_SIG",
        },
    },
}
```

(Verify the dollskills array shape in `data/dotgg/char_drake-nikke.json` while writing this — if dollskills levels differ structurally, adjust `assemble_skill_values` here, not the manifest.)

Add to `backend/app/skill_rules/rei_ayanami.py` — the lootandwaifus pilot. Skill order in `data/lootandwaifus/char_rei-ayanami.json` (verified 2026-07-16): `skills[0]` = Preemptive Subdual, `skills[1]` = Attack Support, `skills[2]` = Annihilation: High Explosives. Fixture constants default to `key.upper()` — confirm `PREEMPTIVE_SUBDUAL`/`ATTACK_SUPPORT`/`ANNIHILATION` exist at module level in `test_skill_rules_rei_ayanami.py` (add `fixtures` overrides if named differently):

```python
SKILL_VALUE_MANIFESTS = {
    "rei-ayanami": {
        "source": "lootandwaifus",
        "test_module": "test_skill_rules_rei_ayanami",
        "keys": {
            "preemptive_subdual": ("skills", 0),
            "attack_support": ("skills", 1),
            "annihilation": ("skills", 2),
        },
    },
}
```

Add to `backend/app/skill_rules/registry.py` (bottom of file):

```python
import importlib
import pkgutil

import app.skill_rules as _skill_rules_package

_skill_value_manifest_cache = None


def get_skill_value_manifest(slug):
    """The colocated SKILL_VALUE_MANIFESTS entry for `slug`, or None. A module
    without a manifest is simply not loadable from user data (excluded +
    reported, same as a non-encoded slug) - see user_roster.load_nikke_spec."""
    global _skill_value_manifest_cache
    if _skill_value_manifest_cache is None:
        merged = {}
        for info in pkgutil.iter_modules(_skill_rules_package.__path__):
            if info.name.startswith("_"):
                continue
            module = importlib.import_module(f"app.skill_rules.{info.name}")
            merged.update(getattr(module, "SKILL_VALUE_MANIFESTS", {}))
        _skill_value_manifest_cache = merged
    return _skill_value_manifest_cache.get(slug)
```

- [ ] **Step 4: Run to verify pass** — `PYTHONIOENCODING=utf-8 python3 -m pytest tests/test_skill_values.py -q`, expected: all pass.
- [ ] **Step 5: Run the full suite** (`... -m pytest tests/ -q`) — must stay green (pkgutil import of every module must not explode).
- [ ] **Step 6: Commit** — `feat: manifest-driven skill-value assembly + pilot manifests (drake, rei-ayanami)`

---

## Task 3: Verification harness (the correctness anchor)

**Files:**
- Test: `backend/tests/test_skill_value_assembly.py` (new)

**Interfaces:**
- Consumes: `get_skill_value_manifest`, `assemble_skill_values`, each unit test module's module-level fixture dicts.

- [ ] **Step 1: Write the harness**

```python
"""Assembly verification harness: for EVERY encoded unit that declares a
SKILL_VALUE_MANIFESTS entry, assemble max-level skill_values from the local
data files and compare each slot against the values the unit's own test
fixtures assert (the fixtures are ground truth - hand-transcribed during
encoding, and every builder is tested against them). A mismatch is fixed by a
drop_tokens override in that unit's manifest, NEVER by loosening this
comparison. New encodings must declare a manifest and pass this too (see the
nikke-skill-encoding skill workflow)."""
import importlib.util
from pathlib import Path

import pytest

from app.skill_rules.registry import ENCODED_SLUGS, get_skill_value_manifest
from app.skill_values import assemble_skill_values

MAX_LEVELS = {"skill1": 10, "skill2": 10, "burst": 10}

MANIFEST_SLUGS = [slug for slug in ENCODED_SLUGS if get_skill_value_manifest(slug)]


def _load_test_module(name):
    path = Path(__file__).with_name(f"{name}.py")
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_at_least_the_pilots_have_manifests():
    assert {"drake", "drake-signature", "rei-ayanami"} <= set(MANIFEST_SLUGS)


@pytest.mark.parametrize("slug", MANIFEST_SLUGS)
def test_assembled_max_level_values_match_fixtures(slug):
    manifest = get_skill_value_manifest(slug)
    values = assemble_skill_values(slug, manifest, MAX_LEVELS)
    fixtures_module = _load_test_module(manifest["test_module"])
    for key in manifest["keys"]:
        fixture_name = manifest.get("fixtures", {}).get(key, key.upper())
        fixture = getattr(fixtures_module, fixture_name)
        parsed = values[key]
        for slot, expected in fixture.items():
            assert slot in parsed, f"{slug}.{key}: parser produced no {slot} (got {sorted(parsed)})"
            assert float(parsed[slot]) == pytest.approx(float(expected)), (
                f"{slug}.{key}.{slot}: parsed {parsed[slot]!r} != fixture {expected!r}"
            )
```

- [ ] **Step 2: Run it** — `PYTHONIOENCODING=utf-8 python3 -m pytest tests/test_skill_value_assembly.py -v`
Expected: pilots pass, or fail with a **clear per-slot diff**. Fix any pilot failure with a `drop_tokens` entry (lootandwaifus) — investigate the raw text first; the override lists exactly the trigger-phrase token indexes to skip.
- [ ] **Step 3: Commit** — `test: assembly verification harness over manifest-declaring units`

---

## Task 4: Roster loader

**Files:**
- Create: `backend/app/user_roster.py`
- Test: `backend/tests/test_user_roster.py`

**Interfaces:**
- Consumes: `UserNikkeState` (`app.models`), `NikkeSpec` (`app.roster`), `assemble_skill_values`/`load_character_data` (Task 2), `get_skill_value_manifest`, `ENCODED_SLUGS`.
- Produces: `load_nikke_spec(state: UserNikkeState) -> NikkeSpec | None` (None = not loadable); `load_roster(states: list[UserNikkeState]) -> tuple[list[NikkeSpec], list[str]]` (specs, excluded_slugs in submission order, deduped).

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_user_roster.py`:

```python
from app.models import UserNikkeState
from app.user_roster import load_nikke_spec, load_roster


def _state(slug, **overrides):
    payload = {
        "character_slug": slug,
        "level": 200,
        "core_level": 0,
        "hp": 1_000_000.0,
        "atk": 60_000.0,
        "def_": 3_000.0,
        "skill_levels": {"skill1": 10, "skill2": 10, "burst": 10},
    }
    payload.update(overrides)
    return UserNikkeState(**payload)


def test_loads_drake_end_to_end_from_real_data_files():
    spec = load_nikke_spec(_state("drake"))
    assert spec is not None
    assert spec.burst_tier == 3
    assert spec.element == "Fire"
    assert spec.weapon == "SG"
    assert spec.burst_cooldown == 40.0
    assert spec.base_stats == {"atk": 60_000.0, "def": 3_000.0, "max_hp": 1_000_000.0}
    # weapon stats from data/dotgg/char_drake-nikke.json ("damage": "214.3%", maxAmmo 9, ...)
    assert spec.weapon_stats == {
        "weapon": "SG", "damage_percent": 214.3, "max_ammo": 9,
        "reload_time": 0.5, "charge_time": 0.0, "charge_damage_percent": 100.0,
    }
    # skill values assembled at max level (DRAKE_SPECIAL fixture ground truth)
    assert float(spec.skill_values["drake_special"]["description_value_01"]) == 1254.0


def test_skill_levels_flow_into_assembled_values():
    lv1 = load_nikke_spec(_state("drake", skill_levels={"skill1": 10, "skill2": 10, "burst": 1}))
    lv10 = load_nikke_spec(_state("drake"))
    assert float(lv1.skill_values["drake_special"]["description_value_01"]) < float(
        lv10.skill_values["drake_special"]["description_value_01"]
    )


def test_overload_and_cube_pass_through():
    spec = load_nikke_spec(_state(
        "drake",
        overload_options=[{"name": "Increases ATK", "value": 10.0}],
        pve_cube={"name": "Resilience Cube", "level": 7},
    ))
    assert spec.overload_options == [{"name": "Increases ATK", "value": 10.0}]
    assert spec.cube == {"name": "Resilience Cube", "level": 7}


def test_unloadable_units_are_excluded_not_errors():
    assert load_nikke_spec(_state("totally-unknown")) is None          # not encoded
    assert load_nikke_spec(_state("crown")) is None                    # encoded, but no manifest yet (backfill pending)


def test_load_roster_partitions_specs_and_excluded():
    specs, excluded = load_roster([_state("drake"), _state("totally-unknown"), _state("crown")])
    assert [s.slug for s in specs] == ["drake"]
    assert excluded == ["totally-unknown", "crown"]
```

(If Task 6's backfill later gives `crown` a manifest, swap that assertion's slug for a still-manifestless one or drop it — the exclusion path stays covered by `totally-unknown` + the missing-dotgg case below.)

- [ ] **Step 2: Run to verify failure** — `ModuleNotFoundError: app.user_roster`.

- [ ] **Step 3: Implement**

Create `backend/app/user_roster.py`:

```python
"""Assembles a user's submitted roster (UserNikkeState, from the web form)
into engine NikkeSpecs using LOCAL data files only - the glue between the API
and assemble_simulation_inputs / find_best_decks.

A unit that can't be loaded is EXCLUDED and reported, never an error (Fienn,
2026-07-16): not encoded; encoded but no SKILL_VALUE_MANIFESTS yet; missing a
data file (e.g. lootandwaifus-only units have no dotgg weapon stats until
collected). Character metadata prefers the lootandwaifus file (project source
priority) and falls back to the dotgg file; weapon stats come from dotgg only.
"""
from pathlib import Path

from app.models import UserNikkeState
from app.roster import NikkeSpec
from app.skill_rules.registry import ENCODED_SLUGS, get_skill_value_manifest
from app.skill_values import DATA_DIR, assemble_skill_values, load_character_data

_WEAPON_STAT_FIELDS = ("weapon", "maxAmmo", "damage", "reloadTime", "chargeTime", "chargeDamage")


def _percent(raw):
    return float(str(raw).rstrip("%"))


def _weapon_stats(dotgg_data):
    if any(field not in dotgg_data for field in _WEAPON_STAT_FIELDS):
        return None
    return {
        "weapon": dotgg_data["weapon"],
        "damage_percent": _percent(dotgg_data["damage"]),
        "max_ammo": int(dotgg_data["maxAmmo"]),
        "reload_time": float(dotgg_data["reloadTime"]),
        "charge_time": float(dotgg_data["chargeTime"]),
        "charge_damage_percent": _percent(dotgg_data["chargeDamage"]),
    }


def load_nikke_spec(state: UserNikkeState, data_dir: Path = DATA_DIR) -> NikkeSpec | None:
    slug = state.character_slug
    if slug not in ENCODED_SLUGS:
        return None
    manifest = get_skill_value_manifest(slug)
    if manifest is None:
        return None
    data_slug = manifest.get("data_slug", slug)
    try:
        dotgg = load_character_data("dotgg", data_slug, data_dir)
    except FileNotFoundError:
        return None
    weapon_stats = _weapon_stats(dotgg)
    if weapon_stats is None:
        return None
    try:
        meta = load_character_data("lootandwaifus", data_slug, data_dir)
    except FileNotFoundError:
        meta = dotgg
    try:
        skill_values = assemble_skill_values(
            slug, manifest, state.skill_levels.model_dump(), data_dir
        )
        burst_tier = int(meta["burst"])
        burst_cooldown = float(meta.get("cooldown") or meta["skills"][2]["cooldown"])
        element, weapon = meta["element"], meta["weapon"]
    except (KeyError, IndexError, TypeError, ValueError):
        return None
    return NikkeSpec(
        slug=slug,
        burst_tier=burst_tier,
        burst_cooldown=burst_cooldown,
        element=element,
        weapon=weapon,
        base_stats={"atk": state.atk, "def": state.def_, "max_hp": state.hp},
        skill_values=skill_values,
        weapon_stats=weapon_stats,
        overload_options=[o.model_dump() for o in state.overload_options],
        cube=state.pve_cube.model_dump() if state.pve_cube else None,
    )


def load_roster(states: list[UserNikkeState], data_dir: Path = DATA_DIR):
    specs, excluded, seen = [], [], set()
    for state in states:
        spec = load_nikke_spec(state, data_dir)
        if spec is not None:
            specs.append(spec)
        elif state.character_slug not in seen:
            excluded.append(state.character_slug)
        seen.add(state.character_slug)
    return specs, excluded
```

Check `overload_options_to_effects` / `cube_to_effects` expected dict shapes against `roster.py`'s `_passive_effects` (cube uses `reload_speed_percent`/`superior_code_damage_percent` keys, which `PveCube` doesn't carry — read `app/cube_effects.py` and convert `PveCube(name, level)` to whatever it consumes; if cube effects need a name→stats lookup that doesn't exist yet, pass the cube through as `{"name": ..., "level": ...}` only if `_passive_effects` tolerates missing keys via `.get`, which it does — verify with a test rather than assuming).

- [ ] **Step 4: Run to verify pass** — `... -m pytest tests/test_user_roster.py -q`.
- [ ] **Step 5: Full suite green; commit** — `feat: user-roster loader (UserNikkeState -> NikkeSpec, exclusion-based)`

---

## Task 5: FastAPI `POST /api/recommend`

**Files:**
- Create: `backend/app/api.py`
- Modify: `backend/requirements.txt` (add `httpx`)
- Test: `backend/tests/test_api_recommend.py`

**Interfaces:**
- Consumes: `load_roster` (Task 4), `BossProfile`/`find_best_decks` (`app.deck_search`).
- Produces: `POST /api/recommend` per `frontend/README.md` contract **plus `excluded_slugs`**; FastAPI default 422 shape for malformed bodies / infeasible usable roster; CORS for `http://localhost:5173`. Run with `uvicorn app.api:app --reload` from `backend/`.

- [ ] **Step 0: Prerequisite — run Task 6's priority batch (1) first.** At this point only the pilots have manifests, and `rei-ayanami` has no dotgg file, so the only loadable units are `drake`/`drake-signature` — not a feasible deck. Backfill the 13 dotgg-file units (Task 6, batch 1) before this task so the feasible-roster test below has real tiers 1/2/3 to load.

- [ ] **Step 1: Install deps** — `python3 -m pip install -r requirements.txt` after appending `httpx` to `backend/requirements.txt` (fastapi/uvicorn are already listed but not installed in this env).

- [ ] **Step 2: Write the failing tests**

Create `backend/tests/test_api_recommend.py`:

```python
from fastapi.testclient import TestClient

from app.api import app

client = TestClient(app)


def _nikke(slug, burst_tier_hint_atk=60_000.0):
    return {
        "character_slug": slug,
        "level": 200,
        "core_level": 0,
        "hp": 1_000_000.0,
        "atk": burst_tier_hint_atk,
        "def_": 3_000.0,
        "skill_levels": {"skill1": 10, "skill2": 10, "burst": 10},
    }


BOSS = {"element": "Water", "core_hittable": False, "enemy_def": 0,
        "fight_duration": 180, "part_destructible": False}

# Five loadable slugs covering burst tiers 1/2/3 - pick from the units that
# have BOTH a manifest and a dotgg data file at implementation time (after
# Task 6's first backfill batch; e.g. tier 1: little-mermaid, tier 2:
# arcana/grave/mint/nayuta/brid-silent-track, tier 3: drake/modernia/rapi-red-hood).
FEASIBLE = ["little-mermaid", "arcana", "grave", "drake", "modernia"]


def test_feasible_roster_returns_ranked_decks_and_exclusions():
    roster = [_nikke(slug) for slug in FEASIBLE] + [_nikke("totally-unknown")]
    response = client.post("/api/recommend", json={"roster": roster, "boss": BOSS, "top_n": 3})
    assert response.status_code == 200
    body = response.json()
    assert body["excluded_slugs"] == ["totally-unknown"]
    assert 1 <= len(body["decks"]) <= 3
    totals = [d["total_damage"] for d in body["decks"]]
    assert totals == sorted(totals, reverse=True)
    first = body["decks"][0]
    assert set(first) == {"deck", "total_damage", "burst_damage", "normal_attack_damage"}
    assert len(first["deck"]) == 5


def test_infeasible_after_exclusion_is_422_naming_exclusions():
    response = client.post(
        "/api/recommend",
        json={"roster": [_nikke("totally-unknown")] * 5, "boss": BOSS},
    )
    assert response.status_code == 422
    assert "totally-unknown" in str(response.json()["detail"])


def test_malformed_body_is_422():
    response = client.post("/api/recommend", json={"roster": "nope", "boss": BOSS})
    assert response.status_code == 422
```

- [ ] **Step 3: Run to verify failure**, then implement `backend/app/api.py`:

```python
"""FastAPI surface for the deck recommender - the real POST /api/recommend
behind frontend/README.md's contract (plus excluded_slugs, per the roster
assembly design spec). Run from backend/: uvicorn app.api:app --reload

Known limitation: find_best_decks is exhaustive; a 30+ unit usable roster
makes this endpoint slow. Deliberately not optimized here (flagged to Fienn).
"""
from typing import Literal

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app.deck_search import BossProfile, find_best_decks
from app.models import UserNikkeState
from app.user_roster import load_roster


class BossProfileIn(BaseModel):
    element: Literal["Fire", "Water", "Wind", "Iron", "Electric"] | None = None
    core_hittable: bool = False
    enemy_def: float = 0.0
    fight_duration: float = 180.0
    part_destructible: bool = False


class RecommendRequest(BaseModel):
    roster: list[UserNikkeState]
    boss: BossProfileIn
    top_n: int = Field(default=5, ge=1)


class DeckRecommendation(BaseModel):
    deck: list[str]
    total_damage: float
    burst_damage: float
    normal_attack_damage: float


class RecommendResponse(BaseModel):
    decks: list[DeckRecommendation]
    excluded_slugs: list[str]


app = FastAPI(title="NIKKE Deck Builder")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/api/recommend", response_model=RecommendResponse)
def recommend(request: RecommendRequest) -> RecommendResponse:
    specs, excluded = load_roster(request.roster)
    boss = BossProfile(
        element=request.boss.element,
        core_hittable=request.boss.core_hittable,
        enemy_def=request.boss.enemy_def,
        fight_duration=request.boss.fight_duration,
        part_destructible=request.boss.part_destructible,
    )
    results = find_best_decks(specs, boss, top_n=request.top_n)
    if not results:
        raise HTTPException(
            status_code=422,
            detail=(
                "No feasible 5-unit deck (burst tiers 1, 2 and 3 all required) "
                f"in the usable roster. Excluded (not yet supported): {excluded}."
            ),
        )
    return RecommendResponse(
        decks=[
            DeckRecommendation(
                deck=r["deck"], total_damage=r["total_damage"],
                burst_damage=r["burst_damage"], normal_attack_damage=r["normal_attack_damage"],
            )
            for r in results
        ],
        excluded_slugs=excluded,
    )
```

- [ ] **Step 4: Tests pass; also smoke it manually**: `uvicorn app.api:app` + one `curl`/`Invoke-RestMethod` POST; verify a `part_destructible: true` request completes (flag reaches the sim via BossProfile — an Ark-Ranger-including deck assertion belongs in the API test once `ark-ranger-black` has a manifest + dotgg stats; add it then).
- [ ] **Step 5: Commit** — `feat: POST /api/recommend endpoint (roster assembly -> find_best_decks, excluded_slugs)`

---

## Task 6: Manifest backfill over the remaining encoded units

**Files:** every `backend/app/skill_rules/<unit>.py` without `SKILL_VALUE_MANIFESTS`; occasionally its test module (only to expose fixtures at module level if any are currently function-local).

This is deliberately mechanical and harness-driven — no per-unit code in this plan because the harness (Task 3) defines done-ness exactly. **Batch by 8–10 units per commit**, priority order: (1) units with a dotgg data file (immediately API-loadable: `ade-agent-bunny`, `anchor-innocent-maid`, `arcana`, `arcana-fortune-mate`, `blanc`, `brid-silent-track`, `grave`, `little-mermaid`, `mast-romantic-maid`, `mint`, `modernia`, `nayuta`, `rapi-red-hood`), (2) everything else (loadable later, once their dotgg stats are collected).

Per unit, the loop is:

- [ ] Read the module's builders → list its sub-skill keys and which `skills[i]`/`dollskills[i]` each was transcribed from (the module docstring names the skills; `SKILL_VALUE_SOURCE` is whatever the docstring/fixtures say the data came from).
- [ ] Declare `SKILL_VALUE_MANIFESTS` (same shape as the pilots).
- [ ] Run `PYTHONIOENCODING=utf-8 python3 -m pytest tests/test_skill_value_assembly.py -q -k <slug>`.
- [ ] On a slot mismatch (lootandwaifus units): open the raw level text, identify the trigger-phrase token(s) the encoder skipped, add `drop_tokens` for exactly those indexes, re-run. Never touch the fixture or the harness.
- [ ] If a unit's values genuinely can't be reproduced from the data file (e.g. derived constants) — leave it manifestless with a `# no SKILL_VALUE_MANIFESTS: <reason>` comment; it stays excluded, honestly.
- [ ] Commit per batch: `feat: skill-value manifests batch N (<slugs>)` — full suite green each time.

Also in this task: add the workflow step to `.claude/skills/nikke-skill-encoding/SKILL.md` — "declare `SKILL_VALUE_MANIFESTS`; run the assembly verification harness" — so every future encoding ships with a manifest.

---

## Task 7: Frontend follow-up (excluded slugs + live wiring)

**Files:**
- Modify: `frontend/src/types/recommend.ts`, `src/api/recommendClient.mock.ts`, `src/hooks/useRecommend.ts`, `src/components/DeckResults.tsx`, `src/components/RecommendPanel.tsx`
- Modify: `frontend/vite.config.ts` (dev proxy)
- Test: `frontend/src/components/DeckResults.test.tsx`, `src/hooks/useRecommend.test.ts` (extend)

**Interfaces:**
- Consumes: the deployed response shape `{decks, excluded_slugs}`.
- Produces: `RecommendResponse.excluded_slugs: string[]`; `useRecommend` exposes `excludedSlugs: string[]`; results view renders a "not yet supported" list; `VITE_RECOMMEND_API=live npm run dev` talks to `uvicorn` on :8000 through the Vite proxy.

- [ ] **Step 1: Types** — in `types/recommend.ts` add to `RecommendResponse`:

```ts
export interface RecommendResponse {
  decks: DeckRecommendation[] // ranked by total_damage desc, length <= top_n
  excluded_slugs: string[] // submitted slugs the backend can't evaluate yet (not encoded / no data); shown as "not yet supported"
}
```

- [ ] **Step 2: Failing tests** — extend `useRecommend.test.ts` (mock resolves `{decks, excluded_slugs: ['some-slug']}` → hook exposes it) and `DeckResults.test.tsx` (renders the excluded list when non-empty, nothing when empty). Run `npm run test` — fail.

- [ ] **Step 3: Implement**
  - `recommendClient.mock.ts`: return `{ decks, excluded_slugs: [] }` (and keep the 422 path unchanged).
  - `useRecommend.ts`: add `excludedSlugs` state set from `response.excluded_slugs`, expose it in `RecommendState`.
  - `DeckResults.tsx` (or `RecommendPanel.tsx`, whichever owns the results block — match existing composition): render

```tsx
{excludedSlugs.length > 0 && (
  <p className="deck-results__excluded">
    Not yet supported (excluded from search): {excludedSlugs.join(', ')}
  </p>
)}
```

- [ ] **Step 4: Vite dev proxy** — the live client fetches a *relative* `/api/recommend`, which hits the Vite origin, so proxy it (CORS alone doesn't reroute a relative URL). In `frontend/vite.config.ts`:

```ts
server: {
  proxy: { '/api': 'http://localhost:8000' },
},
```

- [ ] **Step 5: Verify end to end** — `uvicorn app.api:app` (backend/) + `VITE_RECOMMEND_API=live npm run dev` (frontend/); submit a roster containing the Task 5 FEASIBLE slugs plus one junk slug; see ranked decks + the excluded line. `npx tsc --noEmit` and `npm run test` green.
- [ ] **Step 6: Commit** — `frontend: excluded_slugs display + live /api/recommend wiring (vite proxy)`

---

## Task 8: Contract + docs sweep

- [ ] `frontend/README.md`: add `excluded_slugs` to the response shape; flip endpoint status to implemented with the `uvicorn app.api:app` dev command + proxy note; document `VITE_RECOMMEND_API=live`.
- [ ] `docs/superpowers/specs/2026-07-16-roster-assembly-api-design.md`: Status → implemented.
- [ ] `docs/roadmap.md`: Phase 6 status → 🔄 (input UI + results UI + live API done; ShiftyPad automation still Phase 7), tick the To-Do items "React 입력 폼"/"FastAPI 백엔드 엔드포인트" and the `NikkeSpec` skill-level To-Do (folded into the loader), note the dotgg-stats collection gap (encoded units without dotgg files stay excluded — future collection batch).
- [ ] `/document` the decisions: manifest colocation + harness-as-anchor; exclusion-over-422; dotgg url-field indexing.
- [ ] Full backend suite + frontend tests green. Commit — `docs: stage 3 contract flip + roadmap`.

---

## Self-review checklist (run after writing code, per task)

- Spec coverage: parser §2 ✓ (T1), manifest §1 ✓ (T2), harness §3 ✓ (T3), loader §4 ✓ (T4), endpoint §5 ✓ (T5), contract/frontend §6 ✓ (T7/T8). Out-of-scope items (Phase 5, auth, ShiftyPad scraping, dotgg stat collection) stay out.
- The harness compares floats (never string-equality) and fails with slug/key/slot context.
- `load_roster` never raises for a bad unit — every failure path returns None → excluded.
- Frontend mock and live client stay swappable at `recommend.ts` only.
