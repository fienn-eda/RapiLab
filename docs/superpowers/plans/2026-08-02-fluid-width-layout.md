# 창 폭을 쓰는 레이아웃 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 1120px에 갇힌 앱을 창 폭에 맞게 유동화하고, 결과와 실행 버튼을 설정 행 바로 아래로 올려 팔레트를 스크롤해 지나지 않아도 되게 한다.

**Architecture:** 레이아웃 변경은 두 갈래다. (1) CSS — `.app`의 폭 상한을 없애고, 대신 문장을 담는 블록에만 `--measure` 읽기 폭을 건다. 이미 `auto-fill` 그리드와 `flex-wrap`으로 짜인 하위 요소들은 따라온다. (2) JSX — 진행/에러/결과 블록과 (단일·전부 최적화 모드의) 실행 버튼을 폼 끝에서 설정 행 바로 뒤로 옮긴다. 새 컴포넌트도 새 상태도 만들지 않는다.

**Tech Stack:** React 19 + TypeScript + Vite, Vitest + @testing-library/react (jsdom)

## Global Constraints

- 스펙: `docs/superpowers/specs/2026-08-02-fluid-width-layout-design.md`
- 프론트 테스트 기준선: 49개 파일 464 통과. 어느 태스크도 이 수를 **줄이지 않는다**. 테스트를 삭제하거나 약화시키지 않는다.
- `frontend/vite.config.ts`에 `test: { css: false }` — **Vitest는 CSS를 처리하지 않는다.** 따라서 CSS 규칙은 단위 테스트로 검증할 수 없다. CSS 태스크의 검증은 Task 5의 실제 앱 육안 확인이다. 이를 대신할 가짜 테스트를 만들지 않는다.
- 주석은 **무엇을·왜**만 쓴다. "예전엔 이랬다", "N에서 옮김" 같은 변경 이력을 코드 주석에 남기지 않는다 (프로젝트 CLAUDE.md).
- 명령은 모두 워크트리 루트 `C:\Users\fienn\Desktop\NikkeDeckBuilder\.claude\worktrees\fluid-width-layout` 기준이다.
- 이 브랜치는 `wip/scaffolding`(트렁크) 위에 리베이스되어 있다. 아래 줄 번호는 그 기준이다.

## File Structure

| 파일 | 역할 | 태스크 |
| --- | --- | --- |
| `frontend/src/components/RecommendPanel.tsx` | 솔로 레이드 패널. 폼 내부 순서를 바꾼다 | 1, 2 |
| `frontend/src/components/RecommendPanel.test.tsx` | 위 패널의 DOM 순서 테스트를 추가 | 1, 2 |
| `frontend/src/components/UnionRaidPanel.tsx` | 유니온 레이드 패널. 같은 순서 변경 | 3 |
| `frontend/src/components/UnionRaidPanel.test.tsx` | 위 패널의 DOM 순서 테스트를 추가 | 3 |
| `frontend/src/App.css` | 폭 상한 제거 · 글줄 폭 제한 · sticky 바 규칙 삭제 | 2, 4 |
| `frontend/src/index.css` | `--measure` 토큰 추가 | 4 |
| `docs/roadmap.md` | 착륙 기록 | 5 |

---

### Task 1: 결과·에러·진행 메시지를 설정 행 바로 아래로 (RecommendPanel)

결과 블록이 유닛 팔레트 **뒤**에 있어, 결과를 보려면 70여 개 칩을 스크롤해 지나야 한다. 설정 행 바로 뒤로 옮긴다.

**Files:**
- Modify: `frontend/src/components/RecommendPanel.tsx:517-673`
- Test: `frontend/src/components/RecommendPanel.test.tsx`

**Interfaces:**
- Consumes: 없음 (첫 태스크)
- Produces: 없음. JSX 순서만 바뀌고 export·props·훅 시그니처는 그대로다.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`frontend/src/components/RecommendPanel.test.tsx`의 기존 `'puts the boss profile beside the mode choice, with no palette between them'` 테스트(106행부터) **바로 뒤**에 넣는다. 그 테스트가 쓰는 `compareDocumentPosition` 패턴을 그대로 따른다.

