# RapiLab UI 개편 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 앱 이름을 RapiLab으로 세우고 화면 용어를 게임 표기에 맞추며, 실행 버튼이 스크롤 위치와 무관하게 항상 화면에 남게 한다.

**Architecture:** 프론트엔드만 건드린다. 대부분은 문자열 교체이고, 마지막 두 태스크만 레이아웃을 바꾼다 — 액션 블록(제출/취소 버튼)을 모드에 따라 두 자리 중 하나에 렌더한다: 우측 덱 컬럼이 있는 모드는 이미 `position: sticky`인 그 컬럼 안에, 없는 모드는 폼 바닥의 화면 하단 고정 바에.

**Tech Stack:** React 19 + TypeScript + Vite, Vitest + @testing-library/react, 순수 CSS(`frontend/src/App.css`, 변수는 `index.css`).

**설계 문서:** `docs/superpowers/specs/2026-07-28-rapilab-ui-rename-design.md`

## Global Constraints

- 작업 디렉터리는 워크트리 `.claude/worktrees/ui+rapilab-rename` 이고 브랜치는 `worktree-ui+rapilab-rename` 이다. `main`/`master`는 없다.
- 백엔드는 건드리지 않는다. `frontend/` 밖의 소스는 읽기 전용이다.
- 테스트 명령은 `npm --prefix frontend test -- --run` 이다. 시작 기준선은 **44 파일 / 387 passed** 이며, 어떤 태스크도 이 수를 줄이지 않는다.
- `RecommendMode` 유니온 값(`'single' | 'raid' | 'draft' | 'evaluate'`)과 `Tab` 유니온 값(`'roster' | 'recommend' | 'union'`), 그리고 `tab-*`/`panel-*` DOM id는 **바꾸지 않는다**. 앞의 것은 `StoredInputs.mode`로 localStorage에 저장돼 있어 바꾸면 기존 사용자의 저장 결과가 복원되지 않고, 뒤의 것은 접근성 배선이다. 화면에 보이는 라벨만 바꾼다.
- 다음 문자열은 **바꾸지 않는다**: `api/recommendApiError.ts`·`hooks/useAsyncRequestStatus.ts`의 에러 문구 속 "덱 추천"(앱 이름이 아니라 동작 설명), `lib/rosterImport.ts`의 `Resilience Cube`(blablalink API가 주는 데이터 값).
- 확정된 문구(그대로 복사할 것):
  - 앱 이름: `RapiLab`
  - 큐브 안내: `모든 니케가 재장전 큐브 15레벨을 착용한 것으로 계산합니다.`
  - 탭: `니케 풀`, `솔로 레이드`, `유니온 레이드`
  - 모드 이름: `단일 덱`, `전부 최적화`, `빈자리만 최적화`, `기대 딜량 계산`
  - 모드 힌트: `기대 딜량이 높은 개별 덱을 찾아줘요` / `설정한 덱 개수만큼 최적화해요` / `직접 편성한 니케들을 기반으로 나머지 자리를 최적화해요` / `직접 짠 덱의 기대 딜량만 빠르게 계산해요, 최적화는 하지 않아요`
  - 제출 버튼 유휴 라벨(전 모드·전 탭 공통): `인카운터!`
- 주석은 무엇을/왜만 쓴다. "예전에는 …였다", "…로 바꿨다" 같은 변경 이력은 주석에 남기지 않는다.

---

### Task 1: 앱 셸 네이밍 — RapiLab, 큐브 문구, 탭 라벨

**Files:**
- Modify: `frontend/index.html:7`
- Modify: `frontend/src/App.tsx:27-31`, `frontend/src/App.tsx:76`, `frontend/src/App.tsx:80-82`
- Test: `frontend/src/App.test.tsx:51`, `:90`, `:226`, `:231`, `:232`

