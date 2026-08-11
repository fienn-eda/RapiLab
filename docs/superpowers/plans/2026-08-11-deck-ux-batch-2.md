# 덱 편성 조작 2차 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fienn이 앱을 쓰며 적어 준 덱 편성 조작 5건 — 팔레트 자동 덱 전환, 덱 간
이동 표적, 덱 선택 표적, 초성·영문 검색, 미란다 계산기 교환 버그 — 를 고친다.

**Architecture:** 순수 함수를 먼저 만들고(`firstDeckWithRoom`, `toChosung`),
컴포넌트는 그걸 배선만 한다. 덱을 향한 클릭은 `DraftEditor`의 덱 컨테이너에 단
껍데기 핸들러 하나가 받고, 안쪽 컨트롤이 `stopPropagation`으로 자기 몫을
가져간다. 검색은 `unitFilter.ts`의 이름 대조 한 곳만 세 갈래로 넓힌다.

**Tech Stack:** React 19 · TypeScript · Vite · Vitest + @testing-library/react +
@testing-library/user-event · jsdom

설계 근거: `docs/superpowers/specs/2026-08-11-deck-ux-batch-2-design.md`

## Global Constraints

- 작업 위치는 워크트리 `C:\Users\fienn\Desktop\NikkeDeckBuilder\.claude\worktrees\deck-ux-batch-2`,
  브랜치 `worktree-deck-ux-batch-2`, base `daad08e8`. 메인 체크아웃은 건드리지 않는다.
- **기준선: 프론트 테스트 778 passed / 68 files, 타입에러 0.** 어느 태스크가
  끝나도 이보다 줄면 안 된다.
- 테스트 실행: `npm --prefix frontend test -- <경로>` (cwd는 저장소 루트, 경로는
  `frontend/` 기준의 상대 경로 — 예 `src/types/draft.test.ts`). 전체는 인자 없이.
- **타입체크: `npx --prefix frontend tsc -b --noEmit frontend`** — `--prefix`는 tsc
  실행 파일을 찾는 곳이고, 맨 뒤 `frontend`는 tsconfig가 있는 프로젝트 경로다.
  cwd는 루트 그대로다. **vitest는 타입을 안 보므로 이 명령을 따로 돌린다.**
- Vitest는 `css: false`다. CSS 변경은 테스트가 못 잰다 — 앱을 띄워서 확인한다.
- 주석·커밋 메시지는 **무엇을·왜**만 적는다. "예전엔 이랬다", "N을 M으로 바꿨다"
  같은 변경 이력은 금지(프로젝트 CLAUDE.md).
- 화면 문구는 `frontend/src/lib/helpText.ts`의 `HELP`를 거친다. 새 문구를 컴포넌트에
  하드코딩하지 않는다. (단 `placeholder`는 기존에도 인라인이므로 그대로 인라인이다.)
- 커밋은 태스크마다 한 번. `git add`는 반드시 그 태스크가 만진 파일만 명시한다
  (`git add -A` 금지).

## File Structure

| 파일 | 책임 | 태스크 |
|---|---|---|
| `frontend/src/components/MirandaCalculatorPanel.tsx` | 미란다 화면이 든 유닛을 안다 | 1 |
| `frontend/src/types/draft.ts` | `firstDeckWithRoom` — 팔레트가 향할 덱 | 2 |
| `frontend/src/components/RecommendPanel.tsx` | 솔로 탭 팔레트 배선 | 3 |
| `frontend/src/components/UnionRaidPanel.tsx` | 유니온 탭 팔레트 배선 | 3 |
| `frontend/src/components/DraftEditor.tsx` | 덱 껍데기 클릭 + 안쪽 컨트롤 전파 차단 | 4 |
| `frontend/src/App.css` | 누를 수 있는 덱의 커서 | 4 |
| `frontend/src/lib/helpText.ts` | 조작 안내 문구 | 4 |
| `frontend/src/lib/koreanSearch.ts` (신규) | 초성 추출·초성 질의 판별 | 5 |
| `frontend/src/lib/unitFilter.ts` | 이름 대조 세 갈래 + `UnitFacets.slug` | 6 |
| `frontend/src/components/UnitPalette.tsx` | facets에 slug | 6 |
| `frontend/src/components/RosterGrid.tsx` | facets에 slug | 6 |
| `frontend/src/components/UnitFilterBar.tsx` | 검색창 placeholder | 6 |
| `docs/roadmap.md` | 착륙 기록 | 7 |

---

### Task 1: 미란다 계산기가 든 유닛을 안다

솔로·유니온 패널에는 있고 미란다 패널에만 빠진 배선이다. `DraftEditor`에
`onHeldSlugChange`를 안 넘기므로 패널은 좌석이 들렸다는 것을 모르고, 팔레트
클릭이 꽉 찬 덱에 `placeUnit`을 불러 조용히 거절당한다.

**Files:**
- Modify: `frontend/src/components/MirandaCalculatorPanel.tsx`
- Test: `frontend/src/components/MirandaCalculatorPanel.test.tsx`

**Interfaces:**
- Consumes: `replaceUnit(draft, replacedSlug, slug)` — 이미 `./DraftEditor`가
  export한다. `DraftEditor`의 `onHeldSlugChange?: (slug: string | null) => void`.
- Produces: 없음. 이 태스크는 다른 태스크가 참조하는 이름을 만들지 않는다.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`frontend/src/components/MirandaCalculatorPanel.test.tsx`의 `describe('MirandaCalculatorPanel', ...)`
블록 안, `'배치 버튼만으로 빈자리를 채운다'` 테스트 바로 뒤에 넣는다.

```tsx
  // 덱이 꽉 차면 배치 버튼은 placeUnit으로 아무것도 못 한다. 자리를 비우려면
  // 좌석을 두 번 눌러 빼고 다시 앉혀야 했는데, 그게 되는지조차 화면에 안
  // 나타난다 - 솔로/유니온 탭에는 있는 「들고 팔레트를 눌러 물려주기」가
  // 이 화면에만 없었다.
  it('앉은 니케를 들고 팔레트 니케를 누르면 그 자리를 물려준다', async () => {
    renderPanel([...FULL, 'snow-white'].map(state))

    for (const name of ['크라운', '에이다 웡', '신데렐라', '이사벨']) {
      await userEvent.click(screen.getByRole('button', { name: `${name} 배치` }))
    }
    expect(screen.getByText('5/5')).toBeInTheDocument()

    await userEvent.click(screen.getByRole('button', { name: '덱 1의 크라운' }))
    await userEvent.click(screen.getByRole('button', { name: '백설공주 배치' }))

    expect(screen.getByRole('button', { name: '덱 1의 백설공주' })).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: '덱 1의 크라운' })).not.toBeInTheDocument()
    // 하나 나가고 하나 들어왔으므로 자리 수는 그대로다. 미란다도 그대로다.
    expect(screen.getByText('5/5')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: /덱 1의 미란다/ })).not.toBeInTheDocument()
    // 밀려난 크라운은 다시 앉힐 수 있는 상태로 팔레트에 돌아온다.
    expect(screen.getByRole('button', { name: '크라운 배치' })).toBeInTheDocument()
  })
```

- [ ] **Step 2: 실패를 확인한다**

```
npm --prefix frontend test -- src/components/MirandaCalculatorPanel.test.tsx
```

Expected: FAIL. `덱 1의 백설공주` 버튼을 못 찾는다 — 팔레트 클릭이 꽉 찬 덱에
`placeUnit`을 불러 아무 일도 안 일어났기 때문이다.

- [ ] **Step 3: 배선을 넣는다**

`MirandaCalculatorPanel.tsx` 상단 import에서 `replaceUnit`을 추가한다:

```ts
import { DraftEditor, placeUnit, replaceUnit } from './DraftEditor'
```

`const [busy, setBusy] = useState(false)` 아래에 상태를 추가한다:

```ts
  // 팔레트가 DraftEditor 밖에 있어서, 그 안에서 들린 유닛을 이 사본으로
  // 따라 안다 - 팔레트 클릭을 "빈자리에 앉히기"와 "든 유닛에게 자리
  // 물려주기"로 가르는 데 쓴다.
  const [heldSlug, setHeldSlug] = useState<string | null>(null)
```

`UnitPalette`의 `onSeat`을 바꾼다:

```tsx
          onSeat={(slug) => {
            if (heldSlug) {
              // 들고 있던 자리를 팔레트 유닛에게 내준다. 들고 있던 쪽은
              // 풀로 돌아간다.
              setDraft((current) => replaceUnit(current, heldSlug, slug))
              setHeldSlug(null)
              return
            }
            setDraft((current) => placeUnit(current, 0, slug))
          }}
```

`DraftEditor`에 알림을 넘긴다 — `fixedSlugs` 줄 뒤에 추가한다:

```tsx
            fixedSlugs={[mirandaSlug]}
            onHeldSlugChange={setHeldSlug}
```

- [ ] **Step 4: 통과를 확인한다**

```
npm --prefix frontend test -- src/components/MirandaCalculatorPanel.test.tsx
npx --prefix frontend tsc -b --noEmit frontend
```

Expected: 두 명령 다 통과. 기존 7개 테스트도 그대로 초록이어야 한다.

- [ ] **Step 5: 커밋**

```bash
git add frontend/src/components/MirandaCalculatorPanel.tsx frontend/src/components/MirandaCalculatorPanel.test.tsx
git commit -m "미란다 계산기도 든 니케를 안다 - 꽉 찬 덱에서 팔레트로 교환한다"
```

---

### Task 2: `firstDeckWithRoom` — 팔레트가 향할 덱

순수 함수 하나. UI 없이 이것만 먼저 못 박는다.

**Files:**
- Modify: `frontend/src/types/draft.ts`
- Test: `frontend/src/types/draft.test.ts`

**Interfaces:**
- Consumes: 같은 파일의 `Draft`, `MAX_DRAFT_SEATS_PER_DECK`.
- Produces: `firstDeckWithRoom(draft: Draft, from: number, numDecks: number): number | null`
  — Task 3이 `RecommendPanel`·`UnionRaidPanel`에서 쓴다.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`frontend/src/types/draft.test.ts` 맨 아래에 붙인다. 파일 맨 위 import에
`firstDeckWithRoom`을 추가하는 것을 잊지 말 것 (기존 import 목록에 이어 붙인다).

```ts
describe('firstDeckWithRoom', () => {
  const deck = (count: number) =>
    Array.from({ length: count }, (_, i) => ({ slug: `u${i}`, locked: false }))

  it('활성 덱에 자리가 있으면 그 덱이다', () => {
    expect(firstDeckWithRoom({ decks: [deck(0), deck(0)] }, 0, 2)).toBe(0)
    expect(firstDeckWithRoom({ decks: [deck(4), deck(0)] }, 0, 2)).toBe(0)
  })

  it('활성 덱이 꽉 차면 다음 덱이다', () => {
    expect(firstDeckWithRoom({ decks: [deck(5), deck(0)] }, 0, 2)).toBe(1)
  })

  // 앞 덱을 비워 두고 뒤에서 채우다 끝에 닿았을 때, 되돌아가지 않으면 빈자리를
  // 두고도 "전부 찼다"가 된다.
  it('뒤가 다 차 있으면 처음으로 되돌아간다', () => {
    expect(firstDeckWithRoom({ decks: [deck(0), deck(5), deck(5)] }, 1, 3)).toBe(0)
    expect(firstDeckWithRoom({ decks: [deck(0), deck(5), deck(5)] }, 2, 3)).toBe(0)
  })

  it('전부 차 있으면 null이다', () => {
    expect(firstDeckWithRoom({ decks: [deck(5), deck(5)] }, 0, 2)).toBeNull()
  })

  // 덱 개수를 줄인 직후에는 draft.decks가 numDecks보다 길다(리사이즈 이펙트가
  // 아직 안 돌았다). 화면에 없는 덱에 앉히면 유저는 유닛이 사라진 것을 본다.
  it('numDecks 밖의 덱은 보지 않는다', () => {
    expect(firstDeckWithRoom({ decks: [deck(5), deck(0)] }, 0, 1)).toBeNull()
  })

  // 반대로 늘린 직후에는 decks가 numDecks보다 짧다. 없는 덱을 골라 주면
  // placeUnit이 조용히 거절해서, 활성 덱만 옮겨가고 아무도 안 앉는다.
  it('decks 배열에 아직 없는 자리는 건너뛴다', () => {
    expect(firstDeckWithRoom({ decks: [deck(5)] }, 0, 3)).toBeNull()
  })
})
```

- [ ] **Step 2: 실패를 확인한다**

```
npm --prefix frontend test -- src/types/draft.test.ts
```

Expected: FAIL — `firstDeckWithRoom is not a function` (혹은 import 해석 실패).

- [ ] **Step 3: 함수를 쓴다**

`frontend/src/types/draft.ts` 맨 아래에 추가한다:

```ts
/** `from`부터 앞으로, 끝까지 가면 처음으로 되돌아 훑어 빈자리가 있는 첫 덱.
 * 전부 찼으면 null.
 *
 * 팔레트 클릭이 어느 덱에 앉는지와, 앉힌 뒤 활성 덱이 어디로 가는지를 이 하나가
 * 정한다 - 그래서 「덱이 차면 다음 덱으로 넘어간다」와 「꽉 찬 덱을 직접 골라
 * 두고 팔레트를 눌렀을 때」가 같은 규칙으로 풀린다.
 *
 * `numDecks` 밖은 보지 않고, decks 배열에 아직 없는 자리는 건너뛴다. 덱 개수를
 * 방금 바꿨을 때 저장된 draft와 화면의 덱 수가 한 렌더 어긋나는데, 그때 화면에
 * 없는 덱을 고르면 placeUnit이 조용히 거절해 아무도 안 앉는다. */
export const firstDeckWithRoom = (
  draft: Draft,
  from: number,
  numDecks: number,
): number | null => {
  for (let offset = 0; offset < numDecks; offset += 1) {
    const index = (from + offset) % numDecks
    const seats = draft.decks[index]
    if (seats !== undefined && seats.length < MAX_DRAFT_SEATS_PER_DECK) return index
  }
  return null
}
```

- [ ] **Step 4: 통과를 확인한다**

```
npm --prefix frontend test -- src/types/draft.test.ts
npx --prefix frontend tsc -b --noEmit frontend
```

Expected: 둘 다 통과.

- [ ] **Step 5: 커밋**

```bash
git add frontend/src/types/draft.ts frontend/src/types/draft.test.ts
git commit -m "팔레트가 향할 덱을 고르는 규칙을 함수 하나로 둔다"
```

---

### Task 3: 팔레트가 빈 덱을 찾아 앉히고 활성 덱을 따라 옮긴다

두 패널의 `onSeat`이 같은 모양으로 바뀐다. 지금은 둘 다 `seatDeck`에 그냥
`placeUnit`을 불러, 그 덱이 꽉 차 있으면 조용히 아무 일도 안 한다.

**Files:**
- Modify: `frontend/src/components/RecommendPanel.tsx` (약 981-990행의 `onSeat`)
- Modify: `frontend/src/components/UnionRaidPanel.tsx` (약 302-311행의 `onSeat`)
- Test: `frontend/src/components/RecommendPanel.test.tsx`
- Test: `frontend/src/components/UnionRaidPanel.test.tsx`

**Interfaces:**
- Consumes: Task 2의 `firstDeckWithRoom(draft, from, numDecks): number | null`,
  기존 `placeUnit(draft, deckIndex, slug, locked?)`, `replaceUnit(draft, replacedSlug, slug)`.
- Produces: 없음.

- [ ] **Step 1: 유니온 탭의 실패하는 테스트를 쓴다**

