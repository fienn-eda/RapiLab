# 다계정 프로필(Multi-Account Profiles) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 여러 NIKKE 계정을 절대 섞이지 않게 각각 보관하고, 각 계정의 추천 결과를 브라우저 재시작 후에도 재활용해 재실행을 줄인다.

**Architecture:** 전적으로 클라이언트(localStorage) 모델. 계정 = blablalink `open_id`로 식별하는 프로필. 계정 고유 데이터(roster·results·마지막 입력)는 프로필 내부에 격리. 서버·인증·DB 없음. 설계 근거: `docs/superpowers/specs/2026-07-23-multi-account-profiles-design.md`.

**Tech Stack:** React + Vite + TypeScript, Vitest. 신규 의존성 없음.

## Global Constraints

- **localStorage 전용, 브라우저 로컬.** 서버/인증/DB/크로스 기기 동기화 없음.
- **프로필 키 = `open_id`. 서로 다른 open_id는 절대 병합 금지**(격리 불변식).
- **백엔드 요청 shape 불변.** `open_id`/`nickname`은 클라이언트에만 저장하고 어떤 백엔드 호출(`/api/assemble-roster`, `/api/recommend*`)에도 싣지 않는다(무상태·프라이버시 규율 유지). 백엔드로 가는 유일 식별자는 기존 `clientId`.
- **엔진은 RNG 없는 결정론적 순수 함수** → (입력→결과) 캐싱은 정확. 캐시 키는 로스터 투자데이터 전체 + boss + draft를 포함해야 무효화가 정확하다.
- **live/mock 스위치는 `src/api/`에 국한**(기존 `recommend.ts`/`recommendRaid.ts` 패턴). 컴포넌트는 활성 클라이언트를 몰라야 한다.
- **테스트 병치**(`*.test.ts(x)`), 타입체크는 `npx tsc -b`(bare `tsc --noEmit`는 아무것도 검사 안 함), 테스트는 `npm run test`(Vitest). 주변 코드 스타일·주석 밀도에 맞춘다.
- **`NikkeDraft` 문자열 필드 모델 유지**(collector 파싱이 이미 이 형태를 생성). 편집 UI만 제거하고 타입은 재사용한다(YAGNI).
- 아직 배포 서비스 아님 → 기존 `nikke-roster` localStorage 키는 **마이그레이션 없이 폐기**.

---

## File Structure

**신규:**
- `frontend/src/types/profile.ts` — `Profile`, `ProfilesState` 타입 + 순수 헬퍼(upsert/switch/delete/migration).
- `frontend/src/types/profile.test.ts`
- `frontend/src/hooks/useProfiles.ts` — localStorage 백킹 프로필 스토어 훅.
- `frontend/src/hooks/useProfiles.test.ts`
- `frontend/src/lib/inputHash.ts` — `hashRecommendInputs(roster, boss, draft)` 안정 해시.
- `frontend/src/lib/inputHash.test.ts`
- `frontend/src/components/ProfileSwitcher.tsx` — 프로필 드롭다운 + 삭제.
- `frontend/src/components/ProfileSwitcher.test.tsx`

**수정:**
- `frontend/src/lib/bookmarklet.ts` — `GetUserProfileBasicInfo` 호출 추가, payload에 `open_id`/`nickname`.
- `frontend/src/hooks/useBookmarkletImport.ts` — payload에서 metadata 분리, roster 필드만 assembleRoster로.
- `frontend/src/api/assembleRoster.ts` — `RawRosterPayload`에서 metadata 분리(백엔드로 안 보냄).
- `frontend/src/components/SyncRosterPanel.tsx` — onImport에 `{openId, nickname, roster}` 전달.
- `frontend/src/App.tsx` — `useRoster` → `useProfiles`, ProfileSwitcher, 읽기전용 로스터, ImportRosterButton 제거.
- `frontend/src/components/RecommendPanel.tsx` — 성공 시 결과 저장 + 마운트/전환 시 복원.
- `frontend/src/components/NikkeCard.tsx` — 읽기전용 표시로 전환.
- `frontend/src/types/nikkeDraft.ts` — `mergeRosterDrafts`(exia) 제거.
- `frontend/README.md` — 다계정/결과영속 계약 섹션 추가.