**Interfaces:**
- Consumes: 없음 (첫 태스크)
- Produces: 탭 접근명 `니케 풀` / `솔로 레이드`. 이후 태스크의 App 레벨 테스트는 탭을 이 이름으로 연다.

- [ ] **Step 1: 실패하는 테스트로 바꾼다**

`frontend/src/App.test.tsx`에서 다섯 군데를 새 문구로 고친다.

51행:
```tsx
    expect(screen.getByText(/재장전 큐브 15레벨/i)).toBeInTheDocument()
```

90행, 226행, 232행 (`'추천'` 탭을 여는 세 곳):
```tsx
    await user.click(screen.getByRole('tab', { name: '솔로 레이드' }))
```

231행 (`'로스터'` 탭으로 돌아가는 곳):
```tsx
    await user.click(screen.getByRole('tab', { name: '니케 풀' }))
```

같은 파일 49행의 테스트 이름도 내용에 맞춘다:
```tsx
  it('states the harmony cube assumption', () => {
```
는 그대로 두고, 앱 이름을 확인하는 테스트를 하나 추가한다 (48행 `describe('App', () => {` 바로 아래):
```tsx
  it('앱 이름을 RapiLab으로 내건다', () => {
    render(<App />)
    expect(screen.getByRole('heading', { level: 1, name: 'RapiLab' })).toBeInTheDocument()
  })

```

- [ ] **Step 2: 실패를 확인한다**

Run: `npm --prefix frontend test -- --run src/App.test.tsx`
Expected: FAIL — `재장전 큐브 15레벨`, `RapiLab` heading, `솔로 레이드`/`니케 풀` 탭을 못 찾는다.

- [ ] **Step 3: 구현한다**

`frontend/index.html` 7행:
```html
    <title>RapiLab</title>
```

`frontend/src/App.tsx` 27-31행:
```tsx
const TABS: { id: Tab; label: string }[] = [
  { id: 'roster', label: '니케 풀' },
  { id: 'recommend', label: '솔로 레이드' },
  { id: 'union', label: '유니온 레이드' },
]
```

`frontend/src/App.tsx` 76행:
```tsx
        <h1 className="app__title">RapiLab</h1>
```

`frontend/src/App.tsx` 80-82행:
```tsx
        <p className="app__note">
          모든 니케가 재장전 큐브 15레벨을 착용한 것으로 계산합니다.
        </p>
```

- [ ] **Step 4: 통과를 확인한다**

Run: `npm --prefix frontend test -- --run src/App.test.tsx`
Expected: PASS

전체도 돌린다. Run: `npm --prefix frontend test -- --run`
Expected: 388 passed (기준선 387 + 새로 추가한 1건)

- [ ] **Step 5: 커밋**

```bash
git add frontend/index.html frontend/src/App.tsx frontend/src/App.test.tsx
git commit -m "The app is RapiLab, and its tabs are named for what they hold"
```

---

### Task 2: 솔로 레이드 패널 문구 — 카드 제목, 모드 이름, 힌트, 진행 안내

**Files:**
- Modify: `frontend/src/components/RecommendPanel.tsx:413-415` (카드 제목/aria-label), `:431-482` (모드 라디오 4개), `:593-599` (진행 안내)
- Test: `frontend/src/components/RecommendPanel.test.tsx` (아래 목록), `frontend/src/App.test.tsx:57`, `:88`, `:92`, `:189`, `:192`, `:201`, `:227`, `:236`

**Interfaces:**
- Consumes: Task 1의 탭 이름 `솔로 레이드`.
- Produces: 라디오 접근명 `단일 덱` / `전부 최적화` / `빈자리만 최적화` / `기대 딜량 계산`, 카드 heading `솔로 레이드`. Task 3~4의 테스트가 이 이름으로 모드를 고른다.

**주의 — 탭 이름과 heading 이름이 같다.** `솔로 레이드`는 탭(role=`tab`)이자 카드 제목(role=`heading`)이다. 두 쿼리 모두 `role`을 명시하므로 충돌하지 않는다. `getByText('솔로 레이드')`는 쓰지 말 것.

