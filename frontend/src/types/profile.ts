// One profile per (open_id, area) pair - a blablalink account holds a
// separate roster on each game server, so the account alone isn't specific
// enough to key a profile. Different (open_id, area) pairs must never mix -
// that's the whole point of a profile store, since a single shared
// roster/result cache is what breaks multi-account (or multi-server) use.

import type { NikkeDraft } from './nikkeDraft'
import type { BossProfile, DeckRecommendation, DraftAllocation, RaidDeck } from './recommend'
import type { Draft } from './draft'

/** What the player submitted for a POST /api/recommend-raid call - enough to
 * reproduce it (restore the form) or recompute its inputHash. */
export interface StoredInputs {
  mode: 'raid' | 'draft'
  numDecks: number
  boss: BossProfile
  draft: Draft | null
}

/** The useRecommendRaid success payload fields, cached verbatim so a repeat
 * request (same inputHash) can be restored without calling the backend
 * again - the engine is deterministic, so this is exact, not stale. */
export interface StoredResult {
  decks: RaidDeck[]
  combinedTotalDamage: number
  excludedSlugs: string[]
  leftoverSlugs: string[]
  withinDraft: DraftAllocation | null
  baselineTotalDamage: number | null
  /** 없을 수 있다 — 이 필드가 생기기 전에 저장된 결과. 없으면 경고하지 않는다. */
  swapConverged?: boolean
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

export interface Profile {
  openId: string
  /** 이 로스터가 속한 게임 서버(blablalink API의 `nikke_area_id`). 한 open_id가
   * 여러 서버에 각각 로스터를 가질 수 있어서, 프로필을 특정하려면 둘 다 필요하다. */
  area: number
  nickname: string
  roster: NikkeDraft[]
  results: Record<string, StoredResult> // key = inputHash (see lib/inputHash.ts)
  lastResultHash: string | null
  lastInputs: StoredInputs | null
  savedRuns: SavedRun[]
  /** 추천에 쓰지 않기로 한 니케들. 계정마다 하나이고(니케 풀 탭에서 정한다)
   * 솔로·유니온이 함께 읽는다. */
  excludedSlugs: string[]
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

/**
 * Create or resync a profile for (openId, area). A new pair is created and
 * made active. An existing pair has its roster refreshed; if the roster
 * actually changed, cached results are invalidated since they no longer
 * describe the current roster.
 *
 * The stored name is a LABEL the user owns, not a mirror of the in-game
 * nickname. A sync seeds it only while it is empty; once there is a name,
 * nothing but an explicit rename replaces it. blablalink rejects the nickname
 * call (`GetUserProfileBasicInfo`, code 1300015) whenever the ShiftyPad page
 * has just fetched it - which is exactly when a first sync happens - so the
 * name that does arrive is a lucky bonus, and the one the user typed is the
 * one worth keeping (2026-08-09 measurement).
 */
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
        nickname: existing.nickname || args.nickname,
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
        savedRuns: [],
        excludedSlugs: [],
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

/** Deleting the active profile falls back to another remaining profile, or null. */
export const deleteProfile = (state: ProfilesState, key: string): ProfilesState => {
  const { [key]: _removed, ...remaining } = state.profiles
  const activeKey =
    state.activeKey === key ? (Object.keys(remaining)[0] ?? null) : state.activeKey
  return { activeKey, profiles: remaining }
}

export const activeProfile = (state: ProfilesState): Profile | null =>
  state.activeKey === null ? null : (state.profiles[state.activeKey] ?? null)

/** Cached results per profile beyond this are evicted oldest-first - a
 * profile's roster and boss/draft choices only vary so much, so this is
 * plenty to avoid recomputation without growing localStorage unbounded. */
export const RESULTS_CAP = 20

/**
 * Cache one recommend-raid result under its inputHash. Re-saving an existing
 * hash refreshes it to newest (LRU): entries beyond RESULTS_CAP are evicted
 * oldest-first, using Record insertion order as the recency signal.
 */
export const saveResult = (
  state: ProfilesState,
  key: string,
  args: { hash: string; result: StoredResult; inputs: StoredInputs },
): ProfilesState => {
  const profile = state.profiles[key]
  if (!profile) return state

  // Delete then reinsert so a re-saved hash moves to the end (newest) -
  // object key order is insertion order, which is what backs the LRU here.
  const { [args.hash]: _discard, ...withoutHash } = profile.results
  let results: Record<string, StoredResult> = { ...withoutHash, [args.hash]: args.result }

  const keys = Object.keys(results)
  if (keys.length > RESULTS_CAP) {
    const { [keys[0]]: _oldest, ...trimmed } = results
    results = trimmed
  }

  const updatedProfile: Profile = {
    ...profile,
    results,
    lastResultHash: args.hash,
    lastInputs: args.inputs,
  }
  return { ...state, profiles: { ...state.profiles, [key]: updatedProfile } }
}

export const getResult = (profile: Profile, hash: string): StoredResult | null =>
  profile.results[hash] ?? null

/** 프로필 하나가 보관할 수 있는 결과 수. 넘으면 저장을 거절한다 - 캐시와 달리
 * 유저가 이름 붙여 남긴 것을 말없이 밀어내면 안 된다. */
export const SAVED_RUNS_CAP = 50

/** 같은 밀리초에 두 번 저장해도 부딪히지 않는 결정적 id. */
export const makeRunId = (savedAt: number, existing: SavedRun[]): string =>
  `${savedAt}-${existing.filter((run) => run.savedAt === savedAt).length}`

/** 상한을 넘으면 상태를 그대로 돌려준다 - 호출부는 참조 동일성으로 거절을 안다. */
export const saveRun = (state: ProfilesState, key: string, run: SavedRun): ProfilesState => {
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

/** 이 니케를 추천에서 뺄지 뒤집는다. 로스터에 없는 슬러그도 그대로 담는다 -
 * 동기화가 잠깐 실패해 로스터가 짧아졌다고 판단까지 잃을 이유는 없다. */
export const toggleExcluded = (state: ProfilesState, key: string, slug: string): ProfilesState => {
  const profile = state.profiles[key]
  if (!profile) return state

  const excludedSlugs = profile.excludedSlugs.includes(slug)
    ? profile.excludedSlugs.filter((s) => s !== slug)
    : [...profile.excludedSlugs, slug]
  return { ...state, profiles: { ...state.profiles, [key]: { ...profile, excludedSlugs } } }
}

/** 한 탭이 보여줄 보관물, 최신순. */
export const runsForTab = (profile: Profile, tab: SavedRun['tab']): SavedRun[] =>
  profile.savedRuns
    .filter((run) => run.tab === tab)
    .slice()
    .sort((a, b) => b.savedAt - a.savedAt)

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
