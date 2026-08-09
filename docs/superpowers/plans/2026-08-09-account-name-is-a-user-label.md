# 계정 이름을 유저의 라벨로 만들기 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 계정 이름을 유저가 소유하는 라벨로 만들고, blablalink 닉네임 조회를 「되면 좋고 안 되면 그만」인 1회 시도로 낮춘다.

**Architecture:** 저장된 `Profile.nickname`은 **한 번 정해지면 동기화가 덮어쓰지 않는 라벨**이 된다. 동기화는 비어 있을 때만 씨앗을 심고, 유저는 계정 드롭다운 옆에서 언제든 이름을 바꾼다. 북마크릿은 닉네임 조회의 재시도·간격을 걷어내고, **자기가 도는 페이지가 이미 그 조회를 했으면 아예 묻지 않는다**.

**Tech Stack:** React 19 + TypeScript + Vite, Vitest + @testing-library/react. 프론트엔드만 바뀐다 — 백엔드·엔진은 손대지 않는다.

## Global Constraints

- 화면 문구는 전부 한국어 존댓말 (`~해요` 체). 기존 `helpText.ts`·컴포넌트 문구와 같은 톤.
- 주석은 WHAT/WHY만. 「예전엔 이랬다」를 코드 주석에 쓰지 않는다 (CLAUDE.md).
- 이 작업의 근거가 되는 실측은 `2026-08-09` 세션의 `scripts/measure_blablalink_cooldown.js` 결과다. 주석에서 근거를 인용할 때 이 날짜를 쓴다.
- 테스트는 `frontend/`에서 `npm test -- --run`. 타입은 `npx tsc -b --noEmit`을 따로 돌린다 (vitest는 타입을 안 본다).
- 커밋 메시지는 한국어 한 줄 요약 + 빈 줄 + 본문. 기존 로그 형식과 같게.

## 실측이 정한 것 (이 계획의 전제)

이 값들은 추측이 아니라 2026-08-09 콘솔 실측이다. 계획의 판단이 전부 여기 기댄다.

| 사실 | 어떻게 알았나 |
|---|---|
| ShiftyPad 화면이 뜨며 프록시를 1.3초에 13호출 하고, 그중 `GetUserProfileBasicInfo`가 있다 | Resource Timing |
| 그 직후엔 **호출 하나짜리** 이름 조회도 `1300015`로 거절된다 | 최소 재현 |
| 같은 순간 `GetUserCharacters`는 `code 0`으로 통과한다 | 로스터가 멀쩡히 들어오던 이유 |
| 거절된 뒤 15/30/60/120초 정적을 두고 다시 물어도 4분 내내 거절된다 | 계단 |
| 조용한 상태에서는 0.4초 간격 연속 두 번도 통과한다 | 개별 쿨다운 없음 |
| 이름은 `basic_info` 밖 어디에도 없다 | outpost·characters·details 2단계 스캔 |
| `GetSavedRoleInfo.role_info.role_name`은 **로그인 세션**의 이름이다 | 계정을 바꿔도 같은 값 |

따라 나오는 결론: **재시도는 해롭고**(거절도 창을 민다), **호출 수 축소·간격·순서는 원인이 아니었으며**, 최초 동기화 시점의 이름 조회는 신뢰할 수 없다.

---

### Task 1: 저장된 계정 이름은 동기화가 덮어쓰지 않는다

**Files:**
- Modify: `frontend/src/types/profile.ts:120-165` (`upsertProfile` 문서와 닉네임 규칙), 파일 끝에 `renameProfile` 추가
- Test: `frontend/src/types/profile.test.ts`

**Interfaces:**
- Consumes: 없음 (첫 태스크)
- Produces: `renameProfile(state: ProfilesState, key: string, name: string): ProfilesState` — 이름을 trim해서 넣는다. 빈 문자열이거나 없는 key면 `state`를 그대로 돌려준다(참조 동일).

- [ ] **Step 1: 기존 기대를 뒤집는 테스트 둘을 고친다**

`profile.test.ts`에 이미 있는 두 테스트는 **「들어온 닉네임이 저장된 것을 이긴다」**를 고정하고 있다. 이 태스크가 그 규칙을 뒤집으므로 같이 뒤집는다. 지우지 말고 이름과 본문을 바꿔서, 규칙이 바뀌었다는 사실이 테스트에 남게 한다.

`'닉네임이 실제로 바뀌면 갱신한다'`(현재 44행 근처)를 이렇게 교체:

```ts
  // 이름은 유저의 라벨이다. 유저가 「JP 본계」라고 붙여둔 것을 다음 동기화가
  // 게임 닉네임으로 되돌리면, 계정을 구분하려고 붙인 이름이 유저 몰래 사라진다.
  it('저장된 이름이 있으면 동기화가 가져온 닉네임으로 덮어쓰지 않는다', () => {
    let s = upsertProfile(emptyProfilesState(), { openId: 'A', area: 81, nickname: '본계', roster: [draft('liter')] })
    s = upsertProfile(s, { openId: 'A', area: 81, nickname: '개명', roster: [draft('liter')] })
    expect(s.profiles['A:81'].nickname).toBe('본계')
  })

  // 씨앗은 심는다 - 이름을 못 읽은 채 만들어진 프로필이 나중에 운 좋은 동기화
  // 하나로 이름을 얻을 수 있어야 한다. 그것이 이 조회를 남겨두는 유일한 이유다.
  it('저장된 이름이 비어 있으면 동기화가 가져온 닉네임을 채운다', () => {
    let s = upsertProfile(emptyProfilesState(), { openId: 'A', area: 81, nickname: '', roster: [draft('liter')] })
    s = upsertProfile(s, { openId: 'A', area: 81, nickname: '뒤늦게읽음', roster: [draft('liter')] })
    expect(s.profiles['A:81'].nickname).toBe('뒤늦게읽음')
  })
```

