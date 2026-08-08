import { describe, it, expect } from 'vitest'
import {
  emptyProfilesState, upsertProfile, switchProfile, deleteProfile, activeProfile,
  saveResult, getResult, profileKey, RESULTS_CAP,
  saveRun, renameRun, deleteRun, runsForTab, makeRunId, SAVED_RUNS_CAP,
  type StoredResult, type StoredInputs, type SavedRun,
} from './profile'
import type { NikkeDraft } from './nikkeDraft'

const draft = (slug: string): NikkeDraft =>
  ({ id: slug, character_slug: slug, level: '400', hp: '1', atk: '1', def_: '1',
     actualHp: '', actualAtk: '', actualDef: '',
     skill_levels: { skill1: '1', skill2: '1', burst: '1' }, overload_options: [] })

describe('upsertProfile', () => {
  it('새 open_id는 프로필을 만들고 활성으로 만든다', () => {
    const s = upsertProfile(emptyProfilesState(), { openId: 'A', area: 81, nickname: '본계', roster: [draft('liter')] })
    expect(s.activeKey).toBe('A:81')
    expect(s.profiles['A:81'].nickname).toBe('본계')
    expect(s.profiles['A:81'].roster.map((d) => d.character_slug)).toEqual(['liter'])
  })

  it('다른 open_id는 절대 병합되지 않는다(격리)', () => {
    let s = upsertProfile(emptyProfilesState(), { openId: 'A', area: 81, nickname: '본계', roster: [draft('liter')] })
    s = upsertProfile(s, { openId: 'B', area: 81, nickname: '부계', roster: [draft('crown')] })
    expect(Object.keys(s.profiles).sort()).toEqual(['A:81', 'B:81'])
    expect(s.profiles['A:81'].roster.map((d) => d.character_slug)).toEqual(['liter'])
    expect(s.profiles['B:81'].roster.map((d) => d.character_slug)).toEqual(['crown'])
  })

  it('재sync가 빈 닉네임으로 와도 저장된 닉네임을 지우지 않는다', () => {
    // 북마클릿은 닉네임을 로스터와 다른 blablalink 호출(GetUserProfileBasicInfo)에서
    // 읽고 그 실패를 삼킨다. 그래서 빈 문자열은 "계정 이름이 없어졌다"가 아니라
    // "이번 싱크가 못 읽었다"는 뜻이고, 덮어쓰면 Account 드롭다운이 원래 uid로
    // 되돌아간 뒤 다음 싱크가 운 좋기만 기다려야 한다.
    let s = upsertProfile(emptyProfilesState(), { openId: 'A', area: 81, nickname: '본계', roster: [draft('liter')] })
    s = upsertProfile(s, { openId: 'A', area: 81, nickname: '', roster: [draft('liter'), draft('crown')] })
    expect(s.profiles['A:81'].nickname).toBe('본계')
    // 로스터는 정상적으로 갱신된다 - 닉네임만 보존하는 것이다.
    expect(s.profiles['A:81'].roster.map((d) => d.character_slug)).toEqual(['liter', 'crown'])
  })

  it('닉네임이 실제로 바뀌면 갱신한다', () => {
    let s = upsertProfile(emptyProfilesState(), { openId: 'A', area: 81, nickname: '본계', roster: [draft('liter')] })
    s = upsertProfile(s, { openId: 'A', area: 81, nickname: '개명', roster: [draft('liter')] })
    expect(s.profiles['A:81'].nickname).toBe('개명')
  })

  it('기존 open_id 재sync: 로스터가 바뀌면 results를 클리어한다', () => {
    let s = upsertProfile(emptyProfilesState(), { openId: 'A', area: 81, nickname: '본계', roster: [draft('liter')] })
    s = { ...s, profiles: { ...s.profiles, 'A:81': { ...s.profiles['A:81'], results: { h1: {} as never }, lastResultHash: 'h1' } } }
    s = upsertProfile(s, { openId: 'A', area: 81, nickname: '본계', roster: [draft('liter'), draft('crown')] })
    expect(s.profiles['A:81'].results).toEqual({})
    expect(s.profiles['A:81'].lastResultHash).toBeNull()
  })

  it('기존 open_id 재sync: 로스터가 byte-동일이면 results를 유지한다', () => {
    let s = upsertProfile(emptyProfilesState(), { openId: 'A', area: 81, nickname: '본계', roster: [draft('liter')] })
    s = { ...s, profiles: { ...s.profiles, 'A:81': { ...s.profiles['A:81'], results: { h1: {} as never }, lastResultHash: 'h1' } } }
    s = upsertProfile(s, { openId: 'A', area: 81, nickname: '본계2', roster: [draft('liter')] })
    expect(s.profiles['A:81'].results).toHaveProperty('h1')
    expect(s.profiles['A:81'].nickname).toBe('본계2')   // 닉네임은 갱신
  })
})

