# 솔로 레이드 설정 영역 재배치 — 구현 계획

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 솔로 레이드 탭의 설정 영역을 좌(보스 설정 + 모드) / 우(시즌 가이드) 2컬럼으로 다시 짜고, 보스 설정을 접어 두고, 체크박스·라디오를 토글 칩으로 바꾼다.

**Architecture:** 전부 프론트엔드다. 백엔드·API·데이터 스키마를 건드리지 않는다. 새 컴포넌트 셋(`ToggleChip` · `FightTimeline` · `SeasonGuideCard`), 새 훅 하나(`useBossGuides`, localStorage), 새 순수 함수 하나(`gimmickBadges`)를 만들고 나머지는 기존 두 컴포넌트의 기본값과 배치를 고친다.

**Tech Stack:** React 18 + TypeScript + Vite · Vitest + @testing-library/react + userEvent · 순수 CSS(`frontend/src/App.css`, 토큰은 `index.css`)

**Spec:** `docs/superpowers/specs/2026-08-20-solo-raid-setup-layout-design.md`

## Global Constraints

- **워크트리에는 `frontend/node_modules`가 없다.** 첫 작업 전에 `npm --prefix frontend install`을 한 번 돌린다. 없다고 회귀로 읽지 말 것.
- **테스트**: `npm --prefix frontend test -- --run` (vitest). 특정 파일만: `npm --prefix frontend test -- --run src/components/Foo.test.tsx`
- **타입체크**: `npx --prefix frontend tsc -b --noEmit frontend` — `npm --prefix frontend exec -- tsc`는 이 환경에서 실패한다.
- **vitest는 타입을 안 본다.** 테스트가 초록이어도 타입체크를 따로 돌린다.
- **CSS는 vitest에 안 보인다** (`css: false`). 시각 확인은 앱을 띄워서만 된다.
- **새 색 토큰을 만들지 않는다.** `index.css`의 기존 토큰만 쓴다.
- **모션을 넣지 않는다.** `transition`/`@keyframes`/`animation`을 새로 추가하지 않는다.
- **문구 규칙**: 빈 상태는 상태 설명이 아니라 다음 행동을 적는다. 라벨은 문장부호 없이, 안내는 마침표까지.
- **기준선**(이 계획 착수 시점, `5bb269fa`): 프론트 **970 passed / 74 files**, 타입에러 0, lint 에러 0.

---

### Task 1: `lib/bossBadges.ts` — 기믹 뱃지 규칙을 한 곳으로

**Files:**
- Create: `frontend/src/lib/bossBadges.ts`
- Create: `frontend/src/lib/bossBadges.test.ts`
- Modify: `frontend/src/components/BossSummary.tsx:23-29`

**Interfaces:**
- Consumes: 없음
- Produces: `BossGimmickFlags` (인터페이스), `gimmickBadges(boss: BossGimmickFlags): string[]`

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`frontend/src/lib/bossBadges.test.ts`:

```ts
import { describe, expect, it } from 'vitest'
import { gimmickBadges, type BossGimmickFlags } from './bossBadges'

const none: BossGimmickFlags = {
  core_hittable: false,
  pierce_hits_body_behind_core: false,
  part_destructible: false,
  spawns_adds: false,
  elemental_interrupt_required: false,
}

describe('gimmickBadges', () => {
  it('꺼진 기믹은 적지 않는다', () => {
    expect(gimmickBadges(none)).toEqual([])
  })

  it('켜진 것만 적는다', () => {
    expect(gimmickBadges({ ...none, part_destructible: true })).toEqual(['부위파괴'])
  })

  it('순서가 고정이다 - 켜진 조합이 달라져도 자리를 바꾸지 않는다', () => {
    expect(
      gimmickBadges({
        core_hittable: true,
        pierce_hits_body_behind_core: true,
        part_destructible: true,
        spawns_adds: true,
        elemental_interrupt_required: true,
      }),
    ).toEqual(['코어 피격', '2관통', '부위파괴', '잡몹 생성', '속성저지 필수'])
  })
})
```

- [ ] **Step 2: 실패를 확인한다**

Run: `npm --prefix frontend test -- --run src/lib/bossBadges.test.ts`
Expected: FAIL — `Failed to resolve import "./bossBadges"`

- [ ] **Step 3: 최소 구현**

`frontend/src/lib/bossBadges.ts`:

```ts
// 보스의 기믹을 낱말로. 결과 화면(BossSummary)과 시즌 가이드 카드가 같은 낱말을
// 써야 해서 한 곳에서 만든다 - 두 곳이 갈라지면 같은 보스가 화면마다 다른 기믹을
// 가진 것처럼 읽힌다.

/** 뱃지를 만드는 데 필요한 필드만. 결과의 `BossProfile`과 폼 상태인
 * `BossProfileDraft`가 둘 다 구조적으로 이것을 만족한다 - 둘 중 하나로 좁혀
 * 잡으면 나머지 한쪽이 못 부른다. */
export interface BossGimmickFlags {
  core_hittable: boolean
  pierce_hits_body_behind_core: boolean
  part_destructible: boolean
  spawns_adds: boolean
  elemental_interrupt_required: boolean
}

/** 켜진 기믹만. 꺼진 것까지 적으면 줄만 길어지고, 없는 것은 화면에 없는 것으로
 * 읽힌다. 순서가 고정인 이유: 보스를 바꿀 때마다 뱃지가 자리를 옮기면 읽는 눈이
 * 매번 줄 전체를 처음부터 훑어야 한다. */
export const gimmickBadges = (boss: BossGimmickFlags): string[] =>
  [
    boss.core_hittable && '코어 피격',
    boss.pierce_hits_body_behind_core && '2관통',
    boss.part_destructible && '부위파괴',
    boss.spawns_adds && '잡몹 생성',
    boss.elemental_interrupt_required && '속성저지 필수',
  ].filter((label): label is string => typeof label === 'string')
```

- [ ] **Step 4: 통과를 확인한다**

Run: `npm --prefix frontend test -- --run src/lib/bossBadges.test.ts`
Expected: PASS (3 tests)

- [ ] **Step 5: `BossSummary`가 그것을 쓰게 한다**

`frontend/src/components/BossSummary.tsx` — import에 다음을 더한다:

```ts
import { gimmickBadges } from '../lib/bossBadges'
```

그리고 `export function BossSummary({ boss }: BossSummaryProps) {` 바로 아래의 인라인 배열을 통째로 지우고 한 줄로 바꾼다. 지우는 것은 다음 블록이다:

```tsx
  const gimmicks = [
    boss.core_hittable && '코어 피격',
    boss.pierce_hits_body_behind_core && '2관통',
    boss.part_destructible && '부위파괴',
    boss.spawns_adds && '잡몹 생성',
    boss.elemental_interrupt_required && '속성저지 필수',
  ].filter((label): label is string => typeof label === 'string')
```

넣는 것:

```tsx
  const gimmicks = gimmickBadges(boss)
```

파일 맨 위 주석의 「켜진 기믹만 나온다 — …」 문단도 지운다. 그 규칙은 이제
`bossBadges.ts`가 갖고 있고, 같은 규칙이 두 곳에 적혀 있으면 한쪽만 고쳐진다.

- [ ] **Step 6: 기존 테스트가 그대로 통과하는지 확인한다**

Run: `npm --prefix frontend test -- --run src/components/BossSummary.test.tsx src/lib/bossBadges.test.ts`
Expected: PASS — `BossSummary`의 출력은 한 글자도 바뀌지 않았다.

(`BossSummary.test.tsx`가 없으면 그 파일 인자를 빼고 돌린다.)

- [ ] **Step 7: 커밋**

```bash
git add frontend/src/lib/bossBadges.ts frontend/src/lib/bossBadges.test.ts frontend/src/components/BossSummary.tsx
git commit -m "기믹 뱃지 규칙을 lib/bossBadges로 모은다"
```

---

### Task 2: `ToggleChip` — 버튼처럼 보이는 진짜 input

**Files:**
- Create: `frontend/src/components/fields/ToggleChip.tsx`
- Create: `frontend/src/components/fields/ToggleChip.test.tsx`
- Modify: `frontend/src/App.css` (`.element-picker` 블록 바로 앞에 새 블록을 넣는다)

**Interfaces:**
- Consumes: 없음
- Produces: `<ToggleChip type="checkbox" | "radio" checked={boolean} onChange={(checked: boolean) => void} name?={string} help?={ReactNode}>{label}</ToggleChip>`

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`frontend/src/components/fields/ToggleChip.test.tsx`:

