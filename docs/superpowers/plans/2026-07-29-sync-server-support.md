# 서버별 로스터 동기화 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 한 blablalink 계정이 여러 게임 서버에 데이터를 가질 수 있다는 사실을 동기화 전 구간이 알게 해서, 일본이 아닌 서버(한국 등)의 로스터도 정확히 가져오게 한다.

**Architecture:** 북마크릿이 다섯 서버를 모두 조회해 니케가 있는 서버만 후보로 올린다. 후보가 하나면 앱이 그대로 진행하고, 둘 이상이면 앱이 사용자에게 고르게 한 뒤 **고른 것만** 백엔드에 조립시킨다. 프로필의 정체성은 `open_id` 단독에서 `(open_id, area)` 쌍으로 바뀌므로, 같은 사람의 두 서버 로스터가 서로 덮어쓰지 않는다.

**Tech Stack:** React 19 + TypeScript + Vite, Vitest + @testing-library/react.

**설계 문서:** `docs/superpowers/specs/2026-07-29-sync-region-support-design.md`

## Global Constraints

- 작업 디렉터리는 워크트리 `.claude/worktrees/fix+sync-region-area-id`, 브랜치 `worktree-fix+sync-region-area-id`. `main`/`master`는 없다.
- 프론트엔드만 건드린다. `backend/`와 `tools/`는 읽기 전용이다 — 둘 다 이미 `area`를 파라미터로 받으므로 손댈 것이 없다.
- 테스트 명령은 `npm --prefix frontend test -- --run`. 시작 기준선은 **47 파일 / 423 passed**이며, 어떤 태스크도 이 수를 줄이지 않는다.
- **사용자에게 보이는 말은 "서버"다.** "리전"은 blablalink API 용어(`nikke_area_id`, `GetRegionList`)를 설명하는 코드 주석에만 쓴다. 화면 문구·라벨·에러 메시지에는 쓰지 않는다.
- 서버 표기는 정확히 이 다섯 코드다: `JP`(81) · `NA`(82) · `KR`(83) · `GL`(84) · `SEA`(85).
- `open_id`는 숫자만으로 이뤄지거나 빈 문자열이다(`lib/shareUrl.ts`의 `/^\d{6,}$/`가 입력을 검증한다). 따라서 `:`를 구분자로 쓰는 복합 키에서 openId 쪽에 `:`가 섞일 일은 없다. **복합 키는 절대 다시 쪼개지 않는다** — `Profile`이 `openId`와 `area`를 각각 필드로 갖는다.
- 주석은 무엇을/왜만 쓴다. "예전엔 이랬다", "…로 바꿨다" 같은 변경 이력을 주석에 남기지 않는다.
- 커밋 메시지는 이 저장소 관례를 따른다: 지금 코드에 대해 참인 사실을 도메인 언어로 서술한다.

---

### Task 1: 서버 상수

**Files:**
- Create: `frontend/src/types/server.ts`
- Test: `frontend/src/types/server.test.ts`

**Interfaces:**
- Consumes: 없음 (첫 태스크)
- Produces:
  - `SERVERS: readonly { area: number; label: string }[]` — 81 JP · 82 NA · 83 KR · 84 GL · 85 SEA, 이 순서
  - `serverLabel(area: number): string` — 모르는 area는 `String(area)`를 돌려준다
  - `SERVER_AREAS: readonly number[]` — `[81, 82, 83, 84, 85]`

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`frontend/src/types/server.test.ts`:
```ts
import { describe, expect, it } from 'vitest'
import { SERVERS, SERVER_AREAS, serverLabel } from './server'

describe('SERVERS', () => {
  it('blablalink의 다섯 서버를 area와 표기로 담는다', () => {
    expect(SERVERS.map((s) => [s.area, s.label])).toEqual([
      [81, 'JP'],
      [82, 'NA'],
      [83, 'KR'],
      [84, 'GL'],
      [85, 'SEA'],
    ])
  })

  it('SERVER_AREAS는 SERVERS의 area만 순서대로 담는다', () => {
    expect(SERVER_AREAS).toEqual([81, 82, 83, 84, 85])
  })
})

describe('serverLabel', () => {
  it('area를 서버 표기로 바꾼다', () => {
    expect(serverLabel(81)).toBe('JP')
    expect(serverLabel(83)).toBe('KR')
  })

  // 새 서버가 열리면 목록보다 데이터가 먼저 도착할 수 있다. 그때 라벨 자리가
  // 비는 것보다 숫자가 보이는 편이 낫다.
  it('모르는 area는 숫자를 그대로 보여준다', () => {
    expect(serverLabel(99)).toBe('99')
  })
})
```

- [ ] **Step 2: 실패를 확인한다**

Run: `npm --prefix frontend test -- --run src/types/server.test.ts`
Expected: FAIL — `./server` 모듈이 없다.

- [ ] **Step 3: 구현한다**

`frontend/src/types/server.ts`:
```ts
// 한 blablalink 계정은 여러 게임 서버에 각각 다른 로스터를 가질 수 있고, API는
// 서버를 `nikke_area_id`로 지목한다. 목록의 출처는 blablalink 자신이다:
// GET api/lip/direct/commodity/Game/GetRegionList?game_id=29080 -> area_list.
// API가 부르는 이름은 Japan/NA/Korea/Global/SEA이고, 화면에는 짧은 코드를 쓴다.
// 하드코딩인 이유: 이 목록이 바뀌는 것은 새 서버가 열릴 때뿐이고, 그때 한 줄
// 더하는 것이 라이브 조회를 유지하는 것보다 싸다.

export const SERVERS: readonly { area: number; label: string }[] = [
  { area: 81, label: 'JP' },
  { area: 82, label: 'NA' },
  { area: 83, label: 'KR' },
  { area: 84, label: 'GL' },
  { area: 85, label: 'SEA' },
]

export const SERVER_AREAS: readonly number[] = SERVERS.map((s) => s.area)

export const serverLabel = (area: number): string =>
  SERVERS.find((s) => s.area === area)?.label ?? String(area)
```

