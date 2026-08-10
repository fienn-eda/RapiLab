# 안내 문구 중앙화 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 앱 곳곳에 흩어진 설명·안내 문구 47개를 `frontend/src/lib/helpText.ts`의 `HELP` 객체로 모아, 문구 수정이 그 파일 한 곳에서 끝나게 한다.

**Architecture:** 순수 이동이다 — 화면에 보이는 글자는 한 글자도 바뀌지 않는다. 값이 끼는 문구는 템플릿 리터럴을 반환하는 함수가 되고, 어느 문장을 쓸지 고르는 분기는 컴포넌트에 남는다. 문구를 하드코딩하던 테스트도 `HELP`를 참조하게 바꿔, 옮긴 글자가 원본과 같은지를 테스트가 증명하게 만든다.

**Tech Stack:** React 19 + TypeScript + Vite, Vitest + @testing-library/react.

**설계문서:** `docs/superpowers/specs/2026-08-10-help-text-centralization-design.md`

## Global Constraints

- **글자를 바꾸지 않는다.** 이 계획의 모든 문자열은 최종 형태로 적혀 있다. 옮길 때 다시 타이핑하지 말고 이 계획에서 복사한다.
- **JSX 여러 줄 텍스트는 줄바꿈이 공백 하나로 접힌 뒤 렌더된다.** 이 계획의 문자열은 이미 접힌 형태다. 원본 JSX와 대조할 때 줄바꿈 위치 차이는 정상이고, 공백 개수 차이는 결함이다.
- **끝 공백이 있는 문자열이 셋 있다** (`draft.seatHintWithDeckPick`, `draft.seatHintSingleDeck`, `recommend.poolUnsupported`의 앞 공백). 지우면 단어가 붙는다.
- **작업 브랜치:** `wip/help-text-centralization` (이미 생성됨, 설계문서 커밋 `f1d4ba51` 위).
- **명령은 `frontend/`에서 돈다.** 테스트 `npm test`, 타입 `npx tsc -b --noEmit`.
- **`npm test`는 타입을 보지 않는다.** 두 명령을 따로 돌린다.
- `HELP` 객체는 `as const`를 유지한다. 함수 프로퍼티가 섞여도 문제없다.
- 새로 추가하는 그룹은 기존 그룹 사이 알파벳 순이 아니라 **화면 흐름 순**으로 넣는다: `app` → `boss` → `charge` → `miranda` → `recommend` → `recommendMode` → `draft` → `results` → `savedRuns` → `roster` → `profile` → `sync` → `syncHelp` → `attribution` → `privacy`.

## 이 계획의 TDD 사이클

문구를 옮기는 작업이라 「새 기능의 실패하는 테스트」가 없다. 대신 **기존 테스트를 먼저 `HELP` 참조로 바꾸는 것**이 red를 만든다:

1. 테스트를 `HELP.x` 참조로 바꾼다 → `HELP.x`가 없으므로 **실패**(`undefined`가 matcher로 넘어간다)
2. `helpText.ts`에 `x`를 추가한다 → **통과**. 컴포넌트는 아직 리터럴이지만 글자가 같으니 붙는다.
   **이 통과가 이 리팩토링의 핵심 검증이다** — 옮겨 적은 글자가 화면의 글자와 정확히 같음을 증명한다.
3. 컴포넌트를 `HELP.x` 참조로 바꾼다 → 여전히 통과
4. `npx tsc -b --noEmit` → 0
5. 커밋

### 어떤 assertion을 바꾸고 어떤 것을 두는가

문구를 하드코딩한 assertion은 **11개 파일에 39군데** 있고, 그중 **29군데를 참조로 바꾸고 10군데는 정규식을 유지**한다. 유지하는 두 종류:

- **문장 일부만 재는 자리** — `/9.90% 밑으로 내려가면/`처럼 값 하나를 확인한다. 정확 문자열로 바꾸려면 나머지 인자를 픽스처에서 계산해야 하는데, 그 assertion이 재는 것은 값이지 문장이 아니다.
- **문구가 함수인데 「없음」을 재는 자리** — 함수에 아무 인자나 넣어 만든 정확 문자열로 부재를 재면, 문구가 바뀌어도 그 특정 조합이 없다는 이유로 초록이 된다.

문구가 **상수**일 때는 존재/부재 쌍을 함께 바꾼다 — 그래야 문구가 바뀔 때 두 줄이 같이 따라간다.

테스트가 없는 문구는 2단계 검증을 못 받는다. 그 대신 각 태스크 끝에서 커밋 diff의 한글을 대조한다:

```bash
git diff HEAD~1 -U0 -- frontend/src | grep -E '^[-+].*[가-힣]'
```

지운 줄의 글자와 넣은 줄의 글자가 같은지 눈으로 본다. 다르면 그 자리가 결함이다.

## File Structure

| 파일 | 책임 | 이 계획에서 |
|---|---|---|
| `frontend/src/lib/helpText.ts` | 화면 설명 문구 전부 | 47항목 추가, 헤더 주석 갱신 |
| `frontend/src/components/HelpText.tsx` | `**굵게**`를 그리는 인라인 렌더러 | 변경 없음 |
| 컴포넌트 20개 | 문구를 `HELP` 참조로 | 문자열 리터럴 → 참조 |
| `frontend/src/lib/rosterImport.ts` | 로스터 파싱 + 경고 생성 | 경고 문구 2개 참조로 |
| `frontend/src/hooks/useBookmarkletImport.ts` | 북마크릿 수신 | 거절 안내 1개 참조로 |
| 테스트 8개 | | 하드코딩 문구 → `HELP` 참조 |

---

### Task 1: 파일 헤더 규칙을 고쳐 쓰고 `app` 그룹을 옮긴다

가장 단순한 그룹으로 패턴을 확립한다. 헤더 주석의 경계 서술이 지금은 「진행·결과·에러 메시지는 오지 않는다」인데, 이 작업이 진행 안내와 빈 상태를 가져오므로 그 문장이 틀린 말이 된다.

**Files:**
- Modify: `frontend/src/lib/helpText.ts:1-11` (헤더), `:29` (`HELP` 객체 시작)
- Modify: `frontend/src/App.tsx:146-152`, `:169-173`
- Test: `frontend/src/App.test.tsx:70`

**Interfaces:**
- Produces: `HELP.app.subtitle`, `HELP.app.cubeAssumption`, `HELP.app.noProfiles` — 전부 `string`

- [ ] **Step 1: 테스트를 HELP 참조로 바꾼다**

`frontend/src/App.test.tsx` 맨 위 import에 추가(이미 다른 import들이 있는 자리):

```ts
import { HELP } from './lib/helpText'
```

70행을 바꾼다:

```ts
// 지금
expect(screen.getByText(/덱 추천은 .*재장전 큐브 15레벨/i)).toBeInTheDocument()
// 바꾼 뒤
expect(screen.getByText(HELP.app.cubeAssumption)).toBeInTheDocument()
```

- [ ] **Step 2: 테스트를 돌려 실패를 확인한다**

Run: `cd frontend && npx vitest run src/App.test.tsx -t "재장전 큐브"`

Expected: FAIL. `HELP.app`이 `undefined`라 `HELP.app.cubeAssumption` 접근에서 TypeError가 난다.

(테스트 이름이 안 맞으면 `-t` 없이 `npx vitest run src/App.test.tsx`로 돌리고 해당 케이스가 빨간지 본다.)

- [ ] **Step 3: helpText.ts 헤더 주석을 고쳐 쓴다**

`frontend/src/lib/helpText.ts`의 1-11행을 통째로 아래로 바꾼다:

```ts
// 화면에 나오는 안내 문구를 한곳에 모은다. 컴포넌트마다 흩어 두면 문구 한 줄을
// 고치려고 그 컴포넌트를 찾아 읽어야 하는데, 문구는 코드를 몰라도 고칠 수 있는
// 것이어야 한다.
//
// 여기 오는 것은 **읽고 이해하는 문장**이다. 안내·해설·빈 상태·진행 중 안내·
// 확인 문구가 모두 그렇다. 오지 않는 것은 **조작 대상의 이름**이다 - 라벨, 버튼,
// 셀렉트 옵션, 단위 표시("초", "%"). 그리고 실패 보고(에러·검증 메시지)도 오지
// 않는다. 경계는 「문장이냐 이름이냐」이지 상태냐 아니냐가 아니다.
//
// `**...**`로 감싼 부분은 굵게 나온다(components/HelpText.tsx). 지원하는 표기는
// 그것 하나뿐이다 - 필요한 것이 강조뿐이고, 여기 있는 것은 유저 입력이 아니라
// 우리가 쓴 상수라 임의 HTML을 다룰 위험이 없다. `평문 전용`이라 적힌 항목은
// 문자열만 받는 자리(title 속성, window.confirm, 에러 상태)로 가므로 별표가
// 글자 그대로 보인다.
//
// 값이 끼는 문구는 함수다. 자리표시자 문자열을 쓰지 않는 이유는 조용히 틀리기
// 때문이다 - 이름을 오타 내도 컴파일러가 말이 없고 화면에 자리표시자가 박힌다.
// 포맷 헬퍼(percent, formatDamage)를 통과한 값은 문자열로 받고, 그 밖의 값은
// 숫자로 받아 자릿수와 단위를 문구가 붙인다.
```

- [ ] **Step 4: `app` 그룹을 추가한다**

`export const HELP = {` 바로 다음 줄에 `boss:`보다 **앞에** 넣는다:

```ts
  app: {
    subtitle: 'blablalink에서 로스터를 동기화하면 엔진이 덱을 구성해줘요.',
    cubeAssumption:
      '덱 추천은 모든 니케가 재장전 큐브 15레벨을 착용한 것으로 계산합니다. 계산기 탭에서는 큐브를 직접 고릅니다.',
    noProfiles: '아직 동기화된 계정이 없어요. 위에서 blablalink 동기화를 시작해보세요.',
  },

```

- [ ] **Step 5: 테스트를 돌려 통과를 확인한다**

Run: `cd frontend && npx vitest run src/App.test.tsx`

Expected: PASS. **여기서 통과한다는 것은 옮겨 적은 글자가 App.tsx의 글자와 정확히 같다는 뜻이다.** 실패하면 옮긴 문자열의 공백이나 글자가 다르다 — 계획의 문자열과 App.tsx 원본을 대조한다.

- [ ] **Step 6: App.tsx를 HELP 참조로 바꾼다**

import 추가(다른 `./lib/...` import 옆):

```ts
import { HELP } from './lib/helpText'
import { HelpText } from './components/HelpText'
```

(`HelpText`가 이미 import돼 있으면 중복해 넣지 않는다.)

146-152행:

```tsx
          <p className="app__subtitle">
            <HelpText>{HELP.app.subtitle}</HelpText>
          </p>
          <p className="app__note">
            <HelpText>{HELP.app.cubeAssumption}</HelpText>
          </p>
```

169-173행:

```tsx
          <div className="empty">
            <p className="empty__text">
              <HelpText>{HELP.app.noProfiles}</HelpText>
            </p>
          </div>
```

- [ ] **Step 7: 테스트와 타입을 확인한다**

Run: `cd frontend && npx vitest run src/App.test.tsx && npx tsc -b --noEmit`

Expected: 테스트 PASS, tsc 출력 없음(에러 0).

- [ ] **Step 8: 커밋하고 diff의 글자를 대조한다**

```bash
git add frontend/src/lib/helpText.ts frontend/src/App.tsx frontend/src/App.test.tsx
git commit -m "앱 머리말 안내를 helpText.ts로 옮기고 파일의 경계 규칙을 고쳐 쓴다"
git diff HEAD~1 -U0 -- frontend/src | grep -E '^[-+].*[가-힣]'
```

지운 줄 셋의 글자와 넣은 줄 셋의 글자가 같은지 본다.

---

### Task 2: `results` 그룹 — 결과 화면 해설 9개

결과 화면 다섯 곳에 흩어진 해설과 빈 상태다. 「벤치」 문구가 두 컴포넌트에 똑같이 박혀 있어 여기서 합쳐진다.

**Files:**
- Modify: `frontend/src/lib/helpText.ts` (`recommendMode` 다음, `sync` 앞에 `results` 그룹 추가)
- Create: `frontend/src/components/BenchNote.tsx`
- Modify: `frontend/src/components/DeckResults.tsx:18`
- Modify: `frontend/src/components/RaidResults.tsx:38`, `:46-49`, `:64-67`
- Modify: `frontend/src/components/DraftResults.tsx:197-201`
- Modify: `frontend/src/components/EvaluationResults.tsx:51-54`
- Modify: `frontend/src/components/SwapConvergenceNote.tsx:13-17`
- Modify: `frontend/src/components/DeckCard.tsx:85`, `:96-102`
- Modify: `frontend/src/components/ExcludedSlugsNote.tsx:14-18`
- Test: `DeckResults.test.tsx:9`, `:53`; `RaidResults.test.tsx:9`, `:50`, `:64`; `DraftResults.test.tsx:79`; `RecommendPanel.test.tsx:471`, `:851`, `:971`, `:1034` (전부 `frontend/src/components/` 아래)

**Interfaces:**
- Consumes: 없음 (Task 1과 독립)
- Produces:
  - `HELP.results.emptyDecks: string`
  - `HELP.results.emptyRaid: string`
  - `HELP.results.raidSplit: (deckCount: number) => string`
  - `HELP.results.bench: (names: string) => string`
  - `HELP.results.seatOrder: string`
  - `HELP.results.swapCutoff: string`
  - `HELP.results.holdBurst: (names: string) => string`
  - `HELP.results.pinTitle: string` (평문 전용)
  - `HELP.results.excludedUnsupported: (names: string) => string`

- [ ] **Step 1: assertion 열 곳을 HELP 참조로 바꾼다**

각 파일 상단에 `import { HELP } from '../lib/helpText'`를 추가한다.

```ts
// DeckResults.test.tsx:9
expect(screen.getByText(HELP.results.emptyDecks)).toBeInTheDocument()

// DeckResults.test.tsx:53
screen.getByText(HELP.results.excludedUnsupported('Some Slug, Other Slug')),

// RaidResults.test.tsx:9
expect(screen.getByText(HELP.results.emptyRaid)).toBeInTheDocument()

// RaidResults.test.tsx:50
expect(screen.getByText(HELP.results.bench('F, G'))).toBeInTheDocument()

// RaidResults.test.tsx:64
screen.getByText(HELP.results.excludedUnsupported('Some Slug')),

// DraftResults.test.tsx:79
expect(screen.getByText(HELP.results.bench('Bench Unit'))).toBeInTheDocument()

// RecommendPanel.test.tsx:471 과 :1034 (두 곳 같은 형태)
expect(screen.getByText(HELP.results.bench('K'))).toBeInTheDocument()

// RecommendPanel.test.tsx:851 과 :971 (두 곳 같은 형태)
expect(await screen.findByText(HELP.results.raidSplit(1))).toBeInTheDocument()
```

**`RecommendPanel.test.tsx:854`는 바꾸지 않는다** — `queryByText(/모두 함께 편성/)`로 「없음」을 재는데 `raidSplit`이 함수라, 아무 덱 수나 넣어 만든 정확 문자열로 부재를 재면 문구가 바뀌어도 초록이 된다.

- [ ] **Step 2: 테스트를 돌려 실패를 확인한다**

Run: `cd frontend && npx vitest run src/components/DeckResults.test.tsx src/components/RaidResults.test.tsx src/components/DraftResults.test.tsx`

