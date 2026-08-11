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

1. **Detect (live).** Run `python3 scripts/check_new_nikkes.py --dry-run` for a
   fresh directory fetch that lists new SSRs without toasting (read-only, needs no
   worktree). If none, stop: report "신규 없음" and end — before spending any setup.
2. **Isolate.** Only once there ARE new units: work in a dedicated worktree/branch
   and run `python scripts/sync_worktree_data.py` first (data/ is gitignored;
   measurements lie until synced).
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

For each approved unit, follow `nikke-skill-encoding` steps 5–14:
- module + tests + registry `_BUILDERS` entry + `frontend/src/lib/resourceIdSlugMap.ts`
  row + `SKILL_VALUE_MANIFESTS` (source `"shiftypad"`) + docstring
- portrait: `python scripts/download_portraits.py` (add a `SLUG_ALIASES` line if the
  lootandwaifus slug carries a `-nikke` suffix, then re-run)
- Korean name: one line in `backend/app/display_names.py`, copied from the snapshot's
  `name_ko` (step 3 refreshed it) — never transliterated. The failing
  `test_every_encoded_slug_is_named_in_korean` prints the official name.
- alias row: `'<slug>': [],  // <Korean name>` in
  `frontend/src/lib/nikkeAliases.ts`, aliases left empty for Fienn to fill.
  `backend/tests/test_nikke_aliases.py` fails until the row exists.
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