- [ ] **Step 1: 실패하는 테스트로 바꾼다**

`frontend/src/App.test.tsx` — 57행·88행·92행의 heading 이름:
```tsx
    expect(screen.queryByRole('heading', { name: '솔로 레이드' })).not.toBeInTheDocument()
```
```tsx
    expect(screen.getByRole('heading', { name: '솔로 레이드' })).toBeInTheDocument()
```

같은 파일 189·192·227·236행의 `/레이드 배분/i` → `/전부 최적화/i`, 201행의 `/단일 덱/i`는 그대로.

`frontend/src/components/RecommendPanel.test.tsx` — 셀렉터만 일괄 치환한다. 의미는 그대로 두고 이름만 새것으로 옮긴다:

| 현재 셀렉터 | 새 셀렉터 |
|---|---|
| `getByLabelText(/레이드 배분/i)` (263, 280, 314, 332, 360, 686, 846, 906, 938행) | `getByLabelText(/전부 최적화/i)` |
| `getByRole('radio', { name: /레이드 배분/i })` (1036, 1050행) | `getByRole('radio', { name: /전부 최적화/i })` |
| `renderMode(..., /레이드 배분/i)` (995, 1007행) | `renderMode(..., /전부 최적화/i)` |
| `getByRole('radio', { name: /평가/ })` (523, 532, 549, 577, 608, 655, 711, 740, 753행) | `getByRole('radio', { name: /기대 딜량 계산/ })` |

`드래프트 최적화` 라디오를 고르는 곳이 있으면 `/빈자리만 최적화/`로 바꾼다. (402, 461, 481, 1022행의 `getByRole('button', { name: /드래프트 최적화/i })`는 **버튼**이므로 이 태스크에서 건드리지 않는다 — Task 3 소관이다. 라디오인지 버튼인지 `getByRole`의 첫 인자로 판별할 것.)

- [ ] **Step 2: 실패를 확인한다**

Run: `npm --prefix frontend test -- --run src/App.test.tsx src/components/RecommendPanel.test.tsx`
Expected: FAIL — 새 라디오/heading 이름을 못 찾는다.

- [ ] **Step 3: 구현한다**

`frontend/src/components/RecommendPanel.tsx` 413-415행:
```tsx
    <section className="card" aria-label="솔로 레이드">
      <header className="card__header">
        <h2 className="card__title">솔로 레이드</h2>
```

431-482행의 `.mode-switch` 안 라벨 네 개:
```tsx
              <label className="radio">
                <input
                  type="radio"
                  name="recommend-mode"
                  value="single"
                  checked={mode === 'single'}
                  onChange={() => switchMode('single')}
                />
                단일 덱
                <span className="group__hint"> — 기대 딜량이 높은 개별 덱을 찾아줘요</span>
              </label>
              <label className="radio">
                <input
                  type="radio"
                  name="recommend-mode"
                  value="raid"
                  checked={mode === 'raid'}
                  onChange={() => switchMode('raid')}
                />
                전부 최적화
                <span className="group__hint"> — 설정한 덱 개수만큼 최적화해요</span>
              </label>
              <label className="radio">
                <input
                  type="radio"
                  name="recommend-mode"
                  value="draft"
                  checked={mode === 'draft'}
                  onChange={() => switchMode('draft')}
                />
                빈자리만 최적화
                <span className="group__hint">
                  {' '}
                  — 직접 편성한 니케들을 기반으로 나머지 자리를 최적화해요
                </span>
              </label>
              <label className="radio">
                <input
                  type="radio"
                  name="recommend-mode"
                  value="evaluate"
                  checked={mode === 'evaluate'}
                  onChange={() => switchMode('evaluate')}
                />
                기대 딜량 계산
                <span className="group__hint">
                  {' '}
                  — 직접 짠 덱의 기대 딜량만 빠르게 계산해요, 최적화는 하지 않아요
                </span>
              </label>
```