```tsx
  // 결과를 읽으려면 70여 개 칩의 팔레트를 스크롤해 지나야 해서는 안 된다.
  it('renders the results above the unit palette', async () => {
    const user = userEvent.setup()
    vi.mocked(recommendDecks).mockResolvedValue({
      decks: [
        {
          deck: ['a', 'b', 'c', 'd', 'e'],
          total_damage: 100,
          burst_damage: 60,
          normal_attack_damage: 40,
          skill_damage: 0,
        },
      ],
      excluded_slugs: [],
      engine_version: 'test-engine-version',
    })

    render(<RecommendPanel roster={fullRoster} {...noPersistence} />)
    await user.click(screen.getByRole('button', { name: /인카운터/ }))

    const results = (await screen.findByText('#1')).closest('ol')!
    const palette = screen.getByRole('group', { name: /사용할 유닛/i })

    expect(results.compareDocumentPosition(palette) & Node.DOCUMENT_POSITION_FOLLOWING)
      .toBeTruthy()
  })
```

- [ ] **Step 2: 실패하는지 확인한다**

Run: `cd frontend && npm test -- --run RecommendPanel`
Expected: FAIL — `renders the results above the unit palette`에서 `expect(received).toBeTruthy()` / received `0`. (결과가 팔레트 **뒤**에 있어 `DOCUMENT_POSITION_FOLLOWING` 비트가 서지 않는다.)

- [ ] **Step 3: 진행·에러·결과 블록을 폼 안으로 옮긴다**

`RecommendPanel.tsx`에서 현재 `</form>`(591행) **뒤**에 있는 블록 전체 — 593행 `{(mode === 'raid' || mode === 'draft') && raid.status === 'loading' && (` 부터 673행 `)}` 까지 — 를 잘라내어, `recommend-form__setup` div가 닫히는 517행 `</div>` **바로 다음 줄**에 붙여넣는다. 잘라낸 자리(현재 `</form>`와 `</section>` 사이)에는 아무것도 남지 않는다.

옮긴 블록 맨 앞에 이 주석을 단다:

```tsx
        {/* 답은 설정 바로 아래에 선다. 팔레트와 편성 칸은 그 아래로, 결과를
            읽는 데 스크롤이 필요 없도록. */}
```

이동하는 JSX는 한 글자도 고치지 않는다 — 진행 메시지 두 개, 에러 세 개, 결과 네 개(`DeckResults` / `RaidResults` / `DraftResults` / `EvaluationResults`)가 조건까지 그대로 따라간다.

- [ ] **Step 4: 통과하는지 확인한다**

Run: `cd frontend && npm test -- --run RecommendPanel`
Expected: PASS — 새 테스트 포함, `RecommendPanel.test.tsx` 전부 통과.

- [ ] **Step 5: 전체 테스트를 돌린다**

Run: `cd frontend && npm test -- --run`
Expected: 465 통과 (기준선 464 + 새 테스트 1). 실패가 있으면 그 테스트가 **무엇을 지키려 했는지** 읽고 기대만 고친다. 삭제하지 않는다.

- [ ] **Step 6: 커밋한다**

```bash
git add frontend/src/components/RecommendPanel.tsx frontend/src/components/RecommendPanel.test.tsx
git commit -m "Stand the results under the setup row, above the palette

A run's answer sat past the whole 70-chip palette, so reading it meant
scrolling through every unit you own. It now follows the boss/mode row
directly, which is where you are already looking when the run ends."
```

---

### Task 2: 단일·전부 최적화 모드의 실행 버튼을 설정 행 아래로

이 두 모드의 실행 버튼은 화면 하단 sticky 바에 붙어 있다. 설정 바로 아래·결과 위로 올리고, sticky 바를 지탱하던 CSS를 지운다. 빈자리·기대 딜량·유니온 모드의 버튼은 sticky 덱 컬럼에 있어 **건드리지 않는다**.

**Files:**
- Modify: `frontend/src/components/RecommendPanel.tsx` (Task 1 적용 후의 폼 본문)
- Modify: `frontend/src/App.css:894-906` (sticky 규칙 삭제)
- Test: `frontend/src/components/RecommendPanel.test.tsx`