- [ ] **Step 4: 통과를 확인한다**

Run: `npm --prefix frontend test -- --run`
Expected: 426 passed (기준선 423 + 새 3건)

- [ ] **Step 5: 커밋**

```bash
git add frontend/src/types/server.ts frontend/src/types/server.test.ts
git commit -m "The five game servers an account can hold a roster on"
```

---

### Task 2: 프로필 정체성을 `(open_id, area)` 쌍으로

**Files:**
- Modify: `frontend/src/types/profile.ts` (전반)
- Modify: `frontend/src/hooks/useProfiles.ts` (`readStoredProfiles`, 반환 API)
- Modify: `frontend/src/App.tsx` (`activeOpenId` 사용처 6곳)
- Modify: `frontend/src/components/ProfileSwitcher.tsx` (props 이름)
- Modify: `frontend/src/components/RecommendPanel.tsx` (`activeOpenId` prop 이름)
- Test: `frontend/src/types/profile.test.ts`, `frontend/src/hooks/useProfiles.test.ts`, 그리고 위 컴포넌트들의 기존 테스트

**Interfaces:**
- Consumes: 없음
- Produces:
  - `profileKey(openId: string, area: number): string` — `` `${openId}:${area}` ``
  - `Profile`에 `area: number` 추가
  - `ProfilesState.activeOpenId` → `activeKey: string | null`
  - `upsertProfile(state, { openId, area, nickname, roster })` — 키를 내부에서 만들고 그 프로필을 활성으로 만든다
  - `switchProfile(state, key)` · `deleteProfile(state, key)` · `saveResult(state, key, args)` — 전부 **복합 키**를 받는다
  - `activeProfile(state)` 시그니처는 그대로
  - `useProfiles()` 반환의 `switchProfile`/`deleteProfile`은 키를 받고, `saveResult`는 `{ key, hash, result, inputs }`를 받고, `upsertProfile`은 `{ openId, area, nickname, roster }`를 받는다

**주의:** 이 태스크는 컴파일이 깨지지 않게 호출부까지 한 번에 옮긴다. 라벨에 서버를 붙이는 것은 Task 3이므로 여기서는 **표시 문구를 바꾸지 않는다**.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`frontend/src/types/profile.test.ts` 끝에 추가:
```ts
describe('(open_id, area) 정체성', () => {
  it('같은 open_id의 두 서버 프로필이 서로 덮어쓰지 않는다', () => {
    const jp = upsertProfile(emptyProfilesState(), {
      openId: '111111',
      area: 81,
      nickname: 'FIENN',
      roster: [],
    })
    const both = upsertProfile(jp, {
      openId: '111111',
      area: 83,
      nickname: 'FIENN',
      roster: [],
    })

    expect(Object.keys(both.profiles).sort()).toEqual(['111111:81', '111111:83'])
    expect(both.activeKey).toBe('111111:83')
    expect(both.profiles['111111:81'].area).toBe(81)
    expect(both.profiles['111111:83'].area).toBe(83)
  })

  it('한 서버 프로필을 지워도 같은 open_id의 다른 서버는 남는다', () => {
    const state = upsertProfile(
      upsertProfile(emptyProfilesState(), {
        openId: '111111',
        area: 81,
        nickname: 'FIENN',
        roster: [],
      }),
      { openId: '111111', area: 83, nickname: 'FIENN', roster: [] },
    )

    const after = deleteProfile(state, '111111:83')
    expect(Object.keys(after.profiles)).toEqual(['111111:81'])
    expect(after.activeKey).toBe('111111:81')
  })

  it('profileKey는 open_id와 area를 이어 붙인다', () => {
    expect(profileKey('111111', 83)).toBe('111111:83')
  })
})
```

`profile.test.ts` 상단 import에 `profileKey`를 더하고, 기존 테스트들이 쓰는 `activeOpenId`를 `activeKey`로, 기존 `upsertProfile` 호출에 `area: 81`을, `switchProfile`/`deleteProfile`/`saveResult`의 인자를 복합 키로 바꾼다. **단언의 의미는 바꾸지 않는다** — 같은 것을 새 키로 확인한다.

`frontend/src/hooks/useProfiles.test.ts`에 마이그레이션 테스트를 추가한다. 이 파일의 기존 렌더 방식을 그대로 따를 것:
```ts
  it('구 스키마(open_id만 키)를 area 81 프로필로 옮긴다', () => {
    localStorage.setItem(
      'nikke-profiles',
      JSON.stringify({
        activeOpenId: '111111',
        profiles: {
          '111111': {
            openId: '111111',
            nickname: 'FIENN',
            roster: [],
            results: {},
            lastResultHash: null,
            lastInputs: null,
          },
        },
      }),
    )

    const { result } = renderHook(() => useProfiles())

    expect(Object.keys(result.current.state.profiles)).toEqual(['111111:81'])
    expect(result.current.state.activeKey).toBe('111111:81')
    expect(result.current.state.profiles['111111:81'].area).toBe(81)
  })

  it('이미 새 스키마면 그대로 둔다', () => {
    localStorage.setItem(
      'nikke-profiles',
      JSON.stringify({
        activeKey: '111111:83',
        profiles: {
          '111111:83': {
            openId: '111111',
            area: 83,
            nickname: 'FIENN',
            roster: [],
            results: {},
            lastResultHash: null,
            lastInputs: null,
          },
        },
      }),
    )

    const { result } = renderHook(() => useProfiles())

    expect(Object.keys(result.current.state.profiles)).toEqual(['111111:83'])
    expect(result.current.state.activeKey).toBe('111111:83')
  })
```

- [ ] **Step 2: 실패를 확인한다**

Run: `npm --prefix frontend test -- --run src/types/profile.test.ts src/hooks/useProfiles.test.ts`
Expected: FAIL — `profileKey`가 없고 `activeKey`가 `undefined`다.

- [ ] **Step 3: 구현한다**