```tsx
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import { ToggleChip } from './ToggleChip'
import { HelpTip } from '../HelpTip'

describe('ToggleChip', () => {
  it('진짜 체크박스로 렌더된다 - 라벨로 찾을 수 있어야 한다', async () => {
    const onChange = vi.fn()
    const user = userEvent.setup()
    render(
      <ToggleChip type="checkbox" checked={false} onChange={onChange}>
        코어 타격 가능
      </ToggleChip>,
    )

    const input = screen.getByLabelText('코어 타격 가능')
    expect(input).toHaveAttribute('type', 'checkbox')
    await user.click(input)
    expect(onChange).toHaveBeenCalledWith(true)
  })

  it('라디오는 name으로 묶인다', () => {
    render(
      <>
        <ToggleChip type="radio" name="mode" checked onChange={vi.fn()}>
          단일 덱
        </ToggleChip>
        <ToggleChip type="radio" name="mode" checked={false} onChange={vi.fn()}>
          전부 최적화
        </ToggleChip>
      </>,
    )

    expect(screen.getByLabelText('단일 덱')).toBeChecked()
    expect(screen.getByLabelText('전부 최적화')).not.toBeChecked()
  })

  // 이 구조의 존재 이유. help가 <label> 안에 있으면 설명을 열려던 클릭이
  // 설정을 바꾼다.
  it('설명 버튼을 눌러도 토글되지 않는다', async () => {
    const onChange = vi.fn()
    const user = userEvent.setup()
    render(
      <ToggleChip
        type="checkbox"
        checked={false}
        onChange={onChange}
        help={<HelpTip label="코어 타격 가능">코어를 때릴 수 있는 보스</HelpTip>}
      >
        코어 타격 가능
      </ToggleChip>,
    )

    await user.click(screen.getByRole('button', { name: '코어 타격 가능 설명' }))
    expect(onChange).not.toHaveBeenCalled()
  })
})
```

- [ ] **Step 2: 실패를 확인한다**

Run: `npm --prefix frontend test -- --run src/components/fields/ToggleChip.test.tsx`
Expected: FAIL — `Failed to resolve import "./ToggleChip"`

- [ ] **Step 3: 최소 구현**

`frontend/src/components/fields/ToggleChip.tsx`:

```tsx
// 켜고 끄는 것을 버튼처럼 보이게 하되 진짜 input을 남긴다. div/button으로 만들면
// 라디오 그룹의 화살표 이동과 화면 낭독기의 그룹 읽기를 둘 다 잃는다 -
// .element-picker(약점 칩)가 같은 이유로 같은 구조다.
//
// help가 <label> 밖에 서는 것이 이 구조의 요점이다: 라벨 안에서는 아무 클릭이나
// 컨트롤을 토글하므로, 설명을 열려던 클릭이 설정을 바꾼다.

import type { ReactNode } from 'react'

interface ToggleChipProps {
  type: 'checkbox' | 'radio'
  checked: boolean
  onChange: (checked: boolean) => void
  children: ReactNode
  /** 라디오 그룹을 묶는 이름. checkbox에는 필요 없다. */
  name?: string
  /** 칩 옆에 서는 설명. 라벨 밖이라 눌러도 토글되지 않는다. */
  help?: ReactNode
}

export function ToggleChip({
  type,
  checked,
  onChange,
  children,
  name,
  help,
}: ToggleChipProps) {
  return (
    <span className="chip-toggle">
      <label className="chip-toggle__label">
        <input
          type={type}
          className="visually-hidden"
          name={name}
          checked={checked}
          onChange={(event) => onChange(event.target.checked)}
        />
        {children}
      </label>
      {help}
    </span>
  )
}
```

- [ ] **Step 4: 통과를 확인한다**

Run: `npm --prefix frontend test -- --run src/components/fields/ToggleChip.test.tsx`
Expected: PASS (3 tests)

- [ ] **Step 5: CSS를 더한다**

`frontend/src/App.css`의 `/* Element picker ---…` 주석 바로 **앞**에 넣는다:

```css
/* Toggle chip ------------------------------------------------------------- */

/* 켜고 끄는 칩. 라디오/체크박스를 .visually-hidden으로 숨기고 :has()로 칠하는
   것은 .element-picker와 같은 구조다.

   선택은 흰색으로 채운다. 이 팔레트에서 흰 채움은 「누르는 것」이고(index.css의
   --primary) 칩은 실제로 누르는 것이다. 뱃지(.guide-badge)는 테두리만 쓰므로
   한 화면에 같이 서도 갈린다 - 채움 = 누르는 것, 테두리 = 읽는 것.

   --accent를 안 쓰는 이유: 기믹은 다중 선택이라 켜진 것이 셋이면 빨강 테두리가
   셋 뜬다. 약점 칩이 accent를 써도 괜찮았던 것은 선택이 언제나 정확히 하나여서다. */
.chip-row {
  display: flex;
  flex-wrap: wrap;
  gap: var(--sp-2);
}

.chip-toggle {
  display: inline-flex;
  align-items: center;
  gap: var(--sp-1);
  border: 1px solid var(--border-strong);
  border-radius: var(--radius-sm);
  background: var(--surface-2);
  /* 설명 버튼이 있는 칩만 오른쪽에 자리를 낸다 - 없으면 라벨이 상자를 다 쓴다. */
  padding-right: 0;
}

.chip-toggle:has(.help-tip) {
  padding-right: var(--sp-2);
}

.chip-toggle__label {
  padding: var(--sp-2) var(--sp-3);
  font-size: 14px;
  cursor: pointer;
}

.chip-toggle:has(input:checked) {
  background: var(--primary);
  border-color: var(--primary);
  color: var(--primary-contrast);
}

/* 흰 바닥 위에서는 설명 버튼의 회색 테두리가 사라진다. */
.chip-toggle:has(input:checked) .help-tip__button {
  color: var(--primary-contrast);
  border-color: var(--primary-contrast);
}

.chip-toggle:has(input:focus-visible) {
  outline: 2px solid var(--accent);
  outline-offset: 1px;
}
```

- [ ] **Step 6: 커밋**

```bash
git add frontend/src/components/fields/ToggleChip.tsx frontend/src/components/fields/ToggleChip.test.tsx frontend/src/App.css
git commit -m "토글 칩 - 버튼처럼 보이는 진짜 input"
```

---

### Task 3: 보스 설정의 기믹 체크박스 5개를 칩으로

**Files:**
- Modify: `frontend/src/components/BossProfileField.tsx:330-425` (다섯 개의 `.checkbox-row` 블록)
- Modify: `frontend/src/App.css:1291-1305` (`.checkbox` / `.radio` / `.checkbox-row` 규칙)

**Interfaces:**
- Consumes: Task 2의 `ToggleChip`
- Produces: 없음 (화면 구조만 바뀐다. 접근 가능 이름은 그대로라 기존 테스트가 계속 통과한다)

- [ ] **Step 1: 기존 테스트가 지금 통과하는지 먼저 확인한다**

Run: `npm --prefix frontend test -- --run src/components/BossProfileField.test.tsx`
Expected: PASS. 이 작업의 성공 기준은 **이 테스트가 한 줄도 안 바뀌고 계속 통과하는 것**이다 — 칩 전환은 접근 가능 이름을 바꾸지 않는다.

- [ ] **Step 2: import를 더한다**

`frontend/src/components/BossProfileField.tsx`의 import 목록에:

```ts
import { ToggleChip } from './fields/ToggleChip'
```

- [ ] **Step 3: 다섯 블록을 바꾼다**

`{/* 설명 버튼이 <label> 밖에 있는 이유: … */}` 주석부터 `속성저지 필수` 블록 끝까지를 통째로 아래로 바꾼다. 주석은 이제 `ToggleChip` 안에 있으므로 여기서 지운다.

