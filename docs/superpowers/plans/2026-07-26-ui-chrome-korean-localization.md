# UI 크롬 한글화 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace every hardcoded English UI-chrome string in `frontend/src` (headings, labels, buttons, hints, empty states, aria-labels, titles, fallback error messages) with Korean, per `docs/superpowers/specs/2026-07-26-ui-chrome-korean-localization-design.md`.

**Architecture:** No i18n library. Direct string replacement in JSX/TS, matching the existing project convention of hardcoding Korean text directly in source (`backend/app/overload_effects.py`'s `NAME_TO_STAT`). A small shared `lib/elementName.ts` module avoids duplicating the 5-entry element-name map between `BossProfileField.tsx` (static select options) and `UnitPalette.tsx` (dynamic per-unit display).

**Tech Stack:** React 19 + TypeScript + Vite, Vitest + Testing Library (existing stack, unchanged).

## Global Constraints

- Never introduce an i18n library (react-i18next, etc.) — this is a Korean-only service, decided prior to this work (see the design spec's "배경").
- Register/tone: casual-polite Korean ("~해요", "~돼요", "~하세요"), matching the tone already used in `lib/bookmarklet.ts`'s alerts. Not stiff formal Korean.
- Established project vocabulary (reuse verbatim, do not invent alternatives): 로스터 (roster), 덱 (deck), 돌파 (breakthrough/grade), 코어 (core), 오버로드 (overload), 큐브 (cube), 보스 설정 (boss profile).
- Element names (Fienn's exact call, `docs/superpowers/specs/2026-07-26-ui-chrome-korean-localization-design.md`): Fire=작열, Water=수냉, Wind=풍압, Iron=철갑, Electric=전격.
- The "all Nikkes wear a Resilience Cube Lv.15" note reuses the exact wording Fienn already approved in `docs/superpowers/specs/2026-07-20-harmony-cube-assumed-lv15-design.md:157-158`: "모든 니케가 Resilience 큐브 Lv.15를 착용한 것으로 계산합니다." (keep "Resilience" untranslated — that's the approved wording; only "Cube"→"큐브" changed).
- Unit name "Ark Ranger Black" → "아크레인저 블랙" (per `backend/app/display_names.py:91`, the one already-encoded display name this plan's hint text needs to quote).
- Out of scope (do not touch): raw FastAPI/Pydantic validation `msg` strings passed through from the backend (only the frontend's own fallback text is in scope); `lib/bookmarklet.ts` (already Korean); short game-standard codes `S1`/`S2`/`B`, `B1`/`B2`/`B3` (kept as-is); the placeholder example URL in `SyncRosterPanel.tsx`.
- After each task, run the test file(s) named in that task and confirm PASS before committing. Two test files — `App.test.tsx` and `RecommendPanel.test.tsx` — render most of the component tree as children, so they will show *additional* stale-English failures introduced by earlier tasks' component changes, on top of their own. That's expected and intentional (see Task 8 and Task 9, which are where those two files are brought fully green) — don't stop to fix them early.
- Final task runs the whole suite (`npm test -- --run`) and must match the pre-change baseline: **289 passed, 0 failed** (same test count — this is a string-content change, not a coverage change).

---

## Task 1: Shared element-name helper

**Files:**
- Create: `frontend/src/lib/elementName.ts`
- Create: `frontend/src/lib/elementName.test.ts`

**Interfaces:**
- Produces: `elementLabel(element: NikkeElement): string` — used by Task 3 (`BossProfileField.tsx`) and Task 7 (`UnitPalette.tsx`).

- [ ] **Step 1: Write the failing test**

```typescript
// frontend/src/lib/elementName.test.ts
import { describe, it, expect } from 'vitest'
import { elementLabel } from './elementName'

describe('elementLabel', () => {
  it.each([
    ['Fire', '작열'],
    ['Water', '수냉'],
    ['Wind', '풍압'],
    ['Iron', '철갑'],
    ['Electric', '전격'],
  ] as const)('%s -> %s', (element, label) => {
    expect(elementLabel(element)).toBe(label)
  })
})
```

- [ ] **Step 2: Run test to verify it fails**

Run: `npx vitest run src/lib/elementName.test.ts`
Expected: FAIL — cannot find module `./elementName`

- [ ] **Step 3: Write minimal implementation**

```typescript
// frontend/src/lib/elementName.ts
// Korean display names for a Nikke/boss element (Fienn's call, 2026-07-26 —
// see docs/superpowers/specs/2026-07-26-ui-chrome-korean-localization-design.md).
// Shared by BossProfileField (static element picker) and UnitPalette (per-unit
// display) so the two never drift.

import type { NikkeElement } from '../types/supportedUnit'

const ELEMENT_LABELS: Record<NikkeElement, string> = {
  Fire: '작열',
  Water: '수냉',
  Wind: '풍압',
  Iron: '철갑',
  Electric: '전격',
}

export const elementLabel = (element: NikkeElement): string => ELEMENT_LABELS[element]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npx vitest run src/lib/elementName.test.ts`
Expected: PASS (5 tests)

- [ ] **Step 5: Commit**

```bash
git add frontend/src/lib/elementName.ts frontend/src/lib/elementName.test.ts
git commit -m "Add shared Korean element-name helper"
```

---

## Task 2: DeckCard + ExcludedSlugsNote

These two are rendered by DeckResults/RaidResults/DraftResults/RecommendPanel, so translating them first means every consumer test file's DeckCard/ExcludedSlugsNote-related assertions only need updating once (in each consumer's own task below), not repeatedly discovered later.

**Files:**
- Modify: `frontend/src/components/DeckCard.tsx`
- Modify: `frontend/src/components/ExcludedSlugsNote.tsx`
- Test: none directly (covered transitively by Task 3/4/6/8's test files) — this task has no test file of its own to turn green, so instead confirm the two files still compile: `npx tsc -b --noEmit`.

- [ ] **Step 1: Edit DeckCard.tsx**

In `frontend/src/components/DeckCard.tsx`:

```diff
-        <span className="deck-results__total">
-          {formatDamage(deck.total_damage)} total dmg
-        </span>
+        <span className="deck-results__total">
+          {formatDamage(deck.total_damage)} 총딜
+        </span>
```

```diff
-                <span className="deck-results__pin" title="Kept here because you locked it">
+                <span className="deck-results__pin" title="고정해서 여기 유지됨">
                   <span aria-hidden="true">📌</span>
-                  <span className="visually-hidden">pinned</span>
+                  <span className="visually-hidden">고정됨</span>
```

```diff
-        <span>Burst: {formatDamage(deck.burst_damage)}</span>
-        <span>Normal: {formatDamage(deck.normal_attack_damage)}</span>
+        <span>버스트: {formatDamage(deck.burst_damage)}</span>
+        <span>평타: {formatDamage(deck.normal_attack_damage)}</span>
```

- [ ] **Step 2: Edit ExcludedSlugsNote.tsx**

In `frontend/src/components/ExcludedSlugsNote.tsx`:

```diff
-      Not yet supported (excluded from search): {excludedSlugs.map(nameFromSlug).join(', ')}
+      아직 미지원 (탐색에서 제외됨): {excludedSlugs.map(nameFromSlug).join(', ')}
```

- [ ] **Step 3: Type-check**

Run: `npx tsc -b --noEmit`
Expected: no errors (this task only changed string literals)

- [ ] **Step 4: Commit**

```bash
git add frontend/src/components/DeckCard.tsx frontend/src/components/ExcludedSlugsNote.tsx
git commit -m "Localize DeckCard and ExcludedSlugsNote to Korean"
```

(Leave `npm test -- --run` red after this task — DeckResults.test.tsx, RaidResults.test.tsx, DraftResults.test.tsx and RecommendPanel.test.tsx all assert the old English text these two files produced. Each is fixed in its own task below.)

---

## Task 3: DeckResults + RaidResults

**Files:**
- Modify: `frontend/src/components/DeckResults.tsx`
- Modify: `frontend/src/components/RaidResults.tsx`
- Test: `frontend/src/components/DeckResults.test.tsx`
- Test: `frontend/src/components/RaidResults.test.tsx`

- [ ] **Step 1: Edit DeckResults.tsx**

```diff
-      <p className="empty__text">No decks recommended yet.</p>
+      <p className="empty__text">아직 추천된 덱이 없어요.</p>
```

- [ ] **Step 2: Edit RaidResults.tsx**

```diff
-        <p className="empty__text">No raid decks allocated yet.</p>
+        <p className="empty__text">아직 배분된 레이드 덱이 없어요.</p>
```

```diff
-      <p className="raid-results__note">
-        Field all {decks.length} of these decks together — each Nikke is allocated to exactly
-        one deck. This is a partition, not a ranked list of alternatives.
-      </p>
-      <p className="raid-results__combined">
-        Combined total: <strong>{formatDamage(combinedTotalDamage)} dmg</strong>
-      </p>
+      <p className="raid-results__note">
+        이 {decks.length}개 덱을 모두 함께 편성하세요 — 각 니케는 정확히 하나의 덱에만
+        배정돼요. 이것은 순위별 대안이 아니라 하나의 분할이에요.
+      </p>
+      <p className="raid-results__combined">
+        총합: <strong>{formatDamage(combinedTotalDamage)} 딜</strong>
+      </p>
```

```diff
-            label={`Deck ${index + 1}`}
+            label={`덱 ${index + 1}`}
```

```diff
-          Bench (not allocated to a deck): {leftoverSlugs.map(nameFor).join(', ')}
+          벤치 (덱에 배정되지 않음): {leftoverSlugs.map(nameFor).join(', ')}
```

- [ ] **Step 3: Run tests to see the expected failures**

Run: `npx vitest run src/components/DeckResults.test.tsx src/components/RaidResults.test.tsx`
Expected: FAIL — several `getByText`/`queryByText` calls can't find the (now-Korean) text

- [ ] **Step 4: Update DeckResults.test.tsx**

```diff
-    expect(screen.getByText('No decks recommended yet.')).toBeInTheDocument()
+    expect(screen.getByText('아직 추천된 덱이 없어요.')).toBeInTheDocument()
```

```diff
-    expect(screen.getByText('5,000,000 total dmg')).toBeInTheDocument()
-    expect(screen.getByText('Burst: 3,000,000')).toBeInTheDocument()
-    expect(screen.getByText('Normal: 2,000,000')).toBeInTheDocument()
+    expect(screen.getByText('5,000,000 총딜')).toBeInTheDocument()
+    expect(screen.getByText('버스트: 3,000,000')).toBeInTheDocument()
+    expect(screen.getByText('평타: 2,000,000')).toBeInTheDocument()
```

```diff
-      screen.getByText('Not yet supported (excluded from search): Some Slug, Other Slug'),
+      screen.getByText('아직 미지원 (탐색에서 제외됨): Some Slug, Other Slug'),
```

```diff
-    expect(screen.queryByText(/Not yet supported/)).not.toBeInTheDocument()
+    expect(screen.queryByText(/아직 미지원/)).not.toBeInTheDocument()
```

- [ ] **Step 5: Update RaidResults.test.tsx**

```diff
-    expect(screen.getByText('No raid decks allocated yet.')).toBeInTheDocument()
+    expect(screen.getByText('아직 배분된 레이드 덱이 없어요.')).toBeInTheDocument()
```

```diff
-    expect(screen.getByText('Deck 1')).toBeInTheDocument()
-    expect(screen.getByText('Deck 2')).toBeInTheDocument()
+    expect(screen.getByText('덱 1')).toBeInTheDocument()
+    expect(screen.getByText('덱 2')).toBeInTheDocument()
    expect(screen.queryByText('#1')).not.toBeInTheDocument()
-    expect(screen.getByText('5,000,000 total dmg')).toBeInTheDocument()
-    expect(screen.getByText('Burst: 3,000,000')).toBeInTheDocument()
-    expect(screen.getByText('Normal: 2,000,000')).toBeInTheDocument()
+    expect(screen.getByText('5,000,000 총딜')).toBeInTheDocument()
+    expect(screen.getByText('버스트: 3,000,000')).toBeInTheDocument()
+    expect(screen.getByText('평타: 2,000,000')).toBeInTheDocument()
```

```diff
-    expect(screen.getByText('100 dmg')).toBeInTheDocument()
+    expect(screen.getByText('100 딜')).toBeInTheDocument()
```

```diff
-    expect(screen.getByText('Bench (not allocated to a deck): F, G')).toBeInTheDocument()
+    expect(screen.getByText('벤치 (덱에 배정되지 않음): F, G')).toBeInTheDocument()
```

```diff
-    expect(screen.queryByText(/Bench/)).not.toBeInTheDocument()
+    expect(screen.queryByText(/벤치/)).not.toBeInTheDocument()
```

```diff
-      screen.getByText('Not yet supported (excluded from search): Some Slug'),
+      screen.getByText('아직 미지원 (탐색에서 제외됨): Some Slug'),
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `npx vitest run src/components/DeckResults.test.tsx src/components/RaidResults.test.tsx`
Expected: PASS (both files' suites green)

- [ ] **Step 7: Commit**

```bash
git add frontend/src/components/DeckResults.tsx frontend/src/components/RaidResults.tsx frontend/src/components/DeckResults.test.tsx frontend/src/components/RaidResults.test.tsx
git commit -m "Localize DeckResults and RaidResults to Korean"
```

---

## Task 4: DraftEditor

**Files:**
- Modify: `frontend/src/components/DraftEditor.tsx`
- Test: `frontend/src/components/DraftEditor.test.tsx`

- [ ] **Step 1: Edit DraftEditor.tsx**

```diff
-      <p className="draft-editor__hint">
-        Drag a unit onto a deck to seat it, or from one deck to another to move
-        it. Slots are membership only — the engine assigns burst roles.
-      </p>
+      <p className="draft-editor__hint">
+        유닛을 덱 위로 드래그하면 배치돼요. 다른 덱으로 옮기려면 그쪽으로
+        드래그하세요. 슬롯은 소속만 나타내며, 버스트 순서는 엔진이 정해요.
+      </p>
```

```diff
-              <h4 className="draft-editor__deck-title">
-                Deck {deckIndex + 1}
-                {missing.length > 0 && (
-                  <span className="draft-editor__deck-warning">
-                    no {missing.map((tier) => `B${tier}`).join(', ')}
-                  </span>
-                )}
+              <h4 className="draft-editor__deck-title">
+                덱 {deckIndex + 1}
+                {missing.length > 0 && (
+                  <span className="draft-editor__deck-warning">
+                    {missing.map((tier) => `B${tier}`).join(', ')} 없음
+                  </span>
+                )}
```

```diff
-                  const where = `deck ${deckIndex + 1}`
+                  const where = `덱 ${deckIndex + 1}`
```

```diff
-                        aria-label={`Lock ${name} in ${where}`}
+                        aria-label={`${where}에서 ${name} 고정`}
```

```diff
-                        aria-label={`Remove ${name} from ${where}`}
+                        aria-label={`${where}에서 ${name} 제거`}
```

- [ ] **Step 2: Run test to see the expected failures**

Run: `npx vitest run src/components/DraftEditor.test.tsx`
Expected: FAIL — heading/button name queries for "Deck N", "no B2, B3", "Lock ... in deck 1", "Remove ... from deck 1" no longer match

- [ ] **Step 3: Update DraftEditor.test.tsx**

```diff
-    expect(screen.getByRole('heading', { name: /Deck 1/ })).toBeInTheDocument()
-    expect(screen.getByRole('heading', { name: /Deck 2/ })).toBeInTheDocument()
-    expect(screen.getByRole('button', { name: 'Remove Crown from deck 1' })).toBeInTheDocument()
+    expect(screen.getByRole('heading', { name: /덱 1/ })).toBeInTheDocument()
+    expect(screen.getByRole('heading', { name: /덱 2/ })).toBeInTheDocument()
+    expect(screen.getByRole('button', { name: '덱 1에서 Crown 제거' })).toBeInTheDocument()
```

```diff
-    expect(screen.getByRole('heading', { name: /no B2, B3/ })).toBeInTheDocument()
+    expect(screen.getByRole('heading', { name: /B2, B3 없음/ })).toBeInTheDocument()
```

```diff
-    expect(screen.queryByText(/^no B/)).not.toBeInTheDocument()
+    expect(screen.queryByText(/없음$/)).not.toBeInTheDocument()
```

```diff
-    const lock = screen.getByRole('button', { name: 'Lock Crown in deck 1' })
+    const lock = screen.getByRole('button', { name: '덱 1에서 Crown 고정' })
```

```diff
-    await user.click(screen.getByRole('button', { name: 'Remove Crown from deck 1' }))
+    await user.click(screen.getByRole('button', { name: '덱 1에서 Crown 제거' }))
```

```diff
-      screen.getByRole('heading', { name: new RegExp(`Deck ${index + 1}`) }).closest('div')!
+      screen.getByRole('heading', { name: new RegExp(`덱 ${index + 1}`) }).closest('div')!
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npx vitest run src/components/DraftEditor.test.tsx`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/DraftEditor.tsx frontend/src/components/DraftEditor.test.tsx
git commit -m "Localize DraftEditor to Korean"
```

---

## Task 5: DraftResults

**Files:**
- Modify: `frontend/src/components/DraftResults.tsx`
- Test: `frontend/src/components/DraftResults.test.tsx`

- [ ] **Step 1: Edit DraftResults.tsx**

```diff
-      <p className="raid-results__note">
-        Three ascending tiers: your submitted draft, the best allocation using
-        only your drafted units, and the bench-inclusive recommendation.
-      </p>
+      <p className="raid-results__note">
+        세 단계로 올라갑니다: 제출한 드래프트, 드래프트한 유닛만으로 만든
+        최선의 배분, 벤치까지 포함한 추천.
+      </p>
```

```diff
-      <section className="draft-results__tier" aria-label="Your draft">
-        <h3 className="draft-results__tier-title">Your draft</h3>
-        <p className="draft-results__tier-total">{formatDamage(baselineTotalDamage)} dmg</p>
+      <section className="draft-results__tier" aria-label="내 드래프트">
+        <h3 className="draft-results__tier-title">내 드래프트</h3>
+        <p className="draft-results__tier-total">{formatDamage(baselineTotalDamage)} 딜</p>
```

```diff
-      <section className="draft-results__tier" aria-label="Best within your draft">
-        <h3 className="draft-results__tier-title">
-          Best within your draft (+{formatDamage(delta1)})
-        </h3>
-        <p className="draft-results__tier-total">
-          {formatDamage(withinDraft.combined_total_damage)} dmg
-        </p>
+      <section className="draft-results__tier" aria-label="드래프트 내 최선">
+        <h3 className="draft-results__tier-title">
+          드래프트 내 최선 (+{formatDamage(delta1)})
+        </h3>
+        <p className="draft-results__tier-total">
+          {formatDamage(withinDraft.combined_total_damage)} 딜
+        </p>
```

```diff
-                label={`Deck ${index + 1}`}
+                label={`덱 ${index + 1}`}
```
(this `label={\`Deck ${index + 1}\`}` edit occurs twice in the file — within-draft tier and recommended tier — apply to both)

```diff
-      <section className="draft-results__tier" aria-label="Recommended">
-        <h3 className="draft-results__tier-title">
-          Recommended, bench-inclusive (+{formatDamage(delta2)})
-        </h3>
-        <p className="draft-results__tier-total">{formatDamage(combinedTotalDamage)} dmg</p>
+      <section className="draft-results__tier" aria-label="추천">
+        <h3 className="draft-results__tier-title">
+          추천 (벤치 포함, +{formatDamage(delta2)})
+        </h3>
+        <p className="draft-results__tier-total">{formatDamage(combinedTotalDamage)} 딜</p>
```

```diff
-          Bench (not allocated to a deck): {leftoverSlugs.map(nameFor).join(', ')}
+          벤치 (덱에 배정되지 않음): {leftoverSlugs.map(nameFor).join(', ')}
```

- [ ] **Step 2: Run test to see the expected failures**

Run: `npx vitest run src/components/DraftResults.test.tsx`
Expected: FAIL — several text queries no longer match

- [ ] **Step 3: Update DraftResults.test.tsx**

```diff
-    expect(screen.getByText('Your draft')).toBeInTheDocument()
-    expect(screen.getByText('100 dmg')).toBeInTheDocument()
+    expect(screen.getByText('내 드래프트')).toBeInTheDocument()
+    expect(screen.getByText('100 딜')).toBeInTheDocument()
```

```diff
-    expect(screen.getByText(/Best within your draft/)).toHaveTextContent('+10')
-    expect(screen.getByText('110 dmg')).toBeInTheDocument()
+    expect(screen.getByText(/드래프트 내 최선/)).toHaveTextContent('+10')
+    expect(screen.getByText('110 딜')).toBeInTheDocument()
```

```diff
-    expect(screen.getByText(/Recommended/)).toHaveTextContent('+20')
-    expect(screen.getByText('130 dmg')).toBeInTheDocument()
+    expect(screen.getByText(/추천/)).toHaveTextContent('+20')
+    expect(screen.getByText('130 딜')).toBeInTheDocument()
```

```diff
-    expect(screen.getByText('pinned')).toBeInTheDocument()
+    expect(screen.getByText('고정됨')).toBeInTheDocument()
```

```diff
-    expect(screen.queryByText('Your draft')).not.toBeInTheDocument()
-    expect(screen.queryByText(/Best within your draft/)).not.toBeInTheDocument()
-    expect(screen.getByText('Deck 1')).toBeInTheDocument()
-    expect(screen.getByText('130 dmg')).toBeInTheDocument()
-    expect(screen.getByText('Bench (not allocated to a deck): Bench Unit')).toBeInTheDocument()
+    expect(screen.queryByText('내 드래프트')).not.toBeInTheDocument()
+    expect(screen.queryByText(/드래프트 내 최선/)).not.toBeInTheDocument()
+    expect(screen.getByText('덱 1')).toBeInTheDocument()
+    expect(screen.getByText('130 딜')).toBeInTheDocument()
+    expect(screen.getByText('벤치 (덱에 배정되지 않음): Bench Unit')).toBeInTheDocument()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npx vitest run src/components/DraftResults.test.tsx`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/DraftResults.tsx frontend/src/components/DraftResults.test.tsx
git commit -m "Localize DraftResults to Korean"
```

---

## Task 6: InvestmentBadge, InvestmentSummary, NikkeCard, FavoriteItemBadge check

**Files:**
- Modify: `frontend/src/components/InvestmentBadge.tsx`
- Modify: `frontend/src/components/InvestmentSummary.tsx`
- Modify: `frontend/src/components/NikkeCard.tsx`
- Test: `frontend/src/components/InvestmentBadge.test.tsx` (no assertion touches the changed string — confirm it still passes unmodified)
- Test: `frontend/src/components/NikkeCard.test.tsx`

`FavoriteItemBadge.tsx` needs no change (already Korean, `title="애장품 장착"`).

- [ ] **Step 1: Edit InvestmentBadge.tsx**

```diff
-    <span className="investment" title="Breakthrough and core enhancement">
+    <span className="investment" title="돌파 및 코어 강화">
```

- [ ] **Step 2: Edit InvestmentSummary.tsx**

```diff
-export function OverloadLines({ options, emptyText = 'No overload lines.' }: OverloadLinesProps) {
+export function OverloadLines({ options, emptyText = '오버로드 없음.' }: OverloadLinesProps) {
```

- [ ] **Step 3: Edit NikkeCard.tsx**

```diff
-  const title = name || draft.character_slug.trim() || `Nikke ${index + 1}`
+  const title = name || draft.character_slug.trim() || `니케 ${index + 1}`
```

```diff
-    <section className="card roster-card" data-element={element} aria-label={`Investment data for ${title}`}>
+    <section className="card roster-card" data-element={element} aria-label={`${title} 투자 정보`}>
```

```diff
-      <OverloadLines options={draft.overload_options} emptyText="No overload" />
+      <OverloadLines options={draft.overload_options} emptyText="오버로드 없음" />
```

- [ ] **Step 4: Run tests**

Run: `npx vitest run src/components/InvestmentBadge.test.tsx src/components/NikkeCard.test.tsx`
Expected: `InvestmentBadge.test.tsx` still PASS unmodified (no assertion checks the `title` attribute). `NikkeCard.test.tsx` FAILs on the `'Nikke 1'` heading-name assertion.

- [ ] **Step 5: Update NikkeCard.test.tsx**

```diff
-    expect(screen.getByRole('heading', { name: 'Nikke 1' })).toBeInTheDocument()
+    expect(screen.getByRole('heading', { name: '니케 1' })).toBeInTheDocument()
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `npx vitest run src/components/InvestmentBadge.test.tsx src/components/NikkeCard.test.tsx`
Expected: PASS (both files)

- [ ] **Step 7: Commit**

```bash
git add frontend/src/components/InvestmentBadge.tsx frontend/src/components/InvestmentSummary.tsx frontend/src/components/NikkeCard.tsx frontend/src/components/NikkeCard.test.tsx
git commit -m "Localize InvestmentBadge, InvestmentSummary default, and NikkeCard to Korean"
```

---

## Task 7: RosterGrid + UnitPalette

**Files:**
- Modify: `frontend/src/components/RosterGrid.tsx`
- Modify: `frontend/src/components/UnitPalette.tsx` (consumes `elementLabel` from Task 1)
- Test: `frontend/src/components/RosterGrid.test.tsx`
- Test: `frontend/src/components/UnitPalette.test.tsx`

- [ ] **Step 1: Edit RosterGrid.tsx**

```diff
-          <summary className="roster__unsupported-summary">
-            Not yet supported by the engine ({unsupported.length})
-          </summary>
+          <summary className="roster__unsupported-summary">
+            엔진 미지원 ({unsupported.length}기)
+          </summary>
```

- [ ] **Step 2: Edit UnitPalette.tsx**

```diff
+import { elementLabel } from '../lib/elementName'
```
(add alongside the existing imports at the top of the file)

```diff
-                      aria-label={`Use ${unit.name}`}
+                      aria-label={`${unit.name} 사용`}
```

```diff
-                          <span className="palette__meta">
-                            B{unit.burstTier} · {unit.element}
-                          </span>
-                          <OverloadLines
-                            options={owned.overload_options}
-                            emptyText="No overload"
-                          />
+                          <span className="palette__meta">
+                            B{unit.burstTier} · {elementLabel(unit.element)}
+                          </span>
+                          <OverloadLines
+                            options={owned.overload_options}
+                            emptyText="오버로드 없음"
+                          />
```

- [ ] **Step 3: Run tests to see the expected failures**

Run: `npx vitest run src/components/RosterGrid.test.tsx src/components/UnitPalette.test.tsx`
Expected: FAIL — `'Not yet supported by the engine (2)'` and `/use crown/i`-style queries and `'No overload'` no longer match

- [ ] **Step 4: Update RosterGrid.test.tsx**

```diff
-    expect(screen.getByText('Not yet supported by the engine (2)')).toBeInTheDocument()
+    expect(screen.getByText('엔진 미지원 (2기)')).toBeInTheDocument()
```
(this string occurs twice in the file — apply to both)

- [ ] **Step 5: Update UnitPalette.test.tsx**

```diff
-    expect(unitButton(/use crown/i)).toBeInTheDocument()
-    expect(screen.queryByRole('button', { name: /anne/i })).not.toBeInTheDocument()
-    expect(screen.queryByRole('button', { name: /noir/i })).not.toBeInTheDocument()
+    expect(unitButton(/crown 사용/i)).toBeInTheDocument()
+    expect(screen.queryByRole('button', { name: /anne/i })).not.toBeInTheDocument()
+    expect(screen.queryByRole('button', { name: /noir/i })).not.toBeInTheDocument()
```

```diff
-    expect(unitButton(/use crown/i)).toBeInTheDocument()
-    expect(unitButton(/use liter/i)).toBeInTheDocument()
+    expect(unitButton(/crown 사용/i)).toBeInTheDocument()
+    expect(unitButton(/liter 사용/i)).toBeInTheDocument()
```
(the `/use crown/i` / `/use liter/i` / `/use blanc/i` patterns recur across several `it` blocks in this file — replace every occurrence with `/crown 사용/i` / `/liter 사용/i` / `/blanc 사용/i` respectively, keeping which slug each occurrence refers to unchanged)

```diff
-    expect(screen.getByText('No overload')).toBeInTheDocument()
+    expect(screen.getByText('오버로드 없음')).toBeInTheDocument()
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `npx vitest run src/components/RosterGrid.test.tsx src/components/UnitPalette.test.tsx`
Expected: PASS (both files)

- [ ] **Step 7: Commit**

```bash
git add frontend/src/components/RosterGrid.tsx frontend/src/components/UnitPalette.tsx frontend/src/components/RosterGrid.test.tsx frontend/src/components/UnitPalette.test.tsx
git commit -m "Localize RosterGrid and UnitPalette to Korean"
```

---

## Task 8: BossProfileField + RecommendPanel

This is the big one: `RecommendPanel.test.tsx` renders the whole recommend-panel tree (BossProfileField, DeckResults, RaidResults, DraftEditor, DraftResults, UnitPalette — all already translated by Tasks 2–7), so this task is where every remaining stale-English assertion in that file gets fixed in one pass, together with this task's own new BossProfileField/RecommendPanel string changes.

**Files:**
- Modify: `frontend/src/components/BossProfileField.tsx` (consumes `elementLabel` from Task 1)
- Modify: `frontend/src/components/RecommendPanel.tsx`
- Test: `frontend/src/components/RecommendPanel.test.tsx`

- [ ] **Step 1: Edit BossProfileField.tsx**

```diff
+import { elementLabel } from '../lib/elementName'
```
(add alongside existing imports)

```diff
-      <legend className="group__legend">Boss profile</legend>
+      <legend className="group__legend">보스 설정</legend>
```

```diff
-        <label className="field__label" htmlFor={elementId}>
-          Element
-        </label>
+        <label className="field__label" htmlFor={elementId}>
+          속성
+        </label>
```

```diff
-          <option value="">Non-elemental</option>
-          {BOSS_ELEMENTS.map((element) => (
-            <option key={element} value={element}>
-              {element}
-            </option>
-          ))}
+          <option value="">무속성</option>
+          {BOSS_ELEMENTS.map((element) => (
+            <option key={element} value={element}>
+              {elementLabel(element)}
+            </option>
+          ))}
```

```diff
-        Core is hittable
+        코어 피격 가능
```

```diff
-        Part-destruction gimmick
-        <span className="group__hint">
-          {' '}
-          selects the max-potential model for part-dependent units (e.g. Ark Ranger
-          Black); unchecked uses the lower-bound model
-        </span>
+        부위파괴 기믹
+        <span className="group__hint">
+          {' '}
+          부위파괴에 의존하는 유닛(예: 아크레인저 블랙)의 최대 잠재력 모델을
+          선택합니다. 체크 해제 시 하한 모델을 사용합니다.
+        </span>
```

```diff
-          label="Enemy DEF"
+          label="적 방어력"
```

```diff
-          label="Fight duration"
-          hint="seconds"
+          label="전투 시간"
+          hint="초"
```

- [ ] **Step 2: Edit RecommendPanel.tsx**

```diff
-  const submitLabel =
-    mode === 'single'
-      ? active.status === 'loading'
-        ? 'Recommending…'
-        : 'Recommend decks'
-      : mode === 'raid'
-        ? active.status === 'loading'
-          ? 'Allocating…'
-          : 'Allocate raid decks'
-        : active.status === 'loading'
-          ? 'Optimizing…'
-          : 'Optimize draft'
+  const submitLabel =
+    mode === 'single'
+      ? active.status === 'loading'
+        ? '추천 중…'
+        : '덱 추천'
+      : mode === 'raid'
+        ? active.status === 'loading'
+          ? '배분 중…'
+          : '레이드 덱 배분'
+        : active.status === 'loading'
+          ? '최적화 중…'
+          : '드래프트 최적화'
```

```diff
-    <section className="card" aria-label="Deck recommendation">
-      <header className="card__header">
-        <h2 className="card__title">Recommend decks</h2>
+    <section className="card" aria-label="덱 추천">
+      <header className="card__header">
+        <h2 className="card__title">덱 추천</h2>
```

```diff
-            <legend className="group__legend">Mode</legend>
+            <legend className="group__legend">모드</legend>
```

```diff
-                Single deck
-                <span className="group__hint"> — ranked alternatives for one deck</span>
+                단일 덱
+                <span className="group__hint"> — 덱 하나의 순위별 대안</span>
```

```diff
-                Raid allocation
-                <span className="group__hint"> — multiple disjoint decks fielded together</span>
+                레이드 배분
+                <span className="group__hint"> — 여러 개의 겹치지 않는 덱을 동시에 편성</span>
```

```diff
-                Draft-based optimization
-                <span className="group__hint">
-                  {' '}
-                  — seed decks with your own key units, the engine fills/optimizes the rest
-                </span>
+                드래프트 기반 최적화
+                <span className="group__hint">
+                  {' '}
+                  — 직접 고른 핵심 유닛으로 덱을 시드하면, 엔진이 나머지를 채우고
+                  최적화
+                </span>
```

```diff
-                <label className="field__label" htmlFor={numDecksId}>
-                  Number of decks
-                </label>
+                <label className="field__label" htmlFor={numDecksId}>
+                  덱 개수
+                </label>
```

```diff
-              {active.status === 'loading' && (
-                <button type="button" className="btn" onClick={active.cancel}>
-                  Cancel
-                </button>
-              )}
-              {rosterTooSmall && (
-                <p className="field__error" role="alert">
-                  Add at least {MIN_DECK_ROSTER_SIZE} ready Nikkes to recommend a deck.
-                </p>
-              )}
+              {active.status === 'loading' && (
+                <button type="button" className="btn" onClick={active.cancel}>
+                  취소
+                </button>
+              )}
+              {rosterTooSmall && (
+                <p className="field__error" role="alert">
+                  덱을 추천하려면 준비된 니케가 최소 {MIN_DECK_ROSTER_SIZE}기 필요해요.
+                </p>
+              )}
```

```diff
-            <legend className="group__legend">Units to use</legend>
+            <legend className="group__legend">사용할 유닛</legend>
```

```diff
-              <summary className="group__hint">
-                {poolKnown ? poolIncluded : effectiveRoster.length}/
-                {poolKnown ? poolTotal : roster.length} in the search pool — click any you
-                won&rsquo;t field to drop it
-                {poolKnown && unsupportedCount > 0 && (
-                  <> ({unsupportedCount} owned but not yet supported)</>
-                )}
-              </summary>
+              <summary className="group__hint">
+                {poolKnown ? poolIncluded : effectiveRoster.length}/
+                {poolKnown ? poolTotal : roster.length} 탐색 풀에 포함됨 — 편성하지
+                않을 유닛을 클릭하면 제외돼요
+                {poolKnown && unsupportedCount > 0 && (
+                  <> (보유 중이나 아직 미지원 {unsupportedCount}기)</>
+                )}
+              </summary>
```

```diff
-            <legend className="group__legend">Draft</legend>
+            <legend className="group__legend">드래프트</legend>
```

```diff
-      {mode !== 'single' && raid.status === 'loading' && (
-        <p className="recommend-form__progress" role="status">
-          {mode === 'raid' ? 'Allocating raid decks' : 'Optimizing your draft'} — this runs
-          thousands of simulations and typically takes 1–2 minutes. It&rsquo;s still working; the
-          button will re-enable when it&rsquo;s done.
-        </p>
-      )}
+      {mode !== 'single' && raid.status === 'loading' && (
+        <p className="recommend-form__progress" role="status">
+          {mode === 'raid' ? '레이드 덱 배분 중' : '드래프트 최적화 중'} — 수천 번의
+          시뮬레이션을 실행하며 보통 1~2분이 걸려요. 아직 진행 중이니 완료되면
+          버튼이 다시 활성화돼요.
+        </p>
+      )}
```

- [ ] **Step 3: Run test to see the expected failures**

Run: `npx vitest run src/components/RecommendPanel.test.tsx`
Expected: FAIL — many assertions (from this task's changes, plus the accumulated changes from Tasks 2–7 that this file's tests also exercise)

- [ ] **Step 4: Update RecommendPanel.test.tsx**

Apply every one of these replacements (each `old` may occur more than once in the file — replace every occurrence):

| Old | New |
|---|---|
| `'Add at least 5 ready Nikkes to recommend a deck.'` | `'덱을 추천하려면 준비된 니케가 최소 5기 필요해요.'` |
| `/recommend decks/i` (button name) | `/덱 추천/i` |
| `/boss profile/i` (group name) | `/보스 설정/i` |
| `/^mode$/i` (group name) | `/^모드$/i` |
| `/units to use/i` (group name) | `/사용할 유닛/i` |
| `/^cancel$/i` | `/^취소$/i` |
| `'100 total dmg'` | `'100 총딜'` |
| `/raid allocation/i` | `/레이드 배분/i` |
| `/allocate raid decks/i` | `/레이드 덱 배분/i` |
| `/allocating/i` (button name, loading state) | `/배분 중/i` |
| `/draft-based/i` | `/드래프트 기반/i` |
| `/optimize draft/i` | `/드래프트 최적화/i` |
| `'Element'` (label text) | `'속성'` |
| `'Core is hittable'` | `'코어 피격 가능'` |
| `'Enemy DEF'` | `'적 방어력'` |
| `/part-destruction gimmick/i` | `/부위파괴 기믹/i` |
| `'Number of decks'` | `'덱 개수'` |
| `/use a/i` (aria-label, unit named "A") | `/a 사용/i` |
| `/use bready/i` | `/bready 사용/i` |
| `/use u0/i` | `/u0 사용/i` |
| `'Deck 1'` / `'Deck 2'` | `'덱 1'` / `'덱 2'` |
| `` `Deck ${deckNumber}` `` (in the `dropOnDeck` test helper's RegExp) | `` `덱 ${deckNumber}` `` |
| `'180 dmg'` / `'100 dmg'` / `'999 dmg'` | `'180 딜'` / `'100 딜'` / `'999 딜'` |
| `'Bench (not allocated to a deck): K'` | `'벤치 (덱에 배정되지 않음): K'` |
| `/Field all 1 of these decks together/` | `/이 1개 덱을 모두 함께 편성하세요/` |
| `/Field all/` | `/모두 함께 편성/` |
| `'Combined total:'` (in `queryByText(..., { exact: false })`) | `'총합:'` |
| `'Remove A from deck 1'` | `'덱 1에서 A 제거'` |
| `/1–2 minutes/` | `/1~2분/` |

Two spots need special care rather than a blind replace:

1. The `dropOnDeck` helper near the top of the file:
   ```diff
   -  const deck = screen.getByRole('heading', { name: new RegExp(`Deck ${deckNumber}`) })
   +  const deck = screen.getByRole('heading', { name: new RegExp(`덱 ${deckNumber}`) })
   ```
2. `selectOptions(screen.getByLabelText('Element'), 'Fire')` — **do not change the `'Fire'` argument.** It matches the `<option>`'s `value` attribute, which stays the raw English enum (`BossElement`) — only the option's visible text became `elementLabel(element)` in Step 1. Only `getByLabelText('Element')` needs updating (to `'속성'`); the value `'Fire'` is correct as-is.

- [ ] **Step 5: Run test to verify it passes**

Run: `npx vitest run src/components/RecommendPanel.test.tsx`
Expected: PASS (all tests in the file)

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/BossProfileField.tsx frontend/src/components/RecommendPanel.tsx frontend/src/components/RecommendPanel.test.tsx
git commit -m "Localize BossProfileField and RecommendPanel to Korean"
```

---

## Task 9: SyncRosterPanel + ProfileSwitcher

**Files:**
- Modify: `frontend/src/components/SyncRosterPanel.tsx`
- Modify: `frontend/src/components/ProfileSwitcher.tsx`
- Test: `frontend/src/components/SyncRosterPanel.test.tsx`
- Test: `frontend/src/components/ProfileSwitcher.test.tsx`

- [ ] **Step 1: Edit SyncRosterPanel.tsx**

```diff
-    setSummary(`${drafts.length} units synced`)
+    setSummary(`${drafts.length}기 동기화됨`)
```

```diff
-      <h2 className="sync__title">Sync from blablalink</h2>
+      <h2 className="sync__title">blablalink에서 동기화</h2>
       <div className="field">
         <label className="field__label" htmlFor="share-url">
-          ShiftyPad share URL
+          ShiftyPad 공유 URL
         </label>
```

```diff
-          <p className="sync__hint">
-            Drag this link to your bookmarks bar, then click it while logged in
-            to blablalink. Your roster opens in a new tab, so this tab
-            won&rsquo;t update until you reload it.
-          </p>
+          <p className="sync__hint">
+            이 링크를 북마크 바로 드래그한 다음, blablalink에 로그인한 상태에서
+            클릭하세요. 로스터가 새 탭에서 열리므로, 이 탭은 새로고침해야
+            갱신돼요.
+          </p>
```

```diff
-            Sync NIKKE roster
+            니케 로스터 동기화
```

```diff
-      {status === 'importing' && <p className="sync__message">Importing…</p>}
+      {status === 'importing' && <p className="sync__message">가져오는 중…</p>}
```

- [ ] **Step 2: Edit ProfileSwitcher.tsx**

```diff
-    if (window.confirm(`Delete profile "${activeLabel}"? This removes its synced roster and cached results.`)) {
+    if (window.confirm(`"${activeLabel}" 프로필을 삭제할까요? 동기화된 로스터와 캐시된 결과가 함께 삭제돼요.`)) {
```

```diff
-      <label className="field__label" htmlFor="profile-select">
-        Account
-      </label>
+      <label className="field__label" htmlFor="profile-select">
+        계정
+      </label>
```

```diff
-        aria-label={`Delete profile ${activeLabel}`}
+        aria-label={`${activeLabel} 프로필 삭제`}
```

```diff
-      >
-        Delete
-      </button>
+      >
+        삭제
+      </button>
```

- [ ] **Step 3: Run tests to see the expected failures**

Run: `npx vitest run src/components/SyncRosterPanel.test.tsx src/components/ProfileSwitcher.test.tsx`
Expected: FAIL — label/link/text queries relying on English substrings no longer match

- [ ] **Step 4: Update SyncRosterPanel.test.tsx**

```diff
-    fireEvent.change(screen.getByLabelText(/share url/i), {
+    fireEvent.change(screen.getByLabelText(/공유 url/i), {
```
(this `getByLabelText(/share url/i)` pattern occurs 3 times in the file — update every occurrence to `/공유 url/i`)

```diff
-    const link = screen.getByRole('link', { name: /roster/i })
+    const link = screen.getByRole('link', { name: /로스터/i })
```
(the `getByRole('link', { name: /roster/i })` / `queryByRole('link', { name: /roster/i })` pattern occurs 5 times — update every occurrence to `/로스터/i`)

```diff
-    expect(screen.getByText('1 units synced')).toBeTruthy()
+    expect(screen.getByText('1기 동기화됨')).toBeTruthy()
```

```diff
-      await screen.findByText(/1 owned units not yet supported/),
+      await screen.findByText(/보유 유닛 중 1기가 아직 미지원/),
```

```diff
-    await waitFor(() => expect(screen.getByText('0 units synced')).toBeTruthy())
-    fireEvent.change(input, { target: { value: '' } })
-    expect(screen.queryByText('0 units synced')).toBeNull()
+    await waitFor(() => expect(screen.getByText('0기 동기화됨')).toBeTruthy())
+    fireEvent.change(input, { target: { value: '' } })
+    expect(screen.queryByText('0기 동기화됨')).toBeNull()
```

- [ ] **Step 5: Update ProfileSwitcher.test.tsx**

```diff
-    await user.click(screen.getByRole('button', { name: /delete/i }))
+    await user.click(screen.getByRole('button', { name: /삭제/i }))
```
(occurs twice in the file — update both)

- [ ] **Step 6: Run tests to verify they pass**

Run: `npx vitest run src/components/SyncRosterPanel.test.tsx src/components/ProfileSwitcher.test.tsx`
Expected: PASS (both files)

- [ ] **Step 7: Commit**

```bash
git add frontend/src/components/SyncRosterPanel.tsx frontend/src/components/ProfileSwitcher.tsx frontend/src/components/SyncRosterPanel.test.tsx frontend/src/components/ProfileSwitcher.test.tsx
git commit -m "Localize SyncRosterPanel and ProfileSwitcher to Korean"
```

---

## Task 10: App.tsx

`App.test.tsx` renders the whole app shell (ProfileSwitcher, SyncRosterPanel, RosterGrid, RecommendPanel — all already translated by prior tasks), so — like Task 8 — this is where the file's accumulated stale assertions plus this task's own changes both get fixed.

**Files:**
- Modify: `frontend/src/App.tsx`
- Test: `frontend/src/App.test.tsx`

- [ ] **Step 1: Edit App.tsx**

```diff
 const TABS: { id: Tab; label: string }[] = [
-  { id: 'roster', label: 'Roster' },
-  { id: 'recommend', label: 'Recommend' },
+  { id: 'roster', label: '로스터' },
+  { id: 'recommend', label: '추천' },
 ]
```

```diff
       <header className="app__header">
-        <h1 className="app__title">NIKKE Deck Builder</h1>
-        <p className="app__subtitle">
-          Sync your roster from blablalink, then have the engine build decks
-          from it.
-        </p>
-        <p className="app__note">
-          All Nikkes are simulated wearing a Resilience Cube Lv.15.
-        </p>
+        <h1 className="app__title">NIKKE 덱 빌더</h1>
+        <p className="app__subtitle">
+          blablalink에서 로스터를 동기화하면 엔진이 덱을 구성해줘요.
+        </p>
+        <p className="app__note">
+          모든 니케가 Resilience 큐브 Lv.15를 착용한 것으로 계산합니다.
+        </p>
       </header>
```

```diff
-          <div className="tabs" role="tablist" aria-label="Sections">
+          <div className="tabs" role="tablist" aria-label="섹션">
```

```diff
           <div className="empty">
             <p className="empty__text">
-              No synced account yet. Sync from blablalink above to get started.
+              아직 동기화된 계정이 없어요. 위에서 blablalink 동기화를
+              시작해보세요.
             </p>
           </div>
```

```diff
       {activeProfile !== null && (
         <footer className="app__footer">
-          {validRoster.length} of {drafts.length}{' '}
-          {drafts.length === 1 ? 'Nikke' : 'Nikkes'} ready
+          니케 {validRoster.length}/{drafts.length}기 준비 완료
         </footer>
       )}
```

- [ ] **Step 2: Run test to see the expected failures**

Run: `npx vitest run src/App.test.tsx`
Expected: FAIL — the Resilience Cube regex, the "no synced account" regex, the `'Recommend decks'` heading, and the `'Roster'`/`'Recommend'` tab-name queries no longer match

- [ ] **Step 3: Update App.test.tsx**

```diff
-    expect(screen.getByText(/Resilience Cube Lv\.15/i)).toBeInTheDocument()
+    expect(screen.getByText(/Resilience 큐브 Lv\.15/i)).toBeInTheDocument()
```

```diff
-    expect(screen.getByText(/no synced account yet/i)).toBeInTheDocument()
+    expect(screen.getByText(/동기화된 계정이 없어요/i)).toBeInTheDocument()
```

```diff
-    expect(screen.queryByRole('heading', { name: 'Recommend decks' })).not.toBeInTheDocument()
+    expect(screen.queryByRole('heading', { name: '덱 추천' })).not.toBeInTheDocument()
```
(this `queryByRole('heading', { name: 'Recommend decks' })` / `getByRole('heading', { name: 'Recommend decks' })` pattern occurs 3 times in the file — update every occurrence to `'덱 추천'`, keeping `query`/`get` as they already are)

```diff
-    await user.click(screen.getByRole('tab', { name: 'Recommend' }))
+    await user.click(screen.getByRole('tab', { name: '추천' }))
```
(occurs 3 times — update every occurrence)

```diff
-    await user.selectOptions(screen.getByLabelText('Account'), '부계')
+    await user.selectOptions(screen.getByLabelText('계정'), '부계')
```
(occurs twice — update both)

```diff
-    await user.click(screen.getByRole('tab', { name: 'Roster' }))
+    await user.click(screen.getByRole('tab', { name: '로스터' }))
```

```diff
-    await user.click(screen.getByLabelText(/raid allocation/i))
+    await user.click(screen.getByLabelText(/레이드 배분/i))
```
(occurs 3 times — update every occurrence)

```diff
-    await user.click(screen.getByRole('button', { name: /allocate raid decks/i }))
+    await user.click(screen.getByRole('button', { name: /레이드 덱 배분/i }))
```
(occurs twice — update both)

```diff
-    expect(await screen.findByRole('status')).toHaveTextContent(/1–2 minutes/)
+    expect(await screen.findByRole('status')).toHaveTextContent(/1~2분/)
```
(occurs twice — update both)

```diff
-    expect(screen.getByLabelText(/single deck/i)).toBeChecked()
+    expect(screen.getByLabelText(/단일 덱/i)).toBeChecked()
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npx vitest run src/App.test.tsx`
Expected: PASS (all tests in the file)

- [ ] **Step 5: Commit**

```bash
git add frontend/src/App.tsx frontend/src/App.test.tsx
git commit -m "Localize App shell to Korean"
```

---

## Task 11: Hook and API fallback error messages

**Files:**
- Modify: `frontend/src/hooks/useAsyncRequestStatus.ts`
- Modify: `frontend/src/hooks/useRecommendRaid.ts`
- Modify: `frontend/src/hooks/useSupportedUnits.ts`
- Modify: `frontend/src/api/recommendApiError.ts`
- Modify: `frontend/src/api/assembleRosterApiError.ts`
- Test: `frontend/src/hooks/useRecommendRaid.test.ts`
- Test: `frontend/src/hooks/useSupportedUnits.test.ts`
- Test: `frontend/src/api/recommendApiError.test.ts`
- Test: `frontend/src/api/assembleRosterApiError.test.ts`
- Test: `frontend/src/hooks/useAsyncRequestStatus.test.ts` (no assertion touches the changed default — confirm it still passes unmodified)

- [ ] **Step 1: Edit the five production files**

`useAsyncRequestStatus.ts`:
```diff
-const DEFAULT_FALLBACK_ERROR_MESSAGE = 'Failed to fetch deck recommendations.'
+const DEFAULT_FALLBACK_ERROR_MESSAGE = '덱 추천을 가져오지 못했어요.'
```

`useRecommendRaid.ts`:
```diff
-const FALLBACK_ERROR_MESSAGE = 'Failed to fetch raid deck allocation.'
+const FALLBACK_ERROR_MESSAGE = '레이드 덱 배분을 가져오지 못했어요.'
```

`useSupportedUnits.ts`:
```diff
-const FALLBACK_ERROR_MESSAGE = 'Failed to load supported units.'
+const FALLBACK_ERROR_MESSAGE = '지원 유닛 목록을 불러오지 못했어요.'
```

`recommendApiError.ts`:
```diff
   if (err.status === 422) {
     return (
       detailMessage ??
-      'The roster or boss profile is invalid for a deck recommendation.'
+      '로스터 또는 보스 설정이 덱 추천에 유효하지 않아요.'
     )
   }
-  return detailMessage ?? `Deck recommendation request failed (${err.status}).`
+  return detailMessage ?? `덱 추천 요청이 실패했어요 (${err.status}).`
```

`assembleRosterApiError.ts`:
```diff
   if (err.status === 422) {
-    return detailMessage ?? 'The blablalink payload was not in the expected shape.'
+    return detailMessage ?? 'blablalink 응답 형식이 예상과 달라요.'
   }
-  return detailMessage ?? `Roster sync failed (${err.status}).`
+  return detailMessage ?? `로스터 동기화가 실패했어요 (${err.status}).`
```

- [ ] **Step 2: Run tests to see the expected failures**

Run: `npx vitest run src/hooks/useRecommendRaid.test.ts src/hooks/useSupportedUnits.test.ts src/api/recommendApiError.test.ts src/api/assembleRosterApiError.test.ts src/hooks/useAsyncRequestStatus.test.ts`
Expected: FAIL in the first four files (they assert exact fallback text); PASS unmodified in `useAsyncRequestStatus.test.ts` (it only ever passes its own custom fallback string, e.g. `'could not fetch'`, never the default)

- [ ] **Step 3: Update useRecommendRaid.test.ts**

```diff
-    expect(result.current.error).toBe('Failed to fetch raid deck allocation.')
+    expect(result.current.error).toBe('레이드 덱 배분을 가져오지 못했어요.')
```

- [ ] **Step 4: Update useSupportedUnits.test.ts**

```diff
-    expect(result.current.error).toBe('Failed to load supported units.')
+    expect(result.current.error).toBe('지원 유닛 목록을 불러오지 못했어요.')
```

- [ ] **Step 5: Update recommendApiError.test.ts**

```diff
-    expect(describeRecommendApiError(err)).toBe(
-      'The roster or boss profile is invalid for a deck recommendation.',
-    )
+    expect(describeRecommendApiError(err)).toBe(
+      '로스터 또는 보스 설정이 덱 추천에 유효하지 않아요.',
+    )
```

```diff
-    expect(describeRecommendApiError(err)).toBe('Deck recommendation request failed (500).')
+    expect(describeRecommendApiError(err)).toBe('덱 추천 요청이 실패했어요 (500).')
```

- [ ] **Step 6: Update assembleRosterApiError.test.ts**

```diff
-    expect(describeAssembleRosterApiError(err)).toBe(
-      'The blablalink payload was not in the expected shape.',
-    )
+    expect(describeAssembleRosterApiError(err)).toBe(
+      'blablalink 응답 형식이 예상과 달라요.',
+    )
```

```diff
-    expect(describeAssembleRosterApiError(err)).toBe('Roster sync failed (500).')
+    expect(describeAssembleRosterApiError(err)).toBe('로스터 동기화가 실패했어요 (500).')
```

- [ ] **Step 7: Run tests to verify they pass**

Run: `npx vitest run src/hooks/useRecommendRaid.test.ts src/hooks/useSupportedUnits.test.ts src/api/recommendApiError.test.ts src/api/assembleRosterApiError.test.ts src/hooks/useAsyncRequestStatus.test.ts`
Expected: PASS (all five files)

- [ ] **Step 8: Commit**

```bash
git add frontend/src/hooks/useAsyncRequestStatus.ts frontend/src/hooks/useRecommendRaid.ts frontend/src/hooks/useSupportedUnits.ts frontend/src/api/recommendApiError.ts frontend/src/api/assembleRosterApiError.ts frontend/src/hooks/useRecommendRaid.test.ts frontend/src/hooks/useSupportedUnits.test.ts frontend/src/api/recommendApiError.test.ts frontend/src/api/assembleRosterApiError.test.ts
git commit -m "Localize hook and API fallback error messages to Korean"
```

---

## Task 12: lib/rosterImport.ts + lib/shareUrl.ts

**Files:**
- Modify: `frontend/src/lib/rosterImport.ts`
- Modify: `frontend/src/lib/shareUrl.ts`
- Test: `frontend/src/lib/rosterImport.test.ts` (no assertion touches the changed prefixes — confirm it still passes unmodified)
- Test: `frontend/src/lib/shareUrl.test.ts`

- [ ] **Step 1: Edit rosterImport.ts**

```diff
-    throw new Error('Not a collector roster: missing "units".')
+    throw new Error('수집기 로스터 형식이 아니에요: "units" 필드가 없어요.')
```

```diff
-      warnings.push('unit missing name_en/raid400')
+      warnings.push('유닛에 name_en/raid400이 없어요')
```

```diff
-    warnings.push(
-      `${unsupported.length} owned units not yet supported (excluded from ` +
-        `recommendation): ${unsupported.join(', ')}`,
-    )
+    warnings.push(
+      `보유 유닛 중 ${unsupported.length}기가 아직 미지원이라 추천에서 ` +
+        `제외돼요: ${unsupported.join(', ')}`,
+    )
```

```diff
-    warnings.push(
-      `${data.unmeasured.length} owned units left out — their level-400 stats ` +
-        `were never measured: ` +
-        data.unmeasured.map((u) => `${u.name_en} (${u.reason})`).join('; '),
-    )
+    warnings.push(
+      `보유 유닛 중 ${data.unmeasured.length}기가 제외됐어요 — 레벨 400 ` +
+        `스탯이 측정된 적이 없어요: ` +
+        data.unmeasured.map((u) => `${u.name_en} (${u.reason})`).join('; '),
+    )
```

- [ ] **Step 2: Edit shareUrl.ts**

```diff
-  if (!uid) throw new Error('Not a ShiftyPad share URL: no uid parameter.')
+  if (!uid) throw new Error('ShiftyPad 공유 URL이 아니에요: uid 파라미터가 없어요.')
```

```diff
-    throw new Error('Not a ShiftyPad share URL: uid is not base64.')
+    throw new Error('ShiftyPad 공유 URL이 아니에요: uid가 base64 형식이 아니에요.')
```

```diff
-  if (!OPEN_ID.test(openId)) {
-    throw new Error('Not a ShiftyPad share URL: no open id inside uid.')
-  }
+  if (!OPEN_ID.test(openId)) {
+    throw new Error('ShiftyPad 공유 URL이 아니에요: uid 안에 open id가 없어요.')
+  }
```

- [ ] **Step 3: Run tests to see the expected result**

Run: `npx vitest run src/lib/rosterImport.test.ts src/lib/shareUrl.test.ts`
Expected: `rosterImport.test.ts` PASSes unmodified — it only asserts `toThrow(/units/)` (still matches the quoted `"units"` field name) and `toContain('Soline')`/`toContain('Rei')`/`toContain('never measured')` (all substrings of *data* values, not the translated prefix). `shareUrl.test.ts` FAILs — its `toThrow(/share URL/i)` assertions no longer match.

- [ ] **Step 4: Update shareUrl.test.ts**

```diff
-  it('uid가 없으면 거부한다', () => {
-    expect(() => parseShareUrl('https://www.blablalink.com/shiftyspad'))
-      .toThrow(/share URL/i)
-  })
+  it('uid가 없으면 거부한다', () => {
+    expect(() => parseShareUrl('https://www.blablalink.com/shiftyspad'))
+      .toThrow(/공유 URL/i)
+  })
```

```diff
-  it('디코드 결과가 예상 형태가 아니면 거부한다', () => {
-    expect(() => parseShareUrl(`https://www.blablalink.com/shiftyspad?uid=${btoa('junk')}`))
-      .toThrow(/share URL/i)
-  })
+  it('디코드 결과가 예상 형태가 아니면 거부한다', () => {
+    expect(() => parseShareUrl(`https://www.blablalink.com/shiftyspad?uid=${btoa('junk')}`))
+      .toThrow(/공유 URL/i)
+  })
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `npx vitest run src/lib/rosterImport.test.ts src/lib/shareUrl.test.ts`
Expected: PASS (both files)

- [ ] **Step 6: Commit**

```bash
git add frontend/src/lib/rosterImport.ts frontend/src/lib/shareUrl.ts frontend/src/lib/shareUrl.test.ts
git commit -m "Localize rosterImport and shareUrl error messages to Korean"
```

---

## Task 13: types/bossProfileDraft.ts

**Files:**
- Modify: `frontend/src/types/bossProfileDraft.ts`
- Test: `frontend/src/types/bossProfileDraft.test.ts`

- [ ] **Step 1: Edit bossProfileDraft.ts**

```diff
 const parseFloatField = (raw: string, bounds: { min: number }): ParsedNumber => {
   const trimmed = raw.trim()
-  if (trimmed === '') return { error: 'Required' }
+  if (trimmed === '') return { error: '필수 입력이에요' }
   const value = Number(trimmed)
-  if (!Number.isFinite(value)) return { error: 'Must be a number' }
-  if (value < bounds.min) return { error: `Must be ≥ ${bounds.min}` }
+  if (!Number.isFinite(value)) return { error: '숫자를 입력하세요' }
+  if (value < bounds.min) return { error: `${bounds.min} 이상이어야 해요` }
   return { value }
 }
```

```diff
   const fightDuration = parseFloatField(draft.fight_duration, { min: 0 })
   if (fightDuration.error) errors.fight_duration = fightDuration.error
-  else if (fightDuration.value === 0) errors.fight_duration = 'Must be > 0'
+  else if (fightDuration.value === 0) errors.fight_duration = '0보다 커야 해요'
```

- [ ] **Step 2: Run test to see the expected failures**

Run: `npx vitest run src/types/bossProfileDraft.test.ts`
Expected: FAIL — several `.errors.*` assertions expect the old English strings

- [ ] **Step 3: Update bossProfileDraft.test.ts**

```diff
-    expect(errors.enemy_def).toBe('Must be ≥ 0')
+    expect(errors.enemy_def).toBe('0 이상이어야 해요')
```

```diff
-    ).toBe('Must be > 0')
+    ).toBe('0보다 커야 해요')
```

```diff
-    ).toBe('Must be ≥ 0')
+    ).toBe('0 이상이어야 해요')
```

```diff
-    expect(validateBossProfileDraft(draft).errors.enemy_def).toBe('Must be a number')
+    expect(validateBossProfileDraft(draft).errors.enemy_def).toBe('숫자를 입력하세요')
```

```diff
-    expect(validateBossProfileDraft(draft).errors.fight_duration).toBe('Required')
+    expect(validateBossProfileDraft(draft).errors.fight_duration).toBe('필수 입력이에요')
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npx vitest run src/types/bossProfileDraft.test.ts`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/src/types/bossProfileDraft.ts frontend/src/types/bossProfileDraft.test.ts
git commit -m "Localize bossProfileDraft validation errors to Korean"
```

---

## Task 14: types/nikkeDraft.ts (dead-code validation errors)

Not rendered by any current UI (no NikkeDraft edit form exists — the roster is sync-only), but translating it now avoids English leaking back in if an edit form is ever wired up later. Same translation vocabulary as Task 13.

**Files:**
- Modify: `frontend/src/types/nikkeDraft.ts`
- Test: `frontend/src/types/nikkeDraft.test.ts`

- [ ] **Step 1: Edit nikkeDraft.ts**

```diff
 const parseIntField = (
   raw: string,
   bounds: { min: number; max?: number },
 ): ParsedNumber => {
   const trimmed = raw.trim()
-  if (trimmed === '') return { error: 'Required' }
-  if (!/^-?\d+$/.test(trimmed)) return { error: 'Must be a whole number' }
+  if (trimmed === '') return { error: '필수 입력이에요' }
+  if (!/^-?\d+$/.test(trimmed)) return { error: '정수를 입력하세요' }
   const value = Number(trimmed)
-  if (value < bounds.min) return { error: `Must be ≥ ${bounds.min}` }
+  if (value < bounds.min) return { error: `${bounds.min} 이상이어야 해요` }
   if (bounds.max !== undefined && value > bounds.max)
-    return { error: `Must be ≤ ${bounds.max}` }
+    return { error: `${bounds.max} 이하여야 해요` }
   return { value }
 }
```

```diff
 const parseFloatField = (
   raw: string,
   bounds: { min: number },
 ): ParsedNumber => {
   const trimmed = raw.trim()
-  if (trimmed === '') return { error: 'Required' }
+  if (trimmed === '') return { error: '필수 입력이에요' }
   const value = Number(trimmed)
-  if (!Number.isFinite(value)) return { error: 'Must be a number' }
-  if (value < bounds.min) return { error: `Must be ≥ ${bounds.min}` }
+  if (!Number.isFinite(value)) return { error: '숫자를 입력하세요' }
+  if (value < bounds.min) return { error: `${bounds.min} 이상이어야 해요` }
   return { value }
 }
```

```diff
-  if (draft.character_slug.trim() === '') errors.character_slug = 'Required'
+  if (draft.character_slug.trim() === '') errors.character_slug = '필수 입력이에요'
```

```diff
     const name = row.name.trim()
-    if (name === '') rowErrors.name = 'Required'
+    if (name === '') rowErrors.name = '필수 입력이에요'
```

- [ ] **Step 2: Run test to see the expected failures**

Run: `npx vitest run src/types/nikkeDraft.test.ts`
Expected: FAIL — every `.errors.*` assertion in the file expects the old English strings

- [ ] **Step 3: Update nikkeDraft.test.ts**

```diff
-    expect(errors.character_slug).toBe('Required')
-    expect(errors.level).toBe('Required')
-    expect(errors.hp).toBe('Required')
-    expect(errors.atk).toBe('Required')
-    expect(errors.def_).toBe('Required')
-    expect(errors.skill_levels).toEqual({
-      skill1: 'Required',
-      skill2: 'Required',
-      burst: 'Required',
-    })
+    expect(errors.character_slug).toBe('필수 입력이에요')
+    expect(errors.level).toBe('필수 입력이에요')
+    expect(errors.hp).toBe('필수 입력이에요')
+    expect(errors.atk).toBe('필수 입력이에요')
+    expect(errors.def_).toBe('필수 입력이에요')
+    expect(errors.skill_levels).toEqual({
+      skill1: '필수 입력이에요',
+      skill2: '필수 입력이에요',
+      burst: '필수 입력이에요',
+    })
```

```diff
-    expect(errors.level).toBe('Must be ≥ 1')
+    expect(errors.level).toBe('1 이상이어야 해요')
```

```diff
-    expect(validateDraft({ ...validDraft(), level: '10.5' }).errors.level).toBe(
-      'Must be a whole number',
-    )
+    expect(validateDraft({ ...validDraft(), level: '10.5' }).errors.level).toBe(
+      '정수를 입력하세요',
+    )
```

```diff
-    expect(validateDraft({ ...validDraft(), hp: '-1' }).errors.hp).toBe('Must be ≥ 0')
+    expect(validateDraft({ ...validDraft(), hp: '-1' }).errors.hp).toBe('0 이상이어야 해요')
```

```diff
-    expect(validateDraft({ ...validDraft(), atk: 'abc' }).errors.atk).toBe(
-      'Must be a number',
-    )
+    expect(validateDraft({ ...validDraft(), atk: 'abc' }).errors.atk).toBe(
+      '숫자를 입력하세요',
+    )
```

```diff
-    expect(low.errors.skill_levels).toEqual({ skill1: 'Must be ≥ 1' })
+    expect(low.errors.skill_levels).toEqual({ skill1: '1 이상이어야 해요' })
```

```diff
-    expect(high.errors.skill_levels).toEqual({ burst: 'Must be ≤ 10' })
+    expect(high.errors.skill_levels).toEqual({ burst: '10 이하여야 해요' })
```

```diff
-    expect(errors.overload_options?.[bad.id]).toEqual({
-      name: 'Required',
-      value: 'Must be a number',
-    })
+    expect(errors.overload_options?.[bad.id]).toEqual({
+      name: '필수 입력이에요',
+      value: '숫자를 입력하세요',
+    })
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npx vitest run src/types/nikkeDraft.test.ts`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/src/types/nikkeDraft.ts frontend/src/types/nikkeDraft.test.ts
git commit -m "Localize nikkeDraft validation errors to Korean"
```

---

## Task 15: Full-suite verification

**Files:** none (verification only)

- [ ] **Step 1: Type-check the whole frontend**

Run: `npx tsc -b --noEmit`
Expected: no errors

- [ ] **Step 2: Run the full test suite**

Run: `npm test -- --run`
Expected: **289 passed** (same count as the pre-change baseline — this task changed string content only, never added or removed a test), 0 failed

- [ ] **Step 3: Build**

Run: `npm run build`
Expected: clean build, no errors

- [ ] **Step 4: Manual spot-check (optional but recommended)**

Start both dev servers (`uvicorn app.api:app --reload` in `backend/`, `npm run dev` in `frontend/`) and click through the roster tab, sync panel, and all three recommend modes (single/raid/draft) to confirm the Korean text reads naturally in context — a mechanical find-replace can produce grammatically-off phrasing that only shows up rendered in the actual layout.

- [ ] **Step 5: Update docs**

Add a line to `docs/roadmap.md`'s recent-progress log noting this work landed (date, test count, brief summary — follow the existing log-entry style at the top of the file). Use the `/document` skill (docs-keeper subagent) for this rather than hand-editing, per project convention.

- [ ] **Step 6: Final commit (if Step 5 produced changes not already committed by docs-keeper)**

```bash
git add docs/roadmap.md
git commit -m "Record UI chrome Korean localization completion in roadmap"
```
