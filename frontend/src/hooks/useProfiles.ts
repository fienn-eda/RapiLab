// Owns the multi-account profile store: one Profile per blablalink open_id,
// switched between and persisted to localStorage. This replaces the old
// single-roster 'nikke-roster' key, which mixed every account together.
//
// The app is not deployed yet, so a legacy 'nikke-roster' key is discarded on
// load rather than migrated - there is nothing depending on it surviving.

import { useCallback, useEffect, useState } from 'react'
import {
  activeProfile as computeActiveProfile,
  deleteProfile,
  emptyProfilesState,
  saveResult as pureSaveResult,
  switchProfile,
  upsertProfile,
  type Profile,
  type ProfilesState,
  type StoredInputs,
  type StoredResult,
} from '../types/profile'
import type { NikkeDraft } from '../types/nikkeDraft'

export interface Profiles {
  state: ProfilesState
  activeProfile: Profile | null
  upsertProfile: (args: {
    openId: string
    nickname: string
    roster: NikkeDraft[]
  }) => void
  switchProfile: (openId: string) => void
  deleteProfile: (openId: string) => void
  saveResult: (args: {
    openId: string
    hash: string
    result: StoredResult
    inputs: StoredInputs
  }) => void
}

const STORAGE_KEY = 'nikke-profiles'
const LEGACY_ROSTER_KEY = 'nikke-roster'

const readStoredProfiles = (): ProfilesState => {
  const raw = localStorage.getItem(STORAGE_KEY)
  if (raw === null) {
    // No profile store yet. A legacy single-roster key from before profiles
    // existed is discarded, not migrated - this app isn't deployed yet, so
    // there's nothing depending on it surviving.
    if (localStorage.getItem(LEGACY_ROSTER_KEY) !== null) {
      localStorage.removeItem(LEGACY_ROSTER_KEY)
    }
    return emptyProfilesState()
  }
  try {
    return JSON.parse(raw) as ProfilesState
  } catch {
    // Unparseable means unrecoverable, but start usable rather than dead -
    // never let a bad key keep the form from opening.
    console.warn(`Discarding unreadable stored profiles (${STORAGE_KEY}).`)
    return emptyProfilesState()
  }
}

export const useProfiles = (): Profiles => {
  const [state, setState] = useState<ProfilesState>(() => readStoredProfiles())

  useEffect(() => {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(state))
  }, [state])

  const upsert = useCallback(
    (args: { openId: string; nickname: string; roster: NikkeDraft[] }) => {
      setState((current) => upsertProfile(current, args))
    },
    [],
  )

  const switchTo = useCallback((openId: string) => {
    setState((current) => switchProfile(current, openId))
  }, [])

  const remove = useCallback((openId: string) => {
    setState((current) => deleteProfile(current, openId))
  }, [])

  const save = useCallback(
    (args: { openId: string; hash: string; result: StoredResult; inputs: StoredInputs }) => {
      setState((current) =>
        pureSaveResult(current, args.openId, {
          hash: args.hash,
          result: args.result,
          inputs: args.inputs,
        }),
      )
    },
    [],
  )

  return {
    state,
    activeProfile: computeActiveProfile(state),
    upsertProfile: upsert,
    switchProfile: switchTo,
    deleteProfile: remove,
    saveResult: save,
  }
}
