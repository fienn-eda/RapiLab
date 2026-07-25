import { describe, it, expect } from 'vitest'
import { mapSupportedUnit, ownedSlugFor, ownedSlugIndex } from './supportedUnit'

describe('mapSupportedUnit', () => {
  it('maps the backend snake_case wire shape to the camelCase frontend shape', () => {
    expect(
      mapSupportedUnit({ slug: 'crown', name: 'Crown', burst_tier: 1, element: 'Iron' }),
    ).toEqual({ slug: 'crown', name: 'Crown', burstTier: 1, element: 'Iron' })
  })

  it('carries the candidate list of an owned slug the engine fans out', () => {
    expect(
      mapSupportedUnit({
        slug: 'bready',
        name: 'Bready',
        burst_tier: 3,
        element: 'Water',
        candidates: ['bready-lingering', 'bready-recommended'],
      }).candidates,
    ).toEqual(['bready-lingering', 'bready-recommended'])
  })

  it('treats a null or single-entry candidate list as no choice at all', () => {
    // The backend sends null for the vast majority; a one-entry list would say
    // the same thing. Neither should leave a `candidates` key behind.
    for (const candidates of [null, undefined, ['crown']]) {
      const unit = mapSupportedUnit({
        slug: 'crown', name: 'Crown', burst_tier: 1, element: 'Iron', candidates,
      })
      expect(unit.candidates).toBeUndefined()
    }
  })
})

describe('ownedSlugFor', () => {
  const units = [
    mapSupportedUnit({ slug: 'crown', name: 'Crown', burst_tier: 1, element: 'Iron' }),
    mapSupportedUnit({
      slug: 'bready', name: 'Bready', burst_tier: 3, element: 'Water',
      candidates: ['bready-lingering', 'bready-recommended'],
    }),
  ]
  const index = ownedSlugIndex(units)

  it('maps every candidate back to the slug the player owns', () => {
    expect(ownedSlugFor('bready-lingering', index)).toBe('bready')
    expect(ownedSlugFor('bready-recommended', index)).toBe('bready')
  })

  it('leaves a slug that is its own character alone', () => {
    expect(ownedSlugFor('crown', index)).toBe('crown')
    // Including the owned slug itself, and one the catalog has never heard of -
    // a stale cached result must not resolve to undefined.
    expect(ownedSlugFor('bready', index)).toBe('bready')
    expect(ownedSlugFor('who-dis', index)).toBe('who-dis')
  })
})