`frontend/src/components/UnionRaidPanel.test.tsx`의 `describe('UnionRaidPanel', ...)`
안, `'배치 버튼은 덱 1이 아니라 활성 덱을 채운다'` 바로 뒤에 넣는다. 이 파일의
로스터는 `u0`..`u14` 15기, 전투 3회 × 5자리라 딱 맞아떨어진다.

```tsx
  // Fienn이 든 예: 팔레트에서 15명을 누르면 덱 3개가 차야 한다. 지금은 덱 1이
  // 찬 뒤로 열 번의 클릭이 전부 조용히 삼켜진다.
  it('덱이 차면 다음 덱으로 넘어가, 15번 누르면 세 덱이 다 찬다', async () => {
    const user = userEvent.setup()
    renderPanel()
    await screen.findByRole('button', { name: /u0 배치/i })

    for (let i = 0; i < 15; i += 1) {
      await user.click(screen.getByRole('button', { name: `U${i} 배치` }))
    }

    expect(screen.getAllByText(/^\d\/5$/).map((e) => e.textContent)).toEqual([
      '5/5',
      '5/5',
      '5/5',
    ])
  })

  // 다음 클릭이 어디로 갈지는 눌러 보기 전에 보여야 한다. 앉힌 「직후」 상태로
  // 다시 훑지 않으면 표시는 여섯 번째 클릭까지 덱 1에 남는다.
  it('덱이 차는 순간 활성 표시가 다음 덱으로 옮겨간다', async () => {
    const user = userEvent.setup()
    renderPanel()
    await screen.findByRole('button', { name: /u0 배치/i })

    for (let i = 0; i < 5; i += 1) {
      await user.click(screen.getByRole('button', { name: `U${i} 배치` }))
    }

    expect(screen.getByRole('button', { name: '덱 1 활성 덱으로 선택' }))
      .toHaveAttribute('aria-pressed', 'false')
    expect(screen.getByRole('button', { name: '덱 2 활성 덱으로 선택' }))
      .toHaveAttribute('aria-pressed', 'true')
  })
```

- [ ] **Step 2: 솔로 탭의 실패하는 테스트를 쓴다**

`frontend/src/components/RecommendPanel.test.tsx`에서 `const supportedUnits = ['a', 'b', 'c', 'd', 'e'].map(...)`
가 선언된 **draft 모드 describe 블록**(약 522행) 안, `'sends the built draft, spanning multiple decks, to the raid endpoint'`
바로 뒤에 넣는다. 그 블록의 `supportedUnits`와 `fullRoster`를 그대로 쓴다.

```tsx
  // 같은 규칙이 두 패널에 각각 배선돼 있어 한쪽만 고치면 다른 쪽이 조용히
  // 낡는다.
  it('덱이 차면 팔레트가 다음 덱에 앉힌다', async () => {
    const user = userEvent.setup()
    const sixUnits = [
      ...supportedUnits,
      { slug: 'f', name: 'F', burstTier: 1 as const, element: 'Iron' as const },
    ]
    vi.mocked(getSupportedUnits).mockResolvedValue(sixUnits)

    render(<RecommendPanel roster={[...fullRoster, nikke('f')]} {...noPersistence} />)
    await user.click(screen.getByLabelText(/빈자리만 최적화/i))
    await screen.findByRole('button', { name: 'A 배치' })

    for (const name of ['A', 'B', 'C', 'D', 'E', 'F']) {
      await user.click(screen.getByRole('button', { name: `${name} 배치` }))
    }

    expect(screen.getByRole('button', { name: '덱 1의 A' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: '덱 2의 F' })).toBeInTheDocument()
  })
```

- [ ] **Step 3: 실패를 확인한다**

```
npm --prefix frontend test -- src/components/UnionRaidPanel.test.tsx src/components/RecommendPanel.test.tsx
```

Expected: 새 테스트 3개 전부 FAIL.
- 유니온 첫 번째: `['5/5', '0/5', '0/5']`을 받는다 — u5부터 열 번이 삼켜졌다.
- 유니온 두 번째: 덱 1이 여전히 `aria-pressed="true"`다.
- 솔로: `덱 2의 F` 버튼이 없다 — F가 어디에도 안 앉았다.

- [ ] **Step 4: 두 패널을 고친다**

`RecommendPanel.tsx`의 import에 `firstDeckWithRoom`을 추가한다. 기존 draft 타입
import 줄을 이렇게 만든다:

```ts
import { firstDeckWithRoom, isDraftComplete, makeEmptyDraft, resizeDraft, type Draft } from '../types/draft'
```

`UnitPalette`의 `onSeat`을 이렇게 바꾼다:

```tsx
                onSeat={(slug) => {
                  if (heldSlug) {
                    // 들고 있던 자리를 팔레트 유닛에게 내준다. 들고 있던
                    // 쪽은 풀로 돌아간다. 자리를 물려받는 것이라 덱 크기가
                    // 안 변하므로 활성 덱도 그대로다.
                    setDraftValue((current) => replaceUnit(current, heldSlug, slug))
                    setHeldSlug(null)
                    return
                  }
                  // 활성 덱이 꽉 차 있으면 다음 빈 덱을 찾는다. 클릭 하나는
                  // 한 번의 배치라 클로저의 draftValue가 최신이다 - 갱신자
                  // 안에서 setActiveDeck을 부르면 갱신자가 더 이상 순수하지
                  // 않고 StrictMode가 두 번 부른다.
                  const target = firstDeckWithRoom(draftValue, seatDeck, numDecks)
                  if (target === null) return
                  const next = placeUnit(draftValue, target, slug)
                  setDraftValue(next)
                  // 앉힌 직후로 다시 훑는다 - 방금 찬 덱이면 표시가 곧바로
                  // 다음 덱으로 넘어가, 다음 클릭이 어디로 갈지 보인다.
                  setActiveDeck(firstDeckWithRoom(next, target, numDecks) ?? target)
                }}
```

`UnionRaidPanel.tsx`도 같은 모양으로 바꾼다. 덱 개수 변수 이름만 다르다
(`numDecks`가 아니라 `numBattles`):

```tsx
              onSeat={(slug) => {
                if (heldSlug) {
                  // 들고 있던 자리를 팔레트 유닛에게 내준다. 들고 있던 쪽은
                  // 풀로 돌아간다. 자리를 물려받는 것이라 덱 크기가 안 변하므로
                  // 활성 덱도 그대로다.
                  setDraftValue((current) => replaceUnit(current, heldSlug, slug))
                  setHeldSlug(null)
                  return
                }
                // 활성 덱이 꽉 차 있으면 다음 빈 덱을 찾는다. 클릭 하나는 한
                // 번의 배치라 클로저의 draftValue가 최신이다 - 갱신자 안에서
                // setActiveDeck을 부르면 갱신자가 더 이상 순수하지 않고
                // StrictMode가 두 번 부른다.
                const target = firstDeckWithRoom(draftValue, seatDeck, numBattles)
                if (target === null) return
                const next = placeUnit(draftValue, target, slug)
                setDraftValue(next)
                // 앉힌 직후로 다시 훑는다 - 방금 찬 덱이면 표시가 곧바로 다음
                // 덱으로 넘어가, 다음 클릭이 어디로 갈지 보인다.
                setActiveDeck(firstDeckWithRoom(next, target, numBattles) ?? target)
              }}
```

`UnionRaidPanel.tsx`의 import에도 `firstDeckWithRoom`을 추가한다. 이 파일이
`../types/draft`에서 무엇을 가져오는지 먼저 읽고, 그 목록에 이어 붙일 것 —
`RecommendPanel`과 가져오는 이름이 다르다.

- [ ] **Step 5: 통과를 확인한다**

```
npm --prefix frontend test -- src/components/UnionRaidPanel.test.tsx src/components/RecommendPanel.test.tsx
npx --prefix frontend tsc -b --noEmit frontend
```

