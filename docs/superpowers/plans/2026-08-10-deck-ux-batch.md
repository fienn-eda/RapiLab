# 덱 편성 조작과 표기 9건 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 덱 편성 화면의 조작 결함 3건·표기 결함 3건·동작 버그 1건·접기 1건을 고치고, 유닛 카드 클릭 표적을 카드 전체로 넓힌다.

**Architecture:** 전부 `frontend/` 안에서 끝난다. 백엔드·엔진·wire 타입은 건드리지 않는다. 새 파일은 라벨 헬퍼 하나(`lib/bossLabel.ts`)뿐이고 나머지는 기존 컴포넌트 수정이다. 보스 이름을 `BossProfileDraft`로 끌어올리는 것이 §6 덱 라벨과 §8 접기 머리를 동시에 먹여 살린다.

**Tech Stack:** React 19 + TypeScript + Vite, Vitest(`environment: 'jsdom'`, `css: false`) + @testing-library/react + @testing-library/user-event.

설계문서: `docs/superpowers/specs/2026-08-10-deck-ux-batch-design.md`

## Global Constraints

- **작업 디렉터리는 `frontend/`다.** 모든 테스트 명령은 거기서 돈다.
- **테스트: `cd frontend && npx vitest run <경로>`**. 전체는 `npx vitest run`.
- **`npm test`는 타입을 안 본다.** 각 태스크 커밋 전에 `npx tsc -b --noEmit`을 따로 돌린다.
- **CSS로 숨기지 않는다.** Vitest가 `css: false`라 CSS로 감춘 요소는 쿼리에 계속 잡힌다. 「안 보인다」는 언마운트로 구현한다.
- **화면에 나오는 설명 문장은 `frontend/src/lib/helpText.ts`에 둔다.** 라벨·버튼 이름은 컴포넌트에 남는다. 테스트는 문구를 하드코딩하지 말고 `HELP.…`를 참조한다.
- **기존 한국어 톤을 따른다** — `~해요` 체.
- **주석은 WHAT/WHY만.** 「예전엔 이랬다」를 쓰지 않는다.
- **커밋은 태스크마다 한 번.** 메시지는 한국어 한 줄.

## File Structure

| 파일 | 책임 | 태스크 |
|---|---|---|
| `src/hooks/useProfiles.ts` | 보관 상한 거절을 호출부에 정확히 알린다 | 1 |
| `src/components/MirandaTargets.tsx` | 파워업! 두 뱃지가 같은 횟수를 단다 | 2 |
| `src/lib/bossLabel.ts` **(신규)** | 약점 낱말과 보스 머리 라벨을 한 곳에서 만든다 | 3 |
| `src/types/bossProfileDraft.ts` | 보스 이름을 draft가 들고 다닌다 | 4 |
| `src/components/BossProfileField.tsx` | 이름을 쓰고 지운다 / 접기 | 4, 12 |
| `src/components/UnionRaidPanel.tsx` | 저장 이름·덱 라벨을 공급한다 | 5, 6 |
| `src/components/DraftEditor.tsx` | 덱 라벨 표시 / 집기·놓기 | 6, 9, 10, 11 |
| `src/components/NikkeCard.tsx` | 카드 전체가 제외 토글 | 7 |
| `src/components/UnitPalette.tsx` | 칩 전체가 배치, 제외는 막힘 | 8 |
| `src/components/RecommendPanel.tsx` | 솔로 팔레트도 같은 교체 배선 | 11 |
| `src/lib/helpText.ts` | 바뀐 조작을 설명한다 | 11 |
| `src/App.css` | 커서·들린 표시·아이콘 여백 | 6–9, 12 |

---

### Task 1: 첫 저장인데 뜨는 보관 상한 경고를 고친다

설계 §7. 순수 함수 `saveRun`은 멀쩡하다 — 깨진 것은 그 거절 신호를 React 밖으로 옮기는 배선이다.

**Files:**
- Modify: `frontend/src/hooks/useProfiles.ts:165-175`
- Test: `frontend/src/hooks/useProfiles.test.ts`

**Interfaces:**
- Consumes: `pureSaveRun(state, key, run)` — 상한이면 `state`를 그대로 돌려준다(참조 동일성이 거절 신호).
- Produces: `saveRun({key, run}): boolean` — 시그니처 불변. 의미만 고쳐진다.

- [ ] **Step 1: 재현하는 실패 테스트를 쓴다**

`frontend/src/hooks/useProfiles.test.ts` 끝에 추가한다:

```ts
import { renderHook, act } from '@testing-library/react'
import { useProfiles } from './useProfiles'

describe('saveRun 거절 신호', () => {
  it('빈 프로필에 첫 저장은 거절되지 않는다', () => {
    localStorage.clear()
    const { result } = renderHook(() => useProfiles())

    act(() => {
      result.current.upsertProfile({
        openId: 'A', area: 81, name: '테스트', roster: [], drafts: [],
      })
    })
    const key = result.current.state.activeKey!

    let accepted: boolean | undefined
    act(() => {
      accepted = result.current.saveRun({
        key,
        run: { id: '1-0', name: '첫 저장', savedAt: 1, tab: 'union', view: null as never },
      })
    })

    expect(accepted).toBe(true)
    expect(result.current.activeProfile!.savedRuns).toHaveLength(1)
  })

  it('상한에 찬 프로필에서만 거절한다', () => {
    localStorage.clear()
    const { result } = renderHook(() => useProfiles())
    act(() => {
      result.current.upsertProfile({
        openId: 'B', area: 81, name: '가득', roster: [], drafts: [],
      })
    })
    const key = result.current.state.activeKey!

    act(() => {
      for (let i = 0; i < SAVED_RUNS_CAP; i++) {
        result.current.saveRun({
          key,
          run: { id: `${i}-0`, name: `#${i}`, savedAt: i, tab: 'union', view: null as never },
        })
      }
    })

    let accepted: boolean | undefined
    act(() => {
      accepted = result.current.saveRun({
        key,
        run: { id: 'over', name: '넘침', savedAt: 999, tab: 'union', view: null as never },
      })
    })

    expect(accepted).toBe(false)
    expect(result.current.activeProfile!.savedRuns).toHaveLength(SAVED_RUNS_CAP)
  })
})
```

`upsertProfile`의 실제 인자 모양은 `useProfiles.ts`의 `upsert` 정의를 열어 그대로 맞춘다. 위 필드 이름이 다르면 **테스트가 아니라 호출을 고친다** — 훅의 계약이 정답이다.

- [ ] **Step 2: 실패를 확인한다**

```bash
cd frontend && npx vitest run src/hooks/useProfiles.test.ts -t '거절 신호'
```

기대: 첫 번째 테스트가 `expected true, received false`로 실패. **이 실패를 눈으로 확인하지 않고 다음으로 넘어가지 않는다.** 만약 두 테스트가 다 통과하면 원인이 `useProfiles`가 아니라 `App.tsx`의 `state.activeKey` 경로다 — 그때는 Step 3 대신 `App.tsx:242-243`과 `:275-276`을 조사하고, 무엇이 진짜 원인이었는지 계획서에 적은 뒤 진행한다.

- [ ] **Step 3: 판정을 setState 밖으로 꺼낸다**

`useProfiles.ts`의 `keepRun`을 통째로 바꾼다:

```ts
  /** 상한에 걸려 거절됐는지를 돌려준다 - 저장이 조용히 안 되는 화면을 만들지
   * 않기 위해서다. 판정은 setState 밖에서 끝낸다: React는 업데이터를 즉시
   * 실행한다고 약속하지 않아서, 업데이터 안에서 정한 값을 밖에서 읽으면
   * 아직 안 정해진 값을 읽는다. */
  const keepRun = useCallback(
    (args: { key: string; run: SavedRun }): boolean => {
      const profile = state.profiles[args.key]
      if (!profile || profile.savedRuns.length >= SAVED_RUNS_CAP) return false
      setState((current) => pureSaveRun(current, args.key, args.run))
      return true
    },
    [state],
  )