```tsx
          <div className="chip-row">
            <ToggleChip
              type="checkbox"
              checked={value.core_hittable}
              onChange={(checked) =>
                onChange({
                  ...value,
                  core_hittable: checked,
                  // 코어를 못 때리면 뚫고 지나갈 것도 없다. 엔진도 두 값을 같이 읽지만,
                  // 폼에서 모순 상태를 아예 만들지 않는 편이 화면이 정직하다.
                  pierce_hits_body_behind_core: checked && value.pierce_hits_body_behind_core,
                  // 코어를 못 때리면 크기도 의미가 없다. 값을 남겨 두면 화면에서
                  // 사라진 칸이 계산에는 남는다.
                  core_diameter_px: checked ? value.core_diameter_px : '',
                })
              }
              help={
                <HelpTip label="코어 타격 가능">
                  <HelpText>{HELP.boss.coreHittable}</HelpText>
                </HelpTip>
              }
            >
              코어 타격 가능
            </ToggleChip>

            <ToggleChip
              type="checkbox"
              checked={value.pierce_hits_body_behind_core}
              onChange={(checked) =>
                onChange({
                  ...value,
                  pierce_hits_body_behind_core: checked,
                  core_hittable: checked || value.core_hittable,
                })
              }
              help={
                <HelpTip label="상시 코어 2관통">
                  <HelpText>{HELP.boss.corePierce}</HelpText>
                </HelpTip>
              }
            >
              상시 코어 2관통
            </ToggleChip>

            <ToggleChip
              type="checkbox"
              checked={value.part_destructible}
              onChange={(checked) => onChange({ ...value, part_destructible: checked })}
              help={
                <HelpTip label="부위파괴 기믹">
                  <HelpText>{HELP.boss.partDestructible}</HelpText>
                </HelpTip>
              }
            >
              부위파괴 기믹
            </ToggleChip>

            <ToggleChip
              type="checkbox"
              checked={value.spawns_adds}
              onChange={(checked) => onChange({ ...value, spawns_adds: checked })}
              help={
                <HelpTip label="잡몹 생성">
                  <HelpText>{HELP.boss.spawnsAdds}</HelpText>
                </HelpTip>
              }
            >
              잡몹 생성
            </ToggleChip>

            {showElementalInterrupt && (
              <ToggleChip
                type="checkbox"
                checked={value.elemental_interrupt_required}
                onChange={(checked) =>
                  onChange({ ...value, elemental_interrupt_required: checked })
                }
                help={
                  <HelpTip label="속성저지 필수">
                    <HelpText>{HELP.boss.elementalInterrupt}</HelpText>
                  </HelpTip>
                }
              >
                속성저지 필수
              </ToggleChip>
            )}
          </div>
```

- [ ] **Step 4: 죽은 CSS를 지운다**

`frontend/src/App.css`에서 아래 두 블록을 찾아 고친다.

지우는 것:

```css
.checkbox,
.radio {
  display: flex;
  align-items: center;
  gap: var(--sp-2);
  font-size: 14px;
}
```

`.checkbox-row`가 `.field__label-row`와 규칙을 공유하고 있으므로 선택자에서 한쪽만 떼어낸다. 있는 것:

```css
/* Carries the help button beside a checkbox instead of inside its label, where
   a click meant for the help would toggle the box. */
.checkbox-row,
.field__label-row {
```

바꿀 것:

```css
/* 라벨과 그 옆의 설명 버튼을 한 줄에 세운다. */
.field__label-row {
```

`.checkbox` · `.checkbox-row` · `.radio`는 Task 4까지 끝나면 아무도 쓰지 않는다. `.radio`는 Task 4에서 지운다.

- [ ] **Step 5: 테스트가 그대로 통과하는지 확인한다**

Run: `npm --prefix frontend test -- --run src/components/BossProfileField.test.tsx`
Expected: PASS — **테스트 파일을 한 줄도 고치지 않았는데** 통과해야 한다. 실패하면 `ToggleChip`이 접근 가능 이름을 잃은 것이므로 되돌아가 고친다.

- [ ] **Step 6: 커밋**

```bash
git add frontend/src/components/BossProfileField.tsx frontend/src/App.css
git commit -m "보스 기믹을 토글 칩으로"
```

---

### Task 4: 모드 라디오 4개를 칩으로 + 선택된 모드의 힌트만

**Files:**
- Modify: `frontend/src/components/RecommendPanel.tsx:126` (모드 목록 상수 추가), `:846-897` (모드 fieldset)
- Modify: `frontend/src/App.css` (`.mode-switch` 블록, `.radio` 잔여)

**Interfaces:**
- Consumes: Task 2의 `ToggleChip`
- Produces: 없음

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`frontend/src/components/RecommendPanel.test.tsx` 안에, 기존 `describe` 블록 하나의 끝에 더한다. (import에 이미 `screen`·`userEvent`가 있다.)

```tsx
  it('선택된 모드의 설명만 보인다', async () => {
    const user = userEvent.setup()
    render(<RecommendPanel roster={fullRoster} {...noPersistence} />)

    expect(screen.getByText(/기대 딜량이 높은 개별 덱을 찾아줘요/)).toBeInTheDocument()
    expect(screen.queryByText(/설정한 덱 개수만큼 최적화해요/)).not.toBeInTheDocument()

    await user.click(screen.getByLabelText('전부 최적화'))

    expect(screen.getByText(/설정한 덱 개수만큼 최적화해요/)).toBeInTheDocument()
    expect(screen.queryByText(/기대 딜량이 높은 개별 덱을 찾아줘요/)).not.toBeInTheDocument()
  })
```

`fullRoster`(58행)와 `noPersistence`(73행)는 이 파일이 이미 갖고 있는 픽스처다.
`render(<RecommendPanel roster={fullRoster} {...noPersistence} />)`는 이 파일의
대다수 테스트가 쓰는 그대로다(152·178·203행 등).

- [ ] **Step 2: 실패를 확인한다**

Run: `npm --prefix frontend test -- --run src/components/RecommendPanel.test.tsx -t '선택된 모드의 설명만'`
Expected: FAIL — 지금은 네 문장이 전부 화면에 있으므로 `queryByText(/설정한 덱 개수만큼/)`이 요소를 찾는다.

- [ ] **Step 3: 모드 목록 상수를 더한다**

`frontend/src/components/RecommendPanel.tsx`의 `type RecommendMode = 'single' | 'raid' | 'draft' | 'evaluate'` **바로 아래**에:

```tsx
// 화면에 그리는 네 모드. Record로 두는 이유는 모드를 하나 더 만들 때 타입이
// 빠진 자리를 잡아 주기 때문이다 - 배열에서 find로 꺼내면 못 찾는 경우를 타입이
// 요구하는데, 실제로는 못 찾을 수 없다.
const RECOMMEND_MODES: RecommendMode[] = ['single', 'raid', 'draft', 'evaluate']

const MODE_LABEL: Record<RecommendMode, string> = {
  single: '단일 덱',
  raid: '전부 최적화',
  draft: '빈자리만 최적화',
  evaluate: '기대 딜량 계산',
}

const MODE_HINT: Record<RecommendMode, string> = {
  single: HELP.recommendMode.single,
  raid: HELP.recommendMode.raid,
  draft: HELP.recommendMode.draft,
  evaluate: HELP.recommendMode.evaluate,
}
```

import에 다음을 더한다:

```ts
import { ToggleChip } from './fields/ToggleChip'
```

- [ ] **Step 4: 모드 fieldset을 바꾼다**

`<legend className="group__legend">모드</legend>` 다음의 `<div className="mode-switch">…</div>` 블록 전체(라디오 네 개)를 아래로 바꾼다.

```tsx
            {/* 네 문장을 전부 세워 두면 세로가 길어지고, 정작 지금 무엇을 하려는지는
                고른 하나가 답한다. 그래서 힌트는 선택된 모드의 것만 아래 한 줄로 선다. */}
            <div className="chip-row">
              {RECOMMEND_MODES.map((option) => (
                <ToggleChip
                  key={option}
                  type="radio"
                  name="recommend-mode"
                  checked={mode === option}
                  onChange={() => switchMode(option)}
                >
                  {MODE_LABEL[option]}
                </ToggleChip>
              ))}
            </div>
            <p className="mode-switch__hint group__hint">
              <HelpText>{MODE_HINT[mode]}</HelpText>
            </p>
```

- [ ] **Step 5: CSS를 고친다**

`frontend/src/App.css`에서 `.mode-switch` 블록을 찾아 바꾼다.

있는 것:

```css
/* 모드 힌트는 인라인 <span>이라 max-width가 듣지 않는다. 줄바꿈을 결정하는
   것은 이 컨테이너다. */
.mode-switch {
  display: flex;
  flex-direction: column;
  gap: var(--sp-2);
  max-width: var(--measure);
}
```

바꿀 것:

```css
/* 선택된 모드의 설명 한 줄. 문장이라 읽기 폭을 넘지 않는다. */
.mode-switch__hint {
  margin: 0;
  max-width: var(--measure);
}
```

그리고 Task 3에서 남겨 둔 `.radio`가 이제 아무도 안 쓴다 — 이미 Task 3 Step 4에서 `.checkbox, .radio` 블록을 통째로 지웠다면 할 일이 없다. `App.css`에 `radio`가 남아 있는지 확인한다:

Run: `grep -n "\.radio\b\|\.checkbox\b\|\.checkbox-row" frontend/src/App.css`
Expected: 아무것도 안 나온다.

- [ ] **Step 6: 통과를 확인한다**

Run: `npm --prefix frontend test -- --run src/components/RecommendPanel.test.tsx`
Expected: PASS — 새 테스트를 포함해 전부. 기존 모드 전환 테스트들은 `getByLabelText('전부 최적화')`를 쓰므로 그대로 통과한다.

- [ ] **Step 7: 커밋**

