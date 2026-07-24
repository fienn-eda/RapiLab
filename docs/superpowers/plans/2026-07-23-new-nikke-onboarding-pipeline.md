# New-NIKKE Onboarding Pipeline Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a single `/onboard-new-nikkes` skill that orchestrates the existing detection, collection, and encoding pieces into one flow with a single human gate at plan approval.

**Architecture:** The deliverable is a markdown orchestration procedure (`.claude/skills/onboard-new-nikkes/SKILL.md`) plus two pointer edits so the daily toast and the ops guide name the new command. The skill sequences existing tools (`check_new_nikkes.py`, `collect.js`, `normalize_shiftypad_raw.py`, `download_portraits.py`) and delegates all encoding methodology to the `nikke-skill-encoding` skill — it contains no encoding logic of its own. There is no new runtime code, so verification is reference-integrity (every command/flag the skill names exists) plus the untouched detection test suite.

**Tech Stack:** Markdown skill authoring; existing Python/Node scripts; git worktrees for isolation.

## Global Constraints

- The skill is an ORCHESTRATOR only — encoding "how" stays in `nikke-skill-encoding`; this skill owns "what, when, in what order" and the failure/merge policy.
- Exactly ONE human gate: encoding-plan approval. Plan approval is the FINAL approval and authorizes the merge.
- Phase 2 merges into `wip/scaffolding` only on a pristine full test suite; never merge a failing state.
- Design spec: `docs/superpowers/specs/2026-07-23-new-nikke-onboarding-pipeline-design.md`.
- Windows: pytest runs under the anaconda interpreter (`C:/Users/Fienn/anaconda3/python3.exe`), prefixed with `PYTHONIOENCODING=utf-8`. The bare `python` (C:\Python314) has no pytest.

---

### Task 1: Create the `onboard-new-nikkes` orchestrator skill

**Files:**
- Create: `.claude/skills/onboard-new-nikkes/SKILL.md`

**Interfaces:**
- Consumes (must already exist, verified in Step 2): `scripts/check_new_nikkes.py` (`--dry-run`), `tools/collect-blablalink/collect.js` (`--nikke`, `--directory`, `--headless`, `--deep`), `scripts/normalize_shiftypad_raw.py`, `scripts/download_portraits.py` (`SLUG_ALIASES`), the `nikke-skill-encoding` skill.
- Produces: a user-invocable skill `/onboard-new-nikkes` (no code interface; a procedure other agents follow).

- [ ] **Step 1: Verify every tool the skill will reference actually exists (pre-check)**

Run:
```bash
cd C:/Users/fienn/Desktop/NikkeDeckBuilder/.claude/worktrees/plans-frontend3-encoding
ls scripts/check_new_nikkes.py scripts/normalize_shiftypad_raw.py scripts/download_portraits.py tools/collect-blablalink/collect.js .claude/skills/nikke-skill-encoding/SKILL.md
grep -c -- '--nikke' tools/collect-blablalink/collect.js
grep -c 'SLUG_ALIASES' scripts/download_portraits.py
grep -c -- '--dry-run' scripts/check_new_nikkes.py
```
Expected: all five paths listed (no "No such file"), and each `grep -c` prints a non-zero count.

- [ ] **Step 2: Write the skill file**

Create `.claude/skills/onboard-new-nikkes/SKILL.md` with exactly this content:

```markdown
---
name: onboard-new-nikkes
description: Onboard newly released NIKKEs end-to-end — detect, collect data, encode, and land them in the deck recommender. Use when the daily "신규 니케 감지" toast fires, when the user says "onboard the new nikke(s)" / "새 니케 온보딩/추가", or wants the new-release pipeline run. Orchestrates detection + ShiftyPad/lootandwaifus collection + the nikke-skill-encoding skill + portrait + docs + merge, with one human gate at plan approval.
---

# Onboarding newly released NIKKEs (detection → recommendation)

This skill is an ORCHESTRATOR. It sequences existing pieces into one flow and
holds NO encoding methodology — the `nikke-skill-encoding` skill is the authority
for classifying effects and writing modules. Design spec:
`docs/superpowers/specs/2026-07-23-new-nikke-onboarding-pipeline-design.md`.

The flow has ONE human gate: the encoding-plan approval. Everything before it
(collect + draft plan) and everything after it (implement + test + docs + merge)
is automatic. Plan approval is the FINAL approval — it authorizes the merge.

## Phase 1 — auto (detect → collect → draft plan)

1. **Isolate.** Work in a dedicated worktree/branch. Run
   `python scripts/sync_worktree_data.py` first (data/ is gitignored; measurements
   lie until synced).
2. **Detect (live).** Run `python3 scripts/check_new_nikkes.py --dry-run` for a
   fresh directory fetch that lists new SSRs without toasting. If none, stop:
   report "신규 없음" and end.
3. **Refresh the committed snapshot** (the resource_id-map guard needs the new
   units in it): `cd tools/collect-blablalink && node collect.js --directory
   --headless --deep`.
4. **Collect each new unit's data:**
   - Non-signature (default): `node collect.js --nikke <rid> --headless` (public
     data, no login — it bundles playwright-core), then
     `python scripts/normalize_shiftypad_raw.py <rid>:<slug>` →
     `data/shiftypad/<slug>.json`.
   - Effect text + portrait: fetch the lootandwaifus character page with `curl` and
     a browser User-Agent (WebFetch gets HTTP 403). If the page doesn't exist yet,
     leave the portrait to the chip fallback and note it.
5. **Draft the encoding plan.** Follow `nikke-skill-encoding` steps 3–4: classify
   every effect (model / approximate / defer / skip) for ALL detected units in ONE
   batch plan. Flag any signature-build (`skills` vs `dollskills`) choice and any
   unit that will be a thin stub.
6. **Present the plan and STOP for approval.**

## Gate — human (the only touch-point)

Fienn approves or corrects the batch plan. This is the FINAL approval and
authorizes the Phase 2 merge.

## Phase 2 — auto (implement → verify → merge)

For each approved unit, follow `nikke-skill-encoding` steps 5–12:
- module + tests + registry `_BUILDERS` entry + `frontend/src/lib/resourceIdSlugMap.ts`
  row + `SKILL_VALUE_MANIFESTS` (source `"shiftypad"`) + docstring
- portrait: `python scripts/download_portraits.py` (add a `SLUG_ALIASES` line if the
  lootandwaifus slug carries a `-nikke` suffix, then re-run)
- docs: `docs/encoded-nikkes.md` row + Burst count + 갱신 노트; if a thin stub,
  register the gap in `docs/engine-gaps.md`
- commit the refreshed directory snapshot

Then:
- Run the full suite from `backend/`:
  `PYTHONIOENCODING=utf-8 python -m pytest tests/ -q` (use the anaconda python that
  has pytest). It MUST be pristine.
- On ANY failure or merge conflict: STOP, keep the branch, report. NEVER merge a
  failing state.
- On green: confirm the main checkout is clean, then fast-forward merge the branch
  into `wip/scaffolding` with `git -C <main-checkout> merge --ff-only <branch>`
  (keep cwd in the worktree). The refreshed snapshot lands in the main checkout →
  the daily "신규 니케 감지" toast stops. registry registration makes `deck_search`
  include the unit immediately (recommendation surface done).

## Failure / edge defaults

- Collection failure (collect.js / network / normalize): stop in Phase 1, report,
  commit nothing partial.
- lootandwaifus page missing: portrait → chip fallback; encode from ShiftyPad values.
- Phase 2 test failure / merge conflict: stop, preserve the branch, report — never merge.
- Multiple units at once: one plan, one approval, batched (like the 2026-07-23
  Maxwell + Laplace onboarding).
- Idempotent: already-encoded slugs (registry `ENCODED_SLUGS`) are skipped —
  detection only counts "in the directory but not encoded" as new.
```

- [ ] **Step 3: Verify the skill file is well-formed and reference-clean**

Run:
```bash
cd C:/Users/fienn/Desktop/NikkeDeckBuilder/.claude/worktrees/plans-frontend3-encoding
head -3 .claude/skills/onboard-new-nikkes/SKILL.md
grep -nE 'check_new_nikkes|collect\.js|normalize_shiftypad_raw|download_portraits|nikke-skill-encoding' .claude/skills/onboard-new-nikkes/SKILL.md
```
Expected: the frontmatter opens with `---` then `name: onboard-new-nikkes`; the grep lists the referenced tools (all names match real files verified in Step 1).

- [ ] **Step 4: Commit**

```bash
cd C:/Users/fienn/Desktop/NikkeDeckBuilder/.claude/worktrees/plans-frontend3-encoding
git add .claude/skills/onboard-new-nikkes/SKILL.md
git commit -m "Add onboard-new-nikkes orchestrator skill"
```

---

### Task 2: Point the toast and ops guide at the new command

**Files:**
- Modify: `scripts/check_new_nikkes.py:127-130` (the onboarding-guidance print)
- Modify: `docs/new-nikke-detection.md` (the "온보딩" section lead)

