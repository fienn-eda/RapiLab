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
    expect(errors.character_slug).toBe('Required')
    expect(errors.level).toBe('Required')
    expect(errors.hp).toBe('Required')
    expect(errors.atk).toBe('Required')
    expect(errors.def_).toBe('Required')
    expect(errors.skill_levels).toEqual({
      skill1: 'Required',
      skill2: 'Required',
      burst: 'Required',
    })
  })

  it('enforces level >= 1', () => {
    const { errors, value } = validateDraft({ ...validDraft(), level: '0' })
    expect(errors.level).toBe('Must be ≥ 1')
    expect(value).toBeUndefined()
  })

  it('rejects non-integer whole-number fields', () => {
    expect(validateDraft({ ...validDraft(), level: '10.5' }).errors.level).toBe(
      'Must be a whole number',
    )
  })

  it('rejects negative stats', () => {
    expect(validateDraft({ ...validDraft(), hp: '-1' }).errors.hp).toBe('Must be ≥ 0')
  })

  it('rejects non-numeric stats', () => {
    expect(validateDraft({ ...validDraft(), atk: 'abc' }).errors.atk).toBe(
      'Must be a number',
    )
  })

  it('enforces skill levels within 1–10', () => {
    const low = validateDraft({
      ...validDraft(),
      skill_levels: { skill1: '0', skill2: '5', burst: '5' },
    })
    expect(low.errors.skill_levels).toEqual({ skill1: 'Must be ≥ 1' })

    const high = validateDraft({
      ...validDraft(),
      skill_levels: { skill1: '5', skill2: '5', burst: '11' },
    })
    expect(high.errors.skill_levels).toEqual({ burst: 'Must be ≤ 10' })
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

  it('reports per-row overload errors keyed by row id', () => {
    const bad = { id: 'row-1', name: '', value: 'x' }
    const draft = validDraft()
    draft.overload_options = [bad]
    const { errors, value } = validateDraft(draft)
    expect(value).toBeUndefined()
    expect(errors.overload_options?.[bad.id]).toEqual({
      name: 'Required',
      value: 'Must be a number',
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
