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
  saveRun as pureSaveRun,
  renameRun as pureRenameRun,
  deleteRun as pureDeleteRun,
  switchProfile,
  upsertProfile,
  type Profile,
  type ProfilesState,
  type SavedRun,
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
  /** 보관 상한에 걸려 거절됐으면 false. */
  saveRun: (args: { key: string; run: SavedRun }) => boolean
  renameRun: (args: { key: string; id: string; name: string }) => void
  deleteRun: (args: { key: string; id: string }) => void
}

const STORAGE_KEY = 'nikke-profiles'
const LEGACY_ROSTER_KEY = 'nikke-roster'

/** 복합 키가 생기기 전의 저장소는 open_id만으로 프로필을 키잡고 `activeOpenId`를
 * 들고 있었다. 그때 동기화된 데이터는 전부 area 81로 조회된 것이라, 81을 채워
 * 넣으면 정확하다. 멱등이다 - 이미 새 모양인 항목은 손대지 않는다.
 *
 * 이 판단은 스토어 전체가 아니라 프로필 한 항목씩 내린다: 이 함수는
 * 브라우저에 남은 실제 유저 데이터에서 돈다는 점에서 실수가 복구 불가능하다.
 * 스토어 전체를 한 번에 "신 스키마"로 단정하고 통째로 통과시키면, 그 안에
 * area 없는 bare-key 항목이 하나라도 섞여 있을 때 그 항목만 마이그레이션을
 * 건너뛰어 area 없는 프로필로 남는다. */
const migrate = (raw: unknown): ProfilesState => {
  const state = raw as Partial<ProfilesState> & {
    activeOpenId?: string | null
    profiles?: Record<string, Profile & { area?: number; savedRuns?: SavedRun[] }>
  }
  const profiles = state.profiles ?? {}

  const migrated: Record<string, Profile> = {}
  for (const profile of Object.values(profiles)) {
    const area = profile.area ?? 81
    migrated[profileKey(profile.openId, area)] = {
      ...profile,
      area,
      // 보관 목록이 생기기 전에 저장된 프로필은 이 필드가 없다. 여기서 한 번
      // 채우면 읽는 쪽마다 `?? []`를 흩뿌리지 않아도 된다.
      savedRuns: profile.savedRuns ?? [],
    }
  }

  // activeKey가 이미 복합 키를 가리키면(신 스키마) 그대로 쓴다. 그렇지 않고
  // 구 스키마의 activeOpenId(bare open_id)가 있으면, 그 open_id의 원본
  // 프로필에서 area를 읽어 같은 방식으로 복합 키를 다시 계산한다.
  const legacyActive = state.activeOpenId ?? null
  const activeOpenIdProfile = legacyActive === null ? undefined : profiles[legacyActive]
  const activeKey =
    activeOpenIdProfile !== undefined
      ? profileKey(activeOpenIdProfile.openId, activeOpenIdProfile.area ?? 81)
      : (state.activeKey ?? null)

  return { activeKey, profiles: migrated }
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

  /** 상한에 걸려 거절됐는지를 돌려준다 - 저장이 조용히 안 되는 화면을 만들지
   * 않기 위해서다. 거절은 순수 함수가 상태를 그대로 돌려주는 것으로 나타난다. */
  const keepRun = useCallback((args: { key: string; run: SavedRun }): boolean => {
    let accepted = false
    setState((current) => {
      const next = pureSaveRun(current, args.key, args.run)
      accepted = next !== current
      return next
    })
    return accepted
  }, [])

  const rename = useCallback((args: { key: string; id: string; name: string }) => {
    setState((current) => pureRenameRun(current, args.key, args.id, args.name))
  }, [])

  const removeRun = useCallback((args: { key: string; id: string }) => {
    setState((current) => pureDeleteRun(current, args.key, args.id))
  }, [])

  return {
    state,
    activeProfile: computeActiveProfile(state),
    upsertProfile: upsert,
    switchProfile: switchTo,
    deleteProfile: remove,
    saveResult: save,
    saveRun: keepRun,
    renameRun: rename,
    deleteRun: removeRun,
  }
}
