import { describe, it, expect } from 'vitest'
import {
  emptyProfilesState, upsertProfile, switchProfile, deleteProfile, activeProfile,
  saveResult, getResult, RESULTS_CAP,
  type StoredResult, type StoredInputs,
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

  it('재sync가 빈 닉네임으로 와도 저장된 닉네임을 지우지 않는다', () => {
    // 북마클릿은 닉네임을 로스터와 다른 blablalink 호출(GetUserProfileBasicInfo)에서
    // 읽고 그 실패를 삼킨다. 그래서 빈 문자열은 "계정 이름이 없어졌다"가 아니라
    // "이번 싱크가 못 읽었다"는 뜻이고, 덮어쓰면 Account 드롭다운이 원래 uid로
    // 되돌아간 뒤 다음 싱크가 운 좋기만 기다려야 한다.
    let s = upsertProfile(emptyProfilesState(), { openId: 'A', nickname: '본계', roster: [draft('liter')] })
    s = upsertProfile(s, { openId: 'A', nickname: '', roster: [draft('liter'), draft('crown')] })
    expect(s.profiles.A.nickname).toBe('본계')
    // 로스터는 정상적으로 갱신된다 - 닉네임만 보존하는 것이다.
    expect(s.profiles.A.roster.map((d) => d.character_slug)).toEqual(['liter', 'crown'])
  })

  it('닉네임이 실제로 바뀌면 갱신한다', () => {
    let s = upsertProfile(emptyProfilesState(), { openId: 'A', nickname: '본계', roster: [draft('liter')] })
    s = upsertProfile(s, { openId: 'A', nickname: '개명', roster: [draft('liter')] })
    expect(s.profiles.A.nickname).toBe('개명')
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
  boss: { element: null, core_hittable: false, enemy_def: 0, fight_duration: 180, part_destructible: false },
  draft: null,
}

describe('saveResult / getResult', () => {
  const baseState = () =>
    upsertProfile(emptyProfilesState(), { openId: 'A', nickname: '본계', roster: [] })

  it('저장 후 getResult로 조회되고 lastResultHash/lastInputs가 갱신된다', () => {
    let s = baseState()
    s = saveResult(s, 'A', { hash: 'h1', result: result(1), inputs })
    expect(getResult(s.profiles.A, 'h1')).toEqual(result(1))
    expect(s.profiles.A.lastResultHash).toBe('h1')
    expect(s.profiles.A.lastInputs).toEqual(inputs)
  })

  it('없는 해시는 getResult가 null을 반환한다', () => {
    const s = baseState()
    expect(getResult(s.profiles.A, 'missing')).toBeNull()
  })

  it('RESULTS_CAP을 초과하면 가장 오래 저장된 항목을 제거한다', () => {
    let s = baseState()
    for (let i = 0; i < RESULTS_CAP + 1; i++) {
      s = saveResult(s, 'A', { hash: `h${i}`, result: result(i), inputs })
    }
    expect(Object.keys(s.profiles.A.results)).toHaveLength(RESULTS_CAP)
    expect(getResult(s.profiles.A, 'h0')).toBeNull() // oldest evicted
    expect(getResult(s.profiles.A, `h${RESULTS_CAP}`)).toEqual(result(RESULTS_CAP)) // newest kept
  })

  it('같은 해시로 재저장하면 최신 항목으로 재정렬된다(LRU)', () => {
    let s = baseState()
    s = saveResult(s, 'A', { hash: 'h0', result: result(0), inputs })
    s = saveResult(s, 'A', { hash: 'h1', result: result(1), inputs })
    s = saveResult(s, 'A', { hash: 'h0', result: result(99), inputs })
    expect(Object.keys(s.profiles.A.results)).toEqual(['h1', 'h0'])
    expect(getResult(s.profiles.A, 'h0')).toEqual(result(99))
  })
})
