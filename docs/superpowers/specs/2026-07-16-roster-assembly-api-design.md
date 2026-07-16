# Roster assembly layer + /api/recommend endpoint (design)

- Date: 2026-07-16
- Status: implemented (2026-07-16 — parsers/manifests/harness/loader/endpoint/frontend wiring; manifest backfill batch 2 pending)
- Scope: the missing glue between the web app and the engine: an automated
  `UserNikkeState[] → NikkeSpec[]` assembly layer, and the real FastAPI
  `POST /api/recommend` endpoint on top of it. Fienn chose "build the assembly
  layer properly" over deferring or hand-assembling a demo subset.

## Problem

`NikkeSpec` (what `assemble_simulation_inputs` → `find_best_decks` consume) has
only ever been constructed by hand in tests. Three pieces of glue are missing:

1. **Skill values**: builders take `skill_values` dicts keyed by
   module-chosen sub-skill names (e.g. `values["transform"]`) holding
   `description_value_NN` slots. lootandwaifus data stores each skill level as
   **raw text**; encoders hand-numbered slots left-to-right. No loader exists.
2. **Sub-skill key mapping**: the key names (`"transform"`, `"sparkling_boost"`)
   are per-module conventions; no data maps them to skill indexes.
3. **weapon_stats**: hand-invented in tests. (Resolved: dotgg character JSON
   carries real values — `damage`, `maxAmmo`, `reloadTime`, `chargeTime`,
   `chargeDamage`, plus `weapon`/`element`/`burst`/`cooldown`.)

## Decisions already made (Fienn, 2026-07-16)

- Build the assembly layer properly (not a hand-assembled demo, not deferred).
- Non-encoded Nikkes in the submitted roster are **excluded from the search and
  reported** in a new `excluded_slugs` response field — never a 422. Users
  enter their whole roster; the UI can label unsupported characters.
- User skill levels are honored from day one: `levels[level-1]` per skill
  (roadmap To-Do item folded in).

## Components

### 1. Per-unit assembly manifest (colocated with each builder)

Each `skill_rules/<slug>.py` module declares, next to the builders that define
the key names:

```python
SKILL_VALUE_KEYS = {"transform": 0, "tremble": 1, "ultimate": 2}
SKILL_VALUE_SOURCE = "lootandwaifus"  # or "dotgg" — the source this module's
                                      # slot numbering was transcribed from
```

The registry aggregates them (like `_BUILDERS`) into
`get_skill_value_manifest(slug)`. Colocation keeps the mapping beside the code
that depends on it; a module without a manifest is simply not loadable from
user data (excluded + reported, same as non-encoded).

### 2. Skill-value parser

`backend/app/skill_values.py`:

- **lootandwaifus source**: extract numeric tokens left-to-right from the
  level's raw text → `{"description_value_01": ..., ...}` — the same convention
  encoders used by hand.
- **dotgg source**: the API already provides native `description_value_NN`
  slots per level; use them as-is.