`frontend/src/types/profile.ts`:
```ts
export interface Profile {
  openId: string
  /** 이 로스터가 속한 게임 서버(blablalink API의 `nikke_area_id`). 한 open_id가
   * 여러 서버에 각각 로스터를 가질 수 있어서, 프로필을 특정하려면 둘 다 필요하다. */
  area: number
  nickname: string
  roster: NikkeDraft[]
  results: Record<string, StoredResult>
  lastResultHash: string | null
  lastInputs: StoredInputs | null
}

export interface ProfilesState {
  activeKey: string | null
  profiles: Record<string, Profile>
}

/** 프로필 저장소의 키. 두 서버의 같은 계정이 서로 덮어쓰지 않게 하는 것이 전부라,
 * 다시 쪼개 쓰지 않는다 - openId와 area는 Profile에 필드로 들어 있다. */
export const profileKey = (openId: string, area: number): string => `${openId}:${area}`

export const emptyProfilesState = (): ProfilesState => ({
  activeKey: null,
  profiles: {},
})
```

`upsertProfile`을 이렇게 바꾼다(기존 닉네임 폴백 주석과 로스터 변경 시 캐시 무효화 규칙은 그대로 유지):
```ts
export const upsertProfile = (
  state: ProfilesState,
  args: { openId: string; area: number; nickname: string; roster: NikkeDraft[] },
): ProfilesState => {
  const key = profileKey(args.openId, args.area)
  const existing = state.profiles[key]
  const rosterChanged =
    existing !== undefined &&
    JSON.stringify(existing.roster) !== JSON.stringify(args.roster)

  const profile: Profile = existing
    ? {
        ...existing,
        nickname: args.nickname || existing.nickname,
        roster: args.roster,
        ...(rosterChanged
          ? { results: {}, lastResultHash: null, lastInputs: null }
          : {}),
      }
    : {
        openId: args.openId,
        area: args.area,
        nickname: args.nickname,
        roster: args.roster,
        results: {},
        lastResultHash: null,
        lastInputs: null,
      }

  return {
    activeKey: key,
    profiles: { ...state.profiles, [key]: profile },
  }
}

export const switchProfile = (state: ProfilesState, key: string): ProfilesState => ({
  ...state,
  activeKey: key,
})

/** 활성 프로필을 지우면 남은 것 하나로 넘어가고, 없으면 null이 된다. */
export const deleteProfile = (state: ProfilesState, key: string): ProfilesState => {
  const { [key]: _removed, ...remaining } = state.profiles
  const activeKey =
    state.activeKey === key ? (Object.keys(remaining)[0] ?? null) : state.activeKey
  return { activeKey, profiles: remaining }
}

export const activeProfile = (state: ProfilesState): Profile | null =>
  state.activeKey === null ? null : (state.profiles[state.activeKey] ?? null)
```

`saveResult`의 두 번째 인자 이름을 `openId`에서 `key`로 바꾸고 본문의 `state.profiles[openId]`/`[openId]:`를 `key`로 바꾼다. 나머지 LRU 로직은 그대로 둔다.

`frontend/src/hooks/useProfiles.ts` — 마이그레이션을 `readStoredProfiles` 안에 넣는다:
```ts
/** 복합 키가 생기기 전의 저장소는 open_id만으로 프로필을 키잡고 `activeOpenId`를
 * 들고 있었다. 그때 동기화된 데이터는 전부 area 81로 조회된 것이라, 81을 채워
 * 넣으면 정확하다. 멱등이다 - 이미 새 모양이면 손대지 않는다. */
const migrate = (raw: unknown): ProfilesState => {
  const state = raw as Partial<ProfilesState> & {
    activeOpenId?: string | null
    profiles?: Record<string, Profile & { area?: number }>
  }
  const profiles = state.profiles ?? {}
  if (state.activeKey !== undefined && !('activeOpenId' in state)) {
    return { activeKey: state.activeKey ?? null, profiles: profiles as Record<string, Profile> }
  }

  const migrated: Record<string, Profile> = {}
  for (const [key, profile] of Object.entries(profiles)) {
    const area = profile.area ?? 81
    migrated[profileKey(profile.openId, area)] = { ...profile, area }
  }
  const legacyActive = state.activeOpenId ?? null
  const activeOpenIdProfile = legacyActive === null ? undefined : profiles[legacyActive]
  return {
    activeKey:
      activeOpenIdProfile === undefined
        ? (state.activeKey ?? null)
        : profileKey(activeOpenIdProfile.openId, activeOpenIdProfile.area ?? 81),
    profiles: migrated,
  }
}
```
`readStoredProfiles`의 `return JSON.parse(raw) as ProfilesState`를 `return migrate(JSON.parse(raw))`로 바꾼다. `profileKey`와 `Profile`을 import에 더한다.

훅의 콜백 이름/인자를 맞춘다:
```ts
  const upsert = useCallback(
    (args: { openId: string; area: number; nickname: string; roster: NikkeDraft[] }) => {
      setState((current) => upsertProfile(current, args))
    },
    [],
  )

  const switchTo = useCallback((key: string) => {
    setState((current) => switchProfile(current, key))
  }, [])

  const remove = useCallback((key: string) => {
    setState((current) => deleteProfile(current, key))
  }, [])

  const save = useCallback(
    (args: { key: string; hash: string; result: StoredResult; inputs: StoredInputs }) => {
      setState((current) =>
        pureSaveResult(current, args.key, {
          hash: args.hash,
          result: args.result,
          inputs: args.inputs,
        }),
      )
    },
    [],
  )
```
`Profiles` 인터페이스의 시그니처도 같이 고친다.

