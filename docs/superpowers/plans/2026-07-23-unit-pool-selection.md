# Unit Pool Selection Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let the user toggle off Nikkes they will not field, shrinking the search candidate pool at the source (faster raid-from-scratch, more relevant results), across all three recommend modes.

**Architecture:** Pure frontend. A `UnitPalette` component (generalized from `DraftPalette`) renders each owned+supported unit with a "Use" checkbox (default on). `RecommendPanel` holds an ephemeral `excludedSlugs` set and filters the roster to `effectiveRoster` before every request/hash/size-check. No backend or API-contract change — excluded units simply never appear in the payload.

**Tech Stack:** React + Vite + TypeScript; Vitest + @testing-library/react + @testing-library/user-event.

## Global Constraints

- **No backend change.** Excluded units are filtered out client-side; the `/api/recommend`, `/api/recommend-raid`, and `/api/supported-units` contracts are untouched. No backend test changes.
- **Ephemeral exclusion.** `excludedSlugs` lives in React state only — never written to localStorage — and resets to empty when the active profile (`activeOpenId`) changes.
- **Whitelist framing, default all-in.** Every owned+supported unit starts included (checkbox checked); the user unchecks the few they will not field.
- **All three modes.** The palette appears in `single`, `raid`, and `draft` modes. `effectiveRoster` feeds the request roster, `hashRecommendInputs`, and the `rosterTooSmall` guard in all three.
- **Existing constants (do not redefine):** `MIN_DECK_ROSTER_SIZE = 5`, `MAX_DRAFT_SEATS_PER_DECK = 5` (already exported from `types/recommend.ts` / `types/draft.ts`).

---

## File Structure

- `frontend/src/components/DraftEditor.tsx` — add `removeUnitBySlug` helper (unplace a unit found anywhere by slug).
- `frontend/src/components/UnitPalette.tsx` — NEW, generalizes `DraftPalette`: tier-grouped grid, per-unit "Use" checkbox (pool membership) + optional place button (draft).
- `frontend/src/components/DraftPalette.tsx` — DELETE (replaced by `UnitPalette`).
- `frontend/src/components/UnitPalette.test.tsx` — NEW (absorbs `DraftPalette.test.tsx` cases + pool-toggle cases).
- `frontend/src/components/DraftPalette.test.tsx` — DELETE.
- `frontend/src/components/RecommendPanel.tsx` — exclusion state, `effectiveRoster`, `toggleExclude`, render `UnitPalette` in all modes, profile-switch reset.
- `frontend/src/components/RecommendPanel.test.tsx` — new exclusion integration tests.
- `frontend/src/App.css` — add `.draft-palette__item`, `--excluded`, and `__use` rules (reuses existing `draft-palette` classes; no CSS rename).

---

### Task 1: `removeUnitBySlug` draft helper

Excluding a unit that is already placed in the draft must remove it from its seat. The existing `removeUnit(draft, deckIndex, seatIndex)` removes by position; add a thin slug-based wrapper.

**Files:**
- Modify: `frontend/src/components/DraftEditor.tsx` (add export near `removeUnit`, ~line 44)
- Test: `frontend/src/components/DraftEditor.test.tsx` (append)

**Interfaces:**
- Consumes: `Draft` (`{ decks: DraftSeat[][] }`), existing `mapDeck`.
- Produces: `removeUnitBySlug(draft: Draft, slug: string): Draft` — returns a new Draft with `slug` removed from whichever deck holds it; returns `draft` unchanged if the slug is not placed.

- [ ] **Step 1: Write the failing test**

Append to `frontend/src/components/DraftEditor.test.tsx`:

```tsx
import { removeUnitBySlug, placeUnit } from './DraftEditor'
import { makeEmptyDraft } from '../types/draft'

describe('removeUnitBySlug', () => {
  it('removes a placed slug from whichever deck holds it', () => {
    let draft = makeEmptyDraft(2)
    draft = placeUnit(draft, 1, 'liter')
    const next = removeUnitBySlug(draft, 'liter')
    expect(next.decks[1]).toEqual([])
  })

  it('returns the draft unchanged when the slug is not placed', () => {
    const draft = placeUnit(makeEmptyDraft(2), 0, 'crown')
    expect(removeUnitBySlug(draft, 'liter')).toBe(draft)
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npx vitest run src/components/DraftEditor.test.tsx`
Expected: FAIL — `removeUnitBySlug is not a function` / not exported.