593-599행의 진행 안내에서 모드 이름을 새것으로:
```tsx
      {(mode === 'raid' || mode === 'draft') && raid.status === 'loading' && (
        <p className="recommend-form__progress" role="status">
          {mode === 'raid' ? '전부 최적화 중' : '빈자리만 최적화 중'} — 수천 번의
          시뮬레이션을 실행하며 보통 1~2분이 걸려요. 아직 진행 중이니 완료되면
          버튼이 다시 활성화돼요.
        </p>
      )}
```

- [ ] **Step 4: 통과를 확인한다**

Run: `npm --prefix frontend test -- --run`
Expected: 388 passed

- [ ] **Step 5: 커밋**

```bash
git add frontend/src/components/RecommendPanel.tsx frontend/src/components/RecommendPanel.test.tsx frontend/src/App.test.tsx
git commit -m "Name the modes by what they optimize, not by how they are seeded"
```

---

### Task 3: 제출 버튼 유휴 라벨을 '인카운터!'로 통일

**Files:**
- Modify: `frontend/src/components/RecommendPanel.tsx:381-396` (`submitLabel`)
- Modify: `frontend/src/components/UnionRaidPanel.tsx:205-207`
- Test: `frontend/src/components/RecommendPanel.test.tsx` (아래), `frontend/src/components/UnionRaidPanel.test.tsx:97, 149, 194, 232, 252`, `frontend/src/App.test.tsx:190, 228`

**Interfaces:**
- Consumes: Task 2의 라디오 이름.
- Produces: 두 패널 모두 제출 버튼 접근명이 유휴 시 `인카운터!`. 실행 중 라벨은 모드별로 남는다 (`추천 중…` / `배분 중…` / `최적화 중…` / `계산 중…`).

**주의 — App 레벨에서 버튼 이름이 충돌한다.** `App.tsx`는 세 패널을 동시에 마운트한 채 `hidden`으로만 감춘다. 두 패널의 제출 버튼 이름이 똑같이 `인카운터!`가 되므로, `App.test.tsx`에서 `screen.getByRole('button', { name: /인카운터/ })`는 "found multiple elements"로 터진다. `within()`으로 패널을 스코프해야 한다:

```tsx
import { render, screen, within } from '@testing-library/react'

const soloPanel = () => within(document.getElementById('panel-recommend')!)
```

`RecommendPanel.test.tsx`/`UnionRaidPanel.test.tsx`는 패널 하나만 렌더하므로 스코프가 필요 없다.

- [ ] **Step 1: 실패하는 테스트로 바꾼다**

`frontend/src/App.test.tsx` — 2행의 import에 `within`을 더하고, 190행·228행:
```tsx
    await user.click(
      within(document.getElementById('panel-recommend')!).getByRole('button', {
        name: /인카운터/,
      }),
    )
```

`frontend/src/components/RecommendPanel.test.tsx` — 제출 버튼을 가리키는 모든 셀렉터를 `/인카운터/`로 바꾼다. 유휴 상태를 가리키는 것들이다:

| 현재 | 새것 |
|---|---|
| `getByRole('button', { name: /덱 추천/i })` (100, 111, 145, 156, 176, 200, 220, 241행) | `getByRole('button', { name: /인카운터/ })` |
| `getByRole('button', { name: /레이드 덱 배분/i })` (282, 315, 333, 361, 687, 847, 907, 939, 950, 997, 1009, 1052행) | `getByRole('button', { name: /인카운터/ })` |
| `findByRole('button', { name: /레이드 덱 배분/i })` (1055행 — 로딩이 끝나 유휴로 돌아온 것을 기다린다) | `findByRole('button', { name: /인카운터/ })` |
| `getByRole('button', { name: /드래프트 최적화/i })` (402, 461, 481, 1022행) | `getByRole('button', { name: /인카운터/ })` |

