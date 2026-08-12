# 편성 전체 초기화 · 저장한 결과 가져오기 — 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 편성 칸이 있는 세 화면에 「전체 초기화」와 「저장한 결과 가져오기」 버튼을 더해, 최적화가 뽑아 준 덱을 편성으로 옮겨 손볼 수 있게 한다.

**Architecture:** 순수 변환 함수 하나(`lib/importRun.ts`)와 표시용 컴포넌트 둘(`ClearDraftButton`, `ImportRunButton`)을 만들고, 두 패널(`RecommendPanel`, `UnionRaidPanel`)이 그것을 액션 행에 배선한다. 패널은 자기 화면의 보스·덱 개수·모드를 어떻게 되돌릴지만 알고, 덱을 편성으로 바꾸는 규칙은 공용 함수 하나가 안다.

**Tech Stack:** React 19 + TypeScript + Vite, Vitest + @testing-library/react, 순수 CSS(`App.css` / `index.css`의 토큰).

설계 문서: `docs/superpowers/specs/2026-08-12-deck-clear-and-import-design.md`

## Global Constraints

- 화면에 나오는 **문장**은 전부 `frontend/src/lib/helpText.ts`의 `HELP`에 둔다. **조작 대상의 이름**(버튼 라벨, 필드 라벨)은 거기 두지 않는다 — 그 파일 머리말이 정한 경계다.
- `window.confirm`에 들어가는 문구는 **평문 전용**이다. `**굵게**` 표기를 쓰면 별표가 글자 그대로 보인다. 기존 `savedRuns.confirmDelete`와 같은 주석을 붙인다.
- 폼 안의 버튼은 **반드시 `type="button"`** 이다. 맨 버튼은 submit이라, 초기화를 누르면 시뮬레이션이 시작된다.
- 새 버튼 라벨은 정확히 이 둘이다: `전체 초기화`, `저장한 결과 가져오기`. 펼친 목록 안의 버튼은 `가져오기`.
- 테스트에서 버튼을 찾을 때 `/가져오기/` 같은 정규식을 쓰지 말 것 — 「저장한 결과 가져오기」와 「가져오기」가 둘 다 걸린다. 정확 문자열(`name: '가져오기'`)을 쓴다.
- 기존 스위트에서 실행 버튼을 찾는 `/인카운터/` 정규식 70여 개가 그대로 초록이어야 한다.
- 좌석은 `DraftSeat = { slug: string; locked: boolean }`. 가져온 좌석은 **전부 `locked: false`**.
- 커밋 메시지는 한국어 현재형 한 줄(`git log --oneline`의 기존 어투를 따른다).
- 프론트 타입체크는 `npx --prefix frontend tsc -b --noEmit frontend` (cwd는 저장소 루트).
- 프론트 테스트는 `npm --prefix frontend test -- --run <경로>`.

---

### Task 1: `lib/importRun.ts` — 결과 덱을 편성으로

**Files:**
- Create: `frontend/src/lib/importRun.ts`
- Test: `frontend/src/lib/importRun.test.ts`

**Interfaces:**
- Consumes: `Draft`, `DraftSeat` (`frontend/src/types/draft.ts`)
- Produces:
  ```ts
  interface ImportedDraft { draft: Draft; droppedSlugs: string[] }
  const draftFromResultDecks: (
    deckSlugs: string[][],
    numDecks: number,
    lookups: { ownedSlugFor: (slug: string) => string; canSeat: (slug: string) => boolean },
  ) => ImportedDraft
  const canSeatFrom: (
    roster: { character_slug: string }[],
    excludedSlugs: Set<string>,
  ) => (slug: string) => boolean
  ```

- [ ] **Step 1: Write the failing test**

`frontend/src/lib/importRun.test.ts`:

```ts
import { describe, expect, it } from 'vitest'
import { canSeatFrom, draftFromResultDecks } from './importRun'

/** 기본 조회: 슬러그는 그대로, 전부 앉힐 수 있음. */
const plain = {
  ownedSlugFor: (slug: string) => slug,
  canSeat: () => true,
}

describe('draftFromResultDecks', () => {
  it('결과 덱을 순서대로 좌석으로 앉힌다', () => {
    const { draft, droppedSlugs } = draftFromResultDecks(
      [['a', 'b'], ['c']],
      2,
      plain,
    )

    expect(draft.decks).toEqual([
      [
        { slug: 'a', locked: false },
        { slug: 'b', locked: false },
      ],
      [{ slug: 'c', locked: false }],
    ])
    expect(droppedSlugs).toEqual([])
  })

  it('엔진 슬러그를 소유 슬러그로 되돌린다', () => {
    const { draft } = draftFromResultDecks([['bready-lingering']], 1, {
      ...plain,
      ownedSlugFor: (slug) => (slug === 'bready-lingering' ? 'bready' : slug),
    })

    expect(draft.decks[0]).toEqual([{ slug: 'bready', locked: false }])
  })

  it('앉힐 수 없는 니케는 자리를 비우고 목록에 담는다', () => {
    const { draft, droppedSlugs } = draftFromResultDecks([['a', 'gone', 'b']], 1, {
      ...plain,
      canSeat: (slug) => slug !== 'gone',
    })

    expect(draft.decks[0]).toEqual([
      { slug: 'a', locked: false },
      { slug: 'b', locked: false },
    ])
    expect(droppedSlugs).toEqual(['gone'])
  })

  it('앉힐 수 있는지는 되돌린 소유 슬러그로 묻는다', () => {
    const asked: string[] = []
    draftFromResultDecks([['bready-lingering']], 1, {
      ownedSlugFor: () => 'bready',
      canSeat: (slug) => {
        asked.push(slug)
        return true
      },
    })

    expect(asked).toEqual(['bready'])
  })

  it('덱 개수에 맞춰 자르고 모자란 자리는 빈 덱으로 채운다', () => {
    const { draft } = draftFromResultDecks([['a'], ['b'], ['c']], 2, plain)
    expect(draft.decks).toHaveLength(2)

    const grown = draftFromResultDecks([['a']], 3, plain)
    expect(grown.draft.decks).toEqual([[{ slug: 'a', locked: false }], [], []])
  })

  it('같은 니케가 두 번 나와도 한 번만 앉는다', () => {
    const { draft } = draftFromResultDecks([['a'], ['a', 'b']], 2, plain)

    expect(draft.decks[0]).toEqual([{ slug: 'a', locked: false }])
    expect(draft.decks[1]).toEqual([{ slug: 'b', locked: false }])
  })
})

describe('canSeatFrom', () => {
  const roster = [{ character_slug: 'a' }, { character_slug: 'b' }]

  it('로스터에 있고 미사용이 아닌 니케만 앉힌다', () => {
    const canSeat = canSeatFrom(roster, new Set(['b']))

    expect(canSeat('a')).toBe(true)
    expect(canSeat('b')).toBe(false) // 미사용으로 둔 니케
    expect(canSeat('z')).toBe(false) // 로스터에 없는 니케
  })
})
```

