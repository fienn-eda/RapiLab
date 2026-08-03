import { describe, it, expect } from 'vitest'
import { hashRecommendInputs } from './inputHash'
import type { UserNikkeState } from '../types/userNikkeState'
import type { BossProfile } from '../types/recommend'
import type { Draft } from '../types/draft'

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
  effective_range_band: null,
}

describe('hashRecommendInputs', () => {
  it('동일 입력은 동일 해시를 낸다', () => {
    const r = [nikke('liter'), nikke('crown')]
    expect(hashRecommendInputs(r, boss, null, 5, null)).toBe(
      hashRecommendInputs(r, boss, null, 5, null),
    )
  })

  it('로스터 순서가 달라도 같은 해시(정규화)', () => {
    const a = [nikke('liter'), nikke('crown')]
    const b = [nikke('crown'), nikke('liter')]
    expect(hashRecommendInputs(a, boss, null, 5, null)).toBe(
      hashRecommendInputs(b, boss, null, 5, null),
    )
  })

  it('boss 한 필드만 바뀌어도 해시가 다르다', () => {
    const r = [nikke('liter')]
    expect(hashRecommendInputs(r, boss, null, 5, null)).not.toBe(
      hashRecommendInputs(r, { ...boss, enemy_def: 999 }, null, 5, null),
    )
  })

  it('roster 투자 데이터(레벨 등) 한 필드만 바뀌어도 해시가 다르다', () => {
    const r = [nikke('liter')]
    const r2 = [{ ...nikke('liter'), level: 401 }]
    expect(hashRecommendInputs(r, boss, null, 5, null)).not.toBe(
      hashRecommendInputs(r2, boss, null, 5, null),
    )
  })

  it('draft=null(zero-base)과 빈 decks 배열을 구분한다', () => {
    const r = [nikke('liter')]
    const emptyDraft: Draft = { decks: [] }
    expect(hashRecommendInputs(r, boss, null, 5, null)).not.toBe(
      hashRecommendInputs(r, boss, emptyDraft, 5, null),
    )
  })

  it('draft가 다르면 해시가 다르다', () => {
    const r = [nikke('liter'), nikke('crown')]
    const draftA: Draft = { decks: [[{ slug: 'liter', locked: true }]] }
    const draftB: Draft = { decks: [[{ slug: 'crown', locked: true }]] }
    expect(hashRecommendInputs(r, boss, draftA, 5, null)).not.toBe(
      hashRecommendInputs(r, boss, draftB, 5, null),
    )
  })

  it('덱 내 시트 순서가 달라도 같은 해시(정규화)', () => {
    const r = [nikke('liter'), nikke('crown')]
    const draftA: Draft = { decks: [[{ slug: 'liter', locked: false }, { slug: 'crown', locked: true }]] }
    const draftB: Draft = { decks: [[{ slug: 'crown', locked: true }, { slug: 'liter', locked: false }]] }
    expect(hashRecommendInputs(r, boss, draftA, 5, null)).toBe(
      hashRecommendInputs(r, boss, draftB, 5, null),
    )
  })

  it('numDecks만 달라도 해시가 다르다', () => {
    const r = [nikke('liter'), nikke('crown')]
    expect(hashRecommendInputs(r, boss, null, 3, null)).not.toBe(
      hashRecommendInputs(r, boss, null, 5, null),
    )
  })

  it('엔진 버전이 다르면 해시가 달라진다', () => {
    const r = [nikke('liter'), nikke('crown')]
    const a = hashRecommendInputs(r, boss, null, 5, 'aaaaaaaaaaaa')
    const b = hashRecommendInputs(r, boss, null, 5, 'bbbbbbbbbbbb')
    expect(a).not.toBe(b)
  })

  it('엔진 버전이 같으면 해시가 같다', () => {
    const r = [nikke('liter'), nikke('crown')]
    const a = hashRecommendInputs(r, boss, null, 5, 'aaaaaaaaaaaa')
    const b = hashRecommendInputs(r, boss, null, 5, 'aaaaaaaaaaaa')
    expect(a).toBe(b)
  })

  it('버전을 모르는 상태(null)도 자기들끼리는 일관된 키를 만든다', () => {
    const r = [nikke('liter'), nikke('crown')]
    const a = hashRecommendInputs(r, boss, null, 5, null)
    const b = hashRecommendInputs(r, boss, null, 5, null)
    expect(a).toBe(b)
    expect(a).not.toBe(hashRecommendInputs(r, boss, null, 5, 'aaaaaaaaaaaa'))
  })
})