`frontend/src/components/ProfileSwitcher.tsx` — props 이름만 바꾼다(라벨은 Task 3):
`activeOpenId: string | null` → `activeKey: string | null`, `onSwitch`/`onDelete`는 키를 받는다. 본문에서 `profiles.find((p) => p.openId === activeOpenId)`는 **키 비교로** 바뀌어야 하므로, `profiles`가 아니라 키를 알아야 한다. 가장 작은 변경은 props에 이미 있는 것으로 키를 만드는 것이다:
```tsx
import { profileKey, type Profile } from '../types/profile'
...
  const active = profiles.find((p) => profileKey(p.openId, p.area) === activeKey)
  const activeLabel = active ? labelFor(active) : UNNAMED

  const handleDelete = () => {
    if (activeKey === null) return
    if (window.confirm(`"${activeLabel}" 프로필을 삭제할까요? 동기화된 로스터와 캐시된 결과가 함께 삭제돼요.`)) {
      onDelete(activeKey)
    }
  }
```
`<select value={activeKey ?? ''}>`, `<option key={k} value={k}>`에서 `k = profileKey(profile.openId, profile.area)`.

`frontend/src/App.tsx` — `state.activeOpenId`를 `state.activeKey`로 바꾸고, `ProfileSwitcher`에 `activeKey={state.activeKey}`, `RecommendPanel`에 `activeKey={state.activeKey}`를 넘긴다. `saveResult` 호출은:
```tsx
                onResult={(args) => {
                  if (state.activeKey) saveResult({ key: state.activeKey, ...args })
                }}
```
세 개의 `key={state.activeOpenId ?? 'none'}`은 `key={state.activeKey ?? 'none'}`으로.

`frontend/src/components/RecommendPanel.tsx` — prop `activeOpenId: string | null`을 `activeKey: string | null`로 이름만 바꾼다(주석의 설명도 "활성 프로필"을 가리키게 맞춘다). 복원 effect의 의존성 배열 `[activeOpenId]` → `[activeKey]`. 이 값은 프로필 정체성으로만 쓰이므로 그 외 로직 변경은 없다.

컴파일이 깨지는 테스트 파일들(`App.test.tsx`, `ProfileSwitcher.test.tsx`, `RecommendPanel.test.tsx`, `profile.test.ts`, `useProfiles.test.ts`)의 픽스처와 prop 이름을 새 이름으로 맞춘다. **단언을 약화시키지 말 것** — 같은 것을 새 이름/새 키로 확인한다.

- [ ] **Step 4: 통과를 확인한다**

Run: `npm --prefix frontend run build` (타입체크)
Expected: 통과

Run: `npm --prefix frontend test -- --run`
Expected: 431 passed (426 + 새 5건)

- [ ] **Step 5: 커밋**

```bash
git add frontend/src frontend/src/types frontend/src/hooks frontend/src/components
git commit -m "A profile is an account on a server, not just an account"
```

---

### Task 3: 프로필 드롭다운에 서버 표기

**Files:**
- Modify: `frontend/src/components/ProfileSwitcher.tsx` (`labelFor`)
- Test: `frontend/src/components/ProfileSwitcher.test.tsx`

**Interfaces:**
- Consumes: Task 1의 `serverLabel(area)`, Task 2의 `Profile.area`
- Produces: 드롭다운 옵션과 삭제 버튼 접근명이 `<이름> (<서버>)` 형태

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`frontend/src/components/ProfileSwitcher.test.tsx`에 추가한다. 이 파일의 `makeProfile` 헬퍼에는 Task 2에서 `area`가 들어갔으므로 그대로 쓴다:
```tsx
  it('같은 닉네임의 두 서버 계정을 서버 표기로 구분한다', () => {
    const profiles = [
      makeProfile({ openId: '111111', area: 81, nickname: 'FIENN' }),
      makeProfile({ openId: '111111', area: 83, nickname: 'FIENN' }),
    ]
    render(
      <ProfileSwitcher
        profiles={profiles}
        activeKey="111111:83"
        onSwitch={vi.fn()}
        onDelete={vi.fn()}
      />,
    )
    expect(screen.getByRole('option', { name: 'FIENN (JP)' })).toBeInTheDocument()
    expect(screen.getByRole('option', { name: 'FIENN (KR)' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'FIENN (KR) 프로필 삭제' })).toBeInTheDocument()
  })

  it('이름이 없는 프로필에도 서버가 붙는다', () => {
    const profiles = [makeProfile({ openId: '', area: 83, nickname: '' })]
    render(
      <ProfileSwitcher
        profiles={profiles}
        activeKey=":83"
        onSwitch={vi.fn()}
        onDelete={vi.fn()}
      />,
    )
    expect(screen.getByRole('option', { name: '이름 없는 계정 (KR)' })).toBeInTheDocument()
  })
```

기존 라벨 단언들(`'본계'`, `'no-nick'`, `'이름 없는 계정'` 등)은 이제 서버가 붙으므로 그에 맞게 고친다. `makeProfile`의 기본 `area`가 81이면 `'Fienn (JP)'` 형태가 된다.

- [ ] **Step 2: 실패를 확인한다**

Run: `npm --prefix frontend test -- --run src/components/ProfileSwitcher.test.tsx`
Expected: FAIL — 라벨에 서버가 없다.

- [ ] **Step 3: 구현한다**

`frontend/src/components/ProfileSwitcher.tsx`:
```tsx
import { serverLabel } from '../types/server'
...
/** 프로필은 닉네임으로 불리고, 닉네임을 못 읽은 동기화는 open_id가 대신 선다.
 * 둘 다 없는 동기화가 남긴 프로필도 골라내 지울 수 있어야 하므로 이름이 필요하다.
 * 서버를 뒤에 붙이는 이유: 한 사람이 두 서버에 같은 닉네임으로 있을 수 있고,
 * 그러면 닉네임만으로는 어느 쪽인지 알 수 없다. */
const labelFor = (profile: Profile): string =>
  `${profile.nickname || profile.openId || UNNAMED} (${serverLabel(profile.area)})`
```

- [ ] **Step 4: 통과를 확인한다**

Run: `npm --prefix frontend test -- --run`
Expected: 433 passed (431 + 새 2건)

- [ ] **Step 5: 커밋**

```bash
git add frontend/src/components/ProfileSwitcher.tsx frontend/src/components/ProfileSwitcher.test.tsx
git commit -m "Two accounts with one nickname are told apart by their server"
```

---

### Task 4: 북마크릿이 다섯 서버를 훑는다

