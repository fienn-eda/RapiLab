# 니케 검색 · 정렬 · 필터 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 로스터 탭과 추천 탭의 유닛 그리드에 이름 검색 · 속성/버스트 필터 · 이름/오버로드 정렬을 붙이고, 로스터 탭에 B1/B2/B3 분류를 신설하며, 작열 속성색을 `#dd3333`으로 바꾼다.

**Architecture:** 필터·정렬 규칙은 `lib/unitFilter.ts`의 순수 함수 하나에 모으고, 두 화면은 자기 데이터 모양(`NikkeDraft`의 문자열 값 / `UserNikkeState`의 숫자 값)을 `UnitFacets`로 환원하는 접근자만 넘긴다. 툴바 `UnitFilterBar`는 controlled — 상태는 각 그리드가 `useState`로 소유한다. 필터는 **그리는 것만** 바꾼다: 추천 탭의 탐색 풀·요청 payload는 손대지 않는다.

**Tech Stack:** React 19 · TypeScript · Vite · Vitest + @testing-library/react · 디자인 토큰 기반 순수 CSS

## Global Constraints

- 설계 스펙: `docs/superpowers/specs/2026-07-28-roster-search-filter-design.md`. 모든 결정의 근거는 여기 있다.
- **기준선: 프론트 `301 passed / 38 files`** (2026-07-28 트렁크 `29c65ff`에서 실측). 이 계획이 끝나면 **`347 passed / 40 files`**가 된다(태스크별 누적: 317 → 332 → 340 → 347 → 347).
- 검증 명령은 항상 `frontend/` 디렉터리에서: `npx vitest run`, `npx tsc -b`.
- **UI 문구는 전부 한국어**, "-어요/-예요" 어미. i18n 라이브러리는 쓰지 않는다(기존 결정).
- 속성 한글 표기는 반드시 `lib/elementName.ts`의 `elementLabel()`을 통한다 — 작열·수냉·풍압·철갑·전격을 다시 적지 않는다.
- 오버로드 축약명(`우코`·`공`·`장탄`·`차속`·`크댐`·`크확`·`차댐`)과 그 표시 순서는 **단일 출처**에서만 나온다. Task 1이 그것을 `lib/overload.ts`로 옮긴다.
- **필터는 `excludedSlugs` / `effectiveRoster` / `hashRecommendInputs` / `poolTotal` / `poolIncluded` / 요청 payload 중 무엇도 바꾸지 않는다.** Task 3이 이것을 회귀 테스트로 고정한다.
- 새 CSS 블록에 `display`를 쓰면서 `hidden` 속성을 함께 쓸 일이 생기면 `[hidden] { display: none; }`을 같이 적어야 한다(`.panel[hidden]` 선례). 이 계획에는 해당 조합이 없다.
- Vitest는 `css: false`로 돈다 — CSS 값은 테스트로 검증할 수 없다. 레이아웃/색상은 실제 앱에서 눈으로 본다.
- 커밋은 태스크마다. 커밋 메시지 본문은 **왜**를 적는다(무엇을 바꿨는지는 diff가 말한다).

---

### Task 1: 필터·정렬 순수 로직

**Files:**
- Create: `frontend/src/lib/overload.ts`
- Create: `frontend/src/lib/unitFilter.ts`
- Create: `frontend/src/lib/unitFilter.test.ts`
- Modify: `frontend/src/types/supportedUnit.ts` (`BurstTier` 타입 · `BURST_TIERS` 상수 신설)
- Modify: `frontend/src/components/InvestmentSummary.tsx:43-79` (오버로드 이름 로직을 `lib/overload.ts`에서 가져오도록)
- Modify: `frontend/src/components/InvestmentSummary.test.ts:2` (import 경로만)
- Modify: `frontend/src/components/UnitPalette.tsx:54` (지역 `BURST_TIERS` 삭제, 타입에서 import)

**Interfaces:**
- Consumes: 없음 (첫 태스크)
- Produces:
  - `lib/overload.ts` — `OVERLOAD_KEYS: readonly OverloadKey[]`, `type OverloadKey`, `abbreviateOverload(name: string): string`, `sortOverload<T extends {name: string}>(options: T[]): T[]`
  - `lib/unitFilter.ts` — `type SortKey = 'name' | OverloadKey`, `interface UnitFilterState`, `EMPTY_FILTER: UnitFilterState`, `isFiltering(state): boolean`, `interface UnitFacets`, `filterAndSort<T>(items: T[], facets: (item: T) => UnitFacets, state: UnitFilterState): T[]`
  - `types/supportedUnit.ts` — `type BurstTier = 1 | 2 | 3`, `BURST_TIERS: readonly BurstTier[]`

- [ ] **Step 1: `BurstTier`를 타입 모듈로 올린다**

`frontend/src/types/supportedUnit.ts`의 `NikkeElement` 선언 바로 아래에 추가:

```ts
export type BurstTier = 1 | 2 | 3

/** 화면이 버스트 그룹을 그리는 순서. 팔레트의 지역 상수였는데, 로스터 그리드도
 * 같은 분류를 그리게 되어 한 곳에서만 정의한다. */
export const BURST_TIERS: readonly BurstTier[] = [1, 2, 3]
```

같은 파일에서 `burst_tier: 1 | 2 | 3`와 `burstTier: 1 | 2 | 3` 두 곳을 `BurstTier`로 교체한다(동작 변화 없음, 이름만 붙인다).

- [ ] **Step 2: 오버로드 이름 로직을 `lib/overload.ts`로 옮긴다**

`frontend/src/lib/overload.ts`를 새로 만들고, `InvestmentSummary.tsx:43-79`의 `ABBREVIATIONS` · `abbreviateOverload` · `DISPLAY_ORDER` · `sortOverload`를 **주석까지 그대로** 옮긴다. 옮기면서 `DISPLAY_ORDER`를 `OVERLOAD_KEYS`로 승격한다:

```ts
// 오버로드 옵션의 이름 규칙. 표시(오버로드 줄)와 정렬(필터 툴바)이 같은 목록을
// 봐야 하므로 컴포넌트가 아니라 lib에 둔다.

// Overload names are long enough to set the width of anything they sit in
// ("우월코드 대미지 증가"), and there are only seven of them, so the player
// reads them as symbols rather than sentences. Abbreviate to the forms used at
// the table (Fienn, 2026-07-25). The trailing "증가" is dropped first: every
// type carries it, so it distinguishes nothing.
const ABBREVIATIONS: Record<string, string> = {
  '우월코드 대미지': '우코',
  '최대 장탄 수': '장탄',
  공격력: '공',
  '차지 대미지': '차댐',
  '차지 속도': '차속',
  '크리티컬 확률': '크확',
  '크리티컬 대미지': '크댐',
}

// The order Fienn reads them in (2026-07-25), not the order blablalink happens
// to return. A fixed order is what lets two units be compared down the column
// instead of line by line - and it doubles as the order of the sort menu.
export const OVERLOAD_KEYS = ['우코', '공', '장탄', '차속', '크댐', '크확', '차댐'] as const

export type OverloadKey = (typeof OVERLOAD_KEYS)[number]

/** Short label for an overload line. An unrecognised name (a new effect type,
 * or another locale) keeps its full text rather than being mangled. */
export const abbreviateOverload = (name: string): string => {
  const stripped = name.replace(/\s*증가$/, '')
  return ABBREVIATIONS[stripped] ?? stripped
}

/** Sorts overload lines into OVERLOAD_KEYS order. An unrecognised effect sorts
 * after all the known ones, keeping its incoming order among its peers - a new
 * type should appear, not disappear or displace a known one. */
export const sortOverload = <T extends { name: string }>(options: T[]): T[] => {
  const rank = (option: T) => {
    const index = OVERLOAD_KEYS.indexOf(abbreviateOverload(option.name) as OverloadKey)
    return index === -1 ? OVERLOAD_KEYS.length : index
  }
  return [...options].sort((a, b) => rank(a) - rank(b))
}
```

