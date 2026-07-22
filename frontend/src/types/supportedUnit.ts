// TS mirror of GET /api/supported-units (frontend/README.md "GET
// /api/supported-units"; backend/app/api.py SupportedUnit model). The backend
// serves snake_case (burst_tier); mapSupportedUnit is the one place that maps
// it to the camelCase shape the rest of the frontend uses — mirrors how
// types/recommend.ts keeps request/response field names in sync with the
// Python source of truth.

export type NikkeElement = 'Fire' | 'Water' | 'Wind' | 'Iron' | 'Electric'

/** Raw wire shape returned by the backend. */
export interface SupportedUnitWire {
  slug: string
  name: string
  burst_tier: 1 | 2 | 3
  element: NikkeElement
}

/** Camel-cased shape the frontend works with. */
export interface SupportedUnit {
  slug: string
  name: string
  burstTier: 1 | 2 | 3
  element: NikkeElement
}

export const mapSupportedUnit = (wire: SupportedUnitWire): SupportedUnit => ({
  slug: wire.slug,
  name: wire.name,
  burstTier: wire.burst_tier,
  element: wire.element,
})