**제거:**
- `frontend/src/hooks/useRoster.ts`(+test) — `useProfiles`로 대체.
- `frontend/src/components/ImportRosterButton.tsx`(+test) — exia 파일 import UI.
- `frontend/src/lib/exiaImport.ts`의 `parseExiaExport`(+ exia 전용 export). **`deriveSlug`는 유지**(collector `rosterImport.ts`가 사용).
- 수동 입력 필드 컴포넌트(사용처 사라지면): `OverloadOptionsField`·`SkillLevelsField`·`fields/NumberField`·`fields/TextField`(구현 시 usage 확인 후 미사용분만).

---

## Task 1: 프로필 스토어 (`useProfiles` + 타입) — 마이그레이션 폐기·전환·삭제

**Files:**
- Create: `frontend/src/types/profile.ts`, `frontend/src/types/profile.test.ts`
- Create: `frontend/src/hooks/useProfiles.ts`, `frontend/src/hooks/useProfiles.test.ts`

**Interfaces:**
- Consumes: `NikkeDraft` (`../types/nikkeDraft`).
- Produces:
  ```ts
  export interface Profile {
    openId: string
    nickname: string
    roster: NikkeDraft[]
    results: Record<string, StoredResult>   // key = inputHash (Task 2)
    lastResultHash: string | null
    lastInputs: StoredInputs | null          // Task 2 타입
  }
  export interface ProfilesState {
    activeOpenId: string | null
    profiles: Record<string, Profile>
  }
  // 순수 헬퍼(스토어와 훅이 공유):
  export const emptyProfilesState = (): ProfilesState
  export const upsertProfile = (
    state: ProfilesState,
    args: { openId: string; nickname: string; roster: NikkeDraft[] },
  ): ProfilesState   // 신규 openId=생성, 기존=roster/nickname 갱신 + roster 변경 시 results 클리어; activeOpenId=openId
  export const switchProfile = (state: ProfilesState, openId: string): ProfilesState
  export const deleteProfile = (state: ProfilesState, openId: string): ProfilesState  // 활성 삭제 시 activeOpenId=남은 것 중 하나 or null
  export const activeProfile = (state: ProfilesState): Profile | null
  ```
  `StoredResult`/`StoredInputs`는 Task 2에서 정의하되, Task 1은 `results: Record<string, unknown>` 및 `lastInputs: unknown | null`의 자리표시 없이 Task 2 타입을 먼저 선언해도 무방(같은 파일). 여기서는 `results`를 빈 객체로만 다룬다.

- [ ] **Step 1: `profile.ts` 순수 헬퍼 실패 테스트 작성** (`profile.test.ts`)