Expected: 전부 통과. 특히 유니온의 기존 `'배치 버튼은 덱 1이 아니라 활성 덱을
채운다'`가 그대로 초록이어야 한다 — 활성 덱에 자리가 있으면 여전히 그 덱이다.

- [ ] **Step 6: 커밋**

```bash
git add frontend/src/components/RecommendPanel.tsx frontend/src/components/UnionRaidPanel.tsx frontend/src/components/RecommendPanel.test.tsx frontend/src/components/UnionRaidPanel.test.tsx
git commit -m "팔레트가 빈 덱을 찾아 앉히고 활성 덱이 따라간다"
```

---

### Task 4: 덱 테두리 안 전체가 표적이다

`DraftEditor`의 덱 컨테이너가 클릭을 받는다. **든 것이 있으면 이동, 없으면
선택.** 안쪽 컨트롤은 자기 몫을 `stopPropagation`으로 가져간다.

**Files:**
- Modify: `frontend/src/components/DraftEditor.tsx`
- Modify: `frontend/src/App.css`
- Modify: `frontend/src/lib/helpText.ts`
- Test: `frontend/src/components/DraftEditor.test.tsx`

**Interfaces:**
- Consumes: 같은 파일의 `moveUnit(draft, deckIndex, slug)` — 꽉 찬 덱과 「이미 그
  덱」을 거절하며 **입력 객체를 그대로** 돌려준다. 이 동일성이 가드다.
- Produces: 없음. 컴포넌트 안에서 끝난다.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`frontend/src/components/DraftEditor.test.tsx`의 `describe('DraftEditor', ...)`
안, `describe('든 유닛 알림 (onHeldSlugChange)', ...)` 앞에 새 블록을 넣는다.
`TIERS`와 `editor` 헬퍼는 그 바깥 스코프에 이미 있다. `editor`는 활성 덱 props를
안 넘기므로, 이 블록은 자기 헬퍼를 따로 둔다.

```tsx
  // 덱 이름 글자와 첫 빈자리의 `+` 글자, 이 둘만 표적이었다. 나머지 테두리
  // 안은 전부 죽어 있어서 「다른 덱으로 옮기기」가 20px 과녁 맞히기였다.
  describe('덱 몸통 표적', () => {
    const seated: Draft = { decks: [[{ slug: 'crown', locked: false }], []] }
    const both: Draft = {
      decks: [[{ slug: 'crown', locked: false }], [{ slug: 'liter', locked: false }]],
    }
    const moved = { decks: [[], [{ slug: 'crown', locked: false }]] }

    const pickable = (
      value: Draft,
      onChange: (next: Draft) => void = () => {},
      onActiveDeckChange: (deckIndex: number) => void = () => {},
      extra: Partial<React.ComponentProps<typeof DraftEditor>> = {},
    ) =>
      render(
        <DraftEditor
          numDecks={2}
          value={value}
          onChange={onChange}
          portraitFor={() => null}
          nameFor={nameFromSlug}
          burstTiersFor={(slug: string) => TIERS[slug] ?? []}
          activeDeck={0}
          onActiveDeckChange={onActiveDeckChange}
          {...extra}
        />,
      )

    /** 덱 컨테이너 자체 - 안쪽 컨트롤이 아니라 테두리 안 빈 면적을 누르는 것과
     * 같다. jsdom에는 레이아웃이 없어서 이 요소에 직접 디스패치한다. */
    const deckBody = (container: HTMLElement, deckNumber: number) =>
      container.querySelectorAll<HTMLElement>('.draft-editor__deck')[deckNumber - 1]

    it('아무것도 안 들었으면 덱 몸통을 누를 때 그 덱이 활성 덱이 된다', async () => {
      const onActiveDeckChange = vi.fn()
      const { container } = pickable(seated, () => {}, onActiveDeckChange)

      await userEvent.click(deckBody(container, 2))

      expect(onActiveDeckChange).toHaveBeenCalledWith(1)
    })

    it('들고 덱 몸통을 누르면 옮기고, 그 덱이 활성 덱이 된다', async () => {
      const onChange = vi.fn()
      const onActiveDeckChange = vi.fn()
      const { container } = pickable(seated, onChange, onActiveDeckChange)

      await userEvent.click(screen.getByRole('button', { name: '덱 1의 Crown' }))
      await userEvent.click(deckBody(container, 2))

      expect(onChange).toHaveBeenCalledWith(moved)
      expect(onActiveDeckChange).toHaveBeenLastCalledWith(1)
    })

    // Fienn의 보고: 「가장 왼쪽 자리만 활성화된다」. 나머지 넷은 버튼이 아니라
    // 클릭이 어디로도 안 갔다.
    it('들고 다른 덱의 세 번째 빈자리를 눌러도 옮긴다', async () => {
      const onChange = vi.fn()
      const { container } = pickable(seated, onChange)

      await userEvent.click(screen.getByRole('button', { name: '덱 1의 Crown' }))
      const open = deckBody(container, 2).querySelectorAll<HTMLElement>(
        '.draft-editor__slot--open',
      )
      expect(open).toHaveLength(5)
      await userEvent.click(open[2])

      expect(onChange).toHaveBeenCalledWith(moved)
    })

    // 껍데기가 moveUnit의 거절을 안 보면, 옮기지도 않고 든 것만 내려놓는다 -
    // 화면에서 유닛이 조용히 사라진 것처럼 보인다.
    it('꽉 찬 덱 몸통을 누르면 옮기지 않고 계속 들고 있다', async () => {
      const full: Draft = {
        decks: [
          [{ slug: 'crown', locked: false }],
          ['liter', 'blanc', 'x1', 'x2', 'x3'].map((slug) => ({ slug, locked: false })),
        ],
      }
      const onChange = vi.fn()
      const onHeldSlugChange = vi.fn()
      const { container } = pickable(full, onChange, () => {}, { onHeldSlugChange })

      await userEvent.click(screen.getByRole('button', { name: '덱 1의 Crown' }))
      onHeldSlugChange.mockClear()
      await userEvent.click(deckBody(container, 2))

      expect(onChange).not.toHaveBeenCalled()
      expect(onHeldSlugChange).not.toHaveBeenCalled()
      expect(container.querySelector('.draft-editor__slot--held')).not.toBeNull()
    })

    // 좌석 버튼이 자기 핸들러에서 setHeld(null)을 불러도, 껍데기가 읽는
    // heldSlug는 같은 배치 안이라 아직 옛 값이다 - 전파를 안 끊으면 교환하고
    // 나서 또 이동한다.
    it('좌석으로 교환할 때 껍데기가 겹쳐 처리하지 않는다', async () => {
      const onChange = vi.fn()
      pickable(both, onChange)

      await userEvent.click(screen.getByRole('button', { name: '덱 1의 Crown' }))
      await userEvent.click(screen.getByRole('button', { name: '덱 2의 Liter' }))

      expect(onChange).toHaveBeenCalledTimes(1)
      expect(onChange).toHaveBeenCalledWith({
        decks: [[{ slug: 'liter', locked: false }], [{ slug: 'crown', locked: false }]],
      })
    })

    it('잠금 토글은 껍데기로 새지 않는다', async () => {
      const onActiveDeckChange = vi.fn()
      pickable(both, () => {}, onActiveDeckChange)

      await userEvent.click(screen.getByRole('button', { name: '덱 2에서 Liter 고정' }))

      expect(onActiveDeckChange).not.toHaveBeenCalled()
    })

    // 든 채로는 덱 이름도 놓는 자리다 - 표적 한가운데에 죽은 띠를 두지 않는다.
    it('들고 덱 이름을 눌러도 옮긴다', async () => {
      const onChange = vi.fn()
      pickable(seated, onChange)

      await userEvent.click(screen.getByRole('button', { name: '덱 1의 Crown' }))
      await userEvent.click(screen.getByRole('button', { name: '덱 2 활성 덱으로 선택' }))

      expect(onChange).toHaveBeenCalledWith(moved)
    })

    it('안 들었을 때 덱 이름은 활성 덱만 한 번 바꾼다', async () => {
      const onChange = vi.fn()
      const onActiveDeckChange = vi.fn()
      pickable(seated, onChange, onActiveDeckChange)

      await userEvent.click(screen.getByRole('button', { name: '덱 2 활성 덱으로 선택' }))

      expect(onActiveDeckChange).toHaveBeenCalledTimes(1)
      expect(onActiveDeckChange).toHaveBeenCalledWith(1)
      expect(onChange).not.toHaveBeenCalled()
    })

    // 덱이 하나면 고를 것이 없다. 껍데기가 onActiveDeckChange의 존재만 보고
    // 부르면, 미란다 화면에 없는 개념이 생긴다.
    it('덱이 하나면 몸통을 눌러도 활성 덱을 부르지 않는다', async () => {
      const onActiveDeckChange = vi.fn()
      const { container } = render(
        <DraftEditor
          numDecks={1}
          value={{ decks: [[]] }}
          onChange={() => {}}
          portraitFor={() => null}
          nameFor={nameFromSlug}
          burstTiersFor={(slug: string) => TIERS[slug] ?? []}
          activeDeck={0}
          onActiveDeckChange={onActiveDeckChange}
        />,
      )

      await userEvent.click(deckBody(container, 1))

      expect(onActiveDeckChange).not.toHaveBeenCalled()
    })
  })
```

