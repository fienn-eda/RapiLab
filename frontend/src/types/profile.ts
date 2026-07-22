// One profile per blablalink account (keyed by open_id), holding that
// account's roster and cached recommend results. Different open_ids must
// never mix - that's the whole point of a profile store, since a single
// shared roster/result cache is what breaks multi-account use.

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
  nickname: string
  roster: NikkeDraft[]
  results: Record<string, StoredResult> // key = inputHash (see lib/inputHash.ts)
  lastResultHash: string | null
  lastInputs: StoredInputs | null
}

export interface ProfilesState {
  activeOpenId: string | null
  profiles: Record<string, Profile>
}

export const emptyProfilesState = (): ProfilesState => ({
  activeOpenId: null,
  profiles: {},
})

/**
 * Create or resync a profile for openId. A new openId is created and made
 * active. An existing openId has its nickname/roster refreshed; if the
 * roster actually changed, cached results are invalidated since they no
 * longer describe the current roster.
 */
export const upsertProfile = (
  state: ProfilesState,
  args: { openId: string; nickname: string; roster: NikkeDraft[] },
): ProfilesState => {
  const existing = state.profiles[args.openId]
  const rosterChanged =
    existing !== undefined &&
    JSON.stringify(existing.roster) !== JSON.stringify(args.roster)

  const profile: Profile = existing
    ? {
        ...existing,
        nickname: args.nickname,
        roster: args.roster,
        ...(rosterChanged
          ? { results: {}, lastResultHash: null, lastInputs: null }
          : {}),
      }
    : {
        openId: args.openId,
        nickname: args.nickname,
        roster: args.roster,
        results: {},
        lastResultHash: null,
        lastInputs: null,
      }

  return {
    activeOpenId: args.openId,
    profiles: { ...state.profiles, [args.openId]: profile },
  }
}

export const switchProfile = (
  state: ProfilesState,
  openId: string,
): ProfilesState => ({ ...state, activeOpenId: openId })

/** Deleting the active profile falls back to another remaining profile, or null. */
export const deleteProfile = (
  state: ProfilesState,
  openId: string,
): ProfilesState => {
  const { [openId]: _removed, ...remaining } = state.profiles
  const activeOpenId =
    state.activeOpenId === openId
      ? (Object.keys(remaining)[0] ?? null)
      : state.activeOpenId
  return { activeOpenId, profiles: remaining }
}

export const activeProfile = (state: ProfilesState): Profile | null =>
  state.activeOpenId === null ? null : (state.profiles[state.activeOpenId] ?? null)

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
  openId: string,
  args: { hash: string; result: StoredResult; inputs: StoredInputs },
): ProfilesState => {
  const profile = state.profiles[openId]
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
  return { ...state, profiles: { ...state.profiles, [openId]: updatedProfile } }
}

export const getResult = (profile: Profile, hash: string): StoredResult | null =>
  profile.results[hash] ?? null
