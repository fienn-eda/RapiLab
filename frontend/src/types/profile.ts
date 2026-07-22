// One profile per blablalink account (keyed by open_id), holding that
// account's roster and cached recommend results. Different open_ids must
// never mix - that's the whole point of a profile store, since a single
// shared roster/result cache is what breaks multi-account use.

import type { NikkeDraft } from './nikkeDraft'

// StoredResult/StoredInputs are defined in Task 2; unknown here is a
// deliberate placeholder, not a modeling choice.
export interface Profile {
  openId: string
  nickname: string
  roster: NikkeDraft[]
  results: Record<string, unknown> // key = inputHash (Task 2)
  lastResultHash: string | null
  lastInputs: unknown | null // Task 2 type
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
