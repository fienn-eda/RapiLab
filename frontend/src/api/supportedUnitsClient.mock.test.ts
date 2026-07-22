import { describe, it, expect } from 'vitest'
import { mockSupportedUnits } from './supportedUnitsClient.mock'

describe('mockSupportedUnits', () => {
  it('resolves a fixed roster of supported units spanning all three burst tiers', async () => {
    const units = await mockSupportedUnits()
    expect(units.length).toBeGreaterThan(0)
    const tiers = new Set(units.map((u) => u.burstTier))
    expect(tiers).toEqual(new Set([1, 2, 3]))
    for (const unit of units) {
      expect(unit).toMatchObject({
        slug: expect.any(String),
        name: expect.any(String),
        burstTier: expect.any(Number),
        element: expect.any(String),
      })
    }
  })
})