그 다음 `InvestmentSummary.tsx`에서 그 네 덩어리를 지우고 맨 위에 import를 넣는다:

```ts
import { abbreviateOverload, sortOverload } from '../lib/overload'
```

`InvestmentSummary.test.ts:2`의 import를 바꾼다:

```ts
import { abbreviateOverload, sortOverload } from '../lib/overload'
```

- [ ] **Step 3: 이동이 아무것도 깨지 않았는지 확인**

Run: `cd frontend && npx vitest run src/components/InvestmentSummary.test.ts`
Expected: PASS (기존 테스트 그대로, 301의 일부)

- [ ] **Step 4: 실패하는 테스트를 쓴다**

`frontend/src/lib/unitFilter.test.ts`:

```ts
import { describe, it, expect } from 'vitest'
import {
  EMPTY_FILTER,
  filterAndSort,
  isFiltering,
  type UnitFacets,
  type UnitFilterState,
} from './unitFilter'

interface Row {
  name: string
  element: UnitFacets['element']
  burstTier: UnitFacets['burstTier']
  overload: { name: string; value: number | string }[]
}

const facets = (row: Row): UnitFacets => row

const ROWS: Row[] = [
  { name: '홍련', element: 'Fire', burstTier: 3, overload: [{ name: '공격력 증가', value: 40.91 }] },
  { name: '라피', element: 'Water', burstTier: 1, overload: [{ name: '공격력 증가', value: 12.5 }] },
  { name: '네온', element: 'Fire', burstTier: 1, overload: [{ name: '우월코드 대미지 증가', value: 99.82 }] },
  { name: '앨리스', element: 'Wind', burstTier: 3, overload: [] },
]

const names = (rows: Row[]) => rows.map((row) => row.name)
const run = (state: Partial<UnitFilterState>) =>
  names(filterAndSort(ROWS, facets, { ...EMPTY_FILTER, ...state }))

describe('filterAndSort', () => {
  it('keeps every unit when nothing is filtered', () => {
    expect(run({}).sort()).toEqual(['네온', '라피', '앨리스', '홍련'].sort())
  })

  // The default sort is by name, so an unfiltered grid is 가나다순 rather than
  // whatever order the backend happened to return.
  it('sorts by name in Korean collation order by default', () => {
    expect(run({})).toEqual(['네온', '라피', '앨리스', '홍련'])
  })

  it('reverses the name order when the direction is descending', () => {
    expect(run({ sortDir: 'desc' })).toEqual(['홍련', '앨리스', '라피', '네온'])
  })

  it('matches a name by substring, ignoring case and surrounding space', () => {
    expect(run({ query: '  련 ' })).toEqual(['홍련'])
  })

  it('finds nothing for a query no name contains', () => {
    expect(run({ query: '없는이름' })).toEqual([])
  })

  it('keeps only the chosen elements, treating an empty list as no filter', () => {
    expect(run({ elements: ['Fire'] })).toEqual(['네온', '홍련'])
    expect(run({ elements: ['Fire', 'Wind'] })).toEqual(['네온', '앨리스', '홍련'])
  })

  it('keeps only the chosen burst tiers', () => {
    expect(run({ burstTiers: [1] })).toEqual(['네온', '라피'])
  })

  // The two facets narrow together, not alternately.
  it('intersects the element and burst filters', () => {
    expect(run({ elements: ['Fire'], burstTiers: [1] })).toEqual(['네온'])
  })

  it('sorts by one overload stat, highest first when descending', () => {
    expect(run({ sortKey: '공', sortDir: 'desc' })).toEqual(['홍련', '라피', '네온', '앨리스'])
  })

  // A unit that never rolled the stat contributes 0 of it, so it sorts as the
  // number it is - which is exactly what "which units did I not invest in"
  // asks for in ascending order.
  it('treats a stat the unit never rolled as zero', () => {
    expect(run({ sortKey: '공', sortDir: 'asc' })).toEqual(['네온', '앨리스', '라피', '홍련'])
  })

  // Two units on 0 must not swap places between renders.
  it('breaks a tie by name, in both directions', () => {
    expect(run({ sortKey: '장탄', sortDir: 'desc' })).toEqual(['네온', '라피', '앨리스', '홍련'])
    expect(run({ sortKey: '장탄', sortDir: 'asc' })).toEqual(['네온', '라피', '앨리스', '홍련'])
  })

  it('leaves the caller array untouched', () => {
    const original = [...ROWS]
    filterAndSort(ROWS, facets, { ...EMPTY_FILTER, sortDir: 'desc' })
    expect(ROWS).toEqual(original)
  })
})

describe('isFiltering', () => {
  it('is false for the empty filter', () => {
    expect(isFiltering(EMPTY_FILTER)).toBe(false)
  })

  it('is true once any facet narrows the list', () => {
    expect(isFiltering({ ...EMPTY_FILTER, query: '홍' })).toBe(true)
    expect(isFiltering({ ...EMPTY_FILTER, elements: ['Fire'] })).toBe(true)
    expect(isFiltering({ ...EMPTY_FILTER, burstTiers: [2] })).toBe(true)
  })

  it('ignores whitespace-only search text', () => {
    expect(isFiltering({ ...EMPTY_FILTER, query: '   ' })).toBe(false)
  })

  // Sorting reorders; it never hides. The "N기 중 M기" line and the clear
  // button are about hiding, so a sort choice must not raise them.
  it('is false for a sort choice alone', () => {
    expect(isFiltering({ ...EMPTY_FILTER, sortKey: '우코', sortDir: 'desc' })).toBe(false)
  })
})
```

- [ ] **Step 5: 실패를 확인한다**

Run: `cd frontend && npx vitest run src/lib/unitFilter.test.ts`
Expected: FAIL — `Failed to resolve import "./unitFilter"`

- [ ] **Step 6: 구현한다**

`frontend/src/lib/unitFilter.ts`:

