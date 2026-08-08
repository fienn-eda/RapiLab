import { describe, it, expect } from 'vitest'
import { restorableResult } from './restorableResult'
import { hashRecommendInputs } from './inputHash'
import type { Profile, StoredInputs, StoredResult } from '../types/profile'
import type { UserNikkeState } from '../types/userNikkeState'
import type { BossProfile } from '../types/recommend'

const nikke = (slug: string): UserNikkeState => ({
  character_slug: slug,
  level: 400,
  hp: 1000,
  atk: 1000,
  def_: 1000,
  skill_levels: { skill1: 1, skill2: 1, burst: 1 },
  overload_options: [],
})

const boss: BossProfile = {
  element: null,
  core_hittable: false,
  pierce_hits_body_behind_core: false,
  enemy_def: 0,
  fight_duration: 180,
  part_destructible: false,
  core_diameter_px: null,
  effective_range_band: null,
  elemental_interrupt_required: false,
}

const ROSTER = [nikke('liter'), nikke('crown')]
const INPUTS: StoredInputs = { mode: 'raid', numDecks: 5, boss, draft: null }

/** 저장된 결과의 내용은 이 판단에 쓰이지 않는다 - 복원하느냐 마느냐만 가른다. */
const RESULT: StoredResult = {
  decks: [],
  combinedTotalDamage: 0,
  excludedSlugs: [],
  leftoverSlugs: [],
  withinDraft: null,
  baselineTotalDamage: null,
}

/** 엔진 버전 `engineVersion`에서 결과를 한 번 받아 저장해 둔 프로필. */
const profileSavedUnder = (engineVersion: string | null): Profile => {
  const hash = hashRecommendInputs(ROSTER, boss, null, INPUTS.numDecks, engineVersion)
  return {
    openId: 'A',
    area: 81,
    nickname: '본계',
    roster: [],
    results: { [hash]: RESULT },
    lastResultHash: hash,
    lastInputs: INPUTS,
    savedRuns: [],
  }
}

describe('restorableResult', () => {
  it('저장 당시와 같은 엔진 버전이면 복원한다', () => {
    expect(restorableResult(profileSavedUnder('engine-1'), ROSTER, 'engine-1')).toBe(RESULT)
  })

  it('엔진이 바뀌었으면 복원하지 않는다', () => {
    // 옛 엔진이 낸 결과는 그 시절의 스키마다. RaidDeck에 필드가 하나 늘기만
    // 해도(hold_burst_slugs가 그랬다) 복원된 옛 결과에는 그 필드가 없어서
    // 그리는 쪽이 undefined를 읽고 터진다 - 그리고 앱 전체가 언마운트된다.
    expect(restorableResult(profileSavedUnder('engine-1'), ROSTER, 'engine-2')).toBeNull()
  })

  it('로스터가 바뀌었으면 복원하지 않는다', () => {
    expect(restorableResult(profileSavedUnder('engine-1'), [nikke('liter')], 'engine-1')).toBeNull()
  })

  it('제출한 적이 없는 프로필은 복원할 것이 없다', () => {
    const fresh: Profile = {
      ...profileSavedUnder('engine-1'),
      results: {},
      lastResultHash: null,
      lastInputs: null,
    }
    expect(restorableResult(fresh, ROSTER, 'engine-1')).toBeNull()
  })
})