**Files:**
- Modify: `frontend/src/lib/bookmarklet.ts` (`buildBookmarklet`의 생성 소스)
- Test: `frontend/src/lib/bookmarklet.test.ts`

**Interfaces:**
- Consumes: Task 1의 `SERVER_AREAS`
- Produces: 북마크릿이 보내는 payload 모양 —
  `{ open_id: string, servers: { area: number, nickname: string, owned: unknown[], character_details: unknown[], recycle_room_researches: unknown[] }[] }`.
  `servers`에는 니케가 1기 이상인 서버만 들어가고, 없으면 payload를 보내지 않고 alert를 낸다.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`frontend/src/lib/bookmarklet.test.ts`의 `area 81과 blablalink origin 가드를 포함한다` 테스트를 다음으로 대체한다. 이 파일이 생성 소스를 검사하는 방식(`decodeURIComponent` 등)은 기존 테스트를 따를 것:
```ts
  it('다섯 서버를 모두 훑고 area를 고정하지 않는다', () => {
    expect(source).toContain('[81,82,83,84,85]')
    expect(source).not.toContain('nikke_area_id:81')
    expect(source).toContain('nikke_area_id:a')
  })

  it('서버별 조회 실패는 그 서버만 건너뛴다', () => {
    // 한 서버의 일시적 오류(1303002가 관측됨)가 동기화 전체를 죽이면 안 된다.
    expect(source).toContain('catch(e){if(!probeErr)probeErr=e;owned=[]}')
  })

  it('니케가 있는 서버가 하나도 없으면 사람이 읽을 문구를 낸다', () => {
    expect(source).toContain('니케를 찾지 못했어요')
  })

  it('payload는 서버 목록을 담는다', () => {
    expect(source).toContain('servers:servers')
  })
```

- [ ] **Step 2: 실패를 확인한다**

Run: `npm --prefix frontend test -- --run src/lib/bookmarklet.test.ts`
Expected: FAIL — 소스가 아직 `nikke_area_id:81`을 담고 있다.

- [ ] **Step 3: 구현한다**

`frontend/src/lib/bookmarklet.ts` 상단에 import를 더한다:
```ts
import { SERVER_AREAS } from '../types/server'
```

파일 헤더 주석의 마지막 단락 앞에 한 문단을 더한다:
```
// 한 계정이 여러 서버에 로스터를 가질 수 있으므로 다섯 서버를 모두 조회한다.
// 어느 것을 쓸지는 앱이 정한다 - 여기서는 니케가 있는 서버를 후보로 올리는
// 것까지만 한다. 서버 하나의 조회 실패는 그 서버만 건너뛴다: 1303002
// ("proxy.GetUserShiftyspadPrivacy error")가 간헐적으로 관측됐고, 그것이
// 나머지 서버의 동기화를 막아선 안 된다.
```

`source` 템플릿의 `const base=...`부터 `payload={...}` 까지를 다음으로 바꾼다:
```
const AREAS=[${SERVER_AREAS.join(',')}];
try{
 const found=[];let probeErr=null;
 for(const a of AREAS){
  let owned=[];
  try{owned=(await call('GetUserCharacters',{intl_open_id:'${openId}',nikke_area_id:a})).characters||[]}catch(e){if(!probeErr)probeErr=e;owned=[]}
  if(owned.length)found.push({area:a,owned:owned})}
 if(!found.length){if(probeErr)throw probeErr;throw new Error('이 계정에서 니케를 찾지 못했어요. 공유 URL이 맞는지 확인해주세요.')}
 const servers=[];
 for(const f of found){
  const base={intl_open_id:'${openId}',nikke_area_id:f.area};
  const detail=await call('GetUserCharacterDetails',{...base,name_codes:f.owned.map(c=>c.name_code)});
  const outpost=await call('GetUserProfileOutpostInfo',{...base});
  const basic=await call('GetUserProfileBasicInfo',{...base}).catch(()=>null);
  const bi=(basic&&basic.basic_info)||{};
  servers.push({area:f.area,nickname:bi.nickname||bi.role_name||'',owned:f.owned,character_details:detail.character_details||[],recycle_room_researches:((outpost.outpost_info||{}).recycle_room_researches)||[]})}
 payload={open_id:'${openId}',servers:servers};
 send()
}catch(err){
```
`catch(err)` 블록의 alert 매핑은 그대로 둔다 — 후보가 하나도 없을 때 첫 조회 오류를 다시 던지므로, `300001`("로그인이 필요해요")과 `1303005`("공유 URL을 다시 확인해주세요") 매핑이 계속 살아 있다.

- [ ] **Step 4: 통과를 확인한다**

Run: `npm --prefix frontend test -- --run`
Expected: 436 passed (433 + 새 4건 − 대체된 1건)

- [ ] **Step 5: 커밋**

```bash
git add frontend/src/lib/bookmarklet.ts frontend/src/lib/bookmarklet.test.ts
git commit -m "The bookmarklet asks every server which ones hold a roster"
```

---

### Task 5: 수신 훅이 후보를 모아 선택을 기다린다

**Files:**
- Modify: `frontend/src/hooks/useBookmarkletImport.ts`
- Test: `frontend/src/hooks/useBookmarkletImport.test.ts`

**Interfaces:**
- Consumes: Task 4의 payload 모양
- Produces: `useBookmarkletImport(onRoster)`가 돌려주는 값 —
  - `status: 'idle' | 'choosing' | 'importing' | 'done' | 'error'`
  - `error: string | null`
  - `candidates: { area: number; count: number }[]` — 서버가 둘 이상일 때만 채워진다
  - `choose(area: number): void` — 그 서버 하나만 조립해 `onRoster`를 부른다
  - `onRoster`는 `{ openId: string; area: number; nickname: string; raw: unknown }`를 받는다 (`area` 추가)