Expected: FAIL. `HELP.results`가 `undefined`.

- [ ] **Step 3: `results` 그룹을 추가한다**

`recommendMode` 그룹 다음에 넣는다:

```ts
  results: {
    emptyDecks: '아직 추천된 덱이 없어요.',
    emptyRaid: '아직 배분된 레이드 덱이 없어요.',
    raidSplit: (deckCount: number) =>
      `이 ${deckCount}개 덱을 모두 함께 편성하세요 — 각 니케는 정확히 하나의 덱에만 배정돼요. 이것은 순위별 대안이 아니라 하나의 분할이에요.`,
    bench: (names: string) => `벤치 (덱에 배정되지 않음): ${names}`,
    seatOrder:
      '자리 순서는 엔진이 기대 딜량이 가장 높게 나오도록 고른 거예요. 인게임에서도 이 순서로 배치해요.',
    swapCutoff: '탐색이 상한에 걸려 끝까지 가지 못했어요. 더 나은 배분이 남아 있을 수 있어요.',
    holdBurst: (names: string) =>
      `${names}는 첫 풀버스트에 버스트를 아껴주세요 — 그래야 이 수치대로 나와요.`,
    /** 평문 전용 - title 속성이라 별표가 글자 그대로 나온다. */
    pinTitle: '고정해서 여기 유지돼요',
    excludedUnsupported: (names: string) => `아직 미지원 (탐색에서 제외됨): ${names}`,
  },

```

- [ ] **Step 4: 테스트를 돌려 통과를 확인한다**

Run: `cd frontend && npx vitest run src/components/DeckResults.test.tsx src/components/RaidResults.test.tsx src/components/DraftResults.test.tsx src/components/RecommendPanel.test.tsx`

Expected: PASS. 옮긴 글자가 컴포넌트의 글자와 같다는 증명이다.

- [ ] **Step 5: 컴포넌트 일곱을 참조로 바꾼다**

각 파일에 `import { HELP } from '../lib/helpText'`와 `import { HelpText } from './HelpText'`를 추가한다(이미 있으면 그대로).

`DeckResults.tsx:18`:

```tsx
        <p className="empty__text"><HelpText>{HELP.results.emptyDecks}</HelpText></p>
```

`RaidResults.tsx:38`:

```tsx
        <p className="empty__text"><HelpText>{HELP.results.emptyRaid}</HelpText></p>
```

`RaidResults.tsx:46-49`:

```tsx
      <p className="raid-results__note">
        <HelpText>{HELP.results.raidSplit(decks.length)}</HelpText>
      </p>
```

**벤치 줄은 컴포넌트로 뽑는다.** 두 결과 화면이 같은 줄을 그리고 있어, 문구만 합치면 렌더 블록이 그대로 두 벌 남는다. 이 저장소에는 같은 문제에서 나온 컴포넌트가 이미 둘 있다 — `ExcludedSlugsNote`와 `SwapConvergenceNote`. 벤치도 그 자리다.

새 파일 `frontend/src/components/BenchNote.tsx`:

```tsx
// The bench line shared by both raid-result views (RaidResults and
// DraftResults): units the allocation left out of every deck.

import { HELP } from '../lib/helpText'
import { HelpText } from './HelpText'

interface BenchNoteProps {
  leftoverSlugs: string[]
  nameFor: (slug: string) => string
}

export function BenchNote({ leftoverSlugs, nameFor }: BenchNoteProps) {
  if (leftoverSlugs.length === 0) return null
  return (
    <p className="raid-results__leftover">
      <HelpText>{HELP.results.bench(leftoverSlugs.map(nameFor).join(', '))}</HelpText>
    </p>
  )
}
```

`RaidResults.tsx:64-67`과 `DraftResults.tsx:197-201` — 둘 다 같은 한 줄로 바뀐다. 두 파일 모두 `const nameFor = lookups.nameFor ?? nameFromSlug`를 이미 지역변수로 갖고 있으므로 그것을 넘긴다:

```tsx
      <BenchNote leftoverSlugs={leftoverSlugs} nameFor={nameFor} />
```

각 파일에 `import { BenchNote } from './BenchNote'`를 추가한다. `leftoverSlugs.length > 0` 가드는 `BenchNote` 안으로 들어갔으므로 호출부에서 지운다.

`EvaluationResults.tsx:51-54`:

```tsx
      <p className="evaluation-results__ordering-note">
        <HelpText>{HELP.results.seatOrder}</HelpText>
      </p>
```

`SwapConvergenceNote.tsx:13-17`:

```tsx
  return (
    <p className="raid-results__note" role="status">
      <HelpText>{HELP.results.swapCutoff}</HelpText>
    </p>
  )
```

`DeckCard.tsx:85` — title 속성이라 `HelpText`를 쓰지 않는다:

```tsx
                  <span className="deck-results__pin" title={HELP.results.pinTitle}>
```

`DeckCard.tsx:96-102`:

```tsx
      {deck.hold_burst_slugs.length > 0 && (
        <p className="deck-results__hold">
          <span aria-hidden="true">⏳</span>{' '}
          <HelpText>{HELP.results.holdBurst(deck.hold_burst_slugs.map(nameFor).join(', '))}</HelpText>
        </p>
      )}
```

`ExcludedSlugsNote.tsx:14-18`:

```tsx
  return (
    <p className="deck-results__excluded">
      <HelpText>{HELP.results.excludedUnsupported(excludedSlugs.map(nameFromSlug).join(', '))}</HelpText>
    </p>
  )
```

- [ ] **Step 6: 테스트와 타입을 확인한다**

Run: `cd frontend && npm test && npx tsc -b --noEmit`

Expected: 719 통과, tsc 에러 0.

- [ ] **Step 7: 커밋하고 diff의 글자를 대조한다**

```bash
git add frontend/src
git commit -m "결과 화면 해설을 helpText.ts로 옮긴다 - 벤치 문구의 두 벌이 하나가 된다"
git diff HEAD~1 -U0 -- frontend/src | grep -E '^[-+].*[가-힣]'
```

---

### Task 3: `savedRuns` + `profile` — 보관 목록과 계정 삭제 5개

`window.confirm()`으로 가는 문구 둘이 여기 있다. 저장 결과 힌트가 두 패널에 똑같이 박혀 있어 여기서 합쳐진다.

**Files:**
- Modify: `frontend/src/lib/helpText.ts` (`results` 다음에 `savedRuns`, 그 다음 `roster`는 Task 7, `profile`은 여기서)
- Modify: `frontend/src/components/SavedRunList.tsx:39-41`, `:82`
- Modify: `frontend/src/components/SaveRunButton.tsx:62-66`
- Modify: `frontend/src/components/ProfileSwitcher.tsx:57`
- Modify: `frontend/src/components/RecommendPanel.tsx:921-923`
- Modify: `frontend/src/components/UnionRaidPanel.tsx:325-327`
- Test: `frontend/src/components/SavedRunList.test.tsx:52`

**Interfaces:**
- Produces:
  - `HELP.savedRuns.restoreHint: string`
  - `HELP.savedRuns.empty: string`
  - `HELP.savedRuns.confirmDelete: (name: string) => string` (평문 전용)
  - `HELP.savedRuns.capReached: (cap: number) => string`
  - `HELP.profile.confirmDelete: (label: string) => string` (평문 전용)

- [ ] **Step 1: 테스트를 HELP 참조로 바꾼다**

`SavedRunList.test.tsx` 상단에 `import { HELP } from '../lib/helpText'` 추가, 52행:

```ts
expect(screen.getByText(HELP.savedRuns.empty)).toBeInTheDocument()
```

- [ ] **Step 2: 테스트를 돌려 실패를 확인한다**

Run: `cd frontend && npx vitest run src/components/SavedRunList.test.tsx`

Expected: FAIL. `HELP.savedRuns`가 `undefined`.

