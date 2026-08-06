# 결과 화면 정리와 결과 보관 — 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 솔로 레이드 보스 방어력 기본값을 넣고, 거의 손대지 않는 두 입력을 접고, 결과 카드를 다열 그리드로 좁히고, 결과에 보스 설정을 적고, 결과를 이름 붙여 보관할 수 있게 한다.

**Architecture:** 앞의 넷은 기존 컴포넌트를 좁게 고치는 일이다(보스 폼 하나, CSS 한 규칙, 새 표시 컴포넌트 하나). 다섯째 보관 기능은 `types/profile.ts`의 순수 함수 → `useProfiles` 훅 → 새 `SavedRunList` 컴포넌트 → 두 탭 배선 순으로 아래에서 위로 쌓는다. 두 탭이 섞이지 않는 것은 `SavedRun.tab` 필드 하나가 담당한다.

**Tech Stack:** React 19 + TypeScript + Vite, Vitest + @testing-library/react, localStorage 직렬화.

## Global Constraints

- 설계 문서: `docs/superpowers/specs/2026-08-06-result-view-and-saved-runs-design.md`
- 시작 기준선: 프론트엔드 **54파일 524 테스트 통과**. 모든 태스크가 끝날 때 이 수가 줄면 안 된다.
- 테스트 실행: `cd frontend && npx vitest run <경로>` (전체는 `npm test -- --run`)
- Vitest는 `css: false`다 — CSS는 단위 테스트로 검증할 수 없다. 그리드는 Task 12에서 앱을 띄워 눈으로 본다.
- 화면 문구는 한국어. 속성은 **약점**으로 말한다(보스 본인 속성이 아니라) — `weaknessFor`/`elementLabel`을 쓴다.
- 주석은 무엇을/왜만 쓴다. 무엇이 바뀌었는지·예전엔 어땠는지는 쓰지 않는다.
- 커밋 메시지는 영어 한 줄, 기존 로그 스타일을 따른다.

---

### Task 1: 솔로 레이드 보스 방어력 기본값

**Files:**
- Modify: `frontend/src/types/bossProfileDraft.ts:18-27`
- Modify: `frontend/src/components/RecommendPanel.tsx:111`
- Test: `frontend/src/types/bossProfileDraft.test.ts`

**Interfaces:**
- Produces: `makeDefaultBossProfileDraft(enemyDef?: string): BossProfileDraft` — 인자가 없으면 `'0'`
- Produces: `SOLO_RAID_DEFAULT_ENEMY_DEF = '31784'` (`RecommendPanel.tsx`가 소유·export)

- [ ] **Step 1: Write the failing test**

`frontend/src/types/bossProfileDraft.test.ts` 맨 아래에 추가:

```ts
describe('makeDefaultBossProfileDraft', () => {
  it('defaults enemy_def to 0 when no default is given', () => {
    expect(makeDefaultBossProfileDraft().enemy_def).toBe('0')
  })

  it('takes the caller-supplied enemy_def', () => {
    expect(makeDefaultBossProfileDraft('31784').enemy_def).toBe('31784')
  })

  it('leaves every other field at its default when given one', () => {
    const withDef = makeDefaultBossProfileDraft('31784')
    expect({ ...withDef, enemy_def: '0' }).toEqual(makeDefaultBossProfileDraft())
  })
})
```

`makeDefaultBossProfileDraft`가 이 파일의 import에 없으면 추가한다.

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npx vitest run src/types/bossProfileDraft.test.ts`
Expected: FAIL — `makeDefaultBossProfileDraft('31784').enemy_def`가 `'0'`

- [ ] **Step 3: Write minimal implementation**

`frontend/src/types/bossProfileDraft.ts`:

```ts
/** 기본 방어력은 호출부가 정한다 — 솔로 레이드와 유니온 레이드 보스는 방어력이
 * 다르므로, 공유 기본값 하나로는 한쪽이 틀린 값으로 계산된다. */
export const makeDefaultBossProfileDraft = (enemyDef = '0'): BossProfileDraft => ({
  element: null,
  core_hittable: false,
  pierce_hits_body_behind_core: false,
  enemy_def: enemyDef,
  fight_duration: '180',
  part_destructible: false,
  effective_range_band: null,
  elemental_interrupt_required: false,
})
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npx vitest run src/types/bossProfileDraft.test.ts`
Expected: PASS

- [ ] **Step 5: 솔로 탭이 그 값을 쓰게 한다**

`frontend/src/components/RecommendPanel.tsx` — `RecommendMode` 타입 선언 바로 위에 상수를 놓는다:

```ts
/** 솔로 레이드 보스의 방어력. 유니온 레이드 보스는 다른 값이라 이 기본값을
 * 공유하지 않는다(Fienn, 2026-08-06). */
export const SOLO_RAID_DEFAULT_ENEMY_DEF = '31784'
```

`useState` 초기화(현재 111행)를 바꾼다:

```ts
  const [draft, setDraft] = useState<BossProfileDraft>(
    makeDefaultBossProfileDraft(SOLO_RAID_DEFAULT_ENEMY_DEF),
  )
```

`UnionRaidPanel.tsx`는 손대지 않는다 — 무인자 호출이 그대로 `'0'`을 받는다.

- [ ] **Step 6: Write the panel-level test**

`frontend/src/components/RecommendPanel.test.tsx`에 추가(파일의 기존 render 헬퍼를 그대로 쓴다):

```ts
it('opens with the solo raid boss DEF prefilled', () => {
  renderPanel()
  expect(screen.getByLabelText(/적 방어력/)).toHaveValue(31784)
})
```

- [ ] **Step 7: Run both test files**

Run: `cd frontend && npx vitest run src/types/bossProfileDraft.test.ts src/components/RecommendPanel.test.tsx`
Expected: PASS

- [ ] **Step 8: Commit**

```bash
git add frontend/src/types/bossProfileDraft.ts frontend/src/types/bossProfileDraft.test.ts frontend/src/components/RecommendPanel.tsx frontend/src/components/RecommendPanel.test.tsx
git commit -m "Prefill the solo raid boss DEF, leaving union raid's default alone"
```

---

### Task 2: 방어력·전투 시간을 "기타 설정"으로 접기

**Files:**
- Modify: `frontend/src/components/BossProfileField.tsx:208-225`
- Modify: `frontend/src/App.css` (`.group__details` 근처, 723-750행 부근)
- Test: `frontend/src/components/BossProfileField.test.tsx`

**Interfaces:**
- Consumes: Task 1의 `makeDefaultBossProfileDraft`
- Produces: 없음 (컴포넌트 내부 변경)

- [ ] **Step 1: Write the failing tests**

`frontend/src/components/BossProfileField.test.tsx`에 추가:

```tsx
describe('기타 설정', () => {
  it('folds DEF and fight duration behind a summary that shows their values', () => {
    render(
      <BossProfileField value={makeDefaultBossProfileDraft('31784')} onChange={() => {}} />,
    )
    const details = screen.getByText(/기타 설정/).closest('details')
    expect(details).not.toBeNull()
    expect(details).not.toHaveAttribute('open')
    expect(screen.getByText(/방어력 31,784/)).toBeInTheDocument()
    expect(screen.getByText(/180초/)).toBeInTheDocument()
  })

  it('opens itself when one of the folded fields has an error', () => {
    render(
      <BossProfileField
        value={{ ...makeDefaultBossProfileDraft(), enemy_def: '' }}
        errors={{ enemy_def: '필수 입력이에요' }}
        onChange={() => {}}
      />,
    )
    expect(screen.getByText(/기타 설정/).closest('details')).toHaveAttribute('open')
  })

  it('shows a dash in the summary while a folded field is empty', () => {
    render(
      <BossProfileField
        value={{ ...makeDefaultBossProfileDraft(), enemy_def: '' }}
        onChange={() => {}}
      />,
    )
    expect(screen.getByText(/방어력 —/)).toBeInTheDocument()
  })
})
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd frontend && npx vitest run src/components/BossProfileField.test.tsx`
Expected: FAIL — "기타 설정" 텍스트가 없다

- [ ] **Step 3: Write the implementation**

`frontend/src/components/BossProfileField.tsx`의 파일 상단에 요약 헬퍼를 추가한다:

```tsx
/** 접힌 채로도 무슨 값으로 계산되는지 보이게 하는 요약. 편집 중이라 비어 있는
 * 칸은 숫자 대신 —로 둔다. */
const foldedSummary = (draft: BossProfileDraft): string => {
  const def = draft.enemy_def.trim()
  const seconds = draft.fight_duration.trim()
  const defText = def === '' ? '—' : Number(def).toLocaleString()
  const secondsText = seconds === '' ? '—' : seconds
  return `방어력 ${defText} · ${secondsText}초`
}
```

`import type` 줄에 `BossProfileDraft`가 이미 있으므로 추가 import는 없다.

컴포넌트 맨 아래의 `<div className="field-row field-row--pair">` 블록을 `<details>`로 감싼다:

```tsx
      {/* 거의 바꾸지 않는 두 값이라 접어 둔다. 오류가 있을 때는 강제로 펼쳐
          제출을 막는 이유가 접힌 상자 안에 숨지 않게 한다. */}
      <details
        className="group__details boss-profile__folded"
        open={errors?.enemy_def || errors?.fight_duration ? true : undefined}
      >
        <summary className="group__hint">기타 설정 — {foldedSummary(value)}</summary>
        <div className="field-row field-row--pair">
          <NumberField
            label="적 방어력"
            value={value.enemy_def}
            error={errors?.enemy_def}
            min={0}
            onChange={(enemy_def) => onChange({ ...value, enemy_def })}
          />
          <NumberField
            label="전투 시간"
            hint="초"
            value={value.fight_duration}
            error={errors?.fight_duration}
            min={0}
            step={1}
            onChange={(fight_duration) => onChange({ ...value, fight_duration })}
          />
        </div>
      </details>