**Interfaces:**
- Consumes: Task 1이 옮겨 놓은 진행/에러/결과 블록의 위치 (버튼은 그 **앞**에 선다)
- Produces: 없음. `actionButtons`(410행)의 정의와 이름은 그대로다.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

Task 1에서 추가한 테스트 바로 뒤에 넣는다.

```tsx
  // 팔레트 아래 sticky 바에 있던 실행 버튼을, 그것이 작용하는 설정 바로
  // 아래에 세운다.
  it('stands the run button between the setup row and the palette', () => {
    render(<RecommendPanel roster={fullRoster} {...noPersistence} />)

    const boss = screen.getByRole('group', { name: /보스 설정/i })
    const setup = boss.parentElement!
    const submit = screen.getByRole('button', { name: /인카운터/ })
    const palette = screen.getByRole('group', { name: /사용할 유닛/i })

    expect(setup.compareDocumentPosition(submit) & Node.DOCUMENT_POSITION_FOLLOWING)
      .toBeTruthy()
    expect(submit.compareDocumentPosition(palette) & Node.DOCUMENT_POSITION_FOLLOWING)
      .toBeTruthy()
  })
```

- [ ] **Step 2: 실패하는지 확인한다**

Run: `cd frontend && npm test -- --run RecommendPanel`
Expected: FAIL — 두 번째 `expect`에서 received `0`. (버튼이 팔레트 **뒤**에 있다.)

- [ ] **Step 3: 버튼을 옮기고 sticky 수식자를 뗀다**

`RecommendPanel.tsx`에서 폼 끝의 이 블록을 **삭제**한다 (주석 포함):

```tsx
        {/* 덱 컬럼이 없는 모드다. 팔레트 70여 개 칩이 화면보다 길어 실행
            버튼이 스크롤 밖으로 밀리므로, 대신 화면 하단에 붙인다. */}
        {(mode === 'single' || mode === 'raid') && (
          <div className="recommend-form__actions recommend-form__actions--sticky">
            {actionButtons}
          </div>
        )}
```

그리고 `recommend-form__setup` div가 닫히는 `</div>` 바로 뒤, **Task 1이 붙여넣은 결과 블록보다 앞**에 이것을 넣는다:

```tsx
        {/* 덱 컬럼이 없는 모드의 실행 버튼. 자기가 작용하는 보스·모드 설정
            바로 아래에 선다. */}
        {(mode === 'single' || mode === 'raid') && (
          <div className="recommend-form__actions">{actionButtons}</div>
        )}
```

- [ ] **Step 4: 죽은 CSS 규칙을 지운다**

`frontend/src/App.css`의 894-906행을 통째로 삭제한다 — 주석 세 줄과 `.recommend-form__actions--sticky` 블록 전체:

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

`.recommend-form__actions`(886-892행)는 **남긴다** — 새 위치에서도 그 flex 규칙을 쓴다.

지운 뒤 참조가 정말 없는지 확인한다:

Run: `grep -rn "recommend-form__actions--sticky" frontend/src`
Expected: 아무것도 나오지 않는다.

- [ ] **Step 5: 통과하는지 확인한다**

Run: `cd frontend && npm test -- --run`
Expected: 466 통과 (464 + Task 1의 1 + 이번 1).

- [ ] **Step 6: 커밋한다**

```bash
git add frontend/src/components/RecommendPanel.tsx frontend/src/components/RecommendPanel.test.tsx frontend/src/App.css
git commit -m "Put the run button under the setup it acts on

The bottom sticky bar existed because the palette pushed the button off
screen. With the button above the palette that reason is gone, and with
it the negative margins and the z-index it needed to cover the popovers
underneath. The draft and union modes keep their button in the sticky
deck column, where it is already always on screen."
```

---

### Task 3: 유니온 레이드 결과를 편성 위로

`UnionRaidPanel`도 결과가 편성(팔레트|덱) 뒤에 있다. 보스 설정 뒤로 옮긴다. **실행 버튼은 sticky 덱 컬럼에 그대로 둔다** — 드래그하다 실행할 때 이미 화면에 있다.

**Files:**
- Modify: `frontend/src/components/UnionRaidPanel.tsx:170-231`
- Test: `frontend/src/components/UnionRaidPanel.test.tsx`