- [ ] **Step 3: Write minimal implementation**

In `frontend/src/components/DraftEditor.tsx`, add after `removeUnit` (line 44):

```tsx
/** Removes `slug` from whichever deck seat holds it (a slug sits in at most
 * one deck). Returns `draft` unchanged if the slug is not placed anywhere. */
export const removeUnitBySlug = (draft: Draft, slug: string): Draft => {
  const deckIndex = draft.decks.findIndex((seats) => seats.some((seat) => seat.slug === slug))
  if (deckIndex === -1) return draft
  const seatIndex = draft.decks[deckIndex].findIndex((seat) => seat.slug === slug)
  return removeUnit(draft, deckIndex, seatIndex)
}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npx vitest run src/components/DraftEditor.test.tsx`
Expected: PASS (all DraftEditor tests).

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/DraftEditor.tsx frontend/src/components/DraftEditor.test.tsx
git commit -m "Add removeUnitBySlug draft helper"
```

---

### Task 2: `UnitPalette` component (generalize `DraftPalette`)

Replace `DraftPalette` with `UnitPalette`: same tier-grouped grid, plus a per-unit "Use" checkbox (pool membership) and an optional place button (draft only). Excluded units render dimmed and are unplaceable. `RecommendPanel`'s existing draft-mode usage is switched over with inert exclusion props (real state comes in Task 3), so the build and behavior stay unchanged this task.

**Files:**
- Create: `frontend/src/components/UnitPalette.tsx`
- Create: `frontend/src/components/UnitPalette.test.tsx`
- Delete: `frontend/src/components/DraftPalette.tsx`, `frontend/src/components/DraftPalette.test.tsx`
- Modify: `frontend/src/components/RecommendPanel.tsx` (import + draft-mode usage, ~line 33 and ~351)
- Modify: `frontend/src/App.css` (append 3 rules after line 521)

**Interfaces:**
- Consumes: `SupportedUnit` (`{ slug, name, burstTier, element }`), `usePortraitManifest`.
- Produces: `UnitPalette` with props:
  - `ownedSlugs: string[]`
  - `supportedUnits: SupportedUnit[]`
  - `excludedSlugs: string[]`
  - `onToggleExclude: (slug: string) => void`
  - `usedSlugs?: string[]` (default `[]`)
  - `onPick?: (slug: string) => void` (when omitted → no place button)

- [ ] **Step 1: Write the failing test**

Create `frontend/src/components/UnitPalette.test.tsx`:

```tsx
import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { UnitPalette } from './UnitPalette'
import type { SupportedUnit } from '../types/supportedUnit'

vi.mock('../hooks/usePortraitManifest', () => ({
  usePortraitManifest: () => ({ portraitFor: () => null }),
}))

const UNITS: SupportedUnit[] = [
  { slug: 'crown', name: 'Crown', burstTier: 1, element: 'Iron' },
  { slug: 'anne', name: 'Anne', burstTier: 1, element: 'Fire' },
  { slug: 'liter', name: 'Liter', burstTier: 2, element: 'Water' },
  { slug: 'blanc', name: 'Blanc', burstTier: 3, element: 'Wind' },
  { slug: 'noir', name: 'Noir', burstTier: 3, element: 'Electric' },
]

const base = {
  ownedSlugs: ['crown', 'liter', 'blanc'],
  supportedUnits: UNITS,
  excludedSlugs: [],
  onToggleExclude: () => {},
}

