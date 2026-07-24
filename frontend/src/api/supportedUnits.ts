// Typed client for GET /api/supported-units. Feeds the unit palette
// (frontend/README.md "GET /api/supported-units"). Maps the backend's
// snake_case wire shape to the frontend's camelCase SupportedUnit.

import type { SupportedUnit, SupportedUnitWire } from '../types/supportedUnit'
import { mapSupportedUnit } from '../types/supportedUnit'
import { RecommendApiError } from './recommendApiError'

export const getSupportedUnits = async (): Promise<SupportedUnit[]> => {
  const response = await fetch('/api/supported-units')
  if (!response.ok) {
    const detail: unknown = await response.json().catch(() => null)
    throw new RecommendApiError(response.status, detail)
  }
  const wire = (await response.json()) as SupportedUnitWire[]
  return wire.map(mapSupportedUnit)
}