```ts
import { describe, it, expect } from 'vitest'
import {
  emptyProfilesState, upsertProfile, switchProfile, deleteProfile, activeProfile,
} from './profile'
import type { NikkeDraft } from './nikkeDraft'

const draft = (slug: string): NikkeDraft =>
  ({ id: slug, character_slug: slug, level: '400', hp: '1', atk: '1', def_: '1',
     actualHp: '', actualAtk: '', actualDef: '',
     skill_levels: { skill1: '1', skill2: '1', burst: '1' }, overload_options: [] })

describe('upsertProfile', () => {
  it('새 open_id는 프로필을 만들고 활성으로 만든다', () => {
    const s = upsertProfile(emptyProfilesState(), { openId: 'A', nickname: '본계', roster: [draft('liter')] })
    expect(s.activeOpenId).toBe('A')
    expect(s.profiles.A.nickname).toBe('본계')
    expect(s.profiles.A.roster.map((d) => d.character_slug)).toEqual(['liter'])
  })

  it('다른 open_id는 절대 병합되지 않는다(격리)', () => {
    let s = upsertProfile(emptyProfilesState(), { openId: 'A', nickname: '본계', roster: [draft('liter')] })
    s = upsertProfile(s, { openId: 'B', nickname: '부계', roster: [draft('crown')] })
    expect(Object.keys(s.profiles).sort()).toEqual(['A', 'B'])
    expect(s.profiles.A.roster.map((d) => d.character_slug)).toEqual(['liter'])
    expect(s.profiles.B.roster.map((d) => d.character_slug)).toEqual(['crown'])
  })

  it('기존 open_id 재sync: 로스터가 바뀌면 results를 클리어한다', () => {
    let s = upsertProfile(emptyProfilesState(), { openId: 'A', nickname: '본계', roster: [draft('liter')] })
    s = { ...s, profiles: { ...s.profiles, A: { ...s.profiles.A, results: { h1: {} as never }, lastResultHash: 'h1' } } }
    s = upsertProfile(s, { openId: 'A', nickname: '본계', roster: [draft('liter'), draft('crown')] })
    expect(s.profiles.A.results).toEqual({})
    expect(s.profiles.A.lastResultHash).toBeNull()
  })

  it('기존 open_id 재sync: 로스터가 byte-동일이면 results를 유지한다', () => {
    let s = upsertProfile(emptyProfilesState(), { openId: 'A', nickname: '본계', roster: [draft('liter')] })
    s = { ...s, profiles: { ...s.profiles, A: { ...s.profiles.A, results: { h1: {} as never }, lastResultHash: 'h1' } } }
    s = upsertProfile(s, { openId: 'A', nickname: '본계2', roster: [draft('liter')] })
    expect(s.profiles.A.results).toHaveProperty('h1')
    expect(s.profiles.A.nickname).toBe('본계2')   // 닉네임은 갱신
  })
})

describe('switch/delete/active', () => {
  it('switchProfile은 활성만 바꾼다', () => {
    let s = upsertProfile(emptyProfilesState(), { openId: 'A', nickname: 'a', roster: [] })
    s = upsertProfile(s, { openId: 'B', nickname: 'b', roster: [] })
    s = switchProfile(s, 'A')
    expect(activeProfile(s)?.openId).toBe('A')
  })
  it('활성 프로필 삭제 시 남은 것으로 전환, 마지막이면 null', () => {
    let s = upsertProfile(emptyProfilesState(), { openId: 'A', nickname: 'a', roster: [] })
    s = deleteProfile(s, 'A')
    expect(s.activeOpenId).toBeNull()
    expect(s.profiles).toEqual({})
  })
})
```

- [ ] **Step 2: 테스트 실패 확인**
Run: `cd frontend && npx vitest run src/types/profile.test.ts`
Expected: FAIL — module not found.

- [ ] **Step 3: `profile.ts` 구현**
`upsertProfile`의 roster 비교는 `JSON.stringify(oldRoster) === JSON.stringify(newRoster)`로 판단(같으면 results 유지, 다르면 `results={}`, `lastResultHash=null`, `lastInputs=null`). 새 프로필은 `results:{}`, `lastResultHash:null`, `lastInputs:null`로 초기화. `deleteProfile`은 활성 삭제 시 `Object.keys(remaining)[0] ?? null`로 활성 이전.

- [ ] **Step 4: 테스트 통과 확인**
Run: `cd frontend && npx vitest run src/types/profile.test.ts` → PASS

- [ ] **Step 5: `useProfiles` 실패 테스트 작성** (`useProfiles.test.ts`)
`@testing-library/react`의 `renderHook`/`act` 사용(기존 `useRoster.test.ts` 패턴 참고). 검증:
  - 초기: localStorage 비어있으면 `emptyProfilesState`.
  - **마이그레이션 폐기:** localStorage에 legacy `nikke-roster` 키만 있고 `nikke-profiles`가 없으면, 초기 상태는 빈 프로필이고 `nikke-roster` 키는 제거된다.
  - `upsert`/`switch`/`delete` 액션이 localStorage(`nikke-profiles`)에 반영되고 리렌더에 살아남는다.
  - `activeProfile` 노출.

```ts
it('legacy nikke-roster를 폐기하고 빈 상태로 시작한다', () => {
  localStorage.setItem('nikke-roster', JSON.stringify([{ character_slug: 'liter' }]))
  const { result } = renderHook(() => useProfiles())
  expect(result.current.state.activeOpenId).toBeNull()
  expect(localStorage.getItem('nikke-roster')).toBeNull()
})
```

- [ ] **Step 6: 실패 확인** → Run vitest on the file → FAIL

- [ ] **Step 7: `useProfiles.ts` 구현**
`STORAGE_KEY='nikke-profiles'`. `useState` 초기화 함수에서 (a) `nikke-profiles` 파싱 시도, 실패/부재 시 (b) legacy `nikke-roster` 존재하면 `localStorage.removeItem('nikke-roster')` 후 `emptyProfilesState()`. `useEffect`로 state를 `nikke-profiles`에 직렬화. 액션(`upsert`/`switch`/`delete`)은 순수 헬퍼를 `setState`로 감싸 노출. 파싱 불가 시 `useRoster`처럼 경고 후 빈 상태(폼이 죽지 않게).