`평가` 모드에서 제출 버튼을 `/기대 딜량 계산/`으로 찾던 곳이 있으면 역시 `/인카운터/`로 바꾼다.

`frontend/src/components/UnionRaidPanel.test.tsx` — 97, 149, 194, 232, 252행의 `getByRole('button', { name: /계산/ })`를 `getByRole('button', { name: /인카운터/ })`로 바꾼다. 단, **실행 중**을 확인하는 곳(버튼이 `계산 중…`인 상태)이 있으면 그건 `/계산 중/`으로 남긴다. 각 줄의 앞뒤 문맥을 읽고 유휴인지 실행 중인지 판별할 것.

라벨 통일 자체를 지키는 회귀 테스트를 넣는다. **기존 `renderMode` 헬퍼는 쓸 수 없다** — `describe('RecommendPanel unit-pool exclusion')`(963행) 안에 스코프돼 있고, 이 테스트는 유닛 풀 제외와 아무 상관이 없다. `RecommendPanel.test.tsx` **맨 끝에 새 최상위 describe**를 연다. 파일 최상위의 `fullRoster`(56행), `makeEvaluateSupportedUnits`(60행), `noPersistence`(71행)는 그대로 쓸 수 있다:

```tsx
// 실행 버튼은 모드를 옮겨도 같은 이름이어야 하고(무엇을 시작하는지는 모드
// 라디오가 말한다), 스크롤을 내려도 닿을 수 있어야 한다.
describe('RecommendPanel 실행 버튼', () => {
  const renderAndPick = async (radio: RegExp) => {
    vi.mocked(getSupportedUnits).mockResolvedValue(makeEvaluateSupportedUnits())
    const user = userEvent.setup()
    render(<RecommendPanel roster={fullRoster} {...noPersistence} />)
    await user.click(screen.getByRole('radio', { name: radio }))
    await screen.findByRole('button', { name: /a 사용/i }) // 팔레트 도착
    return user
  }

  it('모드를 바꿔도 유휴 상태의 라벨은 늘 인카운터!다', async () => {
    const user = await renderAndPick(/전부 최적화/i)
    expect(screen.getByRole('button', { name: /인카운터/ })).toBeInTheDocument()

    await user.click(screen.getByRole('radio', { name: /빈자리만 최적화/i }))
    expect(screen.getByRole('button', { name: /인카운터/ })).toBeInTheDocument()

    await user.click(screen.getByRole('radio', { name: /기대 딜량 계산/ }))
    expect(screen.getByRole('button', { name: /인카운터/ })).toBeInTheDocument()

    await user.click(screen.getByRole('radio', { name: /단일 덱/ }))
    expect(screen.getByRole('button', { name: /인카운터/ })).toBeInTheDocument()
  })
})
```

Task 4가 이 describe에 테스트를 더 붙이므로 `renderAndPick`은 여기 남겨둔다.

- [ ] **Step 2: 실패를 확인한다**

Run: `npm --prefix frontend test -- --run`
Expected: FAIL — `인카운터` 이름의 버튼이 없다.

- [ ] **Step 3: 구현한다**

`frontend/src/components/RecommendPanel.tsx` 381-396행의 `submitLabel`을 통째로 바꾼다:
```tsx
  // 유휴 라벨은 모드와 무관하게 하나다 - 무엇을 시작하는 버튼인지는 바로 위의
  // 모드 라디오가 이미 말한다. 실행 중 라벨만 모드별로 갈리는데, 버튼이 진행
  // 상태를 알려주는 유일한 자리이기 때문이다.
  const loadingLabel =
    mode === 'single'
      ? '추천 중…'
      : mode === 'raid'
        ? '배분 중…'
        : mode === 'draft'
          ? '최적화 중…'
          : '계산 중…'
  const submitLabel = active.status === 'loading' ? loadingLabel : '인카운터!'
```

