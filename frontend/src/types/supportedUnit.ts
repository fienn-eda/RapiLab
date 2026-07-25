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
  candidates?: string[] | null
}

/** Camel-cased shape the frontend works with. */
export interface SupportedUnit {
  slug: string
  name: string
  burstTier: 1 | 2 | 3
  element: NikkeElement
  /** Set only on an OWNED slug the engine fans out into several candidates
   * (one character, several modes). Which mode gets fielded is the engine's
   * pick, so such a unit belongs in the candidate pool but cannot be seated in
   * a specific deck — see `canSeatInDeck`. */
  candidates?: string[]
}

export const mapSupportedUnit = (wire: SupportedUnitWire): SupportedUnit => ({
  slug: wire.slug,
  name: wire.name,
  burstTier: wire.burst_tier,
  element: wire.element,
  ...(wire.candidates && wire.candidates.length > 1
    ? { candidates: wire.candidates }
    : {}),
})

/** Whether a draft can pin this unit to a deck. A slug standing for several
 * engine candidates cannot: the backend resolves a drafted seat to a concrete
 * spec and answers 422 for anything else, and picking a mode on the player's
 * behalf would be inventing a choice they never made. */
export const canSeatInDeck = (unit: SupportedUnit): boolean =>
  unit.candidates === undefined
