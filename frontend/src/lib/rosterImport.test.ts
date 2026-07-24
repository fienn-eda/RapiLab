import { describe, it, expect } from 'vitest'
import { parseRosterJson } from './rosterImport'

const sample = () => ({
  synchroLevel: 663,
  units: [
    {
      resource_id: 16,
      name_en: 'Rapi: Red Hood',
      raid400: { hp: 3532402, atk: 143543, def: 20986 },
      actual: { hp: 9727100, atk: 418862, def: 55537 },
      overload: [{ name: '공격력 증가', value: 42.32 }],
      skill_levels: { skill1: 10, skill2: 10, burst: 10 },
      pve_cube: { name: 'Resilience Cube', level: 15 },
    },
  ],
})

describe('parseRosterJson', () => {
  it('maps raid-400 into hp/atk/def, actual into actual*, derives slug from name_en', () => {
    const { drafts } = parseRosterJson(sample())
    const d = drafts[0]
    expect(d.character_slug).toBe('rapi-red-hood') // resource_id 16 -> map hit
    expect(d.level).toBe('400')
    expect(d.atk).toBe('143543') // solo raid = level 400
    expect(d.actualAtk).toBe('418862') // union raid = real level
    expect(d.skill_levels).toEqual({ skill1: '10', skill2: '10', burst: '10' })
    expect(d.overload_options[0]).toMatchObject({ name: '공격력 증가', value: '42.32' })
  })

  it('ignores a pve_cube field in the imported roster', () => {
    const { drafts } = parseRosterJson({
      units: [
        {
          name_en: 'Rapi',
          resource_id: 16,
          raid400: { hp: 1, atk: 2, def: 0 },
          skill_levels: { skill1: 1, skill2: 1, burst: 1 },
          overload: [],
          pve_cube: { name: 'Resilience Cube', level: 15 },
        },
      ],
    })
    expect(drafts).toHaveLength(1)
    expect(drafts[0]).not.toHaveProperty('pve_cube')
    expect(drafts[0]).not.toHaveProperty('hasCube')
    expect(drafts[0]).not.toHaveProperty('cubeKnown')
  })

  it('handles an uninvested unit (no actual/overload/cube)', () => {
    const { drafts } = parseRosterJson({
      units: [
        {
          name_en: 'Neon: Blue Ocean',
          raid400: { hp: 2309238, atk: 94815, def: 13100 },
          skill_levels: { skill1: 1, skill2: 1, burst: 1 },
          pve_cube: null,
        },
      ],
    })
    const d = drafts[0]
    expect(d.character_slug).toBe('neon-blue-ocean')
    expect(d.atk).toBe('94815')
    expect(d.actualAtk).toBe('')
    expect(d.overload_options).toEqual([])
  })

  it('resolves encoded units by resource_id, not name, and promotes owned signatures', () => {
    const { drafts } = parseRosterJson({
      units: [
        { resource_id: 831, name_en: 'Rei', raid400: { hp: 1, atk: 1, def: 1 } },
        { resource_id: 101, name_en: 'Drake', favorite_item: true,
          raid400: { hp: 1, atk: 1, def: 1 } },
        { resource_id: 150, name_en: 'Julia', favorite_item: false,
          raid400: { hp: 1, atk: 1, def: 1 } },
      ],
    })
    expect(drafts.map((d) => d.character_slug)).toEqual([
      'rei-ayanami',
      'drake-signature', // Favorite Item owned
      'julia', // not owned -> base
    ])
  })

  it("promotes per each unit's own favorite_item flag", () => {
    const { drafts } = parseRosterJson({
      units: [
        { resource_id: 140, name_en: 'Sugar', favorite_item: true,
          raid400: { hp: 1, atk: 1, def: 1 } },
        { resource_id: 101, name_en: 'Drake', favorite_item: false,
          raid400: { hp: 1, atk: 1, def: 1 } },
        { resource_id: 411, name_en: 'Flora', favorite_item: true,
          raid400: { hp: 1, atk: 1, def: 1 } },
      ],
    })
    expect(drafts.map((d) => d.character_slug)).toEqual([
      'sugar-signature',
      'drake',
      'flora-signature',
    ])
  })

  it('leaves dual-slot units on their base slug when the roster omits the flag', () => {
    // A collector scrape cannot report ownership, so nothing may be promoted
    // from it - the recommendation would otherwise credit investment the user
    // may not have.
    const { drafts } = parseRosterJson({
      units: [
        { resource_id: 101, name_en: 'Drake', raid400: { hp: 1, atk: 1, def: 1 } },
        { resource_id: 100, name_en: 'Laplace', raid400: { hp: 1, atk: 1, def: 1 } },
      ],
    })
    expect(drafts.map((d) => d.character_slug)).toEqual(['drake', 'laplace'])
  })

  it('keeps unencoded owned units (raw slug) and warns in aggregate', () => {
    const { drafts, warnings } = parseRosterJson({
      units: [
        { resource_id: 71, name_en: 'Soline', raid400: { hp: 1, atk: 1, def: 1 } },
        { resource_id: 392, name_en: 'Rei', raid400: { hp: 1, atk: 1, def: 1 } },
      ],
    })
    // kept as drafts with raw-derived slugs (backend excludes them from search)
    expect(drafts.map((d) => d.character_slug)).toEqual(['soline', 'rei'])
    expect(warnings).toHaveLength(1)
    expect(warnings[0]).toContain('Soline')
    expect(warnings[0]).toContain('Rei')
  })

  it('throws on non-roster input', () => {
    expect(() => parseRosterJson({})).toThrow(/units/)
  })

  it('carries grade and core through from the payload', () => {
    const { drafts } = parseRosterJson({
      units: [
        {
          name_en: 'Rapi',
          resource_id: 16,
          grade: 3,
          core: 7,
          raid400: { hp: 1, atk: 2, def: 0 },
          skill_levels: { skill1: 1, skill2: 1, burst: 1 },
          overload: [],
        },
      ],
    })
    expect(drafts[0].grade).toBe(3)
    expect(drafts[0].core).toBe(7)
  })

  it('leaves grade and core undefined when the payload omits them', () => {
    // Absent must stay absent - filling in 0 would make the badge claim zero
    // breakthrough for a unit whose investment we never received.
    const { drafts } = parseRosterJson({
      units: [
        {
          name_en: 'Rapi',
          resource_id: 16,
          raid400: { hp: 1, atk: 2, def: 0 },
          skill_levels: { skill1: 1, skill2: 1, burst: 1 },
          overload: [],
        },
      ],
    })
    expect(drafts[0].grade).toBeUndefined()
    expect(drafts[0].core).toBeUndefined()
  })

  it('no longer produces a core_level field', () => {
    // core_level was an input the backend read nowhere; the InvestmentBadge
    // shows the real value instead.
    const { drafts } = parseRosterJson({
      units: [
        {
          name_en: 'Rapi',
          resource_id: 16,
          grade: 3,
          core: 7,
          raid400: { hp: 1, atk: 2, def: 0 },
          skill_levels: { skill1: 1, skill2: 1, burst: 1 },
          overload: [],
        },
      ],
    })
    expect(drafts[0]).not.toHaveProperty('core_level')
  })
})