```bash
git add frontend/src/components/RecommendPanel.tsx frontend/src/components/RecommendPanel.test.tsx frontend/src/App.css
git commit -m "모드를 토글 칩으로, 힌트는 고른 것만"
```

---

### Task 5: `defaultCollapsed` — 솔로에서 보스 설정을 접어 둔다

**Files:**
- Modify: `frontend/src/components/BossProfileField.tsx` (props 인터페이스, `useState`)
- Modify: `frontend/src/components/RecommendPanel.tsx` (`<BossProfileField>` 호출부)
- Modify: `frontend/src/components/BossProfileField.test.tsx` (새 테스트 하나)
- Modify: `frontend/src/components/RecommendPanel.test.tsx` (헬퍼 + 호출부 8곳)

**Interfaces:**
- Consumes: 없음
- Produces: `BossProfileFieldProps.defaultCollapsed?: boolean` (기본 `false`)

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`frontend/src/components/BossProfileField.test.tsx` 끝에:

```tsx
  it('defaultCollapsed면 회차 카드까지 통째로 접힌 채로 뜬다', () => {
    render(
      <BossProfileField
        value={makeDefaultBossProfileDraft('31784')}
        onChange={vi.fn()}
        rotation={timedRotation}
        defaultCollapsed
      />,
    )

    expect(screen.queryByLabelText('코어 타격 가능')).not.toBeInTheDocument()
    expect(screen.queryByText('사치스러운 거미')).not.toBeInTheDocument()
    expect(screen.getByRole('button', { expanded: false })).toBeInTheDocument()
  })
```

`timedRotation`(221행)은 이 파일이 이미 갖고 있는 솔로 40시즌 픽스처이고, 그
보스가 「사치스러운 거미」다. `render`·`screen`·`vi`·`makeDefaultBossProfileDraft`도
전부 이미 import돼 있다.

- [ ] **Step 2: 실패를 확인한다**

Run: `npm --prefix frontend test -- --run src/components/BossProfileField.test.tsx -t 'defaultCollapsed'`
Expected: FAIL — TypeScript가 모르는 prop이고, 렌더는 펼친 채로 나온다.

- [ ] **Step 3: prop을 더한다**

`frontend/src/components/BossProfileField.tsx`의 `BossProfileFieldProps`에:

```ts
  /** 접힌 채로 시작할지. 솔로 탭은 보스를 시즌마다 한 번 정하고 나면 거의 안
   * 건드리므로 접어 둔다. 유니온은 전투마다 다른 보스를 고르므로 펼친 채로
   * 둔다 - 접으면 실행할 때마다 전투 수만큼 펼쳐야 한다. */
  defaultCollapsed?: boolean
```

구조 분해에 `defaultCollapsed = false,`를 더하고, `const [collapsed, setCollapsed] = useState(false)`를 바꾼다:

```ts
  const [collapsed, setCollapsed] = useState(defaultCollapsed)
```

- [ ] **Step 4: 통과를 확인한다**

Run: `npm --prefix frontend test -- --run src/components/BossProfileField.test.tsx`
Expected: PASS — 새 테스트 포함 전부. 나머지 테스트는 prop을 안 넘기므로 펼친 채로 남는다.

- [ ] **Step 5: 솔로 탭에서 켠다**

`frontend/src/components/RecommendPanel.tsx`의 `<BossProfileField … />` 호출에 한 줄을 더한다:

```tsx
            defaultEnemyDef={SOLO_RAID_DEFAULT_ENEMY_DEF}
            defaultCollapsed
```

- [ ] **Step 6: 깨진 테스트를 확인한다**

Run: `npm --prefix frontend test -- --run src/components/RecommendPanel.test.tsx`
Expected: FAIL — 보스 칸을 만지는 테스트들이 요소를 못 찾는다.

- [ ] **Step 7: 헬퍼를 두고 여덟 자리를 고친다**

`frontend/src/components/RecommendPanel.test.tsx` 위쪽, 픽스처들 다음에:

```tsx
/** 솔로 탭의 보스 설정은 접힌 채로 뜬다(defaultCollapsed). 보스 칸을 만지는
 * 테스트는 먼저 펼쳐야 한다. 접힘 버튼은 이 화면에서 aria-expanded를 가진
 * 유일한 버튼이라 역할로 찾는다 - 클래스 이름으로 찾으면 CSS를 고칠 때 깨진다. */
const expandBossProfile = async (user: ReturnType<typeof userEvent.setup>) => {
  const [toggle] = screen.queryAllByRole('button', { expanded: false })
  if (toggle) await user.click(toggle)
}
```

그리고 아래 여덟 자리에서, 보스 칸을 처음 만지기 **직전**에 `await expandBossProfile(user)`를 넣는다. 각 자리의 지금 코드와 넣는 위치:

| 행 | 지금 코드 | 넣는 곳 |
|---|---|---|
| 104 | `expect(screen.getByLabelText(/적 방어력/)).toHaveValue(31784)` | 이 줄 앞 |
| 325 | `await user.click(screen.getByLabelText('코어 타격 가능'))` | 이 줄 앞 |
| 355 | `await user.click(screen.getByLabelText('부위파괴 기믹'))` | 이 줄 앞 |
| 386 | `await user.selectOptions(screen.getByLabelText('보스 적정거리'), 'mid')` | 이 줄 앞 |
| 1059 | `await user.click(screen.getByLabelText('속성저지 필수'))` | 이 줄 앞 |
| 1065 | `await user.click(screen.getByLabelText('속성저지 필수'))` | 이 줄 앞 |
| 1728 | `expect(screen.getByLabelText(/적 방어력/)).toHaveValue(31784)` | 이 줄 앞 |
| 1732 | `expect(screen.getByLabelText(/적 방어력/)).toHaveValue(12345)` | 이 줄 앞 |

행 번호는 이 계획을 쓴 시점(`5bb269fa` + Task 1~4)의 것이므로, Task 4에서 테스트를
더했다면 아래쪽이 밀린다. 코드로 찾는다:

Run: `grep -n "코어 타격 가능\|부위파괴 기믹\|속성저지 필수\|보스 적정거리\|적 방어력" frontend/src/components/RecommendPanel.test.tsx`

1059와 1065는 같은 테스트 안이라, 한 번 펼치면 두 번째는 이미 펼쳐져 있다 —
헬퍼가 `queryAllByRole`로 없으면 아무것도 안 하므로 두 번 불러도 안전하다.
1728·1732·1733도 같은 테스트 안이므로 1728 앞에 한 번이면 된다.

- [ ] **Step 8: 통과를 확인한다**

Run: `npm --prefix frontend test -- --run src/components/RecommendPanel.test.tsx src/components/BossProfileField.test.tsx src/components/UnionRaidPanel.test.tsx`
Expected: PASS — 유니온은 prop을 안 넘기므로 손대지 않았는데도 통과해야 한다. 이게 「유니온은 펼친 채로 둔다」의 회귀 방지다.

- [ ] **Step 9: 커밋**

```bash
git add frontend/src/components/BossProfileField.tsx frontend/src/components/BossProfileField.test.tsx frontend/src/components/RecommendPanel.tsx frontend/src/components/RecommendPanel.test.tsx
git commit -m "솔로 탭의 보스 설정은 접힌 채로 뜬다"
```

---

### Task 6: `useBossGuides` — 회차 보스별 가이드 저장소

**Files:**
- Create: `frontend/src/hooks/useBossGuides.ts`
- Create: `frontend/src/hooks/useBossGuides.test.ts`

**Interfaces:**
- Consumes: 없음
- Produces: `useBossGuides(): { guideFor: (key: string, fallback: string) => string; setGuide: (key: string, text: string) => void }`

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`frontend/src/hooks/useBossGuides.test.ts`:

```ts
import { act, renderHook } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { useBossGuides } from './useBossGuides'

beforeEach(() => {
  localStorage.clear()
})

afterEach(() => {
  vi.restoreAllMocks()
})

describe('useBossGuides', () => {
  it('없는 키에는 fallback을 준다', () => {
    const { result } = renderHook(() => useBossGuides())
    expect(result.current.guideFor('solo-40::사치스러운 거미', '')).toBe('')
    expect(result.current.guideFor('solo-40::사치스러운 거미', '기본 글')).toBe('기본 글')
  })

  it('쓴 글이 localStorage에 남고 다시 읽힌다', () => {
    const { result } = renderHook(() => useBossGuides())
    act(() => result.current.setGuide('solo-40::사치스러운 거미', '알 먼저'))
    expect(result.current.guideFor('solo-40::사치스러운 거미', '')).toBe('알 먼저')

    const reread = renderHook(() => useBossGuides())
    expect(reread.result.current.guideFor('solo-40::사치스러운 거미', '')).toBe('알 먼저')
  })

  // 키가 (회차, 보스)인 것이 요점이다 - 같은 보스가 다음 시즌에 다른 속성으로
  // 나오면 지난 시즌 글이 얹히면 안 된다.
  it('회차가 다르면 다른 칸이다', () => {
    const { result } = renderHook(() => useBossGuides())
    act(() => result.current.setGuide('solo-39::아일랜드 이터', '39시즌 글'))
    expect(result.current.guideFor('solo-40::아일랜드 이터', '')).toBe('')
  })

  it('읽기가 막혀 있어도 던지지 않는다', () => {
    vi.spyOn(Storage.prototype, 'getItem').mockImplementation(() => {
      throw new Error('blocked')
    })
    const { result } = renderHook(() => useBossGuides())
    expect(result.current.guideFor('solo-40::사치스러운 거미', '')).toBe('')
  })

  it('쓰기가 막혀 있어도 이번 세션 동안은 고쳐 쓸 수 있다', () => {
    vi.spyOn(Storage.prototype, 'setItem').mockImplementation(() => {
      throw new Error('blocked')
    })
    const { result } = renderHook(() => useBossGuides())
    act(() => result.current.setGuide('solo-40::사치스러운 거미', '알 먼저'))
    expect(result.current.guideFor('solo-40::사치스러운 거미', '')).toBe('알 먼저')
  })
})
```

- [ ] **Step 2: 실패를 확인한다**

Run: `npm --prefix frontend test -- --run src/hooks/useBossGuides.test.ts`
Expected: FAIL — `Failed to resolve import "./useBossGuides"`

- [ ] **Step 3: 최소 구현**

`frontend/src/hooks/useBossGuides.ts`:

```ts
// 회차 보스마다 Fienn이 직접 쓰는 가이드. 지금은 localStorage에만 산다.
//
// localStorage는 빌드 산출물이 아니라 기기에 붙는다 - 개발 브라우저에 쓴 글은
// 설치본에서 보이지 않고 릴리즈 zip에 실리지도 않는다. 릴리즈에 실리는 쪽은
// 2단계에서 data/raid-rotations.json이 맡고, 이 훅은 그 위를 덮는 층이 된다.
// guideFor가 fallback을 받는 이유가 그것이다: 지금은 언제나 ''이지만 자리는
// 그때 것이고, 시그니처를 나중에 바꾸면 호출부를 다시 훑어야 한다.
//
// 키가 (회차, 보스)인 것은 data/raid-rotations.json과 같은 규칙이다 - 같은 보스가
// 다음 시즌에 다른 속성으로 나오면 가이드도 다른 칸이다.

import { useCallback, useState } from 'react'

const STORAGE_KEY = 'nikke-boss-guides'

interface GuidesFile {
  guides: Record<string, string>
}

/** 저장된 가이드. 읽기가 막혀 있으면(사생활 모드 등) 빈 것으로 시작한다 -
 * 가이드가 없다고 화면이 못 도는 것은 아니다. */
const readGuides = (): Record<string, string> => {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    if (raw === null) return {}
    return (JSON.parse(raw) as GuidesFile).guides ?? {}
  } catch {
    return {}
  }
}

export interface BossGuides {
  /** 저장된 글. 없으면 fallback. */
  guideFor: (key: string, fallback: string) => string
  setGuide: (key: string, text: string) => void
}

export const useBossGuides = (): BossGuides => {
  const [guides, setGuides] = useState<Record<string, string>>(readGuides)

  const setGuide = useCallback((key: string, text: string) => {
    setGuides((current) => {
      const next = { ...current, [key]: text }
      try {
        localStorage.setItem(STORAGE_KEY, JSON.stringify({ guides: next }))
      } catch {
        // 쓰기가 막혀도 이번 세션 동안은 고쳐 쓸 수 있어야 한다.
      }
      return next
    })
  }, [])

  const guideFor = useCallback(
    (key: string, fallback: string) => guides[key] ?? fallback,
    [guides],
  )

  return { guideFor, setGuide }
}
```

- [ ] **Step 4: 통과를 확인한다**

Run: `npm --prefix frontend test -- --run src/hooks/useBossGuides.test.ts`
Expected: PASS (5 tests)

- [ ] **Step 5: 커밋**

```bash
git add frontend/src/hooks/useBossGuides.ts frontend/src/hooks/useBossGuides.test.ts
git commit -m "회차 보스별 가이드 저장소"
```

---

### Task 7: `FightTimeline` — 전투 한 판을 가로 한 줄로

**Files:**
- Create: `frontend/src/components/FightTimeline.tsx`
- Create: `frontend/src/components/FightTimeline.test.tsx`
- Modify: `frontend/src/App.css`

**Interfaces:**
- Consumes: 없음
- Produces: `<FightTimeline durationSeconds={number} destructionTimes={number[]} />`

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`frontend/src/components/FightTimeline.test.tsx`:

```tsx
import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { FightTimeline } from './FightTimeline'

describe('FightTimeline', () => {
  it('전투 시간과 파괴 시각을 적는다', () => {
    render(<FightTimeline durationSeconds={180} destructionTimes={[1, 61, 126]} />)

    expect(screen.getByText('180초')).toBeInTheDocument()
    expect(screen.getByText(/파괴 1 · 61 · 126초/)).toBeInTheDocument()
  })

  // 빈 눈금을 그리면 「관측 안 함」이 「0개」로 읽힌다.
  it('파괴 시각이 없으면 아무것도 안 그린다', () => {
    const { container } = render(
      <FightTimeline durationSeconds={180} destructionTimes={[]} />,
    )
    expect(container).toBeEmptyDOMElement()
  })

  it('전투 시간이 없으면 아무것도 안 그린다', () => {
    const { container } = render(
      <FightTimeline durationSeconds={Number.NaN} destructionTimes={[1]} />,
    )
    expect(container).toBeEmptyDOMElement()
  })

  // 전투 시간을 넘는 시각은 판독이 틀린 것이다. 끝에 몰아 찍으면 틀렸다는
  // 사실이 감춰지므로 버린다.
  it('전투 시간 밖의 시각은 버린다', () => {
    render(<FightTimeline durationSeconds={100} destructionTimes={[10, 150]} />)
    expect(screen.getByText(/파괴 10초/)).toBeInTheDocument()
    expect(screen.queryByText(/150/)).not.toBeInTheDocument()
  })
})
```

- [ ] **Step 2: 실패를 확인한다**

Run: `npm --prefix frontend test -- --run src/components/FightTimeline.test.tsx`
Expected: FAIL — `Failed to resolve import "./FightTimeline"`

- [ ] **Step 3: 최소 구현**

`frontend/src/components/FightTimeline.tsx`:

```tsx
// 전투 한 판을 가로 한 줄로. 엔진이 실제로 읽는 두 값 - 전투 시간과 파츠가 깨지는
// 시각 - 을 그대로 그린다.
//
// 왜 있나: 솔로 탭에서 보스 설정을 접어 두므로 그 두 값을 볼 곳이 여기뿐이다.
// 그리고 값이 틀리면 그 자리에서 이상함이 보인다 - CoreHitRateReadout이 코어
// 지름 옆에서 하는 일과 같은 종류다.
//
// 눈금(svg)은 aria-hidden이다. 같은 값을 아래 줄이 낱말로 다시 말하므로, 화면
// 낭독기에는 그 줄 하나면 된다.

interface FightTimelineProps {
  /** 전투 시간(초). 숫자가 아니거나 0 이하면 그리지 않는다 - 편집 중인 반쪽짜리
   *  입력에 대고 눈금을 내면 자가 춤춘다. */
  durationSeconds: number
  /** 파츠가 깨지는 시각(초). */
  destructionTimes: number[]
}

export function FightTimeline({ durationSeconds, destructionTimes }: FightTimelineProps) {
  if (!Number.isFinite(durationSeconds) || durationSeconds <= 0) return null

  // 전투 시간 밖의 시각은 판독이 틀린 것이다. 끝에 몰아 찍으면 틀렸다는 사실이
  // 감춰지므로 잘라내지 않고 버린다.
  const marks = destructionTimes.filter((t) => t >= 0 && t <= durationSeconds)
  if (marks.length === 0) return null

  return (
    <div className="fight-timeline">
      <p className="fight-timeline__ends">
        <span>0</span>
        <span>{durationSeconds}초</span>
      </p>
      <svg
        className="fight-timeline__rule"
        viewBox="0 0 100 8"
        preserveAspectRatio="none"
        aria-hidden="true"
      >
        {/* preserveAspectRatio="none"이라 가로로 늘어난다. 선 굵기가 같이
            늘어나지 않도록 non-scaling-stroke를 준다. */}
        <line x1="0" y1="4" x2="100" y2="4" vectorEffect="non-scaling-stroke" />
        {marks.map((t) => {
          const x = (t / durationSeconds) * 100
          return (
            <line
              key={t}
              x1={x}
              y1="0"
              x2={x}
              y2="8"
              vectorEffect="non-scaling-stroke"
            />
          )
        })}
      </svg>
      <p className="fight-timeline__marks">파괴 {marks.join(' · ')}초</p>
    </div>
  )
}
```

