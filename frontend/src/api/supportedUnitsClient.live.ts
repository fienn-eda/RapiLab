// Live client for GET /api/supported-units. Feeds the draft palette
// (frontend/README.md "GET /api/supported-units"). Maps the backend's
// snake_case wire shape to the frontend's camelCase SupportedUnit. Swap-in
// point: supportedUnits.ts, the only module that decides between this and the
// dev mock — mirrors recommendRaidClient.live.ts.

import type { SupportedUnit, SupportedUnitWire } from '../types/supportedUnit'
import { mapSupportedUnit } from '../types/supportedUnit'
import { RecommendApiError } from './recommendApiError'

export const fetchSupportedUnits = async (): Promise<SupportedUnit[]> => {
  const response = await fetch('/api/supported-units')
  if (!response.ok) {
    const detail: unknown = await response.json().catch(() => null)
    throw new RecommendApiError(response.status, detail)
  }
  const wire = (await response.json()) as SupportedUnitWire[]
  return wire.map(mapSupportedUnit)
}