```

`SAVED_RUNS_CAP`을 import 목록에 더한다(`../types/profile`).

- [ ] **Step 4: 통과를 확인한다**

```bash
cd frontend && npx vitest run src/hooks/useProfiles.test.ts
npx tsc -b --noEmit
```

기대: 전부 PASS, 타입에러 0.

- [ ] **Step 5: 커밋**

```bash
git add frontend/src/hooks/useProfiles.ts frontend/src/hooks/useProfiles.test.ts
git commit -m "보관 상한 판정을 setState 밖으로 - 첫 저장이 거절로 읽히던 것을 고친다"
```

---

### Task 2: 미란다 공격력 뱃지에 횟수를 붙인다

설계 §4. 공격력과 크댐은 같은 `powerCount`에서 나오는데 횟수가 크댐에만 붙어 있다.

**Files:**
- Modify: `frontend/src/components/MirandaTargets.tsx:105-113`
- Test: `frontend/src/components/MirandaTargets.test.tsx`

**Interfaces:**
- Consumes: `powerCount`(이미 계산됨), `total`(전체 사이클 수).
- Produces: 없음.

- [ ] **Step 1: 실패 테스트를 쓴다**

`MirandaTargets.test.tsx`에 추가한다. 기존 테스트의 렌더 헬퍼와 픽스처 모양을 그대로 재사용하되, **일부 사이클에서만 파워업!을 받는 유닛**이 있어야 한다(전 사이클이면 `n/T`가 아예 안 붙는 게 정상이라 아무것도 못 잰다):

```ts
it('공격력 뱃지도 크댐과 같은 횟수를 단다', () => {
  // 두 사이클 중 한 번만 파워업! 대상이 되는 유닛
  renderTargets({
    cycles: [
      { poweringUp: ['liter'], wakeUpCritRate: [] },
      { poweringUp: [], wakeUpCritRate: [] },
    ],
  })

  const row = screen.getByLabelText('Liter')
  const atkBadge = within(row).getByText('공격력').closest('.miranda-badge')!
  const critBadge = within(row).getByText('크댐').closest('.miranda-badge')!

  expect(atkBadge).toHaveTextContent('1/2')
  expect(critBadge).toHaveTextContent('1/2')
})
```

`renderTargets`/`cycles` prop의 실제 이름과 모양은 `MirandaTargets.test.tsx` 위쪽 기존 테스트에서 복사한다. 컴포넌트가 `cycles`를 어떤 필드명으로 받는지는 `MirandaTargets.tsx:26`(`cycle.wakeUpCritRate`)과 `poweringUp` 사용부를 보고 맞춘다.

- [ ] **Step 2: 실패를 확인한다**

```bash
cd frontend && npx vitest run src/components/MirandaTargets.test.tsx -t '공격력 뱃지'
```

기대: FAIL — `atkBadge`가 `1/2`를 안 가짐.

- [ ] **Step 3: 한 줄을 고친다**

`MirandaTargets.tsx`의 공격력 뱃지를 크댐과 같은 모양으로 만든다:

```tsx
                  {powerCount > 0 && (
                    <>
                      <span className="miranda-badge miranda-badge--silver">
                        <span>공격력</span>
                        {powerCount < total && <b>{powerCount}/{total}</b>}
                      </span>
                      <span className="miranda-badge miranda-badge--silver">
                        <span>크댐</span>
                        {powerCount < total && <b>{powerCount}/{total}</b>}
                      </span>
                    </>
                  )}
```

- [ ] **Step 4: 통과를 확인한다**

```bash
cd frontend && npx vitest run src/components/MirandaTargets.test.tsx
npx tsc -b --noEmit
```

- [ ] **Step 5: 커밋**

```bash
git add frontend/src/components/MirandaTargets.tsx frontend/src/components/MirandaTargets.test.tsx
git commit -m "미란다 공격력 뱃지에도 사이클 횟수를 붙인다 - 같은 파워업!인데 크댐에만 있었다"
```

---

### Task 3: 보스 라벨 헬퍼를 만든다

설계 §5·§6·§8이 전부 같은 낱말을 쓴다. 세 곳에 흩어 쓰면 셋이 따로 낡는다.

**Files:**
- Create: `frontend/src/lib/bossLabel.ts`
- Test: `frontend/src/lib/bossLabel.test.ts`

**Interfaces:**
- Consumes: `weaknessFor` (`lib/elementAdvantage`), `elementLabel` (`lib/elementName`), `WEAKNESS_ICON` (`lib/elementIcon`), `BossElement` (`types/recommend`).
- Produces — 뒤 태스크가 이 이름 그대로 쓴다:
  - `weaknessLabelOf(element: BossElement): string` — `null`이면 `'약점없음'`.
  - `interface BossHeading { text: string; iconSrc: string | null }`
  - `bossHeading(args: { bossName: string | null; element: BossElement; fallback: string }): BossHeading`

- [ ] **Step 1: 실패 테스트를 쓴다**

`frontend/src/lib/bossLabel.test.ts`:

```ts
import { describe, it, expect } from 'vitest'
import { bossHeading, weaknessLabelOf } from './bossLabel'

describe('weaknessLabelOf', () => {
  it('보스 속성을 그 약점의 이름으로 바꾼다', () => {
    // 작열 보스의 약점은 수냉
    expect(weaknessLabelOf('Fire')).toBe('수냉')
    expect(weaknessLabelOf('Water')).toBe('전격')
  })

  it('속성이 없으면 자리를 지키는 낱말을 준다', () => {
    expect(weaknessLabelOf(null)).toBe('약점없음')
  })
})

describe('bossHeading', () => {
  it('보스 이름이 있으면 이름과 약점 아이콘을 준다', () => {
    const h = bossHeading({ bossName: '인디비리아', element: 'Fire', fallback: '덱 1' })
    expect(h.text).toBe('인디비리아')
    expect(h.iconSrc).toBe('/elements/water.png')
  })

  it('이름이 없고 속성만 있으면 약점 이름을 쓴다', () => {
    const h = bossHeading({ bossName: null, element: 'Fire', fallback: '덱 1' })
    expect(h.text).toBe('수냉')
    expect(h.iconSrc).toBe('/elements/water.png')
  })

  it('둘 다 없으면 부르는 쪽이 준 이름으로 돌아간다', () => {
    const h = bossHeading({ bossName: null, element: null, fallback: '덱 1' })
    expect(h.text).toBe('덱 1')
    expect(h.iconSrc).toBeNull()
  })

  // 이름은 그 속성의 보스를 가리켜 붙은 것이다. 속성이 없으면 이름도 가리킬
  // 대상이 없다.
  it('속성 없이 이름만 있으면 폴백으로 돌아간다', () => {
    const h = bossHeading({ bossName: '인디비리아', element: null, fallback: '덱 1' })
    expect(h.text).toBe('덱 1')
    expect(h.iconSrc).toBeNull()
  })
})
```

`weaknessLabelOf('Water')`의 기대값은 **먼저 `lib/elementAdvantage.ts`의 `weaknessFor`를 열어 확인하고** 실제 값으로 적는다. 위 `'전격'`은 확인 전 값이다 — 다르면 테스트를 실제 값으로 고친다.

- [ ] **Step 2: 실패를 확인한다**

```bash
cd frontend && npx vitest run src/lib/bossLabel.test.ts
```

기대: FAIL — 모듈이 없음.

- [ ] **Step 3: 헬퍼를 만든다**

`frontend/src/lib/bossLabel.ts`:

```ts
// 보스를 한 줄로 부르는 이름. 유니온 저장 이름, 덱 라벨, 접힌 보스 설정 머리가
// 같은 낱말을 써야 해서 여기 한 곳에서 만든다.

import { weaknessFor } from './elementAdvantage'
import { elementLabel } from './elementName'
import { WEAKNESS_ICON } from './elementIcon'
import type { BossElement } from '../types/recommend'

/** 이 보스의 약점 속성 이름. 속성을 안 고른 보스도 자리를 지켜야 하는 곳
 * (유니온 저장 이름의 덱 나열)이 있어서 빈 문자열이 아니라 낱말을 준다. */
export const weaknessLabelOf = (element: BossElement): string =>
  element === null ? '약점없음' : elementLabel(weaknessFor(element))

export interface BossHeading {
  text: string
  /** 약점 속성 아이콘. 부를 이름이 폴백뿐이면 null. */
  iconSrc: string | null
}

/** 보스를 부르는 이름 세 단계: 고른 보스 이름 → 약점 이름 → 부르는 쪽이 준
 * 폴백. 이름은 속성이 있을 때만 쓴다 - 속성이 없으면 그 이름이 가리키던 보스도
 * 없다. */
export const bossHeading = (args: {
  bossName: string | null
  element: BossElement
  fallback: string
}): BossHeading => {
  if (args.element === null) return { text: args.fallback, iconSrc: null }
  const iconSrc = WEAKNESS_ICON[weaknessFor(args.element)]
  return { text: args.bossName ?? weaknessLabelOf(args.element), iconSrc }
}
```

- [ ] **Step 4: 통과를 확인한다**

```bash
cd frontend && npx vitest run src/lib/bossLabel.test.ts
npx tsc -b --noEmit
```

- [ ] **Step 5: 커밋**

```bash
git add frontend/src/lib/bossLabel.ts frontend/src/lib/bossLabel.test.ts
git commit -m "보스를 한 줄로 부르는 이름을 한 곳에서 만든다 - 저장 이름·덱 라벨·접힌 머리가 같은 낱말을 쓴다"
```

---

### Task 4: 보스 이름을 draft로 끌어올린다

설계 §6. 지금 이름은 `BossProfileField`의 로컬 상태라 부모가 못 본다.

**Files:**
- Modify: `frontend/src/types/bossProfileDraft.ts:7-32, 48-66`
- Modify: `frontend/src/components/BossProfileField.tsx:175-201, 218-224, 246, 259`
- Test: `frontend/src/components/BossProfileField.test.tsx`

**Interfaces:**
- Produces: `BossProfileDraft.boss_name: string | null`. 뒤 태스크가 이 필드명을 그대로 읽는다.
- **wire로 새지 않는다**: `validateBossProfileDraft`가 `BossProfile`을 필드별로 나열해 만들므로 아무것도 안 해도 안 샌다. `BossProfile`에는 절대 더하지 않는다.

- [ ] **Step 1: 실패 테스트를 쓴다**

`BossProfileField.test.tsx`에 추가한다:

```tsx
it('회차 보스를 고르면 그 이름을 draft에 담아 올린다', async () => {
  const onChange = vi.fn()
  renderField({ onChange, rotation: ROTATION })

  await userEvent.click(screen.getByRole('radio', { name: /인디비리아/ }))

  expect(onChange).toHaveBeenCalledWith(
    expect.objectContaining({ boss_name: '인디비리아' }),
  )
})