```ts
// Search, filter and sort for a unit grid. Shared by the roster tab and the
// recommend palette, which hold the same units in different shapes.
//
// Pure, and deliberately so: this decides what is DRAWN. The recommend tab's
// candidate pool is a separate concept living in RecommendPanel's
// `excludedSlugs`, and nothing here may touch it - hiding a unit must never
// remove it from the search (see the design spec, decision 5).

import { abbreviateOverload, type OverloadKey } from './overload'
import type { BurstTier, NikkeElement } from '../types/supportedUnit'

export type SortKey = 'name' | OverloadKey

export interface UnitFilterState {
  /** 이름 부분일치. 빈 문자열(과 공백뿐인 문자열) = 조건 없음. */
  query: string
  /** 빈 배열 = 전부 표시. "전체" 항목을 따로 두지 않기 위한 규약. */
  elements: NikkeElement[]
  /** 빈 배열 = 전부 표시. */
  burstTiers: BurstTier[]
  sortKey: SortKey
  sortDir: 'asc' | 'desc'
}

/** 기본 상태. 정렬 기본값이 이름·오름차순이라, 필터를 아무것도 걸지 않아도
 * 그리드는 가나다순으로 그려진다 - 백엔드가 준 순서는 유저에게 의미가 없다. */
export const EMPTY_FILTER: UnitFilterState = {
  query: '',
  elements: [],
  burstTiers: [],
  sortKey: 'name',
  sortDir: 'asc',
}

/** 무언가 숨겨지고 있는가. 정렬은 순서만 바꾸고 아무것도 숨기지 않으므로
 * 여기 포함되지 않는다 - "N기 중 M기 표시 중"과 "필터 해제"를 가르는 값. */
export const isFiltering = (state: UnitFilterState): boolean =>
  state.query.trim() !== '' ||
  state.elements.length > 0 ||
  state.burstTiers.length > 0

/** 필터·정렬이 유닛에서 읽는 것 전부. 호출부가 자기 저장 모양을 이걸로
 * 환원해 넘기므로, 두 화면이 데이터 구조를 통일하지 않고도 규칙을 공유한다. */
export interface UnitFacets {
  name: string
  element: NikkeElement
  burstTier: BurstTier
  overload: { name: string; value: number | string }[]
}

/** 한 오버로드 옵션의 4부위 합산값. 안 굴렸으면 0 - 실제 기여가 0이므로
 * 특별 취급하지 않고 그 숫자로 줄 세운다. 값이 문자열인 쪽(NikkeDraft)과
 * 숫자인 쪽(UserNikkeState)을 같이 받으므로 Number()로 통일한다. */
const overloadValue = (facets: UnitFacets, key: OverloadKey): number => {
  const line = facets.overload.find((option) => abbreviateOverload(option.name) === key)
  if (line === undefined) return 0
  const value = Number(line.value)
  return Number.isFinite(value) ? value : 0
}

const matches = (facets: UnitFacets, state: UnitFilterState): boolean => {
  const query = state.query.trim().toLowerCase()
  if (query !== '' && !facets.name.toLowerCase().includes(query)) return false
  if (state.elements.length > 0 && !state.elements.includes(facets.element)) return false
  if (state.burstTiers.length > 0 && !state.burstTiers.includes(facets.burstTier)) return false
  return true
}

export function filterAndSort<T>(
  items: T[],
  facets: (item: T) => UnitFacets,
  state: UnitFilterState,
): T[] {
  const kept = items.filter((item) => matches(facets(item), state))
  const sign = state.sortDir === 'asc' ? 1 : -1
  // Always ascending, whichever way the primary sort runs: a tie-break exists
  // to make the order reproducible, and one that flipped with direction would
  // not be.
  const byName = (a: T, b: T) => facets(a).name.localeCompare(facets(b).name, 'ko')

  if (state.sortKey === 'name') return kept.sort((a, b) => sign * byName(a, b))

  const key = state.sortKey
  return kept.sort((a, b) => {
    const diff = overloadValue(facets(a), key) - overloadValue(facets(b), key)
    return diff !== 0 ? sign * diff : byName(a, b)
  })
}
```

`kept`는 `items.filter`가 만든 새 배열이라 그 자리에서 정렬해도 호출부 배열은 안 바뀐다(Step 4의 마지막 테스트가 이것을 잡는다).

- [ ] **Step 7: 통과를 확인한다**

Run: `cd frontend && npx vitest run src/lib/unitFilter.test.ts`
Expected: PASS (16 tests)

- [ ] **Step 8: 팔레트의 지역 상수를 지운다**

`frontend/src/components/UnitPalette.tsx:54`의 `const BURST_TIERS = [1, 2, 3] as const`를 지우고, 같은 파일의 supportedUnit import를 바꾼다:

```ts
import { BURST_TIERS, type SupportedUnit } from '../types/supportedUnit'
```

- [ ] **Step 9: 전체 스위트와 타입을 확인한다**

Run: `cd frontend && npx vitest run && npx tsc -b`
Expected: `317 passed / 39 files`, tsc 무출력

- [ ] **Step 10: 커밋**

```bash
git add frontend/src/lib/overload.ts frontend/src/lib/unitFilter.ts frontend/src/lib/unitFilter.test.ts frontend/src/types/supportedUnit.ts frontend/src/components/InvestmentSummary.tsx frontend/src/components/InvestmentSummary.test.ts frontend/src/components/UnitPalette.tsx
git commit -F - <<'EOF'
Give the two unit grids one filter and sort rule to share

The roster tab and the recommend palette hold the same units in different
shapes, so the rule takes a facets accessor rather than a common type. The
overload naming moved out of the component it lived in because the sort menu
and the chip lines must never disagree about which seven stats exist.
EOF
```

---

### Task 2: 툴바 컴포넌트

**Files:**
- Create: `frontend/src/components/UnitFilterBar.tsx`
- Create: `frontend/src/components/UnitFilterBar.test.tsx`
- Modify: `frontend/src/App.css` (`.roster__unsupported` 블록 앞, 즉 68행 근처에 새 블록 추가)

**Interfaces:**
- Consumes: Task 1의 `EMPTY_FILTER` · `isFiltering` · `UnitFilterState` · `OVERLOAD_KEYS`, 그리고 `BURST_TIERS` · `BurstTier` · `NikkeElement`
- Produces: `UnitFilterBar({ value, onChange, shown, total })` — controlled, 상태 없음

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`frontend/src/components/UnitFilterBar.test.tsx`:

```ts
import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { UnitFilterBar } from './UnitFilterBar'
import { EMPTY_FILTER, type UnitFilterState } from '../lib/unitFilter'

const bar = (value: Partial<UnitFilterState> = {}, counts: { shown?: number; total?: number } = {}) => {
  const onChange = vi.fn()
  render(
    <UnitFilterBar
      value={{ ...EMPTY_FILTER, ...value }}
      onChange={onChange}
      shown={counts.shown ?? 5}
      total={counts.total ?? 5}
    />,
  )
  return onChange
}

describe('UnitFilterBar', () => {
  it('offers every element as a Korean-labelled toggle', () => {
    bar()
    for (const label of ['작열', '수냉', '풍압', '철갑', '전격']) {
      expect(screen.getByRole('button', { name: label })).toHaveAttribute('aria-pressed', 'false')
    }
  })

  it('offers the three burst tiers as toggles', () => {
    bar()
    for (const label of ['B1', 'B2', 'B3']) {
      expect(screen.getByRole('button', { name: label })).toBeInTheDocument()
    }
  })

  it('adds an element to the filter when its chip is pressed', async () => {
    const user = userEvent.setup()
    const onChange = bar()
    await user.click(screen.getByRole('button', { name: '작열' }))
    expect(onChange).toHaveBeenCalledWith({ ...EMPTY_FILTER, elements: ['Fire'] })
  })

  // Pressing a lit chip must clear that one facet value, not the whole filter.
  it('removes an element that is already in the filter', async () => {
    const user = userEvent.setup()
    const onChange = bar({ elements: ['Fire', 'Water'] })
    await user.click(screen.getByRole('button', { name: '작열' }))
    expect(onChange).toHaveBeenCalledWith({ ...EMPTY_FILTER, elements: ['Water'] })
  })

  it('shows a pressed chip for each active element', () => {
    bar({ elements: ['Water'] })
    expect(screen.getByRole('button', { name: '수냉' })).toHaveAttribute('aria-pressed', 'true')
    expect(screen.getByRole('button', { name: '작열' })).toHaveAttribute('aria-pressed', 'false')
  })

  it('toggles a burst tier as a number, not a label', async () => {
    const user = userEvent.setup()
    const onChange = bar()
    await user.click(screen.getByRole('button', { name: 'B2' }))
    expect(onChange).toHaveBeenCalledWith({ ...EMPTY_FILTER, burstTiers: [2] })
  })

  it('reports what was typed into the search box', async () => {
    const user = userEvent.setup()
    const onChange = bar()
    await user.type(screen.getByLabelText('이름 검색'), '홍')
    expect(onChange).toHaveBeenCalledWith({ ...EMPTY_FILTER, query: '홍' })
  })

  it('lists the seven overload stats alongside 이름 in the sort menu', () => {
    bar()
    const sort = screen.getByLabelText('정렬')
    expect([...sort.querySelectorAll('option')].map((o) => o.textContent)).toEqual([
      '이름', '우코', '공', '장탄', '차속', '크댐', '크확', '차댐',
    ])
  })

  it('reports a chosen sort stat', async () => {
    const user = userEvent.setup()
    const onChange = bar()
    await user.selectOptions(screen.getByLabelText('정렬'), '우코')
    expect(onChange).toHaveBeenCalledWith({ ...EMPTY_FILTER, sortKey: '우코' })
  })

  it('reports a chosen sort direction', async () => {
    const user = userEvent.setup()
    const onChange = bar()
    await user.selectOptions(screen.getByLabelText('정렬 방향'), 'desc')
    expect(onChange).toHaveBeenCalledWith({ ...EMPTY_FILTER, sortDir: 'desc' })
  })

  // A hidden unit must never be silently missing: the count is the only thing
  // that explains where the rest of the roster went.
  it('says how many units survived the filter', () => {
    bar({ elements: ['Fire'] }, { shown: 2, total: 70 })
    expect(screen.getByText('70기 중 2기 표시 중')).toBeInTheDocument()
  })

  it('says nothing about counts when nothing is hidden', () => {
    bar({ sortKey: '우코', sortDir: 'desc' })
    expect(screen.queryByText(/표시 중/)).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: '필터 해제' })).not.toBeInTheDocument()
  })

  // Clearing is about hiding, so it leaves the sort choice alone - otherwise
  // "필터 해제" would silently reorder the grid too.
  it('clears the three narrowing facets but keeps the sort', async () => {
    const user = userEvent.setup()
    const onChange = bar({ query: '홍', elements: ['Fire'], burstTiers: [3], sortKey: '우코', sortDir: 'desc' })
    await user.click(screen.getByRole('button', { name: '필터 해제' }))
    expect(onChange).toHaveBeenCalledWith({
      ...EMPTY_FILTER,
      sortKey: '우코',
      sortDir: 'desc',
    })
  })

  it('says so when the filter matched nothing at all', () => {
    bar({ query: '없는이름' }, { shown: 0, total: 70 })
    expect(screen.getByText('조건에 맞는 니케가 없어요.')).toBeInTheDocument()
  })

  // An empty roster is not a filter that matched nothing.
  it('stays quiet when there were no units to begin with', () => {
    bar({ query: '홍' }, { shown: 0, total: 0 })
    expect(screen.queryByText('조건에 맞는 니케가 없어요.')).not.toBeInTheDocument()
  })
})
```