**Interfaces:**
- Consumes: 없음. Task 1·2와 독립이다.
- Produces: 없음.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`UnionRaidPanel.test.tsx`의 `describe('UnionRaidPanel', ...)` 안 맨 끝에 넣는다. 이 파일의 테스트 이름은 한국어다 — 그 관례를 따른다.

```tsx
  it('결과를 편성 위에 그린다', async () => {
    const user = userEvent.setup()
    vi.mocked(evaluateDecks).mockResolvedValue({
      decks: [
        { deck: ['u0', 'u1', 'u2', 'u3', 'u4'], total_damage: 10, burst_damage: 6, normal_attack_damage: 4, skill_damage: 0 },
        { deck: ['u5', 'u6', 'u7', 'u8', 'u9'], total_damage: 20, burst_damage: 12, normal_attack_damage: 8, skill_damage: 0 },
        { deck: ['u10', 'u11', 'u12', 'u13', 'u14'], total_damage: 30, burst_damage: 18, normal_attack_damage: 12, skill_damage: 0 },
      ],
      combined_total_damage: 60,
      excluded_slugs: [],
      engine_version: 'test-engine-version',
    })

    renderPanel()
    await screen.findByRole('button', { name: /u0 사용/i })
    for (let deck = 0; deck < 3; deck += 1) {
      for (let seat = 0; seat < 5; seat += 1) {
        dropOnDeck(deck + 1, `u${deck * 5 + seat}`)
      }
    }
    await user.click(screen.getByRole('button', { name: /인카운터/ }))

    const results = (await screen.findByText('60 총딜')).closest('section, div')!
    const roster = screen.getByRole('group', { name: /편성/ })

    expect(results.compareDocumentPosition(roster) & Node.DOCUMENT_POSITION_FOLLOWING)
      .toBeTruthy()
  })
```

`'60 총딜'`이 실제 렌더 문자열과 다르면, `EvaluationResults.tsx`가 합계를 어떻게 쓰는지 읽고 그 문자열로 맞춘다. 합계 텍스트를 못 찾으면 대신 첫 덱을 앵커로 쓴다: `(await screen.findByText('덱 1')).closest('li')!`. **테스트를 지우고 넘어가지 않는다.**

- [ ] **Step 2: 실패하는지 확인한다**

Run: `cd frontend && npm test -- --run UnionRaidPanel`
Expected: FAIL — `expect(received).toBeTruthy()` / received `0`.

- [ ] **Step 3: 블록을 옮긴다**

`UnionRaidPanel.tsx`에서 `</form>`(210행) 뒤의 212-231행 — 진행 메시지, 에러, `EvaluationResults` — 를 잘라내어, `union-raid-form__battles` div가 닫히는 170행 `</div>` **바로 뒤**, `편성` fieldset(172행)보다 **앞**에 붙여넣는다.

옮긴 블록 맨 앞에 이 주석을 단다:

```tsx
        {/* 답은 보스 설정 바로 아래에 선다. 편성 칸은 그 아래로. */}
```

- [ ] **Step 4: 통과하는지 확인한다**

Run: `cd frontend && npm test -- --run`
Expected: 467 통과 (464 + 3).

- [ ] **Step 5: 커밋한다**

```bash
git add frontend/src/components/UnionRaidPanel.tsx frontend/src/components/UnionRaidPanel.test.tsx
git commit -m "Stand the union raid result above its roster

Same placement the solo tab now uses: the answer follows the boss
settings, and the seats you fill sit below it. The run button stays in
the sticky deck column, which keeps it on screen while you drag."
```

---

### Task 4: 폭 유동화와 글줄 폭 제한

`.app`의 1120px 상한을 없애 창을 다 쓰고, 대신 문장을 담는 블록에만 읽기 폭을 건다.

**Files:**
- Modify: `frontend/src/index.css:6-61` (`:root` 토큰)
- Modify: `frontend/src/App.css:5-13` (`.app`), 그리고 아래 문장 블록들

**Interfaces:**
- Consumes: Task 2가 `.recommend-form__actions--sticky`를 이미 지웠다는 것
- Produces: `--measure` CSS 변수. 이후 문장 블록은 이 토큰을 쓴다.