// 라벨이 거짓말하지 않게 하는 가드. 이름은 그 속성의 보스를 가리켜 붙은 것이라,
// 속성을 손으로 바꾸면 가리킬 대상이 없어진다.
it('속성을 직접 바꾸면 보스 이름을 버린다', async () => {
  const onChange = vi.fn()
  renderField({
    onChange,
    rotation: ROTATION,
    value: { ...makeDefaultBossProfileDraft(), element: 'Fire', boss_name: '인디비리아' },
  })

  await userEvent.click(screen.getByRole('radio', { name: '전격' }))

  expect(onChange).toHaveBeenCalledWith(expect.objectContaining({ boss_name: null }))
})

it('약점 없음을 골라도 보스 이름을 버린다', async () => {
  const onChange = vi.fn()
  renderField({
    onChange,
    rotation: ROTATION,
    value: { ...makeDefaultBossProfileDraft(), element: 'Fire', boss_name: '인디비리아' },
  })

  await userEvent.click(screen.getByRole('radio', { name: '약점 없음' }))

  expect(onChange).toHaveBeenCalledWith(expect.objectContaining({ boss_name: null }))
})
```

`renderField`/`ROTATION`은 기존 테스트 파일 위쪽 것을 재사용한다. 라디오의 접근 이름(`'전격'`, `'약점 없음'`)은 `BossProfileField.tsx:249,261`의 `element-picker__name` 텍스트와 같다.

- [ ] **Step 2: 실패를 확인한다**

```bash
cd frontend && npx vitest run src/components/BossProfileField.test.tsx -t '보스 이름'
```

기대: FAIL — `boss_name`이 타입에도 값에도 없음.

- [ ] **Step 3: draft에 칸을 만든다**

`types/bossProfileDraft.ts`:

```ts
export interface BossProfileDraft {
  element: BossElement
  /** 회차에서 고른 보스 이름. 표시 전용이라 BossProfile(wire)에는 가지 않는다.
   * 속성이 손으로 바뀌면 null로 돌아간다 - 이름이 가리키던 보스가 아니게 된다. */
  boss_name: string | null
  core_hittable: boolean
  // …나머지 기존 필드 그대로
}
```

`makeDefaultBossProfileDraft`에 `boss_name: null`을 더한다.

`bossProfileToDraft`에도 `boss_name: null`을 더한다 — 저장된 wire에는 이름이 없으므로 복원하면 약점 이름으로 돌아간다. 그 자리에 주석을 남긴다:

```ts
  // wire에는 이름이 없다. 복원한 폼은 약점 이름으로 자기를 부른다.
  boss_name: null,
```

- [ ] **Step 4: 이름을 쓰고 지우게 만든다**

`BossProfileField.tsx`에서:

1. `const [pickedName, setPickedName] = useState<string | null>(null)`과 `picked`/`selectedName` 파생 세 줄을 지운다.
2. 대신 한 줄:

```tsx
  // 이름은 값에 실려 오므로 파생 가드가 필요 없다 - 속성을 바꾸는 모든 길이
  // 이름을 같이 지운다.
  const selectedName = value.boss_name
```

3. `pickRotationBoss`에서 `setPickedName(boss.name)`을 지우고 `onChange`에 이름을 싣는다:

```tsx
    onChange({
      ...makeDefaultBossProfileDraft(defaultEnemyDef),
      element: bossElementFor(boss.weakness),
      boss_name: boss.name,
      effective_range_band: boss.range_band,
      // …나머지 기존 그대로
    })
```

4. 속성 라디오 두 곳에서 이름을 지운다:

```tsx
  onChange={() => onChange({ ...value, element: bossElement, boss_name: null })}
```
```tsx
  onChange={() => onChange({ ...value, element: null, boss_name: null })}
```

- [ ] **Step 5: 통과를 확인한다**

```bash
cd frontend && npx vitest run src/components/BossProfileField.test.tsx src/types
npx tsc -b --noEmit
```

타입 체커가 `boss_name` 없이 `BossProfileDraft`를 만드는 자리를 전부 짚어 준다. 짚어 주는 곳마다 `boss_name: null`을 더한다 — **옵셔널로 만들어 침묵시키지 않는다.**

- [ ] **Step 6: 전체 프론트 스위트를 돌린다**

```bash
cd frontend && npx vitest run
```

기대: 전부 PASS.

- [ ] **Step 7: 커밋**

```bash
git add frontend/src/types/bossProfileDraft.ts frontend/src/components/BossProfileField.tsx frontend/src/components/BossProfileField.test.tsx
git commit -m "보스 이름을 draft에 실어 부모가 읽게 한다 - 속성을 바꾸면 이름을 버린다"
```

---

### Task 5: 유니온 저장 이름을 덱별 약점 나열로 바꾼다

설계 §5.

**Files:**
- Modify: `frontend/src/components/UnionRaidPanel.tsx:59-64, 258`
- Test: `frontend/src/components/UnionRaidPanel.test.tsx`

**Interfaces:**
- Consumes: `weaknessLabelOf` (Task 3).
- Produces: `suggestUnionRunName(bosses: BossProfileDraft[]): string`.

- [ ] **Step 1: 실패 테스트를 쓴다**

`UnionRaidPanel.tsx`에서 `suggestUnionRunName`을 **export** 하고 순수 함수로 직접 잰다:

```ts
import { suggestUnionRunName } from './UnionRaidPanel'
import { makeDefaultBossProfileDraft } from '../types/bossProfileDraft'

describe('suggestUnionRunName', () => {
  const boss = (element: BossElement) => ({ ...makeDefaultBossProfileDraft(), element })

  it('덱 순서대로 약점을 나열한다', () => {
    expect(suggestUnionRunName([boss('Fire'), boss('Water'), boss('Iron')]))
      .toBe('수냉 전격 화염')
  })

  it('속성을 안 고른 덱도 자리를 지킨다', () => {
    expect(suggestUnionRunName([boss('Fire'), boss(null), boss('Fire')]))
      .toBe('수냉 약점없음 수냉')
  })

  it('날짜를 붙이지 않는다 - 목록이 저장 시각을 따로 찍는다', () => {
    expect(suggestUnionRunName([boss('Fire')])).toBe('수냉')
  })
})
```

기대 낱말(`'전격'`, `'화염'`)은 Task 3에서 확인한 `weaknessFor` 실제 값으로 적는다.

- [ ] **Step 2: 실패를 확인한다**

```bash
cd frontend && npx vitest run src/components/UnionRaidPanel.test.tsx -t 'suggestUnionRunName'
```

기대: FAIL — export가 없거나 형식이 다름.

- [ ] **Step 3: 함수를 바꾼다**

`UnionRaidPanel.tsx`의 기존 `suggestUnionRunName`을 통째로 교체한다:

```ts
/** 유니온은 전투마다 보스가 달라 하나를 이름에 뽑을 수 없다 — 덱 순서대로
 * 약점을 나열한다. 날짜는 넣지 않는다: 보관 목록이 이름 옆에 저장 시각을
 * 항상 따로 찍는다. */
export const suggestUnionRunName = (bosses: BossProfileDraft[]): string =>
  bosses.map((boss) => weaknessLabelOf(boss.element)).join(' ')
```

import에 `weaknessLabelOf`(`../lib/bossLabel`)를 더하고, 이제 안 쓰는 것이 있으면 지운다.

- [ ] **Step 4: 호출부를 고친다**

`UnionRaidPanel.tsx:258`:

```tsx
              suggestedName={suggestUnionRunName(bosses.slice(0, numBattles))}
```

`numBattles`가 줄어도 안 쓰는 보스가 이름에 끼지 않도록 자른다.

- [ ] **Step 5: 통과를 확인한다**

```bash
cd frontend && npx vitest run src/components/UnionRaidPanel.test.tsx
npx tsc -b --noEmit
```

기존 테스트 중 `유니온 3전투 · 08-10` 형식을 기대하는 것이 있으면 새 형식으로 고친다.

- [ ] **Step 6: 커밋**

```bash
git add frontend/src/components/UnionRaidPanel.tsx frontend/src/components/UnionRaidPanel.test.tsx
git commit -m "유니온 저장 이름을 덱별 약점 나열로 - 무슨 보스를 잰 것인지 이름이 말한다"
```

---

### Task 6: 덱 라벨을 보스 이름 + 약점 아이콘으로

설계 §6. `DraftEditor`는 솔로도 쓰는데 솔로는 보스가 하나뿐이라, 라벨은 **넘겨줄 때만** 바뀐다.

**Files:**
- Modify: `frontend/src/components/DraftEditor.tsx:21-52, 268-295`
- Modify: `frontend/src/components/UnionRaidPanel.tsx` (DraftEditor 호출부)
- Test: `frontend/src/components/DraftEditor.test.tsx`, `frontend/src/components/UnionRaidPanel.test.tsx`

**Interfaces:**
- Consumes: `BossHeading`, `bossHeading` (Task 3), `BossProfileDraft.boss_name` (Task 4).
- Produces: `DraftEditorProps.deckLabels?: BossHeading[]` — 없으면 지금처럼 `덱 N`.

- [ ] **Step 1: 실패 테스트를 쓴다**

`DraftEditor.test.tsx`의 `describe('DraftEditor')` 안에 추가한다:

```tsx
it('덱 라벨을 넘기면 그 이름과 아이콘으로 부른다', () => {
  const { container } = render(
    <DraftEditor
      numDecks={2}
      value={makeEmptyDraft(2)}
      onChange={() => {}}
      portraitFor={() => null}
      nameFor={nameFromSlug}
      burstTiersFor={() => []}
      deckLabels={[
        { text: '인디비리아', iconSrc: '/elements/water.png' },
        { text: '수냉', iconSrc: '/elements/water.png' },
      ]}
    />,
  )
  expect(screen.getByRole('heading', { name: /인디비리아/ })).toBeInTheDocument()
  expect(screen.getByRole('heading', { name: /수냉/ })).toBeInTheDocument()
  expect(container.querySelectorAll('.draft-editor__deck-icon')).toHaveLength(2)
})

