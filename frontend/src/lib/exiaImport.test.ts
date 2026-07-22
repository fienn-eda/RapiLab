import { describe, it, expect } from 'vitest'
import { deriveSlug } from './exiaImport'

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
