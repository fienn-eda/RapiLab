import { describe, it, expect } from 'vitest'
import {
  getValidRoster,
  makeEmptyDraft,
  validateDraft,
  type NikkeDraft,
} from './nikkeDraft'

// A fully-valid draft used as the baseline; individual tests mutate one field
// to exercise a single constraint.
const validDraft = (): NikkeDraft => ({
  ...makeEmptyDraft(),
  character_slug: 'red-hood',
  level: '200',
  hp: '1000000.5',
  atk: '85000',
  def_: '12000',
  skill_levels: { skill1: '10', skill2: '7', burst: '4' },
  overload_options: [],
})

describe('validateDraft', () => {
  it('accepts a complete, in-range draft and parses it into a UserNikkeState', () => {
    const { errors, value } = validateDraft(validDraft())
    expect(errors).toEqual({})
    expect(value).toEqual({
      character_slug: 'red-hood',
      level: 200,
      hp: 1000000.5,
      atk: 85000,
      def_: 12000,
      skill_levels: { skill1: 10, skill2: 7, burst: 4 },
      overload_options: [],
    })
  })

  it('reports every required field on an empty draft and yields no value', () => {
    const { errors, value } = validateDraft(makeEmptyDraft())
    expect(value).toBeUndefined()
    expect(errors.character_slug).toBe('필수 입력이에요')
    expect(errors.level).toBe('필수 입력이에요')
    expect(errors.hp).toBe('필수 입력이에요')
    expect(errors.atk).toBe('필수 입력이에요')
    expect(errors.def_).toBe('필수 입력이에요')
    expect(errors.skill_levels).toEqual({
      skill1: '필수 입력이에요',
      skill2: '필수 입력이에요',
      burst: '필수 입력이에요',
    })
  })

  it('enforces level >= 1', () => {
    const { errors, value } = validateDraft({ ...validDraft(), level: '0' })
    expect(errors.level).toBe('1 이상이어야 해요')
    expect(value).toBeUndefined()
  })

  it('rejects non-integer whole-number fields', () => {
    expect(validateDraft({ ...validDraft(), level: '10.5' }).errors.level).toBe(
      '정수를 입력하세요',
    )
  })

  it('rejects negative stats', () => {
    expect(validateDraft({ ...validDraft(), hp: '-1' }).errors.hp).toBe('0 이상이어야 해요')
  })

  it('rejects non-numeric stats', () => {
    expect(validateDraft({ ...validDraft(), atk: 'abc' }).errors.atk).toBe(
      '숫자를 입력하세요',
    )
  })

  it('enforces skill levels within 1–10', () => {
    const low = validateDraft({
      ...validDraft(),
      skill_levels: { skill1: '0', skill2: '5', burst: '5' },
    })
    expect(low.errors.skill_levels).toEqual({ skill1: '1 이상이어야 해요' })

    const high = validateDraft({
      ...validDraft(),
      skill_levels: { skill1: '5', skill2: '5', burst: '11' },
    })
    expect(high.errors.skill_levels).toEqual({ burst: '10 이하여야 해요' })
  })

  it('accepts valid overload rows and includes them in the parsed value', () => {
    const draft = validDraft()
    draft.overload_options = [
      { id: 'row-1', name: 'ATK', value: '12.5' },
      { id: 'row-2', name: 'Elemental Damage', value: '9' },
    ]
    const { errors, value } = validateDraft(draft)
    expect(errors.overload_options).toBeUndefined()
    expect(value?.overload_options).toEqual([
      { name: 'ATK', value: 12.5 },
      { name: 'Elemental Damage', value: 9 },
    ])
  })

  it('forwards the per-gear rolls a synced row carries', () => {
    const draft = validDraft()
    draft.overload_options = [
      {
        id: 'row-1',
        name: '차지 속도 증가',
        value: '7.2',
        lines: [
          { slot: 'head', value: 2.57 },
          { slot: 'arm', value: 4.63 },
        ],
      },
    ]
    const { value } = validateDraft(draft)
    expect(value?.overload_options[0].lines).toEqual([
      { slot: 'head', value: 2.57 },
      { slot: 'arm', value: 4.63 },
    ])
  })

  it('drops rolls whose sum no longer matches the total shown', () => {
    // Charge speed is computed from the rolls, so a total edited away from them
    // would keep answering for the old gear. 2.57 + 4.63 is 7.20, not 9.
    const draft = validDraft()
    draft.overload_options = [
      {
        id: 'row-1',
        name: '차지 속도 증가',
        value: '9',
        lines: [
          { slot: 'head', value: 2.57 },
          { slot: 'arm', value: 4.63 },
        ],
      },
    ]
    const { value } = validateDraft(draft)
    expect(value?.overload_options).toEqual([{ name: '차지 속도 증가', value: 9 }])
    expect(value?.overload_options[0].lines).toBeUndefined()
  })

  it('reports per-row overload errors keyed by row id', () => {
    const bad = { id: 'row-1', name: '', value: 'x' }
    const draft = validDraft()
    draft.overload_options = [bad]
    const { errors, value } = validateDraft(draft)
    expect(value).toBeUndefined()
    expect(errors.overload_options?.[bad.id]).toEqual({
      name: '필수 입력이에요',
      value: '숫자를 입력하세요',
    })
  })

})

describe('getValidRoster', () => {
  it('keeps only drafts that parse into a valid UserNikkeState, in order', () => {
    const good = validDraft()
    const bad = { ...makeEmptyDraft(), character_slug: 'incomplete' }
    const roster = getValidRoster([bad, good, bad])
    expect(roster).toEqual([validateDraft(good).value])
  })

  it('returns an empty array when no drafts are valid', () => {
    expect(getValidRoster([makeEmptyDraft()])).toEqual([])
  })
})