- [ ] **Step 1: `--measure` 토큰을 추가한다**

`frontend/src/index.css`의 `:root` 안, `--sans`/`--mono` 폰트 선언(57-58행) 바로 뒤에 넣는다:

```css
  /* 읽기 폭. 레이아웃은 창을 다 쓰지만 문장은 이 폭을 넘지 않는다 - 한 줄이
     길어질수록 다음 줄 첫 글자를 찾기 어려워진다. */
  --measure: 72ch;
```

- [ ] **Step 2: `.app`의 폭 상한을 없앤다**

`frontend/src/App.css`의 1-13행을 이것으로 바꾼다. 주석은 이제 그리드가 창을 따라간다는 사실을 설명해야 한다:

```css
/* Layout and component styles for the ShiftyPad investment-data input UI. */

/* 창 폭을 그대로 쓴다. 로스터 그리드와 유닛 팔레트는 열 수로 폭을 받아내고,
   문장은 --measure가 따로 잡는다. */
.app {
  margin: 0 auto;
  padding: var(--sp-6) var(--sp-5) var(--sp-6);
  display: flex;
  flex-direction: column;
  gap: var(--sp-5);
  min-height: 100svh;
}
```

- [ ] **Step 3: 문장 블록에 읽기 폭을 건다**

`App.css`의 해당 규칙마다 `max-width: var(--measure);` 한 줄을 더한다. 대상은 정확히 이 일곱이다:

- `.app__subtitle` (27행)
- `.app__note` (31행)
- `.recommend-form__progress` (1076행 근처)
- `.raid-results__note, .evaluation-results__ordering-note` (1083행 근처)
- `.deck-results__excluded, .raid-results__leftover` (1062행 근처)
- `.charge-panel__assumption` (1628행 근처)
- `.mode-switch` (1070행 근처) — 모드 힌트는 `<span class="group__hint">`인데 인라인이라 `max-width`가 듣지 않는다. 그래서 컨테이너에 건다.

`.empty__text`는 JSX에만 있고 `App.css`에 규칙이 없다 (확인함). 문장도 한 줄짜리 안내라 읽기 폭이 필요 없다. 이 클래스를 위해 새 규칙을 만들지 않는다.
- 팔레트 요약문 — `.group__details`에는 규칙이 없으므로 새로 만든다. `.group` 규칙(582행) 바로 뒤에 넣는다:

```css
/* 접이식 그룹의 요약문은 문장이라 읽기 폭을 넘지 않는다. */
.group__details > summary {
  max-width: var(--measure);
}
```

`.sync__hint`는 `max-width: 480px`로 일부러 더 좁게 잡혀 있다. **건드리지 않는다.**

- [ ] **Step 4: 회귀가 없는지 확인한다**

Vitest는 CSS를 처리하지 않으므로(`css: false`) 이 태스크는 테스트를 늘리지 않는다. 기존 테스트가 깨지지 않는 것만 확인한다.

Run: `cd frontend && npm test -- --run`
Expected: 467 통과 (Task 3과 같은 수 — CSS는 테스트에 보이지 않는다).

- [ ] **Step 5: 커밋한다**

```bash
git add frontend/src/App.css frontend/src/index.css
git commit -m "Let the app take the window, and the prose keep its measure

A 1920px window spent 42% of itself on empty margin while the roster
grid ran six tiles wide. The cap is gone; the grids and the chip palette
answer the window with column count. Sentences get --measure instead, so
widening the app does not stretch a hint into an unreadable line."
```

---

### Task 5: 실제 앱에서 눈으로 확인하고 기록한다

CSS는 단위 테스트가 닿지 않는다. 진짜 검증은 여기다.

**Files:**
- Modify: `docs/roadmap.md` (착륙 기록)

**Interfaces:**
- Consumes: Task 1-4 전부
- Produces: 없음

- [ ] **Step 1: 백엔드를 띄운다**

로컬 개발은 서버 두 개다 — Vite(:5173)가 `/api/*`를 FastAPI(:8000)로 프록시한다. 백엔드를 안 띄우면 ECONNREFUSED가 난다.