- [ ] **Step 2: 실패를 확인한다**

```
npm --prefix frontend test -- src/components/DraftEditor.test.tsx
```

Expected: 새 테스트 9개 중 8개 FAIL(껍데기가 없으니 아무 일도 안 일어난다).
`'덱이 하나면 몸통을 눌러도 활성 덱을 부르지 않는다'` 하나만 지금도 통과한다 —
아직 아무 핸들러가 없어서다. 그건 정상이며, Step 3 뒤에도 통과해야 진짜 가치가 있다.

- [ ] **Step 3: 껍데기와 전파 차단을 넣는다**

`DraftEditor.tsx`에서 다음 다섯 곳을 고친다.

**(a) 덱 컨테이너** — `className`을 계산하는 곳에 `pressable`을 더하고 `onClick`을 단다.
`const label = deckLabels?.[deckIndex] ?? null` 아래에 추가한다:

```ts
          // 누를 수 있을 때만 손 모양이 뜬다. 든 것이 있으면 꽉 찬 덱은 받지
          // 못하므로 그때는 표적이 아니다.
          const pressable = heldSlug !== null ? !full : picksDeck
```

`<div className={[...]}>`의 배열에 한 줄을 더한다:

```ts
                pressable ? 'draft-editor__deck--pressable' : '',
```

같은 `<div>`의 `onDrop` 아래에 `onClick`을 단다:

```tsx
              // 덱 테두리 안 전체가 표적이다. 안쪽 컨트롤은 저마다 전파를
              // 끊어 자기 몫을 가져가므로, 여기 닿는 것은 「덱을 눌렀다」뿐이다.
              onClick={() => {
                if (heldSlug !== null) {
                  const next = moveUnit(value, deckIndex, heldSlug)
                  // moveUnit은 꽉 찬 덱과 「이미 그 덱」을 거절하며 같은 객체를
                  // 돌려준다. 거절당했는데 든 것을 내려놓으면, 화면에서 유닛이
                  // 조용히 사라진 것처럼 보인다.
                  if (next === value) return
                  onChange(next)
                  setHeld(null)
                  onActiveDeckChange?.(deckIndex)
                  return
                }
                if (picksDeck) onActiveDeckChange(deckIndex)
              }}
```

**(b) 좌석 그립 버튼** — `onClick={() => {` 를 `onClick={(event) => {` 로 바꾸고
첫 줄에 넣는다:

```ts
                            event.stopPropagation()
```

**(c) 잠금 토글** — `onClick={() => onChange(toggleLock(value, deckIndex, seatIndex))}`
를 이렇게 바꾼다:

```tsx
                          onClick={(event) => {
                            event.stopPropagation()
                            onChange(toggleLock(value, deckIndex, seatIndex))
                          }}
```

**(d) 덱 이름 토글** — `onClick={() => onActiveDeckChange(deckIndex)}` 를 이렇게
바꾼다:

```tsx
                    onClick={(event) => {
                      // 든 채로는 이름도 놓는 자리다 - 표적 한가운데에 죽은 띠를
                      // 두지 않는다. 껍데기가 이동으로 처리하도록 흘려보낸다.
                      if (heldSlug !== null) return
                      event.stopPropagation()
                      onActiveDeckChange(deckIndex)
                    }}
```

**(e) 빈자리 `+` 버튼** — 자기 `onClick`을 **지운다**. 껍데기가 하는 일과 같아서,
두 벌로 두면 조용히 갈라진다. 키보드의 Enter/Space도 click 이벤트를 올려보내므로
껍데기가 그대로 받는다. 버튼 자체는 남긴다 — 접근성 트리에 노출되는 유일한 놓기
컨트롤이고, 「덱마다 첫 빈자리 하나만 노출」이라는 기존 결정이 거기 걸려 있다.

```tsx
                    {heldSlug !== null && i === 0 ? (
                      <button
                        type="button"
                        className="draft-editor__slot-plus"
                        aria-label={`덱 ${deckIndex + 1}에 놓기`}
                        // 누르면 덱 껍데기가 이동으로 받는다 - 같은 일을 하는
                        // 핸들러를 두 벌 두면 조용히 갈라진다.
                      >
                        +
                      </button>
                    ) : (
```

- [ ] **Step 4: CSS를 넣는다**

`frontend/src/App.css`에서 `.draft-editor__deck--active` 규칙 바로 뒤에 추가한다:

```css
/* 덱 테두리 안 전체가 표적이다 - 든 니케를 놓거나(든 것이 있을 때) 활성 덱을
   고른다. 받을 수 없는 덱에는 손 모양을 주지 않는다. */
.draft-editor__deck--pressable {
  cursor: pointer;
}
```

- [ ] **Step 5: 조작 안내 문구를 화면과 맞춘다**

`frontend/src/lib/helpText.ts`의 `draft.seatHintWithDeckPick`을 바꾼다. 이제
표적이 이름이 아니라 덱 전체다:

```ts
    seatHintWithDeckPick:
      '팔레트의 니케를 누르면 활성 덱(밝은 테두리)에 앉고, 그 덱이 차면 다음 덱으로 넘어가요. 덱을 누르면 활성 덱이 바뀌어요. 앉은 니케를 눌러 들고 다른 덱을 누르면 옮기거나 맞바꿔요. ',
```

`DraftEditor.tsx` 파일 머리 주석도 지금 하는 일과 맞춘다. 8-14행의 문단을 이렇게
바꾼다:

```
// Pressing a seat's face picks it up; pressing that same seat again vacates
// it, and Esc cancels the pick-up. With a unit held, pressing anywhere inside
// a deck puts it there; with nothing held, pressing a deck makes it the active
// one. Pressing a palette chip fills an open seat, or swaps into the held seat
// if one is held - the palette lives outside this component (in the parent
// panel), so onHeldSlugChange carries what is held across the boundary.
// Dragging still works in a browser but cannot be the way in: the packaged
// app's WebView2 fires `dragstart` and then delivers no drop.
```

- [ ] **Step 6: 통과를 확인한다**

```
npm --prefix frontend test -- src/components/DraftEditor.test.tsx
npx --prefix frontend tsc -b --noEmit frontend
```

Expected: 전부 통과. 특히 기존 테스트 셋이 그대로 초록이어야 한다:
- `'들고 다른 덱의 빈자리를 누르면 옮긴다'` — 이제 껍데기 버블링으로 통과한다.
  이게 빨개지면 (e)의 버튼이 껍데기에 닿지 않는다는 뜻이다.
- `'들었을 때 덱마다 첫 빈자리만 접근성 트리에 노출하고 나머지는 숨긴다'`
- `'아무것도 안 들었으면 빈자리는 버튼이 아니다'`