it('덱 라벨이 없으면 지금처럼 자리 번호로 부른다', () => {
  editor(2, makeEmptyDraft(2))
  expect(screen.getByRole('heading', { name: /덱 1/ })).toBeInTheDocument()
})

// 좌석 컨트롤은 자리 번호를 유지한다 - 「인디비리아에서 Crown 제거」는 어느
// 자리인지 말하지 않는다.
it('좌석 컨트롤은 덱 라벨과 무관하게 자리 번호로 말한다', () => {
  render(
    <DraftEditor
      numDecks={1}
      value={{ decks: [[{ slug: 'crown', locked: false }]] }}
      onChange={() => {}}
      portraitFor={() => null}
      nameFor={nameFromSlug}
      burstTiersFor={(slug) => (slug === 'crown' ? [1] : [])}
      deckLabels={[{ text: '인디비리아', iconSrc: '/elements/water.png' }]}
    />,
  )
  expect(screen.getByRole('button', { name: /덱 1에서 Crown/ })).toBeInTheDocument()
})
```

- [ ] **Step 2: 실패를 확인한다**

```bash
cd frontend && npx vitest run src/components/DraftEditor.test.tsx -t '덱 라벨'
```

기대: FAIL — `deckLabels` prop이 없음.

- [ ] **Step 3: prop을 더한다**

`DraftEditorProps`에:

```ts
  /** 덱마다 그 덱이 무엇인지 부르는 이름. 유니온만 넘긴다 - 솔로는 덱이 여럿
   * 이어도 보스가 하나라 덱마다 다르게 부를 것이 없다. 없으면 자리 번호로
   * 부른다. */
  deckLabels?: BossHeading[]
```

import에 `import type { BossHeading } from '../lib/bossLabel'`를 더하고, 구조분해에 `deckLabels`를 더한다.

- [ ] **Step 4: 제목을 그린다**

`DraftEditor.tsx:268-295`의 `<h4>` 안쪽을 바꾼다. 데크 루프 안, `const seats = …` 아래에 한 줄:

```tsx
          const label = deckLabels?.[deckIndex] ?? null
          const deckName = label?.text ?? `덱 ${deckIndex + 1}`
```

그리고 제목:

```tsx
              <h4 className="draft-editor__deck-title">
                {label?.iconSrc && (
                  <img className="draft-editor__deck-icon" src={label.iconSrc} alt="" />
                )}
                {picksDeck ? (
                  <button
                    type="button"
                    className="draft-editor__deck-pick"
                    aria-pressed={activeDeck === deckIndex}
                    // 조사 없이 쓴다 - 「덱 N을/를」은 N을 읽은 소리의 받침이
                    // 정하는데(1·3·6·7·8은 을, 2·4·5·9는 를), 그걸 위해 숫자
                    // 읽기 표를 들일 만한 문장이 아니다. 자리 번호를 앞에 두어
                    // 보스 이름으로 불러도 몇 번째인지 잃지 않는다.
                    aria-label={`덱 ${deckIndex + 1} ${deckName} 활성 덱으로 선택`}
                    onClick={() => onActiveDeckChange(deckIndex)}
                  >
                    {deckName}
                  </button>
                ) : (
                  <>{deckName}</>
                )}
                {/* 이하 missing / count는 기존 그대로 */}
```

`aria-label`이 라벨 없을 때 `덱 1 덱 1 활성 덱으로 선택`이 되지 않도록, 라벨이 없으면 기존 문구를 쓴다:

```tsx
                    aria-label={
                      label
                        ? `덱 ${deckIndex + 1} ${deckName} 활성 덱으로 선택`
                        : `덱 ${deckIndex + 1} 활성 덱으로 선택`
                    }
```

`const where = \`덱 ${deckIndex + 1}\`` 는 **그대로 둔다** — 좌석 컨트롤은 자리 번호로 말한다.

- [ ] **Step 5: 유니온이 라벨을 공급한다**

`UnionRaidPanel.tsx`에서 `DraftEditor` 호출부에 더한다:

```tsx
              deckLabels={bosses.slice(0, numBattles).map((boss, i) =>
                bossHeading({
                  bossName: boss.boss_name,
                  element: boss.element,
                  fallback: `덱 ${i + 1}`,
                }),
              )}
```

import에 `bossHeading`(`../lib/bossLabel`)을 더한다.

- [ ] **Step 6: 아이콘 여백 CSS**

`frontend/src/App.css`에 더한다. 값은 기존 `.draft-editor__deck-title` 규칙 옆에 두고 그 파일의 간격 단위를 따른다:

```css
.draft-editor__deck-icon {
  width: 16px;
  height: 16px;
  vertical-align: -2px;
}
```

- [ ] **Step 7: 통과를 확인한다**

```bash
cd frontend && npx vitest run
npx tsc -b --noEmit
```

- [ ] **Step 8: 커밋**

```bash
git add frontend/src/components/DraftEditor.tsx frontend/src/components/DraftEditor.test.tsx frontend/src/components/UnionRaidPanel.tsx frontend/src/App.css
git commit -m "유니온 덱을 보스 이름과 약점 아이콘으로 부른다 - 솔로는 자리 번호 그대로"
```

---

### Task 7: 니케 풀 카드 전체를 제외 토글로

설계 §1. 버튼이 초상화만 감싸서 오버로드·이름·스킬레벨을 눌러도 아무 일이 없다.

**Files:**
- Modify: `frontend/src/components/NikkeCard.tsx:45-89`
- Test: `frontend/src/components/NikkeCard.test.tsx`

**Interfaces:**
- Produces: 없음(prop 시그니처 불변).

- [ ] **Step 1: 실패 테스트를 쓴다**

```tsx
it('오버로드 줄을 눌러도 제외가 토글된다', async () => {
  const onToggleExclude = vi.fn()
  render(
    <NikkeCard
      draft={draftWithOverload()}
      index={0}
      name="Crown"
      element="Fire"
      portrait={null}
      onToggleExclude={onToggleExclude}
    />,
  )

  await userEvent.click(screen.getByText(/공격력/))

  expect(onToggleExclude).toHaveBeenCalledTimes(1)
})

it('이름을 눌러도 제외가 토글된다', async () => {
  const onToggleExclude = vi.fn()
  render(
    <NikkeCard draft={makeEmptyDraft()} index={0} name="Crown" element="Fire"
      portrait={null} onToggleExclude={onToggleExclude} />,
  )
  await userEvent.click(screen.getByRole('heading', { name: 'Crown' }))
  expect(onToggleExclude).toHaveBeenCalledTimes(1)
})

// 초상화는 버튼 안이고 버튼은 껍데기 안이다. 둘 다 핸들러를 들면 한 번 눌러
// 두 번 토글돼 아무 일도 안 한 것처럼 보인다.
it('초상화를 눌러도 정확히 한 번만 토글된다', async () => {
  const onToggleExclude = vi.fn()
  render(
    <NikkeCard draft={makeEmptyDraft()} index={0} name="Crown" element="Fire"
      portrait={null} onToggleExclude={onToggleExclude} />,
  )
  await userEvent.click(screen.getByRole('button', { name: 'Crown 사용' }))
  expect(onToggleExclude).toHaveBeenCalledTimes(1)
})

// 제외를 제안하지 않는 화면에서는 카드가 아무 데도 반응하면 안 된다.
it('onToggleExclude가 없으면 카드는 눌리지 않는다', async () => {
  render(<NikkeCard draft={makeEmptyDraft()} index={0} name="Crown" element="Fire" portrait={null} />)
  expect(screen.queryByRole('button')).not.toBeInTheDocument()
})
```

`draftWithOverload()`는 `overload_options`에 「공격력」이 들어간 draft를 만드는 헬퍼다. 기존 파일의 `makeEmptyDraft` 픽스처 옆에 만들고, 실제 `NikkeDraft`/`overload_options` 모양은 `types/nikkeDraft.ts`를 열어 맞춘다.

- [ ] **Step 2: 실패를 확인한다**

```bash
cd frontend && npx vitest run src/components/NikkeCard.test.tsx
```

기대: 오버로드·이름 테스트가 FAIL(핸들러 안 불림), 초상화 테스트는 PASS.

- [ ] **Step 3: 핸들러를 껍데기로 올린다**

`NikkeCard.tsx`의 `<section>`과 버튼을 바꾼다:

```tsx
  return (
    <section
      className={`card roster-card${excluded ? ' roster-card--excluded' : ''}`}
      data-element={element}
      aria-label={`${title} 투자 정보`}
      // 표적은 카드 테두리 안 전체다. 핸들러가 여기 하나뿐이라 초상화를 눌러도
      // 버블링으로 같은 핸들러에 한 번 닿는다 - 버튼에도 두면 두 번 불린다.
      onClick={onToggleExclude}
    >
      <div className="roster-card__figure">
        {onToggleExclude ? (
          <button
            type="button"
            className="roster-card__use"
            aria-pressed={!excluded}
            aria-label={`${title} 사용`}
          >
            {portrait ? (
              <img className="roster-card__portrait" src={portrait} alt="" />
            ) : (
              <span className="roster-card__portrait roster-card__portrait--missing" />
            )}
          </button>
        ) : portrait ? (
          <img className="roster-card__portrait" src={portrait} alt="" />
        ) : (
          <span className="roster-card__portrait roster-card__portrait--missing" />
        )}
        {/* 이하 grade/FavoriteItem 기존 그대로 */}
```

