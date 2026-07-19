import { describe, it, expect } from 'vitest'
import {
  getValidRoster,
  makeEmptyDraft,
  makeOverloadRow,
  mergeCollectorDrafts,
  mergeRosterDrafts,
  validateDraft,
  type NikkeDraft,
} from './nikkeDraft'

// A fully-valid draft used as the baseline; individual tests mutate one field
// to exercise a single constraint.
const validDraft = (): NikkeDraft => ({
  ...makeEmptyDraft(),
  character_slug: 'red-hood',
  level: '200',
  core_level: '7',
  hp: '1000000.5',
  atk: '85000',
  def_: '12000',
  skill_levels: { skill1: '10', skill2: '7', burst: '4' },
  overload_options: [],
  hasCube: false,
  pve_cube: { name: '', level: '' },
})

describe('validateDraft', () => {
  it('accepts a complete, in-range draft and parses it into a UserNikkeState', () => {
    const { errors, value } = validateDraft(validDraft())
    expect(errors).toEqual({})
    expect(value).toEqual({
      character_slug: 'red-hood',
      level: 200,
      core_level: 7,
      hp: 1000000.5,
      atk: 85000,
      def_: 12000,
      skill_levels: { skill1: 10, skill2: 7, burst: 4 },
      overload_options: [],
      pve_cube: null,
    })
  })

  it('reports every required field on an empty draft and yields no value', () => {
    const { errors, value } = validateDraft(makeEmptyDraft())
    expect(value).toBeUndefined()
    expect(errors.character_slug).toBe('Required')
    expect(errors.level).toBe('Required')
    expect(errors.core_level).toBe('Required')
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

  it('allows core_level 0 but rejects negative', () => {
    expect(validateDraft({ ...validDraft(), core_level: '0' }).value).toBeDefined()
    expect(validateDraft({ ...validDraft(), core_level: '-1' }).errors.core_level).toBe(
      'Must be ≥ 0',
    )
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
      { ...makeOverloadRow(), name: 'ATK', value: '12.5' },
      { ...makeOverloadRow(), name: 'Elemental Damage', value: '9' },
    ]
    const { errors, value } = validateDraft(draft)
    expect(errors.overload_options).toBeUndefined()
    expect(value?.overload_options).toEqual([
      { name: 'ATK', value: 12.5 },
      { name: 'Elemental Damage', value: 9 },
    ])
  })

  it('reports per-row overload errors keyed by row id', () => {
    const bad = { ...makeOverloadRow(), name: '', value: 'x' }
    const draft = validDraft()
    draft.overload_options = [bad]
    const { errors, value } = validateDraft(draft)
    expect(value).toBeUndefined()
    expect(errors.overload_options?.[bad.id]).toEqual({
      name: 'Required',
      value: 'Must be a number',
    })
  })

  it('leaves pve_cube null when no cube is equipped', () => {
    expect(validateDraft(validDraft()).value?.pve_cube).toBeNull()
  })

  it('validates the cube name and level 1–15 when a cube is equipped', () => {
    const draft = { ...validDraft(), hasCube: true, pve_cube: { name: '', level: '16' } }
    const { errors, value } = validateDraft(draft)
    expect(value).toBeUndefined()
    expect(errors.pve_cube).toEqual({ name: 'Required', level: 'Must be ≤ 15' })
  })

  it('parses a valid equipped cube into the value', () => {
    const draft = {
      ...validDraft(),
      hasCube: true,
      pve_cube: { name: 'Bastion', level: '9' },
    }
    expect(validateDraft(draft).value?.pve_cube).toEqual({ name: 'Bastion', level: 9 })
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

const draft = (over: Partial<ReturnType<typeof makeEmptyDraft>>) => ({
  ...makeEmptyDraft(),
  ...over,
})

describe('mergeRosterDrafts', () => {
  it('overwrites import fields on a matching slug but preserves manual fields and id', () => {
    const existing = draft({
      character_slug: 'rapi-red-hood',
      atk: '60000',
      hp: '120000',
      def_: '3000',
      hasCube: true,
      pve_cube: { name: 'Bastion Cube', level: '7' },
      skill_levels: { skill1: '1', skill2: '1', burst: '1' },
      level: '200',
      core_level: '0',
    })
    const incoming = draft({
      character_slug: 'rapi-red-hood',
      atk: '',
      hp: '',
      skill_levels: { skill1: '10', skill2: '10', burst: '10' },
      level: '663',
      core_level: '5',
      overload_options: [{ id: 'x', name: '공격력 증가', value: '12' }],
    })

    const { drafts, added, updated } = mergeRosterDrafts([existing], [incoming])

    expect(added).toBe(0)
    expect(updated).toBe(1)
    expect(drafts).toHaveLength(1)
    const merged = drafts[0]
    expect(merged.id).toBe(existing.id)
    expect(merged.atk).toBe('60000')
    expect(merged.hp).toBe('120000')
    expect(merged.def_).toBe('3000')
    expect(merged.hasCube).toBe(true)
    expect(merged.pve_cube).toEqual({ name: 'Bastion Cube', level: '7' })
    expect(merged.level).toBe('663')
    expect(merged.core_level).toBe('5')
    expect(merged.skill_levels).toEqual({ skill1: '10', skill2: '10', burst: '10' })
    expect(merged.overload_options).toEqual([
      { id: 'x', name: '공격력 증가', value: '12' },
    ])
  })

  it('adds a new slug', () => {
    const existing = draft({ character_slug: 'liter' })
    const incoming = draft({ character_slug: 'crown' })
    const { drafts, added, updated } = mergeRosterDrafts([existing], [incoming])
    expect(added).toBe(1)
    expect(updated).toBe(0)
    expect(drafts.map((d) => d.character_slug)).toEqual(['liter', 'crown'])
  })

  it('leaves an existing draft untouched when the import does not include it', () => {
    const kept = draft({ character_slug: 'liter', atk: '999' })
    const incoming = draft({ character_slug: 'crown' })
    const { drafts } = mergeRosterDrafts([kept], [incoming])
    expect(drafts.find((d) => d.character_slug === 'liter')).toEqual(kept)
  })
})

describe('mergeCollectorDrafts', () => {
  it('overwrites hasCube/pve_cube when the incoming unit carries cube info', () => {
    const existing = draft({
      character_slug: 'liter',
      hasCube: true,
      pve_cube: { name: 'Old Cube', level: '5' },
      cubeKnown: true,
    })
    const incoming = draft({
      character_slug: 'liter',
      hasCube: true,
      pve_cube: { name: 'New Cube', level: '10' },
      cubeKnown: true,
    })
    const { drafts, updated } = mergeCollectorDrafts([existing], [incoming])
    expect(updated).toBe(1)
    expect(drafts[0].hasCube).toBe(true)
    expect(drafts[0].pve_cube).toEqual({ name: 'New Cube', level: '10' })
  })

  it('preserves hasCube/pve_cube when the incoming unit carries no cube information at all', () => {
    // The bookmarklet-assembled sync payload never carries pve_cube (the
    // backend has no cube-tid -> name map), so parseRosterJson marks it
    // cubeKnown: false. A sync must not erase a cube entered via file-import.
    const existing = draft({
      character_slug: 'liter',
      hasCube: true,
      pve_cube: { name: 'Existing Cube', level: '7' },
      cubeKnown: true,
    })
    const incoming = draft({
      character_slug: 'liter',
      atk: '77777',
      level: '400',
      hasCube: false,
      pve_cube: { name: '', level: '' },
      cubeKnown: false,
    })
    const { drafts, updated } = mergeCollectorDrafts([existing], [incoming])
    expect(updated).toBe(1)
    expect(drafts[0].hasCube).toBe(true)
    expect(drafts[0].pve_cube).toEqual({ name: 'Existing Cube', level: '7' })
    // Other collector-sourced fields still overwrite even when cube info is unknown.
    expect(drafts[0].atk).toBe('77777')
    expect(drafts[0].level).toBe('400')
  })

  it('adds a new slug with whatever cube info it carries', () => {
    const existing = draft({ character_slug: 'liter' })
    const incoming = draft({
      character_slug: 'crown',
      hasCube: true,
      pve_cube: { name: 'New Cube', level: '3' },
      cubeKnown: true,
    })
    const { drafts, added } = mergeCollectorDrafts([existing], [incoming])
    expect(added).toBe(1)
    expect(drafts.find((d) => d.character_slug === 'crown')?.hasCube).toBe(true)
  })
})