**Interfaces:**
- Consumes: the `/onboard-new-nikkes` skill from Task 1.
- Produces: nothing code-facing; updates the human-facing pointers.

- [ ] **Step 1: Update the check script's onboarding guidance**

In `scripts/check_new_nikkes.py`, replace the print block at lines 127-130:

```python
    print("\nOnboarding: refresh the snapshot with\n"
          "  cd tools/collect-blablalink && node collect.js --directory --headless --deep\n"
          "then /collect-nikke <name>, encode with the nikke-skill-encoding skill\n"
          "(test_resource_id_slug_map.py will force the slug-map entry).")
```

with:

```python
    print("\nOnboarding: run the /onboard-new-nikkes skill — it collects, drafts an\n"
          "encoding plan for your approval, then implements/tests/docs/merges the\n"
          "approved units (the only manual step is approving the plan).")
```

- [ ] **Step 2: Verify the detection tests still pass (text change is inert to logic)**

Run:
```bash
cd C:/Users/fienn/Desktop/NikkeDeckBuilder/.claude/worktrees/plans-frontend3-encoding/backend
PYTHONIOENCODING=utf-8 "C:/Users/Fienn/anaconda3/python3.exe" -m pytest ../scripts -q -k "new_nikke" 2>&1 | tail -5 || echo "no scripts tests dir; running detection-named tests"
PYTHONIOENCODING=utf-8 "C:/Users/Fienn/anaconda3/python3.exe" -m pytest tests/ -q -k "new_nikke or detection" 2>&1 | tail -5
```
Expected: any matched tests pass (or "no tests ran" if the detection tests live elsewhere — a print-string change cannot break comparison logic). If detection tests exist and fail, STOP and investigate before continuing.

- [ ] **Step 3: Update the ops guide's onboarding section lead**

In `docs/new-nikke-detection.md`, find the section header line:

```
## "신규 니케 감지" 토스트가 떴을 때 — 온보딩
```

Insert immediately after it (before the existing "토스트 본문에 새 SSR 이름이 실린다" paragraph) this lead:

```
**한 줄 실행:** 토스트가 뜨면 `/onboard-new-nikkes` 스킬을 한 번 실행한다 — 감지·수집·
인코딩 플랜 초안까지 자동으로 만들어 승인을 기다리고, 승인하면 구현·테스트·문서·머지까지
자동으로 마무리한다(유일한 수동 단계는 플랜 승인). 설계는
`docs/superpowers/specs/2026-07-23-new-nikke-onboarding-pipeline-design.md`. 아래는 그
스킬이 내부적으로 밟는 단계이자, 손으로 할 때의 참고 절차다.
```

- [ ] **Step 4: Verify the edits landed**

Run:
```bash
cd C:/Users/fienn/Desktop/NikkeDeckBuilder/.claude/worktrees/plans-frontend3-encoding
grep -n 'onboard-new-nikkes' scripts/check_new_nikkes.py docs/new-nikke-detection.md
```
Expected: at least one match in each file.

- [ ] **Step 5: Commit**

```bash
cd C:/Users/fienn/Desktop/NikkeDeckBuilder/.claude/worktrees/plans-frontend3-encoding
git add scripts/check_new_nikkes.py docs/new-nikke-detection.md
git commit -m "Point new-nikke toast + ops guide at /onboard-new-nikkes"
```

---

## Self-Review

**Spec coverage:**
- 형태 (single `/onboard-new-nikkes` skill orchestrator) → Task 1. ✅
- 국면 1 / 게이트 / 국면 2 procedure → Task 1 skill body. ✅
- 실패·엣지 defaults → Task 1 skill body ("Failure / edge defaults"). ✅
- 재사용 vs 신규 (reuse scripts + nikke-skill-encoding; new skill + toast text) → Task 1 (skill) + Task 2 (toast/doc). ✅
- 토스트 문구 한 줄 갱신 → Task 2 Step 1. ✅
- 온보딩 운영 가이드 반영 (`docs/new-nikke-detection.md`) → Task 2 Step 3. ✅
- 테스트 전략 (procedure not unit-tested; verify via reference-integrity + untouched detection suite) → Task 1 Steps 1/3, Task 2 Step 2. ✅

**Placeholder scan:** No TBD/TODO; the skill file content is given in full; all commands are concrete. ✅

**Type consistency:** No code types introduced. Tool/flag names used in the skill (`--nikke`, `--directory`, `--headless`, `--deep`, `--dry-run`, `SLUG_ALIASES`, `ENCODED_SLUGS`) all match names verified in Task 1 Step 1 / present in the codebase. ✅