- [ ] **Step 7: 전체 스위트를 돌린다**

```
npm --prefix frontend test
```

Expected: 앞선 태스크의 새 테스트를 더한 수만큼 늘어난 채 전부 통과.
`RecommendPanel`·`UnionRaidPanel`·`MirandaCalculatorPanel`은 `DraftEditor`를
품고 있으므로 여기서 처음 회귀가 드러날 수 있다.

- [ ] **Step 8: 커밋**

```bash
git add frontend/src/components/DraftEditor.tsx frontend/src/components/DraftEditor.test.tsx frontend/src/App.css frontend/src/lib/helpText.ts
git commit -m "덱 테두리 안 전체가 표적이다 - 든 니케를 놓거나 활성 덱을 고른다"
```

---

### Task 5: 초성 추출

순수 함수 둘. `unitFilter`가 쓰기 전에 먼저 못 박는다.

**Files:**
- Create: `frontend/src/lib/koreanSearch.ts`
- Test: `frontend/src/lib/koreanSearch.test.ts`

**Interfaces:**
- Consumes: 없음.
- Produces: `toChosung(text: string): string`, `isChosungQuery(text: string): boolean`
  — Task 6이 `unitFilter.ts`에서 쓴다.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`frontend/src/lib/koreanSearch.test.ts`를 새로 만든다:

```ts
import { describe, it, expect } from 'vitest'
import { isChosungQuery, toChosung } from './koreanSearch'

describe('toChosung', () => {
  it('음절마다 초성 하나를 낸다', () => {
    expect(toChosung('홍련')).toBe('ㅎㄹ')
    expect(toChosung('라피')).toBe('ㄹㅍ')
    expect(toChosung('네온')).toBe('ㄴㅇ')
    expect(toChosung('앨리스')).toBe('ㅇㄹㅅ')
  })

  it('된소리 초성을 그대로 낸다', () => {
    expect(toChosung('빨강')).toBe('ㅃㄱ')
  })

  // 초성은 음절 코드를 588로 나눈 몫이 정한다 - 중성·종성이 무엇이든 안 흔들린다.
  it('겹받침과 중성은 초성을 흐리지 않는다', () => {
    expect(toChosung('값')).toBe('ㄱ')
    expect(toChosung('까')).toBe('ㄲ')
    expect(toChosung('힣')).toBe('ㅎ')
    expect(toChosung('가')).toBe('ㄱ')
  })

  // 버려야 "홍련: 흑영"이 "ㅎㄹㅎㅇ"가 되어 "ㅎㄹ"로도 맞는다. 자리를 남기면
  // 구두점이 초성 사이에 끼어 아무것도 안 맞는다.
  it('한글 음절이 아닌 글자는 버린다', () => {
    expect(toChosung('홍련: 흑영')).toBe('ㅎㄹㅎㅇ')
    expect(toChosung('은화: 택티컬 업')).toBe('ㅇㅎㅌㅌㅋㅇ')
    expect(toChosung('crown')).toBe('')
    expect(toChosung('')).toBe('')
  })
})

describe('isChosungQuery', () => {
  it('초성만으로 이뤄진 질의를 가려낸다', () => {
    expect(isChosungQuery('ㅎㄹ')).toBe(true)
    expect(isChosungQuery('ㅃ')).toBe(true)
  })

  // 완성형이 섞이면 초성 대조는 틀린 답을 낸다 - toChosung('홍련')='ㅎㄹ'에
  // '홍ㄹ'은 없다. 그럴 땐 완성형 부분일치가 답해야 한다.
  it('완성형이 섞이면 초성 질의가 아니다', () => {
    expect(isChosungQuery('홍ㄹ')).toBe(false)
    expect(isChosungQuery('홍련')).toBe(false)
  })

  it('영문과 빈 문자열은 초성 질의가 아니다', () => {
    expect(isChosungQuery('crown')).toBe(false)
    expect(isChosungQuery('')).toBe(false)
    expect(isChosungQuery('   ')).toBe(false)
  })

  // 모음만으로는 초성을 못 만든다.
  it('모음은 초성이 아니다', () => {
    expect(isChosungQuery('ㅏ')).toBe(false)
  })
})
```

- [ ] **Step 2: 실패를 확인한다**

```
npm --prefix frontend test -- src/lib/koreanSearch.test.ts
```

Expected: FAIL — `./koreanSearch` 모듈이 없다.

- [ ] **Step 3: 모듈을 쓴다**

`frontend/src/lib/koreanSearch.ts`를 새로 만든다:

```ts
// 한글 이름 검색을 위한 초성 다루기. 니케 이름은 대부분 한글 두세 음절이라,
// 초성 두 글자가 100기 넘는 그리드를 한 자리수로 줄인다.

/** 유니코드 한글 음절이 초성을 배치한 순서 그대로. 인덱스가 곧 초성 번호다. */
const CHOSUNG = [
  'ㄱ', 'ㄲ', 'ㄴ', 'ㄷ', 'ㄸ', 'ㄹ', 'ㅁ', 'ㅂ', 'ㅃ', 'ㅅ',
  'ㅆ', 'ㅇ', 'ㅈ', 'ㅉ', 'ㅊ', 'ㅋ', 'ㅌ', 'ㅍ', 'ㅎ',
] as const

const SYLLABLE_FIRST = 0xac00 // '가'
const SYLLABLE_LAST = 0xd7a3 // '힣'
/** 초성 하나가 거느리는 음절 수 = 중성 21 × 종성 28. */
const PER_CHOSUNG = 21 * 28

const CHOSUNG_SET: ReadonlySet<string> = new Set(CHOSUNG)

/** 문자열에서 한글 음절의 초성만 뽑아 잇는다. 음절이 아닌 글자(공백·구두점·
 * 괄호·영숫자)는 버린다 - 자리를 남기면 "홍련: 흑영"이 "ㅎㄹ: ㅎㅇ"가 되어
 * 사이의 구두점 때문에 "ㅎㄹㅎㅇ"로 못 찾는다. */
export const toChosung = (text: string): string => {
  let out = ''
  for (const char of text) {
    const code = char.codePointAt(0)!
    if (code < SYLLABLE_FIRST || code > SYLLABLE_LAST) continue
    out += CHOSUNG[Math.floor((code - SYLLABLE_FIRST) / PER_CHOSUNG)]
  }
  return out
}

/** 질의가 초성만으로 이뤄졌는가. 완성형이 섞이면("홍ㄹ") 초성 대조는 틀린 답을
 * 내므로 - toChosung('홍련')은 'ㅎㄹ'이고 거기 '홍ㄹ'은 없다 - 그때는 쓰지
 * 않고 완성형 부분일치에 맡긴다. */
export const isChosungQuery = (text: string): boolean => {
  const chars = [...text].filter((char) => char !== ' ')
  return chars.length > 0 && chars.every((char) => CHOSUNG_SET.has(char))
}
```

- [ ] **Step 4: 통과를 확인한다**

```
npm --prefix frontend test -- src/lib/koreanSearch.test.ts
npx --prefix frontend tsc -b --noEmit frontend
```

Expected: 둘 다 통과.

- [ ] **Step 5: 커밋**

```bash
git add frontend/src/lib/koreanSearch.ts frontend/src/lib/koreanSearch.test.ts
git commit -m "이름에서 초성을 뽑는다 - 한글 그리드를 두 글자로 좁히기 위해"
```

---

### Task 6: 검색이 초성과 영문을 본다

`unitFilter.ts`의 이름 대조 한 곳이 세 갈래가 된다. `UnitFacets`에 `slug`가
늘어나므로 타입체커가 고쳐야 할 호출부를 전부 지목해 준다.

**Files:**
- Modify: `frontend/src/lib/unitFilter.ts`
- Modify: `frontend/src/components/UnitPalette.tsx` (`facetsFor`)
- Modify: `frontend/src/components/RosterGrid.tsx` (`facetsFor`)
- Modify: `frontend/src/components/UnitFilterBar.tsx` (placeholder)
- Test: `frontend/src/lib/unitFilter.test.ts`

