import { describe, it, expect } from 'vitest'
import { abbreviateOverload, sortOverload } from '../lib/overload'

describe('abbreviateOverload', () => {
  // The seven effect types backend/app/overload_decode.py can emit, in the
  // exact wording tables.json's `type_name` uses.
  it.each([
    ['우월코드 대미지 증가', '우코'],
    ['최대 장탄 수 증가', '장탄'],
    ['공격력 증가', '공'],
    ['차지 대미지 증가', '차댐'],
    ['차지 속도 증가', '차속'],
    ['크리티컬 확률 증가', '크확'],
    ['크리티컬 대미지 증가', '크댐'],
  ])('%s -> %s', (full, short) => {
    expect(abbreviateOverload(full)).toBe(short)
  })

  it('leaves an unrecognised effect name readable instead of mangling it', () => {
    // A new overload type reaches the UI before this map learns it; showing
    // the real name beats showing a wrong abbreviation.
    expect(abbreviateOverload('부활 확률 증가')).toBe('부활 확률')
    expect(abbreviateOverload('Attack Damage')).toBe('Attack Damage')
  })
})

describe('sortOverload', () => {
  const line = (name: string) => ({ name, value: 1 })
  const shortNames = (options: { name: string }[]) => options.map((o) => abbreviateOverload(o.name))

  // A fixed order is what lets two units be compared down the column rather
  // than line by line, so it cannot be left to whatever blablalink returned.
  it('puts the seven effects in the order they are read in', () => {
    const scrambled = [
      '차지 대미지 증가',
      '크리티컬 확률 증가',
      '공격력 증가',
      '크리티컬 대미지 증가',
      '우월코드 대미지 증가',
      '차지 속도 증가',
      '최대 장탄 수 증가',
    ].map(line)

    expect(shortNames(sortOverload(scrambled))).toEqual([
      '우코',
      '공',
      '장탄',
      '차속',
      '크댐',
      '크확',
      '차댐',
    ])
  })

  it('sorts a partial roll into the same relative order', () => {
    const rolled = ['크리티컬 확률 증가', '우월코드 대미지 증가', '차지 속도 증가'].map(line)
    expect(shortNames(sortOverload(rolled))).toEqual(['우코', '차속', '크확'])
  })

  it('puts an unknown effect last without dropping it', () => {
    const withUnknown = ['부활 확률 증가', '공격력 증가', 'Attack Damage'].map(line)
    expect(shortNames(sortOverload(withUnknown))).toEqual(['공', '부활 확률', 'Attack Damage'])
  })

  it('leaves the caller\'s array alone', () => {
    const original = ['공격력 증가', '우월코드 대미지 증가'].map(line)
    sortOverload(original)
    expect(shortNames(original)).toEqual(['공', '우코'])
  })
})