- [ ] **Step 4: 통과를 확인한다**

Run: `npm --prefix frontend test -- --run src/components/FightTimeline.test.tsx`
Expected: PASS (4 tests)

- [ ] **Step 5: CSS를 더한다**

`frontend/src/App.css`의 `/* Groups (fieldsets) ---…` 주석 바로 **앞**에:

```css
/* Fight timeline ---------------------------------------------------------- */

/* 전투 한 판을 가로 한 줄로. 눈금은 장식이 아니라 엔진이 읽는 두 값의 그림이고,
   숫자는 --mono가 진다 - 이 프로젝트가 「숫자 열을 맞추는 한 자리」로 남겨 둔
   폰트에 실제로 그 일을 준다. */
.fight-timeline {
  display: flex;
  flex-direction: column;
  gap: var(--sp-1);
}

.fight-timeline__ends {
  display: flex;
  justify-content: space-between;
  margin: 0;
  font-family: var(--mono);
  font-size: 11px;
  color: var(--text-muted);
}

.fight-timeline__rule {
  width: 100%;
  height: 8px;
  stroke: var(--border-strong);
  stroke-width: 1;
}

.fight-timeline__marks {
  margin: 0;
  font-family: var(--mono);
  font-size: 12px;
}
```

- [ ] **Step 6: 커밋**

```bash
git add frontend/src/components/FightTimeline.tsx frontend/src/components/FightTimeline.test.tsx frontend/src/App.css
git commit -m "전투 타임라인 - 전투 시간과 파괴 시각을 한 줄로"
```

---

### Task 8: `SeasonGuideCard` — 뱃지 줄 + 타임라인 + 직접 쓰는 문장

**Files:**
- Create: `frontend/src/components/SeasonGuideCard.tsx`
- Create: `frontend/src/components/SeasonGuideCard.test.tsx`
- Modify: `frontend/src/App.css`

**Interfaces:**
- Consumes: Task 1의 `gimmickBadges`, Task 6의 `useBossGuides`, Task 7의 `FightTimeline`
- Produces: `<SeasonGuideCard rotation={RaidRotation | null} boss={BossProfileDraft} />`, `guideTitle(rotation: RaidRotation | null): string`

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`frontend/src/components/SeasonGuideCard.test.tsx`:

```tsx
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it } from 'vitest'
import { SeasonGuideCard, guideTitle } from './SeasonGuideCard'
import { makeDefaultBossProfileDraft } from '../types/bossProfileDraft'
import type { BossProfileDraft } from '../types/bossProfileDraft'
import type { RaidRotation } from '../types/raidRotation'

const solo40: RaidRotation = {
  id: 'solo-40',
  raid: 'solo',
  title: '솔로 레이드 40시즌',
  starts_at: '2026-08-20T12:00:00+09:00',
  ends_at: '2026-08-27T04:59:00+09:00',
  source_url: 'https://example.test',
  source_locale: 'ko',
  read_on: '2026-08-20',
  bosses: [],
}

const picked = (over: Partial<BossProfileDraft> = {}): BossProfileDraft => ({
  ...makeDefaultBossProfileDraft('31784'),
  element: 'Wind',
  boss_name: '사치스러운 거미',
  ...over,
})

beforeEach(() => {
  localStorage.clear()
})

describe('guideTitle', () => {
  it('회차만 뽑는다 - 이 카드는 솔로 탭 안에만 선다', () => {
    expect(guideTitle(solo40)).toBe('40시즌 가이드')
  })

  it('형식이 다르면 제목을 통째로 쓴다', () => {
    expect(guideTitle({ ...solo40, title: '유니온 레이드 7/31' })).toBe(
      '유니온 레이드 7/31 가이드',
    )
  })

  it('회차가 없으면 폴백', () => {
    expect(guideTitle(null)).toBe('보스 가이드')
  })
})

describe('SeasonGuideCard', () => {
  it('약점과 켜진 기믹을 뱃지로 그린다', () => {
    render(
      <SeasonGuideCard
        rotation={solo40}
        boss={picked({ part_destructible: true, spawns_adds: true })}
      />,
    )

    expect(screen.getByText('작열 약점')).toBeInTheDocument()
    expect(screen.getByText('부위파괴')).toBeInTheDocument()
    expect(screen.getByText('잡몹 생성')).toBeInTheDocument()
    expect(screen.queryByText('코어 피격')).not.toBeInTheDocument()
  })

  it('적정거리를 고른 보스만 거리 뱃지를 갖는다', () => {
    render(<SeasonGuideCard rotation={solo40} boss={picked({ effective_range_band: 'mid' })} />)
    expect(screen.getByText('중거리')).toBeInTheDocument()
  })

  it('보스를 안 골랐으면 무엇을 할지 적는다', () => {
    render(<SeasonGuideCard rotation={solo40} boss={makeDefaultBossProfileDraft('31784')} />)

    expect(screen.getByText('위에서 이번 회차 보스를 고르세요.')).toBeInTheDocument()
    expect(screen.queryByLabelText('가이드 내용')).not.toBeInTheDocument()
  })

  it('쓴 글이 남고, 보스를 바꾸면 다른 글이 나온다', async () => {
    const user = userEvent.setup()
    const { rerender } = render(<SeasonGuideCard rotation={solo40} boss={picked()} />)

    await user.type(screen.getByLabelText('가이드 내용'), '알 먼저')
    expect(screen.getByLabelText('가이드 내용')).toHaveValue('알 먼저')

    rerender(<SeasonGuideCard rotation={solo40} boss={picked({ boss_name: '다른 보스' })} />)
    expect(screen.getByLabelText('가이드 내용')).toHaveValue('')
  })

  it('부위파괴가 꺼져 있으면 파괴 시각을 그리지 않는다', () => {
    render(
      <SeasonGuideCard
        rotation={solo40}
        boss={picked({ part_destructible: false, part_destruction_times: '1, 61' })}
      />,
    )
    expect(screen.queryByText(/파괴 1/)).not.toBeInTheDocument()
  })

  it('부위파괴가 켜져 있으면 파괴 시각을 그린다', () => {
    render(
      <SeasonGuideCard
        rotation={solo40}
        boss={picked({ part_destructible: true, part_destruction_times: '1, 61, 126' })}
      />,
    )
    expect(screen.getByText('파괴 1 · 61 · 126초')).toBeInTheDocument()
  })
})
```

주: `element: 'Wind'`가 「작열 약점」이 되는 것은 `weaknessFor`가 보스 속성의
약점을 돌려주기 때문이다(바람 보스 → 작열이 약점). 테스트가 빨개지면
`lib/elementAdvantage.ts`의 `weaknessFor`를 열어 실제 짝을 확인하고 문자열을
맞춘다 — 짝을 여기서 발명하지 말 것.

- [ ] **Step 2: 실패를 확인한다**

Run: `npm --prefix frontend test -- --run src/components/SeasonGuideCard.test.tsx`
Expected: FAIL — `Failed to resolve import "./SeasonGuideCard"`

- [ ] **Step 3: 최소 구현**

`frontend/src/components/SeasonGuideCard.tsx`:

```tsx
// 이번 회차 보스를 상대하기 전에 읽는 것. 왼쪽 컬럼(보스 설정 · 모드)이 「내가
// 고르는 것」이면 이 카드는 「내가 읽는 것」이다.
//
// 뱃지는 보스 설정에서 파생된다 - 손으로 다시 적지 않으므로 실제 계산 입력과
// 어긋날 수 없다. 보스 설정을 접어 두는 화면에서 그 값들을 비추는 자리이기도 하다.
//
// 문장만 사람이 쓴다. 지금은 localStorage에만 남는다(useBossGuides의 주석 참조).

import { gimmickBadges } from '../lib/bossBadges'
import { weaknessFor } from '../lib/elementAdvantage'
import { elementLabel } from '../lib/elementName'
import { useBossGuides } from '../hooks/useBossGuides'
import { FightTimeline } from './FightTimeline'
import type { BossProfileDraft } from '../types/bossProfileDraft'
import type { RaidRotation } from '../types/raidRotation'
import type { BossRangeBand } from '../types/recommend'

const RANGE_BAND_LABEL: Record<Exclude<BossRangeBand, null>, string> = {
  near: '근거리',
  mid: '중거리',
  far: '원거리',
}

/** 카드 제목. 「솔로 레이드 40시즌」에서 회차만 뽑는 이유는 이 카드가 솔로 탭
 * 안에만 서기 때문이다 - 「솔로 레이드」는 탭이 이미 말하고 있다. 형식이 다른
 * 회차(「유니온 레이드 7/31」)는 뽑을 것이 없으므로 제목을 통째로 쓴다. */
export const guideTitle = (rotation: RaidRotation | null): string => {
  if (rotation === null) return '보스 가이드'
  const season = /\d+시즌/.exec(rotation.title)
  return `${season === null ? rotation.title : season[0]} 가이드`
}

/** 「1, 61, 126」을 숫자로. 폼은 편집 중일 수 있으므로 반쪽짜리 값에 던지지 않고
 * 버린다 - 제출을 막는 판정은 validateBossProfileDraft가 따로 한다. */
const parseTimes = (raw: string): number[] =>
  raw
    .split(',')
    .map((part) => part.trim())
    .filter((part) => part !== '')
    .map(Number)
    .filter((value) => Number.isFinite(value))

interface SeasonGuideCardProps {
  rotation: RaidRotation | null
  boss: BossProfileDraft
}

export function SeasonGuideCard({ rotation, boss }: SeasonGuideCardProps) {
  const { guideFor, setGuide } = useBossGuides()

  // 저장할 칸의 이름. 회차 보스를 안 골랐으면 없다 - 그 상태에서 입력을 받으면
  // 쓴 글이 어디에도 안 남는다.
  const key = rotation !== null && boss.boss_name !== null
    ? `${rotation.id}::${boss.boss_name}`
    : null

  const badges = [
    boss.element === null ? '약점 없음' : `${elementLabel(weaknessFor(boss.element))} 약점`,
    ...(boss.effective_range_band === null
      ? []
      : [RANGE_BAND_LABEL[boss.effective_range_band]]),
    ...gimmickBadges(boss),
  ]

  // 부위파괴가 꺼져 있으면 엔진이 시각을 무시한다 - 화면에서도 빠져야 지울 수
  // 없는 값이 계산에 쓰이는 것처럼 보이지 않는다.
  const times = boss.part_destructible ? parseTimes(boss.part_destruction_times) : []

  const title = guideTitle(rotation)

  return (
    <section className="guide-card" aria-label={title}>
      <h3 className="guide-card__title">{title}</h3>

      <p className="guide-card__badges">
        {badges.map((label) => (
          <span key={label} className="guide-badge">
            {label}
          </span>
        ))}
      </p>

      <FightTimeline
        durationSeconds={Number(boss.fight_duration)}
        destructionTimes={times}
      />

      {key === null ? (
        <p className="guide-card__empty">위에서 이번 회차 보스를 고르세요.</p>
      ) : (
        <textarea
          className="guide-card__text"
          aria-label="가이드 내용"
          placeholder="무엇을 챙기고 무엇을 피하는지"
          value={guideFor(key, '')}
          onChange={(event) => setGuide(key, event.target.value)}
        />
      )}
    </section>
  )
}
```

- [ ] **Step 4: 통과를 확인한다**

Run: `npm --prefix frontend test -- --run src/components/SeasonGuideCard.test.tsx`
Expected: PASS (9 tests)

- [ ] **Step 5: CSS를 더한다**

`frontend/src/App.css`의 `/* Fight timeline ---…` 블록 바로 **앞**에:

```css
/* Season guide ------------------------------------------------------------ */

/* 시즌 가이드. 왼쪽의 .group 상자 둘과 같은 테두리·둥글기·여백을 써서 셋이 한
   식구로 읽힌다. 안쪽은 상자를 또 세우지 않고 --rule 한 줄로 띠를 가른다 -
   .core-measure가 왼쪽 선 하나로 「설정이 아니라 재료」를 말하는 것과 같은
   방식이고, 한 화면에 2px 상자를 넷 세우지 않기 위해서다. */
.guide-card {
  border: 2px solid var(--border);
  border-radius: var(--radius-sm);
  padding: var(--sp-4);
  display: flex;
  flex-direction: column;
  gap: var(--sp-3);
}

.guide-card__title {
  margin: 0;
  font-size: 13px;
  font-weight: 600;
}

.guide-card__badges {
  display: flex;
  flex-wrap: wrap;
  gap: var(--sp-2);
  margin: 0;
}

/* 읽는 것이지 누르는 것이 아니다 - 그래서 채우지 않고 테두리만 쓴다. 같은
   화면의 .chip-toggle은 선택되면 흰색으로 채워지므로 둘이 갈린다. */
.guide-badge {
  border: 1px solid var(--text);
  border-radius: 999px;
  padding: 1px var(--sp-2) 2px;
  font-size: 13px;
  font-weight: 550;
}

/* 띠 사이의 선. 타임라인이 없는 보스에서는 문장이 뱃지 바로 아래로 붙는다. */
.fight-timeline,
.guide-card__text,
.guide-card__empty {
  border-top: 1px solid var(--rule);
  padding-top: var(--sp-3);
}

/* 읽을 때는 카드 본문처럼, 클릭하면 그 자리에서 고쳐진다 - 보기/편집 모드를
   나누면 토글 하나가 늘 뿐 버는 것이 없다. */
.guide-card__text {
  font: inherit;
  font-size: 14px;
  line-height: 1.7;
  color: var(--text);
  background: none;
  border: 0;
  border-top: 1px solid var(--rule);
  border-radius: 0;
  padding: var(--sp-3) 0 0;
  resize: vertical;
  min-height: 8rem;
  width: 100%;
  max-width: var(--measure);
}

.guide-card__text::placeholder {
  color: var(--text-muted);
}

.guide-card__text:focus-visible {
  outline: 2px solid var(--accent);
  outline-offset: 2px;
}

.guide-card__empty {
  margin: 0;
  font-size: 14px;
  color: var(--text-muted);
}
```

- [ ] **Step 6: 커밋**

```bash
git add frontend/src/components/SeasonGuideCard.tsx frontend/src/components/SeasonGuideCard.test.tsx frontend/src/App.css
git commit -m "시즌 가이드 카드"
```

---

### Task 9: 배치 — 좌(보스 + 모드) / 우(가이드)

**Files:**
- Modify: `frontend/src/components/RecommendPanel.tsx` (`.recommend-form__setup` 안쪽)
- Modify: `frontend/src/components/RecommendPanel.test.tsx` (통합 테스트 하나)
- Modify: `frontend/src/App.css` (`.recommend-form__setup`)

**Interfaces:**
- Consumes: Task 8의 `SeasonGuideCard`
- Produces: 없음

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`frontend/src/components/RecommendPanel.test.tsx`에:

```tsx
  it('가이드 카드가 보스 설정과 같은 줄에 선다', async () => {
    const user = userEvent.setup()
    render(<RecommendPanel roster={fullRoster} {...noPersistence} />)

    // 접힌 채로도 카드는 서 있다 - 읽는 자리라 펼치는 것과 무관하다.
    expect(screen.getByRole('region', { name: /가이드/ })).toBeInTheDocument()

    // 보스 설정에서 켠 기믹이 카드의 뱃지가 된다.
    await expandBossProfile(user)
    await user.click(screen.getByLabelText('잡몹 생성'))
    expect(screen.getByText('잡몹 생성')).toBeInTheDocument()
  })
```

주: 마지막 `getByText('잡몹 생성')`은 칩의 라벨과 뱃지 둘 다 잡을 수 있다.
빨개지면 `getAllByText('잡몹 생성')`으로 바꾸고 `toHaveLength(2)`를 검사한다 —
그게 「칩에서 켠 것이 뱃지에 나타났다」의 정확한 표현이다.

- [ ] **Step 2: 실패를 확인한다**

Run: `npm --prefix frontend test -- --run src/components/RecommendPanel.test.tsx -t '가이드 카드가 보스 설정과'`
Expected: FAIL — `region` 역할을 가진 가이드 카드가 아직 없다.

- [ ] **Step 3: 회차를 한 번만 계산하고 배치를 바꾼다**

`frontend/src/components/RecommendPanel.tsx`의 import에:

```ts
import { SeasonGuideCard } from './SeasonGuideCard'
```

`return (` 앞, `actionButtons` 정의 근처에:

```tsx
  // 보스 카드 피커와 가이드 카드가 같은 회차를 본다 - 두 번 계산하면 둘이
  // 다른 회차를 가리키는 날이 온다.
  const soloRotation = latestRotationFor(rotations, 'solo')
```

`<div className="recommend-form__setup">` 안쪽을 아래로 바꾼다. `<BossProfileField>`의
props는 그대로 두되 `rotation`만 새 상수를 쓴다.

