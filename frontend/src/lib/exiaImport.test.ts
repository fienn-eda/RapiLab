import { describe, it, expect } from 'vitest'
import { deriveSlug, resolveSlug, aggregateOverload } from './exiaImport'
import { parseExiaExport } from './exiaImport'

describe('deriveSlug', () => {
  it('kebab-cases a plain name', () => {
    expect(deriveSlug('Zwei')).toBe('zwei')
  })

  it('drops colons and parentheses', () => {
    expect(deriveSlug('Maiden: Ice Rose')).toBe('maiden-ice-rose')
    expect(deriveSlug('Rei (Tentative Name)')).toBe('rei-tentative-name')
    expect(deriveSlug('Asuka: WILLE')).toBe('asuka-wille')
  })
})

describe('resolveSlug', () => {
  it('passes an already-correct derived slug through', () => {
    expect(resolveSlug('Zwei')).toBe('zwei')
    expect(resolveSlug('Maiden: Ice Rose')).toBe('maiden-ice-rose')
  })

  it('applies the alias table for short in-game names', () => {
    expect(resolveSlug('Ada')).toBe('ada-wong')
    expect(resolveSlug('Jill')).toBe('jill-valentine')
    expect(resolveSlug('Rei')).toBe('rei-ayanami')
    expect(resolveSlug('Rei (Tentative Name)')).toBe('rei-ayanami-tentative-name')
    expect(resolveSlug('Asuka: WILLE')).toBe('asuka-shikinami-langley-wille')
    expect(resolveSlug('Soline')).toBe('soline-frost-ticket')
    expect(resolveSlug('Marciana')).toBe('marciana-marine-study')
    expect(resolveSlug('Takina')).toBe('takina-inoue')
    expect(resolveSlug('Chisato')).toBe('chisato-nishikigi')
  })

  it('leaves an unencoded unit as its derived slug (excluded downstream)', () => {
    expect(resolveSlug('Naga')).toBe('naga')
    expect(resolveSlug('Red Hood')).toBe('red-hood')
    expect(resolveSlug('Cinderella: Crystal Wave')).toBe('cinderella-crystal-wave')
  })
})

describe('aggregateOverload', () => {
  it('sums a function_type across the 4 gear pieces and maps to the Korean stat name', () => {
    const { rows } = aggregateOverload({
      '0': [{ function_type: 'IncElementDmg', function_value: 23.56, level: 11 }],
      '1': [{ function_type: 'IncElementDmg', function_value: 19.35, level: 8 }],
      '2': [{ function_type: 'StatAtk', function_value: 10.0, level: 4 }],
      '3': [],
    })
    expect(rows).toEqual([
      { id: expect.any(String), name: '우월코드 대미지 증가', value: '42.91' },
      { id: expect.any(String), name: '공격력 증가', value: '10' },
    ])
  })

  it('maps all seven known function types', () => {
    const { rows } = aggregateOverload({
      '0': [
        { function_type: 'StatAtk', function_value: 1, level: 1 },
        { function_type: 'IncElementDmg', function_value: 1, level: 1 },
        { function_type: 'StatCriticalDamage', function_value: 1, level: 1 },
        { function_type: 'StatCritical', function_value: 1, level: 1 },
        { function_type: 'StatChargeDamage', function_value: 1, level: 1 },
        { function_type: 'StatChargeTime', function_value: 1, level: 1 },
        { function_type: 'StatAmmoLoad', function_value: 1, level: 1 },
      ],
      '1': [],
      '2': [],
      '3': [],
    })
    expect(rows.map((r) => r.name)).toEqual([
      '공격력 증가',
      '우월코드 대미지 증가',
      '크리티컬 대미지 증가',
      '크리티컬 확률 증가',
      '차지 대미지 증가',
      '차지 속도 증가',
      '최대 장탄 수 증가',
    ])
  })

  it('drops unmapped function types (def, accuracy) and reports them', () => {
    const { rows, droppedTypes } = aggregateOverload({
      '0': [
        { function_type: 'StatDef', function_value: 5, level: 2 },
        { function_type: 'StatAccuracyCircle', function_value: 2.3, level: 1 },
        { function_type: 'StatAtk', function_value: 7, level: 3 },
      ],
      '1': [],
      '2': [],
      '3': [],
    })
    expect(rows).toEqual([
      { id: expect.any(String), name: '공격력 증가', value: '7' },
    ])
    expect(droppedTypes).toEqual(['StatDef', 'StatAccuracyCircle'])
  })

  it('returns nothing for empty equipments', () => {
    expect(aggregateOverload({})).toEqual({ rows: [], droppedTypes: [] })
  })
})