- [ ] **Step 2: 실패를 확인한다**

Run: `cd frontend && npx vitest run src/components/UnitFilterBar.test.tsx`
Expected: FAIL — `Failed to resolve import "./UnitFilterBar"`

- [ ] **Step 3: 구현한다**

`frontend/src/components/UnitFilterBar.tsx`:

```tsx
// The search / filter / sort toolbar over a unit grid. Shared by the roster
// tab and the recommend palette.
//
// Controlled and stateless: the grid that draws the units owns the filter, so
// the two tabs keep independent filters without this component knowing there
// is more than one of it.
//
// It narrows what is DRAWN and nothing else. In the recommend tab the
// candidate pool is a separate toggle on each portrait, and a unit hidden
// here is still in the pool - which is why the count line and the clear
// button are not optional chrome: they are the only thing that explains
// where the rest of the grid went.

import { useId } from 'react'
import { elementLabel } from '../lib/elementName'
import {
  EMPTY_FILTER,
  isFiltering,
  type SortKey,
  type UnitFilterState,
} from '../lib/unitFilter'
import { OVERLOAD_KEYS } from '../lib/overload'
import { BURST_TIERS, type NikkeElement } from '../types/supportedUnit'

// Element order follows the game's own listing, which is also the order the
// element tokens are declared in index.css.
const ELEMENTS: readonly NikkeElement[] = ['Fire', 'Water', 'Wind', 'Iron', 'Electric']

interface UnitFilterBarProps {
  value: UnitFilterState
  onChange: (next: UnitFilterState) => void
  /** 필터를 통과한 개수와 전체 개수. 숨긴 유닛이 있을 때만 쓰인다. */
  shown: number
  total: number
}

/** 다중 선택 축에서 한 값을 켜고 끈다. */
const toggle = <T,>(list: T[], value: T): T[] =>
  list.includes(value) ? list.filter((item) => item !== value) : [...list, value]

export function UnitFilterBar({ value, onChange, shown, total }: UnitFilterBarProps) {
  const searchId = useId()
  const sortId = useId()
  const sortDirId = useId()
  const elementsId = useId()
  const tiersId = useId()
  const filtering = isFiltering(value)

  return (
    <div className="unit-filter">
      <div className="unit-filter__row">
        <label className="unit-filter__label" htmlFor={searchId}>
          이름 검색
        </label>
        <input
          id={searchId}
          type="search"
          className="unit-filter__search"
          placeholder="니케 이름"
          value={value.query}
          onChange={(event) => onChange({ ...value, query: event.target.value })}
        />

        <label className="unit-filter__label" htmlFor={sortId}>
          정렬
        </label>
        <select
          id={sortId}
          className="unit-filter__select"
          value={value.sortKey}
          onChange={(event) => onChange({ ...value, sortKey: event.target.value as SortKey })}
        >
          <option value="name">이름</option>
          {OVERLOAD_KEYS.map((key) => (
            <option key={key} value={key}>
              {key}
            </option>
          ))}
        </select>

        {/* A select rather than an arrow toggle: a button whose label has to
            state both the current direction and the action it performs reads
            wrong whichever of the two it names. */}
        <label className="unit-filter__label" htmlFor={sortDirId}>
          정렬 방향
        </label>
        <select
          id={sortDirId}
          className="unit-filter__select"
          value={value.sortDir}
          onChange={(event) =>
            onChange({ ...value, sortDir: event.target.value as UnitFilterState['sortDir'] })
          }
        >
          <option value="asc">오름차순</option>
          <option value="desc">내림차순</option>
        </select>
      </div>

      <div className="unit-filter__row">
        <span className="unit-filter__label" id={elementsId}>
          속성
        </span>
        <div className="unit-filter__chips" role="group" aria-labelledby={elementsId}>
          {ELEMENTS.map((element) => (
            <button
              key={element}
              type="button"
              className="unit-filter__chip"
              // Tints the lit chip with that element's colour, the same token
              // the portrait borders use.
              data-element={element}
              aria-pressed={value.elements.includes(element)}
              onClick={() => onChange({ ...value, elements: toggle(value.elements, element) })}
            >
              {elementLabel(element)}
            </button>
          ))}
        </div>

        <span className="unit-filter__label" id={tiersId}>
          단계
        </span>
        <div className="unit-filter__chips" role="group" aria-labelledby={tiersId}>
          {BURST_TIERS.map((tier) => (
            <button
              key={tier}
              type="button"
              className="unit-filter__chip"
              aria-pressed={value.burstTiers.includes(tier)}
              onClick={() => onChange({ ...value, burstTiers: toggle(value.burstTiers, tier) })}
            >
              B{tier}
            </button>
          ))}
        </div>
      </div>

      {filtering && (
        <p className="unit-filter__status">
          <span>
            {total}기 중 {shown}기 표시 중
          </span>
          {/* Clears only what hides units. Resetting the sort as well would
              reorder the grid on a button that never said it would. */}
          <button
            type="button"
            className="unit-filter__clear"
            onClick={() =>
              onChange({
                ...value,
                query: EMPTY_FILTER.query,
                elements: EMPTY_FILTER.elements,
                burstTiers: EMPTY_FILTER.burstTiers,
              })
            }
          >
            필터 해제
          </button>
        </p>
      )}

      {filtering && shown === 0 && total > 0 && (
        <p className="unit-filter__empty">조건에 맞는 니케가 없어요.</p>
      )}
    </div>
  )
}
```

- [ ] **Step 4: 통과를 확인한다**

Run: `cd frontend && npx vitest run src/components/UnitFilterBar.test.tsx`
Expected: PASS (15 tests)

- [ ] **Step 5: 스타일을 붙인다**