**주의:** 조립(`assembleRoster`)은 **선택 이후**로 미룬다. 후보가 여러 개일 때 미리 조립하면 버릴 것을 위해 백엔드를 왕복한다.

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`frontend/src/hooks/useBookmarkletImport.test.ts`에 추가한다. 이 파일의 `EMPTY`/`post` 헬퍼를 그대로 쓴다:
```ts
  const server = (area: number, count: number, nickname = '') => ({
    area,
    nickname,
    owned: Array.from({ length: count }, (_, i) => ({ name_code: i + 1 })),
    character_details: [],
    recycle_room_researches: [],
  })

  it('서버가 하나면 묻지 않고 바로 조립해 넘긴다', async () => {
    vi.mocked(assembleRoster).mockResolvedValue({ units: [] })
    const onRoster = vi.fn()
    renderHook(() => useBookmarkletImport(onRoster))

    post(BLABLALINK_ORIGIN, {
      type: PAYLOAD_MESSAGE,
      payload: { open_id: 'abc123', servers: [server(83, 181, 'FIENN')] },
    })

    await waitFor(() =>
      expect(onRoster).toHaveBeenCalledWith({
        openId: 'abc123',
        area: 83,
        nickname: 'FIENN',
        raw: { units: [] },
      }),
    )
  })

  it('서버가 둘이면 고르기 전에는 아무것도 조립하지 않는다', async () => {
    vi.mocked(assembleRoster).mockResolvedValue({ units: [] })
    const onRoster = vi.fn()
    const { result } = renderHook(() => useBookmarkletImport(onRoster))

    post(BLABLALINK_ORIGIN, {
      type: PAYLOAD_MESSAGE,
      payload: { open_id: 'abc123', servers: [server(81, 186), server(83, 10)] },
    })

    await waitFor(() => expect(result.current.status).toBe('choosing'))
    expect(result.current.candidates).toEqual([
      { area: 81, count: 186 },
      { area: 83, count: 10 },
    ])
    expect(assembleRoster).not.toHaveBeenCalled()
    expect(onRoster).not.toHaveBeenCalled()
  })

  it('고른 서버 하나만 조립한다', async () => {
    vi.mocked(assembleRoster).mockResolvedValue({ units: [] })
    const onRoster = vi.fn()
    const { result } = renderHook(() => useBookmarkletImport(onRoster))

    post(BLABLALINK_ORIGIN, {
      type: PAYLOAD_MESSAGE,
      payload: { open_id: 'abc123', servers: [server(81, 186), server(83, 10)] },
    })
    await waitFor(() => expect(result.current.status).toBe('choosing'))

    // `choose`는 상태를 바꾸므로 act 안에서 부른다 - 밖에서 부르면 경고가 찍히고,
    // 이 저장소는 테스트 출력이 깨끗해야 통과다.
    await act(async () => {
      result.current.choose(83)
    })

    await waitFor(() => expect(onRoster).toHaveBeenCalledOnce())
    expect(onRoster).toHaveBeenCalledWith({
      openId: 'abc123',
      area: 83,
      nickname: '',
      raw: { units: [] },
    })
    expect(vi.mocked(assembleRoster).mock.calls[0][0].owned).toHaveLength(10)
  })

  // 이미 설치된 북마크릿은 area 81로 조회한 데이터를 옛 모양으로 보낸다.
  it('구 payload는 area 81 서버 하나로 받는다', async () => {
    vi.mocked(assembleRoster).mockResolvedValue({ units: [] })
    const onRoster = vi.fn()
    renderHook(() => useBookmarkletImport(onRoster))

    post(BLABLALINK_ORIGIN, {
      type: PAYLOAD_MESSAGE,
      payload: { ...EMPTY, open_id: 'abc123', nickname: 'FIENN' },
    })

    await waitFor(() =>
      expect(onRoster).toHaveBeenCalledWith({
        openId: 'abc123',
        area: 81,
        nickname: 'FIENN',
        raw: { units: [] },
      }),
    )
  })
```

기존 테스트들의 `onRoster` 단언에 `area: 81`을 더한다(구 shape을 보내므로 81로 승격된다).

**깨뜨리지 말아야 할 기존 테스트 두 개** — 둘 다 그대로 통과해야 하고, 통과 방식이 서로 다르다:
- `open_id가 없는 payload는 프로필을 만들지 않고 오류를 낸다` / `open_id가 공백뿐인 payload도 거절한다` — 로스터 모양은 맞으므로 **에러 상태**가 돼야 한다.
- `blablalink 출처라도 payload가 없거나 형태가 이상하면 assembleRoster를 부르지 않는다` — 이 테스트는 `payload` 누락 · `null` · 문자열 · 필드 일부만인 네 경우를 보낸다. 이들은 **조용히 무시**돼야 하고(에러 상태로 만들지 않는다), 특히 `null`/누락에 `.open_id`를 읽으면 `TypeError`가 던져지므로 형태 검사가 open_id 검사보다 먼저 와야 한다.

- [ ] **Step 2: 실패를 확인한다**

Run: `npm --prefix frontend test -- --run src/hooks/useBookmarkletImport.test.ts`
Expected: FAIL — `candidates`/`choose`가 없고 `onRoster`에 `area`가 없다.

- [ ] **Step 3: 구현한다**

`frontend/src/hooks/useBookmarkletImport.ts`를 이렇게 고친다. 파일 헤더의 `onRoster` ref 설명 단락은 그대로 두고, 그 아래에 한 단락을 더한다:
```
// 한 계정이 여러 서버에 로스터를 가질 수 있어서 북마크릿은 후보를 여러 개
// 보낼 수 있다. 조립은 선택 이후로 미룬다 - 버릴 후보를 위해 백엔드를
// 왕복하지 않는다. 후보가 하나면 물어볼 것이 없으므로 바로 조립한다.
```

타입과 상태:
```ts
type Status = 'idle' | 'choosing' | 'importing' | 'done' | 'error'

export interface BookmarkletImportArgs {
  openId: string
  area: number
  nickname: string
  raw: unknown
}

/** 북마크릿이 올린 한 서버의 원시 로스터. `area`는 blablalink API의
 * `nikke_area_id`이고, 그 서버에서 실제로 니케가 조회된 것만 온다. */
interface ServerPayload {
  area: number
  nickname: string
  owned: unknown[]
  character_details: unknown[]
  recycle_room_researches: unknown[]
}
```