- [ ] **Step 8: 통과 확인** → PASS

- [ ] **Step 9: 커밋**
```bash
git add frontend/src/types/profile.ts frontend/src/types/profile.test.ts frontend/src/hooks/useProfiles.ts frontend/src/hooks/useProfiles.test.ts
git commit -m "Add profile store (useProfiles) with open_id isolation and legacy-roster discard"
```

---

## Task 2: 결과 캐시 — inputHash + 저장/복원 타입

**Files:**
- Create: `frontend/src/lib/inputHash.ts`, `frontend/src/lib/inputHash.test.ts`
- Modify: `frontend/src/types/profile.ts`(+test) — `StoredResult`/`StoredInputs` 타입 + `saveResult`/`getResult` 헬퍼

**Interfaces:**
- Consumes: `UserNikkeState`(`./userNikkeState`), `BossProfile`·`RecommendRaidResponse`(또는 그 프론트 타입) from `../types/recommend`, `Draft`(`../types/draft`).
- Produces:
  ```ts
  // inputHash.ts
  export const hashRecommendInputs = (
    roster: UserNikkeState[], boss: BossProfile, draft: Draft | null,
  ): string
  // profile.ts 추가
  export interface StoredInputs { mode: 'raid' | 'draft'; numDecks: number; boss: BossProfile; draft: Draft | null }
  export interface StoredResult { /* RaidResults/DraftResults 렌더에 필요한 필드 = useRecommendRaid 성공 payload */ }
  export const RESULTS_CAP = 20
  export const saveResult = (
    state: ProfilesState, openId: string,
    args: { hash: string; result: StoredResult; inputs: StoredInputs },
  ): ProfilesState   // results[hash]=result, lastResultHash=hash, lastInputs=inputs; 캡 초과 시 가장 오래된 것 제거(LRU)
  export const getResult = (profile: Profile, hash: string): StoredResult | null
  ```

- [ ] **Step 1: `inputHash` 실패 테스트** — 동일 입력은 동일 해시, 입력 순서 무관(로스터 정렬 불변), boss/draft 한 필드만 바뀌어도 해시가 달라짐, `draft=null`(zero-base)과 빈 draft 구분.

```ts
it('로스터 순서가 달라도 같은 해시(정규화)', () => {
  const a = [nikke('liter'), nikke('crown')]; const b = [nikke('crown'), nikke('liter')]
  expect(hashRecommendInputs(a, boss, null)).toBe(hashRecommendInputs(b, boss, null))
})
it('boss 한 필드만 바뀌어도 해시가 다르다', () => {
  expect(hashRecommendInputs(r, boss, null)).not.toBe(hashRecommendInputs(r, { ...boss, enemy_def: 999 }, null))
})
```

- [ ] **Step 2: 실패 확인** → FAIL

- [ ] **Step 3: `inputHash.ts` 구현**
정규화: 로스터를 `character_slug` 기준 정렬 + 각 유닛의 필드를 정렬된 키로 canonical JSON 직렬화, boss는 키 정렬, draft는 각 덱의 slug/lock을 정렬. 직렬화 문자열을 안정 해시(예: FNV-1a 32bit 또는 djb2 — 외부 의존 없이 순수 함수)로 요약해 hex 문자열 반환. 충돌 무시 가능(캐시 미스는 그냥 재계산).

- [ ] **Step 4: 통과 확인** → PASS

- [ ] **Step 5: `profile.ts` saveResult/getResult 실패 테스트** — 저장 후 `getResult` 히트, `lastResultHash`/`lastInputs` 갱신, `RESULTS_CAP` 초과 시 삽입순 가장 오래된 항목 제거.

- [ ] **Step 6: 실패 확인** → FAIL

- [ ] **Step 7: 구현** — `results`는 삽입 순서를 갖는 객체(JS 객체 키 순서=삽입순, 문자열 키)로 LRU 근사: 캡 초과 시 `Object.keys()[0]` 제거. `saveResult`는 재저장 시 기존 키 삭제 후 재삽입(최신으로).

- [ ] **Step 8: 통과 확인** → PASS

