import { describe, it, expect } from 'vitest'
import { deriveSlug, resolveSlug, aggregateOverload } from './exiaImport'

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
