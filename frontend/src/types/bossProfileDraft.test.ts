import { describe, it, expect } from 'vitest'
import {
  bossProfileToDraft,
  makeDefaultBossProfileDraft,
  validateBossProfileDraft,
  type BossProfileDraft,
} from './bossProfileDraft'

describe('validateBossProfileDraft', () => {
  it('accepts the defaults (non-elemental, DEF 0, 180s, no part destruction)', () => {
    const { errors, value } = validateBossProfileDraft(makeDefaultBossProfileDraft())
    expect(errors).toEqual({})
    expect(value).toEqual({
      element: null,
      core_hittable: false,
      enemy_def: 0,
      fight_duration: 180,
      part_destructible: false,
    })
  })

  it('accepts an elemental, core-hittable, part-destructible boss with a custom DEF and duration', () => {
    const draft: BossProfileDraft = {
      element: 'Fire',
      core_hittable: true,
      enemy_def: '15000',
      fight_duration: '90',
      part_destructible: true,
    }
    expect(validateBossProfileDraft(draft).value).toEqual({
      element: 'Fire',
      core_hittable: true,
      enemy_def: 15000,
      fight_duration: 90,
      part_destructible: true,
    })
  })

  it('rejects a negative enemy_def', () => {
    const draft = { ...makeDefaultBossProfileDraft(), enemy_def: '-1' }
    const { errors, value } = validateBossProfileDraft(draft)
    expect(errors.enemy_def).toBe('0 이상이어야 해요')
    expect(value).toBeUndefined()
  })

  it('rejects a zero or negative fight_duration', () => {
    expect(
      validateBossProfileDraft({ ...makeDefaultBossProfileDraft(), fight_duration: '0' })
        .errors.fight_duration,
    ).toBe('0보다 커야 해요')
    expect(
      validateBossProfileDraft({ ...makeDefaultBossProfileDraft(), fight_duration: '-5' })
        .errors.fight_duration,
    ).toBe('0 이상이어야 해요')
  })

  it('rejects non-numeric fields', () => {
    const draft = { ...makeDefaultBossProfileDraft(), enemy_def: 'abc' }
    expect(validateBossProfileDraft(draft).errors.enemy_def).toBe('숫자를 입력하세요')
  })

  it('rejects empty fields as required', () => {
    const draft = { ...makeDefaultBossProfileDraft(), fight_duration: '' }
    expect(validateBossProfileDraft(draft).errors.fight_duration).toBe('필수 입력이에요')
  })
})

describe('bossProfileToDraft', () => {
  it('round-trips through validate -> toDraft -> validate to an equal BossProfile', () => {
    const draft: BossProfileDraft = {
      element: 'Fire',
      core_hittable: true,
      enemy_def: '15000',
      fight_duration: '90',
      part_destructible: true,
    }
    const { value: boss } = validateBossProfileDraft(draft)
    const restoredDraft = bossProfileToDraft(boss!)
    const { value: restoredBoss } = validateBossProfileDraft(restoredDraft)
    expect(restoredBoss).toEqual(boss)
  })

  it('round-trips the defaults', () => {
    const { value: boss } = validateBossProfileDraft(makeDefaultBossProfileDraft())
    const { value: restoredBoss } = validateBossProfileDraft(bossProfileToDraft(boss!))
    expect(restoredBoss).toEqual(boss)
  })
})