버튼에서 `onClick`을 **지운다**. `onToggleExclude`가 `undefined`면 `onClick`도 `undefined`라 카드는 안 눌린다.

- [ ] **Step 4: 커서를 손 모양으로**

`App.css`에 더한다:

```css
.roster-card:has(.roster-card__use) {
  cursor: pointer;
}
```

- [ ] **Step 5: 통과를 확인한다**

```bash
cd frontend && npx vitest run src/components/NikkeCard.test.tsx src/components/RosterGrid.test.tsx
npx tsc -b --noEmit
```

- [ ] **Step 6: 커밋**

```bash
git add frontend/src/components/NikkeCard.tsx frontend/src/components/NikkeCard.test.tsx frontend/src/App.css
git commit -m "니케 풀 카드는 테두리 안 어디를 눌러도 제외가 토글된다"
```

---

### Task 8: 팔레트 칩 전체를 표적으로, 제외는 배치되지 않게

설계 §1 + §3. 두 변경이 **같은 핸들러 안**에 있어서 한 태스크다.

**Files:**
- Modify: `frontend/src/components/UnitPalette.tsx:144-243`
- Test: `frontend/src/components/UnitPalette.test.tsx`

**Interfaces:**
- Produces: 없음(prop 시그니처 불변).

- [ ] **Step 1: 실패 테스트를 쓴다**

```tsx
it('스킬레벨 칸을 눌러도 배치된다', async () => {
  const onSeat = vi.fn()
  render(<UnitPalette {...base} onSeat={onSeat} usedSlugs={[]} />)

  const chip = screen.getByRole('button', { name: /crown 배치/i }).closest('.palette__item')!
  await userEvent.click(chip.querySelector('.palette__stat--core')!)

  expect(onSeat).toHaveBeenCalledWith('crown')
})

it('초상화를 눌러도 정확히 한 번만 배치된다', async () => {
  const onSeat = vi.fn()
  render(<UnitPalette {...base} onSeat={onSeat} usedSlugs={[]} />)
  await userEvent.click(screen.getByRole('button', { name: /crown 배치/i }))
  expect(onSeat).toHaveBeenCalledTimes(1)
})

// 니케 풀에서 「안 쓴다」고 정한 유닛이 배치 화면에서 들어오면 그 결정이 무효다.
it('제외된 유닛은 칩 어디를 눌러도 배치되지 않는다', async () => {
  const onSeat = vi.fn()
  render(<UnitPalette {...base} onSeat={onSeat} usedSlugs={[]} excludedSlugs={['crown']} />)

  const chip = screen.getByRole('button', { name: /crown/i }).closest('.palette__item')!
  await userEvent.click(chip.querySelector('.palette__stat--core')!)
  await userEvent.click(chip.querySelector('.palette__name')!)

  expect(onSeat).not.toHaveBeenCalled()
})

it('이미 앉은 유닛도 칩 어디를 눌러도 다시 배치되지 않는다', async () => {
  const onSeat = vi.fn()
  render(<UnitPalette {...base} onSeat={onSeat} usedSlugs={['crown']} />)

  const chip = screen.getByRole('button', { name: /crown/i }).closest('.palette__item')!
  await userEvent.click(chip.querySelector('.palette__stat--core')!)

  expect(onSeat).not.toHaveBeenCalled()
})

// 니케 풀 탭에는 onSeat이 없다. 거기서 제외된 칩까지 막으면 되돌릴 길이 없어진다.
it('니케 풀에서는 제외된 칩도 계속 눌린다', async () => {
  const onToggleExclude = vi.fn()
  render(<UnitPalette {...base} onToggleExclude={onToggleExclude} excludedSlugs={['crown']} />)

  const chip = screen.getByRole('button', { name: /crown/i }).closest('.palette__item')!
  await userEvent.click(chip.querySelector('.palette__stat--core')!)

  expect(onToggleExclude).toHaveBeenCalledWith('crown')
})
```

- [ ] **Step 2: 실패를 확인한다**

```bash
cd frontend && npx vitest run src/components/UnitPalette.test.tsx
```

기대: 「스킬레벨 칸」·「제외된 유닛」·「니케 풀에서는」이 FAIL.

- [ ] **Step 3: 핸들러를 칩으로 올린다**

`UnitPalette.tsx`의 `units.map` 안, `const classes = …` 아래에 더한다:

```tsx
                // 표적은 칩 테두리 안 전체다. 껍데기 핸들러는 버튼의 disabled를
                // 우회하므로 같은 조건을 여기서 다시 본다 - 안 그러면 제외된
                // 칩의 스킬레벨 칸을 눌러 배치할 수 있다.
                const handleChipClick = onSeat
                  ? () => {
                      if (isUsed || isExcluded) return
                      onSeat(unit.slug)
                    }
                  : onToggleExclude
                    ? () => onToggleExclude(unit.slug)
                    : undefined
```

`<li>`에 붙인다:

```tsx
                  <li
                    key={unit.slug}
                    className={classes.join(' ')}
                    data-element={unit.element}
                    onClick={handleChipClick}
                  >
```

버튼의 `onClick`을 **지운다**(`onClick={ onSeat ? … : … }` 삼항 전체). `disabled`는 제외까지 포함하도록 넓힌다:

```tsx
                      disabled={onSeat !== undefined && (isUsed || isExcluded)}
```

`draggable`은 그대로 둔다 — 드래그는 click이 아니다.

- [ ] **Step 4: 커서**

`App.css`:

```css
.palette__item {
  cursor: pointer;
}
.palette__item--excluded,
.palette__item--seated {
  cursor: default;
}
```

`.palette__item--excluded`는 니케 풀에서도 붙는데 거기서는 눌려야 하므로, 니케 풀 팔레트에는 `--excluded`만 붙고 `onSeat`이 없다. 커서가 `default`로 보이는 것은 감수한다 — 잘못 눌리는 것보다 낫다. 정확히 하려면 `onSeat` 유무를 클래스로 내보내야 하는데, 그 값어치가 없다.

- [ ] **Step 5: 통과를 확인한다**

```bash
cd frontend && npx vitest run src/components/UnitPalette.test.tsx src/components/RecommendPanel.test.tsx src/components/UnionRaidPanel.test.tsx
npx tsc -b --noEmit
```

- [ ] **Step 6: 커밋**

```bash
git add frontend/src/components/UnitPalette.tsx frontend/src/components/UnitPalette.test.tsx frontend/src/App.css
git commit -m "팔레트 칩은 테두리 안 전체가 표적 - 제외한 유닛은 어디를 눌러도 안 앉는다"
```

---

### Task 9: 좌석을 집는다 — 집기·재클릭 제거·Esc

설계 §2의 첫 조각. 이동은 Task 10에서 붙인다.

**Files:**
- Modify: `frontend/src/components/DraftEditor.tsx:196-, 344-374`
- Test: `frontend/src/components/DraftEditor.test.tsx`

**Interfaces:**
- Produces: `DraftEditor` 내부 상태 `heldSeat: { deckIndex: number; seatIndex: number } | null`. 외부 prop 없음.

- [ ] **Step 1: 실패 테스트를 쓴다**

```tsx
describe('집기와 놓기', () => {
  const seated: Draft = { decks: [[{ slug: 'crown', locked: false }], []] }

  it('좌석을 한 번 누르면 들리고, 아직 빠지지 않는다', async () => {
    const onChange = vi.fn()
    const { container } = editor(2, seated, onChange)

    await userEvent.click(screen.getByRole('button', { name: /덱 1에서 Crown/ }))

    expect(onChange).not.toHaveBeenCalled()
    expect(container.querySelector('.draft-editor__slot--held')).not.toBeNull()
  })

  it('같은 좌석을 다시 누르면 제거한다', async () => {
    const onChange = vi.fn()
    editor(2, seated, onChange)

    const seat = () => screen.getByRole('button', { name: /덱 1에서 Crown/ })
    await userEvent.click(seat())
    await userEvent.click(seat())

    expect(onChange).toHaveBeenCalledWith({ decks: [[], []] })
  })

  it('Esc는 집기를 취소하고 좌석을 그대로 둔다', async () => {
    const onChange = vi.fn()
    const { container } = editor(2, seated, onChange)

    await userEvent.click(screen.getByRole('button', { name: /덱 1에서 Crown/ }))
    await userEvent.keyboard('{Escape}')

    expect(onChange).not.toHaveBeenCalled()
    expect(container.querySelector('.draft-editor__slot--held')).toBeNull()
  })

  it('고정된 좌석은 들리지 않는다', async () => {
    const onChange = vi.fn()
    const { container } = render(
      <DraftEditor
        numDecks={2} value={seated} onChange={onChange}
        portraitFor={() => null} nameFor={nameFromSlug}
        burstTiersFor={(slug) => TIERS[slug] ?? []}
        fixedSlugs={['crown']}
      />,
    )
    const grip = container.querySelector('.draft-editor__slot-grip')!
    await userEvent.click(grip)

    expect(onChange).not.toHaveBeenCalled()
    expect(container.querySelector('.draft-editor__slot--held')).toBeNull()
  })
})
```

- [ ] **Step 2: 실패를 확인한다**

```bash
cd frontend && npx vitest run src/components/DraftEditor.test.tsx -t '집기와 놓기'
```

기대: 첫 테스트가 FAIL — 지금은 첫 클릭이 곧바로 제거를 부른다.

- [ ] **Step 3: 상태와 Esc를 더한다**

`DraftEditor` 본문의 `const [swapTarget, …]` 아래에:

```tsx
  // 든 좌석. 「누르면 제거」와 「누르면 이동」을 한 제스처로 잇는 상태다 -
  // 드래그가 앱에서 죽어 있어 이동은 클릭 두 번으로만 만들 수 있다.
  const [heldSeat, setHeldSeat] = useState<{ deckIndex: number; seatIndex: number } | null>(null)

  // 집었다가 마음이 바뀌었을 때의 출구. 같은 좌석을 다시 누르는 것은 제거라
  // 취소로 쓸 수 없다.
  useEffect(() => {
    if (!heldSeat) return
    const cancel = (event: KeyboardEvent) => {
      if (event.key === 'Escape') setHeldSeat(null)
    }
    window.addEventListener('keydown', cancel)
    return () => window.removeEventListener('keydown', cancel)
  }, [heldSeat])
```

`import { useEffect, useState } from 'react'`로 고친다.

- [ ] **Step 4: 좌석 클릭을 집기로 바꾼다**

좌석의 `<button className="draft-editor__slot-grip">`에서 `onClick`을 바꾼다:

```tsx
                          aria-label={`덱 ${deckIndex + 1}의 ${name}`}
                          onClick={() => {
                            const held =
                              heldSeat?.deckIndex === deckIndex &&
                              heldSeat.seatIndex === seatIndex
                            if (held) {
                              onChange(removeUnit(value, deckIndex, seatIndex))
                              setHeldSeat(null)
                              return
                            }
                            setHeldSeat({ deckIndex, seatIndex })
                          }}
```

**주의:** `aria-label`을 `덱 N에서 X 제거`에서 `덱 N의 X`로 바꾸면 기존 테스트 `DraftEditor.test.tsx:235`가 깨진다. 그 테스트와 위 새 테스트의 정규식을 **둘 다** `/덱 1의 Crown/`로 맞춘다. 이름이 동작을 말해야 하는데 이제 한 번 눌러서는 제거되지 않기 때문이다.

`<li>`의 className에 들린 표시를 더한다:

```tsx
                        heldSeat?.deckIndex === deckIndex && heldSeat.seatIndex === seatIndex
                          ? 'draft-editor__slot--held'
                          : '',
```

기존 className 조립 방식(배열 + `filter(Boolean).join(' ')`)을 따른다. 좌석 `<li>`가 지금 문자열 템플릿을 쓰면 배열 방식으로 바꾼다.

- [ ] **Step 5: 고정 좌석은 안 들리는지 확인**

고정 좌석은 이미 `<div className="draft-editor__slot-grip">`라 `onClick`이 없다. 그대로 두면 테스트가 통과한다.

- [ ] **Step 6: 들린 표시 CSS**

`App.css`:

```css
.draft-editor__slot--held {
  outline: 2px solid var(--accent);
  outline-offset: 2px;
}
```

`--accent` 토큰 이름은 `App.css`에서 실제로 쓰는 것으로 맞춘다.

- [ ] **Step 7: 통과를 확인한다**

```bash
cd frontend && npx vitest run src/components/DraftEditor.test.tsx
npx tsc -b --noEmit
```

- [ ] **Step 8: 커밋**

```bash
git add frontend/src/components/DraftEditor.tsx frontend/src/components/DraftEditor.test.tsx frontend/src/App.css
git commit -m "좌석을 집는다 - 한 번은 들기, 같은 자리 재클릭은 제거, Esc는 취소"
```

---

### Task 10: 들고 놓는다 — 빈자리 이동과 차 있는 자리 교환

설계 §2의 둘째 조각. 순수 함수 `moveUnit`·`swapUnits`가 이미 있으니 배선만 한다.

**Files:**
- Modify: `frontend/src/components/DraftEditor.tsx` (좌석 onClick, 빈자리 렌더)
- Test: `frontend/src/components/DraftEditor.test.tsx`

**Interfaces:**
- Consumes: `moveUnit(draft, deckIndex, slug)`, `swapUnits(draft, slug, otherSlug)`, `heldSeat` (Task 9).

- [ ] **Step 1: 실패 테스트를 쓴다**

```tsx
  it('들고 다른 덱의 빈자리를 누르면 옮긴다', async () => {
    const onChange = vi.fn()
    editor(2, seated, onChange)

    await userEvent.click(screen.getByRole('button', { name: /덱 1의 Crown/ }))
    await userEvent.click(screen.getByRole('button', { name: '덱 2에 놓기' }))

    expect(onChange).toHaveBeenCalledWith({
      decks: [[], [{ slug: 'crown', locked: false }]],
    })
  })

  it('들고 차 있는 자리를 누르면 둘을 교환한다', async () => {
    const both: Draft = {
      decks: [[{ slug: 'crown', locked: false }], [{ slug: 'liter', locked: false }]],
    }
    const onChange = vi.fn()
    editor(2, both, onChange)

    await userEvent.click(screen.getByRole('button', { name: /덱 1의 Crown/ }))
    await userEvent.click(screen.getByRole('button', { name: /덱 2의 Liter/ }))

    expect(onChange).toHaveBeenCalledWith({
      decks: [[{ slug: 'liter', locked: false }], [{ slug: 'crown', locked: false }]],
    })
  })

  it('아무것도 안 들었으면 빈자리는 버튼이 아니다', () => {
    editor(2, seated)
    expect(screen.queryByRole('button', { name: /놓기/ })).not.toBeInTheDocument()
  })

  it('들고 고정된 좌석을 누르면 아무 일도 없고 계속 들고 있다', async () => {
    const both: Draft = {
      decks: [[{ slug: 'crown', locked: false }], [{ slug: 'liter', locked: false }]],
    }
    const onChange = vi.fn()
    const { container } = render(
      <DraftEditor
        numDecks={2} value={both} onChange={onChange}
        portraitFor={() => null} nameFor={nameFromSlug}
        burstTiersFor={(slug) => TIERS[slug] ?? []}
        fixedSlugs={['liter']}
      />,
    )

    await userEvent.click(screen.getByRole('button', { name: /덱 1의 Crown/ }))
    await userEvent.click(container.querySelectorAll('.draft-editor__slot-grip')[1])

    expect(onChange).not.toHaveBeenCalled()
    expect(container.querySelector('.draft-editor__slot--held')).not.toBeNull()
  })
```

- [ ] **Step 2: 실패를 확인한다**

```bash
cd frontend && npx vitest run src/components/DraftEditor.test.tsx -t '놓'
```

기대: FAIL — `덱 2에 놓기` 버튼이 없음.

- [ ] **Step 3: 좌석 onClick에 놓기 분기를 더한다**

Task 9에서 쓴 좌석 `onClick`을 확장한다:

```tsx
                          onClick={() => {
                            const held =
                              heldSeat?.deckIndex === deckIndex &&
                              heldSeat.seatIndex === seatIndex
                            if (held) {
                              onChange(removeUnit(value, deckIndex, seatIndex))
                              setHeldSeat(null)
                              return
                            }
                            if (heldSeat) {
                              // 차 있는 자리에 놓는 것은 교환이다 - 드래그 드롭이
                              // 이미 그렇게 해서 두 경로가 같은 규칙이 된다.
                              const heldSlug =
                                value.decks[heldSeat.deckIndex]?.[heldSeat.seatIndex]?.slug
                              if (heldSlug) onChange(swapUnits(value, heldSlug, seat.slug))
                              setHeldSeat(null)
                              return
                            }
                            setHeldSeat({ deckIndex, seatIndex })
                          }}
```

고정 좌석은 `<div>`라 `onClick`이 없으므로 「들고 고정 좌석을 누르면 계속 들고 있다」가 저절로 성립한다.

- [ ] **Step 4: 빈자리를 놓기 버튼으로**

빈자리 렌더를 바꾼다:

```tsx
                {Array.from({ length: MAX_DRAFT_SEATS_PER_DECK - seats.length }, (_, i) => (
                  <li
                    key={`open-${i}`}
                    className="draft-editor__slot draft-editor__slot--open"
                    // 들고 있을 때만 놓을 수 있다. 누를 수 없는 것을 버튼으로
                    // 보이게 하지 않으려고 그때만 버튼이 된다.
                    aria-hidden={heldSeat ? undefined : 'true'}
                  >
                    {heldSeat && i === 0 ? (
                      <button
                        type="button"
                        className="draft-editor__slot-plus"
                        aria-label={`덱 ${deckIndex + 1}에 놓기`}
                        onClick={() => {
                          const heldSlug =
                            value.decks[heldSeat.deckIndex]?.[heldSeat.seatIndex]?.slug
                          if (heldSlug) onChange(moveUnit(value, deckIndex, heldSlug))
                          setHeldSeat(null)
                        }}
                      >
                        +
                      </button>
                    ) : (
                      <span className="draft-editor__slot-plus">+</span>
                    )}
                  </li>
                ))}
```

`i === 0`인 이유: 한 덱의 빈자리 다섯 개가 전부 같은 일을 하는 버튼이면 스크린리더가 같은 이름을 다섯 번 읽는다. 좌석 순서는 소속만 나타내므로 첫 빈자리 하나면 충분하다.

- [ ] **Step 5: 통과를 확인한다**

```bash
cd frontend && npx vitest run src/components/DraftEditor.test.tsx
npx tsc -b --noEmit
```

- [ ] **Step 6: 커밋**

```bash
git add frontend/src/components/DraftEditor.tsx frontend/src/components/DraftEditor.test.tsx
git commit -m "든 유닛을 빈자리에 놓으면 이동, 찬 자리에 놓으면 교환"
```

---

### Task 11: 든 상태에서 팔레트를 누르면 교체하고, 안내 문구를 고친다

