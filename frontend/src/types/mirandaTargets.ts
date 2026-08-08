// Wire and view shapes for POST /api/miranda-targets. The backend speaks
// snake_case; everything past the api client speaks camelCase.
//
// No field is optional. An optional field would let a wiring gap pass the
// type-checker, which is exactly the failure this project has already paid
// for. `thresholdPercent: null` is a VALUE - "no overload total inside the
// cap wins this buff" - not a missing field.

export interface MirandaSeatWire {
  slug: string
  burst_tier: number
}

export interface MirandaCycleWire {
  index: number
  powering_up: string[]
  wake_up_crit_rate: string[]
}

export interface MirandaOverloadThresholdWire {
  slug: string
  current_percent: number
  kind: 'gain' | 'keep'
  threshold_percent: number | null
}

export interface MirandaTargetsResultWire {
  seats: MirandaSeatWire[]
  miranda_slug: string
  has_favorite_item: boolean
  cycles: MirandaCycleWire[]
  overload_thresholds: MirandaOverloadThresholdWire[]
  overload_atk_cap_percent: number
  notes: string[]
}

export interface MirandaSeat {
  slug: string
  burstTier: number
}

export interface MirandaCycle {
  index: number
  poweringUp: string[]
  wakeUpCritRate: string[]
}

export interface MirandaOverloadThreshold {
  slug: string
  currentPercent: number
  kind: 'gain' | 'keep'
  thresholdPercent: number | null
}

export interface MirandaTargetsResult {
  seats: MirandaSeat[]
  mirandaSlug: string
  hasFavoriteItem: boolean
  cycles: MirandaCycle[]
  overloadThresholds: MirandaOverloadThreshold[]
  overloadAtkCapPercent: number
  notes: string[]
}

export const mapMirandaTargetsResult = (
  wire: MirandaTargetsResultWire,
): MirandaTargetsResult => ({
  seats: wire.seats.map((seat) => ({ slug: seat.slug, burstTier: seat.burst_tier })),
  mirandaSlug: wire.miranda_slug,
  hasFavoriteItem: wire.has_favorite_item,
  cycles: wire.cycles.map((cycle) => ({
    index: cycle.index,
    poweringUp: cycle.powering_up,
    wakeUpCritRate: cycle.wake_up_crit_rate,
  })),
  overloadThresholds: wire.overload_thresholds.map((row) => ({
    slug: row.slug,
    currentPercent: row.current_percent,
    kind: row.kind,
    thresholdPercent: row.threshold_percent,
  })),
  overloadAtkCapPercent: wire.overload_atk_cap_percent,
  notes: wire.notes,
})
