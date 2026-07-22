import { describe, it, expect } from 'vitest'
import { mapSupportedUnit } from './supportedUnit'

describe('mapSupportedUnit', () => {
  it('maps the backend snake_case wire shape to the camelCase frontend shape', () => {
    expect(
      mapSupportedUnit({ slug: 'crown', name: 'Crown', burst_tier: 1, element: 'Iron' }),
    ).toEqual({ slug: 'crown', name: 'Crown', burstTier: 1, element: 'Iron' })
  })
})