- [ ] **Step 3: `savedRuns`와 `profile` 그룹을 추가한다**

`results` 다음에:

```ts
  savedRuns: {
    restoreHint: '이름을 눌러 그때의 결과를 다시 볼 수 있어요',
    empty: '저장한 결과가 없어요.',
    /** 평문 전용 - window.confirm이라 별표가 글자 그대로 나온다. */
    confirmDelete: (name: string) => `"${name}"을(를) 삭제할까요?`,
    capReached: (cap: number) =>
      `보관은 ${cap}개까지예요. 목록에서 몇 개를 지우고 다시 저장해주세요.`,
  },

  profile: {
    /** 평문 전용 - window.confirm이라 별표가 글자 그대로 나온다. */
    confirmDelete: (label: string) =>
      `"${label}" 프로필을 삭제할까요? 동기화된 로스터와 캐시된 결과가 함께 삭제돼요.`,
  },

```

- [ ] **Step 4: 테스트를 돌려 통과를 확인한다**

Run: `cd frontend && npx vitest run src/components/SavedRunList.test.tsx`

Expected: PASS.

- [ ] **Step 5: 컴포넌트 다섯을 참조로 바꾼다**

`SavedRunList.tsx` — import 추가 후 39-41행:

```tsx
  if (runs.length === 0) {
    return <p className="empty__text"><HelpText>{HELP.savedRuns.empty}</HelpText></p>
  }
```

82행(confirm이라 `HelpText` 없음):

```tsx
                    if (window.confirm(HELP.savedRuns.confirmDelete(run.name))) onDelete(run.id)
```

`SaveRunButton.tsx:62-66`:

```tsx
      {refused && (
        <span className="field__error" role="alert">
          <HelpText>{HELP.savedRuns.capReached(SAVED_RUNS_CAP)}</HelpText>
        </span>
      )}
```

`ProfileSwitcher.tsx:57`:

```tsx
    if (window.confirm(HELP.profile.confirmDelete(activeLabel))) {
```

`RecommendPanel.tsx:921-923`:

```tsx
            <summary className="group__hint">
              <HelpText>{HELP.savedRuns.restoreHint}</HelpText>
            </summary>
```

`UnionRaidPanel.tsx:325-327` — 같은 문구다:

```tsx
            <summary className="group__hint">
              <HelpText>{HELP.savedRuns.restoreHint}</HelpText>
            </summary>
```

- [ ] **Step 6: 테스트와 타입을 확인한다**

Run: `cd frontend && npm test && npx tsc -b --noEmit`

Expected: 719 통과, tsc 에러 0.

- [ ] **Step 7: 커밋하고 diff의 글자를 대조한다**

```bash
git add frontend/src
git commit -m "보관 목록과 계정 삭제 안내를 helpText.ts로 옮긴다 - 저장 결과 힌트의 두 벌이 하나가 된다"
git diff HEAD~1 -U0 -- frontend/src | grep -E '^[-+].*[가-힣]'
```

---

### Task 4: `recommend` + `draft` — 탐색 안내와 배치 힌트 9개

진행 중 안내와 배치 힌트가 여기 있다. 「기대 딜량 계산 중」이 두 패널에 똑같이 박혀 있어 합쳐진다. 배치 힌트는 **분기가 컴포넌트에 남는** 첫 사례다.

**Files:**
- Modify: `frontend/src/lib/helpText.ts` (`charge` 다음에 `recommend`, `recommendMode` 다음에 `draft`)
- Modify: `frontend/src/components/RecommendPanel.tsx:695-698`, `:805-822`, `:943-950`
- Modify: `frontend/src/components/UnionRaidPanel.tsx:242-245`
- Modify: `frontend/src/components/DraftEditor.tsx:236-242`
- Modify: `frontend/src/components/DraftResults.tsx:131-134`
- Test: `frontend/src/App.test.tsx:374`, `:476`, `:482`; `frontend/src/components/RecommendPanel.test.tsx:109`, `:485`, `:742`, `:958`, `:1269`, `:1324`, `:1400`

**Interfaces:**
- Produces:
  - `HELP.recommend.minRoster: (minimum: number) => string`
  - `HELP.recommend.searchRunning: (modeLabel: string) => string`
  - `HELP.recommend.evaluateRunning: string`
  - `HELP.recommend.poolNote: (included: number, total: number) => string`
  - `HELP.recommend.poolUnsupported: (count: number) => string` — **앞 공백으로 시작한다**
  - `HELP.draft.seatHintWithDeckPick: string` — **끝 공백으로 끝난다**
  - `HELP.draft.seatHintSingleDeck: string` — **끝 공백으로 끝난다**
  - `HELP.draft.seatHintCommon: string`
  - `HELP.draft.tiersIntro: string`

- [ ] **Step 1: assertion 다섯 곳을 HELP 참조로 바꾼다**

`App.test.tsx:374`, `:476`, `:482`와 `RecommendPanel.test.tsx:485` — **네 곳 모두 「전부 최적화」 라디오를 클릭한 뒤의 검사임을 확인했다.** 인자는 전부 `'전부 최적화 중'`이다:

```ts
expect(await screen.findByRole('status')).toHaveTextContent(
  HELP.recommend.searchRunning('전부 최적화 중'),
)
```

(`App.test.tsx:482`만 `findByRole`이 아니라 `getByRole`이다 — 그 형태는 그대로 두고 matcher만 바꾼다.)

`RecommendPanel.test.tsx:109` — `MIN_DECK_ROSTER_SIZE`는 그 파일 21행에 이미 import돼 있다:

```ts
screen.getByText(HELP.recommend.minRoster(MIN_DECK_ROSTER_SIZE)),
```

**바꾸지 않는 것 넷:**

- `RecommendPanel.test.tsx:742` — 「없음」을 재는데 `minRoster`가 함수다.
- `RecommendPanel.test.tsx:958`, `:1269`, `:1324`, `:1400` — `poolNote` 뒤에 미지원 꼬리가 붙을 수 있어 `<p>`의 텍스트가 문구보다 길다. 이 넷은 「탐색 풀 안내가 떴다」는 스모크이므로 `/탐색 풀에 포함됨/`을 유지한다.

- [ ] **Step 2: 테스트를 돌려 실패를 확인한다**

Run: `cd frontend && npx vitest run src/App.test.tsx src/components/RecommendPanel.test.tsx`

Expected: FAIL. `HELP.recommend`가 `undefined`.

- [ ] **Step 3: `recommend`와 `draft` 그룹을 추가한다**

`charge` 그룹 다음에:

```ts
  recommend: {
    minRoster: (minimum: number) => `덱을 추천하려면 준비된 니케가 최소 ${minimum}기 필요해요.`,
    searchRunning: (modeLabel: string) =>
      `${modeLabel} — 수천 번의 시뮬레이션을 실행하며 보통 2~5분이 걸려요. 아직 진행 중이니 완료되면 버튼이 다시 활성화돼요.`,
    evaluateRunning: '기대 딜량 계산 중이에요 — 몇 초면 끝나요.',
    poolNote: (included: number, total: number) =>
      `${included}/${total} 탐색 풀에 포함됨 — 편성하지 않을 유닛은 니케 풀 탭에서 정해요`,
    /** 앞 공백이 있다 - 위 문장 뒤에 이어 붙는 꼬리다. */
    poolUnsupported: (count: number) => ` (보유 중이나 아직 미지원 ${count}기)`,
  },

```

`recommendMode` 그룹 다음에:

```ts
  draft: {
    /** 끝 공백이 있다 - seatHintCommon이 뒤에 이어 붙는다. */
    seatHintWithDeckPick:
      '팔레트의 니케를 누르면 활성 덱(밝은 테두리)에 앉아요. 덱 이름을 누르면 활성 덱이 바뀌어요. ',
    /** 끝 공백이 있다 - seatHintCommon이 뒤에 이어 붙는다. */
    seatHintSingleDeck: '팔레트의 니케를 누르면 자리에 앉아요. ',
    seatHintCommon:
      '덱에 앉은 니케를 누르면 편성에서 빠져요. 슬롯은 소속만 나타내며, 버스트 순서는 엔진이 정해요.',
    tiersIntro:
      '세 단계로 올라가요: 제출한 드래프트, 드래프트한 유닛만으로 만든 최선의 배분, 벤치까지 포함한 추천.',
  },

```

- [ ] **Step 4: 테스트를 돌려 통과를 확인한다**

Run: `cd frontend && npx vitest run src/App.test.tsx src/components/RecommendPanel.test.tsx`

Expected: PASS.

- [ ] **Step 5: 컴포넌트 넷을 참조로 바꾼다**

`RecommendPanel.tsx:695-698`:

```tsx
      {mode !== 'evaluate' && rosterTooSmall && (
        <p className="field__error" role="alert">
          <HelpText>{HELP.recommend.minRoster(MIN_DECK_ROSTER_SIZE)}</HelpText>
        </p>
      )}
```

`RecommendPanel.tsx:805-822` — 805-813행의 주석 블록은 **그대로 둔다**(실측 근거라 문구가 아니라 코드 설명이다). 814-816행만 바꾼다:

```tsx
            <HelpText>
              {HELP.recommend.searchRunning(
                mode === 'raid' ? '전부 최적화 중' : '빈자리만 최적화 중',
              )}
            </HelpText>
```

821행:

```tsx
            <HelpText>{HELP.recommend.evaluateRunning}</HelpText>
```

`RecommendPanel.tsx:943-950`:

```tsx
            <p className="group__hint">
              <HelpText>
                {HELP.recommend.poolNote(
                  poolKnown ? poolIncluded : effectiveRoster.length,
                  poolKnown ? poolTotal : roster.length,
                )}
              </HelpText>
              {poolKnown && unsupportedCount > 0 && (
                <HelpText>{HELP.recommend.poolUnsupported(unsupportedCount)}</HelpText>
              )}
            </p>
```

`UnionRaidPanel.tsx:242-245`:

```tsx
        {evaluation.status === 'loading' && (
          <p className="recommend-form__progress" role="status">
            <HelpText>{HELP.recommend.evaluateRunning}</HelpText>
          </p>
        )}
```

`DraftEditor.tsx:236-242` — **분기는 여기 남는다**:

```tsx
      <p className="draft-editor__hint">
        <HelpText>
          {(picksDeck ? HELP.draft.seatHintWithDeckPick : HELP.draft.seatHintSingleDeck) +
            HELP.draft.seatHintCommon}
        </HelpText>
      </p>
```

`DraftResults.tsx:131-134`:

```tsx
      <p className="raid-results__note">
        <HelpText>{HELP.draft.tiersIntro}</HelpText>
      </p>
```

- [ ] **Step 6: 테스트와 타입을 확인한다**

Run: `cd frontend && npm test && npx tsc -b --noEmit`

Expected: 719 통과, tsc 에러 0.

- [ ] **Step 7: 커밋하고 diff의 글자를 대조한다**

```bash
git add frontend/src
git commit -m "탐색 진행 안내와 배치 힌트를 helpText.ts로 옮긴다 - 기대 딜량 안내의 두 벌이 하나가 된다"
git diff HEAD~1 -U0 -- frontend/src | grep -E '^[-+].*[가-힣]'
```

---

### Task 5: `miranda` — 미란다 계산기 해설 9개

임계값 해설 넷은 **어느 문장을 쓸지가 로직**인 대표 사례다. 문장만 옮기고 `describeThreshold`의 분기는 그대로 둔다.

**Files:**
- Modify: `frontend/src/lib/helpText.ts` (`charge` 다음, `recommend` 앞에 `miranda`)
- Modify: `frontend/src/components/MirandaCalculatorPanel.tsx:62-67`, `:92-95`, `:125-129`
- Modify: `frontend/src/components/MirandaTargets.tsx:49-66`, `:112-121`
- Test: `frontend/src/components/MirandaCalculatorPanel.test.tsx:114`; `frontend/src/components/MirandaTargets.test.tsx:72`, `:110`, `:125`

**Interfaces:**
- Produces:
  - `HELP.miranda.notInRoster: string`
  - `HELP.miranda.intro: string`
  - `HELP.miranda.running: string`
  - `HELP.miranda.gainCapped: (cap: string) => string`
  - `HELP.miranda.gainAt: (current: string, threshold: string, gapPoints: number) => string`
  - `HELP.miranda.keepAlways: string`
  - `HELP.miranda.keepAbove: (threshold: string, current: string, slackPoints: number) => string`
  - `HELP.miranda.targetsChange: (cycles: string) => string`
  - `HELP.miranda.burstsFewer: (total: number, bursts: number) => string`

- [ ] **Step 1: assertion 넷을 HELP 참조로 바꾼다**

두 테스트 파일 상단에 `import { HELP } from '../lib/helpText'` 추가.

```ts
// MirandaCalculatorPanel.test.tsx:114
expect(screen.getByText(HELP.miranda.notInRoster)).toBeInTheDocument()

// MirandaTargets.test.tsx:72 — ⚠ 가 문구에 포함돼 있어 <p> 전체와 정확히 맞는다
expect(screen.getByText(HELP.miranda.targetsChange('2'))).toBeInTheDocument()

// MirandaTargets.test.tsx:110
expect(screen.getByText(HELP.miranda.burstsFewer(2, 1))).toBeInTheDocument()

// MirandaTargets.test.tsx:125
expect(within(row('신데렐라')).getByText(HELP.miranda.keepAlways)).toBeInTheDocument()
```

**바꾸지 않는 것 넷:**

- `MirandaTargets.test.tsx:86`, `:99` — 「없음」을 재는데 `targetsChange`가 함수다.
- `MirandaTargets.test.tsx:123`, `:124` — 문장 일부(값)만 재는 정규식이다. 정확 문자열로 바꾸려면 나머지 인자를 픽스처에서 계산해야 하는데, 이 둘이 재는 것은 임계값 숫자이지 문장이 아니다.

- [ ] **Step 2: 테스트를 돌려 실패를 확인한다**

Run: `cd frontend && npx vitest run src/components/MirandaTargets.test.tsx src/components/MirandaCalculatorPanel.test.tsx`

Expected: FAIL. `HELP.miranda`가 `undefined`.

- [ ] **Step 3: `miranda` 그룹을 추가한다**

`charge` 그룹 다음, `recommend` 앞에:

```ts
  miranda: {
    notInRoster: '미란다가 로스터에 없어요. 동기화 탭에서 로스터를 다시 가져와 주세요.',
    intro:
      '미란다는 이미 앉아 있어요. 남은 네 자리를 채우면 파워업!과 웨이크업! 3번불릿을 누가 받는지 알려줘요.',
    running: '시뮬레이션을 돌리는 중이에요 — 몇 초 걸려요.',
    gainCapped: (cap: string) => `오버로드 공격력을 상한(${cap})까지 올려도 매 사이클 받지는 못해요`,
    gainAt: (current: string, threshold: string, gapPoints: number) =>
      `오버로드 공격력 ${current} → ${threshold}면 매 사이클 받아요 (+${gapPoints.toFixed(2)}%p)`,
    keepAlways: '오버로드 공격력이 없어도 매 사이클 유지돼요',
    keepAbove: (threshold: string, current: string, slackPoints: number) =>
      `오버로드 공격력이 ${threshold} 밑으로 내려가면 매 사이클은 못 받아요 (지금 ${current}, 여유 ${slackPoints.toFixed(2)}%p)`,
    targetsChange: (cycles: string) => `⚠ ${cycles}사이클에는 파워업!을 받는 니케가 달라요`,
    burstsFewer: (total: number, bursts: number) =>
      `⚠ 미란다는 ${total}사이클 중 ${bursts}번만 버스트해요 (같은 1티어에 니케가 둘이에요)`,
  },

```