```

- [ ] **Step 4: Add the stylesheet rule**

`frontend/src/App.css`의 `.group__details > summary` 규칙 바로 아래에 추가:

```css
/* 접힌 요약은 폼의 다른 라벨과 같은 무게로 읽혀야 한다 — 이것은 값이 아니라
   값이 있는 곳을 가리키는 표지다. */
.boss-profile__folded > summary {
  cursor: pointer;
  margin-top: var(--sp-2);
}
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd frontend && npx vitest run src/components/BossProfileField.test.tsx`
Expected: PASS

- [ ] **Step 6: Run the two panels' tests — they render this field**

Run: `cd frontend && npx vitest run src/components/RecommendPanel.test.tsx src/components/UnionRaidPanel.test.tsx`
Expected: PASS. 실패한다면 그 테스트가 접힌 필드를 직접 찾고 있다는 뜻이다. jsdom은 `<details>`가 닫혀 있어도 자식을 접근성 트리에 남기므로 대부분 그대로 통과한다 — 그래도 깨지면 그 테스트를 고친다(구현이 아니라).

- [ ] **Step 7: Commit**

```bash
git add frontend/src/components/BossProfileField.tsx frontend/src/components/BossProfileField.test.tsx frontend/src/App.css
git commit -m "Fold DEF and fight duration behind a summary that still shows them"
```

---

### Task 3: 결과 카드 다열 그리드

**Files:**
- Modify: `frontend/src/App.css:1110-1118`

**Interfaces:**
- Produces: 없음 (CSS만)

- [ ] **Step 1: Change the rule**

`frontend/src/App.css`의 `.deck-results`를 바꾼다:

```css
/* 덱 카드는 얼굴 다섯 개가 들어가는 만큼만 넓다. 남는 가로 폭은 다음 덱이
   받는다 — 창이 넓을수록 세로 스크롤이 짧아진다. */
.deck-results {
  list-style: none;
  margin: 0;
  padding: 0;
  width: 100%;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(340px, 1fr));
  gap: var(--sp-3);
}
```

`.deck-results__item`은 그대로 둔다 — 그리드 항목이 되어도 내부는 여전히 세로 flex다.

- [ ] **Step 2: Run the four result components' tests**

Run: `cd frontend && npx vitest run src/components/DeckResults.test.tsx src/components/RaidResults.test.tsx src/components/DraftResults.test.tsx src/components/EvaluationResults.test.tsx`
Expected: PASS (Vitest는 `css: false`라 이 변경이 테스트에 보이지 않는다 — 통과가 곧 "안 깨졌다"는 뜻이고, 실제 확인은 Task 13이다)

- [ ] **Step 3: Commit**

```bash
git add frontend/src/App.css
git commit -m "Lay deck cards out in as many columns as the window affords"
```

---

### Task 4: BossSummary 컴포넌트

**Files:**
- Create: `frontend/src/components/BossSummary.tsx`
- Create: `frontend/src/components/BossSummary.test.tsx`
- Modify: `frontend/src/App.css` (`.deck-results__excluded` 규칙 부근)

**Interfaces:**
- Consumes: `BossProfile` (`types/recommend.ts`), `elementLabel`, `weaknessFor`, `formatDamage`
- Produces: `<BossSummary boss={boss} />` — 배지 한 줄을 그리는 컴포넌트

- [ ] **Step 1: Write the failing tests**

`frontend/src/components/BossSummary.test.tsx`:

```tsx
import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { BossSummary } from './BossSummary'
import type { BossProfile } from '../types/recommend'

const boss = (overrides: Partial<BossProfile> = {}): BossProfile => ({
  element: null,
  core_hittable: false,
  pierce_hits_body_behind_core: false,
  enemy_def: 31784,
  fight_duration: 180,
  part_destructible: false,
  effective_range_band: null,
  elemental_interrupt_required: false,
  ...overrides,
})

describe('BossSummary', () => {
  it('names the weakness, not the boss element', () => {
    // 'Fire' 보스는 수냉이 약점이다.
    render(<BossSummary boss={boss({ element: 'Fire' })} />)
    expect(screen.getByText(/약점 수냉/)).toBeInTheDocument()
  })

  it('says so when the boss has no weakness', () => {
    render(<BossSummary boss={boss()} />)
    expect(screen.getByText(/약점 없음/)).toBeInTheDocument()
  })

  it('omits every gimmick that is off', () => {
    render(<BossSummary boss={boss()} />)
    expect(screen.queryByText(/코어 피격/)).not.toBeInTheDocument()
    expect(screen.queryByText(/2관통/)).not.toBeInTheDocument()
    expect(screen.queryByText(/부위파괴/)).not.toBeInTheDocument()
    expect(screen.queryByText(/속성저지/)).not.toBeInTheDocument()
  })

  it('lists the gimmicks that are on', () => {
    render(
      <BossSummary
        boss={boss({
          core_hittable: true,
          pierce_hits_body_behind_core: true,
          part_destructible: true,
          elemental_interrupt_required: true,
        })}
      />,
    )
    expect(screen.getByText('코어 피격')).toBeInTheDocument()
    expect(screen.getByText('2관통')).toBeInTheDocument()
    expect(screen.getByText('부위파괴')).toBeInTheDocument()
    expect(screen.getByText('속성저지 필수')).toBeInTheDocument()
  })

  it('names the range band only when one is set', () => {
    const { rerender } = render(<BossSummary boss={boss()} />)
    expect(screen.queryByText(/거리/)).not.toBeInTheDocument()
    rerender(<BossSummary boss={boss({ effective_range_band: 'far' })} />)
    expect(screen.getByText('원거리')).toBeInTheDocument()
  })

  it('always carries the folded numbers, since the form hides them', () => {
    render(<BossSummary boss={boss()} />)
    expect(screen.getByText('방어력 31,784')).toBeInTheDocument()
    expect(screen.getByText('180초')).toBeInTheDocument()
  })
})
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd frontend && npx vitest run src/components/BossSummary.test.tsx`
Expected: FAIL — `./BossSummary` 모듈이 없다

- [ ] **Step 3: Write the implementation**

`frontend/src/components/BossSummary.tsx`:

```tsx
// 결과가 어떤 보스를 상대로 나온 것인지 한 줄로 적는다. 보스 폼이 방어력과
// 전투 시간을 접어 두므로, 그 두 값이 결과에 남는 유일한 자리이기도 하다.
//
// 켜진 기믹만 나온다 — 꺼진 기믹까지 적으면 줄만 길어지고, 없는 것은 화면에
// 없는 것으로 읽힌다.

import type { BossProfile } from '../types/recommend'
import { elementLabel } from '../lib/elementName'
import { weaknessFor } from '../lib/elementAdvantage'
import { formatDamage } from './formatDamage'

const RANGE_BAND_LABEL: Record<'near' | 'mid' | 'far', string> = {
  near: '근거리',
  mid: '중거리',
  far: '원거리',
}

interface BossSummaryProps {
  boss: BossProfile
}

export function BossSummary({ boss }: BossSummaryProps) {
  const gimmicks = [
    boss.core_hittable && '코어 피격',
    boss.pierce_hits_body_behind_core && '2관통',
    boss.part_destructible && '부위파괴',
    boss.elemental_interrupt_required && '속성저지 필수',
  ].filter((label): label is string => typeof label === 'string')

  return (
    <p className="boss-summary">
      <span className="boss-summary__weakness">
        {boss.element === null ? '약점 없음' : `약점 ${elementLabel(weaknessFor(boss.element))}`}
      </span>
      {boss.effective_range_band !== null && (
        <span className="boss-summary__badge">
          {RANGE_BAND_LABEL[boss.effective_range_band]}
        </span>
      )}
      {gimmicks.map((label) => (
        <span key={label} className="boss-summary__badge">
          {label}
        </span>
      ))}
      <span className="boss-summary__number">방어력 {formatDamage(boss.enemy_def)}</span>
      <span className="boss-summary__number">{boss.fight_duration}초</span>
    </p>
  )
}
```

- [ ] **Step 4: Add the stylesheet rules**

`frontend/src/App.css`의 `.deck-results__excluded` 규칙 바로 위에 추가:

```css
/* 결과가 무엇을 상대로 나온 것인지 적는 줄. 약점은 답을 가장 크게 좌우하므로
   본문 무게로, 기믹과 숫자는 조건이라 무채색으로 물러난다. */
.boss-summary {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  gap: var(--sp-1) var(--sp-3);
  margin: 0;
  font-size: 13px;
}

.boss-summary__weakness {
  font-weight: 600;
}

.boss-summary__badge,
.boss-summary__number {
  color: var(--text-muted);
}

.boss-summary__number {
  font-variant-numeric: tabular-nums;
}
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd frontend && npx vitest run src/components/BossSummary.test.tsx`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/BossSummary.tsx frontend/src/components/BossSummary.test.tsx frontend/src/App.css
git commit -m "Add a one-line boss summary for result views"
```

---

### Task 5: 솔로 결과 위에 BossSummary 걸기

**Files:**
- Modify: `frontend/src/components/RecommendPanel.tsx:651-703`
- Test: `frontend/src/components/RecommendPanel.test.tsx`

**Interfaces:**
- Consumes: Task 4의 `<BossSummary boss={…} />`

- [ ] **Step 1: Write the failing test**

`frontend/src/components/RecommendPanel.test.tsx`에 추가. 이 파일의 기존 제출 헬퍼(단일 덱 모드로 제출하고 성공 응답을 물리는 것)를 그대로 쓴다:

```tsx
it('names the boss the displayed result was computed against', async () => {
  // 폼에서 약점 작열을 고르고 단일 덱으로 제출한다.
  renderPanel()
  await userEvent.click(screen.getByRole('radio', { name: /작열/ }))
  await userEvent.click(screen.getByRole('button', { name: '인카운터!' }))
  expect(await screen.findByText(/약점 작열/)).toBeInTheDocument()
})

it('keeps the summary on the boss the result came from when the form changes after', async () => {
  renderPanel()
  await userEvent.click(screen.getByRole('radio', { name: /작열/ }))
  await userEvent.click(screen.getByRole('button', { name: '인카운터!' }))
  await screen.findByText(/약점 작열/)
  await userEvent.click(screen.getByRole('radio', { name: /수냉/ }))
  expect(screen.getByText(/약점 작열/)).toBeInTheDocument()
})
```

기존 테스트가 어떤 헬퍼로 렌더·제출하는지 먼저 읽고, 그 관례에 맞춘다. 라디오 접근명은 `element-picker`의 `elementLabel` 값(작열/수냉/풍압/철갑/전격)이다.

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npx vitest run src/components/RecommendPanel.test.tsx`
Expected: FAIL — "약점 작열"이 결과에 없다

- [ ] **Step 3: Write the implementation**

네 모드가 각자 "지금 이 모드의 결과가 화면에 있는가"를 다르게 판정하므로, 그 판정을
한 곳에 모은다. `frontend/src/components/RecommendPanel.tsx`에 `handleSubmit` 위쪽으로:

```tsx
  // 지금 화면에 떠 있는 결과가 채점된 보스. 라이브 폼 상태(`draft`)가 아니라
  // 제출 시점 스냅샷을 읽는다 - 결과가 나온 뒤 폼을 만지면 숫자는 옛 보스인데
  // 설명만 새 보스가 되어 화면이 거짓말을 한다.
  const displayedBoss = useMemo<BossProfile | null>(() => {
    if (mode === 'single') return single.status === 'success' ? singleBoss : null
    if (mode === 'raid' || mode === 'draft') {
      return displayResult && displayMode === mode ? displayBoss : null
    }
    return evaluation.status === 'success' ? evaluateBoss : null
  }, [
    mode,
    single.status,
    singleBoss,
    displayResult,
    displayMode,
    displayBoss,
    evaluation.status,
    evaluateBoss,
  ])
```

`import { BossSummary } from './BossSummary'`를 추가하고, 네 결과 렌더 **바로 위**
(현재 651행의 `{mode === 'single' && …}` 앞)에 한 줄을 놓는다:

```tsx
        {displayedBoss && <BossSummary boss={displayedBoss} />}
```

모드별로 네 번 쓰지 않는 이유는 `displayedBoss`가 이미 "어느 모드의 결과가 보이는가"를
답하고 있어서다. Task 11이 이 자리에 저장 버튼을 더한다.

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd frontend && npx vitest run src/components/RecommendPanel.test.tsx`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/RecommendPanel.tsx frontend/src/components/RecommendPanel.test.tsx
git commit -m "Head each solo result with the boss it was computed against"
```

---

### Task 6: 유니온 결과 카드마다 보스 적기

**Files:**
- Modify: `frontend/src/components/DeckCard.tsx`
- Modify: `frontend/src/components/EvaluationResults.tsx`
- Modify: `frontend/src/components/UnionRaidPanel.tsx:66,123,186-195`
- Modify: `frontend/src/components/RecommendPanel.tsx` (evaluate 모드의 `bossElements` 호출부)
- Test: `frontend/src/components/DeckCard.test.tsx`, `frontend/src/components/EvaluationResults.test.tsx`

**Interfaces:**
- Consumes: Task 4의 `<BossSummary />`
- Produces: `DeckCard`에 `boss?: BossProfile` prop 추가 — 있으면 카드 안에 요약을 그린다
- Produces: `EvaluationResults`의 prop이 `bossElements: BossElement[]` → `bosses: BossProfile[]`로 바뀐다

- [ ] **Step 1: Write the failing tests**

`frontend/src/components/DeckCard.test.tsx`에 추가:

```tsx
it('draws the boss inside the card when one is given', () => {
  render(
    <ol>
      <DeckCard
        label="1번 덱"
        deck={deckFixture()}
        boss={{
          element: 'Fire',
          core_hittable: true,
          pierce_hits_body_behind_core: false,
          enemy_def: 31784,
          fight_duration: 180,
          part_destructible: false,
          effective_range_band: null,
          elemental_interrupt_required: false,
        }}
      />
    </ol>,
  )
  expect(screen.getByText(/약점 수냉/)).toBeInTheDocument()
})

it('draws no boss line when none is given', () => {
  render(
    <ol>
      <DeckCard label="#1" deck={deckFixture()} />
    </ol>,
  )
  expect(screen.queryByText(/약점/)).not.toBeInTheDocument()
})
```

`deckFixture()`는 이 파일에 이미 있는 덱 픽스처를 쓴다(이름이 다르면 그것을 쓴다).

`frontend/src/components/EvaluationResults.test.tsx`의 기존 테스트에서 `bossElements={…}`를 `bosses={…}`로 바꾸고, 다음을 추가한다:

```tsx
it('labels each battle with its own boss and repeats the full setting per card', () => {
  render(
    <EvaluationResults
      decks={[deckFixture(), deckFixture2()]}
      combinedTotalDamage={5}
      bosses={[bossFixture({ element: 'Fire' }), bossFixture({ element: 'Wind' })]}
    />,
  )
  expect(screen.getByText(/1번 덱 · 약점 수냉/)).toBeInTheDocument()
  expect(screen.getByText(/2번 덱 · 약점 작열/)).toBeInTheDocument()
  // 카드마다 조건이 다시 적힌다 — 전투마다 보스가 다르기 때문이다.
  expect(screen.getAllByText(/방어력/)).toHaveLength(2)
})
```

`bossFixture`는 Task 4의 테스트가 쓴 `boss()` 헬퍼와 같은 모양으로 이 파일에 만든다.

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd frontend && npx vitest run src/components/DeckCard.test.tsx src/components/EvaluationResults.test.tsx`
Expected: FAIL — `boss`/`bosses` prop이 없다

- [ ] **Step 3: Write the implementation**

`frontend/src/components/DeckCard.tsx` — props에 추가하고 헤더 바로 아래에 그린다:

```tsx
interface DeckCardProps extends UnitLookups {
  label: string
  deck: DeckRecommendation
  /** 이 덱이 상대한 보스. 덱마다 보스가 다른 화면(유니온 레이드)만 넘긴다 —
   * 전부 같은 보스인 화면은 결과 위에 한 번만 적는다. */
  boss?: BossProfile
  …
}
```

`<div className="deck-results__header">` 닫힌 직후:

```tsx
      {boss && <BossSummary boss={boss} />}
```

`import type { BossProfile } from '../types/recommend'`와 `import { BossSummary } from './BossSummary'`를 추가한다.

`frontend/src/components/EvaluationResults.tsx`:

```tsx
interface EvaluationResultsProps extends UnitLookups {
  decks: DeckRecommendation[]
  combinedTotalDamage: number
  excludedSlugs?: string[]
  /** 덱 하나당 보스 하나. 유니온 레이드의 세 전투는 각자 보스를 고른다. */
  bosses: BossProfile[]
}
```

렌더에서:

```tsx
          <DeckCard
            key={deck.deck.join('-')}
            label={`${index + 1}번 덱 · ${bossElementLabel(bosses[index]?.element ?? null)}`}
            deck={deck}
            boss={bosses[index]}
            {...lookups}
          />
```

`import type { BossElement }`는 `bossElementLabel`이 여전히 쓰므로 남긴다. `BossProfile`을 import에 추가한다.

`frontend/src/components/UnionRaidPanel.tsx`:
- `const [evaluatedBossElements, setEvaluatedBossElements] = useState<BossElement[]>([])` →
  `const [evaluatedBosses, setEvaluatedBosses] = useState<BossProfile[]>([])`
- `setEvaluatedBossElements(bossProfiles.map((boss) => boss.element))` → `setEvaluatedBosses(bossProfiles)`
- `bossElements={evaluatedBossElements}` → `bosses={evaluatedBosses}`
- import를 `BossElement` → `BossProfile`로 바꾼다

`frontend/src/components/RecommendPanel.tsx`의 evaluate 렌더:

```tsx
            bosses={evaluation.decks.map(() => evaluateBoss!)}
```

솔로는 이미 결과 위에 한 줄을 적으므로(Task 5) `DeckCard`에는 보스가 내려가지 않는다 — `EvaluationResults`가 `boss={bosses[index]}`를 넘기는 것을 솔로에서만 막을 수는 없으니, **`EvaluationResults`에 `perCardBoss?: boolean`을 두지 않는다**. 대신 솔로 evaluate에서는 카드마다 같은 보스가 반복된다. 이는 받아들인다: 유니온과 코드가 갈리는 비용이 반복 한 줄보다 크다.

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd frontend && npx vitest run src/components/DeckCard.test.tsx src/components/EvaluationResults.test.tsx src/components/UnionRaidPanel.test.tsx src/components/RecommendPanel.test.tsx`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/DeckCard.tsx frontend/src/components/DeckCard.test.tsx frontend/src/components/EvaluationResults.tsx frontend/src/components/EvaluationResults.test.tsx frontend/src/components/UnionRaidPanel.tsx frontend/src/components/RecommendPanel.tsx
git commit -m "Carry each union battle's whole boss setting onto its deck card"
```

---

### Task 7: 보관 저장소 — 타입과 순수 함수

**Files:**
- Modify: `frontend/src/types/profile.ts`
- Modify: `frontend/src/hooks/useProfiles.ts:55-79` (`migrate`)
- Test: `frontend/src/types/profile.test.ts`, `frontend/src/hooks/useProfiles.test.ts`

**Interfaces:**
- Produces: `SavedRun`, `SoloRunView`, `UnionRunView`, `SAVED_RUNS_CAP`, `makeRunId`, `saveRun`, `renameRun`, `deleteRun`, `runsForTab`
- Produces: `Profile.savedRuns: SavedRun[]` (필수 필드)