const sampleExport = () => ({
  name: 'TESTER',
  game_uid: 'SHOULD-NOT-BE-READ',
  synchroLevel: 663,
  cookie: 'game_login_game=SECRET; token=SECRET',
  elements: {
    Electronic: [
      {
        name_en: 'Maiden: Ice Rose',
        skill1_level: 10,
        skill2_level: 9,
        skill_burst_level: 8,
        item_level: 15,
        item_rare: 'SR',
        limit_break: { grade: 3, core: 2 },
        equipments: {
          '0': [
            { function_type: 'IncElementDmg', function_value: 23.56, level: 11 },
            { function_type: 'StatDef', function_value: 5, level: 1 },
          ],
          '1': [{ function_type: 'IncElementDmg', function_value: 19.35, level: 8 }],
          '2': [],
          '3': [],
        },
      },
      {
        name_en: 'Ada',
        skill1_level: 1,
        skill2_level: 1,
        skill_burst_level: 1,
        limit_break: { grade: 0, core: 0 },
        equipments: { '0': [], '1': [], '2': [], '3': [] },
      },
    ],
    Iron: [
      {
        name_en: 'Naga',
        skill1_level: 5,
        skill2_level: 5,
        skill_burst_level: 5,
        limit_break: { grade: null, core: null },
        equipments: { '0': [], '1': [], '2': [], '3': [] },
      },
    ],
    Utility: [],
  },
})

describe('parseExiaExport', () => {
  it('maps a character: slug, synchro level, skills, core, overload — leaving stats/cube manual', () => {
    const { drafts } = parseExiaExport(sampleExport())
    const maiden = drafts.find((d) => d.character_slug === 'maiden-ice-rose')!
    expect(maiden.level).toBe('663')
    expect(maiden.core_level).toBe('2')
    expect(maiden.skill_levels).toEqual({ skill1: '10', skill2: '9', burst: '8' })
    expect(maiden.overload_options).toEqual([
      { id: expect.any(String), name: '우월코드 대미지 증가', value: '42.91' },
    ])
    expect(maiden.hp).toBe('')
    expect(maiden.atk).toBe('')
    expect(maiden.def_).toBe('')
    expect(maiden.hasCube).toBe(false)
    expect(maiden.pve_cube).toEqual({ name: '', level: '' })
  })

  it('applies the slug alias and keeps unencoded units by their derived slug', () => {
    const { drafts } = parseExiaExport(sampleExport())
    expect(drafts.map((d) => d.character_slug).sort()).toEqual([
      'ada-wong',
      'maiden-ice-rose',
      'naga',
    ])
  })

  it('maps a null limit_break to core_level 0', () => {
    const { drafts } = parseExiaExport(sampleExport())
    expect(drafts.find((d) => d.character_slug === 'naga')!.core_level).toBe('0')
  })

  it('reports dropped overload types as a warning', () => {
    const { warnings } = parseExiaExport(sampleExport())
    expect(warnings).toEqual([
      {
        kind: 'dropped-overload',
        nameEn: 'Maiden: Ice Rose',
        slug: 'maiden-ice-rose',
        droppedTypes: ['StatDef'],
      },
    ])
  })

  it('never surfaces cookie or game_uid anywhere in the result', () => {
    const result = parseExiaExport(sampleExport())
    const serialized = JSON.stringify(result)
    expect(serialized).not.toContain('SECRET')
    expect(serialized).not.toContain('SHOULD-NOT-BE-READ')
  })

  it('throws on input that is not an export', () => {
    expect(() => parseExiaExport(null)).toThrow(/elements/)
    expect(() => parseExiaExport({})).toThrow(/elements/)
    expect(() => parseExiaExport({ elements: 'nope' })).toThrow(/elements/)
  })

  it('skips a character with no name_en and reports it', () => {
    const bad = sampleExport()
    // @ts-expect-error deliberately malformed
    bad.elements.Electronic.push({ skill1_level: 1 })
    const { drafts, warnings } = parseExiaExport(bad)
    expect(drafts).toHaveLength(3)
    expect(warnings).toContainEqual(
      expect.objectContaining({ kind: 'skipped-character' }),
    )
  })
})