`'기존 open_id 재sync: 로스터가 byte-동일이면 results를 유지한다'`(현재 58행 근처)의 마지막 줄
`expect(s.profiles['A:81'].nickname).toBe('본계2')` 를 다음으로 바꾼다:

```ts
    expect(s.profiles['A:81'].nickname).toBe('본계') // 이름은 라벨이라 그대로다
```

- [ ] **Step 2: `renameProfile`의 실패 테스트를 쓴다**

`profile.test.ts`의 `describe('switch/delete/active', ...)` 앞에 추가:

```ts
describe('renameProfile', () => {
  it('이름을 바꾼다', () => {
    let s = upsertProfile(emptyProfilesState(), { openId: 'A', area: 81, nickname: '', roster: [] })
    s = renameProfile(s, 'A:81', 'JP 본계')
    expect(s.profiles['A:81'].nickname).toBe('JP 본계')
  })

  it('앞뒤 공백을 떼고 넣는다', () => {
    let s = upsertProfile(emptyProfilesState(), { openId: 'A', area: 81, nickname: '', roster: [] })
    s = renameProfile(s, 'A:81', '  JP 본계  ')
    expect(s.profiles['A:81'].nickname).toBe('JP 본계')
  })

  // 빈 이름을 받아 넣으면 드롭다운이 UID로 되돌아간다 - 유저가 의도한 조작이
  // 아니라 실수(전부 지우고 엔터)일 때 그렇게 되는 편이 흔하다.
  it('빈 이름은 무시하고 상태를 그대로 돌려준다', () => {
    const s = upsertProfile(emptyProfilesState(), { openId: 'A', area: 81, nickname: '본계', roster: [] })
    expect(renameProfile(s, 'A:81', '   ')).toBe(s)
  })

  it('없는 key는 상태를 그대로 돌려준다', () => {
    const s = upsertProfile(emptyProfilesState(), { openId: 'A', area: 81, nickname: '본계', roster: [] })
    expect(renameProfile(s, 'Z:99', '아무개')).toBe(s)
  })
})
```

`profile.test.ts` 맨 위 import에 `renameProfile`을 더한다.

- [ ] **Step 3: 테스트가 빨간지 확인한다**

Run: `cd frontend && npx vitest run src/types/profile.test.ts`
Expected: `renameProfile` 4개는 `renameProfile is not a function`(또는 import 실패)로 FAIL, 덮어쓰기 관련 2개는 `expected '개명' to be '본계'` 로 FAIL.

- [ ] **Step 4: 구현한다**

`profile.ts`의 `upsertProfile` 안, `existing`이 있을 때의 분기에서 한 줄:

```ts
        nickname: existing.nickname || args.nickname,
```

그리고 그 위 docstring에서 닉네임을 설명하는 문단을 통째로 교체:

```
 * The stored name is a LABEL the user owns, not a mirror of the in-game
 * nickname. A sync seeds it only while it is empty; once there is a name,
 * nothing but an explicit rename replaces it. blablalink rejects the nickname
 * call (`GetUserProfileBasicInfo`, code 1300015) whenever the ShiftyPad page
 * has just fetched it - which is exactly when a first sync happens - so the
 * name that does arrive is a lucky bonus, and the one the user typed is the
 * one worth keeping (2026-08-09 measurement).
```

파일 끝의 다른 순수 함수들 옆에 추가:

```ts
/** 계정 이름을 바꾼다. 이름은 유저의 라벨이므로 이것만이 이름을 바꾸는 길이다.
 * 빈 이름과 없는 key는 상태를 그대로 돌려준다 - 실수로 라벨을 지우는 쪽이
 * 못 바꾸는 쪽보다 나쁘다. */
export const renameProfile = (
  state: ProfilesState,
  key: string,
  name: string,
): ProfilesState => {
  const trimmed = name.trim()
  const existing = state.profiles[key]
  if (trimmed === '' || existing === undefined) return state
  return {
    ...state,
    profiles: { ...state.profiles, [key]: { ...existing, nickname: trimmed } },
  }
}
```

- [ ] **Step 5: 초록인지 확인한다**

Run: `cd frontend && npx vitest run src/types/profile.test.ts`
Expected: PASS (모두)

- [ ] **Step 6: 커밋**

```bash
git add frontend/src/types/profile.ts frontend/src/types/profile.test.ts
git commit -m "저장된 계정 이름은 유저의 라벨이다 - 동기화가 덮어쓰지 않는다"
```

---

### Task 2: 계정 드롭다운에서 이름을 바꾼다

**Files:**
- Modify: `frontend/src/hooks/useProfiles.ts` (`Profiles` 인터페이스 + `renameProfile` 배선)
- Modify: `frontend/src/components/ProfileSwitcher.tsx` (인라인 이름 바꾸기)
- Modify: `frontend/src/App.tsx:50-61, 157-162` (구조분해 + prop 전달)
- Test: `frontend/src/components/ProfileSwitcher.test.tsx`