- [ ] **Step 1: Write the failing tests**

`frontend/src/types/profile.test.ts`에 추가:

```ts
const soloRun = (overrides: Partial<SavedRun> = {}): SavedRun => ({
  id: '1000-0',
  name: '작열 · 전부 최적화 · 08-06',
  savedAt: 1000,
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
      effective_range_band: null,
      elemental_interrupt_required: false,
    },
    numDecks: 5,
    decks: [],
    combinedTotalDamage: 42,
    excludedSlugs: [],
    leftoverSlugs: [],
  },
  ...overrides,
})

describe('saved runs', () => {
  it('keeps a saved run on the profile', () => {
    const state = upsertProfile(emptyProfilesState(), {
      openId: 'a', area: 81, nickname: 'A', roster: [],
    })
    const next = saveRun(state, profileKey('a', 81), soloRun())
    expect(next.profiles[profileKey('a', 81)].savedRuns).toHaveLength(1)
  })

  it('refuses to save past the cap rather than evicting the oldest', () => {
    let state = upsertProfile(emptyProfilesState(), {
      openId: 'a', area: 81, nickname: 'A', roster: [],
    })
    const key = profileKey('a', 81)
    for (let i = 0; i < SAVED_RUNS_CAP; i++) {
      state = saveRun(state, key, soloRun({ id: `${i}`, name: `run ${i}` }))
    }
    const full = state
    state = saveRun(state, key, soloRun({ id: 'one-too-many', name: 'nope' }))
    expect(state).toBe(full)
    expect(state.profiles[key].savedRuns.map((r) => r.name)).not.toContain('nope')
  })

  it('survives a roster resync, unlike the result cache', () => {
    let state = upsertProfile(emptyProfilesState(), {
      openId: 'a', area: 81, nickname: 'A', roster: [],
    })
    const key = profileKey('a', 81)
    state = saveRun(state, key, soloRun())
    state = upsertProfile(state, {
      openId: 'a', area: 81, nickname: 'A',
      roster: [{ character_slug: 'rapi' } as never],
    })
    expect(state.profiles[key].savedRuns).toHaveLength(1)
    expect(state.profiles[key].results).toEqual({})
  })

  it('renames and deletes by id', () => {
    let state = upsertProfile(emptyProfilesState(), {
      openId: 'a', area: 81, nickname: 'A', roster: [],
    })
    const key = profileKey('a', 81)
    state = saveRun(state, key, soloRun({ id: 'x' }))
    state = renameRun(state, key, 'x', '새 이름')
    expect(state.profiles[key].savedRuns[0].name).toBe('새 이름')
    state = deleteRun(state, key, 'x')
    expect(state.profiles[key].savedRuns).toHaveLength(0)
  })

  it('separates the two tabs', () => {
    let state = upsertProfile(emptyProfilesState(), {
      openId: 'a', area: 81, nickname: 'A', roster: [],
    })
    const key = profileKey('a', 81)
    state = saveRun(state, key, soloRun({ id: 's' }))
    state = saveRun(state, key, {
      ...soloRun({ id: 'u' }),
      tab: 'union',
      view: { numBattles: 3, bosses: [], draft: { decks: [] }, decks: [], combinedTotalDamage: 0, excludedSlugs: [] },
    })
    const profile = state.profiles[key]
    expect(runsForTab(profile, 'solo').map((r) => r.id)).toEqual(['s'])
    expect(runsForTab(profile, 'union').map((r) => r.id)).toEqual(['u'])
  })

  it('lists newest first', () => {
    let state = upsertProfile(emptyProfilesState(), {
      openId: 'a', area: 81, nickname: 'A', roster: [],
    })
    const key = profileKey('a', 81)
    state = saveRun(state, key, soloRun({ id: 'old', savedAt: 1 }))
    state = saveRun(state, key, soloRun({ id: 'new', savedAt: 2 }))
    expect(runsForTab(state.profiles[key], 'solo').map((r) => r.id)).toEqual(['new', 'old'])
  })
})

describe('makeRunId', () => {
  it('is stable for a lone save at a timestamp', () => {
    expect(makeRunId(1000, [])).toBe('1000-0')
  })

  it('steps past an id already taken at the same millisecond', () => {
    expect(makeRunId(1000, [soloRun({ id: '1000-0', savedAt: 1000 })])).toBe('1000-1')
  })
})
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd frontend && npx vitest run src/types/profile.test.ts`
Expected: FAIL — `saveRun` 등이 export되지 않았다

- [ ] **Step 3: Write the implementation**

`frontend/src/types/profile.ts`에 추가:

```ts
/** 유저가 이름을 붙여 남겨 둔 결과 하나. 캐시(`results`)와 달리 로스터가 바뀌어도
 * 지워지지 않는다 - 이것은 "지금 로스터에 대한 답"이 아니라 "그때 이런 답이
 * 나왔다"는 기록이다. */
export interface SavedRun {
  id: string
  name: string
  savedAt: number
  /** 솔로 탭과 유니온 탭의 보관물이 섞이지 않게 하는 것은 이 필드다. */
  tab: 'solo' | 'union'
  view: SoloRunView | UnionRunView
}

interface SoloRunBase {
  boss: BossProfile
  numDecks: number
  excludedSlugs: string[]
}

/** 솔로 탭 네 모드. `mode`로 갈리는 판별 유니온인 이유는 타입이 실제로 다르기
 * 때문이다 - RaidDeck은 DeckRecommendation에 pinned_slugs를 필수로 더한 것이고,
 * DraftResults는 그 좁은 쪽을 요구한다. */
export type SoloRunView =
  | (SoloRunBase & { mode: 'single'; decks: DeckRecommendation[] })
  | (SoloRunBase & {
      mode: 'raid'
      decks: RaidDeck[]
      combinedTotalDamage: number
      leftoverSlugs: string[]
      swapConverged?: boolean
    })
  | (SoloRunBase & {
      mode: 'draft'
      decks: RaidDeck[]
      combinedTotalDamage: number
      leftoverSlugs: string[]
      withinDraft: DraftAllocation | null
      baselineTotalDamage: number | null
      swapConverged?: boolean
      draft: Draft | null
    })
  | (SoloRunBase & {
      mode: 'evaluate'
      decks: DeckRecommendation[]
      combinedTotalDamage: number
      draft: Draft
    })

export interface UnionRunView {
  numBattles: number
  bosses: BossProfile[]
  draft: Draft
  decks: DeckRecommendation[]
  combinedTotalDamage: number
  excludedSlugs: string[]
}

/** 프로필 하나가 보관할 수 있는 결과 수. 넘으면 저장을 거절한다 - 캐시와 달리
 * 유저가 이름 붙여 남긴 것을 말없이 밀어내면 안 된다. */
export const SAVED_RUNS_CAP = 50

/** 같은 밀리초에 두 번 저장해도 부딪히지 않는 결정적 id. */
export const makeRunId = (savedAt: number, existing: SavedRun[]): string =>
  `${savedAt}-${existing.filter((run) => run.savedAt === savedAt).length}`

/** 상한을 넘으면 상태를 그대로 돌려준다 - 호출부는 참조 동일성으로 거절을 안다. */
export const saveRun = (
  state: ProfilesState,
  key: string,
  run: SavedRun,
): ProfilesState => {
  const profile = state.profiles[key]
  if (!profile) return state
  if (profile.savedRuns.length >= SAVED_RUNS_CAP) return state

  const updated: Profile = { ...profile, savedRuns: [...profile.savedRuns, run] }
  return { ...state, profiles: { ...state.profiles, [key]: updated } }
}

export const renameRun = (
  state: ProfilesState,
  key: string,
  id: string,
  name: string,
): ProfilesState => {
  const profile = state.profiles[key]
  if (!profile) return state
  const updated: Profile = {
    ...profile,
    savedRuns: profile.savedRuns.map((run) => (run.id === id ? { ...run, name } : run)),
  }
  return { ...state, profiles: { ...state.profiles, [key]: updated } }
}

export const deleteRun = (state: ProfilesState, key: string, id: string): ProfilesState => {
  const profile = state.profiles[key]
  if (!profile) return state
  const updated: Profile = {
    ...profile,
    savedRuns: profile.savedRuns.filter((run) => run.id !== id),
  }
  return { ...state, profiles: { ...state.profiles, [key]: updated } }
}

/** 한 탭이 보여줄 보관물, 최신순. */
export const runsForTab = (profile: Profile, tab: SavedRun['tab']): SavedRun[] =>
  profile.savedRuns.filter((run) => run.tab === tab).slice().sort((a, b) => b.savedAt - a.savedAt)
```

`Profile` 인터페이스에 `savedRuns: SavedRun[]`를 추가하고, `upsertProfile`의 새 프로필 생성 분기에 `savedRuns: []`를 넣는다. **로스터 변경 시 비우는 분기(`{ results: {}, lastResultHash: null, lastInputs: null }`)에는 넣지 않는다** — 이것이 위 회귀 테스트가 지키는 것이다.

import에 `Draft`가 이미 있고, `RaidDeck`·`DraftAllocation`·`BossProfile`도 이미 있다.

- [ ] **Step 4: Fill the field for profiles stored before it existed**

`frontend/src/hooks/useProfiles.ts`의 `migrate` 안, `migrated[...] = { ...profile, area }` 줄을 바꾼다:

```ts
    migrated[profileKey(profile.openId, area)] = {
      ...profile,
      area,
      // 이 필드가 생기기 전에 저장된 프로필은 없다. 여기서 한 번 채우면 읽는
      // 쪽마다 `?? []`를 흩뿌리지 않아도 된다.
      savedRuns: profile.savedRuns ?? [],
    }
```

`migrate`의 타입 주석(`profiles?: Record<string, Profile & { area?: number }>`)을 `Profile & { area?: number; savedRuns?: SavedRun[] }`로 넓힌다.