- [ ] **Step 9: 커밋**
```bash
git add frontend/src/lib/inputHash.ts frontend/src/lib/inputHash.test.ts frontend/src/types/profile.ts frontend/src/types/profile.test.ts
git commit -m "Add deterministic input hash and per-profile result cache (LRU)"
```

---

## Task 3: 북마클릿 닉네임 캡처 + payload 확장

**Files:**
- Modify: `frontend/src/lib/bookmarklet.ts`, `frontend/src/lib/bookmarklet.test.ts`

**Interfaces:**
- `buildBookmarklet(openId, appOrigin)` 시그니처 불변. 생성 소스가 4번째 호출 `GetUserProfileBasicInfo`를 포함하고, postMessage payload에 `open_id`와 `nickname`을 싣는다.

**Note:** blablalink 응답에서 `nickname`의 정확한 경로는 미확정(유저 실측으로 키 존재만 확인). 방어적으로 추출: `const nick=(basic&&(basic.nickname||basic.nick_name))||''` 형태로 시도하고, 없으면 `''`(다운스트림에서 open_id로 fallback). 구현자는 이 방어 로직을 명시하고, 정확 경로는 열린 항목으로 둔다.

- [ ] **Step 1: 실패 테스트 추가** (`bookmarklet.test.ts`) — 기존 테스트는 생성 소스 문자열을 단언(`buildBookmarklet(...).source`류). 추가:
```ts
it('GetUserProfileBasicInfo를 호출하고 payload에 open_id·nickname을 싣는다', () => {
  const src = decodeURIComponent(buildBookmarklet('123456', 'https://app.example').slice('javascript:'.length))
  expect(src).toContain('GetUserProfileBasicInfo')
  expect(src).toContain('open_id:')
  expect(src).toContain('nickname:')
})
```
(기존 `bookmarklet.test.ts`의 단언 스타일에 맞춰 조정.)

- [ ] **Step 2: 실패 확인** → FAIL

- [ ] **Step 3: `bookmarklet.ts` 수정** — `call('GetUserProfileBasicInfo',{...base})` 추가, 방어적 nickname 추출, `payload={open_id:'${openId}',nickname:nick,owned,character_details,recycle_room_researches}`. transient-activation 제약(첫 await 전 window.open/리스너 등록)은 유지.

- [ ] **Step 4: 통과 확인** → Run `cd frontend && npx vitest run src/lib/bookmarklet.test.ts` → PASS

- [ ] **Step 5: 커밋**
```bash
git add frontend/src/lib/bookmarklet.ts frontend/src/lib/bookmarklet.test.ts
git commit -m "Capture account nickname + open_id in sync bookmarklet payload"
```

---

## Task 4: sync import → 프로필 upsert 배선 (백엔드로 식별자 미전송)

**Files:**
- Modify: `frontend/src/api/assembleRoster.ts`, `frontend/src/api/assembleRoster.test.ts`
- Modify: `frontend/src/hooks/useBookmarkletImport.ts`(+test)
- Modify: `frontend/src/components/SyncRosterPanel.tsx`(+test)

**Interfaces:**
- `RawRosterPayload`는 이제 `open_id?`/`nickname?`를 **선택 metadata**로 포함하되, `assembleRoster`는 **roster 필드만** 백엔드에 보낸다(metadata strip).
- `useBookmarkletImport(onRoster)`의 `onRoster`는 `(args: { openId: string; nickname: string; roster: NikkeDraft[] }) => void`로 바뀐다(assembled roster + 분리한 metadata).
- `SyncRosterPanel`의 `onImport`는 `(args: { openId: string; nickname: string; roster: NikkeDraft[] }) => void`.

- [ ] **Step 1: `assembleRoster` metadata-strip 실패 테스트** — payload에 `open_id`/`nickname`이 있어도 fetch 본문에는 포함되지 않음(fetch mock의 body 검사).

- [ ] **Step 2: 실패 확인** → FAIL

- [ ] **Step 3: `assembleRoster.ts` 수정** — `const { open_id, nickname, ...rosterPayload } = payload`로 분리 후 `rosterPayload`만 body로. `RawRosterPayload`에 `open_id?`/`nickname?` 추가.

- [ ] **Step 4: 통과 확인** → PASS

- [ ] **Step 5: `useBookmarkletImport` 실패 테스트** — 메시지 payload에서 `open_id`/`nickname`을 뽑아 assembled roster와 함께 `onRoster({openId,nickname,roster})`로 넘김. `isRawRosterPayload` 최소검증은 유지(owned/character_details/recycle_room_researches 배열).