`frontend/src/App.css`의 `.roster__unsupported` 블록(69행) **앞**에 넣는다:

```css
/* Unit filter toolbar ----------------------------------------------------- */

/* Sits above a unit grid in both tabs. Wraps rather than scrolls: the roster
   tab has the width for one row and the recommend palette does not, and a
   toolbar that scrolls sideways hides the controls it exists to offer. */
.unit-filter {
  display: flex;
  flex-direction: column;
  gap: var(--sp-2);
  padding: var(--sp-2) var(--sp-3);
  border: 1px solid var(--border);
  border-radius: var(--radius);
  background: var(--surface-2);
}

.unit-filter__row {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--sp-1) var(--sp-2);
}

.unit-filter__label {
  font-size: 12px;
  font-weight: 600;
  color: var(--text-muted);
}

.unit-filter__search {
  flex: 1 1 160px;
  min-width: 120px;
  padding: 2px var(--sp-2);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  background: var(--surface);
  color: var(--text);
  font: inherit;
  font-size: 13px;
}

.unit-filter__select {
  padding: 2px var(--sp-1);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  background: var(--surface);
  color: var(--text);
  font: inherit;
  font-size: 13px;
}

.unit-filter__chips {
  display: flex;
  flex-wrap: wrap;
  gap: var(--sp-1);
}

.unit-filter__chip {
  padding: 1px var(--sp-2) 2px;
  border: 1px solid var(--border);
  border-radius: 999px;
  background: transparent;
  color: var(--text-muted);
  font: inherit;
  font-size: 12px;
  cursor: pointer;
}

/* Lit by the same element token the portrait borders use, so "작열" in the
   toolbar and a 작열 unit's edge are recognisably the same colour. */
.unit-filter__chip[aria-pressed='true'] {
  border-color: var(--element, var(--accent));
  color: var(--text);
  background: var(--surface);
}

.unit-filter__chip[data-element='Fire'] {
  --element: var(--el-fire);
}
.unit-filter__chip[data-element='Water'] {
  --element: var(--el-water);
}
.unit-filter__chip[data-element='Wind'] {
  --element: var(--el-wind);
}
.unit-filter__chip[data-element='Iron'] {
  --element: var(--el-iron);
}
.unit-filter__chip[data-element='Electric'] {
  --element: var(--el-electric);
}

.unit-filter__status {
  display: flex;
  align-items: baseline;
  gap: var(--sp-2);
  margin: 0;
  font-size: 12px;
  color: var(--text-muted);
}

.unit-filter__clear {
  padding: 0;
  border: 0;
  background: transparent;
  color: var(--accent);
  font: inherit;
  font-size: 12px;
  text-decoration: underline;
  cursor: pointer;
}

.unit-filter__empty {
  margin: 0;
  font-size: 13px;
  color: var(--text-muted);
}
```

- [ ] **Step 6: 전체 스위트와 타입을 확인한다**

Run: `cd frontend && npx vitest run && npx tsc -b`
Expected: `332 passed / 40 files`, tsc 무출력

- [ ] **Step 7: 커밋**

```bash
git add frontend/src/components/UnitFilterBar.tsx frontend/src/components/UnitFilterBar.test.tsx frontend/src/App.css
git commit -F - <<'EOF'
Add the toolbar the two unit grids will hang their filter on

Stateless and controlled, so each tab keeps its own filter without this
knowing there is more than one of it. The count line and the clear button are
load-bearing rather than chrome: in the recommend tab a hidden unit is still
in the search pool, and nothing else on screen would explain where it went.
EOF
```

---

### Task 3: 추천 탭 배선 + 탐색 풀 불변 회귀

**Files:**
- Modify: `frontend/src/components/UnitPalette.tsx`
- Modify: `frontend/src/components/UnitPalette.test.tsx`
- Modify: `frontend/src/components/RecommendPanel.test.tsx` (회귀 테스트 추가만 — `RecommendPanel.tsx`는 **건드리지 않는다**)

**Interfaces:**
- Consumes: Task 1의 `filterAndSort` · `EMPTY_FILTER` · `UnitFacets` · `UnitFilterState`, Task 2의 `UnitFilterBar`
- Produces: 없음 (`UnitPalette`의 prop 시그니처는 그대로 — 필터는 내부 상태다)

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`frontend/src/components/UnitPalette.test.tsx`의 마지막 `})` 앞에 붙인다:

```tsx
  describe('the filter toolbar', () => {
    const filtered = () =>
      render(
        <UnitPalette
          {...base}
          roster={[
            owned('crown', { overload_options: [{ name: '공격력 증가', value: 10 }] }),
            owned('liter', { overload_options: [{ name: '공격력 증가', value: 50 }] }),
            owned('blanc'),
          ]}
        />,
      )

    it('hides the units a name search does not match', async () => {
      const user = userEvent.setup()
      filtered()
      await user.type(screen.getByLabelText('이름 검색'), 'cro')
      expect(unitButton(/crown 사용/i)).toBeInTheDocument()
      expect(screen.queryByRole('button', { name: /liter 사용/i })).not.toBeInTheDocument()
    })

    it('drops a burst heading once its last unit is filtered away', async () => {
      const user = userEvent.setup()
      filtered()
      await user.click(screen.getByRole('button', { name: '철갑' }))
      expect(screen.getByRole('heading', { name: 'B1' })).toBeInTheDocument()
      expect(screen.queryByRole('heading', { name: 'B2' })).not.toBeInTheDocument()
      expect(screen.queryByRole('heading', { name: 'B3' })).not.toBeInTheDocument()
    })

    // Sorting reorders inside each burst group; it never merges them, because
    // a deck is always built tier by tier.
    it('sorts within a burst group without dissolving the groups', async () => {
      const user = userEvent.setup()
      render(
        <UnitPalette
          {...base}
          roster={[
            owned('crown', { overload_options: [{ name: '공격력 증가', value: 10 }] }),
            owned('anne', { overload_options: [{ name: '공격력 증가', value: 90 }] }),
            owned('liter'),
          ]}
        />,
      )
      await user.selectOptions(screen.getByLabelText('정렬'), '공')
      await user.selectOptions(screen.getByLabelText('정렬 방향'), 'desc')

      expect(screen.getByRole('heading', { name: 'B1' })).toBeInTheDocument()
      expect(screen.getByRole('heading', { name: 'B2' })).toBeInTheDocument()
      const b1 = screen.getByRole('heading', { name: 'B1' }).closest('section')!
      const names = [...b1.querySelectorAll('.palette__name')].map((n) => n.textContent)
      expect(names).toEqual(['Anne', 'Crown'])
    })

    // The load-bearing invariant: the filter narrows the view, and the pool is
    // a separate decision the user made per unit.
    it('keeps a hidden unit excluded, and hands it back on clearing the filter', async () => {
      const user = userEvent.setup()
      render(<UnitPalette {...base} excludedSlugs={['liter']} />)
      await user.click(screen.getByRole('button', { name: '철갑' }))
      expect(screen.queryByRole('button', { name: /liter 사용/i })).not.toBeInTheDocument()

      await user.click(screen.getByRole('button', { name: '필터 해제' }))
      expect(unitButton(/liter 사용/i)).toHaveAttribute('aria-pressed', 'false')
    })

    it('counts against the units it draws, not the whole roster', async () => {
      const user = userEvent.setup()
      filtered()
      await user.click(screen.getByRole('button', { name: '철갑' }))
      expect(screen.getByText('3기 중 1기 표시 중')).toBeInTheDocument()
    })
  })
```

- [ ] **Step 2: 실패를 확인한다**

Run: `cd frontend && npx vitest run src/components/UnitPalette.test.tsx`
Expected: FAIL — `Unable to find a label with the text of: 이름 검색`

- [ ] **Step 3: 팔레트를 배선한다**