- [ ] **Step 4: 테스트를 돌려 통과를 확인한다**

Run: `cd frontend && npx vitest run src/components/MirandaTargets.test.tsx src/components/MirandaCalculatorPanel.test.tsx`

Expected: PASS.

- [ ] **Step 5: 두 컴포넌트를 참조로 바꾼다**

`MirandaCalculatorPanel.tsx:62-67`:

```tsx
      <section className="card" aria-label="미란다 계산기">
        <p className="empty__text">
          <HelpText>{HELP.miranda.notInRoster}</HelpText>
        </p>
      </section>
```

`:92-95`:

```tsx
      <p className="group__hint">
        <HelpText>{HELP.miranda.intro}</HelpText>
      </p>
```

`:125-129`:

```tsx
          {busy && (
            <p className="recommend-form__progress" role="status">
              <HelpText>{HELP.miranda.running}</HelpText>
            </p>
          )}
```

`MirandaTargets.tsx:49-66` — **주석(46-48행, 59-60행)은 그대로 두고** 반환 문자열만 바꾼다:

```tsx
  const describeThreshold = (slug: string): string | null => {
    const row = thresholdFor.get(slug)
    if (!row) return null
    if (row.kind === 'gain') {
      if (row.thresholdPercent === null) {
        return HELP.miranda.gainCapped(percent(overloadAtkCapPercent))
      }
      const gap = row.thresholdPercent - row.currentPercent
      return HELP.miranda.gainAt(
        percent(row.currentPercent),
        percent(row.thresholdPercent),
        gap,
      )
    }
    // kind가 'keep'이면 지금 받고 있다는 뜻이라 경계는 항상 숫자다 (백엔드
    // overload_thresholds가 이 조합에서만 null을 안 낸다) - null 분기는 gain 쪽뿐.
    const { thresholdPercent } = row
    if (thresholdPercent === null) return null
    if (thresholdPercent === 0) return HELP.miranda.keepAlways
    const slack = row.currentPercent - thresholdPercent
    return HELP.miranda.keepAbove(
      percent(thresholdPercent),
      percent(row.currentPercent),
      slack,
    )
  }
```

**주의:** `gap`과 `slack`은 원본에서 `.toFixed(2)`가 붙어 있었다. 이제 그 자릿수는 문구가 붙이므로 여기서는 숫자를 그대로 넘긴다.

`:112-121`:

```tsx
      {changedCycles.length > 0 && (
        <p className="miranda-targets__caveat">
          <HelpText>{HELP.miranda.targetsChange(changedCycles.join('·'))}</HelpText>
        </p>
      )}
      {burstCycles < total && (
        <p className="miranda-targets__caveat">
          <HelpText>{HELP.miranda.burstsFewer(total, burstCycles)}</HelpText>
        </p>
      )}
```

- [ ] **Step 6: 테스트와 타입을 확인한다**

Run: `cd frontend && npm test && npx tsc -b --noEmit`

Expected: 719 통과, tsc 에러 0.

- [ ] **Step 7: 커밋하고 diff의 글자를 대조한다**

```bash
git add frontend/src
git commit -m "미란다 계산기 해설을 helpText.ts로 옮긴다 - 임계값 분기는 컴포넌트에 남는다"
git diff HEAD~1 -U0 -- frontend/src | grep -E '^[-+].*[가-힣]'
```

---

### Task 6: `charge` — 차속 사다리 마무리 5개

`closingLine`의 3갈래도 문장만 옮기고 분기는 남긴다.

**Files:**
- Modify: `frontend/src/lib/helpText.ts` (기존 `charge` 그룹에 5개 추가)
- Modify: `frontend/src/components/ChargeWindowLadder.tsx:24-34`
- Modify: `frontend/src/components/ChargeWindowPanel.tsx:134`, `:142`
- Test: `frontend/src/components/ChargeWindowLadder.test.tsx:96`, `:110`

**Interfaces:**
- Produces:
  - `HELP.charge.ladderGap: (gapPoints: number) => string`
  - `HELP.charge.ladderChargeGone: string`
  - `HELP.charge.ladderCeiling: (ceiling: string) => string`
  - `HELP.charge.ladderAtLast: string`
  - `HELP.charge.rosterFallbackHint: string`

- [ ] **Step 1: assertion 둘을 HELP 참조로 바꾼다**

`ChargeWindowLadder.test.tsx:110`은 "does not blame the ceiling for a ladder that ran past it" 케이스다 — 마지막 구간 `0.3333`이 상한 `0.24`보다 위라 `closingLine`의 마지막 return을 탄다. **`ladderAtLast`이지 `ladderChargeGone`이 아니다**(후자는 113행부터의 별도 케이스가 잰다).

```ts
// ChargeWindowLadder.test.tsx:96
expect(screen.getByText(HELP.charge.ladderCeiling('24.00%'))).toBeInTheDocument()

// ChargeWindowLadder.test.tsx:110
expect(screen.getByText(HELP.charge.ladderAtLast)).toBeInTheDocument()
```

**`:109`는 바꾸지 않는다** — 「없음」을 재는데 `ladderCeiling`이 함수다.

**`:113`부터의 케이스도 확인한다.** 이 스캔은 `더 올릴 구간이 없습니다`·`오버로드 상한`으로 잡았는데, 그 케이스는 `차지가 이미 사라졌습니다`를 재고 있을 수 있다. 파일을 열어 `ladderChargeGone`을 재는 줄이 있으면 그것도 참조로 바꾼다:

```ts
expect(screen.getByText(HELP.charge.ladderChargeGone)).toBeInTheDocument()
```

- [ ] **Step 2: 테스트를 돌려 실패를 확인한다**

Run: `cd frontend && npx vitest run src/components/ChargeWindowLadder.test.tsx`

Expected: FAIL. `HELP.charge.ladderAtLast`가 `undefined`.

- [ ] **Step 3: `charge` 그룹에 5개를 추가한다**

기존 `charge` 그룹 안, `notes` 다음에:

```ts
    ladderGap: (gapPoints: number) => `다음 구간까지 ${gapPoints.toFixed(2)}%p 남았습니다.`,
    ladderChargeGone: '더 올릴 구간이 없습니다 — 차지가 이미 사라졌습니다.',
    ladderCeiling: (ceiling: string) =>
      `오버로드 상한 ${ceiling}까지만 보여줍니다 — 4부위 전부 최고 굴림이 그 상한입니다.`,
    ladderAtLast: '더 올릴 구간이 없습니다 — 지금 합계가 이미 마지막 구간입니다.',
    rosterFallbackHint: '(%, 비우면 동기화된 로스터 값)',
```

- [ ] **Step 4: 테스트를 돌려 통과를 확인한다**

Run: `cd frontend && npx vitest run src/components/ChargeWindowLadder.test.tsx`

Expected: PASS. `ladderCeiling('24.00%')`가 실패하면 그 자리의 `percent()` 출력이 `24.00%`가 아니라는 뜻이니, 96행 원본 정규식이 재던 값을 다시 읽는다.

- [ ] **Step 5: 두 컴포넌트를 참조로 바꾼다**

`ChargeWindowLadder.tsx:24-34` — **19-23행 주석은 그대로 둔다**:

```tsx
const closingLine = (result: ChargeWindowResult, gap: number | null): string => {
  if (gap !== null) return HELP.charge.ladderGap(gap * 100)
  const last = result.thresholds[result.thresholds.length - 1]
  if (last === undefined || last.chargeSpeedPercent >= 1) {
    return HELP.charge.ladderChargeGone
  }
  if (last.chargeSpeedPercent <= result.chargeSpeedCeiling + 1e-9) {
    return HELP.charge.ladderCeiling(percent(result.chargeSpeedCeiling))
  }
  return HELP.charge.ladderAtLast
}
```

