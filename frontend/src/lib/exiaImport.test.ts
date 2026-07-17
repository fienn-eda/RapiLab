import { describe, it, expect } from 'vitest'
import { deriveSlug, resolveSlug } from './exiaImport'

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
