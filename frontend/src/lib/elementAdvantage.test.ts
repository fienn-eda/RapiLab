import { describe, expect, it } from 'vitest'
import { bossElementFor, weaknessFor } from './elementAdvantage'
import type { NikkeElement } from '../types/supportedUnit'

const ALL: NikkeElement[] = ['Fire', 'Water', 'Wind', 'Iron', 'Electric']

describe('elementAdvantage', () => {
  it('수냉이 약점인 보스는 작열이다', () => {
    expect(bossElementFor('Water')).toBe('Fire')
    expect(weaknessFor('Fire')).toBe('Water')
  })

  it('두 함수는 서로의 역함수다', () => {
    for (const element of ALL) {
      expect(weaknessFor(bossElementFor(element))).toBe(element)
      expect(bossElementFor(weaknessFor(element))).toBe(element)
    }
  })

  it('엔진의 순환을 그대로 담는다', () => {
    // backend/app/elements.py: Water > Fire > Wind > Iron > Electric > Water
    expect(ALL.map(bossElementFor)).toEqual(['Wind', 'Fire', 'Iron', 'Electric', 'Water'])
  })
})