describe('UnitPalette', () => {
  it('groups owned-and-supported units under B1/B2/B3, excluding unowned', () => {
    render(<UnitPalette {...base} onPick={() => {}} usedSlugs={[]} />)
    expect(screen.getByRole('heading', { name: 'B1' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'B2' })).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: 'B3' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /crown/i })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /anne/i })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /noir/i })).not.toBeInTheDocument()
  })

  it('renders a placed (used) unit as disabled for placement', () => {
    render(<UnitPalette {...base} onPick={() => {}} usedSlugs={['crown']} />)
    expect(screen.getByRole('button', { name: /crown/i })).toBeDisabled()
    expect(screen.getByRole('button', { name: /liter/i })).not.toBeDisabled()
  })

  it('calls onPick when a free, included unit is clicked (draft mode)', async () => {
    const user = userEvent.setup()
    const onPick = vi.fn()
    render(<UnitPalette {...base} onPick={onPick} usedSlugs={[]} />)
    await user.click(screen.getByRole('button', { name: /liter/i }))
    expect(onPick).toHaveBeenCalledWith('liter')
  })

  it('shows a checked Use checkbox per included unit; unchecked when excluded', () => {
    render(<UnitPalette {...base} excludedSlugs={['liter']} />)
    expect(screen.getByRole('checkbox', { name: /use crown/i })).toBeChecked()
    expect(screen.getByRole('checkbox', { name: /use liter/i })).not.toBeChecked()
  })

  it('calls onToggleExclude when a Use checkbox is toggled', async () => {
    const user = userEvent.setup()
    const onToggleExclude = vi.fn()
    render(<UnitPalette {...base} onToggleExclude={onToggleExclude} />)
    await user.click(screen.getByRole('checkbox', { name: /use crown/i }))
    expect(onToggleExclude).toHaveBeenCalledWith('crown')
  })

  it('disables the place button for an excluded unit (draft mode)', () => {
    render(<UnitPalette {...base} onPick={() => {}} usedSlugs={[]} excludedSlugs={['blanc']} />)
    expect(screen.getByRole('button', { name: /blanc/i })).toBeDisabled()
  })

  it('renders no place button when onPick is omitted (single/raid mode)', () => {
    render(<UnitPalette {...base} />)
    expect(screen.queryByRole('button', { name: /crown/i })).not.toBeInTheDocument()
    expect(screen.getByRole('checkbox', { name: /use crown/i })).toBeInTheDocument()
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npx vitest run src/components/UnitPalette.test.tsx`
Expected: FAIL — cannot resolve `./UnitPalette`.

- [ ] **Step 3: Create the component**

Create `frontend/src/components/UnitPalette.tsx`:

```tsx
// The player's unit grid, shared by all three recommend modes. Owned units
// (active profile roster) intersected with engine-supported units
// (GET /api/supported-units), grouped under B1/B2/B3. Each unit has a "Use"
// checkbox for candidate-pool membership (default on); unchecking dims it and
// drops it from the search pool. In draft mode (onPick provided) an included,
// unplaced unit is also clickable to place it into a deck; excluded or placed
// units are not placeable.

import { usePortraitManifest } from '../hooks/usePortraitManifest'
import type { SupportedUnit } from '../types/supportedUnit'

interface UnitPaletteProps {
  /** Slugs of Nikkes in the (validated) owned roster. */
  ownedSlugs: string[]
  supportedUnits: SupportedUnit[]
  /** Slugs the user has toggled OUT of the candidate pool. */
  excludedSlugs: string[]
  onToggleExclude: (slug: string) => void
  /** Draft mode only: slugs already placed in a deck (place button disabled). */
  usedSlugs?: string[]
  /** Draft mode only: click an included, unplaced unit to place it. Omit for
   * single/raid, which have no placement. */
  onPick?: (slug: string) => void
}

const BURST_TIERS = [1, 2, 3] as const

export function UnitPalette({
  ownedSlugs,
  supportedUnits,
  excludedSlugs,
  onToggleExclude,
  usedSlugs = [],
  onPick,
}: UnitPaletteProps) {
  const { portraitFor } = usePortraitManifest()
  const ownedSet = new Set(ownedSlugs)
  const usedSet = new Set(usedSlugs)
  const excludedSet = new Set(excludedSlugs)
  const shown = supportedUnits.filter((unit) => ownedSet.has(unit.slug))

  return (
    <div className="draft-palette">
      {BURST_TIERS.map((tier) => {
        const units = shown.filter((unit) => unit.burstTier === tier)
        if (units.length === 0) return null
        return (
          <section key={tier} className="draft-palette__group">
            <h4 className="draft-palette__heading">B{tier}</h4>
            <ul className="draft-palette__list">
              {units.map((unit) => {
                const isUsed = usedSet.has(unit.slug)
                const isExcluded = excludedSet.has(unit.slug)
                const portrait = portraitFor(unit.slug)
                const chip = portrait ? (
                  <img className="draft-palette__portrait" src={portrait} alt="" />
                ) : (
                  <span className="draft-palette__chip">
                    <span className="draft-palette__chip-name">{unit.name}</span>
                    <span className="draft-palette__chip-meta">
                      B{unit.burstTier} · {unit.element}
                    </span>
                  </span>
                )
                return (
                  <li
                    key={unit.slug}
                    className={
                      isExcluded
                        ? 'draft-palette__item draft-palette__item--excluded'
                        : 'draft-palette__item'
                    }
                  >
                    {onPick ? (
                      <button
                        type="button"
                        className="draft-palette__unit"
                        disabled={isUsed || isExcluded}
                        aria-label={`${unit.name} (B${unit.burstTier})`}
                        onClick={() => onPick(unit.slug)}
                      >
                        {chip}
                      </button>
                    ) : (
                      <span
                        className="draft-palette__unit"
                        aria-label={`${unit.name} (B${unit.burstTier})`}
                      >
                        {chip}
                      </span>
                    )}
                    <label className="draft-palette__use checkbox">
                      <input
                        type="checkbox"
                        checked={!isExcluded}
                        aria-label={`Use ${unit.name}`}
                        onChange={() => onToggleExclude(unit.slug)}
                      />
                      Use
                    </label>
                  </li>
                )
              })}
            </ul>
          </section>
        )
      })}
    </div>
  )
}
```

- [ ] **Step 4: Delete `DraftPalette` and switch `RecommendPanel` over**

Delete the old files:

```bash
git rm frontend/src/components/DraftPalette.tsx frontend/src/components/DraftPalette.test.tsx
```

In `frontend/src/components/RecommendPanel.tsx`, change the import (line 33):

```tsx
import { UnitPalette } from './UnitPalette'
```

And the draft-mode usage (the `<DraftPalette ... />` block ~line 351) — pass inert exclusion props for now (real state lands in Task 3):

```tsx
<UnitPalette
  ownedSlugs={ownedSlugs}
  supportedUnits={supportedUnits.units}
  usedSlugs={usedSlugs}
  onPick={handlePick}
  excludedSlugs={[]}
  onToggleExclude={() => {}}
/>
```

- [ ] **Step 5: Append CSS**

In `frontend/src/App.css`, after line 521 (`.draft-palette__chip-meta` block), add:

```css
.draft-palette__item {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: var(--sp-1);
}

.draft-palette__item--excluded .draft-palette__unit {
  opacity: 0.35;
  text-decoration: line-through;
}

.draft-palette__use {
  font-size: 11px;
  color: var(--text-muted);
}
```

- [ ] **Step 6: Run tests, types, and build**

Run: `cd frontend && npx vitest run src/components/UnitPalette.test.tsx src/components/RecommendPanel.test.tsx && npx tsc -b && npm run build`
Expected: PASS — UnitPalette tests green, RecommendPanel tests still green (behavior unchanged), `tsc -b` clean, build clean.

- [ ] **Step 7: Commit**

```bash
git add -A
git commit -m "Generalize DraftPalette into UnitPalette with a Use (pool) toggle"
```

---

### Task 3: Wire exclusion into `RecommendPanel` (all modes)

Add the ephemeral `excludedSlugs` state, derive `effectiveRoster`, route it into every request + the cache hash + the size guard, render `UnitPalette` in single/raid modes too, auto-unplace on exclude, and reset on profile switch.

**Files:**
- Modify: `frontend/src/components/RecommendPanel.tsx`
- Test: `frontend/src/components/RecommendPanel.test.tsx` (append)

**Interfaces:**
- Consumes: `removeUnitBySlug` (Task 1), `UnitPalette` (Task 2), existing `hashRecommendInputs`, `MIN_DECK_ROSTER_SIZE`.
- Produces: no new exports — internal state/handlers only.

- [ ] **Step 1: Write the failing tests**

Append to `frontend/src/components/RecommendPanel.test.tsx` (helpers `nikke`, `noPersistence`, mocks already exist at file top; the mock for `getSupportedUnits` must return the units so the palette renders — set it per test):

```tsx
import { MIN_DECK_ROSTER_SIZE } from '../types/recommend'
import type { SupportedUnit } from '../types/supportedUnit'

describe('RecommendPanel unit-pool exclusion', () => {
  // getSupportedUnits resolves the ALREADY-MAPPED camelCase shape
  // (SupportedUnit, `burstTier`) — the hook uses it verbatim, no re-mapping.
  const supported: SupportedUnit[] = [
    { slug: 'a', name: 'A', burstTier: 1, element: 'Iron' },
    { slug: 'b', name: 'B', burstTier: 2, element: 'Fire' },
    { slug: 'c', name: 'C', burstTier: 3, element: 'Water' },
    { slug: 'd', name: 'D', burstTier: 3, element: 'Wind' },
    { slug: 'e', name: 'E', burstTier: 3, element: 'Electric' },
    { slug: 'f', name: 'F', burstTier: 2, element: 'Iron' },
  ]
  // Six units so excluding one still leaves >= MIN_DECK_ROSTER_SIZE (5) and the
  // request can actually fire. `fullRoster` (top of file) is exactly 5.
  const poolRoster = ['a', 'b', 'c', 'd', 'e', 'f'].map(nikke)

  const raidResponse = {
    decks: [], combined_total_damage: 0, excluded_slugs: [],
    leftover_slugs: [], within_draft: null, baseline_total_damage: null,
  }

  const renderMode = async (roster: UserNikkeState[], radio: RegExp) => {
    vi.mocked(getSupportedUnits).mockResolvedValue(supported)
    vi.mocked(recommendRaidDecks).mockResolvedValue(raidResponse)
    const user = userEvent.setup()
    render(<RecommendPanel roster={roster} {...noPersistence} />)
    await user.click(screen.getByRole('radio', { name: radio }))
    await screen.findByRole('checkbox', { name: /use a/i }) // palette loaded
    return user
  }

  it('drops an unchecked unit from the raid request roster', async () => {
    const user = await renderMode(poolRoster, /raid allocation/i)
    await user.click(screen.getByRole('checkbox', { name: /use a/i }))
    await user.click(screen.getByRole('button', { name: /allocate raid decks/i }))
    await waitFor(() => expect(recommendRaidDecks).toHaveBeenCalled())
    const sent = vi.mocked(recommendRaidDecks).mock.calls[0][0]
    expect(sent.roster.map((n) => n.character_slug)).not.toContain('a')
    expect(sent.roster.map((n) => n.character_slug)).toContain('b')
  })

  it('disables submit when exclusions drop the roster below the minimum', async () => {
    // fullRoster is exactly MIN_DECK_ROSTER_SIZE (5); excluding one under-fills.
    expect(fullRoster.length).toBe(MIN_DECK_ROSTER_SIZE)
    const user = await renderMode(fullRoster, /raid allocation/i)
    await user.click(screen.getByRole('checkbox', { name: /use a/i }))
    expect(screen.getByRole('button', { name: /allocate raid decks/i })).toBeDisabled()
  })
})
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd frontend && npx vitest run src/components/RecommendPanel.test.tsx -t "unit-pool exclusion"`
Expected: FAIL — no "Use A" checkbox in raid mode (palette not rendered there yet).

- [ ] **Step 3: Add exclusion state + effectiveRoster + handler**

In `frontend/src/components/RecommendPanel.tsx`:

Add state near the other `useState` calls (~line 103):

```tsx
const [excludedSlugs, setExcludedSlugs] = useState<Set<string>>(new Set())
```

Derive the effective roster (add after the `bossProfile` memo, ~line 180):

```tsx
const effectiveRoster = useMemo(
  () => roster.filter((nikke) => !excludedSlugs.has(nikke.character_slug)),
  [roster, excludedSlugs],
)
```

Add the toggle handler (near `handlePick`, ~line 200) — excluding a placed unit unplaces it:

```tsx
const toggleExclude = (slug: string) => {
  setExcludedSlugs((prev) => {
    const next = new Set(prev)
    if (next.has(slug)) {
      next.delete(slug)
    } else {
      next.add(slug)
      setDraftValue((current) => removeUnitBySlug(current, slug))
    }
    return next
  })
}
```

Add the import for `removeUnitBySlug` (line 32, alongside `placeUnit`):

```tsx
import { DraftEditor, placeUnit, removeUnitBySlug, toRequestDraft } from './DraftEditor'
```

- [ ] **Step 4: Route `effectiveRoster` into requests, hash, and the size guard**

Replace `roster` with `effectiveRoster` in these exact spots:

`rosterTooSmall` (line 186):
```tsx
const rosterTooSmall = effectiveRoster.length < MIN_DECK_ROSTER_SIZE
```

Single request (line 213):
```tsx
const request: RecommendRequest = { roster: effectiveRoster, boss: bossProfile }
```

Hash (line 233):
```tsx
const hash = hashRecommendInputs(effectiveRoster, bossProfile, draftForHash, numDecks)
```

Raid request (line 247):
```tsx
const request: RecommendRaidRequest = { roster: effectiveRoster, boss: bossProfile, num_decks: numDecks }
```

Draft request (line 252):
```tsx
const request: RecommendRaidRequest = {
  roster: effectiveRoster,
  boss: bossProfile,
  num_decks: numDecks,
  draft: toRequestDraft(draftValue),
}
```

Leave `ownedSlugs` (line 194) on the full `roster` — the palette must still show excluded units (dimmed) so they can be re-included.

- [ ] **Step 5: Reset exclusions on profile switch**

In the restore effect (the `useEffect` keyed on `[activeOpenId]`, ~line 120), add as the first line of the effect body:

```tsx
setExcludedSlugs(new Set())
```

- [ ] **Step 6: Render `UnitPalette` in all modes**

Extract a shared palette element and render it for every mode. Replace the draft-only `<UnitPalette .../>` block (inside the `mode === 'draft'` fieldset, ~line 351) so the palette shows in single/raid too.

Add, just above the `{mode === 'draft' && (` fieldset (~line 342):

```tsx
{mode !== 'draft' && (
  <fieldset className="group">
    <legend className="group__legend">Units to use</legend>
    {/* Default-expanded (discoverable) but collapsible. `open` also keeps the
        checkboxes in the a11y tree for tests without a jsdom details toggle. */}
    <details className="group__details" open>
      <summary className="group__hint">
        {effectiveRoster.length}/{roster.length} in the search pool — uncheck any you
        won&rsquo;t field
      </summary>
      {supportedUnits.error && <p className="field__error">{supportedUnits.error}</p>}
      <UnitPalette
        ownedSlugs={ownedSlugs}
        supportedUnits={supportedUnits.units}
        excludedSlugs={[...excludedSlugs]}
        onToggleExclude={toggleExclude}
      />
    </details>
  </fieldset>
)}
```

And update the draft-mode `<UnitPalette>` (from Task 2's inert version) to wire the real props:

```tsx
<UnitPalette
  ownedSlugs={ownedSlugs}
  supportedUnits={supportedUnits.units}
  usedSlugs={usedSlugs}
  onPick={handlePick}
  excludedSlugs={[...excludedSlugs]}
  onToggleExclude={toggleExclude}
/>
```

- [ ] **Step 7: Run the exclusion tests**

Run: `cd frontend && npx vitest run src/components/RecommendPanel.test.tsx -t "unit-pool exclusion"`
Expected: PASS.

- [ ] **Step 8: Run the full frontend gate**

Run: `cd frontend && npx vitest run && npx tsc -b && npm run build`
Expected: PASS — all tests green, `tsc -b` clean, build clean.

- [ ] **Step 9: Commit**

```bash
git add frontend/src/components/RecommendPanel.tsx frontend/src/components/RecommendPanel.test.tsx
git commit -m "Wire per-request unit-pool exclusion into all recommend modes"
```

---

### Task 4: Draft-mode auto-unplace integration test

Task 1 unit-tested `removeUnitBySlug` and Task 3 wired it; add one integration test proving that excluding a *placed* unit in draft mode removes it from its seat and from the submitted draft.

**Files:**
- Test: `frontend/src/components/RecommendPanel.test.tsx` (append to the `unit-pool exclusion` describe)

**Interfaces:**
- Consumes: everything from Task 3 (no new production code — this task is test-only unless the integration reveals a defect).

- [ ] **Step 1: Write the failing test**

Append inside the `unit-pool exclusion` describe:

```tsx
it('unplaces a drafted unit when it is excluded (draft mode)', async () => {
  // poolRoster/supported/raidResponse are defined in this describe's scope.
  const user = await renderMode(poolRoster, /draft-based/i)

  // Place unit "a" into a deck, then exclude it.
  await user.click(screen.getByRole('button', { name: /a \(b1\)/i }))
  expect(screen.getByText('a')).toBeInTheDocument() // seat slug rendered by DraftEditor
  await user.click(screen.getByRole('checkbox', { name: /use a/i }))

  await user.click(screen.getByRole('button', { name: /optimize draft/i }))
  await waitFor(() => expect(recommendRaidDecks).toHaveBeenCalled())
  const sent = vi.mocked(recommendRaidDecks).mock.calls[0][0]
  const draftedSlugs = (sent.draft ?? []).flatMap((d) => d.units.map((u) => u.slug))
  expect(draftedSlugs).not.toContain('a')
  expect(sent.roster.map((n) => n.character_slug)).not.toContain('a')
})
```

Note: `renderMode` (Task 3) awaits `findByRole('checkbox', { name: /use a/i })`, which
resolves in draft mode too (the palette renders in every mode). The place button
`a (B1)` is present because unit `a` is included and unplaced.

- [ ] **Step 2: Run test to verify it passes (or fails meaningfully)**

Run: `cd frontend && npx vitest run src/components/RecommendPanel.test.tsx -t "unplaces a drafted unit"`
Expected: PASS (Task 3 already wired `toggleExclude` → `removeUnitBySlug`). If it FAILS, fix the wiring in `RecommendPanel.tsx` `toggleExclude` (this is why the integration test exists), then re-run.

- [ ] **Step 3: Run the full frontend gate**

Run: `cd frontend && npx vitest run && npx tsc -b`
Expected: PASS, clean.

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/RecommendPanel.test.tsx frontend/src/components/RecommendPanel.tsx
git commit -m "Integration-test draft auto-unplace on exclude"
```

---

### Task 5: Docs — mark roadmap follow-up landed

Record the feature against the Phase 5 performance follow-up so the roadmap reflects that the user-driven pool-shrink lever shipped (and the two-stage algorithm remains a deferred, reassess-after backlog item).

**Files:**
- Modify: `docs/roadmap.md` (Phase 5 "후속(성능)" backlog area, around line 447–454)

**Interfaces:** none (documentation).

- [ ] **Step 1: Add the landed note**

In `docs/roadmap.md`, immediately after the `03f77ca` bullet (~line 454), add:

```markdown
  - **✅ 유저 풀 선택(제외) 착지 (2026-07-23):** 세 추천 모드(single/raid/draft)에
    "사용할 니케" 화이트리스트(기본 전체, 안 쓸 유닛만 토글 오프) 추가 — 프론트가
    `보유∩지원−제외`로 로스터를 필터링해 요청 전 전송(백엔드 무변경). 탐색 풀을
    근원에서 줄여 raid-from-scratch를 유저가 뺀 만큼 단축. 휘발성(프로필 전환 리셋),
    `DraftPalette`→`UnitPalette` 일반화. spec/plan:
    `docs/superpowers/{specs,plans}/2026-07-23-unit-pool-selection*`. **2단계 탐색
    (선택→좁은 분할)은 실사용 속도 확인 후 재판단(여전히 백로그).**
```

- [ ] **Step 2: Commit**

```bash
git add docs/roadmap.md
git commit -m "docs(roadmap): record unit-pool selection landing"
```

---

## Self-Review

**Spec coverage:**
- 후보 풀 모델 (`보유∩지원−excluded`, effectiveRoster into requests/hash/rosterTooSmall) → Task 3 Steps 3–4.
- `DraftPalette`→`UnitPalette` 일반화 (Use 토글 + optional 배치) → Task 2.
- 배치 유닛 제외 시 자동 해제 (`removeUnitBySlug`) → Task 1 + wired Task 3 Step 3 + integration Task 4.
- 세 모드 모두 팔레트 노출 → Task 3 Step 6.
- 프로필 전환 리셋 → Task 3 Step 5.
- 과다 제외 → rosterTooSmall → Task 3 Step 4 + test Step 1.
- 캐시 풀별 분리 (effectiveRoster in hash) → Task 3 Step 4 (the differing-roster request test covers the roster path; hash uses the same effectiveRoster).
- 백엔드 무변경 → no backend task; Global Constraints.
- 테스트 (UnitPalette, RecommendPanel, removeUnitBySlug) → Tasks 1, 2, 3, 4.

**Placeholder scan:** No TBD/TODO; every code step shows complete code and exact commands.

**Type consistency:** `removeUnitBySlug(draft, slug)` defined in Task 1, consumed in Task 3 Step 3 and Task 4 with the same signature. `UnitPalette` props defined in Task 2, consumed with matching prop names/types in Task 3 Steps 6. `excludedSlugs` is a `Set<string>` in state, spread to `string[]` (`[...excludedSlugs]`) at the `UnitPalette` boundary (which takes `string[]`) — consistent.