`frontend/src/components/UnionRaidPanel.tsx` 205-207행:
```tsx
          <button type="submit" className="btn btn--primary" disabled={!canSubmit}>
            {evaluation.status === 'loading' ? '계산 중…' : '인카운터!'}
          </button>
```

- [ ] **Step 4: 통과를 확인한다**

Run: `npm --prefix frontend test -- --run`
Expected: 389 passed

- [ ] **Step 5: 커밋**

```bash
git add frontend/src/components/RecommendPanel.tsx frontend/src/components/UnionRaidPanel.tsx frontend/src/components/RecommendPanel.test.tsx frontend/src/components/UnionRaidPanel.test.tsx frontend/src/App.test.tsx
git commit -m "One idle label for every run button: 인카운터!"
```

---

### Task 4: 솔로 레이드 — 실행 버튼을 스크롤과 무관하게 닿게 한다

**Files:**
- Modify: `frontend/src/components/RecommendPanel.tsx:504-526` (액션 블록 정의 위치), `:575-587` (덱 컬럼), `:591` (폼 끝)
- Modify: `frontend/src/App.css:872-878` (`.recommend-form__actions` 바로 뒤에 modifier 추가)
- Test: `frontend/src/components/RecommendPanel.test.tsx`

**Interfaces:**
- Consumes: Task 3의 `submitLabel`, 버튼 접근명 `인카운터!`.
- Produces: 액션 블록의 DOM 위치가 모드에 달렸다. `single`/`raid`는 `<form>`의 마지막 자식이며 `.recommend-form__actions--sticky` 클래스를 갖는다. `draft`/`evaluate`는 `.draft-layout__decks` 안, `DraftEditor` 뒤에 온다.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

**(a)** Task 3이 만든 `describe('RecommendPanel 실행 버튼')` 안에 세 개를 더한다. `renderAndPick`은 그 describe에 이미 있다:

```tsx
  it('덱 컬럼이 없는 모드에서는 실행 버튼이 화면 하단 고정 바에 선다', async () => {
    await renderAndPick(/전부 최적화/i)

    const button = screen.getByRole('button', { name: /인카운터/ })
    expect(button.closest('.recommend-form__actions--sticky')).not.toBeNull()
    expect(button.closest('.draft-layout__decks')).toBeNull()
  })

  it('덱 컬럼이 있는 모드에서는 실행 버튼이 덱과 함께 붙어 다닌다', async () => {
    const user = await renderAndPick(/전부 최적화/i)
    await user.click(screen.getByRole('radio', { name: /빈자리만 최적화/i }))

    const button = screen.getByRole('button', { name: /인카운터/ })
    expect(button.closest('.draft-layout__decks')).not.toBeNull()
    expect(button.closest('.recommend-form__actions--sticky')).toBeNull()
  })

  it('기대 딜량 계산 모드도 실행 버튼을 덱 컬럼에 둔다', async () => {
    const user = await renderAndPick(/전부 최적화/i)
    await user.click(screen.getByRole('radio', { name: /기대 딜량 계산/ }))

    expect(
      screen.getByRole('button', { name: /인카운터/ }).closest('.draft-layout__decks'),
    ).not.toBeNull()
  })
```

**(b)** 기존 테스트 하나가 이 이동과 정면으로 부딪힌다. `RecommendPanel.test.tsx:106-123`의 `puts the boss profile beside the mode choice, with no palette between them`은 제출 버튼이 setup 행 **안에** 있다고 단언한다(117행). 버튼이 그 행을 떠나므로 이 단언만 걷어낸다 — 보스와 모드가 같은 행에 있고 그 행이 팔레트보다 앞에 온다는, 이 테스트의 본래 주장은 그대로 남는다. `submit` 지역 변수(111행)와 117행을 지워 이렇게 만든다:

```tsx
  it('puts the boss profile beside the mode choice, with no palette between them', () => {
    render(<RecommendPanel roster={fullRoster} {...noPersistence} />)

    const boss = screen.getByRole('group', { name: /보스 설정/i })
    const mode = screen.getByRole('group', { name: /^모드$/i })
    const palette = screen.getByRole('group', { name: /사용할 유닛/i })

    // Same row: one wrapper holds the boss fields and the mode block.
    const setup = boss.parentElement!
    expect(setup).toBe(mode.parentElement)
    expect(setup.contains(palette)).toBe(false)

    // ...and that row comes before the palette in the document.
    expect(setup.compareDocumentPosition(palette) & Node.DOCUMENT_POSITION_FOLLOWING)
      .toBeTruthy()
  })
```

103-105행의 주석은 "버튼과 보스 필드 사이의 거리"를 설명하는데 그 근거가 유지되므로 손대지 않는다.

- [ ] **Step 2: 실패를 확인한다**

Run: `npm --prefix frontend test -- --run src/components/RecommendPanel.test.tsx`
Expected: FAIL — 지금은 어느 모드든 버튼이 모드 fieldset 안에 있어 두 `closest`가 모두 `null`이다.

- [ ] **Step 3: 구현한다**

`frontend/src/components/RecommendPanel.tsx` 504-526행의 액션 블록을 모드 fieldset에서 **들어낸다**. 지운 자리(`</fieldset>` 직전)에는 아무것도 남기지 않는다.

`return` 직전(410행 `switchMode` 정의 아래)에 버튼 내용물을 한 번만 정의한다:
```tsx
  // 실행 버튼은 두 자리 중 하나에 선다 - 아래 폼을 볼 것. 내용물은 같으므로
  // 여기서 한 번만 만든다.
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
      {mode !== 'evaluate' && rosterTooSmall && (
        <p className="field__error" role="alert">
          덱을 추천하려면 준비된 니케가 최소 {MIN_DECK_ROSTER_SIZE}기 필요해요.
        </p>
      )}
    </>
  )
```

덱 컬럼(575-587행) 안, `DraftEditor` 바로 뒤에 액션을 넣는다:
```tsx
              <div className="draft-layout__decks">
                <DraftEditor
                  numDecks={numDecks}
                  value={draftValue}
                  onChange={setDraftValue}
                  portraitFor={portraitFor}
                  nameFor={nameFor}
                  burstTierFor={burstTierFor}
                  // Evaluate has no optimizer to constrain - locking a unit in
                  // place has nothing to mean there.
                  showLocks={mode !== 'evaluate'}
                />
                {/* 이 컬럼은 sticky라, 여기 얹은 실행 버튼은 덱과 함께
                    화면에 남는다. */}
                <div className="recommend-form__actions">{actionButtons}</div>
              </div>
```

폼의 마지막 자식으로(591행 `</form>` 직전) 하단 고정 바를 넣는다:
```tsx
        {/* 덱 컬럼이 없는 모드다. 팔레트 70여 개 칩이 화면보다 길어 실행
            버튼이 스크롤 밖으로 밀리므로, 대신 화면 하단에 붙인다. */}
        {(mode === 'single' || mode === 'raid') && (
          <div className="recommend-form__actions recommend-form__actions--sticky">
            {actionButtons}
          </div>
        )}
```

`frontend/src/App.css` — 878행 `.recommend-form__actions` 규칙 바로 뒤에 붙인다:
```css
/* 덱 컬럼이 없는 모드의 실행 버튼. 카드 패딩만큼 좌우로 넓혀 카드 폭을 채우고,
   불투명 배경으로 아래 팔레트를 가린다. 팔레트의 유닛 상세 팝오버가 z-index 2라
   그보다 위에 서야 버튼이 가려지지 않는다. */
.recommend-form__actions--sticky {
  position: sticky;
  bottom: 0;
  z-index: 3;
  margin: 0 calc(-1 * var(--sp-5));
  width: calc(100% + var(--sp-5) * 2);
  padding: var(--sp-3) var(--sp-5);
  border-top: 1px solid var(--border);
  background: var(--surface);
}
```