`frontend/src/components/UnitPalette.tsx`:

import 블록에 추가:

```ts
import { useState } from 'react'
import { UnitFilterBar } from './UnitFilterBar'
import { EMPTY_FILTER, filterAndSort, type UnitFacets, type UnitFilterState } from '../lib/unitFilter'
```

`const shown = supportedUnits.filter(...)` 바로 아래에 넣는다:

```tsx
  // Owned by the palette rather than by RecommendPanel: nothing outside this
  // component may read the filter, precisely because reading it would invite
  // narrowing the request to match. Mode switching remounts the palette and so
  // resets the filter, which is the accepted cost of keeping it local.
  const [filter, setFilter] = useState<UnitFilterState>(EMPTY_FILTER)

  const facetsFor = (unit: SupportedUnit): UnitFacets => ({
    name: unit.name,
    element: unit.element,
    burstTier: unit.burstTier,
    overload: ownedBySlug.get(unit.slug)!.overload_options,
  })

  // Sorted across the whole palette, then partitioned by tier below - a
  // partition preserves relative order, so each group comes out in sort order
  // without sorting three times.
  const visible = filterAndSort(shown, facetsFor, filter)
```

`return (`의 `<div className="palette">` 바로 안쪽 첫 줄에 툴바를 넣는다:

```tsx
    <div className="palette">
      <UnitFilterBar
        value={filter}
        onChange={setFilter}
        shown={visible.length}
        total={shown.length}
      />
      {BURST_TIERS.map((tier) => {
        const units = visible.filter((unit) => unit.burstTier === tier)
```

즉 기존 `const units = shown.filter(...)`를 `visible.filter(...)`로 한 글자씩 바꾼다. 나머지 렌더링은 그대로다.

- [ ] **Step 4: 통과를 확인한다**

Run: `cd frontend && npx vitest run src/components/UnitPalette.test.tsx`
Expected: PASS

- [ ] **Step 5: 탐색 풀 불변 회귀 테스트를 쓴다**

`frontend/src/components/RecommendPanel.test.tsx`의 마지막 `})` 앞에 붙인다:

```tsx
  // The palette filter narrows what is DRAWN. If it ever narrowed the request
  // too, a player would silently run a one-to-two-minute allocation against a
  // roster they never chose to shrink - and the pool count in the summary
  // would be the only place that said so.
  describe('the palette filter and the search pool', () => {
    // Six, not five: the third test excludes one unit, and MIN_DECK_ROSTER_SIZE
    // is 5 - on a five-unit roster the exclusion would disable Submit and the
    // test would be asserting against a button it never actually pressed.
    const paletteUnits: SupportedUnit[] = [
      { slug: 'a', name: 'Crown', burstTier: 1, element: 'Iron' },
      { slug: 'b', name: 'Anne', burstTier: 1, element: 'Fire' },
      { slug: 'c', name: 'Liter', burstTier: 2, element: 'Water' },
      { slug: 'd', name: 'Blanc', burstTier: 3, element: 'Wind' },
      { slug: 'e', name: 'Noir', burstTier: 3, element: 'Electric' },
      { slug: 'f', name: 'Dorothy', burstTier: 2, element: 'Iron' },
    ]
    const sixRoster = [...fullRoster, nikke('f')]

    it('sends the whole roster even while the palette shows one unit', async () => {
      const user = userEvent.setup()
      vi.mocked(getSupportedUnits).mockResolvedValue(paletteUnits)
      vi.mocked(recommendDecks).mockResolvedValue({ decks: [], excluded_slugs: [] })

      render(<RecommendPanel roster={sixRoster} {...noPersistence} />)
      await screen.findByRole('button', { name: /Crown 사용/i })

      await user.click(screen.getByRole('button', { name: '작열' }))
      expect(screen.getByRole('button', { name: /Anne 사용/i })).toBeInTheDocument()
      expect(screen.queryByRole('button', { name: /Crown 사용/i })).not.toBeInTheDocument()

      await user.click(screen.getByRole('button', { name: /덱 추천/i }))

      expect(recommendDecks).toHaveBeenCalledWith(
        expect.objectContaining({ roster: sixRoster }),
        expect.any(AbortSignal),
      )
    })

    it('keeps the pool count on the full roster while a filter hides units', async () => {
      const user = userEvent.setup()
      vi.mocked(getSupportedUnits).mockResolvedValue(paletteUnits)

      render(<RecommendPanel roster={sixRoster} {...noPersistence} />)
      await screen.findByRole('button', { name: /Crown 사용/i })
      expect(screen.getByText(/6\/6 탐색 풀에 포함됨/)).toBeInTheDocument()

      await user.click(screen.getByRole('button', { name: '작열' }))
      expect(screen.getByText(/6\/6 탐색 풀에 포함됨/)).toBeInTheDocument()
    })

    // Excluding is the pool control; filtering is not. A unit excluded before
    // a filter hid it must still be excluded after.
    it('leaves an exclusion intact across a filter that hides that unit', async () => {
      const user = userEvent.setup()
      vi.mocked(getSupportedUnits).mockResolvedValue(paletteUnits)
      vi.mocked(recommendDecks).mockResolvedValue({ decks: [], excluded_slugs: [] })

      render(<RecommendPanel roster={sixRoster} {...noPersistence} />)
      await screen.findByRole('button', { name: /Anne 사용/i })

      await user.click(screen.getByRole('button', { name: /Anne 사용/i }))
      await user.click(screen.getByRole('button', { name: '철갑' }))
      expect(screen.queryByRole('button', { name: /Anne 사용/i })).not.toBeInTheDocument()

      await user.click(screen.getByRole('button', { name: /덱 추천/i }))
      expect(recommendDecks).toHaveBeenCalledWith(
        expect.objectContaining({
          roster: sixRoster.filter((nikke) => nikke.character_slug !== 'b'),
        }),
        expect.any(AbortSignal),
      )
    })
  })
```

`sixRoster`는 슬러그 `a`~`f`이고 `paletteUnits`가 같은 슬러그를 이름 Crown/Anne/Liter/Blanc/Noir/Dorothy로 매핑하므로, 팔레트가 실제로 6기를 그린다. `작열`은 Anne 하나, `철갑`은 Crown과 Dorothy 둘을 남긴다.

- [ ] **Step 6: 회귀 테스트가 통과하는지 확인한다**

Run: `cd frontend && npx vitest run src/components/RecommendPanel.test.tsx`
Expected: PASS — 세 개 모두 통과해야 한다. **하나라도 실패하면 필터가 요청에 새고 있다는 뜻이므로 구현을 고친다.**

- [ ] **Step 7: 전체 스위트와 타입을 확인한다**

Run: `cd frontend && npx vitest run && npx tsc -b`
Expected: `340 passed / 40 files`, tsc 무출력

- [ ] **Step 8: 커밋**

```bash
git add frontend/src/components/UnitPalette.tsx frontend/src/components/UnitPalette.test.tsx frontend/src/components/RecommendPanel.test.tsx
git commit -F - <<'EOF'
Filter the recommend palette without touching the search pool

The filter lives inside the palette so nothing upstream can read it and be
tempted to narrow the request to match. Three tests pin that boundary: the
submitted roster, the pool count in the summary, and a per-unit exclusion all
survive a filter that hides the units they name.
EOF
```

---

### Task 4: 로스터 탭 B1/B2/B3 + 필터

**Files:**
- Modify: `frontend/src/components/RosterGrid.tsx`
- Modify: `frontend/src/components/RosterGrid.test.tsx`
- Modify: `frontend/src/components/NikkeCard.tsx:51` (`<h2>` → `<h3>`)
- Modify: `frontend/src/App.css` (`.roster__group` · `.roster__heading` 추가)