79행의 렌더도 `HelpText`로 바꾼다:

```tsx
      <p className="charge-ladder__next"><HelpText>{closingLine(result, gap)}</HelpText></p>
```

`ChargeWindowPanel.tsx:134`와 `:142` — 두 곳 다:

```tsx
          hint={HELP.charge.rosterFallbackHint}
```

- [ ] **Step 6: 테스트와 타입을 확인한다**

Run: `cd frontend && npm test && npx tsc -b --noEmit`

Expected: 719 통과, tsc 에러 0.

- [ ] **Step 7: 커밋하고 diff의 글자를 대조한다**

```bash
git add frontend/src
git commit -m "차속 사다리 마무리 문구를 helpText.ts로 옮긴다 - 끝난 이유를 고르는 분기는 컴포넌트에 남는다"
git diff HEAD~1 -U0 -- frontend/src | grep -E '^[-+].*[가-힣]'
```

---

### Task 7: `roster` + `sync` — 로스터·동기화 안내 7개

`lib/`와 `hooks/`에 있는 문구가 여기 포함된다. 동기화 패널의 `notes` 렌더를 `<HelpText>`로 바꿔, 로스터 경고와 이름 안내에서도 굵게를 쓸 수 있게 만든다.

**Files:**
- Modify: `frontend/src/lib/helpText.ts` (`savedRuns` 다음 `roster`, 기존 `sync` 그룹에 4개 추가)
- Modify: `frontend/src/components/UnitFilterBar.tsx:181`
- Modify: `frontend/src/lib/rosterImport.ts:86-101`
- Modify: `frontend/src/components/SyncRosterPanel.tsx:72-80`, `:163-166`, `:257`, `:259-263`
- Modify: `frontend/src/hooks/useBookmarkletImport.ts:176-178`
- Test: `frontend/src/components/UnitFilterBar.test.tsx:160`, `:166`; `frontend/src/components/SyncRosterPanel.test.tsx:166`, `:194`, `:212`, `:224`

**Interfaces:**
- Produces:
  - `HELP.roster.emptyFilter: string`
  - `HELP.roster.importUnsupported: (count: number, names: string) => string`
  - `HELP.roster.importUnmeasured: (count: number, names: string) => string`
  - `HELP.sync.serverChoice: string`
  - `HELP.sync.importing: string`
  - `HELP.sync.nameUnavailable: string`
  - `HELP.sync.bookmarkletNoAccount: string` (평문 전용)

- [ ] **Step 1: assertion 여섯 곳을 HELP 참조로 바꾼다**

두 테스트 파일 상단에 `import { HELP } from '../lib/helpText'` 추가.

`emptyFilter`와 `nameUnavailable`은 **둘 다 상수**이므로 존재/부재 쌍을 함께 바꾼다 — 문구가 바뀌면 두 줄이 같이 따라가야 한다.

```ts
// UnitFilterBar.test.tsx:160
expect(screen.getByText(HELP.roster.emptyFilter)).toBeInTheDocument()
// UnitFilterBar.test.tsx:166
expect(screen.queryByText(HELP.roster.emptyFilter)).not.toBeInTheDocument()

// SyncRosterPanel.test.tsx:166
expect(await screen.findByText(HELP.sync.nameUnavailable)).toBeTruthy()
// SyncRosterPanel.test.tsx:194, :212, :224 (셋 다 같은 형태)
expect(screen.queryByText(HELP.sync.nameUnavailable)).toBeNull()
```

**`SyncRosterPanel.test.tsx:260`은 바꾸지 않는다** — `importUnsupported`가 함수인데 그 자리는 `/보유 유닛 중 1기가 아직 미지원/`으로 문장 일부만 잰다.

- [ ] **Step 2: 테스트를 돌려 실패를 확인한다**

Run: `cd frontend && npx vitest run src/components/UnitFilterBar.test.tsx src/components/SyncRosterPanel.test.tsx`

Expected: FAIL. `HELP.roster`가 `undefined`.

- [ ] **Step 3: `roster` 그룹을 추가하고 `sync`에 4개를 넣는다**

`savedRuns` 다음(`profile` 앞)에:

```ts
  roster: {
    emptyFilter: '조건에 맞는 니케가 없어요.',
    importUnsupported: (count: number, names: string) =>
      `보유 유닛 중 ${count}기가 아직 미지원이라 추천에서 제외돼요: ${names}`,
    importUnmeasured: (count: number, names: string) =>
      `보유 유닛 중 ${count}기가 제외됐어요 — 레벨 400 스탯이 측정된 적이 없어요: ${names}`,
  },

```

기존 `sync` 그룹 안, `chooseServer` 다음에:

```ts
    serverChoice: '계정이 있는 서버를 고르면 그 서버만 조회해요. 모르겠으면 자동으로 두세요.',
    importing: '가져오는 중…',
    nameUnavailable:
      '계정 이름을 읽지 못했어요. 로스터는 정상이에요. 위 계정 드롭다운 옆 계정 이름 바꾸기로 원하는 이름을 붙여주세요.',
    /** 평문 전용 - error 상태로 가고 그 자리는 다른 에러도 쓰므로 HelpText로 안 그린다. */
    bookmarkletNoAccount:
      '북마크릿이 계정 정보를 보내지 않았어요. "동기화 방법"을 열어 북마크릿을 다시 설치한 뒤 시도해 주세요.',
```

- [ ] **Step 4: 테스트를 돌려 통과를 확인한다**

Run: `cd frontend && npx vitest run src/components/UnitFilterBar.test.tsx src/components/SyncRosterPanel.test.tsx`

Expected: PASS.

- [ ] **Step 5: 네 파일을 참조로 바꾼다**

`UnitFilterBar.tsx:181`:

```tsx
        <p className="unit-filter__empty"><HelpText>{HELP.roster.emptyFilter}</HelpText></p>
```

`rosterImport.ts` — import 추가 후 86-101행. **92-94행의 주석은 그대로 둔다**:

```ts
  if (unsupported.length > 0) {
    warnings.push(HELP.roster.importUnsupported(unsupported.length, unsupported.join(', ')))
  }
  // A dropped unit is worth a louder line than an unsupported one: it IS
  // encoded and would be fielded, and the only reason it is missing is a hole in
  // the measured data that a different account happens to expose.
  if (data.unmeasured && data.unmeasured.length > 0) {
    warnings.push(
      HELP.roster.importUnmeasured(
        data.unmeasured.length,
        data.unmeasured.map((u) => `${u.name_en} (${u.reason})`).join('; '),
      ),
    )
  }
```

`SyncRosterPanel.tsx:72-80` — **61-70행의 주석은 그대로 둔다**:

```tsx
      setNotes(
        nickname || !nicknameError || alreadyNamed
          ? warnings
          : [...warnings, HELP.sync.nameUnavailable],
      )
```

`:163-166`:

```tsx
            <p className="sync__hint">
              <HelpText>{HELP.sync.serverChoice}</HelpText>
            </p>
```

`:257`:

```tsx
      {status === 'importing' && <p className="sync__message"><HelpText>{HELP.sync.importing}</HelpText></p>}
```

`:259-263` — notes 렌더를 `HelpText`로:

```tsx
      {notes.map((note, i) => (
        <p className="sync__message" key={i}>
          <HelpText>{note}</HelpText>
        </p>
      ))}
```

`useBookmarkletImport.ts:176-178` — import 추가 후:

```ts
      if (id === '') {
        setError(HELP.sync.bookmarkletNoAccount)
```

- [ ] **Step 6: 테스트와 타입을 확인한다**

Run: `cd frontend && npm test && npx tsc -b --noEmit`

Expected: 719 통과, tsc 에러 0.