형태 검증을 둘로 나눈다:
```ts
const isServerPayload = (value: unknown): value is ServerPayload =>
  !!value &&
  typeof value === 'object' &&
  typeof (value as ServerPayload).area === 'number' &&
  Array.isArray((value as ServerPayload).owned) &&
  Array.isArray((value as ServerPayload).character_details) &&
  Array.isArray((value as ServerPayload).recycle_room_researches)

// 이미 설치된 북마크릿은 서버 하나(area 81)를 payload 최상단에 펼쳐 보낸다.
const isLegacyPayload = (value: unknown): value is RawRosterPayload =>
  !!value &&
  typeof value === 'object' &&
  Array.isArray((value as RawRosterPayload).owned) &&
  Array.isArray((value as RawRosterPayload).character_details) &&
  Array.isArray((value as RawRosterPayload).recycle_room_researches)

/** 어느 모양으로 왔든 서버 목록 하나로 만든다. 구 payload는 area 81로 조회된
 * 데이터이므로 81을 붙이는 것이 정확하다. */
const toServers = (payload: unknown): ServerPayload[] | null => {
  const p = payload as { servers?: unknown }
  if (Array.isArray(p?.servers)) {
    return p.servers.every(isServerPayload) ? (p.servers as ServerPayload[]) : null
  }
  if (isLegacyPayload(payload)) {
    return [
      {
        area: 81,
        nickname: String((payload as RawRosterPayload).nickname ?? ''),
        owned: payload.owned,
        character_details: payload.character_details,
        recycle_room_researches: payload.recycle_room_researches,
      },
    ]
  }
  return null
}
```

훅 본문:
```ts
export const useBookmarkletImport = (
  onRoster: (args: BookmarkletImportArgs) => void,
) => {
  const [status, setStatus] = useState<Status>('idle')
  const [error, setError] = useState<string | null>(null)
  const [openId, setOpenId] = useState('')
  const [servers, setServers] = useState<ServerPayload[]>([])

  const onRosterRef = useRef(onRoster)
  useEffect(() => {
    onRosterRef.current = onRoster
  })

  const importServer = useCallback(async (id: string, server: ServerPayload) => {
    setStatus('importing')
    setError(null)
    try {
      const assembled = await assembleRoster({
        owned: server.owned,
        character_details: server.character_details,
        recycle_room_researches: server.recycle_room_researches,
      })
      onRosterRef.current({
        openId: id,
        area: server.area,
        nickname: server.nickname,
        raw: assembled,
      })
      setStatus('done')
    } catch (e) {
      setError(
        e instanceof AssembleRosterApiError
          ? describeAssembleRosterApiError(e)
          : e instanceof Error
            ? e.message
            : String(e),
      )
      setStatus('error')
    }
  }, [])

  const handle = useCallback(
    (payload: unknown) => {
      // 출처를 통과한 메시지라도 payload 형태까지 보장되지는 않는다. 모양이
      // 어긋난 것은 조용히 무시한다 - 우리가 보낸 것이 아닐 수도 있고, 화면에
      // 에러를 띄울 근거가 없다. `null`/`undefined`에 속성을 읽으면 던지므로
      // 이 검사가 open_id 검사보다 반드시 앞에 온다.
      if (!payload || typeof payload !== 'object') return
      const list = toServers(payload)
      if (list === null || list.length === 0) return

      setError(null)
      // open_id는 프로필 저장소 키의 절반이다. 없으면 어느 계정인지 알 수 없어
      // 이름 없는 프로필이 생기므로, 받지 않고 그 자리에서 거절한다. 여기까지
      // 왔다면 로스터 모양은 맞으므로, 이것은 조용히 무시할 문제가 아니다.
      const id = String((payload as { open_id?: unknown }).open_id ?? '').trim()
      if (id === '') {
        setError(
          '북마크릿이 계정 정보를 보내지 않았어요. "동기화 방법"을 열어 북마크릿을 다시 설치한 뒤 시도해 주세요.',
        )
        setStatus('error')
        return
      }
      setOpenId(id)
      setServers(list)
      if (list.length === 1) {
        void importServer(id, list[0])
        return
      }
      setStatus('choosing')
    },
    [importServer],
  )

  const choose = useCallback(
    (area: number) => {
      const server = servers.find((s) => s.area === area)
      if (!server) return
      void importServer(openId, server)
    },
    [servers, openId, importServer],
  )

  useEffect(() => {
    const listener = (event: MessageEvent) => {
      if (event.origin !== BLABLALINK_ORIGIN) return
      const data = event.data as { type?: string; payload?: unknown }
      if (data?.type !== PAYLOAD_MESSAGE) return
      handle(data.payload)
    }
    window.addEventListener('message', listener)
    window.opener?.postMessage({ type: READY_MESSAGE }, BLABLALINK_ORIGIN)
    return () => window.removeEventListener('message', listener)
  }, [handle])

  const candidates = servers.map((s) => ({ area: s.area, count: s.owned.length }))

  return { status, error, candidates, choose }
}
```

`useCallback`을 import에 더한다(이미 있으면 그대로).

- [ ] **Step 4: 통과를 확인한다**

Run: `npm --prefix frontend test -- --run`
Expected: 440 passed (436 + 새 4건)

- [ ] **Step 5: 커밋**

```bash
git add frontend/src/hooks/useBookmarkletImport.ts frontend/src/hooks/useBookmarkletImport.test.ts
git commit -m "Assembling a roster waits until the server is known"
```

---

### Task 6: 서버 선택 UI

**Files:**
- Modify: `frontend/src/components/SyncRosterPanel.tsx`
- Modify: `frontend/src/App.tsx` (`onImport`이 `area`를 넘긴다)
- Modify: `frontend/src/App.css` (선택 UI 스타일)
- Test: `frontend/src/components/SyncRosterPanel.test.tsx`, `frontend/src/App.test.tsx`