각 테스트가 무엇을 잡는지: 2번은 `ownedSlugFor` 호출을 지우면 빨강, 3번은 `canSeat` 필터를 지우면 빨강(자리 수가 3이 되고 목록이 빈다), 4번은 되돌리기 **전** 슬러그로 물으면 빨강, 6번은 중복 방지를 지우면 빨강.

- [ ] **Step 2: Run test to verify it fails**

Run: `npm --prefix frontend test -- --run src/lib/importRun.test.ts`
Expected: FAIL — `Failed to resolve import "./importRun"`

- [ ] **Step 3: Write minimal implementation**

`frontend/src/lib/importRun.ts`:

```ts
// 저장해 둔 결과의 덱을 편성 칸이 쓰는 모양으로 옮긴다.
//
// 결과는 엔진 슬러그를 쓰고(`bready` -> `bready-lingering`) 그때의 로스터로
// 나온 것이라, 편성으로 옮기려면 슬러그를 되돌리고 지금 앉힐 수 없는 니케를
// 걸러내야 한다. 무엇이 걸러졌는지 함께 돌려주는 이유는, 말하지 않으면 5명이어야
// 할 덱이 4명인 채로 이유 없이 서 있기 때문이다.

import type { Draft, DraftSeat } from '../types/draft'

export interface ImportedDraft {
  draft: Draft
  /** 앉히지 못한 소유 슬러그들. 화면은 이 길이만 쓴다. */
  droppedSlugs: string[]
}

/**
 * `deckSlugs`(덱마다 슬러그 목록)를 `numDecks`개짜리 편성으로 만든다.
 *
 * 좌석은 전부 잠기지 않은 채로 나온다 - 가져온 편성은 「여기서 출발」이지
 * 「이 자리를 고정」이 아니다(Fienn, 2026-08-12).
 */
export const draftFromResultDecks = (
  deckSlugs: string[][],
  numDecks: number,
  { ownedSlugFor, canSeat }: {
    ownedSlugFor: (slug: string) => string
    canSeat: (slug: string) => boolean
  },
): ImportedDraft => {
  const droppedSlugs: string[] = []
  // 한 니케는 한 자리에만 앉는다 - 편성 편집기가 지키는 불변식이라
  // (DraftEditor의 placeUnit) 가져오기도 지킨다.
  const seated = new Set<string>()

  const decks = Array.from({ length: numDecks }, (_, deckIndex) => {
    const seats: DraftSeat[] = []
    for (const resultSlug of deckSlugs[deckIndex] ?? []) {
      const slug = ownedSlugFor(resultSlug)
      if (seated.has(slug)) continue
      if (!canSeat(slug)) {
        droppedSlugs.push(slug)
        continue
      }
      seated.add(slug)
      seats.push({ slug, locked: false })
    }
    return seats
  })

  return { draft: { decks }, droppedSlugs }
}

/**
 * `draftFromResultDecks`에 넘길 `canSeat`. 솔로 탭과 유니온 탭이 같은 판정을
 * 쓰므로 여기 한 벌만 둔다.
 *
 * 「제외」는 어디서나 같은 뜻이다: 덱에서도 빠지고 제출 로스터에서도 빠진다
 * (UnitPalette의 toggleExcludedSlug 주석). 팔레트가 막는 배치를 가져오기가
 * 대신 해 주면 그 불변식이 깨진다.
 */
export const canSeatFrom =
  (roster: { character_slug: string }[], excludedSlugs: Set<string>) =>
  (slug: string): boolean =>
    roster.some((nikke) => nikke.character_slug === slug) && !excludedSlugs.has(slug)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `npm --prefix frontend test -- --run src/lib/importRun.test.ts`
Expected: PASS (7 tests)

- [ ] **Step 5: Commit**

```bash
git add frontend/src/lib/importRun.ts frontend/src/lib/importRun.test.ts
git commit -m "결과 덱을 편성으로 옮기는 변환을 만든다"
```

---

### Task 2: `ClearDraftButton` — 전체 초기화

**Files:**
- Create: `frontend/src/components/ClearDraftButton.tsx`
- Test: `frontend/src/components/ClearDraftButton.test.tsx`
- Modify: `frontend/src/lib/helpText.ts` (`HELP`에 `draftActions` 그룹 신설)
- Modify: `frontend/src/App.css` (`.btn--danger`, `.draft-actions__clear`)

**Interfaces:**
- Consumes: `Draft` (`types/draft.ts`), `HELP` (`lib/helpText.ts`)
- Produces: `ClearDraftButton({ draft, onClear }: { draft: Draft; onClear: () => void })`

- [ ] **Step 1: Write the failing test**

`frontend/src/components/ClearDraftButton.test.tsx`:

```ts
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { ClearDraftButton } from './ClearDraftButton'
import type { Draft } from '../types/draft'

const filled: Draft = { decks: [[{ slug: 'a', locked: false }], []] }
const empty: Draft = { decks: [[], []] }

afterEach(() => {
  vi.restoreAllMocks()
})

describe('ClearDraftButton', () => {
  it('확인을 수락하면 비운다', async () => {
    vi.spyOn(window, 'confirm').mockReturnValue(true)
    const onClear = vi.fn()
    const user = userEvent.setup()
    render(<ClearDraftButton draft={filled} onClear={onClear} />)

    await user.click(screen.getByRole('button', { name: '전체 초기화' }))

    expect(onClear).toHaveBeenCalledOnce()
  })

  it('확인을 거절하면 비우지 않는다', async () => {
    vi.spyOn(window, 'confirm').mockReturnValue(false)
    const onClear = vi.fn()
    const user = userEvent.setup()
    render(<ClearDraftButton draft={filled} onClear={onClear} />)

    await user.click(screen.getByRole('button', { name: '전체 초기화' }))

    expect(onClear).not.toHaveBeenCalled()
  })

  it('편성이 비어 있으면 누를 수 없다', () => {
    render(<ClearDraftButton draft={empty} onClear={() => {}} />)

    expect(screen.getByRole('button', { name: '전체 초기화' })).toBeDisabled()
  })

  it('폼 안에서 제출을 일으키지 않는다', async () => {
    vi.spyOn(window, 'confirm').mockReturnValue(true)
    const onSubmit = vi.fn((event: React.FormEvent) => event.preventDefault())
    const user = userEvent.setup()
    render(
      <form onSubmit={onSubmit}>
        <ClearDraftButton draft={filled} onClear={() => {}} />
      </form>,
    )

    await user.click(screen.getByRole('button', { name: '전체 초기화' }))

    expect(onSubmit).not.toHaveBeenCalled()
  })
})
```

무엇을 잡는지: 1·2번은 `confirm` 반환값을 무시하면 하나가 빨강, 3번은 비활성 조건을 지우면 빨강, 4번은 `type="button"`을 빼면 빨강.

- [ ] **Step 2: Run test to verify it fails**

Run: `npm --prefix frontend test -- --run src/components/ClearDraftButton.test.tsx`
Expected: FAIL — `Failed to resolve import "./ClearDraftButton"`

- [ ] **Step 3: 문구를 추가한다**

`frontend/src/lib/helpText.ts` — `savedRuns` 그룹 **바로 뒤**에 새 그룹을 넣는다(가까운 주제끼리 모은다):

```ts
  draftActions: {
    /** 평문 전용 - window.confirm이라 별표가 글자 그대로 나온다. */
    confirmClear: '모든 덱을 초기화하시겠습니까?',
    /** 평문 전용 - 같은 이유. */
    confirmOverwrite: '지금 편성을 저장한 결과로 바꿀까요?',
    droppedUnits: (count: number) =>
      `가져온 편성에서 ${count}기가 빠졌어요 — 지금 로스터에 없거나 미사용으로 둔 니케예요.`,
  },
