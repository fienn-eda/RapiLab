import { describe, it, expect } from 'vitest'
import { canSeatInDeck, mapSupportedUnit } from './supportedUnit'

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
    // the same thing. Neither should leave a `candidates` key behind, since
    // that key is what marks a unit as un-seatable.
    for (const candidates of [null, undefined, ['crown']]) {
      const unit = mapSupportedUnit({
        slug: 'crown', name: 'Crown', burst_tier: 1, element: 'Iron', candidates,
      })
      expect(unit.candidates).toBeUndefined()
      expect(canSeatInDeck(unit)).toBe(true)
    }
  })
})

describe('canSeatInDeck', () => {
  it('refuses a unit standing for several engine candidates', () => {
    // Which mode gets fielded is the engine's pick, and the backend answers 422
    // for a drafted slug that is not a concrete spec - so the draft palette must
    // not offer her at all.
    const bready = mapSupportedUnit({
      slug: 'bready',
      name: 'Bready',
      burst_tier: 3,
      element: 'Water',
      candidates: ['bready-lingering', 'bready-recommended'],
    })
    expect(canSeatInDeck(bready)).toBe(false)
  })
})