설계 §2의 마지막 조각. 팔레트는 `DraftEditor` 밖이라 배선이 부모(`RecommendPanel`·`UnionRaidPanel`)를 지난다.

**Files:**
- Modify: `frontend/src/components/DraftEditor.tsx` (`onHeldSeatChange` prop 추가)
- Modify: `frontend/src/components/RecommendPanel.tsx`, `frontend/src/components/UnionRaidPanel.tsx` (팔레트 `onSeat` 분기)
- Modify: `frontend/src/lib/helpText.ts:126-136`
- Test: `frontend/src/components/UnionRaidPanel.test.tsx`

**Interfaces:**
- Produces: `DraftEditorProps.heldSlug?: string | null`, `DraftEditorProps.onHeldSlugChange?: (slug: string | null) => void` — 든 좌석의 **슬러그**를 부모가 볼 수 있게 한다. 부모는 좌석 좌표를 몰라도 되고 슬러그만 알면 `swapUnits`/`removeUnitBySlug`로 충분하다.

- [ ] **Step 1: 실패 테스트를 쓴다**

`UnionRaidPanel.test.tsx`에 추가한다. 기존 렌더 헬퍼와 로스터 픽스처를 재사용한다:

```tsx
it('덱에서 유닛을 들고 팔레트의 다른 유닛을 누르면 자리를 바꾼다', async () => {
  renderUnionPanel()          // 기존 헬퍼
  // 크라운을 덱 1에 앉힌다
  await userEvent.click(screen.getByRole('button', { name: /crown 배치/i }))
  // 그 좌석을 든다
  await userEvent.click(screen.getByRole('button', { name: /덱 1의 Crown/ }))
  // 팔레트에서 다른 유닛을 누른다
  await userEvent.click(screen.getByRole('button', { name: /liter 배치/i }))

  expect(screen.getByRole('button', { name: /덱 1의 Liter/ })).toBeInTheDocument()
  expect(screen.queryByRole('button', { name: /덱 1의 Crown/ })).not.toBeInTheDocument()
  // 크라운은 풀로 돌아가 다시 배치할 수 있다
  expect(screen.getByRole('button', { name: /crown 배치/i })).toBeEnabled()
})
```

- [ ] **Step 2: 실패를 확인한다**

```bash
cd frontend && npx vitest run src/components/UnionRaidPanel.test.tsx -t '팔레트의 다른 유닛'
```

기대: FAIL — 지금은 팔레트 클릭이 빈자리에 앉히기만 한다.

- [ ] **Step 3: 든 슬러그를 부모에게 알린다**

`DraftEditorProps`에:

```ts
  /** 지금 들려 있는 유닛. 팔레트가 이 컴포넌트 밖에 있어서, 팔레트를 눌렀을 때
   * 무엇과 바꿀지 부모가 알아야 한다. */
  heldSlug?: string | null
  onHeldSlugChange?: (slug: string | null) => void
```

`heldSeat`를 그대로 두되, 바뀔 때마다 슬러그를 위로 알린다:

```tsx
  const setHeld = (next: { deckIndex: number; seatIndex: number } | null) => {
    setHeldSeat(next)
    onHeldSlugChange?.(
      next ? (value.decks[next.deckIndex]?.[next.seatIndex]?.slug ?? null) : null,
    )
  }
```

Task 9·10에서 쓴 `setHeldSeat(...)` 호출을 **전부** `setHeld(...)`로 바꾼다(집기·제거 후·이동 후·교환 후·Esc).

- [ ] **Step 4: 부모가 팔레트 클릭을 분기한다**

`UnionRaidPanel`에 상태를 더한다:

```tsx
  const [heldSlug, setHeldSlug] = useState<string | null>(null)
```

`DraftEditor`에 `heldSlug={heldSlug}`와 `onHeldSlugChange={setHeldSlug}`를 넘긴다.

팔레트의 `onSeat`을 바꾼다:

```tsx
              onSeat={(slug) => {
                if (heldSlug) {
                  // 들고 있던 자리를 팔레트 유닛에게 내준다. 들고 있던 쪽은 풀로
                  // 돌아간다.
                  setDraftValue((current) =>
                    placeUnitAt(removeUnitBySlug(current, heldSlug), heldSlug, slug),
                  )
                  setHeldSlug(null)
                  return
                }
                setDraftValue((current) => placeUnit(current, seatDeck, slug))
              }}
```

`placeUnitAt`은 아직 없다. `DraftEditor.tsx`에 순수 함수로 만들고 export 한다:

```ts
/** `replacedSlug`가 있던 자리에 `slug`를 앉힌다. 자리를 그대로 물려받으므로
 * 덱이 꽉 차 있어도 된다 - 하나 나가고 하나 들어온다. */
export const replaceUnit = (draft: Draft, replacedSlug: string, slug: string): Draft => ({
  decks: draft.decks.map((seats) =>
    seats.map((seat) => (seat.slug === replacedSlug ? { slug, locked: seat.locked } : seat)),
  ),
})
```

이름이 `replaceUnit`이므로 호출부도 그렇게 쓴다:

```tsx
                  setDraftValue((current) => replaceUnit(current, heldSlug, slug))
```

`removeUnitBySlug`는 필요 없다 — `replaceUnit`이 자리를 물려주므로 한 번에 끝난다.

`RecommendPanel`에도 같은 배선을 넣는다. 그 파일의 draft 상태 이름과 `onSeat` 위치는 `placeUnit(`을 grep 해 찾는다.

- [ ] **Step 5: `replaceUnit` 단위 테스트**

`DraftEditor.test.tsx`에:

```ts
describe('replaceUnit', () => {
  it('자리를 물려주므로 꽉 찬 덱에서도 된다', () => {
    const full: Draft = {
      decks: [['a', 'b', 'c', 'd', 'e'].map((slug) => ({ slug, locked: false }))],
    }
    const next = replaceUnit(full, 'c', 'z')
    expect(next.decks[0].map((s) => s.slug)).toEqual(['a', 'b', 'z', 'd', 'e'])
  })

  it('잠금은 자리에 남는다', () => {
    const draft: Draft = { decks: [[{ slug: 'crown', locked: true }]] }
    expect(replaceUnit(draft, 'crown', 'liter').decks[0]).toEqual([
      { slug: 'liter', locked: true },
    ])
  })
})
```

- [ ] **Step 6: 안내 문구를 고친다**

`helpText.ts`의 `draft.seatHintCommon`이 이제 틀렸다(`덱에 앉은 니케를 누르면 편성에서 빠져요`). 바꾼다:

```ts
    seatHintCommon:
      '덱에 앉은 니케를 누르면 들려요. 다른 자리를 누르면 옮기거나 맞바꾸고, 같은 자리를 다시 누르면 편성에서 빠져요. Esc로 취소해요. 슬롯은 소속만 나타내며, 버스트 순서는 엔진이 정해요.',
```

- [ ] **Step 7: 통과를 확인한다**

```bash
cd frontend && npx vitest run
npx tsc -b --noEmit
```

- [ ] **Step 8: 커밋**

```bash
git add frontend/src/components/DraftEditor.tsx frontend/src/components/DraftEditor.test.tsx frontend/src/components/UnionRaidPanel.tsx frontend/src/components/UnionRaidPanel.test.tsx frontend/src/components/RecommendPanel.tsx frontend/src/lib/helpText.ts
git commit -m "든 유닛을 팔레트 유닛과 맞바꾼다 - 안내 문구를 바뀐 조작에 맞춘다"
```

---

### Task 12: 보스 설정을 접는다

설계 §8.

**Files:**
- Modify: `frontend/src/components/BossProfileField.tsx:203-406`
- Modify: `frontend/src/lib/helpText.ts`
- Test: `frontend/src/components/BossProfileField.test.tsx`

**Interfaces:**
- Consumes: `bossHeading` (Task 3), `BossProfileDraft.boss_name` (Task 4).

- [ ] **Step 1: 실패 테스트를 쓴다**

**접기 버튼의 접근 이름은 머리 텍스트 그 자체다**(`보스 설정` / `수냉` / `인디비리아`). `접기`·`펼치기`라는 낱말은 화면 어디에도 없으므로 그런 이름으로 찾지 않는다. 상태는 `aria-expanded`로 읽는다.

