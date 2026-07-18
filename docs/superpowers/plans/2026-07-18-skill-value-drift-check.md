# Skill-Value Drift Check Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A script that detects which dotgg-source skill-value manifests have drifted from current lootandwaifus data (= balance-patched units whose simulation silently uses stale numbers).

**Architecture:** One script `scripts/check_skill_value_drift.py` in the `collect_dotgg_weapons.py` mold — pure comparison helpers, an orchestration function with an injected fetcher, and a thin `main`. Pytest covers the pure logic and orchestration with fakes; the network path (curl) is exercised only by the real run.

**Tech Stack:** Python 3 (anaconda `python3`), pytest, curl (system), existing modules `scripts/lootandwaifus_html_to_json.py` (`parse_html`), `backend/app/skill_values.py` (`load_character_data`), `backend/app/skill_rules/registry.py` (`ENCODED_SLUGS`, `get_skill_value_manifest`).

Spec: `docs/superpowers/specs/2026-07-18-skill-value-drift-check-design.md`

## Global Constraints

- Token regex is exactly the engine's: `\d+(?:\.\d+)?`.
- Comparison is sub-multiset containment (⊆): every non-filler dotgg slot value must consume one matching lootandwaifus token; duplicates need duplicate tokens; extra lootandwaifus tokens are fine.
- dotgg slots valued `""` or exactly `"0"` are skipped (`"0"` is dotgg's unused-slot filler, e.g. SBS Skill 2 value_04).
- Fetch uses curl with this exact User-Agent (lootandwaifus 403s non-browser UAs): `Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36`; URL pattern `https://lootandwaifus.com/character/<slug>-nikke/`.
- Exit code 1 on any DRIFT, else 0. WARNs never change the exit code. No `--strict` flag.
- The pytest suite must not touch the network. `backend/pytest.ini` has `filterwarnings = error` — test output must be pristine.
- Both file loads key off `manifest.get("data_slug", slug)` (drake-signature → drake; the manifest's `(array, index)` keys then select `dollskills`).
- Run tests with anaconda `python3` (plain `python` has no pytest). PowerShell 5.1 has no `&&` — use the Bash tool or separate commands.
- This worktree's `data/` is a synced copy (gitignored). Data files produced by the real run are delivered by copying back to the main checkout at finish, never committed.

---

### Task 1: Pure comparison helpers

**Files:**
- Create: `scripts/check_skill_value_drift.py`
- Test: `backend/tests/test_check_skill_value_drift.py`

**Interfaces:**
- Produces: `NUMBER` (compiled regex), `USER_AGENT` (str), `LW_DIR`, `ROOT` (Paths), `dotgg_level_values(level_dict) -> list[str]`, `level_missing(level_dict, lw_text) -> list[str]` (dotgg raw strings unmatched in the text), `compare_unit(dotgg_data, lw_data, keys) -> tuple[dict, list[str]]` where the dict maps manifest key → `[(level_number_1based, [missing_raw_strings])]` and the list is warning strings. Task 2 builds on all of these.

- [ ] **Step 1: Write the failing tests**

Create `backend/tests/test_check_skill_value_drift.py`:

```python
"""Tests for scripts/check_skill_value_drift.py (pure comparison logic and
orchestration with fakes - the curl path is exercised only by real runs)."""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))

import check_skill_value_drift as drift


def _level(**slots):
    """dotgg level dict helper: _level(description_value_01="10", ...)"""
    return dict(slots)


def test_dotgg_level_values_skips_empty_and_zero_filler():
    level = _level(description_value_01="60", description_value_02="10",
                   description_value_03="0", description_value_04="")
    assert drift.dotgg_level_values(level) == ["60", "10"]


def test_level_missing_all_present_is_empty():
    level = _level(description_value_01="40", description_value_02="10")
    text = "Max Ammunition Capacity 40% for 10 sec."
    assert drift.level_missing(level, text) == []


def test_level_missing_reports_drifted_value():
    level = _level(description_value_01="250.47")
    text = "Deals 283.03% of final ATK as damage."
    assert drift.level_missing(level, text) == ["250.47"]


def test_level_missing_is_multiset():
    # two identical dotgg values need two tokens in the text
    level = _level(description_value_01="10", description_value_02="10")
    assert drift.level_missing(level, "lasts 10 sec") == ["10"]
    assert drift.level_missing(level, "10 sec, again 10 sec") == []


def test_level_missing_matches_numerically():
    # "500" matches the "500.00" token (float compare), extra tokens are fine
    level = _level(description_value_01="500")
    text = "Deals 500.00% of ATK as damage 3 times."
    assert drift.level_missing(level, text) == []


def _unit_data(values, array="skills", levels=10):
    """Build matching dotgg/lw structures: one skill whose every level
    carries the given slot values (dotgg) / a text containing them (lw)."""
    dotgg_levels = [{f"description_value_{i+1:02d}": v
                     for i, v in enumerate(values)} for _ in range(levels)]
    lw_levels = ["Effect " + " and ".join(f"{v}%" for v in values)
                 for _ in range(levels)]
    return ({array: [{"levels": dotgg_levels}]},
            {array: [{"levels": lw_levels}]})


def test_compare_unit_ok():
    dotgg_data, lw_data = _unit_data(["37.28", "5"])
    found, warnings = drift.compare_unit(dotgg_data, lw_data,
                                         {"s1": ("skills", 0)})
    assert found == {}
    assert warnings == []


def test_compare_unit_reports_drift_with_level_numbers():
    dotgg_data, lw_data = _unit_data(["37.28"])
    dotgg_data["skills"][0]["levels"][9]["description_value_01"] = "99.99"
    found, warnings = drift.compare_unit(dotgg_data, lw_data,
                                         {"s1": ("skills", 0)})
    assert found == {"s1": [(10, ["99.99"])]}
    assert warnings == []


def test_compare_unit_warns_on_missing_array():
    dotgg_data, _ = _unit_data(["10"], array="dollskills")
    found, warnings = drift.compare_unit(dotgg_data, {"skills": []},
                                         {"sig": ("dollskills", 0)})
    assert found == {}
    assert len(warnings) == 1 and "dollskills[0]" in warnings[0]


def test_compare_unit_warns_on_level_count_mismatch():
    dotgg_data, lw_data = _unit_data(["10"])
    lw_data["skills"][0]["levels"] = lw_data["skills"][0]["levels"][:7]
    found, warnings = drift.compare_unit(dotgg_data, lw_data,
                                         {"s1": ("skills", 0)})
    assert found == {}
    assert len(warnings) == 1 and "level count mismatch" in warnings[0]
```

- [ ] **Step 2: Run tests to verify they fail**

Run (Bash tool, repo root): `python3 -m pytest backend/tests/test_check_skill_value_drift.py -v`
Expected: FAIL at import — `ModuleNotFoundError: No module named 'check_skill_value_drift'`

- [ ] **Step 3: Write the helpers**

Create `scripts/check_skill_value_drift.py`:

```python
"""Detect balance-patch drift for dotgg-source skill-value manifests.

api.dotgg.gg stopped updating around 2026-05, but some encoded units still
read their runtime skill values from data/dotgg/*.json (manifest source
"dotgg"). When such a unit is balance-patched, the dotgg file keeps loading
without error and the simulation silently uses pre-patch numbers (proven on
Scarlet: Black Shadow, 2026-07 - see docs/insights.md). This script compares
every dotgg-source manifest's consumed skills, all levels, against
lootandwaifus data and reports which units drifted - those are the
migration candidates to source "lootandwaifus".

By default each target unit's lootandwaifus page is re-fetched first (browser
User-Agent curl, per the data-sources reference) so the comparison is against
the live site; the HTML and regenerated JSON land in data/lootandwaifus/ as a
useful side effect. --offline compares whatever is on disk.

Usage:
    python scripts/check_skill_value_drift.py               # fetch + compare all
    python scripts/check_skill_value_drift.py --offline     # local files only
    python scripts/check_skill_value_drift.py --slug mint   # one manifest

Output: one OK/DRIFT line per manifest (DRIFT details indented), WARN lines
for anything unverifiable, then a summary. Exit 1 if any DRIFT, else 0.
"""
import argparse
import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "scripts"))

from lootandwaifus_html_to_json import parse_html

LW_DIR = ROOT / "data" / "lootandwaifus"
# Same numeric-token regex the engine's extractor uses (skill_values.py).
NUMBER = re.compile(r"\d+(?:\.\d+)?")
USER_AGENT = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")


def dotgg_level_values(level_dict):
    """Numeric values a dotgg level actually carries: "" slots are unused and
    a literal "0" is dotgg's unused-slot filler too (e.g. Scarlet: Black
    Shadow Skill 2 value_04) - never a patched stat."""
    return [v for v in level_dict.values() if v not in ("", "0")]


def level_missing(level_dict, lw_text):
    """dotgg slot values (raw strings) with no matching numeric token left in
    the lootandwaifus level text. Multiset semantics: each match consumes its
    token, so duplicate values need duplicate tokens. Extra tokens are fine
    (trigger phrases, "1/2/3 times")."""
    available = Counter(float(t) for t in NUMBER.findall(lw_text))
    missing = []
    for value in dotgg_level_values(level_dict):
        number = float(value)
        if available[number] > 0:
            available[number] -= 1
        else:
            missing.append(value)
    return missing


def compare_unit(dotgg_data, lw_data, keys):
    """Compare every manifest-consumed (array, index) skill across all levels
    both sides have. Returns (drift, warnings): drift maps manifest key ->
    [(level_number_1based, [missing raw strings])]; warnings are strings for
    anything that couldn't be verified (missing array, level-count skew)."""
    drift = {}
    warnings = []
    for key, (array, index) in sorted(keys.items()):
        lw_skills = lw_data.get(array)
        if not lw_skills or index >= len(lw_skills):
            warnings.append(f"{key}: lootandwaifus data has no {array}[{index}]")
            continue
        dotgg_levels = dotgg_data[array][index]["levels"]
        lw_levels = lw_skills[index]["levels"]
        if len(dotgg_levels) != len(lw_levels):
            warnings.append(
                f"{key}: level count mismatch (dotgg {len(dotgg_levels)}, "
                f"lootandwaifus {len(lw_levels)})")
        findings = []
        for i in range(min(len(dotgg_levels), len(lw_levels))):
            missing = level_missing(dotgg_levels[i], lw_levels[i])
            if missing:
                findings.append((i + 1, missing))
        if findings:
            drift[key] = findings
    return drift, warnings
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest backend/tests/test_check_skill_value_drift.py -v`
Expected: 9 passed, output pristine.

- [ ] **Step 5: Commit**

```bash
git add scripts/check_skill_value_drift.py backend/tests/test_check_skill_value_drift.py
git commit -m "feat: drift-check comparison helpers (dotgg slots vs lootandwaifus tokens)"
```

---

### Task 2: Refresh + check orchestration (injected fetcher)

**Files:**
- Modify: `scripts/check_skill_value_drift.py` (append below `compare_unit`)
- Test: `backend/tests/test_check_skill_value_drift.py` (append)

**Interfaces:**
- Consumes: Task 1's `compare_unit`, `parse_html` (already imported).
- Produces: `refresh_lw(slugs, lw_dir, fetch_html) -> list[str]` (warning strings; writes `char_<slug>.html` + `.json` into lw_dir), `run_check(manifests, lw_dir, data_dir, fetch_html=None) -> tuple[dict, list[str]]` where the dict maps manifest slug → `{"status": "OK"|"DRIFT"|"WARN", "drift": <compare_unit dict>, "warnings": [str]}` and the list is refresh warnings. `data_dir` is the data ROOT (the directory containing `dotgg/`). Task 3's `main` calls `run_check`.

- [ ] **Step 1: Write the failing tests**

Append to `backend/tests/test_check_skill_value_drift.py`:

```python
def _lw_page(name="Testy", values=("10.5", "20", "30")):
    """Minimal HTML that parse_html reads warning-free: h1, character-info
    alts, 3 skill titles, 10 level paragraphs each."""
    info = ('<div id="character-info"><img alt="Fire"><img alt="AR">'
            '<img alt="Attacker"><img alt="Burst 3"></div>')
    blocks = []
    for i, v in enumerate(values):
        levels = "".join(
            f'<p class="level-description" data-level="{n}">'
            f"ATK up {v}% for 5 sec.</p>" for n in range(10))
        blocks.append(f'<div class="skill-title-section"><h3>Skill {i}'
                      f"</h3></div>{levels}")
    return f"<h1>{name}</h1>{info}<div id=\"skills\">{''.join(blocks)}</div>"


def test_refresh_lw_writes_html_and_json(tmp_path):
    warnings = drift.refresh_lw(["testy"], tmp_path,
                                lambda slug: _lw_page(name="Testy"))
    assert warnings == []
    assert (tmp_path / "char_testy.html").exists()
    data = json.loads((tmp_path / "char_testy.json").read_text(encoding="utf-8"))
    assert data["name"] == "Testy" and data["source"] == "lootandwaifus"
    assert len(data["skills"][0]["levels"]) == 10


def test_refresh_lw_fetch_failure_is_warning_not_crash(tmp_path):
    def boom(slug):
        raise RuntimeError("curl failed")
    warnings = drift.refresh_lw(["testy"], tmp_path, boom)
    assert len(warnings) == 1 and "testy" in warnings[0]
    assert not (tmp_path / "char_testy.json").exists()


def _data_root(tmp_path, dotgg_values, lw_values):
    """data root with dotgg/char_x.json (url-field indexed) and
    lootandwaifus/char_x.json for slug "x"."""
    (tmp_path / "dotgg").mkdir()
    (tmp_path / "lootandwaifus").mkdir()
    dotgg_data, _ = _unit_data(dotgg_values)
    dotgg_data["url"] = "x"
    _, lw_data = _unit_data(lw_values)
    (tmp_path / "dotgg" / "char_x.json").write_text(
        json.dumps(dotgg_data), encoding="utf-8")
    (tmp_path / "lootandwaifus" / "char_x.json").write_text(
        json.dumps(lw_data), encoding="utf-8")
    return tmp_path


MANIFEST = {"x": {"source": "dotgg", "keys": {"s1": ("skills", 0)}}}


def test_run_check_ok_and_drift(tmp_path):
    root = _data_root(tmp_path, ["37.28"], ["37.28"])
    results, refresh_warnings = drift.run_check(
        MANIFEST, root / "lootandwaifus", root)
    assert refresh_warnings == []
    assert results["x"]["status"] == "OK"

    drifted = _data_root(tmp_path / "b", ["37.28"], ["99.99"])
    results, _ = drift.run_check(MANIFEST, drifted / "lootandwaifus", drifted)
    assert results["x"]["status"] == "DRIFT"
    assert results["x"]["drift"]["s1"][0][1] == ["37.28"]


def test_run_check_missing_lw_json_is_warn(tmp_path):
    root = _data_root(tmp_path, ["1"], ["1"])
    (root / "lootandwaifus" / "char_x.json").unlink()
    results, _ = drift.run_check(MANIFEST, root / "lootandwaifus", root)
    assert results["x"]["status"] == "WARN"
    assert "char_x.json" in results["x"]["warnings"][0]


def test_run_check_refreshes_before_comparing(tmp_path):
    root = _data_root(tmp_path, ["10.5"], ["99.99"])  # stale lw says 99.99
    results, refresh_warnings = drift.run_check(
        MANIFEST, root / "lootandwaifus", root,
        fetch_html=lambda slug: _lw_page(values=("10.5", "2", "3")))
    assert refresh_warnings == []
    assert results["x"]["status"] == "OK"  # fresh fetch wins over stale file
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python3 -m pytest backend/tests/test_check_skill_value_drift.py -v`
Expected: Task 1 tests pass; new ones FAIL with `AttributeError: ... no attribute 'refresh_lw'`.

- [ ] **Step 3: Implement refresh_lw and run_check**

Append to `scripts/check_skill_value_drift.py`:

```python
def refresh_lw(slugs, lw_dir, fetch_html):
    """Re-fetch + re-parse lootandwaifus pages for the given slugs, writing
    char_<slug>.html and char_<slug>.json into lw_dir (same layout the
    collect workflow uses). A failed slug becomes a warning and is skipped -
    its stale local files, if any, are left untouched. Returns warnings."""
    lw_dir = Path(lw_dir)
    warnings = []
    for slug in sorted(set(slugs)):
        try:
            raw = fetch_html(slug)
        except Exception as exc:
            warnings.append(f"{slug}: fetch failed: {exc}")
            continue
        data, parse_warnings = parse_html(raw, slug)
        warnings.extend(f"{slug}: {w}" for w in parse_warnings)
        (lw_dir / f"char_{slug}.html").write_text(raw, encoding="utf-8")
        (lw_dir / f"char_{slug}.json").write_text(
            json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return warnings


def run_check(manifests, lw_dir, data_dir, fetch_html=None):
    """Compare each dotgg-source manifest against lootandwaifus data.
    manifests: {slug: manifest}, pre-filtered to source == "dotgg".
    data_dir: the data ROOT (contains dotgg/). If fetch_html is given, the
    target lootandwaifus pages are refreshed first. Returns
    ({slug: {"status", "drift", "warnings"}}, refresh_warnings)."""
    from app.skill_values import load_character_data

    lw_dir = Path(lw_dir)
    refresh_warnings = []
    if fetch_html is not None:
        slugs = {m.get("data_slug", slug) for slug, m in manifests.items()}
        refresh_warnings = refresh_lw(slugs, lw_dir, fetch_html)

    results = {}
    for slug, manifest in sorted(manifests.items()):
        data_slug = manifest.get("data_slug", slug)
        lw_path = lw_dir / f"char_{data_slug}.json"
        if not lw_path.exists():
            results[slug] = {"status": "WARN", "drift": {}, "warnings": [
                f"no lootandwaifus JSON (char_{data_slug}.json)"]}
            continue
        dotgg_data = load_character_data("dotgg", data_slug, data_dir)
        lw_data = json.loads(lw_path.read_text(encoding="utf-8"))
        drift, warnings = compare_unit(dotgg_data, lw_data, manifest["keys"])
        status = "DRIFT" if drift else ("WARN" if warnings else "OK")
        results[slug] = {"status": status, "drift": drift,
                         "warnings": warnings}
    return results, refresh_warnings
```

Note: `run_check` shadows the module-level name `drift` nowhere — the local
variable in the loop is fine, but do NOT rename the module import in tests.

- [ ] **Step 4: Run tests to verify they pass**

Run: `python3 -m pytest backend/tests/test_check_skill_value_drift.py -v`
Expected: 14 passed, output pristine.

- [ ] **Step 5: Commit**

```bash
git add scripts/check_skill_value_drift.py backend/tests/test_check_skill_value_drift.py
git commit -m "feat: drift-check orchestration - refresh lootandwaifus then compare"
```

---

### Task 3: CLI, live run, full suite

**Files:**
- Modify: `scripts/check_skill_value_drift.py` (append `curl_fetch` and `main`)

**Interfaces:**
- Consumes: Task 2's `run_check`; registry's `ENCODED_SLUGS` / `get_skill_value_manifest` (same pattern as `collect_dotgg_weapons.main`).
- Produces: the CLI. No later task depends on it.

- [ ] **Step 1: Implement curl_fetch and main**

Append to `scripts/check_skill_value_drift.py`:

```python
def curl_fetch(slug):
    """Fetch a character page with the browser-UA curl convention the
    data-sources reference documents (lootandwaifus 403s non-browser UAs)."""
    url = f"https://lootandwaifus.com/character/{slug}-nikke/"
    result = subprocess.run(
        ["curl", "-s", "-L", "--max-time", "60", "-A", USER_AGENT, url],
        capture_output=True, text=True, encoding="utf-8")
    if result.returncode != 0 or not result.stdout:
        raise RuntimeError(f"curl exit {result.returncode} for {url}")
    return result.stdout


def main(argv=None):
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--offline", action="store_true",
                        help="skip re-fetching; compare local files only")
    parser.add_argument("--slug", help="check a single manifest slug")
    args = parser.parse_args(argv)

    from app.skill_rules.registry import ENCODED_SLUGS, get_skill_value_manifest

    manifests = {}
    for slug in sorted(ENCODED_SLUGS):
        manifest = get_skill_value_manifest(slug)
        if manifest is not None and manifest["source"] == "dotgg":
            manifests[slug] = manifest
    if args.slug:
        if args.slug not in manifests:
            parser.error(f"{args.slug!r} is not a dotgg-source manifest slug; "
                         f"candidates: {', '.join(sorted(manifests))}")
        manifests = {args.slug: manifests[args.slug]}

    results, refresh_warnings = run_check(
        manifests, LW_DIR, ROOT / "data",
        fetch_html=None if args.offline else curl_fetch)

    for message in refresh_warnings:
        print(f"WARN {message}")
    counts = Counter(r["status"] for r in results.values())
    for slug, result in sorted(results.items()):
        print(f"{result['status']} {slug}")
        for key, findings in sorted(result["drift"].items()):
            for level, missing in findings:
                print(f"  {key} Lv{level}: dotgg {', '.join(missing)} "
                      f"not in lootandwaifus")
        for message in result["warnings"]:
            print(f"  WARN {message}")
    print(f"\n{counts['OK']} OK, {counts['DRIFT']} DRIFT, {counts['WARN']} "
          f"WARN of {len(results)} dotgg-source manifest(s)")
    return 1 if counts["DRIFT"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
```

- [ ] **Step 2: Offline smoke run**

Run: `python3 scripts/check_skill_value_drift.py --offline`
Expected: 22 manifests listed — 5 compared (brid-silent-track, drake, little-mermaid, mint have local lootandwaifus JSON; drake-signature reads char_drake.json too) and 17 `WARN ... no lootandwaifus JSON` lines. Exit code reflects whether the compared ones drifted — either is acceptable here; the point is the plumbing works. If the manifest count is NOT 22, stop and investigate the registry filter before continuing.

- [ ] **Step 3: Live run (network)**

Run: `python3 scripts/check_skill_value_drift.py`
Expected: no missing-JSON WARNs (all 22 pages fetched), a real OK/DRIFT verdict per manifest. Save the full output — it is the deliverable answer ("which units drifted"). Investigate any fetch-failure or parse WARN (site markup change?) before trusting the verdicts.

- [ ] **Step 4: Full suite**

Run (Bash tool, repo root): `cd backend && python3 -m pytest -q`
Expected: everything passes (708+ tests), pristine output.

- [ ] **Step 5: Commit**

```bash
git add scripts/check_skill_value_drift.py
git commit -m "feat: drift-check CLI - fetch live lootandwaifus and report per-manifest verdicts"
```

---

### Finishing (superpowers:finishing-a-development-branch)

- Copy the refreshed `data/lootandwaifus/char_*.html` / `char_*.json` produced by the live run back to the main checkout's `data/lootandwaifus/` (gitignored — delivered by copy, never committed).
- Update `docs/roadmap.md` (drift-check landed) and `docs/engine-gaps.md` only if the drift results change priorities; record the drift findings in the session report either way.
- Merge to `wip/scaffolding` (local-only, no remote).