describe('switch/delete/active', () => {
  it('switchProfile은 활성만 바꾼다', () => {
    let s = upsertProfile(emptyProfilesState(), { openId: 'A', area: 81, nickname: 'a', roster: [] })
    s = upsertProfile(s, { openId: 'B', area: 81, nickname: 'b', roster: [] })
    s = switchProfile(s, 'A:81')
    expect(activeProfile(s)?.openId).toBe('A')
  })
  it('활성 프로필 삭제 시 남은 것으로 전환, 마지막이면 null', () => {
    let s = upsertProfile(emptyProfilesState(), { openId: 'A', area: 81, nickname: 'a', roster: [] })
    s = deleteProfile(s, 'A:81')
    expect(s.activeKey).toBeNull()
    expect(s.profiles).toEqual({})
  })
})

const result = (n: number): StoredResult => ({
  decks: [],
  combinedTotalDamage: n,
  excludedSlugs: [],
  leftoverSlugs: [],
  withinDraft: null,
  baselineTotalDamage: null,
})

const inputs: StoredInputs = {
  mode: 'raid',
  numDecks: 5,
  boss: { element: null, core_hittable: false, pierce_hits_body_behind_core: false, enemy_def: 0, fight_duration: 180, part_destructible: false, core_diameter_px: null, effective_range_band: null, elemental_interrupt_required: false },
  draft: null,
}

describe('saveResult / getResult', () => {
  const baseState = () =>
    upsertProfile(emptyProfilesState(), { openId: 'A', area: 81, nickname: '본계', roster: [] })

  it('저장 후 getResult로 조회되고 lastResultHash/lastInputs가 갱신된다', () => {
    let s = baseState()
    s = saveResult(s, 'A:81', { hash: 'h1', result: result(1), inputs })
    expect(getResult(s.profiles['A:81'], 'h1')).toEqual(result(1))
    expect(s.profiles['A:81'].lastResultHash).toBe('h1')
    expect(s.profiles['A:81'].lastInputs).toEqual(inputs)
  })

  it('없는 해시는 getResult가 null을 반환한다', () => {
    const s = baseState()
    expect(getResult(s.profiles['A:81'], 'missing')).toBeNull()
  })

  it('RESULTS_CAP을 초과하면 가장 오래 저장된 항목을 제거한다', () => {
    let s = baseState()
    for (let i = 0; i < RESULTS_CAP + 1; i++) {
      s = saveResult(s, 'A:81', { hash: `h${i}`, result: result(i), inputs })
    }
    expect(Object.keys(s.profiles['A:81'].results)).toHaveLength(RESULTS_CAP)
    expect(getResult(s.profiles['A:81'], 'h0')).toBeNull() // oldest evicted
    expect(getResult(s.profiles['A:81'], `h${RESULTS_CAP}`)).toEqual(result(RESULTS_CAP)) // newest kept
  })

  it('같은 해시로 재저장하면 최신 항목으로 재정렬된다(LRU)', () => {
    let s = baseState()
    s = saveResult(s, 'A:81', { hash: 'h0', result: result(0), inputs })
    s = saveResult(s, 'A:81', { hash: 'h1', result: result(1), inputs })
    s = saveResult(s, 'A:81', { hash: 'h0', result: result(99), inputs })
    expect(Object.keys(s.profiles['A:81'].results)).toEqual(['h1', 'h0'])
    expect(getResult(s.profiles['A:81'], 'h0')).toEqual(result(99))
  })
})

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

const boss = {
  element: 'Fire' as const,
  core_hittable: false,
  pierce_hits_body_behind_core: false,
  enemy_def: 31784,
  fight_duration: 180,
  part_destructible: false,
  core_diameter_px: null,
  effective_range_band: null,
  elemental_interrupt_required: false,
}