**Interfaces:**
- Consumes: Task 1의 `renameProfile(state, key, name)`
- Produces:
  - `Profiles.renameProfile: (args: { key: string; name: string }) => void`
  - `ProfileSwitcherProps.onRename: (key: string, name: string) => void`

- [ ] **Step 1: 실패 테스트를 쓴다**

`ProfileSwitcher.test.tsx`의 `describe('ProfileSwitcher', ...)` 안에 추가. 기존 테스트들이 `onDelete={vi.fn()}`만 넘기고 있으므로, **모든 기존 `render(<ProfileSwitcher .../>)` 호출에 `onRename={vi.fn()}`을 더해야** 타입이 통과한다.

```ts
  it('이름 바꾸기를 누르면 현재 이름이 든 입력이 뜨고, 저장하면 그 이름으로 부른다', async () => {
    const onRename = vi.fn()
    const profile = makeProfile({ openId: 'a', nickname: '본계' })
    render(
      <ProfileSwitcher
        profiles={[profile]}
        activeKey={profileKey('a', 81)}
        onSwitch={vi.fn()}
        onDelete={vi.fn()}
        onRename={onRename}
      />,
    )
    await userEvent.click(screen.getByRole('button', { name: '계정 이름 바꾸기' }))
    const input = screen.getByRole('textbox', { name: '계정 이름' })
    expect((input as HTMLInputElement).value).toBe('본계')
    await userEvent.clear(input)
    await userEvent.type(input, 'JP 본계')
    await userEvent.click(screen.getByRole('button', { name: '저장' }))
    expect(onRename).toHaveBeenCalledWith('a:81', 'JP 본계')
  })

  // 이름을 아직 못 읽은 계정이 이 기능이 가장 필요한 계정이다. 그때 입력이
  // UID로 채워져 있으면 유저가 그것을 지우는 것부터 해야 한다.
  it('이름이 없는 계정은 빈 입력으로 시작한다', async () => {
    render(
      <ProfileSwitcher
        profiles={[makeProfile({ openId: 'a', nickname: '' })]}
        activeKey={profileKey('a', 81)}
        onSwitch={vi.fn()}
        onDelete={vi.fn()}
        onRename={vi.fn()}
      />,
    )
    await userEvent.click(screen.getByRole('button', { name: '계정 이름 바꾸기' }))
    expect((screen.getByRole('textbox', { name: '계정 이름' }) as HTMLInputElement).value).toBe('')
  })

  it('빈 이름으로는 저장하지 않는다', async () => {
    const onRename = vi.fn()
    render(
      <ProfileSwitcher
        profiles={[makeProfile({ openId: 'a', nickname: '본계' })]}
        activeKey={profileKey('a', 81)}
        onSwitch={vi.fn()}
        onDelete={vi.fn()}
        onRename={onRename}
      />,
    )
    await userEvent.click(screen.getByRole('button', { name: '계정 이름 바꾸기' }))
    await userEvent.clear(screen.getByRole('textbox', { name: '계정 이름' }))
    await userEvent.click(screen.getByRole('button', { name: '저장' }))
    expect(onRename).not.toHaveBeenCalled()
  })

  // 활성 계정이 없는 상태에서 이름 바꾸기 버튼이 눌리면 어느 계정을 바꿀지가
  // 없다. 삭제 버튼이 activeKey === null에서 아무것도 안 하는 것과 같은 이유다.
  it('활성 계정이 없으면 이름 바꾸기 버튼이 없다', () => {
    render(
      <ProfileSwitcher
        profiles={[makeProfile({ openId: 'a' })]}
        activeKey={null}
        onSwitch={vi.fn()}
        onDelete={vi.fn()}
        onRename={vi.fn()}
      />,
    )
    expect(screen.queryByRole('button', { name: '계정 이름 바꾸기' })).toBeNull()
  })
```

- [ ] **Step 2: 테스트가 빨간지 확인한다**

Run: `cd frontend && npx vitest run src/components/ProfileSwitcher.test.tsx`
Expected: 새 테스트 4개 FAIL — `Unable to find an accessible element with the role "button" and name "계정 이름 바꾸기"`.

- [ ] **Step 3: `ProfileSwitcher`에 인라인 이름 바꾸기를 넣는다**

`SavedRunList.tsx`가 쓰는 것과 같은 형태다 — 버튼으로 열고, 입력에 현재 값을 담고, trim해서 빈 것은 거절한다.

`ProfileSwitcher.tsx`를 다음으로 바꾼다 (import에 `useId`, `useState` 추가):

```tsx
import { useId, useState } from 'react'
import { profileKey, type Profile } from '../types/profile'
import { serverLabel } from '../types/server'

interface ProfileSwitcherProps {
  profiles: Profile[]
  activeKey: string | null
  onSwitch: (key: string) => void
  onDelete: (key: string) => void
  /** 계정 이름은 유저의 라벨이다 - 동기화가 못 읽어 오면 여기서 붙인다. */
  onRename: (key: string, name: string) => void
}
```

컴포넌트 본문에서 `if (profiles.length === 0) return null` 아래에:

```tsx
  const [renaming, setRenaming] = useState(false)
  const [renameValue, setRenameValue] = useState('')
  const renameFieldId = useId()
```

> 훅은 이른 반환보다 위에 있어야 한다. `useState`/`useId` 세 줄을 `if (profiles.length === 0) return null` **앞**으로 옮겨 둘 것 — 아래에 두면 프로필이 0개에서 1개로 바뀌는 순간 훅 개수가 달라져 React가 던진다.

`startRename`/`commitRename`:

```tsx
  const startRename = () => {
    setRenameValue(active?.nickname ?? '')
    setRenaming(true)
  }

  const commitRename = () => {
    const name = renameValue.trim()
    if (name === '' || activeKey === null) return
    onRename(activeKey, name)
    setRenaming(false)
  }
```

삭제 버튼 옆에 (activeKey가 있을 때만):

```tsx
      {activeKey !== null && (
        <button
          type="button"
          className="btn btn--icon"
          aria-label="계정 이름 바꾸기"
          onClick={startRename}
        >
          이름
        </button>
      )}
      {renaming && (
        <div className="profile-switcher__rename">
          <label className="field__label" htmlFor={renameFieldId}>
            계정 이름
          </label>
          <input
            id={renameFieldId}
            className="field__input"
            value={renameValue}
            onChange={(e) => setRenameValue(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter') commitRename()
              if (e.key === 'Escape') setRenaming(false)
            }}
          />
          <button type="button" className="btn btn--primary" onClick={commitRename}>
            저장
          </button>
          <button type="button" className="btn" onClick={() => setRenaming(false)}>
            취소
          </button>
        </div>
      )}
```

`labelFor`의 주석에서 「닉네임을 못 읽은 동기화는 open_id가 대신 선다」는 그대로 사실이므로 유지하고, 다음 한 문장을 더한다: `이름은 유저가 직접 붙일 수 있다 - 동기화가 못 읽어 오는 경우가 정상 경로다.`

- [ ] **Step 4: 초록인지 확인한다**

Run: `cd frontend && npx vitest run src/components/ProfileSwitcher.test.tsx`
Expected: PASS (모두)

- [ ] **Step 5: 훅과 App을 배선한다**

`useProfiles.ts`:
- import에 `renameProfile as pureRenameProfile` 추가
- `Profiles` 인터페이스에:

```ts
  /** 계정 이름 바꾸기. 이름은 유저의 라벨이라 이것만이 이름을 바꾼다. */
  renameProfile: (args: { key: string; name: string }) => void
```

- 콜백:

```ts
  const renameAccount = useCallback((args: { key: string; name: string }) => {
    setState((current) => pureRenameProfile(current, args.key, args.name))
  }, [])
```

- 반환 객체에 `renameProfile: renameAccount,` 추가

`App.tsx`:
- `useProfiles()` 구조분해에 `renameProfile` 추가
- `<ProfileSwitcher ... />`에 `onRename={(key, name) => renameProfile({ key, name })}` 추가

- [ ] **Step 6: 전체 테스트와 타입을 돌린다**

Run: `cd frontend && npm test -- --run && npx tsc -b --noEmit`
Expected: 전부 PASS, 타입 에러 0

- [ ] **Step 7: 커밋**

```bash
git add frontend/src/hooks/useProfiles.ts frontend/src/components/ProfileSwitcher.tsx frontend/src/components/ProfileSwitcher.test.tsx frontend/src/App.tsx
git commit -m "계정 이름을 드롭다운 옆에서 바꾼다 - 동기화가 못 읽어 오는 것이 정상 경로다"
```

---

### Task 3: 북마크릿에서 재시도와 간격을 걷어낸다

**Files:**
- Modify: `frontend/src/lib/bookmarklet.ts` (파일 머리 주석 전체 + `collectSource`)
- Test: `frontend/src/lib/bookmarklet.test.ts`

**Interfaces:**
- Consumes: 없음
- Produces: 생성되는 북마크릿 소스에서 `WAITS`/`GAP` 상수가 사라지고, `GetUserProfileBasicInfo`는 서버당 **최대 한 번** 불린다. `buildLocalSyncBookmarklet(openId, known)` 시그니처는 그대로.

**왜 이 태스크가 필요한가:** 재시도는 완화가 아니라 **악화**다. 거절된 요청도 제한 창을 밀기 때문에, 0/2/5초로 세 번 더 묻는 것은 스스로 빠져나오지 못하게 만든다(2026-08-09 계단 실측: 15/30/60/120초 정적을 둬도 4분 내내 거절). 간격(350ms)과 호출 수 축소는 무해하지만 **원인이 아니었던 것으로 밝혀졌고**, 죽은 가설을 코드로 남기면 다음 사람이 그것을 근거로 삼는다.

- [ ] **Step 1: 테스트 하네스에 `performance`를 주입한다**

`bookmarklet.test.ts`의 `runBookmarklet`을 고친다. 북마크릿이 「이 페이지가 이미 이름을 조회했는가」를 Resource Timing으로 보게 되므로, 테스트가 그 답을 정할 수 있어야 한다.

시그니처에 세 번째 인자를 더한다:

```ts
    const runBookmarklet = async (
      fetchImpl: FetchImpl,
      customSource = source,
      /** 이 페이지가 이미 부른 프록시 URL들. 기본은 아무것도 안 부른 페이지다. */
      pageCalls: string[] = [],
    ): Promise<{ ... }> => {
```

`new Function`과 호출을 고친다:

```ts
      const run = new Function(
        'location', 'fetch', 'alert', 'setTimeout', 'performance',
        `return ${customSource}`,
      )
      await run(
        { origin: BLABLALINK_ORIGIN },
        wrapped,
        (m: string) => alerts.push(m),
        (fn: () => void, ms: number) => { waits.push(ms); fn() },
        { getEntriesByType: () => pageCalls.map((name) => ({ name })) },
      )
```