**Interfaces:**
- Consumes: Task 5의 `toChosung(text)`, `isChosungQuery(text)`.
- Produces: `UnitFacets`에 필수 필드 `slug: string`.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`frontend/src/lib/unitFilter.test.ts`에서 먼저 픽스처에 슬러그를 넣는다.
`Row` 인터페이스와 `ROWS`를 이렇게 바꾼다:

```ts
interface Row {
  slug: string
  name: string
  element: UnitFacets['element']
  burstTier: UnitFacets['burstTier']
  overload: { name: string; value: number | string }[]
}

const facets = (row: Row): UnitFacets => row

const ROWS: Row[] = [
  { slug: 'scarlet', name: '홍련', element: 'Fire', burstTier: 3, overload: [{ name: '공격력 증가', value: 40.91 }] },
  { slug: 'rapi', name: '라피', element: 'Water', burstTier: 1, overload: [{ name: '공격력 증가', value: 12.5 }] },
  { slug: 'neon', name: '네온', element: 'Fire', burstTier: 1, overload: [{ name: '우월코드 대미지 증가', value: 99.82 }] },
  { slug: 'alice', name: '앨리스', element: 'Wind', burstTier: 3, overload: [] },
]
```

`'starts on 우코, highest first'` 테스트 안의 지역 `rows: Row[]` 두 항목에도
`slug`를 붙인다 (`slug: '가'`, `slug: '나'` — 이 테스트는 정렬만 보므로 값은
무엇이든 된다. 다만 서로 달라야 한다).

그 다음 `describe('filterAndSort', ...)` 안, `'finds nothing for a query no name contains'`
바로 뒤에 새 테스트를 넣는다:

```ts
  // 니케 이름은 한글인데 유저가 기억하는 것이 영문일 때가 있다. 슬러그가 곧
  // 케밥케이스 영문명이라(backend/tests/test_resource_id_directory.py가 고정한다)
  // 백엔드가 영문명을 따로 안 내보내도 된다.
  it('영문으로 치면 슬러그로 맞는다', () => {
    expect(run({ query: 'scar' })).toEqual(['홍련'])
    expect(run({ query: 'RAPI' })).toEqual(['라피'])
  })

  it('슬러그의 하이픈과 질의의 공백을 같은 것으로 본다', () => {
    const rows: Row[] = [
      { slug: 'ada-wong', name: '에이다 웡', element: 'Fire', burstTier: 3, overload: [] },
    ]
    const search = (query: string) =>
      names(filterAndSort(rows, facets, { ...EMPTY_FILTER, query }))
    expect(search('ada wong')).toEqual(['에이다 웡'])
    expect(search('ada-wong')).toEqual(['에이다 웡'])
    expect(search('adawong')).toEqual(['에이다 웡'])
  })

  it('초성으로 치면 이름의 초성으로 맞는다', () => {
    expect(run({ query: 'ㅎㄹ' })).toEqual(['홍련'])
    expect(run({ query: 'ㄴㅇ' })).toEqual(['네온'])
  })

  // 한글 질의에서 영숫자만 남기면 빈 문자열이고, 빈 문자열은 모든 슬러그에
  // includes로 맞는다. 가드가 없으면 초성 검색이 아무것도 안 거르는
  // "전부 표시"가 되는데, 값이 전부 그럴듯해 눈으로는 안 보인다.
  it('초성 질의가 슬러그 갈래로 새어 전부 통과시키지 않는다', () => {
    expect(run({ query: 'ㅎㄹ' })).toHaveLength(1)
    expect(run({ query: 'ㅋ' })).toEqual([])
  })

  // 완성형이 섞인 질의는 초성 대조가 답할 수 없다 - 완성형 부분일치가 맡는다.
  it('완성형이 섞인 질의는 초성으로 맞추지 않는다', () => {
    expect(run({ query: '홍ㄹ' })).toEqual([])
    expect(run({ query: '홍' })).toEqual(['홍련'])
  })
```

- [ ] **Step 2: 실패를 확인한다**

```
npm --prefix frontend test -- src/lib/unitFilter.test.ts
```

Expected: FAIL. `'영문으로 치면 슬러그로 맞는다'`·`'초성으로 치면...'`·
`'슬러그의 하이픈과...'`가 빈 배열을 받는다.
(`'초성 질의가 새지 않는다'`와 `'완성형이 섞인...'`은 지금도 통과한다 — 새는
갈래 자체가 아직 없어서다. Step 4 뒤에도 통과해야 진짜 가드다.)

- [ ] **Step 3: `unitFilter.ts`를 고친다**

import를 추가한다:

```ts
import { isChosungQuery, toChosung } from './koreanSearch'
```

`UnitFacets`에 `slug`를 넣는다 — 인터페이스 맨 위:

```ts
export interface UnitFacets {
  /** 검색에서 영문 이름 노릇을 한다: 슬러그가 곧 케밥케이스 영문명이고, 그것을
   * backend/tests/test_resource_id_directory.py가 고정한다. 식별자로 쓰라고
   * 넣은 것이 아니다. */
  slug: string
  name: string
  element: NikkeElement
  burstTier: BurstTier
  overload: { name: string; value: number | string }[]
}
```

`matches` 위에 두 함수를 넣는다:

```ts
/** 영숫자만 남긴 소문자. 슬러그의 하이픈과 유저가 치는 공백을 같은 것으로
 * 보게 만든다 - "ada wong"과 "ada-wong"은 같은 니케다. */
const alphanumericOnly = (text: string): string => text.toLowerCase().replace(/[^a-z0-9]/g, '')

/** 이름 질의 한 건. 세 갈래를 OR로 본다: 한글 완성형 부분일치, 영문(슬러그),
 * 초성. `query`는 이미 trim·소문자다. */
const matchesQuery = (facets: UnitFacets, query: string): boolean => {
  if (facets.name.toLowerCase().includes(query)) return true
  // 한글 질의는 영숫자만 남기면 빈 문자열이 되고, 빈 문자열은 모든 슬러그에
  // includes로 맞는다 - 이 가드가 없으면 초성 검색이 아무것도 안 거른다.
  const alphanumeric = alphanumericOnly(query)
  if (alphanumeric !== '' && alphanumericOnly(facets.slug).includes(alphanumeric)) return true
  return isChosungQuery(query) && toChosung(facets.name).includes(query)
}
```

`matches`의 이름 줄을 바꾼다:

```ts
const matches = (facets: UnitFacets, state: UnitFilterState): boolean => {
  const query = state.query.trim().toLowerCase()
  if (query !== '' && !matchesQuery(facets, query)) return false
  if (state.elements.length > 0 && !state.elements.includes(facets.element)) return false
  if (state.burstTiers.length > 0 && !state.burstTiers.includes(facets.burstTier)) return false
  return true
}
```

- [ ] **Step 4: 타입체커가 지목하는 호출부를 채운다**

```
npx --prefix frontend tsc -b --noEmit frontend
```

`slug`가 빠진 `UnitFacets` 생성부를 전부 짚어 준다. 최소한 이 둘이다:

`frontend/src/components/UnitPalette.tsx`의 `facetsFor`:

```ts
  const facetsFor = (unit: SupportedUnit): UnitFacets => ({
    slug: unit.slug,
    name: unit.name,
    element: unit.element,
    burstTier: unit.burstTier,
    overload: ownedBySlug.get(unit.slug)!.overload_options,
  })
```

`frontend/src/components/RosterGrid.tsx`의 `facetsFor`:

```ts
  const facetsFor = (draft: NikkeDraft): UnitFacets => {
    const unit = bySlug.get(draft.character_slug)!
    return {
      slug: unit.slug,
      name: unit.name,
      element: unit.element,
      burstTier: unit.burstTier,
      overload: draft.overload_options,
    }
  }
```