**Interfaces:**
- Consumes: Task 1의 `filterAndSort` · `EMPTY_FILTER` · `UnitFacets` · `UnitFilterState` · `BURST_TIERS`, Task 2의 `UnitFilterBar`
- Produces: 없음 (`RosterGrid`의 prop 시그니처는 그대로)

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`frontend/src/components/RosterGrid.test.tsx`에서 먼저 상단 헬퍼를 넓힌다 — 지금 `SUPPORTED`가 2기뿐이라 세 단계를 다 못 그린다:

```tsx
import userEvent from '@testing-library/user-event'

const SUPPORTED: SupportedUnit[] = [
  { slug: 'crown', name: 'Crown', burstTier: 1, element: 'Iron' },
  { slug: 'anne', name: 'Anne', burstTier: 1, element: 'Fire' },
  { slug: 'liter', name: 'Liter', burstTier: 2, element: 'Water' },
  { slug: 'blanc', name: 'Blanc', burstTier: 3, element: 'Wind' },
]
```

(기존 테스트는 `crown`/`liter`만 쓰므로 이 확장으로 깨지지 않는다.)

그리고 파일 마지막 `})` 앞에 붙인다:

```tsx
  describe('burst grouping and the filter', () => {
    const overloaded = (slug: string, value: number): NikkeDraft => ({
      ...draft(slug),
      overload_options: [{ id: `${slug}-ol`, name: '공격력 증가', value: String(value) }],
    })

    it('splits the supported units into B1/B2/B3 sections', () => {
      grid(['crown', 'liter', 'blanc'])
      expect(screen.getByRole('heading', { name: 'B1' })).toBeInTheDocument()
      expect(screen.getByRole('heading', { name: 'B2' })).toBeInTheDocument()
      expect(screen.getByRole('heading', { name: 'B3' })).toBeInTheDocument()
    })

    it('draws no heading for a burst tier the player owns nobody in', () => {
      grid(['crown'])
      expect(screen.getByRole('heading', { name: 'B1' })).toBeInTheDocument()
      expect(screen.queryByRole('heading', { name: 'B2' })).not.toBeInTheDocument()
    })

    // Default sort is by name, so the grid reads 가나다순 rather than in
    // whatever order the roster arrived.
    it('orders a group by name before the user chooses anything', () => {
      const { container } = grid(['crown', 'anne'])
      const names = [...container.querySelectorAll('.roster-card__name')].map((n) => n.textContent)
      expect(names).toEqual(['Anne', 'Crown'])
    })

    it('hides the cards an element filter excludes', async () => {
      const user = userEvent.setup()
      const { container } = grid(['crown', 'anne', 'liter'])
      await user.click(screen.getByRole('button', { name: '작열' }))
      expect(container.querySelectorAll('.roster-card')).toHaveLength(1)
      expect(screen.getByRole('heading', { name: 'Anne' })).toBeInTheDocument()
    })

    it('sorts a group by an overload stat within the group only', async () => {
      const user = userEvent.setup()
      const { container } = render(
        <RosterGrid
          drafts={[overloaded('crown', 10), overloaded('anne', 90), overloaded('liter', 50)]}
          supportedUnits={SUPPORTED}
          portraitFor={() => null}
        />,
      )
      await user.selectOptions(screen.getByLabelText('정렬'), '공')
      await user.selectOptions(screen.getByLabelText('정렬 방향'), 'desc')

      const b1 = screen.getByRole('heading', { name: 'B1' }).closest('section')!
      expect([...b1.querySelectorAll('.roster-card__name')].map((n) => n.textContent)).toEqual([
        'Anne',
        'Crown',
      ])
      // Liter outranks neither - she is in another group entirely.
      const b2 = screen.getByRole('heading', { name: 'B2' }).closest('section')!
      expect([...b2.querySelectorAll('.roster-card__name')].map((n) => n.textContent)).toEqual([
        'Liter',
      ])
    })

    // Unsupported units have no element and no burst tier to filter on, so the
    // toolbar deliberately does not reach them.
    it('leaves the unsupported list whole no matter what is filtered', async () => {
      const user = userEvent.setup()
      grid(['crown', '2b', 'alice-wonderland-bunny'])
      await user.click(screen.getByRole('button', { name: '수냉' }))
      expect(screen.getByText('엔진 미지원 (2기)')).toBeInTheDocument()
      expect(screen.getByText('2B')).toBeInTheDocument()
    })

    it('counts against the supported units alone', async () => {
      const user = userEvent.setup()
      grid(['crown', 'anne', '2b'])
      await user.click(screen.getByRole('button', { name: '작열' }))
      expect(screen.getByText('2기 중 1기 표시 중')).toBeInTheDocument()
    })
  })
```

- [ ] **Step 2: 실패를 확인한다**

Run: `cd frontend && npx vitest run src/components/RosterGrid.test.tsx`
Expected: FAIL — `Unable to find an accessible element with the role "heading" and name "B1"`

- [ ] **Step 3: 카드 제목을 한 단계 낮춘다**

`frontend/src/components/NikkeCard.tsx:51`:

```tsx
      <h3 className="roster-card__name">{title}</h3>
```

버스트 그룹 제목이 `<h2>`가 되므로 카드 이름은 그 아래여야 한다. `NikkeCard.test.tsx`는 레벨을 지정하지 않고 `getByRole('heading', ...)`만 쓰므로 그대로 통과한다.

- [ ] **Step 4: 그리드를 다시 짠다**

`frontend/src/components/RosterGrid.tsx` 전체:

```tsx
// The Roster tab's contents: everything the active profile synced, split by
// whether the engine can actually simulate it.
//
// A player owns far more Nikkes than the engine supports (159 vs 70 on the
// roster this was built against). Drawing both alike made more than half the
// tab units that can never enter a deck, at the same size and weight as the
// ones that can. The supported units get the grid; the rest get a collapsed
// list, present so a missing Nikke is explained rather than simply absent.
//
// The supported half is grouped by burst tier, the way the recommend palette
// groups it - a roster is read to answer "what can I field", and that
// question is always asked one tier at a time.

import { useState } from 'react'
import type { NikkeDraft } from '../types/nikkeDraft'
import { BURST_TIERS, type SupportedUnit } from '../types/supportedUnit'
import { displayName } from '../lib/unitName'
import {
  EMPTY_FILTER,
  filterAndSort,
  type UnitFacets,
  type UnitFilterState,
} from '../lib/unitFilter'
import { NikkeCard } from './NikkeCard'
import { UnitFilterBar } from './UnitFilterBar'

interface RosterGridProps {
  drafts: NikkeDraft[]
  supportedUnits: SupportedUnit[]
  portraitFor: (slug: string) => string | null
}

export function RosterGrid({ drafts, supportedUnits, portraitFor }: RosterGridProps) {
  const bySlug = new Map(supportedUnits.map((unit) => [unit.slug, unit]))
  const supported = drafts.filter((draft) => bySlug.has(draft.character_slug))
  const unsupported = drafts.filter((draft) => !bySlug.has(draft.character_slug))
  const names = new Map(supportedUnits.map((unit) => [unit.slug, unit.name]))

  const [filter, setFilter] = useState<UnitFilterState>(EMPTY_FILTER)

  // Only the supported half has an element and a burst tier to filter on; the
  // unsupported list is not in `supportedUnits` at all, so a half-applied
  // toolbar would just look broken there.
  const facetsFor = (draft: NikkeDraft): UnitFacets => {
    const unit = bySlug.get(draft.character_slug)!
    return {
      name: unit.name,
      element: unit.element,
      burstTier: unit.burstTier,
      overload: draft.overload_options,
    }
  }

  // Sorted once across the whole roster, then partitioned by tier - a
  // partition preserves relative order, so each group is already in sort
  // order.
  const visible = filterAndSort(supported, facetsFor, filter)

  return (
    <div className="roster">
      <UnitFilterBar
        value={filter}
        onChange={setFilter}
        shown={visible.length}
        total={supported.length}
      />

      {BURST_TIERS.map((tier) => {
        const units = visible.filter(
          (draft) => bySlug.get(draft.character_slug)!.burstTier === tier,
        )
        if (units.length === 0) return null
        return (
          <section key={tier} className="roster__group">
            <h2 className="roster__heading">B{tier}</h2>
            <div className="roster__grid">
              {units.map((draft, index) => {
                const unit = bySlug.get(draft.character_slug)!
                return (
                  <NikkeCard
                    key={draft.id ?? draft.character_slug}
                    draft={draft}
                    index={index}
                    name={unit.name}
                    element={unit.element}
                    portrait={portraitFor(draft.character_slug)}
                  />
                )
              })}
            </div>
          </section>
        )
      })}

      {unsupported.length > 0 && (
        <details className="roster__unsupported">
          <summary className="roster__unsupported-summary">
            엔진 미지원 ({unsupported.length}기)
          </summary>
          <ul className="roster__unsupported-list">
            {unsupported.map((draft) => (
              <li key={draft.id ?? draft.character_slug}>
                {displayName(draft.character_slug, names)}
              </li>
            ))}
          </ul>
        </details>
      )}
    </div>
  )
}
```