Run: `cd backend && python -m uvicorn app.main:app --port 8000`
(백그라운드로 돌린다.)

- [ ] **Step 2: 프론트를 띄운다**

Run: `cd frontend && npm run dev`
Expected: `http://localhost:5173`

- [ ] **Step 3: 세 폭에서 확인한다**

브라우저 창을 **1920px → 1400px → 900px** 폭으로 바꿔가며 각각 확인한다. 스크린샷을 남긴다.

확인 항목:

1. **니케 풀 탭** — 1920px에서 로스터 그리드 열 수가 1120px 시절(6열)보다 늘었다.
2. **솔로 레이드 탭** — 실행 버튼이 보스·모드 설정 바로 아래에 있고, 화면 하단에 sticky 바가 **없다**.
3. **솔로 레이드 탭, 실행 후** — 결과가 팔레트보다 위에 있다.
4. **긴 힌트 문장** — 모드 라디오의 설명이 창 끝까지 늘어지지 않는다.
5. **빈자리 최적화 / 유니온 레이드 탭** — 덱 컬럼이 여전히 화면에 고정(sticky)되고, 그 안의 실행 버튼도 같이 남는다.
6. **900px** — 기존 축소 규칙(`@media (max-width: 900px)`)이 그대로 돌아 한 컬럼으로 접힌다. **이 폭에서의 동작은 바뀌면 안 된다.**

어긋나는 것이 있으면 고치고 다시 확인한다. 특히 6번이 깨졌다면 회귀다.

- [ ] **Step 4: `docs/roadmap.md`를 갱신한다**

To-Do / 진행 상태에 이번 작업을 반영한다. 파일을 먼저 읽고 그 형식에 맞춘다.

- [ ] **Step 5: 최종 확인과 커밋**

Run: `cd frontend && npm test -- --run`
Expected: 467 통과, 실패 0.

```bash
git add docs/roadmap.md
git commit -m "Roadmap: the fluid-width layout landed"
```

- [ ] **Step 6: 남길 만한 것이 있으면 기록한다**

육안 확인에서 재사용할 만한 교훈(예: 어떤 폭에서 무엇이 깨졌는지)이 나왔다면 `/document`로 `docs/insights.md`에 남긴다. 없으면 건너뛴다.

---

## Self-Review

**스펙 커버리지**

| 스펙 항목 | 태스크 |
| --- | --- |
| 1. `.app` 폭 제한 해제, 패딩 sp-4 → sp-5 | Task 4 Step 2 |
| 2. `--measure` 토큰 + 문장 블록 8곳 (규칙 7개 + 새 `summary` 규칙 1개) | Task 4 Step 1, 3 |
| 3. 결과를 설정 행 아래로 (RecommendPanel) | Task 1 |
| 3. 결과를 설정 행 아래로 (UnionRaidPanel) | Task 3 |
| 4. 단일·전부 모드 실행 버튼 이동 + sticky CSS 삭제 | Task 2 |
| 4. 나머지 모드 버튼은 유지 | Task 2 Step 3 (명시), Task 5 Step 3 항목 5 (확인) |
| 검증: 테스트 기준선 | 각 태스크 마지막 Step |
| 검증: 1920/1400/900px 육안 | Task 5 Step 3 |

빠진 항목 없음.

**Placeholder 스캔**

"TBD"·"적절히 처리"·"위 내용의 테스트를 작성" 없음. Task 3 Step 1과 Task 4 Step 3에 조건부 분기가 하나씩 있으나, 둘 다 **무엇을 확인하고 무엇을 대신 쓸지**를 명시했다 (앵커 텍스트 대안, `grep`으로 존재 확인).

**타입·이름 일관성**

- `actionButtons` — Task 2에서만 쓰이고 정의는 건드리지 않는다.
- `.recommend-form__actions` (남김) vs `.recommend-form__actions--sticky` (삭제) — Task 2에서 구분을 명시했다.
- `--measure` — Task 4 Step 1에서 정의하고 Step 3에서 소비한다. 순서가 맞다.
- 테스트 수: 464 → 465 (T1) → 466 (T2) → 467 (T3) → 467 (T4, CSS는 테스트 없음) → 467 (T5). 단조롭게 이어진다.