```tsx
describe('보스 설정 접기', () => {
  // 머리는 늘 bossHeading이 정한다 - 펼쳐져 있을 때도 같은 이름이다.
  const toggle = (name: string) => screen.getByRole('button', { name })

  it('처음에는 펼쳐져 있다', () => {
    renderField({ rotation: ROTATION })
    expect(toggle('보스 설정')).toHaveAttribute('aria-expanded', 'true')
    expect(screen.getByRole('radiogroup', { name: '보스 약점 속성' })).toBeInTheDocument()
  })

  it('접으면 본문이 사라진다', async () => {
    renderField({
      rotation: ROTATION,
      value: { ...makeDefaultBossProfileDraft(), element: 'Fire', boss_name: '인디비리아' },
    })

    await userEvent.click(toggle('인디비리아'))

    expect(toggle('인디비리아')).toHaveAttribute('aria-expanded', 'false')
    expect(screen.queryByRole('radiogroup', { name: '보스 약점 속성' })).not.toBeInTheDocument()
    expect(screen.queryByLabelText('전투 시간')).not.toBeInTheDocument()
  })

  it('보스를 골랐으면 그 이름으로 부른다', () => {
    renderField({
      value: { ...makeDefaultBossProfileDraft(), element: 'Fire', boss_name: '인디비리아' },
    })
    expect(toggle('인디비리아')).toBeInTheDocument()
  })

  it('이름이 없으면 약점 이름으로 부른다', () => {
    renderField({ value: { ...makeDefaultBossProfileDraft(), element: 'Fire' } })
    expect(toggle('수냉')).toBeInTheDocument()
  })

  it('이름도 속성도 없으면 보스 설정이라고 부른다', () => {
    renderField({})
    expect(toggle('보스 설정')).toBeInTheDocument()
  })

  // 접힌 안에 오류가 숨으면 계산이 이유 없이 안 되는 것처럼 보인다.
  it('오류가 있으면 접혀 있어도 펼친다', async () => {
    const view = render(
      <BossProfileField
        value={makeDefaultBossProfileDraft()}
        errors={{}}
        onChange={() => {}}
      />,
    )

    await userEvent.click(toggle('보스 설정'))
    expect(screen.queryByRole('radiogroup', { name: '보스 약점 속성' })).not.toBeInTheDocument()

    view.rerender(
      <BossProfileField
        value={makeDefaultBossProfileDraft()}
        errors={{ fight_duration: '0보다 커야 해요' }}
        onChange={() => {}}
      />,
    )

    expect(screen.getByText('0보다 커야 해요')).toBeInTheDocument()
    expect(screen.getByRole('radiogroup', { name: '보스 약점 속성' })).toBeInTheDocument()
    expect(toggle('보스 설정')).toHaveAttribute('aria-expanded', 'true')
  })
})
```

`renderField`/`ROTATION`은 기존 테스트 파일 헬퍼를 쓴다. 마지막 테스트만 `rerender`가 필요해서 `render`를 직접 부른다 — `BossProfileField`의 필수 prop이 이 셋뿐인지 `BossProfileFieldProps`를 열어 확인하고, 더 있으면 채운다. `screen.queryByLabelText('전투 시간')`의 라벨 문자열도 실제 필드 라벨로 맞춘다.

- [ ] **Step 2: 실패를 확인한다**

```bash
cd frontend && npx vitest run src/components/BossProfileField.test.tsx -t '접기'
```

기대: FAIL — 접기 버튼이 없음.

- [ ] **Step 3: 접힘 상태와 머리를 만든다**

`BossProfileField` 본문 위쪽에:

```tsx
  const [collapsed, setCollapsed] = useState(false)
  const bodyId = useId()

  // 오류가 접힌 안에 숨으면 화면에는 이유 없이 계산이 안 되는 것처럼 보인다.
  const hasErrors = Object.keys(errors ?? {}).length > 0
  const showBody = !collapsed || hasErrors

  const heading = bossHeading({
    bossName: value.boss_name,
    element: value.element,
    fallback: '보스 설정',
  })
```

import에 `useId`와 `bossHeading`을 더한다.

- [ ] **Step 4: legend를 바꾼다**

```tsx
      <legend className="group__legend">
        <span className="group__legend-row">
          {/* HelpTip을 감싸지 않는다 - 버튼 안의 버튼은 무효다. */}
          <button
            type="button"
            className="group__collapse"
            aria-expanded={showBody}
            aria-controls={bodyId}
            onClick={() => setCollapsed((current) => !current)}
          >
            {heading.iconSrc && (
              <img className="group__collapse-icon" src={heading.iconSrc} alt="" />
            )}
            {heading.text}
          </button>
          {rotation && (
            <HelpTip label="회차 보스">
              <HelpText>{HELP.boss.rotationPicker}</HelpText>
            </HelpTip>
          )}
        </span>
      </legend>

      {showBody && (
        <div id={bodyId}>
          {/* 기존 본문 전체: RaidRotationPicker부터 마지막 필드까지 */}
        </div>
      )}
```

본문을 `{showBody && (<div id={bodyId}> … </div>)}`로 감싼다. **CSS로 숨기지 않는다** — `css: false`라 숨긴 요소가 쿼리에 계속 잡혀 테스트가 아무것도 재지 못한다.

- [ ] **Step 5: 스타일**

`App.css`:

```css
.group__collapse {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  background: none;
  border: 0;
  padding: 0;
  font: inherit;
  color: inherit;
  cursor: pointer;
}
.group__collapse-icon {
  width: 16px;
  height: 16px;
}
.group__collapse[aria-expanded='false']::after { content: ' ▸'; }
.group__collapse[aria-expanded='true']::after { content: ' ▾'; }
```

- [ ] **Step 6: 통과를 확인한다**

```bash
cd frontend && npx vitest run
npx tsc -b --noEmit
```

- [ ] **Step 7: 커밋**

```bash
git add frontend/src/components/BossProfileField.tsx frontend/src/components/BossProfileField.test.tsx frontend/src/App.css
git commit -m "보스 설정을 접는다 - 접힌 머리는 보스 이름, 오류가 있으면 펼침을 강제한다"
```

---

### Task 13: 실제 앱에서 확인하고 마무리한다

브라우저 초록은 앱에 대해 아무 말도 하지 않는다 — 드래그가 죽어 있는 것이 그 증거다. 이번 변경은 전부 클릭이라 앱에서 실제로 되는지 눈으로 본다.

**Files:** 없음(검증만).

- [ ] **Step 1: 전체 스위트와 타입**

```bash
cd frontend && npx vitest run
npx tsc -b --noEmit
```

기대: 전부 PASS, 타입에러 0. 실패가 있으면 **여기서 멈추고** 원인을 고친 뒤 진행한다.

- [ ] **Step 2: 백엔드 스위트도 돌린다**

wire 타입을 안 건드렸다는 것을 확인하는 값싼 방법이다.

```bash
cd backend && python -m pytest -q
```

- [ ] **Step 3: 앱을 빌드해 자체 점검**

```bash
C:\Python314\python.exe scripts/build_app.py
dist/RapiLab/RapiLab.exe --selftest
```

- [ ] **Step 4: 앱을 띄워 아홉 가지를 손으로 확인한다**

1. 니케 풀에서 **오버로드 줄**을 눌러 제외가 토글되는가
2. 솔로 팔레트에서 **스킬레벨 칸**을 눌러 배치되는가
3. 니케 풀에서 제외한 유닛이 솔로·유니온 팔레트에서 **안 눌리는가**
4. 좌석을 눌러 들리고, 다른 덱 빈자리를 눌러 옮겨지는가
5. 든 채로 차 있는 자리를 눌러 교환되는가
6. 든 채로 팔레트 유닛을 눌러 교체되는가
7. 같은 자리 재클릭으로 제거, `Esc`로 취소되는가
8. 유니온 덱이 **보스 이름 + 아이콘**으로 불리고, 저장 이름이 **약점 나열**인가
9. 보스 설정이 접히고, 빈 칸을 두고 계산을 누르면 **저절로 펼쳐지는가**

- [ ] **Step 5: 트렁크를 다시 흡수한다**

이 저장소는 병렬 세션이 트렁크를 계속 민다. 착륙 직전에 한 번 더 당긴다.

```bash
git merge wip/scaffolding --no-edit
cd frontend && npx vitest run && npx tsc -b --noEmit
```

흡수 전 초록은 흡수 후에 대해 아무 말도 하지 않는다.

- [ ] **Step 6: 로드맵을 갱신하고 커밋**

`docs/roadmap.md`의 To-Do에서 이번에 끝난 항목을 체크하고, 레벨 400 항목은 **남긴다**.

```bash
git add docs/roadmap.md
git commit -m "로드맵: 덱 편성 조작·표기 9건 착륙"
```

---

## Self-Review

**1. 스펙 커버리지**

| 설계 | 태스크 |
|---|---|
| §1 카드 클릭 (니케 풀) | 7 |
| §1 카드 클릭 (팔레트) | 8 |
| §2 집기·제거·Esc | 9 |
| §2 이동·교환 | 10 |
| §2 팔레트 교체 + 문구 | 11 |
| §3 제외 시행 | 8 (§1 가드와 같은 핸들러) |
| §4 미란다 | 2 |
| §5 저장 이름 | 5 |
| §6 덱 라벨 | 3, 4, 6 |
| §7 상한 경고 | 1 |
| §8 접기 | 3, 4, 12 |
| §9 테스트 표 11행 | 각 태스크 Step 1 |
| §10 레벨 400 | 범위 밖 — 착수하지 않는다 |

빠진 것 없음.

**2. 플레이스홀더**

「기존 헬퍼를 재사용한다」가 여러 곳에 있는데, 전부 **읽어서 맞출 대상 파일과 줄**을 같이 적었다. 값을 확인하라고 지시한 두 곳(Task 3의 `weaknessFor` 실제 값, Task 1의 `upsertProfile` 인자 모양)은 「확인 전 값이다」라고 명시했다.

**3. 타입 일관성**

- `weaknessLabelOf` / `bossHeading` / `BossHeading` — Task 3에서 정의, 5·6·12에서 같은 이름으로 사용.
- `BossProfileDraft.boss_name` — Task 4에서 정의, 6·12에서 사용.
- `DraftEditorProps.deckLabels` — Task 6, `heldSlug`/`onHeldSlugChange` — Task 11.
- `replaceUnit` — Task 11에서 정의하고 같은 태스크에서 사용. Step 4 초안에 `placeUnitAt`이라 썼다가 `replaceUnit`으로 확정했다고 명시했다.
- 좌석 `aria-label`은 Task 9에서 `덱 N의 X`로 바뀌고, Task 10·11의 셀렉터가 전부 그 형태를 쓴다. 기존 테스트 `DraftEditor.test.tsx:235`를 같이 고치라고 Task 9 Step 4에 적었다.