- [ ] **Step 5: 통과를 확인한다**

Run: `cd frontend && npx vitest run src/components/RosterGrid.test.tsx src/components/NikkeCard.test.tsx`
Expected: PASS

- [ ] **Step 6: 그룹 스타일을 붙인다**

`frontend/src/App.css`의 `.roster__grid` 블록(63-67행) **앞**에 넣는다:

```css
/* One burst tier's worth of the roster. The heading is what makes the grid
   readable as three answers instead of one long wall. */
.roster__group {
  display: flex;
  flex-direction: column;
  gap: var(--sp-2);
}

.roster__heading {
  margin: 0;
  font-size: 13px;
  font-weight: 600;
  color: var(--text-muted);
}
```

- [ ] **Step 7: 전체 스위트와 타입을 확인한다**

Run: `cd frontend && npx vitest run && npx tsc -b`
Expected: `347 passed / 40 files`, tsc 무출력

- [ ] **Step 8: 커밋**

```bash
git add frontend/src/components/RosterGrid.tsx frontend/src/components/RosterGrid.test.tsx frontend/src/components/NikkeCard.tsx frontend/src/App.css
git commit -F - <<'EOF'
Group the roster tab by burst tier and give it the same toolbar

A roster is read to answer "what can I field", which is always asked one
tier at a time - the flat grid made that question take a full scroll. The
unsupported list stays whole under every filter: those units are not in
supportedUnits, so there is no element or tier to judge them on.
EOF
```

---

### Task 5: 작열 속성색 + 로드맵 갱신

**Files:**
- Modify: `frontend/src/index.css:41`
- Modify: `docs/roadmap.md:1321-1329`

**Interfaces:**
- Consumes: 없음
- Produces: 없음

- [ ] **Step 1: 토큰을 바꾼다**

`frontend/src/index.css:39-45`의 주석과 값을 이렇게 바꾼다:

```css
  /* Element identity, so a portrait can state its element without a label.
     Fire is a deep red (Fienn, 2026-07-28) rather than the orange it was:
     next to Iron's gold on a dark surface the two used to read alike.
     Electric leans magenta to stay distinct from the purple accent. */
  --el-fire: #dd3333;
  --el-water: #3fa9f5;
  --el-wind: #46c96b;
  --el-iron: #f2b53b;
  --el-electric: #d158f5;
```

이 토큰을 읽는 곳은 `.roster-card[data-element='Fire']`, `.palette__item[data-element='Fire']`, 그리고 Task 2가 추가한 `.unit-filter__chip[data-element='Fire']` 셋뿐이므로 한 줄로 전부 바뀐다.

- [ ] **Step 2: 아무것도 안 깨졌는지 확인한다**

Run: `cd frontend && npx vitest run`
Expected: `347 passed / 40 files` — Vitest는 `css: false`로 돌아 색상을 못 읽으므로 개수가 그대로여야 정상이다.

- [ ] **Step 3: 로드맵을 갱신한다**

`docs/roadmap.md:1321-1329`의 백로그 항목에서 **첫 번째 하위 항목(니케 검색/정렬/필터)을 지우고** 제목의 "백로그 2건"을 "백로그 1건"으로 바꾼다. 남는 모습:

```markdown
- [ ] **UI 크롬 한글화 스펙 리뷰 중 나온 백로그 1건 (2026-07-26, 아직 미설계 — 범위 밖,
      캡처만).** `docs/superpowers/specs/2026-07-26-ui-chrome-korean-localization-design.md`
      리뷰 중 Fienn이 별도 세션감으로 떠올린 것:
      - Roster/Recommend/Sync를 사이드바 탭으로 재구성 — 지금은 `App.tsx`에 "Roster"·
        "Recommend" 탭 2개뿐이고 Sync 패널은 Roster 탭 안에 얹혀 있다. 이건 네비게이션/
        레이아웃 구조 변경.
```

그리고 그 항목 **바로 아래**에 완료 항목을 추가한다:

```markdown
- [x] **니케 검색·정렬·필터 + 로스터 탭 버스트 분류 — 완료 (2026-07-28).** 두 화면이
      `lib/unitFilter.ts`의 순수 규칙 하나를 공유한다(데이터 모양이 달라 `UnitFacets`
      접근자를 받는 제네릭). 이름 부분일치 검색 · 속성/버스트 다중 필터 · 이름 또는
      오버로드 7종 중 하나로 양방향 정렬. 로스터 탭에 B1/B2/B3 분류를 신설했고, 정렬은
      그룹 **안에서만** 일어난다. 핵심 불변식은 **필터가 시야만 바꾼다**는 것 —
      추천 탭에서 숨겨진 유닛도 탐색 풀에 그대로 있고, 요청 payload·풀 개수·개별 제외
      상태가 필터에 안 흔들린다는 것을 회귀 테스트 3개로 고정했다. 작열 속성색도
      `#f0603c` → `#dd3333`(Fienn 지정)으로 바꿔 철갑 금색과 안 헷갈리게 했다.
      프론트 **301 → 347 passed**. 스펙:
      `docs/superpowers/specs/2026-07-28-roster-search-filter-design.md`.
```

- [ ] **Step 4: 커밋**

```bash
git add frontend/src/index.css docs/roadmap.md
git commit -F - <<'EOF'
Deepen the Fire element colour to the red Fienn asked for

The old #f0603c sat close enough to Iron's gold that a dark screen made the
two portrait borders read alike. One token feeds all three places that draw
an element edge, so the change lands everywhere at once.
EOF
```

---

## 남은 확인 (구현 후, 사람이 한다)

Vitest는 `css: false`로 돌기 때문에 아래 셋은 **테스트가 구조적으로 못 잡는다**. 실제 앱(`cd backend && uvicorn app.api:app --reload` + `cd frontend && npm run dev`)에서 봐야 한다 — 재현 하네스로 재면 틀린다(`docs/insights.md`).

1. **툴바가 먹는 세로 공간.** 추천 탭 팔레트는 `<details>` 안에 있어 여유가 적다. 툴바가 두 줄로 접히면 팔레트 첫 칩이 얼마나 밀려나는지 확인.
2. **`#dd3333`이 `--danger: #f87171`와 헷갈리는지.** 둘이 나란히 놓이는 자리는 없지만 확인할 가치가 있다.
3. **작열 칩이 켜졌을 때 테두리가 보이는지.** `.unit-filter__chip[aria-pressed='true']`가 어두운 표면에서 1px 테두리로 충분히 구분되는지.

실화면 로스터 시드 방법은 `memory/ui-improvements-session.md`의 "실화면 확인용 로스터 시드" 항목에 있다.