- **Known hazard**: trigger-phrase numbers. Encoders skipped some non-value
  numbers (e.g. Anis: Sparkling Summer's "Burst stage 3" is NOT a slot) while
  counting others (Rei's "after 100 normal attack(s)" IS slot _01). Pure
  left-to-right extraction therefore mismatches some modules. Resolution: a
  per-unit **slot override** table in the manifest
  (`SKILL_VALUE_SLOT_OVERRIDES`, e.g. "skill 1: drop token #2"), populated
  exactly where the verification harness (below) fails — no speculative
  heuristics.

### 3. Verification harness (the correctness anchor)

A test that, for **every** encoded unit with a manifest, assembles max-level
`skill_values` from the local data files and compares each slot against the
values the unit's own test fixtures assert (the fixtures are the ground truth —
they were hand-transcribed during encoding and every builder is tested against
them). Any mismatch fails with a clear per-slot diff and is fixed by an
override entry, never by loosening the comparison. New encodings must pass it
too — the `nikke-skill-encoding` skill gains a workflow step ("declare
`SKILL_VALUE_KEYS`; run the assembly verification").

Practical shape: the harness needs the expected values machine-readable, so
each unit's test module exposes its fixture dicts at module level (they already
are, by convention: `TRANSFORM`, `ULTIMATE`, ... constants) and the harness
imports them via the manifest keys.

### 4. Roster loader

`backend/app/user_roster.py`: `load_nikke_spec(state: UserNikkeState) -> NikkeSpec | None`
(None = not loadable → excluded), plus `load_roster(states) -> (specs, excluded_slugs)`.

Per unit, from **local data files only** (no network at request time):

| NikkeSpec field | Source |
|---|---|
| `slug` | `state.character_slug` (signature variants are separate slugs already — `julia` vs `julia-signature`) |
| `burst_tier`, `element`, `weapon`, `burst_cooldown` | character data file (`data/lootandwaifus/char_<slug>.json`, dotgg fallback) |
| `base_stats` | `state.hp / atk / def_` |
| `skill_values` | parser (§2) at `levels[state.skill_levels.<skill> - 1]`, keyed via the manifest (§1); `caster_*` injection stays in `assemble_simulation_inputs` |
| `weapon_stats` | dotgg fields `damage`/`maxAmmo`/`reloadTime`/`chargeTime`/`chargeDamage` (`data/dotgg/char_<slug>.json`) |
| `overload_options`, `cube` | passthrough from `state` (existing converters in `roster.py` consume them) |

Excluded (with slug reported): not encoded; encoded but missing a manifest;
missing either data file (e.g. lootandwaifus-only units have no dotgg weapon
stats yet — excluded honestly until their stats are collected).

### 5. FastAPI endpoint

`backend/app/api.py` (+ uvicorn entry, e.g. `uvicorn app.api:app` from
`backend/`): `POST /api/recommend` per the contract in `frontend/README.md`:

- Request: `{roster: UserNikkeState[], boss: {element, core_hittable,
  enemy_def, fight_duration, part_destructible}, top_n?}` → `BossProfile`
  (`gauge_charge_time`/`mode` stay backend defaults).
- Assembly: `load_roster` → excluded list; remaining specs → `find_best_decks`.
- Response: `{"decks": [...], "excluded_slugs": [...]}` — decks exactly as the
  contract's `DeckRecommendation` (deck slugs in burst order, total/burst/
  normal damage; the raw `result` dict is NOT serialized).
- 422 (FastAPI default shape): malformed body, or the **usable** roster can't
  form any feasible deck (<5 units or a burst tier missing after exclusions) —
  detail message says so and names the exclusions.
- CORS: allow the Vite dev origin (`http://localhost:5173`) so the browser can
  call it during development.

### 6. Contract + frontend follow-up (separate, after the backend lands)

- `frontend/README.md`: add `excluded_slugs` to the response shape; flip the
  endpoint status from "not implemented" to implemented, with the uvicorn dev
  command.
- frontend-builder task: show excluded slugs in the results view ("not yet
  supported"), and document/enable the `VITE_RECOMMEND_API=live` switch.

## Testing strategy

- Parser unit tests (lootandwaifus text → slots; dotgg passthrough; override
  application).
- **Verification harness over all encoded units** (§3) — the load-bearing test.
- Loader tests: one real unit assembled end-to-end from the actual data files
  (values match its fixture; weapon_stats match the dotgg file), plus exclusion
  cases (non-encoded slug, missing data file).
- API tests (FastAPI TestClient): feasible roster → ranked decks +
  `excluded_slugs`; infeasible after exclusion → 422 naming exclusions;
  `part_destructible` flag reaches the sim (Ark Ranger deck: ceiling > floor).
- Full suite stays green.

## Out of scope

- Phase 5 (multi-deck allocation), auth/persistence, ShiftyPad scraping
  (Phase 7), collecting missing dotgg stats for lootandwaifus-only units
  (they exclude cleanly until collected).
