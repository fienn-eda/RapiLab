# 동기화 후속 다듬기 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stop the bookmarklet from stacking a new tab on every re-sync, and show each imported unit's breakthrough/core investment instead of a hardcoded zero.

**Architecture:** Two independent changes sharing one screen. The first adds a window name to the bookmarklet's `window.open`. The second threads `grade`/`core` from the sync payload — which the backend already reads but never emitted — into an optional pair of draft fields rendered as a read-only badge, and removes the `core_level` input that the backend reads nowhere.

**Tech Stack:** React 19 / Vite / TypeScript / Vitest (frontend), Python 3 / FastAPI / pytest (backend).

## Global Constraints

- Work only in the worktree `C:\Users\fienn\Desktop\NikkeDeckBuilder\.claude\worktrees\plans-frontend3-encoding`. Do NOT `cd` to the original repository root.
- Branch: `wip/sync-polish` (already created, already carries the spec).
- Backend tests: `PYTHONPATH=. python3 -m pytest` from `backend/`. Plain `python` on this machine has NO pytest.
- Frontend checks from `frontend/`: `npx vitest run`, `npx tsc -b --noEmit`, `npm run lint`. Bare `tsc --noEmit` is a **no-op** here — the root tsconfig is a references shell, so `-b` is required.
- **Baseline: backend 1015 passing, frontend 155 passing.** Nothing may break.
- Never use bare `git stash` / `git stash pop` — the stash stack is shared with other worktrees.
- UI copy is **English** (`App.tsx`: "Enter each owned Nikke's investment data from ShiftyPad."). Test descriptions in `frontend/src/lib/bookmarklet.test.ts` are **Korean** — match whichever file you are in.
- The window name is exactly `nikke-deck-builder`.
- Badge rendering: 3 star slots, filled count = `grade`; `+N` only when `core > 0`; **render nothing at all when `grade` is absent**. Absent must never be coerced to 0 — that would claim "zero breakthrough" about a unit we have no data for.
- Game rule (confirmed, Fienn 2026-07-20): core enhancement only begins after 3 breakthroughs, so `core > 0` implies `grade == 3`. The badge does **not** enforce this — it renders `+N` whenever `core > 0` regardless of grade, because the branchless version is shorter and does not hide data that violates the rule.

---

### Task 1: Reuse the app tab instead of stacking a new one

**Files:**
- Modify: `frontend/src/lib/bookmarklet.ts:43`
- Test: `frontend/src/lib/bookmarklet.test.ts` (append inside the existing `describe('buildBookmarklet', ...)`)

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces: no new names. The generated bookmarklet source now calls `window.open` with a second argument.

- [ ] **Step 1: Write the failing test**

Append inside the existing `describe('buildBookmarklet', ...)` block in `frontend/src/lib/bookmarklet.test.ts`. The file already defines `code` and `source` at module scope (`source` is the decoded body — assert against `source`, never `code`, because `encodeURIComponent` mangles `://`). Test descriptions in this file are Korean; match that.

```ts
  it('window.open에 창 이름을 줘 재동기화 때 기존 탭을 재사용한다', () => {
    // 이름 없는 window.open은 매번 새 탭을 연다. 같은 이름을 주면 브라우저가
    // 그 탭을 재사용한다(재사용은 새로고침을 일으키지만 draft는 매 변경마다
    // localStorage에 저장되므로 잃는 것이 없다 - useRoster.ts 참고).
    const openCall = source.slice(
      source.indexOf('window.open('),
      source.indexOf('window.open(') + 80,
    )
    expect(openCall).toContain("'nikke-deck-builder'")
  })
```

- [ ] **Step 2: Run test to verify it fails**

Run from `frontend/`:
```
npx vitest run src/lib/bookmarklet.test.ts
```
Expected: FAIL — the assertion reports the `window.open('https://deck.example')` call with no second argument.

- [ ] **Step 3: Write the implementation**

In `frontend/src/lib/bookmarklet.ts`, line 43 currently reads:

```
const w=window.open('${appOrigin}');
```

Change it to:

```
const w=window.open('${appOrigin}','nikke-deck-builder');
```

Note this line lives inside a template literal that becomes the bookmarklet body — keep it on one line and do not add spaces around the comma (the source is minified into a `javascript:` URL).

- [ ] **Step 4: Run the frontend suite**

Run from `frontend/`:
```
npx vitest run
```
Expected: 156 passed. The existing popup-blocking test (`window.open은 첫 await/fetch보다 먼저...`) must still pass — it locates the call with `source.indexOf('window.open(')`, which the added argument does not move.

- [ ] **Step 5: Commit**

```bash
git add frontend/src/lib/bookmarklet.ts frontend/src/lib/bookmarklet.test.ts
git commit -m "Reuse the app tab on re-sync by naming the opened window"
```

---

### Task 2: Emit grade and core from the sync assembly

`assemble_unit` already reads both — `extract_inputs` pulls `detail["grade"]` and `detail["core"]` at lines 42-43 to compute ATK/HP — but the returned dict carries only `name_en` / `resource_id` / `raid400` / `skill_levels` / `overload`. That is why `rosterImport.ts` hardcodes `core_level: '0'`: the frontend has no value to show.

**Files:**
- Modify: `backend/app/roster_assembly.py` (`assemble_unit`'s return)
- Test: `backend/tests/test_roster_assembly.py` (modify the existing key-set assertion, add one test)

**Interfaces:**
- Consumes: nothing from earlier tasks.
- Produces: `assemble_unit(...)` (and therefore `assemble_roster` / `to_roster_json` / `POST /api/assemble-roster`) now emits two more integer keys: `"grade"` and `"core"`. Task 3 consumes them.

- [ ] **Step 1: Write the failing test**

In `backend/tests/test_roster_assembly.py`, the existing `test_fetch_then_assemble_end_to_end` asserts the exact key set:

```python
    assert set(u) == {"name_en", "resource_id", "raid400", "skill_levels", "overload"}
```

Update it to include the new keys (this is a widening, not a weakening — the assertion still pins the exact set):

```python
    assert set(u) == {"name_en", "resource_id", "raid400", "skill_levels",
                      "overload", "grade", "core"}
```

Then append a test that the values are the real ones, not placeholders. It reuses the file's existing `tables` fixture and `DIRECTORY` constant:

```python
def test_assembled_units_carry_the_breakthrough_and_core_they_were_built_from(tables):
    # grade/core are inputs to the ATK/HP calculation and are not consumed by
    # the simulation, but the UI shows them so the user can confirm their
    # roster imported correctly. Emitting a placeholder would defeat that.
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
    u = assemble_roster(tables, directory, raw)[0]
    assert u["grade"] == 3
    assert u["core"] == 6
```

- [ ] **Step 2: Run tests to verify they fail**

Run from `backend/`:
```
PYTHONPATH=. python3 -m pytest tests/test_roster_assembly.py -v
```
Expected: both fail — the key-set assertion reports the two missing keys, and the new test raises `KeyError: 'grade'`.

- [ ] **Step 3: Write the implementation**

In `backend/app/roster_assembly.py`, `assemble_unit`'s return dict gains two entries. Place them right after `resource_id` so identity fields stay together:

```python
    return {
        "name_en": inp["name_en"],
        "resource_id": inp["resource_id"],
        # Not consumed by the simulation - already folded into raid400 - but the
        # UI shows them so the user can confirm their roster imported correctly.
        "grade": inp["grade"],
        "core": inp["core"],
        "raid400": {"hp": round(hp), "atk": round(atk), "def": 0},
        "skill_levels": {
            "skill1": inp["skill1_lv"],
            "skill2": inp["skill2_lv"],
            "burst": inp["ulti_skill_lv"],
        },
        "overload": assemble_overload(tables, detail),
    }
```

- [ ] **Step 4: Run the full backend suite**

Run from `backend/`:
```
PYTHONPATH=. python3 -m pytest -q
```
Expected: **1016 passed** (1015 baseline + 1 new; the key-set test was modified, not added). If `test_assemble_roster_matches_the_collector_scrape` fails, do NOT widen it — it compares against a real scrape and a failure there means the emitted values are wrong, not the test.

- [ ] **Step 5: Commit**

```bash
git add backend/app/roster_assembly.py backend/tests/test_roster_assembly.py
git commit -m "Emit grade and core so the roster UI can show real investment"
```

---

### Task 3: Show the investment badge

**Files:**
- Create: `frontend/src/components/InvestmentBadge.tsx`
- Create: `frontend/src/components/InvestmentBadge.test.tsx`
- Modify: `frontend/src/types/nikkeDraft.ts` (add two optional draft fields)
- Modify: `frontend/src/lib/rosterImport.ts` (map the new payload keys)
- Modify: `frontend/src/lib/rosterImport.test.ts` (add coverage)
- Modify: `frontend/src/components/NikkeCard.tsx` (render the badge in the header)
- Modify: `frontend/src/App.css` (badge styles)

**Interfaces:**
- Consumes: Task 2's `grade` / `core` integer keys on each unit of the roster payload.
- Produces:
  - `NikkeDraft` gains `grade?: number` and `core?: number` — **optional**, absent for manually created drafts.
  - `InvestmentBadge({ grade, core }: { grade?: number; core?: number })` — returns `null` when `grade` is `undefined`.

- [ ] **Step 1: Write the failing badge tests**

Create `frontend/src/components/InvestmentBadge.test.tsx`. Follow the import style of the existing component tests (see `frontend/src/components/RecommendPanel.test.tsx`).

```tsx
import { describe, it, expect } from 'vitest'
import { render, screen } from '@testing-library/react'
import { InvestmentBadge } from './InvestmentBadge'

describe('InvestmentBadge', () => {
  it('fills one star per breakthrough and appends the core count', () => {
    render(<InvestmentBadge grade={3} core={7} />)
    expect(screen.getByText('★★★')).toBeInTheDocument()
    expect(screen.getByText('+7')).toBeInTheDocument()
  })

  it('omits the core count when core is zero', () => {
    render(<InvestmentBadge grade={3} core={0} />)
    expect(screen.getByText('★★★')).toBeInTheDocument()
    expect(screen.queryByText(/^\+/)).toBeNull()
  })

  it('shows empty stars for a partially broken-through unit', () => {
    render(<InvestmentBadge grade={2} core={0} />)
    expect(screen.getByText('★★☆')).toBeInTheDocument()
  })

  it('shows three empty stars for a genuinely zero-breakthrough unit', () => {
    render(<InvestmentBadge grade={0} core={0} />)
    expect(screen.getByText('☆☆☆')).toBeInTheDocument()
  })

  it('renders nothing when grade is unknown, rather than claiming zero', () => {
    // A manually entered draft carries no grade/core. Drawing ☆☆☆ for it would
    // assert "zero breakthrough" about a unit we have no data for. This is the
    // one distinction the whole design turns on - do not collapse it into the
    // grade=0 case above.
    const { container } = render(<InvestmentBadge />)
    expect(container).toBeEmptyDOMElement()
  })
})
```

- [ ] **Step 2: Run tests to verify they fail**

Run from `frontend/`:
```
npx vitest run src/components/InvestmentBadge.test.tsx
```
Expected: FAIL — `Failed to resolve import "./InvestmentBadge"`.

- [ ] **Step 3: Write the badge component**

Create `frontend/src/components/InvestmentBadge.tsx`:

```tsx
// Read-only display of a unit's breakthrough (grade) and core enhancement.
// Both are inputs to the backend's ATK/HP calculation and are already folded
// into the imported stats, so this is informational only - it exists so the
// user can confirm their roster imported correctly.

const STAR_SLOTS = 3

interface InvestmentBadgeProps {
  grade?: number
  core?: number
}

export function InvestmentBadge({ grade, core }: InvestmentBadgeProps) {
  // Absent is not zero: a manually entered draft has no grade, and drawing
  // empty stars for it would claim a fact we do not have.
  if (grade === undefined) return null

  const filled = '★'.repeat(grade)
  const empty = '☆'.repeat(Math.max(0, STAR_SLOTS - grade))

  return (
    <span className="investment" title="Breakthrough and core enhancement">
      <span className="investment__stars">{filled + empty}</span>
      {core !== undefined && core > 0 && (
        <span className="investment__core">+{core}</span>
      )}
    </span>
  )
}
```

- [ ] **Step 4: Run the badge tests**

Run from `frontend/`:
```
npx vitest run src/components/InvestmentBadge.test.tsx
```
Expected: 5 passed.

- [ ] **Step 5: Write the failing import test**

Add to `frontend/src/lib/rosterImport.test.ts`. `parseRosterJson(raw: unknown)` takes an **already-parsed object** (not a JSON string) and returns `{ drafts: NikkeDraft[]; warnings: string[] }`.

```ts
it('carries grade and core through from the payload', () => {
  const { drafts } = parseRosterJson({
    units: [
      {
        name_en: 'Rapi',
        resource_id: 16,
        grade: 3,
        core: 7,
        raid400: { hp: 1, atk: 2, def: 0 },
        skill_levels: { skill1: 1, skill2: 1, burst: 1 },
        overload: [],
      },
    ],
  })
  expect(drafts[0].grade).toBe(3)
  expect(drafts[0].core).toBe(7)
})

it('leaves grade and core undefined when the payload omits them', () => {
  // Absent must stay absent - filling in 0 would make the badge claim zero
  // breakthrough for a unit whose investment we never received.
  const { drafts } = parseRosterJson({
    units: [
      {
        name_en: 'Rapi',
        resource_id: 16,
        raid400: { hp: 1, atk: 2, def: 0 },
        skill_levels: { skill1: 1, skill2: 1, burst: 1 },
        overload: [],
      },
    ],
  })
  expect(drafts[0].grade).toBeUndefined()
  expect(drafts[0].core).toBeUndefined()
})
```

- [ ] **Step 6: Run it to verify it fails**

Run from `frontend/`:
```
npx vitest run src/lib/rosterImport.test.ts
```
Expected: FAIL — `drafts[0].grade` is `undefined` in the first test (and `tsc` would reject the property, which Step 9 catches).

- [ ] **Step 7: Add the draft fields and the import mapping**

In `frontend/src/types/nikkeDraft.ts`, add two optional fields to `NikkeDraft`, after `character_slug`:

```ts
  character_slug: string
  // Breakthrough / core enhancement, display only. Optional because a
  // manually created draft has no import to take them from; absent must not
  // be read as zero.
  grade?: number
  core?: number
  level: string
```

Do **not** add them to `makeEmptyDraft` — a fresh draft genuinely has no value, and adding `grade: undefined` there would be noise.

In `frontend/src/lib/rosterImport.ts`, add the two keys to the `RosterUnit` interface:

```ts
interface RosterUnit {
  resource_id?: number
  name_en: string
  grade?: number
  core?: number
  raid400: { hp: number; atk: number; def: number }
```

and carry them onto the pushed draft, next to `character_slug`:

```ts
      character_slug: mapped ?? deriveSlug(u.name_en),
      grade: u.grade,
      core: u.core,
      level: '400',
```

- [ ] **Step 8: Render the badge in the card header**

In `frontend/src/components/NikkeCard.tsx`, add the import next to the other component imports:

```tsx
import { InvestmentBadge } from './InvestmentBadge'
```

and render it in the header, right after the title, so it reads as part of the unit's identity rather than as a form field:

```tsx
      <header className="card__header">
        <h2 className="card__title">{title}</h2>
        <InvestmentBadge grade={draft.grade} core={draft.core} />
        <div className="card__header-right">
```

Add styles to `frontend/src/App.css`. Read the existing `.card__title` and `.pill` rules first and match their conventions (colour variables, font sizing) rather than inventing new ones:

```css
.investment {
  display: inline-flex;
  align-items: baseline;
  gap: 0.25rem;
}

.investment__core {
  font-variant-numeric: tabular-nums;
}
```

- [ ] **Step 9: Run all frontend checks**

Run from `frontend/`:
```
npx vitest run
npx tsc -b --noEmit
npm run lint
```
Expected: all pass, 163 tests (156 after Task 1 + 5 badge + 2 import). `tsc -b` is the real guard — bare `tsc --noEmit` is a no-op in this repo.

- [ ] **Step 10: Commit**

```bash
git status
git add frontend/src
git commit -m "Show each imported unit's breakthrough and core as a badge"
```

---

### Task 4: Remove the inert core_level input

`core_level` is declared in `backend/app/models.py` as a required field of `UserNikkeState` and is **read nowhere in the backend** — its value is already folded into the imported `raid400` ATK/HP. It is a live form input that changes nothing, the same condition that got `pve_cube` removed in the harmony-cube work. With Task 3's badge showing the real value, leaving an inert input for the same concept beside it would be worse than either alone.

**Files:**
- Modify: `backend/app/models.py` (delete `UserNikkeState.core_level`)
- Modify: `frontend/src/types/userNikkeState.ts` (delete `core_level` from the payload type and from `CONSTRAINTS`)
- Modify: `frontend/src/types/nikkeDraft.ts` (delete `core_level` from the draft, the errors type, `makeEmptyDraft`, `validateDraft`, and the merge functions)
- Modify: `frontend/src/components/NikkeCard.tsx` (delete the Core level `NumberField` and fix the row layout)
- Modify: `frontend/src/lib/rosterImport.ts` (delete `core_level: '0'`)
- Modify tests: `frontend/src/types/nikkeDraft.test.ts`, `frontend/src/lib/rosterImport.test.ts`, `frontend/src/lib/exiaImport.test.ts`, `frontend/src/components/NikkeCard.test.tsx`, `frontend/src/api/recommendClient.mock.test.ts`, `frontend/src/api/recommendRaidClient.mock.test.ts`, `frontend/src/components/RecommendPanel.test.tsx`, and any backend test constructing `UserNikkeState(core_level=...)`

**Interfaces:**
- Consumes: Task 3's badge, which now carries the display duty `core_level` never actually served.
- Produces: `UserNikkeState` no longer has `core_level`; `NikkeDraft` no longer has `core_level`; `CONSTRAINTS.core_level` no longer exists.

- [ ] **Step 1: Write the failing test**

Add to `frontend/src/lib/rosterImport.test.ts`:

```ts
it('no longer produces a core_level field', () => {
  // core_level was an input the backend read nowhere; the InvestmentBadge
  // shows the real value instead.
  const { drafts } = parseRosterJson({
    units: [
      {
        name_en: 'Rapi',
        resource_id: 16,
        grade: 3,
        core: 7,
        raid400: { hp: 1, atk: 2, def: 0 },
        skill_levels: { skill1: 1, skill2: 1, burst: 1 },
        overload: [],
      },
    ],
  })
  expect(drafts[0]).not.toHaveProperty('core_level')
})
```

- [ ] **Step 2: Run it to verify it fails**

Run from `frontend/`:
```
npx vitest run src/lib/rosterImport.test.ts
```
Expected: FAIL — the draft still carries `core_level: '0'`.

- [ ] **Step 3: Remove it from the backend model**

In `backend/app/models.py`, delete this line from `UserNikkeState`:

```python
    core_level: int = Field(ge=0)
```

- [ ] **Step 4: Remove it from the frontend**

In `frontend/src/types/userNikkeState.ts`: delete the `core_level` field from the payload interface and delete `core_level: { min: 0 },` from `CONSTRAINTS`.

In `frontend/src/types/nikkeDraft.ts`, delete every `core_level` occurrence:
- the `core_level: string` field on `NikkeDraft`
- the `core_level?: string` field on `NikkeDraftErrors`
- `core_level: '',` in `makeEmptyDraft`
- in `validateDraft`: the two lines `const coreLevel = parseIntField(draft.core_level, CONSTRAINTS.core_level)` and `if (coreLevel.error) errors.core_level = coreLevel.error`, and `core_level: coreLevel.value!,` from the built payload
- `core_level: inc.core_level,` in the merge function, and the two doc comments that name `core_level` (reword them rather than deleting the surrounding sentence — the comments describe which fields an import overwrites and that list is still meaningful)

In `frontend/src/components/NikkeCard.tsx`, delete the `Core level` `NumberField` entirely. Its wrapper is `<div className="field-row field-row--pair">` holding Level and Core level; with one field left, change that wrapper to a plain `<div className="field-row">` so Level does not render at half width.

In `frontend/src/lib/rosterImport.ts`, delete `core_level: '0',`.

- [ ] **Step 5: Pin that an already-stored roster still loads**

Users have a roster in `localStorage` under the key `nikke-roster` whose entries still carry `core_level`. Removing the field must not make that stored roster unreadable. Add this to `frontend/src/hooks/useRoster.test.ts`, following the setup that file already uses (read it first — it will already have a localStorage-seeding pattern and a `renderHook` import):

```ts
it('loads a stored roster saved before core_level was removed', () => {
  // useRoster JSON.parses whatever is in localStorage; a stale extra key must
  // be ignored, not throw or blank the roster.
  localStorage.setItem(
    'nikke-roster',
    JSON.stringify([
      {
        id: 'a',
        character_slug: 'rapi-red-hood',
        core_level: '7',
        level: '400',
        hp: '1',
        atk: '2',
        def_: '0',
        actualHp: '',
        actualAtk: '',
        actualDef: '',
        skill_levels: { skill1: '1', skill2: '1', burst: '1' },
        overload_options: [],
      },
    ]),
  )
  const { result } = renderHook(() => useRoster())
  expect(result.current.drafts).toHaveLength(1)
  expect(result.current.drafts[0].character_slug).toBe('rapi-red-hood')
  localStorage.clear()
})
```

- [ ] **Step 6: Fix the remaining tests**

Delete `core_level` from the fixture objects and assertions in: `frontend/src/types/nikkeDraft.test.ts`, `frontend/src/lib/rosterImport.test.ts`, `frontend/src/lib/exiaImport.test.ts`, `frontend/src/components/NikkeCard.test.tsx`, `frontend/src/api/recommendClient.mock.test.ts`, `frontend/src/api/recommendRaidClient.mock.test.ts`, `frontend/src/components/RecommendPanel.test.tsx`.

Then grep the backend for constructions that pass it:
```bash
grep -rn "core_level" backend/
```
Delete the argument at each hit. Do not re-add the field to make a test pass; if a test appears to genuinely need it, stop and report that instead.

- [ ] **Step 7: Run everything**

Run from `frontend/`:
```
npx vitest run
npx tsc -b --noEmit
npm run lint
```
Then from `backend/`:
```
PYTHONPATH=. python3 -m pytest -q
```
Expected: all pass. `tsc -b` will name every surviving reference to the deleted field — treat it as the checklist. The backend suite catches contract drift between the frontend payload and the API model.

- [ ] **Step 8: Commit**

```bash
git status
git add frontend/src backend/app backend/tests
git commit -m "Remove the core_level input the backend never read"
```

---

## Documentation (after Task 4)

- [ ] Check off both items in `docs/roadmap.md`'s To-Do "로스터 동기화 후속" section — the bookmarklet tab-reuse entry and the `core_level` display entry — with a one-line resolution each, matching how the harmony-cube entry above them was closed.
- [ ] Add a `docs/decisions.md` entry recording that `core_level` was removed for the same reason as `pve_cube`: an input the backend reads nowhere misleads the user, and the badge now carries the display duty. Note the game rule that core enhancement follows 3 breakthroughs, and that the badge deliberately does not enforce it.
- [ ] Commit the docs.