`setTimeout` 주입 위의 주석은 재시도가 사라지면 거짓이 되므로 이렇게 바꾼다:

```ts
      // setTimeout도 주입한다 - 북마크릿이 대기를 하게 되면 그 길이는 blablalink가
      // 정하는 제품 판단이지 테스트가 정할 것이 아니다. 여기서는 즉시 깨운다.
```

- [ ] **Step 2: 재시도·간격을 고정하던 테스트를 뒤집는다**

`'이름 조회가 한 번 튕겨도 다시 시도해 받아낸다'`(185행 근처)와 `'세 번 다 튕기면 시도 횟수를 적어 보낸다'`(215행 근처)와 `'호출 사이에 간격을 둔다'`(242행 근처) **셋을 지우고**, 그 자리에 다음을 넣는다:

```ts
    // 거절된 요청도 blablalink의 제한 창을 민다(2026-08-09 실측: 15/30/60/120초
    // 정적을 두고 다시 물어도 4분 내내 거절됐다). 그래서 재시도는 완화가 아니라
    // 스스로 못 빠져나오게 만드는 악화다. 한 번 묻고 만다.
    it('이름 조회는 서버당 한 번만 부른다 - 튕겨도 다시 묻지 않는다', async () => {
      let asked = 0
      const { payload } = await runBookmarklet((url: string) => {
        if (url.endsWith('GetUserProfileBasicInfo')) asked++
        return Promise.resolve({
          json: () =>
            Promise.resolve(
              url.endsWith('GetUserProfileBasicInfo')
                ? { code: 1300015, msg: 'Requests are too frequent', data: null }
                : { code: 0, data: responseFor(url) },
            ),
        })
      })
      expect(asked).toBe(1)
      const servers = payload?.servers as { nickname: string; nickname_error: string }[] | undefined
      expect(servers?.[0]?.nickname).toBe('')
      expect(servers?.[0]?.nickname_error).toContain('1300015')
    })

    // 페이지가 방금 부른 것을 우리가 또 부르면 반드시 거절되고, 그 거절이 창을
    // 밀어 다음 동기화까지 망친다. 「이 페이지가 이미 물었는가」는 상수 없이
    // Resource Timing으로 알 수 있다 - 기록은 문서마다 새로 시작한다.
    it('이 페이지가 이미 이름을 조회했으면 묻지 않는다', async () => {
      let asked = 0
      const { payload } = await runBookmarklet(
        (url: string) => {
          if (url.endsWith('GetUserProfileBasicInfo')) asked++
          return Promise.resolve({ json: () => Promise.resolve({ code: 0, data: responseFor(url) }) })
        },
        source,
        ['https://api.blablalink.com/api/game/proxy/Game/GetUserProfileBasicInfo'],
      )
      expect(asked).toBe(0)
      const servers = payload?.servers as { nickname: string; nickname_error: string }[] | undefined
      expect(servers?.[0]?.nickname).toBe('')
      expect(servers?.[0]?.nickname_error).toContain('page')
      // 로스터는 그대로 들어온다 - 막힌 것은 이름 하나다.
      expect((servers?.[0] as unknown as { owned: unknown[] }).owned.length).toBeGreaterThan(0)
    })

    // 페이지가 다른 것만 불렀다면 이름 조회는 통과할 수 있다. 그때는 묻는다 -
    // 계정 하나에 한 번만 성공하면 되고, 그 뒤로는 namedAreas가 건너뛴다.
    it('페이지가 이름을 조회하지 않았으면 한 번 묻는다', async () => {
      let asked = 0
      const { payload } = await runBookmarklet(
        (url: string) => {
          if (url.endsWith('GetUserProfileBasicInfo')) asked++
          return Promise.resolve({ json: () => Promise.resolve({ code: 0, data: responseFor(url) }) })
        },
        source,
        ['https://api.blablalink.com/api/game/proxy/Game/HasFinishOnboardingMissionList'],
      )
      expect(asked).toBe(1)
      const servers = payload?.servers as { nickname: string }[] | undefined
      expect(servers?.[0]?.nickname).toBe(NICKNAME)
    })
```

- [ ] **Step 3: 테스트가 빨간지 확인한다**

Run: `cd frontend && npx vitest run src/lib/bookmarklet.test.ts`
Expected: `이름 조회는 서버당 한 번만 부른다`는 `expected 3 to be 1`로 FAIL, `이 페이지가 이미 이름을 조회했으면 묻지 않는다`는 `expected 1 to be 0`으로 FAIL.

- [ ] **Step 4: `collectSource`를 고친다**

`GAP`/`WAITS`/`lastCall`과 재시도 루프를 걷어내고, 페이지가 이미 물었으면 건너뛴다.

`collectSource` 머리의 세 줄을 이렇게 바꾼다:

```
const call=async(ep,body)=>{
 const r=await fetch('https://api.blablalink.com/api/game/proxy/Game/'+ep,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body),credentials:'include'});
 const j=await r.json();
 if(j.code!==0){const e=new Error(ep+':'+j.code+(j.msg?' '+j.msg:''));e.code=j.code;throw e}
 return j.data};
const NAME_EP='GetUserProfileBasicInfo';
const PAGE_ASKED=performance.getEntriesByType('resource').some(e=>e.name.indexOf(NAME_EP)>=0);
```

서버 루프 안의 이름 조회 블록(현재 `let basic=null,nickErr='',tries=0,nick='';`부터 `if(!nick)nickErr+=...`까지)을 이것으로 교체:

```
 let nickErr='',nick='';
 if(NAMED.indexOf(f.area)>=0){}
 else if(PAGE_ASKED){nickErr='page already asked - 이 화면 말고 다른 blablalink 화면에서 눌러주세요'}
 else{
  let basic=null;
  try{basic=await call(NAME_EP,{...base})}catch(e){nickErr=String(e&&e.message||e)}
  const bi=(basic&&basic.basic_info)||{};
  nick=bi.nickname||bi.role_name||'';
  if(!nick&&!nickErr)nickErr='shape:'+Object.keys(basic||{}).join('|');}
```

- [ ] **Step 5: 초록인지 확인한다**

Run: `cd frontend && npx vitest run src/lib/bookmarklet.test.ts`
Expected: PASS (모두). 실패하는 것이 남으면 그 테스트가 죽은 가설을 고정하고 있는지 먼저 읽을 것 — `outpost:` 키를 붙이던 진단은 이번에 사라진다.

- [ ] **Step 6: 파일 머리 주석을 다시 쓴다**

`bookmarklet.ts` 1~69행의 주석 덩어리는 지금 **죽은 가설의 서술**이다(마지막 자리라서 거절된다 / 간격이 답이다 / 재시도가 답이다 / 순서를 바꾸면 안 된다). 통째로 다음으로 교체한다. 이 아래 다섯 문단 밖의 기존 내용(CSP·1302125·서버별 실패 감싸기 규칙)은 여전히 사실이므로 **그대로 남긴다**.

```
// 유저의 blablalink 세션으로 API를 호출해 원시 payload를 우리 앱에 넘기는
// 북마크릿. blablalink 페이지 컨텍스트에서 도는 것이 전제다 - 거기서만
// credentials:'include' fetch가 CORS를 통과한다(2026-07-19 실측).
//
// 계정 닉네임은 GetUserProfileBasicInfo의 `data.basic_info.nickname`에 있다
// (2026-07-25 실측; `role_name`도 같은 값이다). 한 단계 얕게 `data.nickname`을
// 읽으면 항상 undefined다.
//
// **이 조회는 최선 노력이다.** blablalink는 code 1300015("Requests are too
// frequent")로 이것만 거절하는데, 거절을 부르는 것은 우리 묶음이 아니라
// **ShiftyPad 화면 자신**이다: 그 화면은 뜨면서 프록시를 1.3초에 열세 번 부르고
// 그중 하나가 이 조회다. 유저가 공유 URL을 복사한 직후 북마크를 누르는 최초
// 동기화는 정확히 그 몇 초 안이라 늘 거절된다. 호출 하나짜리로 줄여도 거절되고,
// 로스터 조회는 같은 순간에 멀쩡히 통과한다(2026-08-09 실측).
//
// 그래서 재시도하지 않는다. **거절된 요청도 제한 창을 민다** - 15/30/60/120초
// 정적을 두고 다시 물어도 4분 내내 거절됐다. 세 번 더 묻는 것은 완화가 아니라
// 스스로 못 빠져나오게 만드는 악화다. 같은 이유로, 이 페이지가 **이미** 그
// 조회를 했으면 아예 묻지 않는다 - Resource Timing 기록은 문서마다 새로
// 시작하므로 시간 상수 없이 「이 화면이 이미 물었다」를 알 수 있다.
//
// 이름을 못 받아도 그것은 실패가 아니다. 앱에서 계정 이름은 유저가 소유하는
// 라벨이고(types/profile.ts), 동기화는 그것이 비어 있을 때만 씨앗을 심는다.
// 한 계정에 한 번만 성공하면 되고, 그 뒤로는 `known.namedAreas`가 건너뛴다.
// 왜 비었는지는 payload의 `nickname_error`에 남긴다 - 값이 아니라 코드와 최상위
// 키 이름만 담으므로 계정 정보가 새지 않는다.
//
// 에러 코드 분기는 문자열 정규식이 아니라 `err.code` 숫자 비교로 한다. 메시지가
// 코드 뒤에 붙는 순간 `/:1302125$/`의 `$` 앵커가 빗나가고, 앵커를 넓히려 하면
// 템플릿 리터럴이 `\s`의 백슬래시를 먹어 생성된 소스에 `(s|$)`가 박힌다.
//
// 외부 스크립트 로딩은 blablalink CSP의 script-src에 막힐 공산이 커서 로직이
// 인라인으로 강제되고, 따라서 이 코드를 바꾸면 전 유저가 북마크를 다시 깔아야
// 한다. 판단·조립·검증은 전부 서버로 미루고 여기는 얇게 유지할 것.
```

`KnownAccount`의 `namedAreas` 주석도 한 줄 고친다: 지금은 호출 수 줄이기가 이유로 적혀 있는데, 이제는 **거절될 조회를 아예 안 하는 것**이 이유다.

```ts
  /** 이미 이름을 아는 서버들. 그 서버에서는 이름 조회를 아예 건너뛴다 -
   * 이름은 계정당 한 번만 필요하고, 다시 묻는 것은 거절될 뿐이다. */
```

- [ ] **Step 7: 전체 테스트와 타입**

Run: `cd frontend && npm test -- --run && npx tsc -b --noEmit`
Expected: 전부 PASS, 타입 에러 0

- [ ] **Step 8: 커밋**

```bash
git add frontend/src/lib/bookmarklet.ts frontend/src/lib/bookmarklet.test.ts
git commit -m "이름 조회는 한 번만 묻고, 페이지가 이미 물었으면 묻지 않는다"
```

