// Dev fixture standing in for GET /api/supported-units (frontend/README.md
// "GET /api/supported-units"). A small fixed roster spanning all three burst
// tiers and a few elements, enough to exercise the draft palette's grouping
// and portrait/chip fallback in dev without the backend. Swap-in point:
// supportedUnits.ts.

import type { SupportedUnit } from '../types/supportedUnit'

const FIXTURE_UNITS: SupportedUnit[] = [
  { slug: 'crown', name: 'Crown', burstTier: 1, element: 'Iron' },
  { slug: 'anne', name: 'Anne', burstTier: 1, element: 'Fire' },
  { slug: 'liter', name: 'Liter', burstTier: 2, element: 'Water' },
  { slug: 'noir', name: 'Noir', burstTier: 2, element: 'Electric' },
  { slug: 'blanc', name: 'Blanc', burstTier: 3, element: 'Wind' },
  { slug: 'red-hood', name: 'Red Hood', burstTier: 3, element: 'Fire' },
]

export const mockSupportedUnits = (): Promise<SupportedUnit[]> =>
  Promise.resolve(FIXTURE_UNITS)