타입체커가 더 짚어 주는 곳이 있으면 그 자리의 슬러그를 그대로 넣는다.
**슬러그가 없는 자리에 `''`나 `name`을 넣지 말 것** — 빈 문자열은 위의
`alphanumeric !== ''` 가드를 통과해 모든 질의에 맞는 유닛을 만든다.

- [ ] **Step 5: 검색창이 무엇을 받는지 말하게 한다**

`frontend/src/components/UnitFilterBar.tsx`의 placeholder를 바꾼다. 라벨
`이름 검색`은 테스트 세 파일이 셀렉터로 쓰므로 **건드리지 않는다**.

```tsx
          placeholder="이름 · 초성 · 영문"
```

- [ ] **Step 6: 통과를 확인한다**

```
npm --prefix frontend test -- src/lib/unitFilter.test.ts src/components/UnitPalette.test.tsx src/components/RosterGrid.test.tsx src/components/UnitFilterBar.test.tsx
npx --prefix frontend tsc -b --noEmit frontend
```

Expected: 전부 통과. 기존 `UnitPalette`의 `'hides the units a name search does not match'`
(질의 `'cro'`)가 그대로 초록이어야 한다.

- [ ] **Step 7: 커밋**

```bash
git add frontend/src/lib/unitFilter.ts frontend/src/lib/unitFilter.test.ts frontend/src/components/UnitPalette.tsx frontend/src/components/RosterGrid.tsx frontend/src/components/UnitFilterBar.tsx
git commit -m "이름 검색이 초성과 영문도 받는다 - 슬러그가 곧 영문명이다"
```

---

### Task 7: 전체 검증과 로드맵

**Files:**
- Modify: `docs/roadmap.md`

**Interfaces:**
- Consumes: 앞 여섯 태스크 전부.
- Produces: 없음.

- [ ] **Step 1: 전체 스위트와 타입체크**

```
npm --prefix frontend test
npx --prefix frontend tsc -b --noEmit frontend
npm --prefix frontend run lint
```

Expected: 테스트는 **778보다 늘어난 수**로 전부 통과(새 테스트 약 21개), 타입에러
0, lint 통과. 하나라도 안 맞으면 여기서 멈추고 고친다.

- [ ] **Step 2: 앱을 띄워 다섯 항목을 눈으로 확인한다**

Vitest는 `css: false`라 커서를 못 재고, 설치형 앱의 WebView2는 브라우저와 다르게
동작한 전례가 있다(드래그가 앱에서만 죽어 있었다). `run` 스킬로 앱을 띄워 확인한다:

1. 팔레트에서 계속 눌러 덱 1이 차는 순간 활성 테두리가 덱 2로 옮겨가는가
2. 든 니케를 다른 덱의 **아무 자리나** 눌러 옮겨지는가
3. 덱 테두리 안 아무 데나 눌러 활성 덱이 바뀌는가 (그리고 커서가 손 모양인가)
4. 검색창에 `ㅎㄹ`·`scar`를 쳐서 맞는가
5. 미란다 계산기에서 앉은 니케를 누르고 팔레트 니케를 눌러 교환되는가

- [ ] **Step 3: 로드맵을 갱신한다**

`docs/roadmap.md`의 To-Do 체크리스트에서 이 다섯 건에 해당하는 항목을 찾아
표시한다. **먼저 파일을 읽고** 기존 항목의 표기 형식을 그대로 따를 것. 해당
항목이 없으면 착륙한 것들 아래에 한 줄로 더한다:

```
- [x] 덱 편성 조작 2차 — 팔레트 자동 덱 전환, 덱 몸통 클릭 표적, 초성·영문 검색, 미란다 교환 (2026-08-11)
```

- [ ] **Step 4: 커밋**

```bash
git add docs/roadmap.md
git commit -m "로드맵: 덱 편성 조작 2차 5건 착륙"
```

- [ ] **Step 5: 결정과 인사이트를 남긴다**

`/document` 명령(docs-keeper 서브에이전트)으로 두 가지를 기록한다:

- **결정**: 2026-07-28 스펙이 기각한 초성·슬러그 검색을 2026-08-11에 뒤집었다.
  근거는 슬러그=케밥케이스 영문명이 `backend/tests/test_resource_id_directory.py`로
  이미 고정돼 있어 자모 유틸 25줄 말고는 새 비용이 없다는 것.
- **인사이트**: 껍데기 클릭 핸들러는 (1) 안쪽 컨트롤의 `stopPropagation`과
  (2) 같은 배치 안에서 상태가 아직 안 바뀐다는 두 가지 때문에 조용히 두 번
  처리한다. 그리고 거절을 돌려주는 순수 함수(`moveUnit`)를 쓸 때는 반환 객체
  동일성으로 거절을 봐야 한다 — 안 보면 든 것만 사라진다.

---

## Self-Review

**1. 스펙 커버리지**

| 스펙 절 | 태스크 |
|---|---|
| §A `firstDeckWithRoom` + 두 패널 배선 | 2, 3 |
| §B 덱 껍데기 · 네 컨트롤의 전파 · a11y 유지 · CSS | 4 |
| §C `koreanSearch` · 세 갈래 대조 · `UnitFacets.slug` · placeholder | 5, 6 |
| §D 미란다 배선 | 1 |
| 검증(전체 스위트·타입·앱 육안) | 7 |
| 안 하는 것(백엔드 `name_en`·드래그·껍데기 키보드·혼합 질의) | 어느 태스크도 안 건드림 |

빠진 스펙 요구사항 없음.

**2. 플레이스홀더** — 없음. 모든 코드 단계가 실제 코드를 담고, 모든 테스트가
실제 단언을 담는다. Task 7 Step 3만 "파일을 읽고 형식을 따르라"인데, 이건
로드맵의 현재 내용을 모른 채 형식을 지어내면 오히려 틀리기 때문이다.

**3. 타입 일관성**
- `firstDeckWithRoom(draft, from, numDecks) → number | null` — Task 2에서 정의,
  Task 3에서 같은 이름·같은 인자 순서로 쓴다. ✓
- `toChosung(text) → string`, `isChosungQuery(text) → boolean` — Task 5에서 정의,
  Task 6에서 그대로. ✓
- `UnitFacets.slug: string` — Task 6에서 필수로 추가하고 같은 태스크 안에서 두
  호출부를 채운다. ✓
- `replaceUnit(draft, replacedSlug, slug)` — 기존 export, Task 1·3이 같은 시그니처로
  쓴다. ✓

**4. 이 계획이 스스로 조심하는 것** (지난 두 배치의 결함이 전부 계획의 코드
스니펫에서 나왔다)
- 모든 셀렉터를 실제 소스에서 확인했다: `덱 1의 Crown`(그립),
  `덱 1에서 Crown 고정`(잠금), `덱 2에 놓기`(+), `덱 2 활성 덱으로 선택`(덱 이름),
  `크라운 배치`/`U0 배치`(팔레트), `5/5`(카운트), `.draft-editor__deck`,
  `.draft-editor__slot--open`, `.draft-editor__slot--held`.
- 픽스처가 실제로 데이터를 갖는지 확인했다: 유니온 테스트 로스터는 `u0`..`u14`
  15기(3덱×5자리에 정확히 맞는다), 미란다 `UNITS`에 `snow-white`가 여섯째로
  들어 있다(교환해 들일 상대), 솔로 draft 블록에 `supportedUnits`(a-e)와
  `nikke('f')`가 있다.
- **지금도 통과하는 테스트 둘을 명시했다**(Task 4 Step 2의 `'덱이 하나면...'`,
  Task 6 Step 2의 가드 둘). 그것들은 구현 뒤에도 통과해야 값을 한다.
- 각 가드마다 「무엇을 떼면 빨개지나」를 적었다: `next === value`(Task 4),
  `stopPropagation` 셋(Task 4), `alphanumeric !== ''`(Task 6),
  「앉힌 직후 다시 훑기」(Task 3).
