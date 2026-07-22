import { describe, it, expect } from 'vitest'
import {
  emptyProfilesState, upsertProfile, switchProfile, deleteProfile, activeProfile,
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