`frontend/src/hooks/useProfiles.test.ts`에 추가:

```ts
it('fills savedRuns for a profile stored before the field existed', () => {
  localStorage.setItem('nikke-profiles', JSON.stringify({
    activeKey: 'a:81',
    profiles: { 'a:81': { openId: 'a', area: 81, nickname: 'A', roster: [], results: {}, lastResultHash: null, lastInputs: null } },
  }))
  const { result } = renderHook(() => useProfiles())
  expect(result.current.activeProfile?.savedRuns).toEqual([])
})
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd frontend && npx vitest run src/types/profile.test.ts src/hooks/useProfiles.test.ts`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add frontend/src/types/profile.ts frontend/src/types/profile.test.ts frontend/src/hooks/useProfiles.ts frontend/src/hooks/useProfiles.test.ts
git commit -m "Store named result keepsakes that a roster resync does not clear"
```

---

### Task 8: useProfiles에 보관 동작 얹기

**Files:**
- Modify: `frontend/src/hooks/useProfiles.ts`
- Test: `frontend/src/hooks/useProfiles.test.ts`

**Interfaces:**
- Consumes: Task 7의 `saveRun`/`renameRun`/`deleteRun`/`makeRunId`/`SavedRun`
- Produces: `Profiles`에 세 메서드 추가
  - `saveRun: (args: { key: string; run: SavedRun }) => boolean` — 상한 초과면 `false`
  - `renameRun: (args: { key: string; id: string; name: string }) => void`
  - `deleteRun: (args: { key: string; id: string }) => void`

- [ ] **Step 1: Write the failing test**

`frontend/src/hooks/useProfiles.test.ts`에 추가:

```ts
it('reports a refused save so the caller can tell the user', () => {
  const { result } = renderHook(() => useProfiles())
  act(() => {
    result.current.upsertProfile({ openId: 'a', area: 81, nickname: 'A', roster: [] })
  })
  const key = 'a:81'
  let accepted = true
  for (let i = 0; i < SAVED_RUNS_CAP; i++) {
    act(() => {
      result.current.saveRun({ key, run: { ...runFixture(), id: `${i}` } })
    })
  }
  act(() => {
    accepted = result.current.saveRun({ key, run: { ...runFixture(), id: 'over' } })
  })
  expect(accepted).toBe(false)
  expect(result.current.activeProfile?.savedRuns).toHaveLength(SAVED_RUNS_CAP)
})
```

`runFixture()`는 Task 7의 `soloRun()`과 같은 모양으로 이 파일에 만든다.

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npx vitest run src/hooks/useProfiles.test.ts`
Expected: FAIL — `result.current.saveRun`이 없다

- [ ] **Step 3: Write the implementation**

`frontend/src/hooks/useProfiles.ts`:

```ts
  /** 상한에 걸려 거절됐는지를 돌려준다 - 저장이 조용히 안 되는 화면을 만들지
   * 않기 위해서다. setState 콜백 밖에서 현재 상태를 읽어 판정한다. */
  const keepRun = useCallback(
    (args: { key: string; run: SavedRun }): boolean => {
      let accepted = false
      setState((current) => {
        const next = pureSaveRun(current, args.key, args.run)
        accepted = next !== current
        return next
      })
      return accepted
    },
    [],
  )
```

`accepted`를 setState 콜백 안에서 쓰는 것이 React StrictMode의 이중 호출에 안전한지 주의한다 — 이중 호출되어도 같은 판정을 두 번 내리므로 값은 같다.

`renameRun`/`deleteRun`은 `switchTo`와 같은 모양의 단순 래퍼다:

```ts
  const rename = useCallback((args: { key: string; id: string; name: string }) => {
    setState((current) => pureRenameRun(current, args.key, args.id, args.name))
  }, [])

  const removeRun = useCallback((args: { key: string; id: string }) => {
    setState((current) => pureDeleteRun(current, args.key, args.id))
  }, [])
```

import는 `saveRun as pureSaveRun`, `renameRun as pureRenameRun`, `deleteRun as pureDeleteRun` 형태로 — 파일이 이미 `saveResult as pureSaveResult`로 같은 관례를 쓴다. `Profiles` 인터페이스와 반환 객체에 셋을 더한다(`saveRun: keepRun`, `renameRun: rename`, `deleteRun: removeRun`).

- [ ] **Step 4: Run test to verify it passes**

Run: `cd frontend && npx vitest run src/hooks/useProfiles.test.ts`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/src/hooks/useProfiles.ts frontend/src/hooks/useProfiles.test.ts
git commit -m "Expose keeping, renaming and dropping saved runs from the profile hook"
```

---

### Task 9: SavedRunList 컴포넌트

**Files:**
- Create: `frontend/src/components/SavedRunList.tsx`
- Create: `frontend/src/components/SavedRunList.test.tsx`
- Modify: `frontend/src/App.css`

**Interfaces:**
- Consumes: Task 7의 `SavedRun`
- Produces:

```ts
interface SavedRunListProps {
  runs: SavedRun[]
  /** 펼친 항목의 결과를 그린다. 어떤 뷰냐에 따라 다른 컴포넌트가 나오므로
   * 그리는 일 자체는 탭이 맡는다. */
  renderRun: (run: SavedRun) => ReactNode
  onRestore: (run: SavedRun) => void
  onRename: (id: string, name: string) => void
  onDelete: (id: string) => void
}
```

- [ ] **Step 1: Write the failing tests**

`frontend/src/components/SavedRunList.test.tsx`:

```tsx
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { SavedRunList } from './SavedRunList'
import type { SavedRun } from '../types/profile'

const run = (overrides: Partial<SavedRun> = {}): SavedRun => ({
  id: 'r1',
  name: '작열 · 전부 최적화 · 08-06',
  savedAt: 1754438400000,
  tab: 'solo',
  view: {
    mode: 'raid',
    boss: {
      element: 'Fire', core_hittable: false, pierce_hits_body_behind_core: false,
      enemy_def: 31784, fight_duration: 180, part_destructible: false,
      effective_range_band: null, elemental_interrupt_required: false,
    },
    numDecks: 5, decks: [], combinedTotalDamage: 1,
    excludedSlugs: [], leftoverSlugs: [],
  },
  ...overrides,
})

const noop = () => {}

describe('SavedRunList', () => {
  it('says so when there is nothing kept', () => {
    render(<SavedRunList runs={[]} renderRun={() => null} onRestore={noop} onRename={noop} onDelete={noop} />)
    expect(screen.getByText(/저장한 결과가 없어요/)).toBeInTheDocument()
  })

  it('keeps a run folded until it is opened', async () => {
    render(
      <SavedRunList
        runs={[run()]}
        renderRun={() => <p>결과 내용</p>}
        onRestore={noop} onRename={noop} onDelete={noop}
      />,
    )
    expect(screen.queryByText('결과 내용')).not.toBeInTheDocument()
    await userEvent.click(screen.getByRole('button', { name: /작열 · 전부 최적화/ }))
    expect(screen.getByText('결과 내용')).toBeInTheDocument()
  })

  it('restores only when asked, not on opening', async () => {
    const onRestore = vi.fn()
    render(
      <SavedRunList
        runs={[run()]}
        renderRun={() => <p>결과 내용</p>}
        onRestore={onRestore} onRename={noop} onDelete={noop}
      />,
    )
    await userEvent.click(screen.getByRole('button', { name: /작열 · 전부 최적화/ }))
    expect(onRestore).not.toHaveBeenCalled()
    await userEvent.click(screen.getByRole('button', { name: '이 설정으로 폼 채우기' }))
    expect(onRestore).toHaveBeenCalledWith(run())
  })

  it('asks before dropping one', async () => {
    const onDelete = vi.fn()
    const confirmSpy = vi.spyOn(window, 'confirm').mockReturnValue(false)
    render(
      <SavedRunList
        runs={[run()]}
        renderRun={() => null}
        onRestore={noop} onRename={noop} onDelete={onDelete}
      />,
    )
    await userEvent.click(screen.getByRole('button', { name: /작열 · 전부 최적화/ }))
    await userEvent.click(screen.getByRole('button', { name: '삭제' }))
    expect(onDelete).not.toHaveBeenCalled()
    confirmSpy.mockReturnValue(true)
    await userEvent.click(screen.getByRole('button', { name: '삭제' }))
    expect(onDelete).toHaveBeenCalledWith('r1')
    confirmSpy.mockRestore()
  })

  it('renames through an inline field', async () => {
    const onRename = vi.fn()
    render(
      <SavedRunList
        runs={[run()]}
        renderRun={() => null}
        onRestore={noop} onRename={onRename} onDelete={noop}
      />,
    )
    await userEvent.click(screen.getByRole('button', { name: /작열 · 전부 최적화/ }))
    await userEvent.click(screen.getByRole('button', { name: '이름 바꾸기' }))
    const field = screen.getByLabelText('이름')
    await userEvent.clear(field)
    await userEvent.type(field, '새 이름')
    await userEvent.click(screen.getByRole('button', { name: '확인' }))
    expect(onRename).toHaveBeenCalledWith('r1', '새 이름')
  })
})
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd frontend && npx vitest run src/components/SavedRunList.test.tsx`
Expected: FAIL — `./SavedRunList` 모듈이 없다

- [ ] **Step 3: Write the implementation**

`frontend/src/components/SavedRunList.tsx`:

```tsx
// 이름 붙여 남겨 둔 결과들. 항목을 열면 그 자리에서 결과를 읽기 모드로 펼치고,
// 지금 화면에 떠 있는 계산 결과는 건드리지 않는다 - 폼이 바뀌는 것은 유저가
// "이 설정으로 폼 채우기"를 눌렀을 때뿐이다.
//
// 결과를 그리는 일은 renderRun에 맡긴다: 솔로 네 모드와 유니온이 서로 다른
// 컴포넌트로 그려지는데, 그 분기는 각 탭이 이미 하고 있다.

