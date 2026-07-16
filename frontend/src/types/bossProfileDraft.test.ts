import { describe, it, expect } from 'vitest'
import {
  makeDefaultBossProfileDraft,
  validateBossProfileDraft,
  type BossProfileDraft,
} from './bossProfileDraft'

describe('validateBossProfileDraft', () => {
  it('accepts the defaults (non-elemental, DEF 0, 180s)', () => {
    const { errors, value } = validateBossProfileDraft(makeDefaultBossProfileDraft())
    expect(errors).toEqual({})
    expect(value).toEqual({
      element: null,
      core_hittable: false,
      enemy_def: 0,
      fight_duration: 180,
    })
  })

  it('accepts an elemental, core-hittable boss with a custom DEF and duration', () => {
    const draft: BossProfileDraft = {
      element: 'Fire',
      core_hittable: true,
      enemy_def: '15000',
      fight_duration: '90',
    }
    expect(validateBossProfileDraft(draft).value).toEqual({
      element: 'Fire',
      core_hittable: true,
      enemy_def: 15000,
      fight_duration: 90,
    })
  })

  it('rejects a negative enemy_def', () => {
    const draft = { ...makeDefaultBossProfileDraft(), enemy_def: '-1' }
    const { errors, value } = validateBossProfileDraft(draft)
    expect(errors.enemy_def).toBe('Must be ≥ 0')
    expect(value).toBeUndefined()
  })

  it('rejects a zero or negative fight_duration', () => {
    expect(
      validateBossProfileDraft({ ...makeDefaultBossProfileDraft(), fight_duration: '0' })
        .errors.fight_duration,
    ).toBe('Must be > 0')
    expect(
      validateBossProfileDraft({ ...makeDefaultBossProfileDraft(), fight_duration: '-5' })
        .errors.fight_duration,
    ).toBe('Must be ≥ 0')
  })

  it('rejects non-numeric fields', () => {
    const draft = { ...makeDefaultBossProfileDraft(), enemy_def: 'abc' }
    expect(validateBossProfileDraft(draft).errors.enemy_def).toBe('Must be a number')
  })

  it('rejects empty fields as required', () => {
    const draft = { ...makeDefaultBossProfileDraft(), fight_duration: '' }
    expect(validateBossProfileDraft(draft).errors.fight_duration).toBe('Required')
  })
})