- [ ] **Step 6: 실패 확인** → FAIL

- [ ] **Step 7: `useBookmarkletImport.ts` 수정** — `handle`에서 `const assembled = await assembleRoster(payload)` 후 `onRosterRef.current({ openId: String(payload.open_id ?? ''), nickname: String(payload.nickname ?? ''), roster: assembled as NikkeDraft[] })`. (assembleRoster 반환 타입 정합은 기존 로컬 캐스팅 관행에 맞춤.)

- [ ] **Step 8: 통과 확인** → PASS

- [ ] **Step 9: `SyncRosterPanel` 배선 수정 + 테스트** — `onImport` 타입 변경 반영, summary 표시는 `roster.length`로. 기존 collector summary("N added/updated")는 upsert 모델에선 "N units synced"로 단순화(구현자 판단, 테스트 갱신).

- [ ] **Step 10: 통과 확인** → PASS

- [ ] **Step 11: 커밋**
```bash
git add frontend/src/api/assembleRoster.* frontend/src/hooks/useBookmarkletImport.* frontend/src/components/SyncRosterPanel.*
git commit -m "Wire sync import to profile upsert; keep identifiers off backend calls"
```

---

## Task 5: exia + 수동입력 경로 제거 (collector 경로 보존)

**Files:**
- Delete: `frontend/src/components/ImportRosterButton.tsx`(+`.test.tsx`)
- Delete: `frontend/src/hooks/useRoster.ts`(+`.test.ts`)
- Modify: `frontend/src/lib/exiaImport.ts`(+test) — `parseExiaExport` 및 exia 전용 export 제거, **`deriveSlug`(및 collector가 쓰는 심볼) 유지**
- Modify: `frontend/src/types/nikkeDraft.ts`(+test) — `mergeRosterDrafts` 제거(`mergeCollectorDrafts` 유지)
- Delete(검증 후 미사용분만): `OverloadOptionsField.tsx`·`SkillLevelsField.tsx`·`fields/NumberField.tsx`·`fields/TextField.tsx`

**주의:** `rosterImport.ts`(collector, 유지)가 `deriveSlug`를 import한다 — `exiaImport.ts`를 통째로 지우면 collector가 깨진다. `parseExiaExport`와 exia-전용 헬퍼만 제거하고 공유 심볼은 남긴다.

- [ ] **Step 1: 사용처 확인** — `cd frontend && npx tsc -b` 전에 grep으로 각 삭제 후보의 import 지점 확인:
Run: `grep -rn "OverloadOptionsField\|SkillLevelsField\|fields/NumberField\|fields/TextField\|ImportRosterButton\|useRoster\|mergeRosterDrafts\|parseExiaExport" frontend/src`
Expected: App.tsx/NikkeCard 외 참조가 없어야 삭제 가능. (App/NikkeCard는 Task 6에서 정리.)

- [ ] **Step 2: exia/수동 경로 삭제** — 위 파일 제거 + `exiaImport.ts`/`nikkeDraft.ts`에서 해당 export만 제거. 관련 테스트 파일도 제거/갱신.

- [ ] **Step 3: collector 경로 회귀 없음 확인**
Run: `cd frontend && npx vitest run src/lib/rosterImport.test.ts src/lib/resourceIdSlugMap.test.ts src/lib/exiaImport.test.ts`
Expected: PASS (남은 collector·shared 심볼 테스트만).

- [ ] **Step 4: 타입체크** — `cd frontend && npx tsc -b` — App.tsx/NikkeCard의 잔여 참조는 Task 6에서 고칠 것이므로, 이 Task는 App/NikkeCard를 아직 안 건드렸다면 여기서 tsc가 그 두 곳만 에러낼 수 있다. **Task 5는 Task 6과 한 커밋 경계로 묶어도 되지만, 순서상 5→6이며 5 종료 시 tsc가 App/NikkeCard 에러를 낼 수 있음을 감안**한다(구현자는 5의 삭제와 6의 App 정리를 연속 수행하고 6 종료 시 tsc/테스트 그린을 만든다). 리뷰 경계를 위해 5는 "삭제 + 삭제 대상 자체 테스트 그린"까지, App 그린은 6에서.

