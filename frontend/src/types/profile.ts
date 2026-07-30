// One profile per (open_id, area) pair - a blablalink account holds a
// separate roster on each game server, so the account alone isn't specific
// enough to key a profile. Different (open_id, area) pairs must never mix -
// that's the whole point of a profile store, since a single shared
// roster/result cache is what breaks multi-account (or multi-server) use.

import type { NikkeDraft } from './nikkeDraft'
import type { BossProfile, DraftAllocation, RaidDeck } from './recommend'
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
 * made active. An existing pair has its nickname/roster refreshed; if the
 * roster actually changed, cached results are invalidated since they no
 * longer describe the current roster.
 *
 * A resync that arrives with a BLANK nickname keeps the stored one. The
 * bookmarklet reads the nickname from a separate blablalink call than the
 * roster (`GetUserProfileBasicInfo`) and swallows that call's failure, so an
 * empty string means "this sync could not read it", never "the account is now
 * nameless" - and overwriting on that used to silently demote the account
 * dropdown back to the raw open_id, with no way to get the name back short of a
 * luckier resync.
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
