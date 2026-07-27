import { describe, it, expect } from 'vitest'
import { elementLabel } from './elementName'

describe('elementLabel', () => {
  it.each([
    ['Fire', '작열'],
    ['Water', '수냉'],
    ['Wind', '풍압'],
    ['Iron', '철갑'],
    ['Electric', '전격'],
  ] as const)('%s -> %s', (element, label) => {
    expect(elementLabel(element)).toBe(label)
  })
})
