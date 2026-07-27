// TS mirror of GET /api/supported-units (frontend/README.md "GET
// /api/supported-units"; backend/app/api.py SupportedUnit model). The backend
// serves snake_case (burst_tier); mapSupportedUnit is the one place that maps
// it to the camelCase shape the rest of the frontend uses — mirrors how
// types/recommend.ts keeps request/response field names in sync with the
// Python source of truth.

export type NikkeElement = 'Fire' | 'Water' | 'Wind' | 'Iron' | 'Electric'

export type BurstTier = 1 | 2 | 3

/** 화면이 버스트 그룹을 그리는 순서. 팔레트의 지역 상수였는데, 로스터 그리드도
 * 같은 분류를 그리게 되어 한 곳에서만 정의한다. */
export const BURST_TIERS: readonly BurstTier[] = [1, 2, 3]

/** Raw wire shape returned by the backend. */
export interface SupportedUnitWire {
  slug: string
  name: string
  burst_tier: BurstTier
  element: NikkeElement
  candidates?: string[] | null
}

/** Camel-cased shape the frontend works with. */
export interface SupportedUnit {
  slug: string
  name: string
  burstTier: BurstTier
  element: NikkeElement
  /** Set only on an OWNED slug the engine fans out into several candidates
   * (one character, several modes). She can be pooled and drafted like anyone
   * else; what differs is that a RESULT deck names whichever candidate the
   * engine chose, not this slug — see `ownedSlugFor`. */
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

/** candidate slug → the owned slug it stands for. Derived from `candidates`, so
 * the frontend needs no copy of the engine's variant table. */
export const ownedSlugIndex = (units: SupportedUnit[]): Map<string, string> =>
  new Map(
    units.flatMap((unit) =>
      (unit.candidates ?? []).map((candidate) => [candidate, unit.slug] as const),
    ),
  )

/** The owned slug a result slug belongs to — itself for the vast majority.
 *
 * Anything comparing what the player SENT against what came BACK has to go
 * through this: a drafted `bready` comes back as `bready-lingering`, and a raw
 * slug comparison reads that as the engine having dropped one unit and added
 * another. */
export const ownedSlugFor = (slug: string, index: Map<string, string>): string =>
  index.get(slug) ?? slug