**Interfaces:**
- Consumes: Task 1의 `serverLabel`, Task 5의 `candidates`/`choose`/`status: 'choosing'`, Task 2의 `upsertProfile({ openId, area, nickname, roster })`
- Produces: 없음 (마지막 태스크)

- [ ] **Step 1: 실패하는 테스트를 쓴다**

`frontend/src/components/SyncRosterPanel.test.tsx`에 추가한다. 이 파일의 `RAW_PAYLOAD`/`postPayload` 헬퍼 방식을 그대로 따르되, 서버 두 개를 담은 payload를 보내는 헬퍼를 새로 만든다:
```tsx
  const postTwoServers = () =>
    act(() => {
      window.dispatchEvent(
        new MessageEvent('message', {
          origin: BLABLALINK_ORIGIN,
          data: {
            type: PAYLOAD_MESSAGE,
            payload: {
              open_id: 'abc123',
              servers: [
                { area: 81, nickname: 'FIENN', owned: [{ name_code: 1 }, { name_code: 2 }], character_details: [], recycle_room_researches: [] },
                { area: 83, nickname: 'FIENN', owned: [{ name_code: 3 }], character_details: [], recycle_room_researches: [] },
              ],
            },
          },
        }),
      )
    })

  it('서버가 둘이면 어느 것을 가져올지 묻고, 고르기 전엔 임포트하지 않는다', async () => {
    const onImport = vi.fn()
    render(<SyncRosterPanel onImport={onImport} />)
    postTwoServers()

    expect(await screen.findByText(/어느 서버의 계정을 가져올까요/)).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /JP \(2기\)/ })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: /KR \(1기\)/ })).toBeInTheDocument()
    expect(onImport).not.toHaveBeenCalled()
  })

  it('고른 서버의 area가 onImport로 넘어간다', async () => {
    const user = userEvent.setup()
    const onImport = vi.fn()
    render(<SyncRosterPanel onImport={onImport} />)
    postTwoServers()

    await user.click(await screen.findByRole('button', { name: /KR \(1기\)/ }))

    await waitFor(() => expect(onImport).toHaveBeenCalledOnce())
    expect(onImport.mock.calls[0][0].area).toBe(83)
  })
```

기존 테스트들의 `onImport` 단언에 `area: 81`이 함께 넘어오는 것을 반영한다(구 shape은 81로 승격된다).

`frontend/src/App.test.tsx`는 `onImport` 경로를 직접 단언하지 않으므로 손대지 않는다. 실패하면 그때 픽스처만 맞춘다.

- [ ] **Step 2: 실패를 확인한다**

Run: `npm --prefix frontend test -- --run src/components/SyncRosterPanel.test.tsx`
Expected: FAIL — 선택 UI가 없다.

- [ ] **Step 3: 구현한다**

`frontend/src/components/SyncRosterPanel.tsx`:
```tsx
import { serverLabel } from '../types/server'
...
interface SyncRosterPanelProps {
  onImport: (args: {
    openId: string
    area: number
    nickname: string
    roster: NikkeDraft[]
  }) => void
  defaultHelpOpen?: boolean
}
```
훅 사용부와 선택 UI:
```tsx
  const { status, error, candidates, choose } = useBookmarkletImport(
    ({ openId, area, nickname, raw }) => {
      const { drafts, warnings } = parseRosterJson(raw)
      onImport({ openId, area, nickname, roster: drafts })
      setSummary(`${drafts.length}기 동기화됨`)
      setNotes(warnings)
    },
  )
```
`{status === 'importing' && ...}` 바로 앞에 넣는다:
```tsx
      {/* 한 계정이 여러 서버에 로스터를 가진 경우다. 어느 쪽을 원하는지는
          짐작할 수 없으므로 - 니케가 많은 쪽이 늘 정답은 아니다 - 물어본다. */}
      {status === 'choosing' && (
        <div className="sync__servers">
          <p className="sync__hint">어느 서버의 계정을 가져올까요?</p>
          <div className="sync__server-choices">
            {candidates.map(({ area, count }) => (
              <button
                key={area}
                type="button"
                className="btn"
                onClick={() => choose(area)}
              >
                {serverLabel(area)} ({count}기)
              </button>
            ))}
          </div>
        </div>
      )}
```

`frontend/src/App.tsx` — `SyncRosterPanel`은 `onImport={upsertProfile}`을 그대로 넘기고 있고, Task 2에서 `upsertProfile`이 `area`를 받게 됐으므로 **추가 변경이 없다**. 두 곳의 `<SyncRosterPanel onImport={upsertProfile} ... />`가 타입체크를 통과하는지 확인만 한다.

`frontend/src/App.css` — `.sync__hint` 규칙 뒤에 붙인다:
```css
/* 서버가 여러 개인 계정에서만 나타나는 선택 줄. 버튼이 한 줄에 들어가지 않으면
   접히도록 둔다 - 서버는 다섯까지 늘 수 있다. */
.sync__servers {
  display: flex;
  flex-direction: column;
  gap: var(--sp-2);
}

.sync__server-choices {
  display: flex;
  flex-wrap: wrap;
  gap: var(--sp-2);
}
```

- [ ] **Step 4: 통과를 확인한다**

Run: `npm --prefix frontend run build`
Expected: 통과

Run: `npm --prefix frontend test -- --run`
Expected: 442 passed (440 + 새 2건)

- [ ] **Step 5: 커밋**

```bash
git add frontend/src/components/SyncRosterPanel.tsx frontend/src/components/SyncRosterPanel.test.tsx frontend/src/App.tsx frontend/src/App.css
git commit -m "When an account has rosters on two servers, ask which one"
```

---

## 마무리 (플랜 실행자 아닌 주 세션이 한다)

- `docs/roadmap.md`의 To-Do 갱신, `docs/decisions.md`·`docs/insights.md` 기록
- Fienn에게 북마크릿 재설치 후 KR 계정 동기화 라이브 확인 요청 — 이 변경은 실제 blablalink 세션 없이는 끝까지 검증할 수 없다
- 트렁크 머지는 Fienn의 승인을 받아서