```

`confirmOverwrite`와 `droppedUnits`는 Task 3·4에서 쓴다. 세 문구가 한 그룹이므로 여기서 함께 넣는다.

- [ ] **Step 4: Write minimal implementation**

`frontend/src/components/ClearDraftButton.tsx`:

```tsx
// 편성을 통째로 비우는 버튼. 되돌릴 수 없으므로 확인을 한 번 묻고, 비울 것이
// 없으면 아예 눌리지 않는다.
//
// 비우는 것은 편성뿐이다 - 보스 설정도 덱 개수도 건드리지 않는다. 좌석이
// 사라지므로 잠금은 함께 사라진다.

import { HELP } from '../lib/helpText'
import type { Draft } from '../types/draft'

interface ClearDraftButtonProps {
  /** 비활성 판정에만 쓴다 - 무엇으로 비울지는 부모가 안다(덱 개수를 쥔 쪽이다). */
  draft: Draft
  onClear: () => void
}

export function ClearDraftButton({ draft, onClear }: ClearDraftButtonProps) {
  const isEmpty = draft.decks.every((seats) => seats.length === 0)

  return (
    <button
      type="button"
      className="btn btn--danger draft-actions__clear"
      disabled={isEmpty}
      onClick={() => {
        if (window.confirm(HELP.draftActions.confirmClear)) onClear()
      }}
    >
      전체 초기화
    </button>
  )
}
```

- [ ] **Step 5: Run test to verify it passes**

Run: `npm --prefix frontend test -- --run src/components/ClearDraftButton.test.tsx`
Expected: PASS (4 tests)

- [ ] **Step 6: CSS를 더한다**

`frontend/src/App.css` — `.btn--ghost` 규칙 **바로 앞**(즉 `.btn--primary:hover` 뒤)에 넣는다:

```css
/* 빨강 채움은 이 하나뿐이다. 「빨강은 앱이 가리키는 것」이라는 위 규칙의 예외를
   되돌릴 수 없는 행동 하나에만 허용한 것이다(Fienn, 2026-08-12). 글자가
   근검정인 이유는 흰 글자가 이 빨강 위에서 대비 3.80으로 미달이기 때문이다
   (index.css의 --accent 주석). */
.btn--danger {
  background: var(--accent);
  color: var(--accent-contrast);
  border-color: var(--accent);
  font-weight: 600;
}

/* --accent에는 hover 짝이 없다. 팔레트에 토큰을 하나 더 만드는 대신 밝기만
   올린다 - 색을 새로 고르지 않으므로 대비 검증이 도는 값이 늘지 않는다. */
.btn--danger:hover:not(:disabled) {
  filter: brightness(1.08);
}

/* 파괴적인 것만 행의 반대쪽 끝에 선다. 실행과 가져오기는 왼쪽에 모인다. */
.draft-actions__clear {
  margin-left: auto;
}
```

- [ ] **Step 7: Commit**

```bash
git add frontend/src/components/ClearDraftButton.tsx frontend/src/components/ClearDraftButton.test.tsx frontend/src/lib/helpText.ts frontend/src/App.css
git commit -m "편성을 통째로 비우는 버튼을 만든다"
```

---

### Task 3: `ImportRunButton` — 저장한 결과 고르기

**Files:**
- Create: `frontend/src/components/ImportRunButton.tsx`
- Test: `frontend/src/components/ImportRunButton.test.tsx`
- Create: `frontend/src/lib/savedRunLabel.ts`
- Modify: `frontend/src/components/SavedRunList.tsx:13-17` (자기 안의 `savedAtLabel`을 위 모듈에서 가져오도록)
- Modify: `frontend/src/App.css` (`.import-run`, `.import-run__list`, `.import-run__item`)

**Interfaces:**
- Consumes: `SavedRun` (`types/profile.ts`), `Draft` (`types/draft.ts`), `HELP.draftActions.confirmOverwrite` (Task 2)
- Produces:
  - `savedAtLabel(savedAt: number): string` in `lib/savedRunLabel.ts`
  - `ImportRunButton({ runs, draft, onImport }: { runs: SavedRun[]; draft: Draft; onImport: (run: SavedRun) => void })`

- [ ] **Step 1: Write the failing test**

`frontend/src/components/ImportRunButton.test.tsx`:

```tsx
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { ImportRunButton } from './ImportRunButton'
import type { Draft } from '../types/draft'
import type { SavedRun } from '../types/profile'

const run = (id: string, name: string): SavedRun => ({
  id,
  name,
  savedAt: 1754438400000,
  tab: 'solo',
  view: {
    mode: 'raid',
    boss: {
      element: 'Fire',
      core_hittable: false,
      pierce_hits_body_behind_core: false,
      enemy_def: 31784,
      fight_duration: 180,
      part_destructible: false,
      core_diameter_px: null,
      effective_range_band: null,
      elemental_interrupt_required: false,
    },
    numDecks: 2,
    decks: [],
    combinedTotalDamage: 1,
    excludedSlugs: [],
    leftoverSlugs: [],
  },
})

const filled: Draft = { decks: [[{ slug: 'a', locked: false }], []] }
const empty: Draft = { decks: [[], []] }

afterEach(() => {
  vi.restoreAllMocks()
})