---

### Task 4: 안내 문구를 사실에 맞춘다

**Files:**
- Modify: `frontend/src/components/SyncRosterPanel.tsx:46-53, 59-94` (죽은 가설 주석 + 안내 줄)
- Modify: `frontend/src/lib/helpText.ts:75-116` (도움말)
- Test: `frontend/src/components/SyncRosterPanel.test.tsx:105, 160-200`

**Interfaces:**
- Consumes: Task 3의 `nickname_error`. Task 2의 이름 바꾸기 UI.
- Produces: 없음 (화면 문구만)

**왜:** 지금 화면은 「잠시 뒤 이 계정만 다시 동기화하면 이름이 붙어요」라고 말한다. 그것은 시간이 지나서가 아니라 **화면이 달라져서** 붙던 것이고, 시키는 대로 바로 다시 하면 오히려 창을 밀어 더 안 붙는다. 유저에게 거짓을 시키고 있다.

- [ ] **Step 1: 문구 테스트를 고친다**

`SyncRosterPanel.test.tsx` 165행의 기대를 바꾼다:

```ts
    expect(await screen.findByText(/계정 이름을 읽지 못했어요/)).toBeTruthy()
    expect(screen.getByText(/계정 이름 바꾸기/)).toBeTruthy()
```

185·197행의 `queryByText(/계정 이름을 읽지 못해/)`도 `/계정 이름을 읽지 못했어요/`로 맞춘다.

105행과 108행의 주석 둘은 죽은 가설을 인용하고 있으므로 다음으로 바꾼다:

```ts
  // 계정 이름 자리에 UID가 뜨는 것은 「이름이 잘못 나온다」로만 보인다 -
  // 어디서 고치는지를 같이 말해야 유저가 할 일을 안다.
```
```ts
  // 서버를 고르면 조회가 빨라진다. 다섯 서버를 훑는 것은 느릴 뿐이고,
  // 이름이 안 붙는 것과는 무관하다(2026-08-09 실측).
```

- [ ] **Step 2: 빨간지 확인한다**

Run: `cd frontend && npx vitest run src/components/SyncRosterPanel.test.tsx`
Expected: `Unable to find an element with the text: /계정 이름을 읽지 못했어요/` 로 FAIL

- [ ] **Step 3: 안내 줄을 고친다**

`SyncRosterPanel.tsx`의 `setNotes(...)` 블록과 그 위 주석을 교체:

```tsx
      // 이름 조회는 최선 노력이다 - ShiftyPad 화면이 뜨면서 같은 조회를 이미
      // 하기 때문에, 최초 동기화 시점에는 거의 늘 거절된다(2026-08-09 실측).
      // 그러니 「기다렸다 다시 하세요」는 거짓말이다. 유저가 실제로 할 수 있는
      // 일은 계정 드롭다운 옆에서 이름을 직접 붙이는 것 하나다.
      setNotes(
        nickname || !nicknameError
          ? warnings
          : [
              ...warnings,
              '계정 이름을 읽지 못했어요. 로스터는 정상이에요. ' +
                '위 계정 드롭다운 옆 계정 이름 바꾸기로 원하는 이름을 붙여주세요.',
            ],
      )
```

`nicknameError`를 화면에 그대로 붙이던 부분은 없앤다 — 이제 실패가 정상 경로라 유저에게 원시 코드를 보일 이유가 없다. `nicknameError`는 payload에 남아 있으므로 진단은 그대로 가능하다.

46~53행의 `pickedArea` 주석도 죽은 가설을 인용하므로 교체:

```tsx
  // 어느 서버를 조회할지. null이면 앱이 아는 대로 - 아는 계정이면 그 서버만,
  // 처음 보는 계정이면 다섯을 다 훑는다. 직접 고르면 그 하나만 본다.
  //
  // 고르게 하는 이유는 속도다. 처음 보는 계정은 서버를 몰라 다섯을 다 훑는데,
  // 유저는 자기 서버를 안다.
```

22~25행 `knownFor` prop 주석의 「호출이 잦으면 거절하므로」도 같은 이유로 고친다:

```tsx
  /** 이 open_id에 대해 앱이 이미 아는 것 - 어느 서버에 로스터가 있고, 어느
   * 서버의 이름을 이미 아는지. 아는 서버만 조회해 동기화를 빠르게 하고, 이미
   * 아는 이름은 다시 묻지 않는다(다시 물어도 거절될 뿐이다). */
```

- [ ] **Step 4: 도움말을 고친다**

`helpText.ts`의 `syncHelp.steps` 마지막 항목(99~100행)을 교체하고, 이름에 대한 문단을 하나 더한다:

```ts
      {
        text: 'RapiLab을 켜 둔 채, blablalink에 로그인한 상태로 그 북마크를 눌러요. 로스터가 이 화면으로 바로 들어와요.',
      },
```
→
```ts
      {
        text: 'RapiLab을 켜 둔 채, blablalink에 로그인한 상태로 그 북마크를 눌러요. 로스터가 이 화면으로 바로 들어와요.',
      },
      {
        text: '계정 이름이 UID로 보이면 위 **계정** 드롭다운 옆에서 직접 붙여주세요. blablalink가 이름 조회만 자주 막아서, 이름은 붙을 때도 있고 안 붙을 때도 있어요.',
      },
```

- [ ] **Step 5: 초록인지 확인한다**