**주의:** `SyncRosterPanel.test.tsx:260`은 정규식을 유지했다. 문구가 안 바뀌었으므로 그대로 통과해야 한다 — 빨개지면 `importUnsupported`의 글자가 원본과 다르다는 뜻이다.

- [ ] **Step 7: 커밋하고 diff의 글자를 대조한다**

```bash
git add frontend/src
git commit -m "로스터·동기화 안내를 helpText.ts로 옮기고 동기화 알림줄을 HelpText로 그린다"
git diff HEAD~1 -U0 -- frontend/src | grep -E '^[-+].*[가-힣]'
```

---

### Task 8: 전수 확인 — 남은 설명문이 없는지, 화면이 그대로인지

옮기지 못하고 남은 설명문을 찾고, 앱을 띄워 테스트가 못 잡는 두 가지(CSS 깨짐, 별표 샘)를 확인한다.

**Files:**
- Read only: `frontend/src` 전체
- Modify: 발견된 누락이 있으면 해당 파일과 `helpText.ts`

- [ ] **Step 1: 남은 한글 문자열을 다시 스캔한다**

```bash
cd frontend/src && python -c "
import re,glob,io
files=[f for f in glob.glob('components/**/*.tsx',recursive=True)+['App.tsx']+glob.glob('lib/**/*.ts',recursive=True)+glob.glob('hooks/**/*.ts',recursive=True) if '.test.' not in f and 'helpText' not in f]
out=io.open('../../scan.txt','w',encoding='utf-8')
for f in sorted(files):
    src=open(f,encoding='utf-8').read()
    s=re.sub(r'/\*.*?\*/',lambda m:'\n'*m.group().count('\n'),src,flags=re.S)
    s=re.sub(r'^(\s*)//.*\$',r'\1',s,flags=re.M)
    hits=[(i+1,l.strip()) for i,l in enumerate(s.splitlines()) if re.search(r'[가-힣]',l) and not l.strip().startswith('//')]
    if hits:
        out.write('== '+f+'\n')
        for i,l in hits: out.write(f'{i:4}| {l}\n')
out.close()"
```

`scan.txt`를 읽고, 남은 것이 전부 **라벨·버튼·옵션·에러·검증 메시지·용어 사전**인지 확인한다. 설명 문장이 남아 있으면 해당 그룹에 추가하고 옮긴다. 확인이 끝나면 `scan.txt`를 지운다(리포에 커밋하지 않는다).

- [ ] **Step 2: 전체 테스트와 타입을 돌린다**

Run: `cd frontend && npm test && npx tsc -b --noEmit`

Expected: 719 통과, tsc 에러 0. 두 숫자를 실제 출력에서 읽어 적는다 — 719가 아니면 그 차이가 무엇인지 밝히고 나서 넘어간다.

- [ ] **Step 3: 앱을 띄워 화면을 확인한다**

Run: `./dev.ps1` (백엔드 :8000 + Vite :5173). 포트 8000에 Fienn의 개발 백엔드가 이미 떠 있으면 그것을 쓰고 죽이지 않는다.

브라우저에서 확인할 것:

1. **머리말** — 부제와 큐브 주석이 두 줄로 제자리에 있는가
2. **계정 없음 화면** — 빈 상태 문구가 가운데 정렬돼 있는가
3. **솔로 레이드 탭** — 탐색 풀 안내가 한 줄로 이어지는가(`78/78 탐색 풀에 포함됨 — …`), 미지원 꼬리가 붙을 때 앞 공백이 있는가
4. **드래프트 탭** — 배치 힌트가 두 문장으로 이어지는가(덱 1개일 때와 여러 개일 때 각각)
5. **결과 화면** — 분할 설명·벤치·자리 순서 문구의 여백과 색이 그대로인가
6. **계산기 탭** — 미란다 안내, 차속 사다리 마무리 줄
7. **동기화 탭** — 서버 선택 안내, 알림줄
8. **별표가 새는 곳이 없는가** — 화면 어디에도 `**`가 글자로 보이지 않아야 한다

- [ ] **Step 4: 스크린샷을 남기고 마무리한다**

문제가 없으면 브랜치를 정리한다:

```bash
git log --oneline wip/scaffolding..HEAD
```

8개 커밋(설계문서 1 + 태스크 7)이 보여야 한다.

- [ ] **Step 5: 문서를 갱신한다**

`docs/roadmap.md`의 To-Do에 이 작업 항목이 있으면 체크한다. 없으면 추가하지 않는다 — 이 작업은 로드맵의 단계가 아니라 유지보수다.

`/document` 명령으로 docs-keeper에게 인사이트 하나를 남긴다: **JSX 여러 줄 텍스트를 단일 문자열로 옮길 때 줄바꿈이 공백 하나로 접힌다는 것, 그리고 테스트를 먼저 `HELP` 참조로 바꾸면 그 통과가 「옮긴 글자가 같다」는 증명이 된다는 것.**

---

## Self-Review

**1. Spec coverage**

| 스펙 섹션 | 구현 태스크 |
|---|---|
| §1 무엇이 오고 무엇이 안 오는가 | Task 1(헤더 규칙) + Task 8 Step 1(누락 스캔) |
| §2 규칙 1 함수 | Task 2·4·5·6·7의 함수 항목 |
| §2 규칙 2 분기는 컴포넌트에 | Task 4(DraftEditor), Task 5(describeThreshold), Task 6(closingLine) |
| §2 규칙 3 평문 전용 | Task 2(pinTitle), Task 3(confirm 둘), Task 7(bookmarkletNoAccount) |
| §3 그룹 구조 | Global Constraints의 순서 규칙 + 각 태스크의 삽입 위치 |
| §4 이동 대상 47개 | Task 1(3) + 2(9) + 3(5) + 4(9) + 5(9) + 6(5) + 7(7) = 47 ✓ |
| §5 테스트도 HELP를 참조 | 각 태스크 Step 1 — 39군데 중 29곳을 바꾸고 10곳은 정규식 유지 |
| §6 중복 3쌍 | Task 2(bench), Task 3(restoreHint), Task 4(evaluateRunning) |
| §7 검증 | 각 태스크 Step 6 + Task 8 |

**assertion 39군데의 태스크별 배분** (합이 맞는지 확인용):

| 태스크 | 바꿈 | 유지 |
|---|---|---|
| 1 (app) | `App.test:70` | — |
| 2 (results) | `DeckResults:9,53` · `RaidResults:9,50,64` · `DraftResults:79` · `RecommendPanel:471,851,971,1034` (10) | `RecommendPanel:854` |
| 3 (savedRuns) | `SavedRunList:52` | — |
| 4 (recommend) | `App.test:374,476,482` · `RecommendPanel:109,485` (5) | `RecommendPanel:742,958,1269,1324,1400` (5) |
| 5 (miranda) | `MirandaCalculatorPanel:114` · `MirandaTargets:72,110,125` (4) | `MirandaTargets:86,99,123,124` (4) |
| 6 (charge) | `ChargeWindowLadder:96,110` (+113 케이스 확인) | `ChargeWindowLadder:109` |
| 7 (roster/sync) | `UnitFilterBar:160,166` · `SyncRosterPanel:166,194,212,224` (6) | `SyncRosterPanel:260` |
| **합** | **29** | **10** |

**2. Placeholder scan** — "TBD"·"적절히"·"비슷하게" 없음. 모든 문자열이 최종 형태로 적혀 있다.

**3. Type consistency** — 함수 시그니처가 Interfaces 블록과 코드 블록에서 일치한다. `burstsFewer(total, bursts)`의 인자 순서가 원본 JSX(`{total}사이클 중 {burstCycles}번`)와 같은 순서임을 확인했다.

**남은 판단 지점 하나** — Task 8 Step 1의 스캔 결과에 설명 문장이 남아 있는지. 나머지 둘(테스트 모드, 사다리 갈래)은 원본을 읽어 계획 안에서 확정했다.
