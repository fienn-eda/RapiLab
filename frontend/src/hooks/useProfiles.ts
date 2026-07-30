// Owns the multi-account profile store: one Profile per (open_id, area) pair,
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
  profileKey,
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
    area: number
    nickname: string
    roster: NikkeDraft[]
  }) => void
  switchProfile: (key: string) => void
  deleteProfile: (key: string) => void
  saveResult: (args: {
    key: string
    hash: string
    result: StoredResult
    inputs: StoredInputs
  }) => void
}

const STORAGE_KEY = 'nikke-profiles'
const LEGACY_ROSTER_KEY = 'nikke-roster'

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
  for (const profile of Object.values(profiles)) {
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
    return migrate(JSON.parse(raw))
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

  return {
    state,
    activeProfile: computeActiveProfile(state),
    upsertProfile: upsert,
    switchProfile: switchTo,
    deleteProfile: remove,
    saveResult: save,
  }
}