Run: `cd frontend && npx vitest run src/components/SyncRosterPanel.test.tsx`
Expected: PASS (모두)

- [ ] **Step 6: 전체 테스트·타입, 그리고 앱에서 눈으로 확인**

Run: `cd frontend && npm test -- --run && npx tsc -b --noEmit`
Expected: 전부 PASS, 타입 에러 0

그다음 앱을 띄워 이름 바꾸기가 실제로 보이고 눌리는지 본다 — CSS 결함은 테스트로 안 잡힌다(`css: false`). `scripts/dev.ps1`로 띄우고 계정 드롭다운 옆을 볼 것.

- [ ] **Step 7: 커밋**

```bash
git add frontend/src/components/SyncRosterPanel.tsx frontend/src/components/SyncRosterPanel.test.tsx frontend/src/lib/helpText.ts
git commit -m "안내를 사실에 맞춘다 - 「기다렸다 다시 하세요」는 거짓이었다"
```

---

### Task 5: 문서를 갱신한다

**Files:**
- Modify: `docs/insights.md:38-90` (1300015 항목 전면 재작성)
- Modify: `docs/decisions.md` (결정 항목 추가)
- Modify: `docs/roadmap.md` (To-Do에 남아 있으면 닫는다)

**Interfaces:** 없음

- [ ] **Step 1: `/document`로 docs-keeper에 넘긴다**

넘길 내용:
- **인사이트 재작성**: `docs/insights.md`의 「blablalink 1300015…(미해결)」 항목은 지금 **틀린 다음 수**를 지시하고 있다(이름 조회를 맨 앞으로 옮기라 → 실측으로 반증됨). 위 「실측이 정한 것」 표와 죽은 가설 다섯(순서·개별 쿨다운·다른 응답의 이름·`GetSavedRoleInfo`·프록시 전체 예산)을 담아 **해결 항목**으로 다시 쓴다. 재현 도구는 `scripts/measure_blablalink_cooldown.js`.
- **결정 기록**: 「계정 이름은 유저가 소유하는 라벨이다」 — 대안(게임 닉네임을 진실로 삼고 재시도로 받아내기 / `GetSavedRoleInfo`로 대체)과 각각이 죽은 이유, 그리고 결과(동기화는 씨앗만 심는다, 재시도 제거, 페이지가 이미 물었으면 건너뛴다).
- **계측 도구 자체**: 「거절도 창을 민다」는 성질 때문에 이 부류의 조사는 **직전 시도 시각을 기억하는 계측기**가 필요했다는 점(`localStorage`에 시도 기록).

- [ ] **Step 2: 문서가 실제로 바뀌었는지 읽어 확인한다**

Run: `git diff --stat docs/`
Expected: `insights.md`·`decisions.md`가 바뀌어 있고, `insights.md`에서 「이름 조회를 맨 앞으로 옮겨 본다」가 사라져 있다.

- [ ] **Step 3: 커밋**

```bash
git add docs/
git commit -m "1300015의 결말을 기록한다 - 원인은 페이지 자신이었다"
```

---

## Self-Review

**Spec coverage.** 결정된 두 가지(유저가 이름을 붙인다 / 측정 종료)는 Task 1·2가 앞을 맡고, 실측에서 확정된 「재시도는 해롭다」는 Task 3이 맡는다. Task 4는 화면이 거짓말을 하지 않게 하고, Task 5는 다음 사람이 죽은 가설을 다시 세우지 않게 한다.

**타입 일관성.** `renameProfile(state, key, name)`(순수 함수, Task 1) / `renameProfile({ key, name })`(훅, Task 2) / `onRename(key, name)`(컴포넌트 prop, Task 2) 셋은 이름은 겹치지만 층이 다르다. 기존 `renameRun`이 정확히 같은 세 층 구조를 쓰고 있으므로 그 관례를 따른 것이다.

**이 계획이 뒤집는 기존 테스트.** 넷이다. 전부 죽은 가설을 고정하고 있어서, 남겨두면 고침을 막는다.
- `profile.test.ts` — `닉네임이 실제로 바뀌면 갱신한다`, `…byte-동일이면 results를 유지한다`의 닉네임 단언
- `bookmarklet.test.ts` — `이름 조회가 한 번 튕겨도 다시 시도해 받아낸다`, `세 번 다 튕기면 시도 횟수를 적어 보낸다`, `호출 사이에 간격을 둔다`

**각 테스트를 무엇이 빨갛게 만드나** (빈 데이터에서 초록인 테스트를 만들지 않기 위한 자문):
- Task 1의 덮어쓰기 테스트 → `nickname: args.nickname || existing.nickname` 로 되돌리면 빨개진다.
- Task 1의 씨앗 테스트 → 덮어쓰기를 아예 막으면(`nickname: existing.nickname`) 빨개진다.
- Task 2의 입력 초기값 테스트 → `setRenameValue(active?.nickname ?? '')`를 `?? activeKey`로 바꾸면 빨개진다.
- Task 3의 `asked` 카운터 → 재시도 루프를 되살리면 1이 3이 되어 빨개진다. `PAGE_ASKED` 가드를 떼면 0이 1이 되어 빨개진다.
- Task 3의 「페이지가 이름을 조회하지 않았으면 한 번 묻는다」 → 가드를 「무조건 건너뛴다」로 잘못 넓히면 빨개진다. 이 테스트가 없으면 가드를 지나치게 넓혀도 아무도 모른다.
- Task 4의 문구 테스트 → 옛 문구로 되돌리면 빨개진다.