- [ ] **Step 5: 커밋**
```bash
git add -A
git commit -m "Remove exia import and manual-entry paths (keep shared collector helpers)"
```

---

## Task 6: App 재배선 — 프로필 스토어 + ProfileSwitcher + 읽기전용 로스터

**Files:**
- Create: `frontend/src/components/ProfileSwitcher.tsx`(+`.test.tsx`)
- Modify: `frontend/src/App.tsx`(+`App.test.tsx`)
- Modify: `frontend/src/components/NikkeCard.tsx`(+test) — 읽기전용

**Interfaces:**
- `ProfileSwitcher` props: `{ profiles: Profile[]; activeOpenId: string | null; onSwitch: (openId: string) => void; onDelete: (openId: string) => void }`. 닉네임 드롭다운 + 활성 프로필 삭제 버튼(확인).
- `App`은 `useProfiles()`로 상태·액션을 얻고, `activeProfile(state)`의 `roster`(NikkeDraft[])를 `getValidRoster`로 검증해 `RecommendPanel`에 전달. sync는 `upsert`로 배선.

- [ ] **Step 1: `ProfileSwitcher` 실패 테스트** — 프로필 목록 렌더, 선택 변경 시 `onSwitch(openId)`, 삭제 버튼 클릭 시 확인 후 `onDelete(openId)`. 프로필 0개면 아무것도 안 그리거나 빈 상태 메시지.

- [ ] **Step 2: 실패 확인** → FAIL

- [ ] **Step 3: `ProfileSwitcher.tsx` 구현**

- [ ] **Step 4: 통과 확인** → PASS

- [ ] **Step 5: `NikkeCard` 읽기전용 전환 테스트** — 편집 입력/삭제 버튼 없이 slug·주요 스탯·InvestmentBadge를 표시. `onChange`/`onRemove` prop 제거(또는 무시). 기존 편집 테스트는 표시 테스트로 대체.

- [ ] **Step 6: 실패 확인** → FAIL

- [ ] **Step 7: `NikkeCard.tsx` 구현** — 읽기전용 표시. 편집 필드 컴포넌트 의존 제거(Task 5에서 삭제한 것과 정합).

- [ ] **Step 8: 통과 확인** → PASS

- [ ] **Step 9: `App.tsx` 재배선 + `App.test.tsx` 갱신**
  - `useRoster` → `useProfiles`. `ImportRosterButton` 제거.
  - 헤더 아래 `ProfileSwitcher` 렌더.
  - 활성 프로필 없으면 "blablalink에서 sync로 시작하세요" 빈 상태 + `SyncRosterPanel`만.
  - 활성 프로필 있으면 읽기전용 로스터(NikkeCard 목록) + `RecommendPanel`.
  - `SyncRosterPanel onImport={(a)=>upsert(a)}`.
  - App.test: 최소 (a) 활성 프로필 없을 때 sync 안내, (b) upsert 후 로스터·RecommendPanel 표시, (c) 두 프로필 전환 시 로스터가 바뀜(격리) 스모크.

- [ ] **Step 10: 전체 그린 확인**
Run: `cd frontend && npx tsc -b && npm run test`
Expected: PASS, 타입 클린.

- [ ] **Step 11: 커밋**
```bash
git add -A
git commit -m "Rewire App to profile store: ProfileSwitcher + read-only synced roster"
```

---

## Task 7: RecommendPanel 결과 영속 + 복원

**Files:**
- Modify: `frontend/src/components/RecommendPanel.tsx`(+`RecommendPanel.test.tsx`)
- (필요 시) Modify: `frontend/src/App.tsx` — 활성 프로필과 saveResult/복원 콜백을 RecommendPanel에 전달

**Interfaces:**
- `RecommendPanel` props 확장: `{ roster: UserNikkeState[]; activeOpenId: string | null; getCached: (hash: string) => StoredResult | null; onResult: (args: { hash: string; result: StoredResult; inputs: StoredInputs }) => void; restoreInputs: StoredInputs | null; restoreResult: StoredResult | null }`. (App이 `useProfiles`에서 활성 프로필의 `lastInputs`/`getResult(lastResultHash)`를 계산해 내려줌, 저장은 `saveResult` 액션 콜백.)
- raid/draft 모드만 캐시 대상(single은 스코프 밖 — README에 명시).

