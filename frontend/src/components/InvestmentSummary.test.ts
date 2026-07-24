import { describe, it, expect } from 'vitest'
import { abbreviateOverload } from './InvestmentSummary'

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