- [ ] **Step 4: 통과를 확인한다**

Run: `npm --prefix frontend test -- --run`
Expected: 392 passed

- [ ] **Step 5: 커밋**

```bash
git add frontend/src/components/RecommendPanel.tsx frontend/src/components/RecommendPanel.test.tsx frontend/src/App.css
git commit -m "The run button follows the player down the roster, whichever mode they picked"
```

---

### Task 5: 유니온 레이드 — 실행 버튼을 덱 컬럼으로

**Files:**
- Modify: `frontend/src/components/UnionRaidPanel.tsx:187-208`
- Test: `frontend/src/components/UnionRaidPanel.test.tsx`

**Interfaces:**
- Consumes: Task 3의 `인카운터!` 라벨, Task 4가 쓴 `.draft-layout__decks` 배치 관례.
- Produces: 없음 (마지막 태스크)

**공유하지 않는 이유:** `RecommendPanel`의 액션 블록에는 취소 버튼과 로스터 크기 경고가 있고 여기엔 둘 다 없다. 공통 컴포넌트로 묶으면 조건부 props만 늘어난다. 마크업 한 줄씩을 각자 갖는다.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`frontend/src/components/UnionRaidPanel.test.tsx` 끝에 붙인다. 파일 안의 기존 렌더 헬퍼를 그대로 쓸 것:

```tsx
  it('실행 버튼이 덱 컬럼 안에 있어 편성과 함께 화면에 남는다', async () => {
    renderPanel()

    expect(
      screen.getByRole('button', { name: /인카운터/ }).closest('.draft-layout__decks'),
    ).not.toBeNull()
  })
```

- [ ] **Step 2: 실패를 확인한다**

Run: `npm --prefix frontend test -- --run src/components/UnionRaidPanel.test.tsx`
Expected: FAIL — 버튼이 아직 폼 바닥에 있어 `closest`가 `null`이다.

- [ ] **Step 3: 구현한다**

`frontend/src/components/UnionRaidPanel.tsx` — 204-208행의 액션 블록을 지우고, 187-200행의 덱 컬럼 안 `DraftEditor` 뒤로 옮긴다:
```tsx
            <div className="draft-layout__decks">
              <DraftEditor
                numDecks={numBattles}
                value={draftValue}
                onChange={setDraftValue}
                portraitFor={portraitFor}
                nameFor={nameFor}
                burstTierFor={burstTierFor}
                // There is no optimizer here to constrain - locking a unit in
                // place has nothing to mean on a screen that only scores what
                // was placed.
                showLocks={false}
              />
              {/* 이 컬럼은 sticky라, 여기 얹은 실행 버튼은 편성과 함께
                  화면에 남는다. */}
              <div className="recommend-form__actions">
                <button type="submit" className="btn btn--primary" disabled={!canSubmit}>
                  {evaluation.status === 'loading' ? '계산 중…' : '인카운터!'}
                </button>
              </div>
            </div>
```

`</fieldset>`과 `</form>` 사이에는 이제 아무것도 없다.

- [ ] **Step 4: 통과를 확인한다**

Run: `npm --prefix frontend test -- --run`
Expected: 393 passed

- [ ] **Step 5: 커밋**

```bash
git add frontend/src/components/UnionRaidPanel.tsx frontend/src/components/UnionRaidPanel.test.tsx
git commit -m "Union raid's run button rides with the battle line-ups"
```

---

## 마무리 (플랜 실행자 아닌 주 세션이 한다)

- `docs/roadmap.md`의 To-Do에 이번 작업 반영
- 실제 앱을 띄워 하단 고정 바와 덱 컬럼 배치를 눈으로 확인 (`/run` 또는 `/verify`)
- 브랜치 푸시 후 draft PR