```tsx
        <div className="recommend-form__setup">
          <div className="recommend-form__controls">
            <BossProfileField
              value={draft}
              errors={touched ? errors : {}}
              onChange={setDraft}
              rotation={soloRotation}
              defaultEnemyDef={SOLO_RAID_DEFAULT_ENEMY_DEF}
              defaultCollapsed
            />

            <fieldset className="group">
              <legend className="group__legend">모드</legend>
              {/* 네 문장을 전부 세워 두면 세로가 길어지고, 정작 지금 무엇을 하려는지는
                  고른 하나가 답한다. 그래서 힌트는 선택된 모드의 것만 아래 한 줄로 선다. */}
              <div className="chip-row">
                {RECOMMEND_MODES.map((option) => (
                  <ToggleChip
                    key={option}
                    type="radio"
                    name="recommend-mode"
                    checked={mode === option}
                    onChange={() => switchMode(option)}
                  >
                    {MODE_LABEL[option]}
                  </ToggleChip>
                ))}
              </div>
              <p className="mode-switch__hint group__hint">
                <HelpText>{MODE_HINT[mode]}</HelpText>
              </p>

              {mode !== 'single' && (
                <div className="field">
                  <label className="field__label" htmlFor={numDecksId}>
                    덱 개수
                  </label>
                  <select
                    id={numDecksId}
                    className="field__input"
                    value={numDecks}
                    onChange={(event) => setNumDecks(Number(event.target.value))}
                  >
                    {NUM_DECKS_OPTIONS.map((n) => (
                      <option key={n} value={n} disabled={n < nonEmptyDeckCount}>
                        {n}
                      </option>
                    ))}
                  </select>
                </div>
              )}
            </fieldset>
          </div>

          <SeasonGuideCard rotation={soloRotation} boss={draft} />
        </div>
```

이 fieldset의 내용은 Task 4가 만든 것과 같고 들여쓰기만 한 단계 깊어진다 —
위 블록이 최종 형태이므로 이대로 두면 된다.

- [ ] **Step 4: 그리드를 고친다**

`frontend/src/App.css`의 `.recommend-form__setup` 블록과 그 위 주석을 통째로 바꾼다.

지우는 것(주석 포함):

```css
/* 모드 컬럼은 내용만큼만 차지한다. 그 안의 문장은 --measure에서 끊기는데
   fieldset의 테두리만 창 끝까지 늘어나면 채우다 만 상자로 읽힌다. 남는 자리는
   테두리 없는 배경이라 여백으로 읽힌다. */
.recommend-form__setup {
  display: grid;
  grid-template-columns: minmax(260px, 22rem) minmax(0, auto);
  justify-content: start;
  gap: var(--sp-4);
  align-items: start;
  width: 100%;
}
```

넣는 것:

```css
/* 왼쪽은 내가 고르는 것(보스 설정 · 모드), 오른쪽은 내가 읽는 것(시즌 가이드).
   보스 설정을 접어 두므로 왼쪽 두 상자는 둘 다 짧고, 남는 가로는 가이드가
   받는다 - 예전에는 이 자리에 모드 하나만 서서 오른쪽 아래가 비어 있었다. */
.recommend-form__setup {
  display: grid;
  grid-template-columns: minmax(260px, 22rem) minmax(0, 1fr);
  gap: var(--sp-4);
  align-items: start;
  width: 100%;
}

.recommend-form__controls {
  display: flex;
  flex-direction: column;
  gap: var(--sp-4);
}
```

바로 아래의 `@media (max-width: 900px)` 블록은 그대로 둔다 — 1컬럼으로 떨어지면
세 상자가 세로로 쌓인다.

- [ ] **Step 5: 통과를 확인한다**

Run: `npm --prefix frontend test -- --run src/components/RecommendPanel.test.tsx`
Expected: PASS

- [ ] **Step 6: 커밋**

```bash
git add frontend/src/components/RecommendPanel.tsx frontend/src/components/RecommendPanel.test.tsx frontend/src/App.css
git commit -m "설정 영역을 좌 컨트롤 / 우 가이드로"
```

---

### Task 10: 전체 검증 — 테스트 · 타입 · lint · 눈

**Files:**
- Modify: 없음 (고칠 것이 나오면 그때 고친다)

**Interfaces:**
- Consumes: Task 1~9 전부
- Produces: 없음

- [ ] **Step 1: 프론트 전체 테스트**

Run: `npm --prefix frontend test -- --run`
Expected: PASS. 기준선은 **970 passed / 74 files**였고, 이 계획이 더한 새 파일 5개
(`bossBadges` · `ToggleChip` · `useBossGuides` · `FightTimeline` · `SeasonGuideCard`)와
새 테스트들만큼 늘어야 한다. **줄어들면 회귀다.**

- [ ] **Step 2: 타입체크**

Run: `npx --prefix frontend tsc -b --noEmit frontend`
Expected: 출력 없음(에러 0). vitest는 타입을 안 보므로 이 단계를 건너뛰면 안 된다.

- [ ] **Step 3: lint**

Run: `npm --prefix frontend run lint`
Expected: 에러 0.

- [ ] **Step 4: 죽은 클래스가 남아 있지 않은지 확인**

Run: `grep -rn "className=\"checkbox\|className=\"radio\|checkbox-row" frontend/src`
Expected: 아무것도 안 나온다.

Run: `grep -n "\.checkbox\b\|\.checkbox-row\|\.radio\b\|\.mode-switch {" frontend/src/App.css`
Expected: 아무것도 안 나온다.

- [ ] **Step 5: 앱을 띄워 눈으로 본다**

CSS는 vitest에 안 보인다(`css: false`). 두 서버를 띄운다:

```bash
# 터미널 1 - 백엔드. 8000에 Fienn의 개발 백엔드가 이미 떠 있으면 그걸 쓴다(죽이지 말 것).
cd backend && python -m uvicorn app.api:app --port 8000
# 터미널 2 - 프론트
npm --prefix frontend run dev
```

`http://localhost:5173`의 **솔로 레이드** 탭에서 확인할 것:

1. 보스 설정이 **접힌 채로** 뜨고, 머리 한 줄(속성 아이콘 + 이름)만 보인다.
2. 오른쪽에 가이드 카드가 서고 **오른쪽 아래가 비지 않는다**.
3. 기믹 칩을 켜면 **흰색으로 채워지고**, 가이드 카드의 **테두리 뱃지**와 확실히
   구분된다. 이게 이 디자인의 핵심 판정이다 — 둘이 같은 것으로 보이면 실패다.
4. 켜진 칩 안의 `?` 설명 버튼이 흰 바닥 위에서 보인다.
5. 40시즌 보스(사치스러운 거미)를 고르면 타임라인에 `파괴 1 · 61 · 126초`가 뜬다.
6. 창을 900px 아래로 줄이면 세 상자가 세로로 쌓이고 가로 스크롤이 안 생긴다.
7. 탭 키로 칩 사이를 옮길 때 포커스 테두리가 보인다.

- [ ] **Step 6: 스크린샷을 Fienn에게 보낸다**

솔로 탭 전체가 나오게 한 장, 기믹 칩을 몇 개 켠 상태로 한 장.
**타임라인을 남길지 뺄지는 이 스크린샷을 보고 Fienn이 정한다**(2026-08-20 판단).

- [ ] **Step 7: 백그라운드 dev 서버를 정리한다**

`npm run dev`를 백그라운드로 띄웠다면 node 자식이 `frontend/`를 잡은 채 남아
워크트리 삭제가 「Device or resource busy」로 막힌다. 경로로 골라서 죽인다:

```powershell
Get-CimInstance Win32_Process | Where-Object { $_.CommandLine -like '*solo-raid-setup-layout*' }
```

Fienn의 8000 백엔드는 건드리지 말 것.

- [ ] **Step 8: 커밋**

이 단계에서 고친 것이 있으면:

```bash
git add -u
git commit -m "전체 검증에서 나온 것들"
```

없으면 커밋하지 않는다.

---

## 다음 단계 (이 계획 밖)

2단계는 `data/raid-rotations.json` 스키마 확장 하나로 두 가지를 같이 한다:

- **보스 이미지** — 공지 이미지를 받아 `frontend/public/bosses/`에 커밋하고 회차
  보스가 파일명을 갖는다. 공지 이미지 URL은 서명 URL이라 만료되므로 링크가 아니라
  받아서 커밋해야 한다(`docs/decisions.md` 2026-08-07).
- **가이드 텍스트** — 회차 보스의 `guide`가 `useBossGuides.guideFor(key, fallback)`의
  fallback 자리에 들어간다. 그때 비로소 가이드가 릴리즈 빌드에 실린다
  (`packaging/rapilab.spec`의 `datas`가 `data/`를 담는다). 「기본값으로 되돌리기」가
  같이 붙는다.

둘 다 백엔드 모델 · 로더 · `/update-raid-bosses` 스킬 · 테스트를 지나므로 한 번에
하는 것이 맞다.