import { useId, useState, type ReactNode } from 'react'
import type { SavedRun } from '../types/profile'

const savedAtLabel = (savedAt: number): string => {
  const at = new Date(savedAt)
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${pad(at.getMonth() + 1)}-${pad(at.getDate())} ${pad(at.getHours())}:${pad(at.getMinutes())}`
}

interface SavedRunListProps {
  runs: SavedRun[]
  renderRun: (run: SavedRun) => ReactNode
  onRestore: (run: SavedRun) => void
  onRename: (id: string, name: string) => void
  onDelete: (id: string) => void
}

export function SavedRunList({ runs, renderRun, onRestore, onRename, onDelete }: SavedRunListProps) {
  const [openId, setOpenId] = useState<string | null>(null)
  const [renamingId, setRenamingId] = useState<string | null>(null)
  const [renameValue, setRenameValue] = useState('')
  const renameFieldId = useId()

  if (runs.length === 0) {
    return <p className="empty__text">저장한 결과가 없어요.</p>
  }

  const startRename = (run: SavedRun) => {
    setRenamingId(run.id)
    setRenameValue(run.name)
  }

  const commitRename = (id: string) => {
    const name = renameValue.trim()
    if (name !== '') onRename(id, name)
    setRenamingId(null)
  }

  return (
    <ul className="saved-runs">
      {runs.map((run) => (
        <li key={run.id} className="saved-runs__item">
          <button
            type="button"
            className="saved-runs__open"
            aria-expanded={openId === run.id}
            onClick={() => setOpenId(openId === run.id ? null : run.id)}
          >
            <span className="saved-runs__name">{run.name}</span>
            <span className="saved-runs__when">{savedAtLabel(run.savedAt)}</span>
          </button>

          {openId === run.id && (
            <div className="saved-runs__body">
              <div className="saved-runs__actions">
                <button type="button" className="btn" onClick={() => onRestore(run)}>
                  이 설정으로 폼 채우기
                </button>
                <button type="button" className="btn" onClick={() => startRename(run)}>
                  이름 바꾸기
                </button>
                <button
                  type="button"
                  className="btn"
                  onClick={() => {
                    if (window.confirm(`"${run.name}"을(를) 삭제할까요?`)) onDelete(run.id)
                  }}
                >
                  삭제
                </button>
              </div>

              {renamingId === run.id && (
                <div className="field">
                  <label className="field__label" htmlFor={renameFieldId}>
                    이름
                  </label>
                  <input
                    id={renameFieldId}
                    className="field__input"
                    value={renameValue}
                    onChange={(event) => setRenameValue(event.target.value)}
                  />
                  <div className="saved-runs__actions">
                    <button type="button" className="btn" onClick={() => commitRename(run.id)}>
                      확인
                    </button>
                    <button type="button" className="btn" onClick={() => setRenamingId(null)}>
                      취소
                    </button>
                  </div>
                </div>
              )}

              {renderRun(run)}
            </div>
          )}
        </li>
      ))}
    </ul>
  )
}
```

- [ ] **Step 4: Add the stylesheet rules**

`frontend/src/App.css` 맨 아래에 추가:

```css
/* 보관 목록 ------------------------------------------------------------- */

.saved-runs {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: var(--sp-2);
  width: 100%;
}

.saved-runs__item {
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
}

.saved-runs__open {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: var(--sp-3);
  width: 100%;
  padding: var(--sp-2) var(--sp-3);
  background: none;
  border: 0;
  color: inherit;
  font: inherit;
  text-align: left;
  cursor: pointer;
}

.saved-runs__name {
  font-weight: 600;
}

.saved-runs__when {
  font-size: 12px;
  color: var(--text-muted);
  font-variant-numeric: tabular-nums;
}

.saved-runs__body {
  padding: 0 var(--sp-3) var(--sp-3);
  display: flex;
  flex-direction: column;
  gap: var(--sp-3);
}

.saved-runs__actions {
  display: flex;
  flex-wrap: wrap;
  gap: var(--sp-2);
}
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd frontend && npx vitest run src/components/SavedRunList.test.tsx`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/SavedRunList.tsx frontend/src/components/SavedRunList.test.tsx frontend/src/App.css
git commit -m "Add the saved-run list: fold, open read-only, restore on request"
```

---

### Task 10: SaveRunButton — 이름 붙여 저장하는 컨트롤

**Files:**
- Create: `frontend/src/components/SaveRunButton.tsx`
- Create: `frontend/src/components/SaveRunButton.test.tsx`

**Interfaces:**
- Produces:

```ts
interface SaveRunButtonProps {
  /** 이름 칸에 미리 채워 넣을 제안. */
  suggestedName: string
  /** 확인된 이름으로 저장한다. 상한에 걸려 거절되면 false. */
  onSave: (name: string) => boolean
}
```

- [ ] **Step 1: Write the failing tests**

`frontend/src/components/SaveRunButton.test.tsx`:

```tsx
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { SaveRunButton } from './SaveRunButton'

describe('SaveRunButton', () => {
  it('opens a name field prefilled with the suggestion', async () => {
    render(<SaveRunButton suggestedName="작열 · 전부 최적화 · 08-06" onSave={() => true} />)
    await userEvent.click(screen.getByRole('button', { name: '저장' }))
    expect(screen.getByLabelText('이름')).toHaveValue('작열 · 전부 최적화 · 08-06')
  })

  it('saves the edited name and closes', async () => {
    const onSave = vi.fn(() => true)
    render(<SaveRunButton suggestedName="제안" onSave={onSave} />)
    await userEvent.click(screen.getByRole('button', { name: '저장' }))
    const field = screen.getByLabelText('이름')
    await userEvent.clear(field)
    await userEvent.type(field, '내 이름')
    await userEvent.click(screen.getByRole('button', { name: '확인' }))
    expect(onSave).toHaveBeenCalledWith('내 이름')
    expect(screen.queryByLabelText('이름')).not.toBeInTheDocument()
  })

  it('will not save an empty name', async () => {
    const onSave = vi.fn(() => true)
    render(<SaveRunButton suggestedName="제안" onSave={onSave} />)
    await userEvent.click(screen.getByRole('button', { name: '저장' }))
    await userEvent.clear(screen.getByLabelText('이름'))
    await userEvent.click(screen.getByRole('button', { name: '확인' }))
    expect(onSave).not.toHaveBeenCalled()
  })

  it('stays open and explains when the store refuses', async () => {
    render(<SaveRunButton suggestedName="제안" onSave={() => false} />)
    await userEvent.click(screen.getByRole('button', { name: '저장' }))
    await userEvent.click(screen.getByRole('button', { name: '확인' }))
    expect(screen.getByRole('alert')).toHaveTextContent(/50개/)
    expect(screen.getByLabelText('이름')).toBeInTheDocument()
  })
})
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd frontend && npx vitest run src/components/SaveRunButton.test.tsx`
Expected: FAIL — 모듈이 없다

- [ ] **Step 3: Write the implementation**

`frontend/src/components/SaveRunButton.tsx`:

```tsx
// 화면에 떠 있는 결과에 이름을 붙여 남긴다. 저장이 거절될 수 있으므로(보관
// 상한) 확인 후에도 칸을 닫지 않고 이유를 말한다 - 눌렀는데 아무 일도 안 나는
// 화면을 만들지 않기 위해서다.

import { useId, useState } from 'react'
import { SAVED_RUNS_CAP } from '../types/profile'

interface SaveRunButtonProps {
  suggestedName: string
  onSave: (name: string) => boolean
}

export function SaveRunButton({ suggestedName, onSave }: SaveRunButtonProps) {
  const [open, setOpen] = useState(false)
  const [name, setName] = useState('')
  const [refused, setRefused] = useState(false)
  const fieldId = useId()

  const start = () => {
    setName(suggestedName)
    setRefused(false)
    setOpen(true)
  }

  const commit = () => {
    const trimmed = name.trim()
    if (trimmed === '') return
    if (onSave(trimmed)) {
      setOpen(false)
      return
    }
    setRefused(true)
  }

  if (!open) {
    return (
      <button type="button" className="btn" onClick={start}>
        저장
      </button>
    )
  }

  return (
    <span className="save-run">
      <label className="visually-hidden" htmlFor={fieldId}>
        이름
      </label>
      <input
        id={fieldId}
        className="field__input"
        value={name}
        onChange={(event) => setName(event.target.value)}
      />
      <button type="button" className="btn" onClick={commit}>
        확인
      </button>
      <button type="button" className="btn" onClick={() => setOpen(false)}>
        취소
      </button>
      {refused && (
        <span className="field__error" role="alert">
          보관은 {SAVED_RUNS_CAP}개까지예요. 목록에서 몇 개를 지우고 다시 저장해주세요.
        </span>
      )}
    </span>
  )
}
```

`frontend/src/App.css`에 추가:

```css
.save-run {
  display: inline-flex;
  flex-wrap: wrap;
  align-items: center;
  gap: var(--sp-2);
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd frontend && npx vitest run src/components/SaveRunButton.test.tsx`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add frontend/src/components/SaveRunButton.tsx frontend/src/components/SaveRunButton.test.tsx frontend/src/App.css
git commit -m "Add the name-it-and-keep-it control for a displayed result"
```

---

### Task 11: 솔로 탭 배선

**Files:**
- Modify: `frontend/src/components/RecommendPanel.tsx`
- Modify: `frontend/src/App.tsx:169-188`
- Test: `frontend/src/components/RecommendPanel.test.tsx`

**Interfaces:**
- Consumes: Task 8의 훅 메서드, Task 9 `SavedRunList`, Task 10 `SaveRunButton`, Task 7 `SoloRunView`/`runsForTab`/`makeRunId`
- Produces: `RecommendPanel`에 새 props
  - `savedRuns: SavedRun[]`
  - `onSaveRun: (run: SavedRun) => boolean`
  - `onRenameRun: (id: string, name: string) => void`
  - `onDeleteRun: (id: string) => void`

- [ ] **Step 1: Write the failing test**

`frontend/src/components/RecommendPanel.test.tsx`에 추가:

```tsx
it('keeps the displayed result under a name and lists it', async () => {
  const saved: SavedRun[] = []
  renderPanel({
    savedRuns: saved,
    onSaveRun: (run: SavedRun) => { saved.push(run); return true },
  })
  await userEvent.click(screen.getByRole('radio', { name: /작열/ }))
  await userEvent.click(screen.getByRole('button', { name: '인카운터!' }))
  await screen.findByText(/약점 작열/)
  await userEvent.click(screen.getByRole('button', { name: '저장' }))
  await userEvent.click(screen.getByRole('button', { name: '확인' }))
  expect(saved).toHaveLength(1)
  expect(saved[0].tab).toBe('solo')
  expect(saved[0].view).toMatchObject({ mode: 'single' })
})

it('offers no save button before there is a result', () => {
  renderPanel()
  expect(screen.queryByRole('button', { name: '저장' })).not.toBeInTheDocument()
})
```

`renderPanel`이 인자를 받지 않는 헬퍼라면 오버라이드를 받도록 넓힌다(다른 테스트는 기본값으로 그대로 통과해야 한다).

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npx vitest run src/components/RecommendPanel.test.tsx`
Expected: FAIL — 저장 버튼이 없다

- [ ] **Step 3: Write the implementation — 저장할 뷰를 만든다**

`frontend/src/components/RecommendPanel.tsx`에 헬퍼를 추가한다. 네 모드가 각자 무엇을 들고 있는지가 여기 한 곳에 모인다:

```tsx
const MODE_LABEL: Record<RecommendMode, string> = {
  single: '단일 덱',
  raid: '전부 최적화',
  draft: '빈자리만 최적화',
  evaluate: '기대 딜량 계산',
}

/** 저장 이름 제안. 무엇을 상대로 어떤 모드로 돌렸는지가 나중에 목록에서
 * 고르는 단서다. */
const suggestRunName = (boss: BossProfile, mode: RecommendMode, at: Date): string => {
  const weakness = boss.element === null ? '약점 없음' : elementLabel(weaknessFor(boss.element))
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${weakness} · ${MODE_LABEL[mode]} · ${pad(at.getMonth() + 1)}-${pad(at.getDate())}`
}
```

`elementLabel` import를 추가한다(`weaknessFor`는 이미 있다).

화면에 떠 있는 결과를 `SoloRunView`로 모으는 값을 `useMemo`로 만든다. 네 모드 중 지금 보이는 것 하나만 값을 낸다:

```tsx
  // 지금 화면에 떠 있는 결과를 보관 가능한 모양으로. 없으면 null이고,
  // 그러면 저장 버튼도 없다. 모드별 판정은 displayedBoss와 같은 규칙이다.
  const displayedRun = useMemo<SoloRunView | null>(() => {
    if (mode === 'single') {
      if (single.status !== 'success' || !singleBoss) return null
      return {
        mode: 'single',
        boss: singleBoss,
        numDecks,
        decks: single.decks,
        excludedSlugs: single.excludedSlugs,
      }
    }
    if (mode === 'raid' || mode === 'draft') {
      if (!displayResult || displayMode !== mode || !displayBoss) return null
      const shared = {
        boss: displayBoss,
        numDecks,
        decks: displayResult.decks,
        combinedTotalDamage: displayResult.combinedTotalDamage,
        excludedSlugs: displayResult.excludedSlugs,
        leftoverSlugs: displayResult.leftoverSlugs,
        swapConverged: displayResult.swapConverged,
      }
      return mode === 'raid'
        ? { mode: 'raid', ...shared }
        : {
            mode: 'draft',
            ...shared,
            withinDraft: displayResult.withinDraft,
            baselineTotalDamage: displayResult.baselineTotalDamage,
            draft: submittedDraft ?? null,
          }
    }
    if (evaluation.status !== 'success' || !evaluateBoss) return null
    return {
      mode: 'evaluate',
      boss: evaluateBoss,
      numDecks,
      decks: evaluation.decks,
      combinedTotalDamage: evaluation.combinedTotalDamage,
      excludedSlugs: evaluation.excludedSlugs,
      draft: draftValue,
    }
  }, [
    mode,
    single.status,
    single.decks,
    single.excludedSlugs,
    singleBoss,
    displayResult,
    displayMode,
    displayBoss,
    submittedDraft,
    evaluation.status,
    evaluation.decks,
    evaluation.combinedTotalDamage,
    evaluation.excludedSlugs,
    evaluateBoss,
    numDecks,
    draftValue,
  ])
```

Task 5의 `displayedBoss`는 이제 여기서 파생시킨다 — 같은 판정을 두 번 쓰지 않는다:

```tsx
  const displayedBoss = displayedRun?.boss ?? null
```

Task 5에서 넣은 `displayedBoss` useMemo 블록은 지운다. `<BossSummary boss={displayedBoss} />`
줄은 아래 Step 4에서 저장 버튼과 한 행으로 묶인다.

`single.decks`와 `evaluation.decks`는 `DeckRecommendation[]`, `displayResult.decks`는
`RaidDeck[]`이다 — 판별 유니온의 각 갈래가 이미 맞는 쪽을 선언하고 있으므로 캐스팅이
필요 없다.

- [ ] **Step 4: Write the implementation — 화면에 건다**

Task 5에서 놓은 `{displayedBoss && <BossSummary boss={displayedBoss} />}` 한 줄을 저장 버튼과 한 행으로 묶는다:

```tsx
        {displayedRun && (
          <div className="result-head">
            <BossSummary boss={displayedRun.boss} />
            <SaveRunButton
              suggestedName={suggestRunName(displayedRun.boss, displayedRun.mode, new Date())}
              onSave={(name) => {
                const savedAt = Date.now()
                return onSaveRun({
                  id: makeRunId(savedAt, savedRuns),
                  name,
                  savedAt,
                  tab: 'solo',
                  view: displayedRun,
                })
              }}
            />
          </div>
        )}
```

결과들 아래, `사용할 유닛` fieldset 위에 목록을 놓는다:

```tsx
        <fieldset className="group">
          <legend className="group__legend">저장한 결과 ({savedRuns.length})</legend>
          <details className="group__details">
            <summary className="group__hint">이름을 눌러 그때의 결과를 다시 볼 수 있어요</summary>
            <SavedRunList
              runs={savedRuns}
              renderRun={(run) => renderSavedSoloRun(run)}
              onRestore={restoreRun}
              onRename={onRenameRun}
              onDelete={onDeleteRun}
            />
          </details>
        </fieldset>
```

`renderSavedSoloRun`은 뷰의 `mode`로 갈라 기존 결과 컴포넌트를 읽기 모드로 그린다:

```tsx
  const renderSavedSoloRun = (run: SavedRun) => {
    const view = run.view as SoloRunView
    const lookups = { portraitFor, nameFor }
    return (
      <>
        <BossSummary boss={view.boss} />
        {view.mode === 'single' && <DeckResults decks={view.decks} excludedSlugs={view.excludedSlugs} {...lookups} />}
        {view.mode === 'raid' && (
          <RaidResults
            decks={view.decks}
            combinedTotalDamage={view.combinedTotalDamage}
            excludedSlugs={view.excludedSlugs}
            leftoverSlugs={view.leftoverSlugs}
            swapConverged={view.swapConverged}
            {...lookups}
          />
        )}
        {view.mode === 'draft' && (
          <DraftResults
            decks={view.decks}
            combinedTotalDamage={view.combinedTotalDamage}
            excludedSlugs={view.excludedSlugs}
            leftoverSlugs={view.leftoverSlugs}
            withinDraft={view.withinDraft}
            baselineTotalDamage={view.baselineTotalDamage}
            submittedDraft={view.draft ?? undefined}
            ownedSlugFor={ownedSlugResolver}
            {...lookups}
          />
        )}
        {view.mode === 'evaluate' && (
          <EvaluationResults
            decks={view.decks}
            combinedTotalDamage={view.combinedTotalDamage}
            excludedSlugs={view.excludedSlugs}
            bosses={view.decks.map(() => view.boss)}
            {...lookups}
          />
        )}
      </>
    )
  }
```

`gimmickUnmetFor`는 넘기지 않는다 — 그 판정은 현재 로스터의 속성으로 내리는 것이라, 그때의 로스터로 나온 결과에 지금 기준을 덧씌우면 거짓말이 된다.

폼 복원:

```tsx
  /** 보관물을 여는 것만으로는 폼이 바뀌지 않는다. 이 버튼을 눌렀을 때만
   * 그때의 설정으로 되돌린다 - 결과는 되돌리지 않는다(다시 돌리는 것이 목적이다). */
  const restoreRun = (run: SavedRun) => {
    const view = run.view as SoloRunView
    setMode(view.mode)
    setNumDecks(view.numDecks)
    setDraft(bossProfileToDraft(view.boss))
    // 편성은 draft/evaluate 갈래에만 있다.
    if ('draft' in view && view.draft) setDraftValue(view.draft)
  }
```

`frontend/src/App.css`에 추가:

```css
/* 보스 요약과 저장 버튼이 결과의 첫 줄을 나눠 쓴다. */
.result-head {
  display: flex;
  flex-wrap: wrap;
  align-items: baseline;
  justify-content: space-between;
  gap: var(--sp-2) var(--sp-3);
  width: 100%;
}
```

- [ ] **Step 5: Wire the props from App.tsx**

`frontend/src/App.tsx`의 `<RecommendPanel …>`에 추가한다. `useProfiles`에서 세 메서드를 꺼내고:

```tsx
                savedRuns={activeProfile ? runsForTab(activeProfile, 'solo') : []}
                onSaveRun={(run) =>
                  state.activeKey ? saveRun({ key: state.activeKey, run }) : false
                }
                onRenameRun={(id, name) => {
                  if (state.activeKey) renameRun({ key: state.activeKey, id, name })
                }}
                onDeleteRun={(id) => {
                  if (state.activeKey) deleteRun({ key: state.activeKey, id })
                }}
```

`import { getResult, runsForTab } from './types/profile'`로 넓힌다.

- [ ] **Step 6: Run tests to verify they pass**

Run: `cd frontend && npx vitest run src/components/RecommendPanel.test.tsx src/App.test.tsx`
Expected: PASS

- [ ] **Step 7: Commit**

```bash
git add frontend/src/components/RecommendPanel.tsx frontend/src/components/RecommendPanel.test.tsx frontend/src/App.tsx frontend/src/App.css
git commit -m "Let the solo tab keep, list and reopen its results"
```

---

### Task 12: 유니온 탭 배선

**Files:**
- Modify: `frontend/src/components/UnionRaidPanel.tsx`
- Modify: `frontend/src/App.tsx:197-208`
- Test: `frontend/src/components/UnionRaidPanel.test.tsx`

**Interfaces:**
- Consumes: Task 8·9·10, Task 7의 `UnionRunView`
- Produces: `UnionRaidPanel`에 `savedRuns`/`onSaveRun`/`onRenameRun`/`onDeleteRun` — 솔로와 같은 시그니처

- [ ] **Step 1: Write the failing test**

`frontend/src/components/UnionRaidPanel.test.tsx`에 추가:

```tsx
it('keeps a union result under the union tab, never the solo one', async () => {
  const saved: SavedRun[] = []
  renderPanel({
    savedRuns: saved,
    onSaveRun: (run: SavedRun) => { saved.push(run); return true },
  })
  await submitFullEncounter()   // 이 파일의 기존 헬퍼 관례를 따른다
  await userEvent.click(screen.getByRole('button', { name: '저장' }))
  await userEvent.click(screen.getByRole('button', { name: '확인' }))
  expect(saved).toHaveLength(1)
  expect(saved[0].tab).toBe('union')
})
```

이 파일에 전체 편성을 채우고 제출하는 헬퍼가 없으면, 기존 테스트가 쓰는 방식을 그대로 옮겨 하나 만든다.

- [ ] **Step 2: Run test to verify it fails**

Run: `cd frontend && npx vitest run src/components/UnionRaidPanel.test.tsx`
Expected: FAIL

- [ ] **Step 3: Write the implementation**

`frontend/src/components/UnionRaidPanel.tsx`:

```tsx
  // 화면에 떠 있는 유니온 결과. 보스는 제출 시점 스냅샷(evaluatedBosses)이다.
  const displayedRun = useMemo<UnionRunView | null>(() => {
    if (evaluation.status !== 'success') return null
    return {
      numBattles,
      bosses: evaluatedBosses,
      draft: draftValue,
      decks: evaluation.decks,
      combinedTotalDamage: evaluation.combinedTotalDamage,
      excludedSlugs: evaluation.excludedSlugs,
    }
  }, [evaluation, evaluatedBosses, draftValue, numBattles])
```

`EvaluationResults` 바로 위에 저장 줄을 놓는다:

```tsx
        {evaluation.status === 'success' && displayedRun && (
          <div className="result-head">
            <span className="saved-runs__name">유니온 레이드 {numBattles}전투</span>
            <SaveRunButton
              suggestedName={suggestUnionRunName(new Date(), numBattles)}
              onSave={(name) => {
                const savedAt = Date.now()
                return onSaveRun({
                  id: makeRunId(savedAt, savedRuns),
                  name,
                  savedAt,
                  tab: 'union',
                  view: displayedRun,
                })
              }}
            />
          </div>
        )}
```

이름 제안 헬퍼를 파일 상단에 둔다:

```tsx
/** 유니온은 전투마다 보스가 달라 하나를 이름에 뽑을 수 없다 — 전투 수와 날짜로
 * 구분한다. */
const suggestUnionRunName = (at: Date, numBattles: number): string => {
  const pad = (n: number) => String(n).padStart(2, '0')
  return `유니온 ${numBattles}전투 · ${pad(at.getMonth() + 1)}-${pad(at.getDate())}`
}
```

편성 fieldset 아래에 목록을 놓는다:

```tsx
        <fieldset className="group">
          <legend className="group__legend">저장한 결과 ({savedRuns.length})</legend>
          <details className="group__details">
            <summary className="group__hint">이름을 눌러 그때의 결과를 다시 볼 수 있어요</summary>
            <SavedRunList
              runs={savedRuns}
              renderRun={(run) => {
                const view = run.view as UnionRunView
                return (
                  <EvaluationResults
                    decks={view.decks}
                    combinedTotalDamage={view.combinedTotalDamage}
                    excludedSlugs={view.excludedSlugs}
                    bosses={view.bosses}
                    portraitFor={portraitFor}
                    nameFor={nameFor}
                  />
                )
              }}
              onRestore={(run) => {
                const view = run.view as UnionRunView
                changeNumBattles(view.numBattles)
                setBosses(view.bosses.map(bossProfileToDraft))
                setDraftValue(view.draft)
              }}
              onRename={onRenameRun}
              onDelete={onDeleteRun}
            />
          </details>
        </fieldset>
```

`changeNumBattles`가 `bosses`/`draftValue`도 함께 바꾸므로, 그 뒤에 오는 두 setState가 최종 값을 쥔다 — React가 셋을 한 렌더로 묶는다.

`bossProfileToDraft` import를 추가한다.

- [ ] **Step 4: Wire the props from App.tsx**

`<UnionRaidPanel …>`에 솔로와 같은 네 prop을 넘기되 `runsForTab(activeProfile, 'union')`을 쓴다.

- [ ] **Step 5: Run tests to verify they pass**

Run: `cd frontend && npx vitest run src/components/UnionRaidPanel.test.tsx src/App.test.tsx`
Expected: PASS

- [ ] **Step 6: Commit**

```bash
git add frontend/src/components/UnionRaidPanel.tsx frontend/src/components/UnionRaidPanel.test.tsx frontend/src/App.tsx
git commit -m "Let the union tab keep its own results, apart from the solo tab's"
```

---

### Task 13: 전체 스위트 · 육안 확인 · 문서

**Files:**
- Modify: `docs/roadmap.md`
- Modify: `docs/insights.md` (필요할 때만)

- [ ] **Step 1: Run the whole suite**

Run: `cd frontend && npm test -- --run`
Expected: 524개보다 많고, 실패 0

- [ ] **Step 2: Typecheck and lint**

Run: `cd frontend && npx tsc --noEmit && npm run lint`
Expected: 오류 없음. `npm run lint` 스크립트가 없으면 그 단계는 건너뛴다.

- [ ] **Step 3: 앱을 띄워 눈으로 본다**

CSS는 단위 테스트에 보이지 않는다. 백엔드와 프론트 두 서버가 필요하다:

```bash
# 하나의 터미널
cd backend && uvicorn app.api:app --port 8000
# 다른 터미널
cd frontend && npm run dev
```

확인할 것:
1. 솔로 탭 보스 폼의 방어력이 31,784로 시작하고, "기타 설정"이 접혀 있으며 요약에 그 값이 보인다
2. 유니온 탭 보스 폼의 방어력은 0이다
3. 결과를 하나 돌리고(단일 덱이 가장 빠르다) 창을 넓혔다 좁혔다 하며 덱 카드가 2·3열로 재배치되는지, 좁을 때 1열로 돌아오는지 본다
4. 결과 위에 보스 요약 한 줄이 있고 오른쪽 끝에 저장 버튼이 있다
5. 저장 → 목록에 나타남 → 열면 결과가 다시 보임 → "이 설정으로 폼 채우기"를 누르면 폼이 바뀐다
6. 유니온 탭의 저장 목록에 솔로에서 저장한 것이 **없다**

- [ ] **Step 4: Update the roadmap**

`docs/roadmap.md`의 To-Do에서 이 작업에 해당하는 항목을 체크하거나, 없으면 완료 항목으로 한 줄 추가한다.

- [ ] **Step 5: Commit**

```bash
git add docs/roadmap.md
git commit -m "Record the result-view and saved-runs work in the roadmap"
```

---

## Self-Review

**Spec coverage** — 스펙의 다섯 항목이 각각 Task 1 / Task 2 / Task 3 / Task 4-6 / Task 7-12에 대응한다. 스펙의 "하지 않는 것" 넷은 어느 태스크에도 없다(의도한 바다).

**Type consistency** — `SavedRun`·`SoloRunView`·`UnionRunView`·`SAVED_RUNS_CAP`·`makeRunId`·`saveRun`·`renameRun`·`deleteRun`·`runsForTab`는 Task 7에서 정의되고 Task 8·9·10·11·12가 그 이름 그대로 쓴다. `SaveRunButton.onSave`는 Task 10에서 `(name: string) => boolean`이고 Task 11·12가 같은 시그니처로 넘긴다. `EvaluationResults`의 `bosses`는 Task 6에서 바뀌고 Task 11·12가 그 이름을 쓴다. Task 5의 `displayedBoss`는 Task 11에서 `displayedRun?.boss ?? null`로 파생되어, 같은 판정이 두 벌 남지 않는다.

**덱 타입** — 확인했다. `RaidDeck extends DeckRecommendation`이고 `pinned_slugs: string[]`가 **필수**다. `useRecommend`/`useEvaluateDecks`는 `DeckRecommendation[]`를, `useRecommendRaid`(`StoredResult.decks`)는 `RaidDeck[]`를 낸다. `DraftResults`만 좁은 쪽(`RaidDeck[]`)을 요구하므로, `SoloRunView`를 판별 유니온으로 두어 각 갈래가 맞는 타입을 선언한다. 캐스팅은 없다.
