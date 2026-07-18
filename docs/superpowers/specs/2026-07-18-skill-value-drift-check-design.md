# Skill-value drift check (dotgg-source manifests vs live lootandwaifus)

Date: 2026-07-18
Status: approved by Fienn (design presented in session, "그대로 진행해")

## Problem

`api.dotgg.gg` stopped updating around 2026-05, but 22 skill-value manifests
(21 units + drake-signature) still read their runtime skill values from
`data/dotgg/*.json` (`source: "dotgg"`). When any of those units receives a
balance patch, the dotgg file keeps loading without error and the simulation
silently uses pre-patch numbers. Proven on Scarlet: Black Shadow (2026-07
patch): dotgg L10 Skill 1 250.47/500/750.47% vs live lootandwaifus
283.03/565/848.03% (see docs/insights.md).

We need a detector that says WHICH dotgg-source units have drifted, so they
can be migrated to `source: "lootandwaifus"` in ROI order. This is step 1 of
the agreed staging: drift detection → per-unit source migration → (only then)
fold weapon stats into one file per unit.

## Decision drivers

- Drift is only meaningful against *current* lootandwaifus, so the script
  re-fetches by default (Fienn's explicit choice: "매 실행 시 전체 재수집").
- The pytest suite must NOT depend on the network or go red on a game patch;
  the suite covers the comparison logic only.
- 18 of the 22 targets have no local lootandwaifus JSON today; fetching as a
  side effect fills that coverage and feeds the future migration work.

## Deliverable

`scripts/check_skill_value_drift.py` (~150 lines) + unit tests (~100 lines,
`backend/tests/test_check_skill_value_drift.py`), following the
`collect_dotgg_weapons.py` structure: pure helpers + orchestration + `main`.

### Data flow

1. **Collect targets.** Import every module in `backend/app/skill_rules/`,
   merge their `SKILL_VALUE_MANIFESTS`, keep entries with
   `source == "dotgg"`. Target key = manifest slug; dotgg file resolved via
   `data_slug` (e.g. drake-signature → drake) through the existing
   url-field-indexed loader (`skill_values.load_character_data`).
2. **Refresh lootandwaifus.** For each target slug, fetch
   `lootandwaifus.com/character/<slug>-nikke/` with the browser-UA curl
   convention (same as data-sources reference), save to
   `data/lootandwaifus/char_<slug>.html`, then regenerate the JSON by
   reusing the parser from `scripts/lootandwaifus_html_to_json.py` as a
   module (no subprocess). `--offline` skips this step entirely and compares
   whatever is on disk (for logic testing / no-network runs).
3. **Compare.** For each manifest key `(array, index)` and each of the 10
   levels: parse the dotgg level's non-empty slot values as floats and check
   they are a sub-multiset (⊆) of the numeric tokens extracted from the
   lootandwaifus level text (same `\d+(?:\.\d+)?` token regex the engine
   uses). Extra lootandwaifus tokens are fine (trigger phrases, "1/2/3
   times"). Exception: dotgg slots whose value is exactly `"0"` are skipped —
   dotgg uses `"0"` as filler for unused slots (e.g. SBS Skill 2
   value_04).

### Output / exit code

- One line per manifest: `OK <slug>` or `DRIFT <slug>` followed by indented
  detail lines (skill array+index, level, dotgg value(s) missing from
  lootandwaifus).
- `WARN` lines (and continue) for: fetch/parse failure, lootandwaifus JSON
  missing the skill array (e.g. no `dollskills`), level-count mismatch.
- Summary line at the end: counts of OK / DRIFT / WARN.
- Exit 1 on DRIFT only; WARNs stay visible in output but do not change the
  exit code (no `--strict` flag — YAGNI).
- `--slug SLUG` to check a single manifest (spot checks after a patch).

### Testing

- Comparison helpers are pure functions tested with pytest (tmp_path +
  hand-built dotgg/lootandwaifus level structures): containment pass,
  drift detection, multiset semantics (duplicate values need duplicate
  tokens), the `"0"`-filler exception, missing-array WARN path.
- No network in tests. The fetch step is exercised via a fake fetcher
  callable injected into the orchestration function (same pattern as
  `collect_dotgg_weapons.py` tests).

## Out of scope

- Migrating any manifest to lootandwaifus source (next stage, per-unit).
- Comparing lootandwaifus-source units (lootandwaifus is the source of
  truth; nothing to compare against).
- Weapon-stat drift (lootandwaifus has no weapon stat numbers; patch notes
  are the only check — documented in docs/insights.md).