describe('ImportRunButton', () => {
  it('저장한 결과가 없으면 누를 수 없다', () => {
    render(<ImportRunButton runs={[]} draft={empty} onImport={() => {}} />)

    expect(screen.getByRole('button', { name: '저장한 결과 가져오기' })).toBeDisabled()
  })

  it('누르면 목록이 펼쳐지고 다시 누르면 접힌다', async () => {
    const user = userEvent.setup()
    render(<ImportRunButton runs={[run('r1', '화염 · 전부 최적화')]} draft={empty} onImport={() => {}} />)
    const toggle = screen.getByRole('button', { name: '저장한 결과 가져오기' })

    await user.click(toggle)
    expect(screen.getByText('화염 · 전부 최적화')).toBeInTheDocument()

    await user.click(toggle)
    expect(screen.queryByText('화염 · 전부 최적화')).not.toBeInTheDocument()
  })

  it('고르면 그 결과를 넘기고 목록을 접는다', async () => {
    const onImport = vi.fn()
    const user = userEvent.setup()
    render(<ImportRunButton runs={[run('r1', '화염')]} draft={empty} onImport={onImport} />)

    await user.click(screen.getByRole('button', { name: '저장한 결과 가져오기' }))
    await user.click(screen.getByRole('button', { name: '가져오기' }))

    expect(onImport).toHaveBeenCalledWith(expect.objectContaining({ id: 'r1' }))
    expect(screen.queryByRole('button', { name: '가져오기' })).not.toBeInTheDocument()
  })

  it('편성이 비어 있으면 덮어쓸지 묻지 않는다', async () => {
    const confirmSpy = vi.spyOn(window, 'confirm').mockReturnValue(true)
    const user = userEvent.setup()
    render(<ImportRunButton runs={[run('r1', '화염')]} draft={empty} onImport={() => {}} />)

    await user.click(screen.getByRole('button', { name: '저장한 결과 가져오기' }))
    await user.click(screen.getByRole('button', { name: '가져오기' }))

    expect(confirmSpy).not.toHaveBeenCalled()
  })

  it('편성이 차 있으면 묻고, 거절하면 가져오지 않는다', async () => {
    vi.spyOn(window, 'confirm').mockReturnValue(false)
    const onImport = vi.fn()
    const user = userEvent.setup()
    render(<ImportRunButton runs={[run('r1', '화염')]} draft={filled} onImport={onImport} />)

    await user.click(screen.getByRole('button', { name: '저장한 결과 가져오기' }))
    await user.click(screen.getByRole('button', { name: '가져오기' }))

    expect(window.confirm).toHaveBeenCalledOnce()
    expect(onImport).not.toHaveBeenCalled()
  })

  it('폼 안에서 제출을 일으키지 않는다', async () => {
    const onSubmit = vi.fn((event: React.FormEvent) => event.preventDefault())
    const user = userEvent.setup()
    render(
      <form onSubmit={onSubmit}>
        <ImportRunButton runs={[run('r1', '화염')]} draft={empty} onImport={() => {}} />
      </form>,
    )

    await user.click(screen.getByRole('button', { name: '저장한 결과 가져오기' }))
    await user.click(screen.getByRole('button', { name: '가져오기' }))

    expect(onSubmit).not.toHaveBeenCalled()
  })
})
```

무엇을 잡는지: 4번은 확인을 무조건 묻게 만들면 빨강, 5번은 확인 분기를 지우면 빨강(`onImport`가 불린다), 6번은 두 버튼 중 하나라도 `type="button"`을 빼면 빨강.

- [ ] **Step 2: Run test to verify it fails**

Run: `npm --prefix frontend test -- --run src/components/ImportRunButton.test.tsx`
Expected: FAIL — `Failed to resolve import "./ImportRunButton"`

- [ ] **Step 3: 저장 시각 라벨을 공용 모듈로 옮긴다**

`frontend/src/lib/savedRunLabel.ts` 신규:

```ts
// 보관물이 언제 저장됐는지. 목록 두 곳(SavedRunList, ImportRunButton)이 같은
// 모양으로 말해야 해서 한곳에 둔다.