const soloRun = (overrides: Partial<SavedRun> = {}): SavedRun => ({
  id: '1000-0',
  name: '작열 · 전부 최적화 · 08-06',
  savedAt: 1000,
  tab: 'solo',
  view: {
    mode: 'raid',
    boss,
    numDecks: 5,
    decks: [],
    combinedTotalDamage: 42,
    excludedSlugs: [],
    leftoverSlugs: [],
  },
  ...overrides,
})

const unionRun = (overrides: Partial<SavedRun> = {}): SavedRun => ({
  ...soloRun(),
  tab: 'union',
  view: {
    numBattles: 3,
    bosses: [boss],
    draft: { decks: [] },
    decks: [],
    combinedTotalDamage: 0,
    excludedSlugs: [],
  },
  ...overrides,
})

const withProfile = () =>
  upsertProfile(emptyProfilesState(), {
    openId: 'A', area: 81, nickname: '본계', roster: [draft('liter')],
  })

describe('보관한 결과', () => {
  it('프로필에 남는다', () => {
    const s = saveRun(withProfile(), 'A:81', soloRun())
    expect(s.profiles['A:81'].savedRuns).toHaveLength(1)
  })

  // 캐시는 오래된 것을 조용히 밀어내지만, 유저가 이름 붙여 남긴 것을 그렇게
  // 다루면 안 된다.
  it('상한을 넘으면 밀어내는 대신 저장을 거절한다', () => {
    let s = withProfile()
    for (let i = 0; i < SAVED_RUNS_CAP; i++) {
      s = saveRun(s, 'A:81', soloRun({ id: `${i}`, name: `run ${i}` }))
    }
    const full = s

    s = saveRun(s, 'A:81', soloRun({ id: 'one-too-many', name: '거절될 것' }))

    expect(s).toBe(full)
    expect(s.profiles['A:81'].savedRuns.map((r) => r.name)).not.toContain('거절될 것')
  })

  // 보관물은 "지금 로스터에 대한 답"이 아니라 "그때 이런 답이 나왔다"는 기록이다.
  it('로스터 재동기화에도 살아남는다 - 결과 캐시와 다른 점이다', () => {
    let s = saveRun(withProfile(), 'A:81', soloRun())
    s = saveResult(s, 'A:81', {
      hash: 'h',
      result: { decks: [], combinedTotalDamage: 1, excludedSlugs: [], leftoverSlugs: [], withinDraft: null, baselineTotalDamage: null },
      inputs: { mode: 'raid', numDecks: 5, boss, draft: null },
    })

    s = upsertProfile(s, {
      openId: 'A', area: 81, nickname: '본계', roster: [draft('liter'), draft('crown')],
    })

    expect(s.profiles['A:81'].savedRuns).toHaveLength(1)
    expect(s.profiles['A:81'].results).toEqual({})
  })

  it('id로 이름을 바꾸고 지운다', () => {
    let s = saveRun(withProfile(), 'A:81', soloRun({ id: 'x' }))

    s = renameRun(s, 'A:81', 'x', '새 이름')
    expect(s.profiles['A:81'].savedRuns[0].name).toBe('새 이름')

    s = deleteRun(s, 'A:81', 'x')
    expect(s.profiles['A:81'].savedRuns).toHaveLength(0)
  })

  it('두 탭의 보관물은 서로 섞이지 않는다', () => {
    let s = saveRun(withProfile(), 'A:81', soloRun({ id: 's' }))
    s = saveRun(s, 'A:81', unionRun({ id: 'u' }))

    const profile = s.profiles['A:81']
    expect(runsForTab(profile, 'solo').map((r) => r.id)).toEqual(['s'])
    expect(runsForTab(profile, 'union').map((r) => r.id)).toEqual(['u'])
  })

  it('최신 것을 먼저 보여준다', () => {
    let s = saveRun(withProfile(), 'A:81', soloRun({ id: 'old', savedAt: 1 }))
    s = saveRun(s, 'A:81', soloRun({ id: 'new', savedAt: 2 }))

    expect(runsForTab(s.profiles['A:81'], 'solo').map((r) => r.id)).toEqual(['new', 'old'])
  })
})

describe('makeRunId', () => {
  it('그 시각의 첫 저장은 -0이다', () => {
    expect(makeRunId(1000, [])).toBe('1000-0')
  })

  it('같은 밀리초에 이미 있으면 다음 번호로 넘어간다', () => {
    expect(makeRunId(1000, [soloRun({ id: '1000-0', savedAt: 1000 })])).toBe('1000-1')
  })
})