- [ ] **Step 1: 실패 테스트** (`RecommendPanel.test.tsx`)
  - (a) **복원:** `restoreInputs`(mode/numDecks/boss/draft) + `restoreResult`가 주어지면, 마운트 시 재요청 없이 결과가 렌더되고 boss/draft 입력이 복원된다.
  - (b) **저장:** raid/draft 제출 성공 시 `onResult({hash, result, inputs})`가 정확한 hash로 호출된다(mock client 성공 경로, `hashRecommendInputs`와 일치).
  - (c) **캐시 히트:** 동일 입력 재제출 시 `getCached(hash)`가 히트면 네트워크 호출 없이 즉시 결과 표시(mock client submit이 호출되지 않음).

- [ ] **Step 2: 실패 확인** → FAIL

- [ ] **Step 3: `RecommendPanel.tsx` 구현**
  - 마운트/`activeOpenId` 변경 시 `restoreInputs`로 `mode`/`numDecks`/`draft`(boss)를 세팅하고 `restoreResult`를 표시 상태로 로드(raidResultMode도 그에 맞게).
  - `handleSubmit`(raid/draft): 요청 전 `const hash=hashRecommendInputs(roster, boss, draftOrNull)`; `const cached=getCached(hash)`; 히트면 submit 생략하고 캐시 결과를 렌더 상태로 세팅; 미스면 기존대로 `raid.submit(...)`.
  - `raid.status==='success'`가 되면(해당 모드일 때) `onResult({hash, result: <raid 성공 payload>, inputs})` 호출로 저장. (성공 payload를 `StoredResult`로 매핑.)
  - single 모드는 변경 없음(캐시 미적용).

- [ ] **Step 4: 통과 확인** → Run RecommendPanel.test → PASS

- [ ] **Step 5: App 배선(필요 시) + 전체 그린**
Run: `cd frontend && npx tsc -b && npm run test`
Expected: PASS.

- [ ] **Step 6: 커밋**
```bash
git add -A
git commit -m "Persist and restore raid/draft recommendations per profile"
```

---

## Task 8: README 계약 갱신 + 최종 정리

**Files:**
- Modify: `frontend/README.md`

- [ ] **Step 1: README에 다계정/결과영속 섹션 추가**
  - 저장 모델(`nikke-profiles`), 프로필 = open_id, 격리 불변식.
  - sync가 nickname/open_id를 캡처하되 **백엔드로 안 보냄**.
  - 결과 영속(raid/draft만, inputHash 키, LRU 상한, 재오픈 복원), single 모드는 비대상.
  - exia/수동입력 제거됨을 명시(과거 "Current scope" 수동입력 문구 갱신/삭제).
  - 마이그레이션: legacy `nikke-roster` 폐기.

- [ ] **Step 2: 전체 스위트 그린 확인**
Run: `cd frontend && npx tsc -b && npm run test`
Expected: PASS.
Run(백엔드 무변경 회귀 확인): `cd backend && python -m pytest -q`
Expected: 기존과 동일 그린(이 기능은 백엔드 무변경).

- [ ] **Step 3: 커밋**
```bash
git add frontend/README.md
git commit -m "Document multi-account profiles + result persistence contract"
```

---

## Self-Review 메모 (계획 작성자)

- **Spec 커버리지:** 저장 모델(T1), 결과 영속·해시·복원(T2/T7), sync nickname 캡처(T3), upsert·식별자 미전송(T4), exia/수동 제거(T5), 프로필 UI·읽기전용 로스터(T6), 마이그레이션 폐기(T1), 프라이버시 규율(T4 + README T8) — 모두 태스크에 매핑됨.
- **타입 일관성:** `Profile`/`ProfilesState`/`StoredInputs`/`StoredResult`/`hashRecommendInputs`가 T1→T2→T7에서 동일 시그니처로 사용됨.
- **열린 항목(스펙과 동일):** `GetUserProfileBasicInfo`의 nickname 정확 경로(T3 방어적 추출 + fallback), `StoredResult`를 useRecommendRaid 성공 payload에 정확 매핑(T2/T7 구현 시 확정), 미사용 필드 컴포넌트 삭제 범위(T5 grep 확인).
- **경계 주의:** T5(삭제)→T6(App 그린)은 tsc 그린 시점이 T6 종료임 — SDD 리뷰 시 T5는 "삭제 + 자체 테스트 그린", 전역 tsc 그린은 T6에서로 리뷰어에게 명시할 것.