export const savedAtLabel = (savedAt: number): string => {
  const at = new Date(savedAt)
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${pad(at.getMonth() + 1)}-${pad(at.getDate())} ${pad(at.getHours())}:${pad(at.getMinutes())}`
}
```

`frontend/src/components/SavedRunList.tsx`에서 13~17행의 지역 `savedAtLabel` 정의를 지우고, 상단 import에 다음을 더한다:

```ts
import { savedAtLabel } from '../lib/savedRunLabel'
```

- [ ] **Step 4: Write minimal implementation**

`frontend/src/components/ImportRunButton.tsx`:

```tsx
// 이름 붙여 남겨 둔 결과 하나를 골라 편성으로 가져오는 버튼. 누르면 그 자리에
// 고르기 목록이 펼쳐진다.
//
// SavedRunList를 재사용하지 않는 이유: 저쪽은 펼쳐서 결과를 읽고 이름을 바꾸고
// 지우는 관리 목록이고, 이쪽은 고르면 끝나는 선택 목록이다. 한 컴포넌트에 두
// 역할을 넣으면 props가 역할 스위치로 갈라진다.

import { useState } from 'react'
import { HELP } from '../lib/helpText'
import { savedAtLabel } from '../lib/savedRunLabel'
import type { Draft } from '../types/draft'
import type { SavedRun } from '../types/profile'

interface ImportRunButtonProps {
  /** 이 탭의 보관물, 최신순. */
  runs: SavedRun[]
  /** 이미 앉은 니케가 있으면 덮어쓸지 한 번 묻는다. 비어 있으면 잃을 것이 없다. */
  draft: Draft
  onImport: (run: SavedRun) => void
}

export function ImportRunButton({ runs, draft, onImport }: ImportRunButtonProps) {
  const [open, setOpen] = useState(false)
  const hasSeats = draft.decks.some((seats) => seats.length > 0)

  const pick = (run: SavedRun) => {
    if (hasSeats && !window.confirm(HELP.draftActions.confirmOverwrite)) return
    onImport(run)
    setOpen(false)
  }

  return (
    <div className="import-run">
      <button
        type="button"
        className="btn import-run__toggle"
        disabled={runs.length === 0}
        aria-expanded={open}
        onClick={() => setOpen((current) => !current)}
      >
        저장한 결과 가져오기
      </button>

      {open && (
        <ul className="import-run__list">
          {runs.map((run) => (
            <li key={run.id} className="import-run__item">
              <span className="import-run__name">{run.name}</span>
              <span className="import-run__when">{savedAtLabel(run.savedAt)}</span>
              <button type="button" className="btn" onClick={() => pick(run)}>
                가져오기
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `npm --prefix frontend test -- --run src/components/ImportRunButton.test.tsx src/components/SavedRunList.test.tsx`
Expected: PASS — 새 6개, 그리고 `savedAtLabel`을 옮긴 뒤에도 `SavedRunList` 스위트가 그대로 초록

- [ ] **Step 6: CSS를 더한다**

`frontend/src/App.css` — Task 2에서 더한 `.draft-actions__clear` 바로 뒤에 넣는다:

```css
/* 고르기 목록은 액션 행 아래로 겹쳐 뜬다. 흐름 안에 펼치면 sticky 덱 컬럼이
   그만큼 길어져 실행 버튼이 화면 밖으로 밀린다 - 그 컬럼은 뷰포트 높이에
   묶여 있다(.draft-layout__decks). */
.import-run {
  position: relative;
}

.import-run__list {
  position: absolute;
  top: calc(100% + var(--sp-2));
  left: 0;
  z-index: 5;
  min-width: 20rem;
  max-height: 16rem;
  overflow-y: auto;
  margin: 0;
  padding: var(--sp-2);
  list-style: none;
  display: flex;
  flex-direction: column;
  gap: var(--sp-2);
  background: var(--surface-2);
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  box-shadow: var(--shadow);
}

.import-run__item {
  display: flex;
  align-items: center;
  gap: var(--sp-3);
}

/* 이름이 남는 폭을 다 가져가고, 시각과 버튼은 제 크기만 쓴다. */
.import-run__name {
  flex: 1 1 auto;
  min-width: 0;
}

.import-run__when {
  flex: 0 0 auto;
  font-size: 13px;
  color: var(--text-muted);
}
```

- [ ] **Step 7: Commit**

```bash
git add frontend/src/components/ImportRunButton.tsx frontend/src/components/ImportRunButton.test.tsx frontend/src/lib/savedRunLabel.ts frontend/src/components/SavedRunList.tsx frontend/src/App.css
git commit -m "저장한 결과를 골라 가져오는 버튼을 만든다"
```

---

### Task 4: `RecommendPanel` 배선

**Files:**
- Modify: `frontend/src/components/RecommendPanel.tsx`
- Test: `frontend/src/components/RecommendPanel.test.tsx` (기존 파일 끝에 새 `describe` 추가)

**Interfaces:**
- Consumes: `draftFromResultDecks` (Task 1), `ClearDraftButton` (Task 2), `ImportRunButton` (Task 3), `HELP.draftActions.droppedUnits` (Task 2)
- Produces: 없음(패널 내부 배선)

**배선 규칙** (설계 §E):

| 저장된 모드 | 편성에 넣을 덱 | 덱 개수 |
|---|---|---|
| `raid` · `draft` · `evaluate` | `view.decks.map((d) => d.deck)` | `view.numDecks` |
| `single` | `[view.decks[0]?.deck ?? []]` | 그대로 유지 |

모드는 지금이 `draft`/`evaluate`면 유지, 아니면 `evaluate`로 전환한다.

- [ ] **Step 1: Write the failing tests**

`frontend/src/components/RecommendPanel.test.tsx` 파일 맨 끝에 붙인다. 파일 위쪽의 `nikke`, `fullRoster`, `makeEvaluateSupportedUnits`, `noPersistence`, `renderSettled`, `dropOnDeck`을 그대로 쓴다.

```tsx
describe('RecommendPanel — 편성 초기화와 가져오기', () => {
  const bossOf = (element: 'Fire' | 'Water') => ({
    element,
    core_hittable: false,
    pierce_hits_body_behind_core: false,
    enemy_def: 31784,
    fight_duration: 180,
    part_destructible: false,
    core_diameter_px: null,
    effective_range_band: null,
    elemental_interrupt_required: false,
  })

  /** 5인 덱 하나를 가진 전부-최적화 보관물. 덱 개수 1로 저장돼 있다. */
  const raidRun = (): SavedRun => ({
    id: 'r1',
    name: '보관한 배분',
    savedAt: 1754438400000,
    tab: 'solo',
    view: {
      mode: 'raid',
      boss: bossOf('Water'),
      numDecks: 1,
      decks: [
        {
          deck: ['a', 'b', 'c', 'd', 'e'],
          total_damage: 10,
          burst_damage: 4,
          normal_attack_damage: 3,
          skill_damage: 3,
          hold_burst_slugs: [],
          pinned_slugs: [],
        },
      ],
      combinedTotalDamage: 10,
      excludedSlugs: [],
      leftoverSlugs: [],
    },
  })

  const singleRun = (): SavedRun => ({
    id: 's1',
    name: '보관한 단일 덱',
    savedAt: 1754438400000,
    tab: 'solo',
    view: {
      mode: 'single',
      boss: bossOf('Water'),
      numDecks: 3,
      decks: [
        {
          deck: ['a', 'b', 'c', 'd', 'e'],
          total_damage: 10,
          burst_damage: 4,
          normal_attack_damage: 3,
          skill_damage: 3,
          hold_burst_slugs: [],
        },
      ],
      excludedSlugs: [],
    },
  })

  const openWithRuns = async (runs: SavedRun[], overrides = {}) => {
    vi.mocked(getSupportedUnits).mockResolvedValue(makeEvaluateSupportedUnits())
    const user = userEvent.setup()
    await renderSettled(
      <RecommendPanel roster={fullRoster} {...noPersistence} savedRuns={runs} {...overrides} />,
    )
    return user
  }

  it('전부 최적화 결과를 가져오면 편성과 보스가 함께 들어온다', async () => {
    const user = await openWithRuns([raidRun()])
    await user.click(screen.getByRole('radio', { name: /기대 딜량 계산/ }))

    await user.click(screen.getByRole('button', { name: '저장한 결과 가져오기' }))
    await user.click(screen.getByRole('button', { name: '가져오기' }))

    // 덱 1이 다섯 자리를 다 받았다.
    const deck = screen.getByRole('heading', { name: /덱 1/ }).closest('div')!
    for (const slug of ['A', 'B', 'C', 'D', 'E']) {
      expect(within(deck).getByText(slug)).toBeInTheDocument()
    }
    // 보스도 그 결과의 것으로 바뀌었다. 속성 라디오는 **약점**으로 말하고
    // (BossProfileField가 bossElementFor로 변환한다) BossProfile.element는
    // 보스 본인 속성이다: 'Water' 보스의 약점은 '전격'이다. 기본값은
    // element: null이라 아무 라디오도 안 켜져 있으므로, 이 체크는 가져오기가
    // 실제로 보스를 넣었을 때만 통과한다.
    expect(screen.getByRole('radio', { name: '전격' })).toBeChecked()
  })

  it('단일 덱 결과는 덱 1만 채우고 덱 개수를 건드리지 않는다', async () => {
    const user = await openWithRuns([singleRun()])
    await user.click(screen.getByRole('radio', { name: /기대 딜량 계산/ }))
    await user.selectOptions(screen.getByLabelText('덱 개수'), '2')

    await user.click(screen.getByRole('button', { name: '저장한 결과 가져오기' }))
    await user.click(screen.getByRole('button', { name: '가져오기' }))

    expect(screen.getByLabelText('덱 개수')).toHaveValue('2')
    const deck2 = screen.getByRole('heading', { name: /덱 2/ }).closest('div')!
    expect(within(deck2).queryByText('A')).not.toBeInTheDocument()
  })

  it('편성 칸이 없는 모드에서 가져오면 기대 딜량 계산으로 옮겨간다', async () => {
    const user = await openWithRuns([raidRun()])
    // 기본 모드는 단일 덱이다 - 편성 칸이 없다.

    await user.click(screen.getByRole('button', { name: '저장한 결과 가져오기' }))
    await user.click(screen.getByRole('button', { name: '가져오기' }))

    expect(screen.getByRole('radio', { name: /기대 딜량 계산/ })).toBeChecked()
  })

  it('빈자리만 최적화 중에 가져오면 그 모드에 남는다', async () => {
    const user = await openWithRuns([raidRun()])
    await user.click(screen.getByRole('radio', { name: /빈자리만 최적화/ }))

    await user.click(screen.getByRole('button', { name: '저장한 결과 가져오기' }))
    await user.click(screen.getByRole('button', { name: '가져오기' }))

    expect(screen.getByRole('radio', { name: /빈자리만 최적화/ })).toBeChecked()
  })

  it('미사용으로 둔 니케는 앉히지 않고 몇 기가 빠졌는지 말한다', async () => {
    const user = await openWithRuns([raidRun()], { excludedSlugs: ['c'] })
    await user.click(screen.getByRole('radio', { name: /기대 딜량 계산/ }))

    await user.click(screen.getByRole('button', { name: '저장한 결과 가져오기' }))
    await user.click(screen.getByRole('button', { name: '가져오기' }))

    expect(screen.getByText(HELP.draftActions.droppedUnits(1))).toBeInTheDocument()
    const deck = screen.getByRole('heading', { name: /덱 1/ }).closest('div')!
    expect(within(deck).queryByText('C')).not.toBeInTheDocument()
  })

  it('전체 초기화는 편성만 비우고 보스와 덱 개수는 그대로 둔다', async () => {
    const user = await openWithRuns([])
    await user.click(screen.getByRole('radio', { name: /기대 딜량 계산/ }))
    await user.selectOptions(screen.getByLabelText('덱 개수'), '2')
    await user.click(screen.getByRole('radio', { name: '작열' }))
    dropOnDeck(1, 'a')

    vi.spyOn(window, 'confirm').mockReturnValue(true)
    await user.click(screen.getByRole('button', { name: '전체 초기화' }))

    const deck = screen.getByRole('heading', { name: /덱 1/ }).closest('div')!
    expect(within(deck).queryByText('A')).not.toBeInTheDocument()
    expect(screen.getByLabelText('덱 개수')).toHaveValue('2')
    expect(screen.getByRole('radio', { name: '작열' })).toBeChecked()
    vi.mocked(window.confirm).mockRestore()
  })

  it('단일 덱 모드에는 전체 초기화가 없다', async () => {
    await openWithRuns([])

    expect(screen.queryByRole('button', { name: '전체 초기화' })).not.toBeInTheDocument()
  })
})
```

무엇을 잡는지: 1번은 보스 적용을 빠뜨리면 빨강(요청의 절반이다), 3·4번은 모드 전환 조건을 뒤집으면 하나가 빨강, 5번은 `canSeat`에 벤치 조건을 안 넘기면 빨강, 6번은 초기화가 보스/덱 개수까지 건드리면 빨강, 7번은 초기화 버튼의 모드 조건을 지우면 빨강.

주의: `'수냉'`·`'작열'`은 이 파일이 이미 쓰는 속성 라디오 라벨이다(179·208행). 보스 속성 라디오가 실제로 그 이름인지는 그 테스트들이 보증한다.

- [ ] **Step 2: Run tests to verify they fail**

Run: `npm --prefix frontend test -- --run src/components/RecommendPanel.test.tsx -t '편성 초기화와 가져오기'`
Expected: FAIL — `Unable to find role="button" and name "저장한 결과 가져오기"`

- [ ] **Step 3: import를 더한다**

`frontend/src/components/RecommendPanel.tsx` 상단 import 블록에:

```ts
import { canSeatFrom, draftFromResultDecks } from '../lib/importRun'
import { ClearDraftButton } from './ClearDraftButton'
import { ImportRunButton } from './ImportRunButton'
```

- [ ] **Step 4: 상태와 핸들러를 더한다**

`heldSlug` 상태 선언 바로 뒤에 더한다:

```tsx
  // 방금 가져오기에서 앉히지 못한 니케 수. 다음 가져오기나 초기화까지 남는다 -
  // 5명이어야 할 덱이 4명인 이유를 화면이 말하지 않으면 거짓말이 된다.
  const [droppedCount, setDroppedCount] = useState(0)
```

`restoreRun` 함수 **바로 뒤**에 다음 둘을 더한다:

```tsx
  /** 편성 칸을 비운다. 보스도 덱 개수도 모드도 건드리지 않는다. */
  const clearDraft = () => {
    setDraftValue(makeEmptyDraft(numDecks))
    setDroppedCount(0)
  }

  /** 보관물의 결과 덱을 편성으로 가져온다. 「이 설정으로 폼 채우기」(restoreRun)와
   * 다른 일이다 - 저쪽은 그때의 설정으로 되돌리고, 이쪽은 그때 나온 덱 구성을
   * 편집기에 앉힌다. */
  const importRun = (run: SavedRun) => {
    const view = run.view as SoloRunView
    // 단일 덱 결과는 배분이 아니라 한 덱의 대안 랭킹이라 1위만 가져온다. 덱
    // 개수도 그 결과가 정할 수 있는 값이 아니므로 지금 값을 지킨다.
    const isSingle = view.mode === 'single'
    const deckSlugs = isSingle
      ? [view.decks[0]?.deck ?? []]
      : view.decks.map((deck) => deck.deck)
    const nextNumDecks = isSingle ? numDecks : view.numDecks

    const { draft: imported, droppedSlugs } = draftFromResultDecks(deckSlugs, nextNumDecks, {
      ownedSlugFor: ownedSlugResolver,
      canSeat: canSeatFrom(roster, excludedSlugs),
    })

    // 덱 개수를 먼저 바꾼다 - numDecks를 감시하는 resizeDraft 이펙트가 뒤에
    // 돌면서 방금 넣은 편성을 옛 개수로 자르지 않게 하기 위해서다.
    setNumDecks(nextNumDecks)
    setDraftValue(imported)
    setDroppedCount(droppedSlugs.length)
    setDraft(bossProfileToDraft(view.boss))

    // 편성을 갈아치웠으므로 그 전 편성으로 나온 결과는 화면에서 내린다.
    setDisplayResult(null)
    setDisplayMode(null)
    setDisplayBoss(null)
    // 편성 칸이 없는 모드였다면 받을 칸이 있는 화면으로 데려간다. switchMode가
    // evaluate 결과도 함께 리셋한다.
    switchMode(mode === 'draft' || mode === 'evaluate' ? mode : 'evaluate')
  }
```

`switchMode`는 이 함수보다 아래에 선언돼 있다. `const` 선언이라 호이스팅되지 않으므로, **`switchMode` 선언을 `restoreRun` 위로 옮긴다**(선언만 이동, 본문은 그대로). 옮긴 뒤 `actionButtons` 정의는 그대로 둔다.

- [ ] **Step 5: 액션 행에 버튼을 배선한다**

`actionButtons`(현재 694행 근처)를 다음으로 바꾼다:

```tsx
  const actionButtons = (
    <>
      <button type="submit" className="btn btn--primary" disabled={!canSubmit}>
        {submitLabel}
      </button>
      {/* 무언가 실제로 돌고 있을 때만 - 제출 옆에 상시 놓인 취소는 두 행동
          사이의 선택처럼 읽힌다. `type="button"`이 중요하다: 폼 안의 맨
          버튼은 제출이라, 첫 실행을 멈추는 대신 두 번째를 시작해버린다. */}
      {active.status === 'loading' && (
        <button type="button" className="btn" onClick={active.cancel}>
          취소
        </button>
      )}
      <ImportRunButton runs={savedRuns} draft={draftValue} onImport={importRun} />
      {/* 편성 칸이 있는 모드에만. 이 조건 덕분에 단일 덱·전부 최적화 자리의
          액션 행에는 나오지 않는다. */}
      {(mode === 'draft' || mode === 'evaluate') && (
        <ClearDraftButton draft={draftValue} onClear={clearDraft} />
      )}
      {droppedCount > 0 && (
        <p className="field__error" role="status">
          <HelpText>{HELP.draftActions.droppedUnits(droppedCount)}</HelpText>
        </p>
      )}
      {mode !== 'evaluate' && rosterTooSmall && (
        <p className="field__error" role="alert">
          <HelpText>{HELP.recommend.minRoster(MIN_DECK_ROSTER_SIZE)}</HelpText>
        </p>
      )}
    </>
  )
```

- [ ] **Step 6: Run the new tests**

Run: `npm --prefix frontend test -- --run src/components/RecommendPanel.test.tsx -t '편성 초기화와 가져오기'`
Expected: PASS (7 tests)

- [ ] **Step 7: Run the whole panel suite**

Run: `npm --prefix frontend test -- --run src/components/RecommendPanel.test.tsx`
Expected: PASS — 기존 테스트가 전부 그대로. 실패하면 대개 `/인카운터/`가 아니라 폼 제출 흐름이 바뀐 것이니, 새 버튼의 `type="button"`부터 확인한다.

- [ ] **Step 8: Commit**

```bash
git add frontend/src/components/RecommendPanel.tsx frontend/src/components/RecommendPanel.test.tsx
git commit -m "솔로 탭 액션 행에 초기화와 가져오기를 배선한다"
```

---

### Task 5: `UnionRaidPanel` 배선

**Files:**
- Modify: `frontend/src/components/UnionRaidPanel.tsx`
- Test: `frontend/src/components/UnionRaidPanel.test.tsx` (기존 파일 끝에 새 `describe` 추가)

**Interfaces:**
- Consumes: Task 1~3의 산출물 전부. 유니온 뷰는 `UnionRunView { numBattles, bosses, draft, decks, combinedTotalDamage, excludedSlugs }`.
- Produces: 없음

- [ ] **Step 1: Write the failing tests**

`frontend/src/components/UnionRaidPanel.test.tsx` 파일 맨 끝에 붙인다. 파일 위쪽의 `roster`, `supportedUnits`, `renderPanel`, `fillDecks`, `dropOnDeck`을 그대로 쓴다.

```tsx
describe('UnionRaidPanel — 편성 초기화와 가져오기', () => {
  const bossOf = (element: 'Fire' | 'Water') => ({
    element,
    core_hittable: false,
    pierce_hits_body_behind_core: false,
    enemy_def: 31784,
    fight_duration: 180,
    part_destructible: false,
    core_diameter_px: null,
    effective_range_band: null,
    elemental_interrupt_required: false,
  })

  const deckOf = (slugs: string[]) => ({
    deck: slugs,
    total_damage: 10,
    burst_damage: 4,
    normal_attack_damage: 3,
    skill_damage: 3,
    hold_burst_slugs: [],
  })

  /** 두 전투짜리 보관물. */
  const unionRun = (): SavedRun => ({
    id: 'u1',
    name: '보관한 유니온',
    savedAt: 1754438400000,
    tab: 'union',
    view: {
      numBattles: 2,
      bosses: [bossOf('Water'), bossOf('Fire')],
      draft: {
        decks: [
          ['u0', 'u1', 'u2', 'u3', 'u4'].map((slug) => ({ slug, locked: false })),
          ['u5', 'u6', 'u7', 'u8', 'u9'].map((slug) => ({ slug, locked: false })),
        ],
      },
      decks: [
        deckOf(['u0', 'u1', 'u2', 'u3', 'u4']),
        deckOf(['u5', 'u6', 'u7', 'u8', 'u9']),
      ],
      combinedTotalDamage: 20,
      excludedSlugs: [],
    },
  })

  it('가져오면 전투 수·보스·편성이 함께 들어온다', async () => {
    const user = userEvent.setup()
    renderPanel({ savedRuns: [unionRun()] })

    await user.click(screen.getByRole('button', { name: '저장한 결과 가져오기' }))
    await user.click(screen.getByRole('button', { name: '가져오기' }))

    expect(screen.getByLabelText('전투 수')).toHaveValue('2')
    // 덱 제목은 속성이 있으면 약점 낱말이 된다(bossHeading). 'Water' 보스의
    // 약점은 '전격', 'Fire' 보스의 약점은 '수냉'이다. 기본 보스는
    // element: null이라 제목이 '덱 N'이므로, 제목이 바뀌었다는 것 자체가
    // 보스가 들어왔다는 증거다.
    const deck1 = screen.getByRole('heading', { name: /전격/ }).closest('div')!
    expect(within(deck1).getByText('U0')).toBeInTheDocument()
    expect(screen.getByRole('heading', { name: /수냉/ })).toBeInTheDocument()
  })

  it('전체 초기화는 편성만 비운다', async () => {
    const user = userEvent.setup()
    renderPanel()
    await fillDecks()

    vi.spyOn(window, 'confirm').mockReturnValue(true)
    await user.click(screen.getByRole('button', { name: '전체 초기화' }))

    expect(screen.getByRole('button', { name: /인카운터/ })).toBeDisabled()
    expect(screen.getByLabelText('전투 수')).toHaveValue('3')
    vi.mocked(window.confirm).mockRestore()
  })

  it('저장한 결과가 없으면 가져오기를 누를 수 없다', () => {
    renderPanel()

    expect(screen.getByRole('button', { name: '저장한 결과 가져오기' })).toBeDisabled()
  })
})
```

무엇을 잡는지: 1번은 보스 배열이나 전투 수 적용을 빠뜨리면 빨강, 2번은 초기화가 전투 수까지 건드리면 빨강(그리고 편성이 안 비면 인카운터가 여전히 활성이라 빨강).

셀렉터는 전부 확인된 것이다: `전투 수`는 `UnionRaidPanel.tsx:234`의 라벨이고, 덱 제목 규칙은 `lib/bossLabel.ts`의 `bossHeading`이다(속성 있으면 약점 낱말, 없으면 `덱 N`). `evaluation.reset()`은 `hooks/useEvaluateDecks.ts:55`가 내보낸다.

- [ ] **Step 2: Run tests to verify they fail**

Run: `npm --prefix frontend test -- --run src/components/UnionRaidPanel.test.tsx -t '편성 초기화와 가져오기'`
Expected: FAIL — 버튼을 찾지 못한다

- [ ] **Step 3: import와 리졸버를 더한다**

`frontend/src/components/UnionRaidPanel.tsx` 상단 import에:

```ts
import { canSeatFrom, draftFromResultDecks } from '../lib/importRun'
import { ClearDraftButton } from './ClearDraftButton'
import { ImportRunButton } from './ImportRunButton'
import { ownedSlugFor, ownedSlugIndex } from '../types/supportedUnit'
```

(`SupportedUnit` 타입은 이미 그 파일에서 `type` import 중이므로, 값 import를 따로 더한다.)

`heldSlug` 상태 선언 뒤에:

```tsx
  // 방금 가져오기에서 앉히지 못한 니케 수. 솔로 탭과 같은 이유로 화면에 남긴다.
  const [droppedCount, setDroppedCount] = useState(0)
```

`changeNumBattles` 정의 뒤에:

```tsx
  // 결과가 부르는 슬러그를 유저가 가진 슬러그로 되돌린다 - 솔로 탭이 쓰는 것과
  // 같은 표다(bready-lingering -> bready).
  const ownedSlugs = useMemo(() => ownedSlugIndex(supportedUnits), [supportedUnits])
```

- [ ] **Step 4: 핸들러를 더한다**

`handleSubmit` 정의 **앞**에:

```tsx
  /** 편성만 비운다. 전투 수도 보스 설정도 그대로다. */
  const clearDraft = () => {
    setDraftValue(makeEmptyDraft(numBattles))
    setDroppedCount(0)
  }

  const importRun = (run: SavedRun) => {
    const view = run.view as UnionRunView
    const { draft: imported, droppedSlugs } = draftFromResultDecks(
      view.decks.map((deck) => deck.deck),
      view.numBattles,
      {
        ownedSlugFor: (slug) => ownedSlugFor(slug, ownedSlugs),
        canSeat: canSeatFrom(roster, excludedSlugs),
      },
    )

    // changeNumBattles가 bosses/draftValue도 함께 바꾸므로, 뒤따르는 두 setState가
    // 최종 값을 쥔다 - React가 셋을 한 렌더로 묶는다(onRestore와 같은 순서다).
    changeNumBattles(view.numBattles)
    setBosses(view.bosses.map(bossProfileToDraft))
    setDraftValue(imported)
    setDroppedCount(droppedSlugs.length)
    // 편성을 갈아치웠으므로 그 전 편성으로 나온 결과는 화면에서 내린다.
    evaluation.reset()
  }
```

`evaluation.reset()`은 `hooks/useEvaluateDecks.ts:55`가 내보내는 것을 확인했다.

- [ ] **Step 5: 액션 행에 배선한다**

`UnionRaidPanel.tsx` 367~372행의 액션 행을 다음으로 바꾼다:

```tsx
              <div className="recommend-form__actions">
                {missingActualStats && <HelpText>{HELP.sync.unionNeedsActualStats}</HelpText>}
                <button type="submit" className="btn btn--primary" disabled={!canSubmit}>
                  {evaluation.status === 'loading' ? '계산 중…' : '인카운터!'}
                </button>
                <ImportRunButton runs={savedRuns} draft={draftValue} onImport={importRun} />
                <ClearDraftButton draft={draftValue} onClear={clearDraft} />
                {droppedCount > 0 && (
                  <p className="field__error" role="status">
                    <HelpText>{HELP.draftActions.droppedUnits(droppedCount)}</HelpText>
                  </p>
                )}
              </div>
```

- [ ] **Step 6: Run the tests**

Run: `npm --prefix frontend test -- --run src/components/UnionRaidPanel.test.tsx`
Expected: PASS — 새 3개와 기존 전부

- [ ] **Step 7: Commit**

```bash
git add frontend/src/components/UnionRaidPanel.tsx frontend/src/components/UnionRaidPanel.test.tsx
git commit -m "유니온 탭 액션 행에 초기화와 가져오기를 배선한다"
```

---

### Task 6: 전체 검증

**Files:** 없음(검증만). 고칠 것이 나오면 그 파일.

- [ ] **Step 1: 타입체크**

Run: `npx --prefix frontend tsc -b --noEmit frontend`
Expected: 출력 없음. `npm test`는 타입을 보지 않으므로 이 단계를 건너뛰면 타입 에러가 초록 뒤에 숨는다.

- [ ] **Step 2: 프론트 전체 스위트**

Run: `npm --prefix frontend test -- --run`
Expected: 기존 828 + 새 20 남짓이 전부 통과. 실패가 나오면 새 버튼이 기존 쿼리에 걸린 것인지부터 본다(`/가져오기/` 같은 느슨한 정규식을 쓰는 기존 테스트가 있는지 `grep`).

- [ ] **Step 3: lint**

Run: `npm --prefix frontend run lint`
Expected: exit 0

- [ ] **Step 4: 실제 앱에서 눈으로 확인**

Vitest는 CSS를 보지 않는다(`css: false`). 이 작업은 색·정렬·팝오버가 절반이므로 반드시 띄워서 본다.

```bash
# 백엔드(포트 8000이 이미 떠 있으면 그대로 쓴다 - Fienn의 --reload 개발 서버를 죽이지 말 것)
cd backend && python -m uvicorn app.api:app --port 8000
# 프론트
npm --prefix frontend run dev
```

확인할 것:
1. 빈자리만 최적화 모드에서 액션 행이 `[인카운터!] [저장한 결과 가져오기] ……… [전체 초기화]`로 서는가.
2. 전체 초기화가 빨강 채움에 근검정 글자인가, 가져오기가 외곽선인가.
3. 가져오기를 눌렀을 때 목록이 sticky 덱 컬럼에 잘리지 않고 뜨는가(`z-index: 5`가 팔레트 hover 카드에 지는지 확인).
4. 저장한 결과가 없을 때 두 버튼의 비활성 모습이 다른 비활성 버튼과 같은가.
5. 유니온 탭에서도 1~4가 같은가.

어긋나면 `App.css`를 고치고 다시 본다.

- [ ] **Step 5: Commit**

CSS를 고쳤다면:

```bash
git add frontend/src/App.css
git commit -m "액션 행 버튼의 배치를 실제 화면에 맞춘다"
```

- [ ] **Step 6: 문서를 갱신한다**

`docs/roadmap.md`의 To-Do에 이 작업에 해당하는 항목이 있으면 체크한다. 없으면 아무것도 하지 않는다 — 없는 항목을 새로 만들지 않는다.

```bash
git add docs/roadmap.md
git commit -m "덱 편성 조작 항목을 로드맵에 반영한다"
```

---

## 자체 검토 결과

**스펙 대응**: §A→Task 1, §B→Task 3, §C→Task 2, §D→Task 1의 `canSeat` + Task 4·5의 배선(벤치·로스터 두 조건), §E→Task 4·5, §F→Task 2·3의 CSS 단계, §G→Task 2의 문구 단계. 스펙의 테스트 17개는 Task 1(1~5번), Task 2(6~7번), Task 3(8~11번), Task 4·5(12~17번)에 흩어져 들어갔다.

**검토에서 고친 것**: 첫 초안은 보스 적용을 `radio name: '수냉'`으로 재고 있었다. 속성 라디오는 **약점**으로 말하고 `BossProfile.element`는 **보스 본인 속성**이라(`lib/elementAdvantage.ts`), 'Water' 보스가 켜는 라디오는 '전격'이다. 그대로 뒀으면 구현이 맞아도 빨간 테스트가 나왔다.

**셀렉터 출처**: `덱 개수`는 `RecommendPanel.tsx:788`, `전투 수`는 `UnionRaidPanel.tsx:234`, 덱 제목 규칙은 `lib/bossLabel.ts`, 속성 낱말은 `lib/elementName.ts`(작열·수냉·풍압·철갑·전격), 약점 표는 `lib/elementAdvantage.ts`. 전부 열어서 확인했다.
